#!/usr/bin/env bash
# test-scan-substrate-orphans.sh: the orphan gate six fleet commands key their apply step on
# finds orphans, passes a clean file, and never passes a path it did not read. Added
# 2026-09-22, when a named file that did not exist was found printing OK with exit 0.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCAN="${SCRIPT_DIR}/../scan-substrate-orphans.py"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

printf '# T\n\n## Current phase\n- implementation\n' > "$TMP/clean.md"
python3 "$SCAN" "$TMP/clean.md" >/dev/null 2>&1; rc=$?
[ "$rc" = "0" ] && pass "1. a file with every bullet under a heading passes" || fail "1. clean file passes (rc=$rc)"

printf '# T\n- orphan before any section\n\n## Current phase\n- ok\n' > "$TMP/orphan.md"
out="$(python3 "$SCAN" "$TMP/orphan.md" 2>&1)"; rc=$?
[ "$rc" = "1" ] && [[ "$out" == *"orphan"* ]] && pass "2. an orphan bullet exits 1 and is reported" \
  || fail "2. an orphan bullet exits 1 (rc=$rc)"

err="$(python3 "$SCAN" "$TMP/clean.md" "$TMP/absent.md" 2>&1 >/dev/null)"; rc=$?
[ "$rc" = "2" ] && [[ "$err" == *"absent.md"* ]] && [[ "$err" == *"not scanned"* ]] \
  && pass "3. a named file that does not exist exits 2, named, even beside a clean one" \
  || fail "3. a named absent file exits 2 (rc=$rc)"

mkdir -p "$TMP/emptytask"
python3 "$SCAN" "$TMP/emptytask" >/dev/null 2>&1; rc=$?
[ "$rc" = "2" ] && pass "4. a folder holding none of the substrate files exits 2" \
  || fail "4. an empty task folder exits 2 (rc=$rc)"

mkdir -p "$TMP/task" && cp "$TMP/clean.md" "$TMP/task/TASK_STATE.md"
python3 "$SCAN" "$TMP/task" >/dev/null 2>&1; rc=$?
[ "$rc" = "0" ] && pass "5. a folder missing some substrate files still scans the ones present" \
  || fail "5. a partial task folder scans what is present (rc=$rc)"

echo ""
echo "test-scan-substrate-orphans: ${checks} check(s), ${fails} failure(s)"
[ "$fails" -eq 0 ]
