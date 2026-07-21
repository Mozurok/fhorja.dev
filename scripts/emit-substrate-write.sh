#!/usr/bin/env bash
# emit-substrate-write.sh -- invokable emit side of the K.2 substrate write
# protocol (commands/_shared/substrate-write-protocol.md, ADR-0034, ADR-0101).
#
# Wraps RUN_ID/TS generation, sha_of_section, and the JSONL append so writers
# stop hand-copying the bash helpers (the K.8 first-lived-test found 125/126
# writes half-compliant). The script emits headers/log lines; the caller still
# performs the actual section write with its editing tool.
#
# Subcommands:
#   sha   --file F [--section '## X']
#         With --section: print the SHA-256 of the section's current bytes (or
#         'null' if the section is absent). Use BEFORE a write to capture
#         sha_before. Without --section: print one "<sha>\t<H2 section>" line
#         per H2 heading in the file (the full-rewrite pre-snapshot in one
#         invocation).
#   emit  --owner O --file F --section '## X' --event E --mode M --reason R
#         [--sha-before H|null] [--task-root DIR] [--run-id ID] [--invoked-by P]
#         [--print-header]
#         Compute sha_after from the file's CURRENT state (run AFTER the write;
#         for --event delete, sha_after is forced null) and append one JSONL
#         line to <task-root>/.wos/VERIFICATION_LOG.jsonl. With --print-header,
#         also print the exact <!-- wos:write --> header line to insert above
#         the section.
#   batch --owner O --file F --reason R [--mode applied] [--event write]
#         [--task-root DIR] [--run-id ID]
#         For EVERY H2 section in F whose preceding line is a wos:write header
#         with owner=O, emit one JSONL line (sha_before=null: batch mode is for
#         genesis-style first writes, e.g. task-init's ~25-30 sections; for
#         mutations of existing sections use per-section emit with a captured
#         sha_before). One RUN_ID/TS pair is shared across the whole batch.
#   apply --owner O --file F --section '## X' --reason R --body-file B
#         [--mode applied] [--event write|overwrite] [--task-root DIR]
#         [--run-id ID] [--invoked-by P] [--sha-before H]
#         The whole write cycle in ONE call (ADR-0110): capture sha_before,
#         insert-or-replace the transaction header above the section, splice
#         the section body from B, self-check sha_after against the intended
#         body, append one JSONL line. Die rules: the exact section line must
#         be UNIQUE in F (a duplicate, e.g. a code-fence decoy, refuses); the
#         body must not contain H2 or wos:write lines (apply never creates
#         sections); a caller-passed --sha-before that mismatches the measured
#         value refuses (the measured value is authoritative). Event defaults
#         to write when the section body was empty, overwrite otherwise.
#         sha/emit/batch behavior is unchanged; apply is additive.
#
# Reason strings are capped at 80 chars (validator rule). Requires jq.
#
# Quick combined flow (capture sha_before, then emit after the write):
#   SHA_BEFORE=$(scripts/emit-substrate-write.sh sha --file F --section '## X')
#   scripts/emit-substrate-write.sh emit --owner O --file F --section '## X' \
#     --event write --mode applied --reason R --sha-before "$SHA_BEFORE"
set -euo pipefail

