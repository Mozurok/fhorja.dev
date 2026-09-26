#!/usr/bin/env bash
# test-skill-frontmatter-spec.sh: the generated skill frontmatter stays inside the
# Agent Skills spec, and `allowed-tools` stays OUT of it deliberately.
#
# Spec read 2026-09-17 from https://agentskills.io/specification, HTTP 200.
# Defined fields: name (required), description (required), license, compatibility,
# metadata, allowed-tools. `metadata` is "a map from string keys to string values"
# for "additional properties not defined by the Agent Skills spec".
#
# WHY allowed-tools IS ABSENT ON PURPOSE, pinned here so a future reader does not
# "fix" it. The spec defines it as "a space-separated string of tools that are
# PRE-APPROVED to run", and marks it Experimental with support varying between
# implementations. It is a permission grant, not a declaration of what a skill uses.
# Fhorja's `metadata.tools` is the second thing: documentation of what the command
# needs. Migrating one into the other across 98 skills would silently pre-approve
# Bash for the whole catalogue, which is a permission escalation wearing the costume
# of spec compliance. If that trade is ever wanted it is the maintainer's call and it
# needs an ADR, not a sweep.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SKILLS="${REPO}/.claude/skills"
checks=0; fails=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); fails=$((fails+1)); echo "  FAIL $1"; }
[ -d "$SKILLS" ] || { echo "  FAIL no generated skills at $SKILLS"; exit 1; }

n="$(ls -d "$SKILLS"/*/ 2>/dev/null | wc -l | tr -d ' ')"
[ "$n" -gt 0 ] && pass "1. $n generated skill(s) present" || fail "1. no generated skills"

hits="$(grep -l '^allowed-tools:' "$SKILLS"/*/SKILL.md 2>/dev/null || true)"
[ -z "$hits" ] \
  && pass "2. no generated skill grants allowed-tools (a permission grant, not a declaration)" \
  || fail "2. allowed-tools appeared in: $(printf '%s' "$hits" | head -1)"

# metadata values must be STRINGS. A YAML list here is off-spec even though it reads
# naturally, and the build script converts the command's list form into a string.
listy="$(grep -h -A20 '^metadata:' "$SKILLS"/*/SKILL.md 2>/dev/null | grep -E '^  [a-z-]+: \[' || true)"
[ -z "$listy" ] \
  && pass "3. every metadata value is a string, not a YAML list" \
  || fail "3. a metadata value is a list: $(printf '%s' "$listy" | head -1)"

# Control on check 3: the source commands DO use the list form, so check 3 is
# measuring the build's conversion rather than a property both sides share.
srclist="$(grep -h -A20 '^metadata:' "${REPO}"/commands/*.md 2>/dev/null | grep -cE '^  [a-z-]+: \[' || true)"
[ "${srclist:-0}" -gt 0 ] \
  && pass "4. control: the source commands use the list form ($srclist), so check 3 measures the conversion" \
  || fail "4. control: no source command uses the list form, so check 3 proves nothing"

# The two required fields, on every skill.
missing=0
for f in "$SKILLS"/*/SKILL.md; do
  grep -q '^name:' "$f" && grep -q '^description:' "$f" || missing=$((missing+1))
done
[ "$missing" -eq 0 ] && pass "5. every skill carries the two required fields" \
  || fail "5. $missing skill(s) missing name or description"

# name must match the parent directory, per the spec.
bad=0
for d in "$SKILLS"/*/; do
  b="$(basename "$d")"
  grep -q "^name: ${b}\$" "${d}SKILL.md" || bad=$((bad+1))
done
[ "$bad" -eq 0 ] && pass "6. every name matches its parent directory" || fail "6. $bad name/dir mismatch(es)"

# --- B11: the host's combined re-attachment budget --------------------------
# Contract quoted from https://code.claude.com/docs/en/skills, 2026-09-17:
# "keeping the first 5,000 tokens of each. Re-attached skills share a combined
# budget of 25,000 tokens." The build models the per-skill cap and nothing modelled
# the combined one, under which whole skills vanish after compaction.
BUD="${REPO}/scripts/check-skill-budget.sh"
if [ -x "$BUD" ]; then
  out="$("$BUD" 2>&1)"; rc=$?
  [ "$rc" -eq 0 ] && pass "7. the budget advisory exits 0" || fail "7. exited $rc; it must never gate"
  printf '%s' "$out" | grep -qE '^Skill-budget: [0-9]+ skill' \
    && pass "8. it reports a skill count" || fail "8. no Skill-budget: line: $out"
  printf '%s' "$out" | grep -qE 'fit the host'"'"'s 25000-token combined budget' \
    && pass "9. it names the combined budget, not only the per-skill cap" \
    || fail "9. the combined budget is not reported"
  # The number that matters must be stable under the chars-per-token estimate, or it
  # is an artefact of the estimate rather than a fact about the catalogue. Measured
  # at both ratios in use here, 4 and 3.6, the answer was 5 to 7 either way.
  n="$(printf '%s' "$out" | grep -oE '[0-9]+ to [0-9]+ fit|[0-9]+ fit' | head -1)"
  [ -n "$n" ] && pass "10. the fit range is reported as a number ($n)" || fail "10. no fit figure"
else
  fail "7. scripts/check-skill-budget.sh is missing"
fi

echo
echo "skill-frontmatter-spec: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
