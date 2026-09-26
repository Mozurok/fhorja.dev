#!/usr/bin/env bash
# test-install-payload.sh -- pins that the installer ships the RUNTIME payload on every
# sync, not only under --with-docs.
# Run from anywhere:  bash scripts/tests/test-install-payload.sh
#
# Why this exists. Every command file cites at least one `wos/<topic>.md`, and several
# of those loads are declared MANDATORY (an unread floor is a skipped gate, not a saved
# token). Before this, `sync_workflow_docs()` copied four .md files plus templates/ and
# nothing else, and it ran only under `--with-docs`, whose default is 0 and which
# `bootstrap-user-setup.sh` never suggests. So an installed session resolved those paths
# against nothing.
#
# The load-bearing check is check 1, and it is keyed on a run with NO FLAGS on purpose.
# Keying it on the copy function instead would be satisfiable while the payload stayed
# behind `--with-docs`, which is exactly what D-2 forbids: the criterion could not
# observe the failure it exists to prevent.
#
# Every run here points the installer at a scratch directory through the env overrides
# it already supports, so the real home is never touched.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SYNC="$SCRIPT_DIR/../sync-workflow-slash-commands.sh"

# The spine size is DERIVED, never written here. It was hardcoded to 14 until 2026-08-30, when
# ADR-0178 added `where-we-at` and `test-strategy` and this suite failed with "want 14" on a
# correct tree. A test that has to be edited every time the thing it measures changes is a test
# that will eventually be edited to match a bug. Counted the same way the installer filters:
# a flat command whose x-wos-profiles inline list names the tier.
MINIMAL_N="$(grep -l 'x-wos-profiles: \[[^]]*minimal' "$REPO_ROOT"/commands/*.md 2>/dev/null | wc -l | tr -d ' ')"
if [ -z "$MINIMAL_N" ] || [ "$MINIMAL_N" = "0" ]; then
  fail "could not derive the minimal spine size from commands/*.md; the extractor is broken"
  MINIMAL_N=-1
