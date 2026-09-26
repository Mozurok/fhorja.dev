#!/usr/bin/env bash
# test-ci-test-list-coverage.sh: the CI test allowlist against the tests on disk.
#
# .github/workflows/lint.yml names each suite explicitly rather than globbing,
# and the comment above the loop says why: adding a suite should be a decision,
# not something a filename pattern does silently. The cost of that choice is a
# silent failure mode. A new scripts/tests/test-*.sh that nobody adds to the list
# never runs, the build is green, and no check notices. Measured 2026-09-16: 19
# listed, 19 on disk, agreeing by hand and by nothing else.
#
# This is the same defect class as a coverage rule with no checker, applied to
# the test suite itself. Both directions are checked: a test on disk that CI does
# not run, and a name CI runs that is not on disk (a rename leaves that behind).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKFLOW="${REPO}/.github/workflows/lint.yml"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

# The two sides of the comparison, each pointable at a fixture so the check can
# be mutated without touching the repository.
declared() { grep -oE '\./scripts/tests/test-[A-Za-z0-9._-]+\.sh' "$1" 2>/dev/null | sed 's#.*/##' | sort -u; }
present()  { find "$1" -maxdepth 1 -name 'test-*.sh' 2>/dev/null -exec basename {} \; | sort -u; }

unlisted() { comm -23 <(present "$2") <(declared "$1"); }   # on disk, CI ignores
dangling() { comm -13 <(present "$2") <(declared "$1"); }   # CI names, absent

[ -f "$WORKFLOW" ] || { echo "  FAIL workflow not found at $WORKFLOW"; exit 1; }

# --- the repository itself --------------------------------------------------
u="$(unlisted "$WORKFLOW" "${REPO}/scripts/tests")"
if [ -z "$u" ]; then pass "1. every test-*.sh on disk is named in the CI loop"; else
  fail "1. test file(s) CI never runs:"; printf '%s\n' "$u" | sed 's/^/         /'
fi

d="$(dangling "$WORKFLOW" "${REPO}/scripts/tests")"
if [ -z "$d" ]; then pass "2. every name in the CI loop exists on disk"; else
  fail "2. CI names test file(s) that do not exist:"; printf '%s\n' "$d" | sed 's/^/         /'
fi

n_present="$(present "${REPO}/scripts/tests" | wc -l | tr -d ' ')"
n_declared="$(declared "$WORKFLOW" | wc -l | tr -d ' ')"
[ "$n_present" = "$n_declared" ] \
  && pass "3. counts agree ($n_present on disk, $n_declared in CI)" \
  || fail "3. counts disagree ($n_present on disk, $n_declared in CI)"

# --- mutation: the check must bite -----------------------------------------
mkdir -p "$TMP/tests"
printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP/tests/test-alpha.sh"
printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP/tests/test-beta.sh"
printf 'jobs:\n  run: |\n    for t in \\\n      ./scripts/tests/test-alpha.sh\n    do bash "$t"; done\n' > "$TMP/wf.yml"

mu="$(unlisted "$TMP/wf.yml" "$TMP/tests")"
[ "$mu" = "test-beta.sh" ] \
  && pass "4. mutation: an unlisted test file is detected" \
  || fail "4. mutation did not bite (got '$mu', expected 'test-beta.sh')"

printf 'jobs:\n  run: |\n    for t in \\\n      ./scripts/tests/test-alpha.sh \\\n      ./scripts/tests/test-gamma.sh\n    do bash "$t"; done\n' > "$TMP/wf2.yml"
md="$(dangling "$TMP/wf2.yml" "$TMP/tests")"
printf '%s\n' "$md" | grep -q 'test-gamma.sh' \
  && pass "5. mutation: a CI name with no file is detected" \
  || fail "5. dangling-name mutation did not bite (got '$md')"

# A clean fixture must pass, or check 4 proves nothing.
printf 'jobs:\n  run: |\n    for t in \\\n      ./scripts/tests/test-alpha.sh \\\n      ./scripts/tests/test-beta.sh\n    do bash "$t"; done\n' > "$TMP/wf3.yml"
[ -z "$(unlisted "$TMP/wf3.yml" "$TMP/tests")" ] && [ -z "$(dangling "$TMP/wf3.yml" "$TMP/tests")" ] \
  && pass "6. control: a fixture in agreement reports nothing" \
  || fail "6. control fixture reported a finding"

# --- the loop must still parse ------------------------------------------------
# A name added without its trailing backslash breaks the shell loop, and CI then
# runs none of the suites. Measured 2026-09-23: two integrations left two names
# without a continuation, the list checks above stayed green, and the loop did not
# parse from 33f580a3 to a93791ee. Extract the loop and syntax-check it.
loop_parses() { awk '/for t in/{p=1} p{print} p&&/done/{exit}' "$1" | sed 's/^ *//' | bash -n 2>/dev/null; }
loop_parses "$WORKFLOW" \
  && pass "7. the CI test loop parses as shell" \
  || fail "7. the CI test loop in lint.yml does not parse (a name without its trailing backslash?)"
printf 'jobs:\n  run: |\n    for t in \\\n      ./scripts/tests/test-alpha.sh\n      ./scripts/tests/test-beta.sh\n    do bash "$t"; done\n' > "$TMP/wf4.yml"
loop_parses "$TMP/wf4.yml" \
  && fail "8. mutation did not bite: a missing continuation parsed" \
  || pass "8. mutation: a name without its continuation is detected"
loop_parses "$TMP/wf3.yml" \
  && pass "9. control: a well-formed loop parses" \
  || fail "9. control fixture did not parse"

echo
echo "ci-test-list-coverage: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
