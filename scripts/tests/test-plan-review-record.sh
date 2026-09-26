#!/usr/bin/env bash
# test-plan-review-record.sh: the approval verdict trail (ADR-0208).
#
# This record is not bookkeeping. ADR-0208 accepted the measured 39-percent
# plan-rejection rate and replaced the control rather than disputing it, which
# moves the burden of proof onto the replacement. Nothing inside a session can
# discharge that; sampling these lines across tasks can. A trail that is wrong,
# incomplete, or drifted from its schema cannot be sampled, so the properties
# below are the ones that decide whether the burden is dischargeable at all.
#
# Check 6 is the one that would rot quietly. It asserts the writer and the
# schema agree on the field set, in both directions. A field the helper emits
# and the schema never documents is invisible to a reader; a field the schema
# promises and the helper never writes is a reader looking for something that
# is not there.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HELPER="${REPO}/scripts/compute-task-outcome.py"
SCHEMA="${REPO}/templates/OUTCOMES.schema.md"

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

emit() {  # emit <exit> [extra args...]; echoes the JSON line, or ERROR
  python3 "$HELPER" --plan-review 2026-09-16_fixture --project acme__demo \
    --exit "$1" --rubric "locked-decision authorization" "${@:2}" 2>/dev/null || echo ERROR
}

# --- every exit in the shared set is accepted -------------------------------
SHARED="${REPO}/commands/_shared/grounded-residue-termination.md"
EXITS="$(grep -oE '^   - [A-Z_]+\.' "$SHARED" | tr -d ' -.' | sort -u)"
bad=""
while IFS= read -r e; do
  [ -n "$e" ] || continue
  out="$(emit "$e")"
  printf '%s' "$out" | grep -q "\"exit\": *\"$e\"" || bad="$bad $e"
done <<EOF
$EXITS
EOF
[ -z "$bad" ] && pass "1. every exit the shared block defines is accepted" \
              || fail "1. exit(s) the helper rejected:$bad"

# --- anything outside that set is refused, not recorded ---------------------
out="$(emit APPROVED)"
[ "$out" = "ERROR" ] && pass "2. an exit outside the five is refused, not written" \
                     || fail "2. the helper recorded an invented exit: $(printf '%s' "$out" | cut -c1-70)"

# --- escalated_on is bound to ESCALATED -------------------------------------
out="$(emit ESCALATED --escalated-on "S3 commits to a retry policy D-2 does not authorize")"
printf '%s' "$out" | grep -q 'retry policy' \
  && pass "3. ESCALATED carries what could not be grounded" \
  || fail "3. ESCALATED dropped its residue"

out="$(emit RESOLVED --escalated-on "something")"
if [ "$out" = "ERROR" ]; then
  pass "4. a residue on a non-ESCALATED exit is refused"
else
  v="$(printf '%s' "$out" | python3 -c 'import sys,json; print(json.load(sys.stdin)["escalated_on"])' 2>/dev/null || echo PARSE_ERROR)"
  [ "$v" = "None" ] && pass "4. a residue on a non-ESCALATED exit is dropped to null" \
                    || fail "4. RESOLVED recorded a residue ('$v'); the schema says non-null only on ESCALATED"
fi

# --- no confidence value, anywhere ------------------------------------------
hits=""
while IFS= read -r e; do
  [ -n "$e" ] || continue
  printf '%s' "$(emit "$e")" | grep -qiE 'confidence|certainty|"score"|likelihood' && hits="$hits $e"
done <<EOF
$EXITS
EOF
[ -z "$hits" ] && pass "5. no confidence, certainty or score field on any exit" \
               || fail "5. a confidence-shaped field appeared on:$hits"

# --- the writer and the schema agree, in both directions --------------------
emitted="$(emit RESOLVED | python3 -c 'import sys,json; print("\n".join(sorted(json.load(sys.stdin))))')"
documented="$(awk '/^## Event type: plan_review/,/^## Event type: revert/' "$SCHEMA" \
             | grep -oE '^\| [a-z_]+ \|' | tr -d '| ' | grep -vx field | sort -u)"
undocumented="$(comm -23 <(printf '%s\n' "$emitted") <(printf '%s\n' "$documented"))"
unwritten="$(comm -13 <(printf '%s\n' "$emitted") <(printf '%s\n' "$documented"))"
if [ -z "$undocumented" ] && [ -z "$unwritten" ]; then
  pass "6. the helper's fields and the schema's table agree exactly"
else
  fail "6. writer and schema disagree"
  [ -n "$undocumented" ] && printf '       emitted but undocumented: %s\n' "$(printf '%s' "$undocumented" | tr '\n' ' ')"
  [ -n "$unwritten" ] && printf '       documented but never written: %s\n' "$(printf '%s' "$unwritten" | tr '\n' ' ')"
fi

# --- the schema forbids the field this record must never grow ---------------
awk '/^## Event type: plan_review/,/^## Event type: revert/' "$SCHEMA" \
  | grep -qiE 'no confidence, score, or certainty field' \
  && pass "7. the schema states the prohibition rather than leaving it to habit" \
  || fail "7. the schema does not forbid a confidence field"

echo
echo "plan-review-record: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