fi
fails=0
checks=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); echo "  FAIL $1"; fails=$((fails+1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Run the installer fully sandboxed: every destination it knows about goes under $TMP.
# HOME is redirected FIRST and the explicit vars second, and that order is the point: every
# destination in the installer defaults to "${HOME}/...", so overriding HOME sandboxes any
# destination that exists now or is added later. The explicit list alone is a hand-maintained
# allowlist, and it already failed once: a Codex docs destination was added to the installer,
# not added here, and the run wrote 125 topics into the real home.
run_install() {  # run_install [extra-args...]
  HOME="$TMP/home" \
  CODEX_WORKFLOW_DOCS_DIR="$TMP/codex/workflow-docs" \
  CURSOR_COMMANDS_DIR="$TMP/cursor/commands" \
  CLAUDE_COMMANDS_DIR="$TMP/claude/commands" \
  CODEX_PROMPTS_DIR="$TMP/codex/prompts" \
  CLAUDE_SKILLS_DIR="$TMP/claude/skills" \
  CURSOR_SKILLS_DIR="$TMP/cursor/skills" \
  CODEX_SKILLS_DIR="$TMP/agents/skills" \
  WORKFLOW_DOCS_DIR="$TMP/cursor/workflow-docs" \
  CLAUDE_WORKFLOW_DOCS_DIR="$TMP/claude/workflow-docs" \
  KIMI_CODE_HOME="$TMP/kimi" \
  bash "$SYNC" --no-skills "$@" >"$TMP/out.txt" 2>&1
  echo $?
}

REPO_WOS_COUNT="$(find "$REPO_ROOT/wos" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"

# Floor first. Both key checks used to be satisfiable at zero: with $REPO_ROOT/wos missing,
# the count compared 0 against 0 and the per-path loop read an empty stream, so the harness
# printed "0 of 0 topics" and self-certified against nothing.
if [ ! -d "$REPO_ROOT/wos" ] || [ "$REPO_WOS_COUNT" -lt 100 ]; then
  echo "HARNESS ERROR: source wos/ missing or implausibly small ($REPO_WOS_COUNT topics at $REPO_ROOT/wos)" >&2
  exit 2
fi

# THE assertion. One property, used at every destination, replacing three separate proxies
# (a file count, a per-path existence loop, a directory-exists test). Each proxy was passed by
# a degenerate installer: the count by a flattened tree, the path loop by zero-byte files, the
# directory test by a bare mkdir. `diff -r` compares structure AND content, so all three
# degenerate shapes fail it and no further proxy is needed.
payload_state() {  # payload_state <dest-root>; echoes '' when byte-identical to the repo
  local d="$1/wos"
  if [ ! -d "$d" ]; then printf 'absent'; return; fi
  if ! diff -r "$REPO_ROOT/wos" "$d" >/dev/null 2>&1; then printf 'differs from the repo tree'; return; fi
}

# Every destination the installer can write, so an "it wrote nothing" assertion means it,
# rather than checking one path and calling it proof.
ALL_DESTS=(
  "$TMP/cursor/commands" "$TMP/claude/commands" "$TMP/codex/prompts"
  "$TMP/cursor/workflow-docs" "$TMP/claude/workflow-docs" "$TMP/codex/workflow-docs"
  "$TMP/claude/skills" "$TMP/cursor/skills" "$TMP/agents/skills"
)
any_dest_written() {  # echoes the first destination that exists and is non-empty, or nothing
  local d
  for d in "${ALL_DESTS[@]}"; do
    if [ -d "$d" ] && [ -n "$(ls -A "$d" 2>/dev/null)" ]; then printf '%s' "$d"; return; fi
  done
}


# 1. THE ONE THAT MATTERS. A run with NO flags ships a payload byte-identical to the repo's
#    wos/. Keyed on a bare run, because keying it on the copy function would pass while the
#    payload stayed gated behind --with-docs.
rc=$(run_install)
state="$(payload_state "$TMP/claude/workflow-docs")"
[ "$rc" = "0" ] && [ -z "$state" ] \
  && pass "no-flag run ships wos/ byte-identical to the repo ($REPO_WOS_COUNT topics)" \
  || fail "no-flag run payload $state (exit $rc)"

# 1b. A topic retired from the repository leaves an installed payload on the next sync (B33).
#     Planted in the payload the run above wrote, then the same bare run again: diff -r in
#     payload_state fails on any extra file, so a sync that only copies on top fails here.
printf 'retired topic\n' > "$TMP/claude/workflow-docs/wos/retired-topic-for-test.md"
rc=$(run_install)
state="$(payload_state "$TMP/claude/workflow-docs")"
[ "$rc" = "0" ] && [ -z "$state" ] && [ ! -e "$TMP/claude/workflow-docs/wos/retired-topic-for-test.md" ] \
  && pass "a topic retired from the repo is removed from the installed payload on the next sync" \
  || fail "a retired topic survived the next sync (payload $state, exit $rc)"

# 1c. A template retired from the repository leaves the --with-docs copy on the next sync
#     (ADR-0228, the installer half of D-6 in the 2026-09-23 backlog task). Same shape as 1b:
#     one planted at the top of templates/ and one in a subdirectory, then diff -r against the
#     repository, so a sync that only copies on top fails here.
rc=$(run_install --with-docs)
tdocs="$TMP/claude/workflow-docs/templates"
printf 'retired template\n' > "$tdocs/RETIRED_FOR_TEST.template.md"
mkdir -p "$tdocs/foundations"; printf 'retired\n' > "$tdocs/foundations/retired-for-test.md"
rc=$(run_install --with-docs)
if [ "$rc" != "0" ]; then
  fail "the --with-docs sync exited $rc"
elif [ -e "$tdocs/RETIRED_FOR_TEST.template.md" ] || [ -e "$tdocs/foundations/retired-for-test.md" ]; then
  fail "a template retired from the repo survived the next --with-docs sync"
elif ! diff -r "$REPO_ROOT/templates" "$tdocs" >/dev/null 2>&1; then
  fail "the installed templates/ differs from the repo's after the sync"
else
  pass "a template retired from the repo is removed from the --with-docs copy on the next sync"
fi

# 2. The payload is not gated by --with-docs. Same assertion, stated so a future edit that
#    moves the copy back inside sync_workflow_docs() fails here rather than silently.
grep -q 'wos' <<<"$(sed -n '/^sync_workflow_docs()/,/^}/p' "$SYNC")" \
  && fail "the wos/ copy lives inside sync_workflow_docs(), which only runs under --with-docs" \
  || pass "the wos/ copy is outside sync_workflow_docs()"

# 3. Per-tool gating. --cursor-only must not write a Claude destination. The first pass
#    put these calls outside the DO_CURSOR / DO_CLAUDE guards every sibling call respects,
#    so a tool-scoped run wrote both trees while correctly writing zero excluded commands.
rm -rf "$TMP/claude" "$TMP/cursor"
rc=$(run_install --cursor-only)
if [ -d "$TMP/claude/workflow-docs/wos" ]; then
  fail "--cursor-only wrote the Claude payload"
elif [ -n "$(payload_state "$TMP/cursor/workflow-docs")" ]; then
  fail "--cursor-only Cursor payload: $(payload_state "$TMP/cursor/workflow-docs")"
else
  pass "--cursor-only wrote only the Cursor payload, byte-identical"
fi

# 3a. The mirror of 3, for the tool 3 does not cover. Exit criterion 2 names --cursor-only OR
#     --claude-only, and closure found only the first was ever run: the guards are symmetric in
#     the source, which is an argument, not evidence.
rm -rf "$TMP/claude" "$TMP/cursor"
rc=$(run_install --claude-only)
if [ -d "$TMP/cursor/workflow-docs/wos" ]; then
  fail "--claude-only wrote the Cursor payload"
elif [ -n "$(payload_state "$TMP/claude/workflow-docs")" ]; then
  fail "--claude-only Claude payload: $(payload_state "$TMP/claude/workflow-docs")"
else
  pass "--claude-only wrote only the Claude payload, byte-identical"
fi

# 3b. ONLY the allowlisted scripts ship (D-3, answered per script by ADR-0214). Until
#     2026-09-22 this asserted that NO script ships, which was D-3's rule then. D-3 itself left
#     "which scripts can ship at all" as a per-script question, and ADR-0214 answered it for one.
#     The guarantee this check exists for is unchanged: nothing reaches the payload by accident.
#     A script is allowed only when it is named in the installer's SHIPPED_SCRIPTS, so a stray
#     .sh, .py or executable still fails, and the allowlist is read from the installer rather
#     than restated here, so the two cannot drift apart.
rm -rf "$TMP/claude" "$TMP/cursor" "$TMP/codex"
rc=$(run_install)
ALLOWED="$(sed -n 's/^SHIPPED_SCRIPTS=(\(.*\))$/\1/p' "$REPO_ROOT/scripts/sync-workflow-slash-commands.sh")"
stray=""
while IFS= read -r f; do
  [ -z "$f" ] && continue
  name="$(basename "$f")"
  case " $ALLOWED " in *" $name "*) continue ;; esac
  stray="${stray}${f} "
done < <(find "$TMP/claude/workflow-docs" "$TMP/cursor/workflow-docs" "$TMP/codex/workflow-docs" \
           \( -name '*.sh' -o -name '*.py' -o -perm -u+x -type f \) 2>/dev/null)
[ -z "$stray" ] \
  && pass "only allowlisted scripts ship with the payload (${ALLOWED:-none})" \
  || fail "the payload shipped a script that is not in SHIPPED_SCRIPTS: $(printf '%s' "$stray" | cut -c1-140)"

# 3c. Every allowlisted script passes BOTH of D-3's tests, run as an installed copy. Asserted
#     here so an entry cannot be added to SHIPPED_SCRIPTS on a reading alone, which is how D-3
#     was first answered wrongly: a measured subset ranked by how often a script was MENTIONED
#     rather than by whether it runs where it lands.
#     Test 1, runs where it lands: no path derived from its own location.
#     Test 2, names the absence: against an empty target it must not print a well-formed empty
#     result with exit 0, which is the portfolio-review.sh failure D-3 was written from.
EMPTY="$TMP/empty-project"; mkdir -p "$EMPTY/active" "$EMPTY/archive"
# An empty log, for the validator's probe: a log with no lines records no write.
mkdir -p "$EMPTY/.wos"; : > "$EMPTY/.wos/VERIFICATION_LOG.jsonl"
# A real substrate file for the emitter's probe, so the only thing missing is the task folder
# its --task-root names. The old emitter wrote a stray log there with exit 0.
printf '# DOC\n\n## S\nbody\n' > "$EMPTY/doc.md"
# A PATH with no secret scanner on it, for the secret gate's probe: only what the gate needs.
NOSCAN="$TMP/noscan-bin"; mkdir -p "$NOSCAN"
for t in mktemp rm grep head; do p="$(command -v "$t")" && ln -s "$p" "$NOSCAN/$t"; done
BASH_BIN="$(command -v bash)"
for s in $ALLOWED; do
  inst="$TMP/claude/workflow-docs/scripts/$s"
  if [ ! -x "$inst" ]; then fail "D-3 test: $s is allowlisted but did not install as an executable"; continue; fi
  # A script may locate itself only to reach a sibling that ships beside it (ADR-0224): the
  # integrity wrapper runs three validators from its own directory. Anything else derived from
  # its location (a parent directory, a repo root, __file__, dirname "$0") reads the wrong tree
  # on an install. So BASH_SOURCE is allowed only on the line defining SCRIPT_DIR, and every
  # other SCRIPT_DIR use must be "$SCRIPT_DIR/<name>" with <name> in SHIPPED_SCRIPTS.
  selfloc=""
  if grep -qE '__file__|dirname "\$0"' "$inst"; then
    selfloc="uses __file__ or dirname \$0"
  elif grep -qE 'BASH_SOURCE|SCRIPT_DIR' "$inst"; then
    while IFS= read -r ln; do
      case "$ln" in
        *'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"'*) continue ;;
      esac
      if printf '%s' "$ln" | grep -q 'BASH_SOURCE'; then selfloc="BASH_SOURCE outside the SCRIPT_DIR definition"; break; fi
      bad=""
      while IFS= read -r use; do
        tgt="${use#*SCRIPT_DIR}"; tgt="${tgt#\}}"; tgt="${tgt#/}"
        case " $ALLOWED " in *" $tgt "*) ;; *) bad="${tgt:-<bare SCRIPT_DIR>}"; break ;; esac
      done < <(printf '%s\n' "$ln" | grep -oE '\$\{?SCRIPT_DIR\}?(/[A-Za-z0-9._-]+)?')
      if [ -n "$bad" ]; then selfloc="reaches $bad through SCRIPT_DIR, which is not a shipped sibling"; break; fi
    done < <(grep -E 'BASH_SOURCE|SCRIPT_DIR' "$inst")
  fi
  if [ -n "$selfloc" ]; then
    fail "D-3 test 1: $s derives a path from its own location ($selfloc), so an installed copy reads the wrong tree"
    continue
  fi
  # Each script is probed with the empty target in the argument position it reads.
  case "$s" in
    compute-task-outcome.py) out="$(cd "$TMP" && python3 "$inst" "$EMPTY/active/2026-01-01_absent" --merge-status merged 2>&1)" ;;
    ingest-scan.py) out="$(cd "$TMP" && printf '' | python3 "$inst" 2>&1)" ;;
    scan-substrate-orphans.py) out="$(cd "$TMP" && python3 "$inst" "$EMPTY/active/2026-01-01_absent/TASK_STATE.md" 2>&1)" ;;
    emit-substrate-write.sh) out="$(cd "$TMP" && bash "$inst" emit --owner probe --file "$EMPTY/doc.md" --section '## S' --reason probe --task-root "$EMPTY/active" 2>&1)" ;;
    scan-substrate-headers.sh|verify-substrate-batch.sh|check-live-markers.sh|check-plan-coverage.sh)
      out="$(cd "$TMP" && bash "$inst" "$EMPTY/active" 2>&1)" ;;
    verify-log-validator.py) out="$(cd "$TMP" && python3 "$inst" "$EMPTY/.wos/VERIFICATION_LOG.jsonl" 2>&1)" ;;
    plan-adherence.py) out="$(cd "$TMP" && python3 "$inst" "$EMPTY/active" 2>&1)" ;;
    memory-lint.sh) out="$(cd "$TMP" && bash "$inst" "$EMPTY/active/2026-01-01_absent" 2>&1)" ;;
    secret-scan-gate.sh) out="$(cd "$TMP" && PATH="$NOSCAN" "$BASH_BIN" "$inst" "$EMPTY" 2>&1)" ;;
    portfolio-review.sh) out="$(cd "$EMPTY/active" && bash "$inst" 2>&1)" ;;
    *)    out="$(cd "$TMP" && bash "$inst" "probe" "$EMPTY" 2>&1)" ;;
  esac
  rc_probe=$?
  # A named absence followed by a pass verdict is still a pass on a target nobody read: the
  # orphan scanner printed "file not found" and then OK with exit 0 until 2026-09-22, and the
  # absence pattern alone accepted it.
  # The pass shapes are each shipped script's own clean line (ADR-0224 added the last five: a
  # plan-adherence verdict, a live-marker "none", a header count of 0, a lint count of 0 and a
  # batch combined=0 were each printed with exit 0 on a target nobody read).
  if [ "$rc_probe" = "0" ] && printf '%s' "$out" | grep -qE '^OK$|VERDICT: CLEAN|VERDICT: CONFORMANT|Live-markers: none|substrate_header_drift_count: 0$|MEMORY-LINT: 0 finding|combined=0'; then
    fail "D-3 test 2: $s reports a pass verdict with exit 0 on a target it did not read"
  elif printf '%s' "$out" | grep -qiE 'no .* found|0 ranked|not found|nothing to|nothing was checked|not scanned|not measured|not checked'; then
    pass "D-3 tests: $s runs from outside the repo and names an empty target instead of reporting clean"
  else
    fail "D-3 test 2: $s gave no named absence on an empty target: $(printf '%s' "$out" | head -1 | cut -c1-100)"
  fi
