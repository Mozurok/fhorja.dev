#!/usr/bin/env bash
# test-shipped-helpers-absence.sh -- four helpers that join the install payload name what they
# did not scan instead of reporting clean, and read the tree they are run from.
# Run from anywhere:  bash scripts/tests/test-shipped-helpers-absence.sh
#
# Why this exists (ADR-0224). Measured 2026-09-23, each of these reported a pass on nothing:
#   plan-adherence.py   an empty task folder printed VERDICT: CONFORMANT, exit 0
#   memory-lint.sh      a named folder that does not exist printed "looked under ./projects"
#                       and then "MEMORY-LINT: 0 finding(s)"
#   secret-scan-gate.sh with no gitleaks, trufflehog or rg on PATH it exited 0 with no output
#   portfolio-review.sh read projects/ beside its own file, so an installed copy printed a
#                       board of 0 tasks with exit 0 from any directory
# Measured against the scripts before this change: 10 of 13 fail. The three that pass on both
# (2, 3b, 4b) pin that the fix did not stop a helper working where there IS something to read,
# and that memory-lint stays advisory.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
S="$SCRIPT_DIR/.."
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "ok   - $1"; }
fail() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }
check() { if [[ "$2" -eq 0 ]]; then ok "$1"; else fail "$1"; fi }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
EMPTY="$WORK/empty-task"; mkdir -p "$EMPTY"

# ---------- plan-adherence.py ----------
RC=0; OUT=$(python3 "$S/plan-adherence.py" "$EMPTY" 2>&1) || RC=$?
check "1. plan-adherence: a folder with no plan exits 2" $([[ "$RC" -eq 2 ]]; echo $?)
check "1b. plan-adherence: it says not checked and prints no verdict" $(grep -q 'not checked, no IMPLEMENTATION_PLAN.md' <<<"$OUT" && ! grep -q 'VERDICT' <<<"$OUT"; echo $?)
PLANNED="$WORK/planned"; mkdir -p "$PLANNED"
printf '# Plan\n\n## Slices\n\n### Slice 1: demo\n\n- Status: PENDING\n' > "$PLANNED/IMPLEMENTATION_PLAN.md"
RC=0; OUT=$(python3 "$S/plan-adherence.py" "$PLANNED" 2>&1) || RC=$?
check "2. plan-adherence: a folder with a plan still gets a verdict (exit 0)" $([[ "$RC" -eq 0 ]] && grep -q '^VERDICT:' <<<"$OUT"; echo $?)

# ---------- memory-lint.sh ----------
RC=0; OUT=$(cd "$WORK" && bash "$S/memory-lint.sh" "$WORK/no-such-task" 2>&1) || RC=$?
check "3. memory-lint: a named folder that does not exist is named" $(grep -q 'memory-lint: no such task folder: ' <<<"$OUT"; echo $?)
check "3b. memory-lint: advisory, so it still exits 0" $([[ "$RC" -eq 0 ]]; echo $?)
check "3c. memory-lint: the trailer says not scanned, never 0 findings" $(grep -q '^MEMORY-LINT: not scanned$' <<<"$OUT" && ! grep -q 'finding(s)' <<<"$OUT"; echo $?)
RC=0; OUT=$(cd "$WORK" && WOS_TASKS_ROOT="$WORK/nothing-here" bash "$S/memory-lint.sh" 2>&1) || RC=$?
check "4. memory-lint: no folder found to scan says not scanned" $(grep -q '^MEMORY-LINT: not scanned$' <<<"$OUT"; echo $?)
printf '# TASK_STATE\n' > "$EMPTY/TASK_STATE.md"
RC=0; OUT=$(bash "$S/memory-lint.sh" "$EMPTY" 2>&1) || RC=$?
check "4b. memory-lint: a real folder is still scanned and counted" $(grep -qE '^MEMORY-LINT: [0-9]+ finding\(s\)$' <<<"$OUT"; echo $?)
rm -f "$EMPTY/TASK_STATE.md"

# ---------- secret-scan-gate.sh ----------
# A PATH holding only what the gate itself needs, so no scanner is reachable. Built from the
# running system's own tools, so the check does not depend on what this machine has installed.
SB="$WORK/bin"; mkdir -p "$SB"
for t in mktemp rm grep head; do
  p="$(command -v "$t")" && ln -s "$p" "$SB/$t"
done
BASH_BIN="$(command -v bash)"
SRC="$WORK/src"; mkdir -p "$SRC"; printf 'hello\n' > "$SRC/a.txt"
RC=0; OUT=$(PATH="$SB" "$BASH_BIN" "$S/secret-scan-gate.sh" "$SRC" 2>&1) || RC=$?
check "5. secret-scan-gate: no scanner on PATH exits 3" $([[ "$RC" -eq 3 ]]; echo $?)
check "5b. secret-scan-gate: and says NOT scanned" $(grep -q 'secret-scan-gate: NOT scanned (no gitleaks, trufflehog or rg on PATH)' <<<"$OUT"; echo $?)
if command -v rg >/dev/null 2>&1; then
  ln -s "$(command -v rg)" "$SB/rg"
  RC=0; OUT=$(PATH="$SB" "$BASH_BIN" "$S/secret-scan-gate.sh" "$SRC" 2>&1) || RC=$?
  check "6. secret-scan-gate: an rg pass that finds nothing says it was a coarse pattern scan" $([[ "$RC" -eq 0 ]] && grep -q 'coarse rg pattern scan' <<<"$OUT"; echo $?)
else
  ok "6. skipped: rg is not installed here, so the coarse-scan line cannot be exercised"
fi

# ---------- portfolio-review.sh ----------
# An installed copy, run from a task repository. The board must count that repository's task.
INST="$WORK/installed/scripts"; mkdir -p "$INST"; cp "$S/portfolio-review.sh" "$INST/"
REPO="$WORK/taskrepo"; T="$REPO/projects/acme__demo/active/2026-09-23_demo"; mkdir -p "$T"
printf '# TASK_STATE\n\n## Current phase\n\nimplementation\n\n## Recommended next step\n\n- Command: implement-approved-slice\n' > "$T/TASK_STATE.md"
RC=0; OUT=$(cd "$REPO" && bash "$INST/portfolio-review.sh" --json 2>&1) || RC=$?
check "7. portfolio-review: an installed copy reads the working directory's projects/" $([[ "$RC" -eq 0 ]] && grep -q '2026-09-23_demo' <<<"$OUT"; echo $?)
RC=0; OUT=$(cd "$WORK/installed" && bash "$INST/portfolio-review.sh" 2>&1) || RC=$?
check "8. portfolio-review: a directory with no projects/ is refused with exit 2" $([[ "$RC" -eq 2 ]] && grep -q 'not scanned, no projects/ directory' <<<"$OUT"; echo $?)

echo "----"
echo "pass=$PASS fail=$FAIL"
[[ "$FAIL" -eq 0 ]]
