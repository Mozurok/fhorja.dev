#!/usr/bin/env bash
# test-mirror-codenames.sh -- regression pins for the codename gate's matcher.
# Run from anywhere:  bash scripts/tests/test-mirror-codenames.sh
#
# Both pins exist because the same detector leaked twice on 2026-07-29:
#   D-1: `-w` treats `_` as a word character, so a codename embedded in a
#        project slug (client__client-be) never matched and passed the gate.
#   D-7: the scan was case-sensitive, so a codename lowercased inside a slug
#        passed even after D-1 fixed the boundary.
# Check 3 pins the other side: the alnum boundary must still REJECT a longer
# word that merely starts with the token, or the fix trades a leak for noise.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATE="$SCRIPT_DIR/../check-mirror-codenames.sh"
fails=0
pass() { echo "  ok   $1"; }
fail() { echo "  FAIL $1"; fails=$((fails+1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
LIST="$TMP/codenames"
printf 'Acme|public-alias\n' > "$LIST"

run_gate() {  # run_gate <file-content>; echoes exit code
  local body="$1" d="$TMP/tree"
  rm -rf "$d"; mkdir -p "$d"
  printf '%s\n' "$body" > "$d/doc.md"
  MIRROR_CODENAMES_FILE="$LIST" bash "$GATE" "$d" >/dev/null 2>&1
  echo $?
}

# 1. D-1: embedded in a project slug, bounded by underscores
rc=$(run_gate 'see projects/Acme__Acme-be/active/x for detail')
[ "$rc" = "1" ] && pass "D-1 embedded-in-slug detected (exit 1)" \
                 || fail "D-1 embedded-in-slug MISSED (exit $rc, expected 1)"

# 2. D-7: same shape, lowercased
rc=$(run_gate 'see projects/acme__acme-be/active/x for detail')
[ "$rc" = "1" ] && pass "D-7 lowercased-in-slug detected (exit 1)" \
                 || fail "D-7 lowercased-in-slug MISSED (exit $rc, expected 1)"

# 3. the boundary must not flood: a longer word starting with the token
rc=$(run_gate 'the Acmeous compound and acmeism are ordinary words')
[ "$rc" = "0" ] && pass "longer-word false positive rejected (exit 0)" \
                 || fail "longer-word FALSE POSITIVE (exit $rc, expected 0)"

# 4. a clean tree passes
rc=$(run_gate 'nothing sensitive here at all')
[ "$rc" = "0" ] && pass "clean tree passes (exit 0)" \
                 || fail "clean tree rejected (exit $rc, expected 0)"

echo
if [ "$fails" -eq 0 ]; then echo "test-mirror-codenames: all 4 checks passed"; exit 0
else echo "test-mirror-codenames: $fails check(s) FAILED"; exit 1; fi
