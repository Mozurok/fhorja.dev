#!/usr/bin/env bash
# test-verify-log-scope.sh -- verify-log-validator.py reads a digest at the scope the line
# declares, refuses to call an empty log clean, and resolves --task from where it is run.
# Run from anywhere:  bash scripts/tests/test-verify-log-scope.sh
#
# Why this exists (ADR-0224). The only substrate fallback an installed user gets, when the
# per-section helper is unreachable, is a whole-file digest marked "sha_scope":"file"
# (commands/_shared/substrate-digest-fallback.md). The validator had no notion of scope, so it
# recomputed a SECTION digest and reported content-vs-log drift on every such line. The closure
# integrity floor runs it with --check-deletes, so every close that used the fallback failed.
# Measured against the validator before this change: 9 of 12 fail (1, 2b, 3, 4b, 5, 6, 7, 7b,
# 8). The three that pass on both (2, 4, 5b) pin that the fix did not turn the check off.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATOR="$SCRIPT_DIR/../verify-log-validator.py"
CUT="2026-07-18T00:00:00.000Z"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "ok   - $1"; }
fail() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }
check() { if [[ "$2" -eq 0 ]]; then ok "$1"; else fail "$1"; fi }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

filesha() { shasum -a 256 "$1" | awk '{print $1}'; }

# line TS RUN SECTION SHA_BEFORE SHA_AFTER SCOPE  (SCOPE: file, or a lone hyphen for no field)
line() {
  local sb=$4 sa=$5 scope=""
  [[ "$sb" == null ]] || sb="\"$sb\""
  [[ "$sa" == null ]] || sa="\"$sa\""
  [[ "$6" == - ]] || scope=",\"sha_scope\":\"$6\""
  printf '{"ts":"%s","run_id":"%s","owner":"t","owner_type":"command","invoked_by":null,"file":"TASK_STATE.md","section":"%s","event":"write","mode":"applied","sha_before":%s,"sha_after":%s,"reason":"t","partials":null,"strategy":null%s}\n' \
    "$1" "$2" "$3" "$sb" "$sa" "$scope"
}

run() {  # run <task-dir>; sets RC and OUT
  RC=0; OUT=$(python3 "$VALIDATOR" "$1/.wos/VERIFICATION_LOG.jsonl" --check-deletes --cutover-ts "$CUT" 2>&1) || RC=$?
}

# ---------- 1. a file-scope line matching the whole file is clean ----------
T="$WORK/one"; mkdir -p "$T/.wos"
printf '# TASK_STATE\n\n## Current phase\nplanning\n\n## Next step\nwrite the plan\n' > "$T/TASK_STATE.md"
H=$(filesha "$T/TASK_STATE.md")
line 2026-09-23T10:00:00.000Z R1 '## Current phase' null "$H" file > "$T/.wos/VERIFICATION_LOG.jsonl"
run "$T"
check "1. a file-scope digest that matches the file passes (exit 0)" $([[ "$RC" -eq 0 ]]; echo $?)

# ---------- 2. the same line against a changed file is still drift ----------
printf 'an unlogged edit\n' >> "$T/TASK_STATE.md"
run "$T"
check "2. a file changed after its file-scope line is reported (nonzero)" $([[ "$RC" -ne 0 ]]; echo $?)
check "2b. the report says the drift is at file scope" $(grep -q 'at file scope' <<<"$OUT"; echo $?)

# ---------- 3. one run digests the file once for two sections, a later run continues ----------
T="$WORK/three"; mkdir -p "$T/.wos"
printf '# TASK_STATE\n\n## A\nold\n' > "$T/TASK_STATE.md"
H0=$(filesha "$T/TASK_STATE.md")
printf '# TASK_STATE\n\n## A\nnew\n\n## B\nnew\n' > "$T/TASK_STATE.md"
H1=$(filesha "$T/TASK_STATE.md")
printf '# TASK_STATE\n\n## A\nnewer\n\n## B\nnew\n' > "$T/TASK_STATE.md"
H2=$(filesha "$T/TASK_STATE.md")
{
  line 2026-09-23T10:00:00.000Z R1 '## A' "$H0" "$H1" file
  line 2026-09-23T10:00:00.000Z R1 '## B' "$H0" "$H1" file
  line 2026-09-23T11:00:00.000Z R2 '## A' "$H1" "$H2" file
} > "$T/.wos/VERIFICATION_LOG.jsonl"
run "$T"
check "3. a shared per-run file digest and a continuing later run pass (exit 0)" $([[ "$RC" -eq 0 ]]; echo $?)