done

# 3c. A bad --project path refuses BEFORE anything is written. The previous version accepted
#     ANY non-zero exit as "the refusal" and inspected one destination out of nine, so it went
#     green on a run that had already written 14 command files.
rm -rf "$TMP/claude" "$TMP/cursor" "$TMP/codex" "$TMP/agents"
rc=$(run_install --project="$TMP/definitely-not-a-directory")
msg="$(cat "$TMP/out.txt")"
wrote="$(any_dest_written)"
if [ "$rc" = "0" ]; then
  fail "a bad --project did not refuse (exit 0)"
elif ! printf '%s' "$msg" | grep -q 'Project path is not a directory'; then
  fail "a bad --project exited $rc for some other reason, not the path check"
elif [ -n "$wrote" ]; then
  fail "a bad --project refused but had already written ${wrote#$TMP/}"
else
  pass "a bad --project refuses for the stated reason, with all 9 destinations untouched"
fi

# 3d. A valid --project receives the payload, which the analogous docs sync already served.
rm -rf "$TMP/claude" "$TMP/cursor"; mkdir -p "$TMP/proj"
rc=$(run_install --project="$TMP/proj")
state="$(payload_state "$TMP/proj/.cursor/workflow-docs")"
[ -z "$state" ] \
  && pass "--project receives a byte-identical payload" \
  || fail "--project payload $state (exit $rc)"