die() { echo "emit-substrate-write: $*" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || die "jq is required"

# P5 (opt-in): resolve a timeout(1) binary. if/elif, NOT `command -v X && VAR=X`
# (that returns non-zero and aborts under set -e when the binary is absent).
TIMEOUT_BIN=""
if command -v timeout >/dev/null 2>&1; then TIMEOUT_BIN=timeout
elif command -v gtimeout >/dev/null 2>&1; then TIMEOUT_BIN=gtimeout
fi

sha_of_section() {
  local file="$1" header="$2"
  [[ -f "$file" ]] || { printf 'null'; return; }
  local body
  body=$(awk -v h="$header" '
    $0 == h                 { f=1; next }
    f && /^## /             { exit }
    f && /^<!-- wos:write / { next }
    f                       { print }
  ' "$file")
  if [[ -z "$body" ]]; then printf 'null'; else printf '%s' "$body" | shasum -a 256 | awk '{print $1}'; fi
}

sha_of_section_guarded() {
  # P5 (opt-in): with WOS_TIMEOUT set and a timeout binary present, bound ONLY
  # the sha compute in a child re-exec (reusing the byte-identical sha_of_section);
  # on timeout/kill, fall back to a valid 'null' record rather than hang or abort.
  local file="$1" header="$2"
  if [[ -z "$WOS_TIMEOUT" || -z "$TIMEOUT_BIN" ]]; then
    sha_of_section "$file" "$header"
    return
  fi
  local out rc=0
  out=$("$TIMEOUT_BIN" "$WOS_TIMEOUT" bash "$0" __sha-of-section "$file" "$header") || rc=$?
  if [[ "$rc" -ne 0 ]]; then
    printf 'null'
  else
    printf '%s' "$out"
  fi
}

new_run_id() {
  printf '01J%s%s' "$(date -u +%y%m%d%H%M%S)" "$(openssl rand -hex 4 2>/dev/null || head -c 4 /dev/urandom | xxd -p)"
}

append_line() {
  local task_root="$1" owner="$2" file="$3" section="$4" event="$5" mode="$6" reason="$7" sb="$8" sa="$9" rid="${10}" ts="${11}" invoked_by="${12}"
  mkdir -p "$task_root/.wos"
  jq -nc \
    --arg ts "$ts" --arg rid "$rid" --arg owner "$owner" \
    --arg file "$file" --arg section "$section" \
    --arg event "$event" --arg mode "$mode" --arg reason "$reason" \
    --arg sb "$sb" --arg sa "$sa" --arg inv "$invoked_by" \
    '{ts:$ts, run_id:$rid, owner:$owner, owner_type:"command",
      invoked_by:(if $inv=="" then null else $inv end),
      file:$file, section:$section, event:$event, mode:$mode,
      sha_before:(if $sb=="null" or $sb=="" then null else $sb end),
      sha_after:(if $sa=="null" or $sa=="" then null else $sa end),
      reason:$reason, partials:null, strategy:null}' \
    >> "$task_root/.wos/VERIFICATION_LOG.jsonl"
}

last_sha_after() {
  # S2: sha_after of the most recent log record for (basename(FILE), SECTION);
  # empty when there is no prior record. -R + fromjson? tolerates malformed lines
  # under set -e; 2>/dev/null and || true neutralize a non-zero pipeline.
  local log="$TASK_ROOT/.wos/VERIFICATION_LOG.jsonl" bn
  bn=$(basename "$FILE")
  [[ -f "$log" ]] || { printf ''; return; }
  jq -rR --arg f "$bn" --arg s "$SECTION" \
    'fromjson? | select(.file==$f and .section==$s) | .sha_after' \
    "$log" 2>/dev/null | tail -n1 || true
}

# P5 (opt-in): internal re-entry so `timeout` can bound only the sha compute in a
# child, reusing the exact sha_of_section. Sentinel first arg no emitter passes.
if [[ "${1:-}" == "__sha-of-section" ]]; then
  sha_of_section "$2" "$3"
  exit 0
fi

SUB="${1:-}"; shift || true
OWNER="" FILE="" SECTION="" EVENT="write" MODE="applied" REASON="" SHA_BEFORE="null"
TASK_ROOT="." RUN_ID="" INVOKED_BY="" PRINT_HEADER=0
BODY_FILE="" EVENT_EXPLICIT=0  # apply (ADR-0110)
DERIVE_SB=1 ALLOW_SB_MISMATCH=0 SB_EXPLICIT=0  # S2: derive-by-default since v3 wave3 (opt out: --no-derive-sha-before / WOS_DERIVE_SHA_BEFORE=0)
DERIVE_EXPLICIT=0 FIRST_LOGGED=0               # v3 wave3: flag tracking + legacy-promote entry path
WOS_TIMEOUT="${WOS_TIMEOUT:-}"  # P5 (opt-in): wall-time cap (timeout(1) duration); empty=off
while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner) OWNER="$2"; shift 2;;
    --file) FILE="$2"; shift 2;;
    --section) SECTION="$2"; shift 2;;
    --event) EVENT="$2"; EVENT_EXPLICIT=1; shift 2;;
    --mode) MODE="$2"; shift 2;;
    --reason) REASON="$2"; shift 2;;
    --sha-before) SHA_BEFORE="$2"; SB_EXPLICIT=1; shift 2;;
    --task-root) TASK_ROOT="$2"; shift 2;;
    --run-id) RUN_ID="$2"; shift 2;;
    --invoked-by) INVOKED_BY="$2"; shift 2;;
    --print-header) PRINT_HEADER=1; shift;;
    --derive-sha-before) DERIVE_SB=1; DERIVE_EXPLICIT=1; shift;;     # S2 (now the default)
    --no-derive-sha-before) DERIVE_SB=0; DERIVE_EXPLICIT=1; shift;;  # S2 opt-out (v3 wave3)
    --first-logged-write) FIRST_LOGGED=1; shift;;                    # legacy-promote entry (v3 wave3)
    --allow-sha-before-mismatch) ALLOW_SB_MISMATCH=1; shift;; # S2 (opt-in)
    --timeout) WOS_TIMEOUT="$2"; shift 2;;                    # P5 (opt-in)
    --body-file) BODY_FILE="$2"; shift 2;;                    # apply (ADR-0110)
    *) die "unknown flag: $1";;
  esac
