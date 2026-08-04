#!/usr/bin/env bash
# test-mirror-codenames.sh -- regression pins for the codename gate's matcher.
# Run from anywhere:  bash scripts/tests/test-mirror-codenames.sh
#
# Checks 1 and 2 exist because the same detector leaked twice on 2026-07-29:
#   D-1: `-w` treats `_` as a word character, so a codename embedded in a
#        project slug (client__client-be) never matched and passed the gate.
#   D-7: the scan was case-sensitive, so a codename lowercased inside a slug
#        passed even after D-1 fixed the boundary.
# Check 3 pins the other side: the alnum boundary must still REJECT a longer
# word that merely starts with the token, or the fix trades a leak for noise.
# Check 5 is the fail-OPEN pin: a token carrying a regex metacharacter used to
# reach the ERE unescaped, so `Acme[corp]` compiled as a character class and the
# gate reported clean over a file holding the codename verbatim. That is the
# worst failure a leak guard has, so it is pinned against a literal-text file.
# Checks 6 to 9 pin the per-entry `mode` field: `compound` widens the scan to a
# codename buried in a dotted or underscored machine identifier, and every other
# mode value (unknown, or a sidecar carrying an extra field a newer writer added)
# must fall back to the default boundary rather than silently widening or dying.
# Checks 10 to 13 pin the two sidecar line forms that predate the alias and the
# mode field: a bare `TOKEN` and a `TOKEN|` carrying an empty alias must both read
# as the default mode, so a list written before either field existed keeps its
# behaviour under a script that parses three fields. Each form is pinned in both
# directions, because a dropped entry reports clean exactly like a correctly
# narrow one, and only the detect direction tells them apart.
# Check 14 pins the non-ASCII token, and check 15 the usage exit for an absent
# sidecar, which must stay 2 and never be confused with a clean tree.
#
# Every token here is SYNTHETIC. The real sidecar is gitignored and is never
# read, echoed, or derived from by this file.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATE="$SCRIPT_DIR/../check-mirror-codenames.sh"
fails=0
checks=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); echo "  FAIL $1"; fails=$((fails+1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
LIST="$TMP/codenames"

# The sidecar entry is per-check, not fixed: mode is a field of the entry, so a
# mode-routing check can only be written by varying the entry the gate reads.
run_gate() {  # run_gate <file-content> [sidecar-entry]; echoes exit code
  local body="$1" entry="${2:-Acme|public-alias}" d="$TMP/tree"
  rm -rf "$d"; mkdir -p "$d"
  printf '%s\n' "$body" > "$d/doc.md"
  printf '%s\n' "$entry" > "$LIST"
  MIRROR_CODENAMES_FILE="$LIST" bash "$GATE" "$d" >/dev/null 2>&1
  echo $?
}

run_gate_no_list() {  # run_gate_no_list <file-content>; echoes exit code
  local body="$1" d="$TMP/tree"
  rm -rf "$d"; mkdir -p "$d"
  printf '%s\n' "$body" > "$d/doc.md"
  MIRROR_CODENAMES_FILE="$TMP/absent/codenames" bash "$GATE" "$d" >/dev/null 2>&1
  echo $?
}

# The bundle-id shape reused by the mode checks: the token sits with an
# alphanumeric on its trailing side, so only `compound` can reach it.
BUNDLE_ID_BODY='shipping id com.Acmeeng.Acmelauncher to the store'

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

# 5. FAIL-OPEN pin: a token carrying regex metacharacters, against a file that
#    contains that token as literal text. Unescaped, `Acme[corp]` compiles to a
#    character class that cannot match the literal `[`, and the gate says clean.
rc=$(run_gate 'the bundle Acme[corp] appears verbatim here' 'Acme[corp]|public-alias')
[ "$rc" = "1" ] && pass "metacharacter token matched literally (exit 1)" \
                 || fail "metacharacter token FAILED OPEN (exit $rc, expected 1)"

# 6. compound mode reaches the bundle-id form
rc=$(run_gate "$BUNDLE_ID_BODY" 'Acme|public-alias|compound')
[ "$rc" = "1" ] && pass "compound mode detects bundle-id form (exit 1)" \
                 || fail "compound mode MISSED bundle-id form (exit $rc, expected 1)"

# 7. same file, default mode: proves 6 is the mode doing the work, not the body
rc=$(run_gate "$BUNDLE_ID_BODY")
[ "$rc" = "0" ] && pass "default mode leaves bundle-id form alone (exit 0)" \
                 || fail "default mode widened without compound (exit $rc, expected 0)"

# 8. an unknown mode falls back to the default rather than widening or dying
rc=$(run_gate "$BUNDLE_ID_BODY" 'Acme|public-alias|bogus')
[ "$rc" = "0" ] && pass "unknown mode falls back to default (exit 0)" \
                 || fail "unknown mode not defaulted (exit $rc, expected 0)"

# 9. a field appended after the mode is not a mode: an older checkout reading a
#    sidecar a newer writer extended must default, not half-parse `compound`.
rc=$(run_gate "$BUNDLE_ID_BODY" 'Acme|public-alias|compound|extra')
[ "$rc" = "0" ] && pass "extra field after mode falls back to default (exit 0)" \
                 || fail "extra field after mode not defaulted (exit $rc, expected 0)"

# 10 to 13. The two sidecar line forms that predate the alias and the mode field.
# Each is pinned in BOTH directions on purpose. The negative alone is not a pin: an
# entry the parser drops on the floor also reports clean, so a skipped entry and a
# correctly-defaulted one are the same exit code. The positive is what separates
# them, and it is the direction that carries the leak.
LEGACY_HIT_BODY='see projects/Acme__Acme-be/active/x for detail'

# 10. bare token, no pipe at all: still DETECTS a boundary-bounded occurrence
rc=$(run_gate "$LEGACY_HIT_BODY" 'Acme')
[ "$rc" = "1" ] && pass "bare token entry still detects (exit 1)" \
                 || fail "bare token entry DROPPED (exit $rc, expected 1)"

# 11. bare token: and still does not widen to the compound form
rc=$(run_gate "$BUNDLE_ID_BODY" 'Acme')
[ "$rc" = "0" ] && pass "bare token entry reads as default mode (exit 0)" \
                 || fail "bare token entry widened (exit $rc, expected 0)"

# 12. pipe with an empty alias: the form that puts an empty string where the mode
#     split later had to look for a field. Still detects.
rc=$(run_gate "$LEGACY_HIT_BODY" 'Acme|')
[ "$rc" = "1" ] && pass "empty-alias entry still detects (exit 1)" \
                 || fail "empty-alias entry DROPPED (exit $rc, expected 1)"

# 13. empty alias: and still does not widen to the compound form
rc=$(run_gate "$BUNDLE_ID_BODY" 'Acme|')
[ "$rc" = "0" ] && pass "empty-alias entry reads as default mode (exit 0)" \
                 || fail "empty-alias entry widened (exit $rc, expected 0)"

# 14. a non-ASCII token matches the same accented string (and only it: the
#     unaccented spelling is a different token and is not this check's concern)
rc=$(run_gate 'the roastery Acme-café is listed' 'Acme-café|public-alias')
[ "$rc" = "1" ] && pass "non-ASCII token matches accented string (exit 1)" \
                  || fail "non-ASCII token MISSED accented string (exit $rc, expected 1)"

# 15. no sidecar at all is a usage error, never a clean pass
rc=$(run_gate_no_list 'nothing sensitive here at all')
[ "$rc" = "2" ] && pass "absent sidecar is a usage error (exit 2)" \
                 || fail "absent sidecar not reported (exit $rc, expected 2)"

echo
if [ "$fails" -eq 0 ]; then echo "test-mirror-codenames: all $checks checks passed"; exit 0
else echo "test-mirror-codenames: $fails of $checks check(s) FAILED"; exit 1; fi
