#!/usr/bin/env bash
# test-review-coverage-record.sh: a verdict must state what it looked at.
#
# The defect this closes is not a wrong answer, it is an UNBOUNDED one. A verdict
# that states findings without stating scope makes a claim about the complement of
# what it checked, and nothing grounds that. Measured 2026-09-17: that is why
# "are you sure?" had no stable answer here. Every re-ask found something real, so
# no earlier round was ever trustworthy, and the loop had no end.
#
# The rule is the one deliverable-reconcile already applies to the deliverable
# ledger, moved to a second object: a de-scope is allowed, silence is not.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HELPER="${REPO}/scripts/compute-task-outcome.py"
CMD="${REPO}/commands/review-hard.md"
checks=0; fails=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); fails=$((fails+1)); echo "  FAIL $1"; }
[ -f "$HELPER" ] || { echo "  FAIL $HELPER missing"; exit 1; }

run() { python3 "$HELPER" --review-coverage 2026-09-17_t --project acme__demo "$@" >/tmp/rcv.$$ 2>&1; echo $?; }
OK=(--units-declared 12 --units-checked 12 --criteria "wos/bug-classes: correctness" --residual "none: every declared file was read" --findings 3)

[ "$(run "${OK[@]}")" = "0" ] && pass "1. a complete record is emitted" || fail "1. a valid record was refused"

python3 "$HELPER" --review-coverage 2026-09-17_t --project acme__demo "${OK[@]}" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d["event"]=="review_coverage" else 1)' \
  && pass "2. the event type is review_coverage" || fail "2. wrong event type"

# THE RULE. Silence is refused, not degraded. Every other mode in this helper turns a
# bad input into a null field and exits 0; this one must not, because a null residual
# reproduces the silence the record exists to forbid.
[ "$(run --units-declared 12 --units-checked 8 --criteria "x" --residual "")" != "0" ] \
  && pass "3. an empty residual is REFUSED" || fail "3. an empty residual was accepted"
[ "$(run --units-declared 12 --units-checked 8 --criteria "x" --residual "   ")" != "0" ] \
  && pass "4. a whitespace-only residual is refused too" || fail "4. whitespace passed as a residual"
grep -q "silence is not" /tmp/rcv.$$ 2>/dev/null \
  && pass "5. the refusal states the rule rather than a bare error" || fail "5. refusal does not state the rule"

# A scope that grew mid-pass was never a declared scope.
[ "$(run --units-declared 5 --units-checked 9 --criteria "x" --residual "none")" != "0" ] \
  && pass "6. checking more units than declared is refused" || fail "6. an over-count was accepted"

# Control on checks 3, 4 and 6: the same call with only the offending field fixed
# must pass, or those checks are rejecting for some unrelated reason.
[ "$(run --units-declared 12 --units-checked 8 --criteria "x" --residual "4 files behind a feature flag not exercised")" = "0" ] \
  && pass "7. control: the same call with a real residual passes" \
  || fail "7. control: it was being refused for an unrelated reason"

# No certainty anywhere in the record (ADR-0109 D-2).
python3 "$HELPER" --review-coverage 2026-09-17_t --project acme__demo "${OK[@]}" \
  | grep -qiE '"(confidence|certainty|sure|likelihood)"' \
  && fail "8. the record carries a certainty field, which ADR-0109 D-2 forbids" \
  || pass "8. no certainty field in the record"

# The command consumes it rather than describing it.
grep -q 'compute-task-outcome.py --review-coverage' "$CMD" \
  && pass "9. review-hard emits the record" || fail "9. review-hard does not emit the record"
grep -q 'PROCESS DEFECT' "$CMD" \
  && pass "10. review-hard names a finding inside declared-clean scope as a process defect" \
  || fail "10. the re-ask contract is not stated"

rm -f /tmp/rcv.$$
echo
echo "review-coverage-record: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