# 3e. --codex-only must ship the payload too. D-2 says every sync; the payload used to be
#     gated on the other two tools alone, so a codex-scoped run installed prompts whose
#     MANDATORY wos/ loads resolved against nothing on the whole machine.
rm -rf "$TMP/claude" "$TMP/cursor" "$TMP/codex"
rc=$(run_install --codex-only)
state="$(payload_state "$TMP/codex/workflow-docs")"
[ -z "$state" ] \
  && pass "--codex-only ships a byte-identical payload" \
  || fail "--codex-only payload $state (exit $rc)"

# 4. --dry-run announces the payload instead of lying about what it copies.
rc=$(run_install --dry-run)
out="$(cat "$TMP/out.txt")"
if ! printf '%s' "$out" | grep -q 'wos'; then
  fail "--dry-run does not mention wos/, so the announcement understates the copy"
elif printf '%s' "$out" | grep -qE 'runtime script|scripts/ ->'; then
  fail "--dry-run still announces a scripts subset that D-3 removed"
else
  pass "--dry-run announces wos/ and no scripts subset"
fi

# 5. A dry run writes nothing. Guards the announcement added above from becoming a real copy.
# All FOUR payload destinations, not one. The previous version cleared and inspected only the
# Claude path, so a dry run that wrote 250 files to the other three still reported clean.
rm -rf "$TMP/claude" "$TMP/cursor" "$TMP/codex" "$TMP/proj"; mkdir -p "$TMP/proj"
rc=$(run_install --dry-run --project="$TMP/proj")
wrote="$(find "$TMP/claude/workflow-docs" "$TMP/cursor/workflow-docs" "$TMP/codex/workflow-docs" \
           "$TMP/proj/.cursor/workflow-docs" -type f 2>/dev/null | wc -l | tr -d ' ')"
