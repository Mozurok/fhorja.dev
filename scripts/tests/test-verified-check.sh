#!/usr/bin/env bash
# test-verified-check.sh: the helper that refuses to print PASS for a check that
# cannot fail must itself be unable to print PASS for a check that cannot fail.
#
# Every check below asserts a REFUSAL as well as a pass, because a suite that only
# proves the happy path is the exact defect this helper exists to stop.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VC="${REPO}/scripts/verified-check.sh"
checks=0; fails=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); fails=$((fails+1)); echo "  FAIL $1"; }
[ -x "$VC" ] || { echo "  FAIL $VC is not executable"; exit 1; }

run() { "$VC" "$@" >/dev/null 2>&1; echo $?; }

[ "$(run t --good true --bad false)" = "0" ] \
  && pass "1. both directions behave: exit 0" || fail "1. a valid pair did not pass"

[ "$(run t --good true --bad true)" = "1" ] \
  && pass "2. a bad case that PASSES is refused" || fail "2. a check that cannot fail was accepted"

[ "$(run t --good false --bad false)" = "1" ] \
  && pass "3. a good case that FAILS is refused" || fail "3. a broken good case was accepted"

[ "$(run t --good true)" = "1" ] \
  && pass "4. a missing --bad case is refused, not silently one-sided" || fail "4. one-sided run accepted"

[ "$(run "" --good true --bad false)" = "2" ] \
  && pass "5. a missing label exits 2, distinct from a refusal" || fail "5. missing label not distinguished"

[ "$(run t --good true --bad "echo wrong-reason; false" --bad-expect "the-stated-reason")" = "1" ] \
  && pass "6. a bad case failing for the WRONG reason is refused" || fail "6. wrong-reason failure accepted"

[ "$(run t --good true --bad "echo the-stated-reason; false" --bad-expect "the-stated-reason")" = "0" ] \
  && pass "7. a bad case failing for the stated reason passes" || fail "7. right-reason failure refused"

# Both exit codes must be VISIBLE, not merely computed. A helper that decided
# correctly and printed nothing would leave the author with no evidence to paste.
out="$("$VC" t --good true --bad false 2>&1)"
printf '%s' "$out" | grep -qE 'good exit=0 +bad exit=1' \
  && pass "8. both exit codes are printed" || fail "8. exit codes are not in the output"

# Control: the assertion in check 8 must be able to fail.
out2="$("$VC" t --good true --bad true 2>&1)"
printf '%s' "$out2" | grep -qE 'good exit=0 +bad exit=1' \
  && fail "9. control: check 8's pattern matched a run where it should not have" \
  || pass "9. control: check 8's pattern does not match every run"

# The helper must work on a real repository check, not only on true/false.
COV="${REPO}/scripts/check-plan-coverage.sh"
if [ -x "$COV" ]; then
  [ "$(run "real checker" --good "'$COV' --help >/dev/null 2>&1 || true" --bad "'$COV' /nonexistent-task-folder")" = "0" ] \
    && pass "10. works against a real repository checker" || fail "10. real checker pair did not behave"
else
  pass "10. skipped: check-plan-coverage.sh absent"
fi

echo
echo "verified-check: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
