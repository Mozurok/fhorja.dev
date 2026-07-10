#!/usr/bin/env bash
# run-tests.sh -- tests for the Fhorja autonomy helpers (ADR-0044, Slice 2).
# Deterministic: no real sleeping; the governor's clock is injected via
# $AUTONOMY_NOW_EPOCH. Run: bash scripts/autonomy/tests/run-tests.sh

set -uo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLASSIFY="$DIR/classify-slice.sh"
GOV="$DIR/governor.sh"
STOP="$DIR/stop-check.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
expect_code() { # <desc> <expected-code> ; reads actual from $?
  local desc="$1" want="$2" got="$3"
  if [[ "$got" == "$want" ]]; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: $desc (want exit $want, got $got)"; fi
}

# --- classify-slice ---
bash "$CLASSIFY" src/app/button.tsx src/lib/util.ts >/dev/null 2>&1; expect_code "plain source -> auto" 0 $?
bash "$CLASSIFY" db/migrations/0007_add_col.sql >/dev/null 2>&1; expect_code "migration -> escalate" 10 $?
bash "$CLASSIFY" src/app/button.test.tsx >/dev/null 2>&1; expect_code "test file -> escalate (D12)" 10 $?
bash "$CLASSIFY" evals/scenarios/56-foo.md >/dev/null 2>&1; expect_code "eval scenario -> escalate (D12)" 10 $?
bash "$CLASSIFY" src/auth/session.ts >/dev/null 2>&1; expect_code "auth path -> escalate (D6)" 10 $?
bash "$CLASSIFY" >/dev/null 2>&1; expect_code "empty set -> escalate (default-deny)" 10 $?
# mixed set with one boundary file must escalate (false-negative direction)
bash "$CLASSIFY" src/ok.ts api/orders.ts >/dev/null 2>&1; expect_code "mixed w/ boundary -> escalate" 10 $?
# malformed: several paths joined into ONE argument must escalate (POC finding 2026-06-16)
bash "$CLASSIFY" "db/schema.sql src/db.js" >/dev/null 2>&1; expect_code "joined-arg hiding boundary -> escalate" 10 $?
bash "$CLASSIFY" "src/a.ts src/b.ts" >/dev/null 2>&1; expect_code "joined-arg (whitespace) -> escalate (malformed)" 10 $?

# --- stop-check ---
bash "$STOP" "$TMP/nope.stop" >/dev/null 2>&1; expect_code "absent STOP -> continue" 0 $?
touch "$TMP/run.stop"
bash "$STOP" "$TMP/run.stop" >/dev/null 2>&1; expect_code "present STOP -> halt" 30 $?

# --- governor: max-iter ---
st="$TMP/gov1"; rm -f "$st"
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 2 --timeout-sec 0 --command a >/dev/null 2>&1; expect_code "gov iter1 continue" 0 $?
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 2 --timeout-sec 0 --command b >/dev/null 2>&1; expect_code "gov iter2 continue" 0 $?
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 2 --timeout-sec 0 --command c >/dev/null 2>&1; expect_code "gov iter3 halt (max-iter)" 20 $?

# --- governor: timeout ---
st="$TMP/gov2"; rm -f "$st"
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 99 --timeout-sec 60 --command x >/dev/null 2>&1; expect_code "gov within timeout" 0 $?
AUTONOMY_NOW_EPOCH=1100 bash "$GOV" "$st" --max-iter 99 --timeout-sec 60 --command y >/dev/null 2>&1; expect_code "gov over timeout halt" 20 $?

# --- governor: identical-command loop ---
st="$TMP/gov3"; rm -f "$st"
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 99 --timeout-sec 0 --command "same" >/dev/null 2>&1; expect_code "loop 1 continue" 0 $?
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 99 --timeout-sec 0 --command "same" >/dev/null 2>&1; expect_code "loop 2 continue" 0 $?
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 99 --timeout-sec 0 --command "same" >/dev/null 2>&1; expect_code "loop 3 halt (identical-command)" 20 $?

echo "----"
echo "autonomy helper tests: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]] || exit 1