[ "$wrote" = "0" ] \
  && pass "--dry-run wrote no payload to any of the 4 destinations" \
  || fail "--dry-run WROTE $wrote file(s); a dry run must not touch any destination"

# 6. Skills-on minimal. The --no-skills wrapper above cannot observe this path. A prior
#    refuse (ADR-0059 D-4) exited 1 on --profile=minimal --with-skills even though
#    branch-commit is already [minimal, core, full] and tier-routing-closure is clean.
#    HOME stays sandboxed. Existing payload checks above stay on --no-skills.
run_install_skills() {  # run_install_skills [extra-args...]
  HOME="$TMP/home" \
  CODEX_WORKFLOW_DOCS_DIR="$TMP/codex/workflow-docs" \
  CURSOR_COMMANDS_DIR="$TMP/cursor/commands" \
  CLAUDE_COMMANDS_DIR="$TMP/claude/commands" \
  CODEX_PROMPTS_DIR="$TMP/codex/prompts" \
  CLAUDE_SKILLS_DIR="$TMP/claude/skills" \
  CURSOR_SKILLS_DIR="$TMP/cursor/skills" \
  CODEX_SKILLS_DIR="$TMP/agents/skills" \
  KIMI_SKILLS_DIR="$TMP/kimi/skills" \
  WORKFLOW_DOCS_DIR="$TMP/cursor/workflow-docs" \
  CLAUDE_WORKFLOW_DOCS_DIR="$TMP/claude/workflow-docs" \
  KIMI_CODE_HOME="$TMP/kimi" \
  bash "$SYNC" "$@" >"$TMP/out.txt" 2>&1
  echo $?
}