# ---------- 4. a later run that does not start where the last one ended breaks ----------
T="$WORK/four"; mkdir -p "$T/.wos"
cp "$WORK/three/TASK_STATE.md" "$T/TASK_STATE.md"
{
  line 2026-09-23T10:00:00.000Z R1 '## A' "$H0" "$H1" file
  line 2026-09-23T11:00:00.000Z R2 '## B' "$H0" "$H2" file
} > "$T/.wos/VERIFICATION_LOG.jsonl"
run "$T"
check "4. a file-scope chain break across runs is reported (nonzero)" $([[ "$RC" -ne 0 ]]; echo $?)
check "4b. it is reported as a chain break" $(grep -q 'sha-chain break' <<<"$OUT"; echo $?)

# ---------- 5. a section-scope write after a file-scope one: no false drift ----------
# The section write moves the file's bytes, so the earlier file digest has nothing left to be
# compared with; the section write itself is still checked at section scope.
T="$WORK/five"; mkdir -p "$T/.wos"
printf '# TASK_STATE\n\n## A\nfirst\n\n## B\nbody b\n' > "$T/TASK_STATE.md"
HA=$(filesha "$T/TASK_STATE.md")
printf '# TASK_STATE\n\n## A\nfirst\n\n## B\nbody b2\n' > "$T/TASK_STATE.md"
SB2=$(printf 'body b2' | shasum -a 256 | awk '{print $1}')
{
  line 2026-09-23T10:00:00.000Z R1 '## A' null "$HA" file
  line 2026-09-23T11:00:00.000Z R2 '## B' null "$SB2" -
} > "$T/.wos/VERIFICATION_LOG.jsonl"
run "$T"
check "5. a section write after a file-scope write raises no false drift (exit 0)" $([[ "$RC" -eq 0 ]]; echo $?)
printf 'tampered\n' >> "$T/TASK_STATE.md"
run "$T"
check "5b. the section write is still held to its own digest (nonzero after tampering)" $([[ "$RC" -ne 0 ]]; echo $?)

# ---------- 6. an unknown scope is an error, not a silent default ----------
T="$WORK/six"; mkdir -p "$T/.wos"
printf '# TASK_STATE\n\n## A\nx\n' > "$T/TASK_STATE.md"
line 2026-09-23T10:00:00.000Z R1 '## A' null "$(filesha "$T/TASK_STATE.md")" project > "$T/.wos/VERIFICATION_LOG.jsonl"
run "$T"
check "6. sha_scope outside {section, file} is rejected" $([[ "$RC" -ne 0 ]] && grep -q 'sha_scope' <<<"$OUT"; echo $?)

# ---------- 7. an empty log is NOT CHECKED, exit 2 ----------
T="$WORK/seven"; mkdir -p "$T/.wos"; : > "$T/.wos/VERIFICATION_LOG.jsonl"
run "$T"
check "7. an empty log exits 2, not 0" $([[ "$RC" -eq 2 ]]; echo $?)
check "7b. an empty log says NOT CHECKED and never OK" $(grep -q 'NOT CHECKED: log has no lines' <<<"$OUT" && ! grep -qx 'OK' <<<"$OUT"; echo $?)

# ---------- 8. --task resolves from the directory it is run in ----------
# An installed copy sits in a docs directory with no projects/ beside it. Copied there, it
# must still find the task under the caller's working directory.
INST="$WORK/installed/scripts"; mkdir -p "$INST"; cp "$VALIDATOR" "$INST/"
TR="$WORK/taskrepo/projects/acme__demo/active/2026-09-23_demo"; mkdir -p "$TR/.wos"
printf '# TASK_STATE\n\n## A\nx\n' > "$TR/TASK_STATE.md"
line 2026-09-23T10:00:00.000Z R1 '## A' null "$(filesha "$TR/TASK_STATE.md")" file > "$TR/.wos/VERIFICATION_LOG.jsonl"
RC=0; OUT=$(cd "$WORK/taskrepo" && python3 "$INST/verify-log-validator.py" --task 2026-09-23_demo 2>&1) || RC=$?
check "8. an installed copy resolves --task under the working directory (exit 0)" $([[ "$RC" -eq 0 ]] && grep -q 'lines: 1' <<<"$OUT"; echo $?)

echo "----"
echo "pass=$PASS fail=$FAIL"
[[ "$FAIL" -eq 0 ]]
