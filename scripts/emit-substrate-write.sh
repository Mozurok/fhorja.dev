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
#
# Reason strings are capped at 80 chars (validator rule). Requires jq.
set -euo pipefail

die() { echo "emit-substrate-write: $*" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || die "jq is required"

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

SUB="${1:-}"; shift || true
OWNER="" FILE="" SECTION="" EVENT="write" MODE="applied" REASON="" SHA_BEFORE="null"
TASK_ROOT="." RUN_ID="" INVOKED_BY="" PRINT_HEADER=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner) OWNER="$2"; shift 2;;
    --file) FILE="$2"; shift 2;;
    --section) SECTION="$2"; shift 2;;
    --event) EVENT="$2"; shift 2;;
    --mode) MODE="$2"; shift 2;;
    --reason) REASON="$2"; shift 2;;
    --sha-before) SHA_BEFORE="$2"; shift 2;;
    --task-root) TASK_ROOT="$2"; shift 2;;
    --run-id) RUN_ID="$2"; shift 2;;
    --invoked-by) INVOKED_BY="$2"; shift 2;;
    --print-header) PRINT_HEADER=1; shift;;
    *) die "unknown flag: $1";;
  esac
done

# Resolve a relative --file that is absent in cwd against --task-root.
if [[ -n "$FILE" && "$FILE" != /* && ! -f "$FILE" && -f "$TASK_ROOT/$FILE" ]]; then
  FILE="$TASK_ROOT/$FILE"
fi

[[ -n "$SUB" ]] || die "subcommand required: sha | emit | batch"
[[ ${#REASON} -le 80 ]] || die "reason exceeds 80 chars (${#REASON})"
TS=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
[[ -n "$RUN_ID" ]] || RUN_ID=$(new_run_id)

case "$SUB" in
  sha)
    [[ -n "$FILE" ]] || die "sha needs --file"
    if [[ -n "$SECTION" ]]; then
      sha_of_section "$FILE" "$SECTION"; echo
    elif [[ ! -f "$FILE" ]]; then
      echo 'null'
    else
      while IFS= read -r sec; do
        printf '%s\t%s\n' "$(sha_of_section "$FILE" "$sec")" "$sec"
      done < <(grep '^## ' "$FILE")
    fi ;;
  emit)
    [[ -n "$OWNER" && -n "$FILE" && -n "$SECTION" && -n "$REASON" ]] || die "emit needs --owner --file --section --reason"
    [[ -f "$FILE" ]] || die "file not found (cwd and task-root checked): $FILE"
    SA=$(sha_of_section "$FILE" "$SECTION")
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
    COUNT=0; SKIP_OWNER=0; SKIP_HEADERLESS=0
    while IFS=$'\t' read -r kind sec; do
      case "$kind" in
        S)
          SA=$(sha_of_section "$FILE" "$sec")
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
    [[ "$COUNT" -gt 0 ]] || die "batch emitted 0 lines (no owner=$OWNER headers in $FILE)" ;;
  *) die "unknown subcommand: $SUB" ;;
esac
