#!/usr/bin/env bash
# test-scan-substrate-headers.sh -- the header drift guard names a folder it could not scan,
# survives --verbose with drift, and scans a task folder outside any git repository.
# Run from anywhere:  bash scripts/tests/test-scan-substrate-headers.sh
#
# Why this exists (ADR-0224). Three defects, each measured on 2026-09-23 before the script
# joined the install payload:
#   - a folder with no substrate file printed `substrate_header_drift_count: 0` with exit 0,
#     the same line a clean scan prints;
#   - `${#DRIFT_LOG[@]:-0}` is a bad substitution, so --verbose died with exit 1 whenever
#     there was drift to show;
#   - a task folder outside a git repository exited 2, which on an install whose task
#     repository is not a git repository fails the closure integrity floor on every close.
# Checks 6 and 7 isolate the first two defects inside a git repository; checks 1 to 5 run
# outside one. All but check 1 fail on the script before this change (check 1 exited 2 there
# for the other reason). The drift count itself stays informational: exit 0 with drift is the
# documented contract (ADR-0034), pinned by check 5.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCAN="$SCRIPT_DIR/../scan-substrate-headers.sh"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "ok   - $1"; }
fail() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }
check() { if [[ "$2" -eq 0 ]]; then ok "$1"; else fail "$1"; fi }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# A task folder in the canonical shape, outside any git repository.
TASK="$WORK/projects/acme__demo/active/2026-09-23_demo"
mkdir -p "$TASK"

# ---------- 1. no substrate file: not scanned, exit 2 ----------
RC=0; OUT=$(bash "$SCAN" "$TASK" 2>&1) || RC=$?
check "1. a folder with no substrate file exits 2" $([[ "$RC" -eq 2 ]]; echo $?)
check "1b. it prints 'not scanned', never a count of 0" $(grep -q 'substrate_header_drift_count: not scanned' <<<"$OUT" && ! grep -q 'substrate_header_drift_count: 0' <<<"$OUT"; echo $?)

# ---------- 2. outside a git repository, a real folder is scanned ----------
printf '# TASK_STATE\n\n## Current phase\nplanning\n' > "$TASK/TASK_STATE.md"
RC=0; OUT=$(bash "$SCAN" "$TASK" 2>&1) || RC=$?
check "2. a task folder outside git is scanned (exit 0)" $([[ "$RC" -eq 0 ]]; echo $?)
check "2b. and the header-less section is counted" $(grep -q 'substrate_header_drift_count: 1' <<<"$OUT"; echo $?)

# ---------- 3. --verbose with drift does not die ----------
RC=0; OUT=$(bash "$SCAN" "$TASK" --verbose 2>&1) || RC=$?
check "3. --verbose with drift exits 0" $([[ "$RC" -eq 0 ]]; echo $?)
check "3b. and prints the drift detail" $(grep -q 'drift detail (1 sections)' <<<"$OUT" && grep -q '## Current phase' <<<"$OUT"; echo $?)

# ---------- 4. a headed section is not drift ----------
printf '# TASK_STATE\n\n<!-- wos:write owner=task-init section='\''## Current phase'\'' run_id=01Jt ts=2026-09-23T10:00:00.000Z reason=t mode=applied -->\n## Current phase\nplanning\n' > "$TASK/TASK_STATE.md"
RC=0; OUT=$(bash "$SCAN" "$TASK" 2>&1) || RC=$?
check "4. a section with its transaction header scans clean (count 0, exit 0)" $([[ "$RC" -eq 0 ]] && grep -q 'substrate_header_drift_count: 0' <<<"$OUT"; echo $?)

# ---------- 5. drift stays informational ----------
printf '\n## Unheaded\nx\n' >> "$TASK/TASK_STATE.md"
RC=0; OUT=$(bash "$SCAN" "$TASK" 2>&1) || RC=$?
check "5. drift is a count, not an exit code (exit 0 with count 1)" $([[ "$RC" -eq 0 ]] && grep -q 'substrate_header_drift_count: 1' <<<"$OUT"; echo $?)

# ---------- 6-7. the same two defects inside a git repository ----------
# Checks 1 and 3 above run outside git, where the old script exited 2 before reaching either
# defect. These isolate each one where the old script did reach it.
GREPO="$WORK/grepo"
git -c init.defaultBranch=main init -q "$GREPO"
git -C "$GREPO" -c user.email=t@test -c user.name=t commit -q --allow-empty -m init
GTASK="$GREPO/projects/acme__demo/active/2026-09-23_demo"; mkdir -p "$GTASK"
RC=0; OUT=$(bash "$SCAN" "$GTASK" 2>&1) || RC=$?
check "6. in git, a folder with no substrate says not scanned with exit 2 (was: count 0, exit 0)" $([[ "$RC" -eq 2 ]] && grep -q 'not scanned' <<<"$OUT"; echo $?)
printf '# TASK_STATE\n\n## Current phase\nplanning\n' > "$GTASK/TASK_STATE.md"
RC=0; OUT=$(bash "$SCAN" "$GTASK" --verbose 2>&1) || RC=$?
check "7. in git, --verbose with drift exits 0 (was: bad substitution, exit 1)" $([[ "$RC" -eq 0 ]] && ! grep -q 'bad substitution' <<<"$OUT"; echo $?)

echo "----"
echo "pass=$PASS fail=$FAIL"
[[ "$FAIL" -eq 0 ]]