rm -rf "$TMP/claude" "$TMP/cursor" "$TMP/codex" "$TMP/agents" "$TMP/kimi" "$TMP/home"
mkdir -p "$TMP/home"
rc=$(run_install_skills --profile=minimal --with-skills)
out="$(cat "$TMP/out.txt")"
skill_n="$(find "$TMP/claude/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
cmd_n="$(find "$TMP/claude/commands" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
if printf '%s' "$out" | grep -q 'Refusing: skills cannot be mirrored'; then
  fail "minimal+skills still refuses"
elif [ "$rc" != "0" ]; then
  fail "minimal+skills exit $rc"
elif [ "$skill_n" != "$MINIMAL_N" ]; then
  fail "minimal+skills installed $skill_n skills, want $MINIMAL_N"
elif [ "$cmd_n" != "$MINIMAL_N" ]; then
  fail "minimal+skills installed $cmd_n commands, want $MINIMAL_N"
elif ! printf '%s' "$out" | grep -q 'Only the everyday spine commands'; then
  fail "summary does not name the everyday spine"
else
  pass "minimal+skills installs $MINIMAL_N commands and $MINIMAL_N skills (exit 0)"
fi

help_out="$(bash "$SYNC" --help 2>&1 || true)"
if printf '%s' "$help_out" | grep -q 'minimal is REFUSED for skills'; then
  fail "installer help still refuses minimal skills"
elif ! printf '%s' "$help_out" | grep -q 'minimal (the everyday'; then
  fail "installer help does not describe the minimal profile"
else
  pass "installer help describes the minimal profile and does not refuse minimal skills"
fi

# LAST. The sandbox itself. Every installer destination defaults to ${HOME}/..., so anything
# found under the redirected HOME means a destination bypassed the explicit paths this harness
# names. Catching it here is what stops the next added destination from reaching the real home.
escaped="$(find "$TMP/home" -type f 2>/dev/null | head -3)"
[ -z "$escaped" ] \
  && pass "no destination escaped into HOME" \
  || fail "a destination wrote under HOME instead of a named path: $(printf '%s' "$escaped" | tr '\n' ' ' | cut -c1-140)"

echo
if [ "$fails" -eq 0 ]; then echo "test-install-payload: all $checks checks passed"; exit 0
else echo "test-install-payload: $fails of $checks check(s) FAILED"; exit 1; fi