done

# S2 env fallback (explicit flags win; if-form is set -e safe). Since v3 wave3 the
# default is derive=on, so the env's main job is the opt-out for CI or legacy flows.
if [[ "$DERIVE_EXPLICIT" != 1 ]]; then
  if [[ "${WOS_DERIVE_SHA_BEFORE:-}" == 0 ]]; then DERIVE_SB=0; fi
  if [[ "${WOS_DERIVE_SHA_BEFORE:-}" == 1 ]]; then DERIVE_SB=1; fi
fi
if [[ "${WOS_ALLOW_SHA_BEFORE_MISMATCH:-}" == 1 ]]; then ALLOW_SB_MISMATCH=1; fi
if [[ -n "$WOS_TIMEOUT" && -z "$TIMEOUT_BIN" ]]; then
  echo "emit-substrate-write: --timeout set but no timeout(1)/gtimeout(1) found; running unguarded" >&2
fi

# Resolve a relative --file that is absent in cwd against --task-root.
if [[ -n "$FILE" && "$FILE" != /* && ! -f "$FILE" && -f "$TASK_ROOT/$FILE" ]]; then
  FILE="$TASK_ROOT/$FILE"
fi

[[ -n "$SUB" ]] || die "subcommand required: sha | emit | batch"
[[ ${#REASON} -le 80 ]] || die "reason exceeds 80 chars (${#REASON})"
TS=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
[[ -n "$RUN_ID" ]] || RUN_ID=$(new_run_id)

case "$SUB" in
  help|--help)
    cat <<'USAGE'
emit-substrate-write.sh -- emit side of the K.2 substrate write protocol.

Subcommands:
  sha   --file F [--section '## X']
        With --section: print the SHA-256 of the section's current bytes (or
        'null' if the section is absent). Without --section: print one
        "<sha>\t<H2 section>" line per H2 heading in the file.
  emit  --owner O --file F --section '## X' --event E --mode M --reason R
        [--sha-before H|null] [--task-root DIR] [--run-id ID] [--invoked-by P]
        [--print-header]
        Append one JSONL line to <task-root>/.wos/VERIFICATION_LOG.jsonl.
  batch --owner O --file F --reason R [--mode applied] [--event write]
        [--task-root DIR] [--run-id ID]
        Emit one JSONL line for every H2 section preceded by a wos:write
        header with owner=O.

Combined flow example:
  SHA_BEFORE=$(scripts/emit-substrate-write.sh sha --file F --section '## X')
  scripts/emit-substrate-write.sh emit --owner O --file F --section '## X' \
    --event write --mode applied --reason R --sha-before "$SHA_BEFORE"
USAGE
    exit 0 ;;
  sha)
    [[ -n "$FILE" ]] || die "sha needs --file"
    if [[ -n "$SECTION" ]]; then
      sha_of_section_guarded "$FILE" "$SECTION"; echo
    elif [[ ! -f "$FILE" ]]; then
      echo 'null'
    else
      while IFS= read -r sec; do
        printf '%s\t%s\n' "$(sha_of_section_guarded "$FILE" "$sec")" "$sec"
      done < <(grep '^## ' "$FILE")
    fi ;;
  emit)
    [[ -n "$OWNER" && -n "$FILE" && -n "$SECTION" && -n "$REASON" ]] || die "emit needs --owner --file --section --reason"
    [[ -f "$FILE" ]] || die "file not found (cwd and task-root checked): $FILE"
    if [[ "$FIRST_LOGGED" == 1 ]]; then
      # v3 wave3: dedicated entry for the FIRST logged write to an EXISTING
      # legacy section. Asserts no prior record; records the caller's captured
      # pre-write sha (capture-then-write) or, when omitted, the current
      # measured value; event defaults to legacy-promote (already in the enum).
      DERIVED=$(last_sha_after)
      [[ -z "$DERIVED" ]] || die "--first-logged-write: a prior log record exists for $(basename "$FILE") '$SECTION' (last sha_after=$DERIVED); use the normal derive path"
      if [[ "$SB_EXPLICIT" != 1 ]]; then
        SHA_BEFORE=$(sha_of_section_guarded "$FILE" "$SECTION")
      fi
      if [[ "$EVENT_EXPLICIT" -eq 0 ]]; then EVENT="legacy-promote"; fi
      DERIVE_SB=0
    fi
    if [[ "$DERIVE_SB" == 1 ]]; then
      # S2 (default since v3 wave3): derive sha_before from the log instead of
      # trusting the flag.
      DERIVED=$(last_sha_after)
      if [[ -z "$DERIVED" ]]; then
        if [[ "$SB_EXPLICIT" == 1 && "$SHA_BEFORE" != "null" && "$ALLOW_SB_MISMATCH" != 1 ]]; then
          die "sha_before for a section with no prior log record must be null (got '$SHA_BEFORE'). If this is the first LOGGED write to an existing legacy section, pass --first-logged-write (records event=legacy-promote with the measured value); if the section is genuinely new, pass --sha-before null; --allow-sha-before-mismatch overrides"
        fi
        SHA_BEFORE="null"
      else
        if [[ "$SB_EXPLICIT" == 1 && "$SHA_BEFORE" != "$DERIVED" && "$ALLOW_SB_MISMATCH" != 1 ]]; then
          die "sha_before mismatch for $(basename "$FILE") '$SECTION': caller='$SHA_BEFORE' derived='$DERIVED' (pass --allow-sha-before-mismatch to override)"
        fi
        SHA_BEFORE="$DERIVED"
      fi
    fi
    SA=$(sha_of_section_guarded "$FILE" "$SECTION")
    if [[ "$EVENT" == "delete" ]]; then
      [[ "$SHA_BEFORE" != "null" ]] || die "delete requires --sha-before (the removed section's last hash)"
      SA="null"
    fi
    append_line "$TASK_ROOT" "$OWNER" "$(basename "$FILE")" "$SECTION" "$EVENT" "$MODE" "$REASON" "$SHA_BEFORE" "$SA" "$RUN_ID" "$TS" "$INVOKED_BY"
    if [[ "$PRINT_HEADER" -eq 1 ]]; then
      printf '<!-- wos:write owner=%s section='\''%s'\'' run_id=%s ts=%s reason=%s mode=%s -->\n' \
        "$OWNER" "$SECTION" "$RUN_ID" "$TS" "$REASON" "$MODE"
    fi ;;
  batch)
    [[ -n "$OWNER" && -n "$FILE" && -n "$REASON" ]] || die "batch needs --owner --file --reason"
    [[ -f "$FILE" ]] || die "file not found (cwd and task-root checked): $FILE"
    FOUND=$(awk -v o="owner=$OWNER " '
      /^<!-- wos:write / { hdr = index($0, o) ? 1 : 0; next }
      /^## /             { if (hdr == 1) n++; hdr = 0; next }
      { hdr = 0 }
      END { print n + 0 }
    ' "$FILE")
    COUNT=0; SKIP_OWNER=0; SKIP_HEADERLESS=0
    while IFS=$'\t' read -r kind sec; do
      case "$kind" in
        S)
          SA=$(sha_of_section_guarded "$FILE" "$sec")
          append_line "$TASK_ROOT" "$OWNER" "$(basename "$FILE")" "$sec" "$EVENT" "$MODE" "$REASON" "null" "$SA" "$RUN_ID" "$TS" "$INVOKED_BY"
          COUNT=$((COUNT + 1));;
        O) SKIP_OWNER=$((SKIP_OWNER + 1));;
        H) SKIP_HEADERLESS=$((SKIP_HEADERLESS + 1));;
      esac
    done < <(awk -v o="owner=$OWNER " '
      /^<!-- wos:write / { hdr = index($0, o) ? 1 : 2; next }
      /^## / {
        if (hdr == 1)      print "S\t" $0
        else if (hdr == 2) print "O\t" $0
        else               print "H\t" $0
        hdr = 0; next
      }
      { hdr = 0 }
    ' "$FILE")
    echo "emitted $COUNT, skipped $SKIP_OWNER other-owner, $SKIP_HEADERLESS headerless ($FILE, run_id=$RUN_ID)"
    [[ "$COUNT" -gt 0 ]] || die "batch emitted 0 lines (no owner=$OWNER headers in $FILE)"
    [[ "$COUNT" -eq "$FOUND" ]] || die "batch count mismatch: found $FOUND owner=$OWNER section(s) but emitted $COUNT ($FILE, run_id=$RUN_ID)" ;;
  apply)
    # ADR-0110: the whole write cycle in one call. sha/emit/batch untouched.
    [[ -n "$OWNER" && -n "$FILE" && -n "$SECTION" && -n "$REASON" ]] || die "apply needs --owner --file --section --reason"
    [[ -f "$FILE" ]] || die "file not found (cwd and task-root checked): $FILE"
    [[ -n "$BODY_FILE" ]] || die "apply needs --body-file (the new section body)"
    [[ -f "$BODY_FILE" ]] || die "body file not found: $BODY_FILE"
    if grep -qE '^## |^<!-- wos:write ' "$BODY_FILE"; then
      die "apply body must not contain H2 headings or wos:write lines (apply never creates sections; header lines are excluded from the section hash and would break the self-check)"
    fi
    MATCHES=$(grep -cxF "$SECTION" "$FILE" || true)
    [[ "$MATCHES" -eq 1 ]] || die "apply target '$SECTION' must match exactly one line in $FILE (found $MATCHES; a duplicate can be a code-fence decoy and the splice boundary is not fence-aware)"
    SB=$(sha_of_section "$FILE" "$SECTION")
    if [[ "$SB_EXPLICIT" == 1 && "$SHA_BEFORE" != "$SB" ]]; then
      die "apply sha_before mismatch for $(basename "$FILE") '$SECTION': caller expected '$SHA_BEFORE', measured '$SB' (the measured value is authoritative)"
    fi
    if [[ "$EVENT_EXPLICIT" -eq 0 ]]; then
      if [[ "$SB" == "null" ]]; then EVENT="write"; else EVENT="overwrite"; fi
    fi
    HDR_LINE=$(printf '<!-- wos:write owner=%s section='\''%s'\'' run_id=%s ts=%s reason=%s mode=%s -->' \
      "$OWNER" "$SECTION" "$RUN_ID" "$TS" "$REASON" "$MODE")
    TMP_OUT=$(mktemp "${TMPDIR:-/tmp}/wos-apply.XXXXXX")
    awk -v sec="$SECTION" -v hdr="$HDR_LINE" -v bodyfile="$BODY_FILE" '
      BEGIN {
        n = 0
        while ((getline line < bodyfile) > 0) body[n++] = line
        close(bodyfile)
      }
      { lines[NR] = $0 }
      END {
        s = 0
        for (i = 1; i <= NR; i++) if (lines[i] == sec) { s = i; break }
        e = NR + 1
        for (i = s + 1; i <= NR; i++) if (lines[i] ~ /^## /) { e = i; break }
        stop = e - 1
        if (e <= NR && stop >= s + 1 && lines[stop] ~ /^<!-- wos:write /) stop = stop - 1
        pre_end = s - 1
        if (pre_end >= 1 && lines[pre_end] ~ /^<!-- wos:write /) pre_end = pre_end - 1
        for (i = 1; i <= pre_end; i++) print lines[i]
        print hdr
        print lines[s]
        for (j = 0; j < n; j++) print body[j]
        if (e <= NR) print ""
        for (i = stop + 1; i <= NR; i++) print lines[i]
      }
    ' "$FILE" > "$TMP_OUT"
    SA=$(sha_of_section "$TMP_OUT" "$SECTION")
    BODY_CONTENT=$(<"$BODY_FILE")
    if [[ -z "$BODY_CONTENT" ]]; then
      EXPECT="null"
    else
      EXPECT=$(printf '%s' "$BODY_CONTENT" | shasum -a 256 | awk '{print $1}')
    fi
    if [[ "$SA" != "$EXPECT" ]]; then
      rm -f "$TMP_OUT"
      die "apply self-check failed for '$SECTION': post-splice hash '$SA' != intended-body hash '$EXPECT' (splice boundary error; original file untouched)"
    fi
    mv "$TMP_OUT" "$FILE"
    append_line "$TASK_ROOT" "$OWNER" "$(basename "$FILE")" "$SECTION" "$EVENT" "$MODE" "$REASON" "$SB" "$SA" "$RUN_ID" "$TS" "$INVOKED_BY"
    echo "applied '$SECTION' in $FILE (event=$EVENT sha_before=$SB sha_after=$SA run_id=$RUN_ID)" ;;
  *) die "unknown subcommand: $SUB" ;;
esac
