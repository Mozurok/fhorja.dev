#!/usr/bin/env bash
# test-skill-in-profile.sh: skill_in_profile() reads BOTH shapes of x-wos-profiles,
# and advertise_chars() sums what a mirrored set costs to advertise.
#
# The old block sequence is what is on disk today; the quoted scalar is what E4.1b
# writes, because the Agent Skills spec fixed metadata as a map from string keys to
# STRING values on 2026-08-03. This test lands with the parser and BEFORE the
# flattening, so no ordering of the two can leave `--profile=minimal` copying zero
# skills in silence.
#
# The substring case is the one worth staring at: a permissive parser matches `core`
# inside `hardcore`, which would silently widen every profile. Comparison is per item
# after the split, and check 8 proves it.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC="${SCRIPT_DIR}/../sync-workflow-slash-commands.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Load the function alone: the script's top level parses flags and would run a sync.
eval "$(sed -n '/^skill_in_profile()/,/^}$/p' "$SYNC")"
eval "$(sed -n '/^advertise_chars()/,/^}$/p' "$SYNC")"

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

make_skill() {  # make_skill <name> <profiles-yaml-fragment>; echoes the dir
  local d="$TMP/$1"; mkdir -p "$d"
  { echo "---"; echo "name: $1"; echo "metadata:"; printf '%s\n' "$2"; echo "  provenance: first-party"; echo "---"; echo "body"; } > "$d/SKILL.md"
  echo "$d"
}

expect() {  # expect <dir> <profile> <0|1> <label>
  skill_in_profile "$1" "$2"; local rc=$?
  [ "$rc" = "$3" ] && pass "$4" || fail "$4 (exit $rc, expected $3)"
}

OLD="$(make_skill old "$(printf '  x-wos-profiles:\n    - minimal\n    - core\n    - full')")"
NEW="$(make_skill new '  x-wos-profiles: "minimal, core, full"')"
NARROW="$(make_skill narrow '  x-wos-profiles: "core, full"')"
EMPTY="$(make_skill empty '  x-wos-profiles: ""')"
ABSENT="$(make_skill absent '  provenance-note: none')"
TRICK="$(make_skill trick '  x-wos-profiles: "hardcore, fullstack"')"

# 1-2. old block shape still resolves, which is what is on disk today.
expect "$OLD" minimal 0 "old block shape matches minimal"
expect "$OLD" core 0 "old block shape matches core"
# 3-4. new scalar shape resolves identically.
expect "$NEW" minimal 0 "new scalar shape matches minimal"
expect "$NEW" core 0 "new scalar shape matches core"
# 5. a narrower scalar refuses a profile it does not list.
expect "$NARROW" minimal 1 "new scalar without minimal does not match minimal"
# 6. an empty scalar matches nothing: it is a declaration of no profiles, not a wildcard.
expect "$EMPTY" minimal 1 "empty scalar matches nothing"
# 7. a file without the key matches nothing.
expect "$ABSENT" minimal 1 "absent key matches nothing"
# 8. THE substring trap: `core` must not match inside `hardcore`, nor `full` in `fullstack`.
expect "$TRICK" core 1 "core does not match inside hardcore"
expect "$TRICK" full 1 "full does not match inside fullstack"
# 9. an empty requested profile means unfiltered, which is the D-4 bare-invocation path.
expect "$NARROW" "" 0 "empty requested profile is unfiltered"

# ---------------------------------------------------------------------------
# advertise_chars(): the number the end-of-run summary reports.
#
# Every skill in this repository carries a MULTI-LINE description, so check 11 is
# the one that matters: a parser that reads only the first line undercounts the
# real total by most of it and the summary understates the cost it exists to show.
# ---------------------------------------------------------------------------

make_desc() {  # make_desc <name> <profiles-scalar> <description-block>; echoes the dir
  local d="$TMP/adv_$1"; mkdir -p "$d"
  { echo "---"; echo "name: $1"; printf '%s\n' "$3"
    echo "metadata:"; echo "  x-wos-profiles: \"$2\""; echo "---"; echo "body"; } > "$d/SKILL.md"
  echo "$d"
}

ADV="$TMP/advdir"; mkdir -p "$ADV"
# one-line description, 10 chars of value
mkdir -p "$ADV/one"; { echo "---"; echo "name: one"; echo "description: 0123456789";
  echo "metadata:"; echo "  x-wos-profiles: \"minimal, full\""; echo "---"; } > "$ADV/one/SKILL.md"
# multi-line: 5 + 1 joining space + 4 = 10 chars
mkdir -p "$ADV/many"; { echo "---"; echo "name: many"; echo "description: AAAAA";
  echo "  BBBB"; echo "metadata:"; echo "  x-wos-profiles: \"full\""; echo "---"; } > "$ADV/many/SKILL.md"

n="$(advertise_chars "$ADV" minimal)"
[ "$n" = "10" ] && pass "advertise_chars counts a one-line description (10)" \
                || fail "advertise_chars one-line: got $n, expected 10"
n="$(advertise_chars "$ADV" full)"
[ "$n" = "20" ] && pass "advertise_chars joins continuation lines (10 + 10 = 20)" \
                || fail "advertise_chars multi-line: got $n, expected 20"
n="$(advertise_chars "$ADV" "")"
[ "$n" = "20" ] && pass "an empty profile counts every skill" \
                || fail "advertise_chars unfiltered: got $n, expected 20"
n="$(advertise_chars "$ADV" nosuch)"
[ "$n" = "0" ] && pass "a profile no skill declares counts nothing" \
               || fail "advertise_chars unknown profile: got $n, expected 0"

# The real corpus, as a tolerance and never an equality: descriptions get edited,
# and a build that fails on an ordinary wording change teaches people to ignore it.
# 72596 chars measured 2026-09-03 across 98 skills; 20 per cent either way still
# catches a parser that silently drops the continuation lines, which is the failure
# this guards.
REAL_SRC="${SCRIPT_DIR}/../../.claude/skills"
if [ -d "$REAL_SRC" ]; then
  n="$(advertise_chars "$REAL_SRC" "")"
  if [ "$n" -ge 58000 ] && [ "$n" -le 87000 ]; then
    pass "the real corpus lands in the measured band ($n chars)"
  else
    fail "the real corpus is outside the band: $n chars, expected 58000 to 87000"
  fi
else
  pass "real corpus not present, skipped (installed tree without .claude/skills)"
fi

echo
if [ "$fails" -eq 0 ]; then echo "test-skill-in-profile: all $checks checks passed"; exit 0
else echo "test-skill-in-profile: $fails of $checks check(s) FAILED"; exit 1; fi
