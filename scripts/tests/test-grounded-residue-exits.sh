#!/usr/bin/env bash
# test-grounded-residue-exits.sh: the shape of a question-asking command's exit.
#
# Six commands used to stop and wait for a person. They now loop on a typed
# residue set and leave through exactly one of five labelled exits. Two things
# about that are load-bearing and neither is visible from a green build:
#
#   1. NO_PROGRESS and BUDGET are NOT stops. They are the exits that fire when
#      the loop has nothing left to try, and the whole point of the rework is
#      that they continue the chain with the residue recorded. A future edit that
#      turns either into a halt reinstates the defect this task removed, and it
#      would read as a reasonable edit.
#   2. No exit may gate on self-reported confidence. ADR-0109 D-2 forbids a
#      confidence field, a numeric threshold and a self-assessment prompt
#      anywhere in the doctrine's source surfaces, and a loop that terminates on
#      "am I sure enough yet" is exactly the shape it forbids. This suite carries
#      the same pattern check-claim-grounding.sh uses, applied to the block and
#      to every command that consumes it, so the two agree by construction.
#
# ADR-0233 added a third: in an attended chain on a task branch, ESCALATED
# stops only for reason 1. A product decision becomes a provisional P-N and the
# chain continues, a named deliverable is never de-scoped provisionally, and
# unattended runs keep their never-self-lock rule. Checks 11 to 15 pin that.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BLOCK="${REPO}/commands/_shared/grounded-residue-termination.md"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

# Same pattern as scripts/check-claim-grounding.sh: assignment-shaped only, so
# the doctrine's own forbidding sentences do not match themselves.
CONF_PATTERN='confidence[ _-]?(field|score|level|threshold)?[ ]*[:=][ ]*("?(high|medium|low)"?|[0-9]|0\.[0-9]|[0-9]+%)'
# The Portuguese brief that started this task asked for a loop running to
# "confianca de 5/5". The loop was built; the scoring was deliberately not.
SCORE_PATTERN='[0-9][ ]*(/|de|out of)[ ]*5[ ]*(confidence|confianc)'

[ -f "$BLOCK" ] || { echo "  FAIL shared block not found at $BLOCK"; exit 1; }

# --- the five exits ---------------------------------------------------------
missing=""
for e in RESOLVED NO_PROGRESS BUDGET ESCALATED ENVIRONMENT; do
  grep -q "^[ ]*-[ ]*${e}\." "$BLOCK" || missing="$missing $e"
done
[ -z "$missing" ] && pass "1. all five exits are declared in the shared block" \
                  || fail "1. exits not declared:$missing"

extra="$(grep -oE '^[ ]*-[ ]*[A-Z][A-Z_]{3,}\.' "$BLOCK" | tr -d ' -.' | sort -u \
         | grep -vxE 'RESOLVED|NO_PROGRESS|BUDGET|ESCALATED|ENVIRONMENT' || true)"
[ -z "$extra" ] && pass "2. no sixth exit has been added" \
                || fail "2. undeclared exit label(s): $(printf '%s' "$extra" | tr '\n' ' ')"

# --- the two exits that must not become stops -------------------------------
for e in NO_PROGRESS BUDGET; do
  line="$(grep -E "^[ ]*-[ ]*${e}\." "$BLOCK" | head -1)"
  if printf '%s' "$line" | grep -q 'not a stop'; then
    pass "3. ${e} still declares itself not a stop"
  else
    fail "3. ${e} no longer says it is not a stop; the loop may halt there again"
  fi
done

grep -q 'ESCALATED' "$BLOCK" && grep -qE 'four reasons a chain stops|four reasons' "$BLOCK" \
  && pass "4. ESCALATED routes through the four canonical stop reasons" \
  || fail "4. ESCALATED no longer names the four stop reasons"

# --- propagation to every consumer -----------------------------------------
consumers="$(grep -ln 'grounded-residue-termination' "${REPO}"/commands/*.md | sed 's#.*/##' | sort)"
n="$(printf '%s\n' "$consumers" | grep -c . )"
[ "$n" -ge 6 ] && pass "5. the block reaches $n question-asking commands" \
               || fail "5. only $n consumer(s) carry the block, expected at least 6"

incomplete=""
for c in $consumers; do
  grep -q 'NO_PROGRESS' "${REPO}/commands/$c" || incomplete="$incomplete $c"
done
[ -z "$incomplete" ] && pass "6. every consumer carries the propagated exit set" \
                     || fail "6. consumer(s) missing the exit set:$incomplete"

# --- no confidence gate anywhere -------------------------------------------
hits=""
for f in "$BLOCK" $(printf '%s\n' "$consumers" | sed "s#^#${REPO}/commands/#"); do
  grep -qiE "$CONF_PATTERN" "$f" && hits="$hits $(basename "$f")"
  grep -qiE "$SCORE_PATTERN" "$f" && hits="$hits $(basename "$f"):score"
done
[ -z "$hits" ] && pass "7. no confidence field or n/5 score in the block or its consumers" \
               || fail "7. confidence-shaped gate found in:$hits"

# --- mutation: the confidence check must bite -------------------------------
cp "$BLOCK" "$TMP/mutated.md"
printf '\n- Continue until confidence: high.\n' >> "$TMP/mutated.md"
grep -qiE "$CONF_PATTERN" "$TMP/mutated.md" \
  && pass "8. mutation: an injected confidence field is detected" \
  || fail "8. mutation did not bite; the pattern is blind to a real violation"

cp "$BLOCK" "$TMP/scored.md"
printf '\n- Loop until 5/5 confidence is reached.\n' >> "$TMP/scored.md"
grep -qiE "$SCORE_PATTERN" "$TMP/scored.md" \
  && pass "9. mutation: an injected n/5 score is detected" \
  || fail "9. score mutation did not bite"

cp "$BLOCK" "$TMP/halted.md"
python3 - "$TMP/halted.md" <<'PY'
import sys,io,re
p=sys.argv[1]; s=io.open(p,encoding='utf-8').read()
s=re.sub(r'(- BUDGET\..*?)This is not a stop either\.', r'\1Stop and wait.', s, count=1, flags=re.S)
io.open(p,'w',encoding='utf-8').write(s)
PY
if grep -E '^[ ]*-[ ]*BUDGET\.' "$TMP/halted.md" | grep -q 'not a stop'; then
  fail "10. mutation did not bite; BUDGET could become a halt unnoticed"
else
  pass "10. mutation: BUDGET turned into a halt is detected"
fi

# --- the attended chain records instead of stopping (ADR-0233) -------------
DI="${REPO}/commands/decision-interview.md"
attended_ok() { grep -q 'only reason 1 stops' "$1" && grep -q 'Provisional decisions' "$1"; }
attended_ok "$BLOCK" \
  && pass "11. ESCALATED in an attended chain stops only for reason 1 and records a P-N" \
  || fail "11. the attended-chain rule under ESCALATED is gone; a product decision may stop the chain again"

grep -q 'SHALL NOT be recorded as a provisional de-scope' "$BLOCK" \
  && pass "12. a named deliverable is never de-scoped provisionally" \
  || fail "12. the no-provisional-de-scope rule is missing from the block"

grep -q 'never self-locks' "$BLOCK" \
  && pass "13. unattended runs still never self-lock" \
  || fail "13. the unattended never-self-lock rule is missing from the block"

if grep -q 'Provisional mode' "$DI" && grep -q 'Status: provisional' "$DI" \
   && grep -q 'Confirms: P-N' "$DI"; then
  pass "14. decision-interview defines the provisional mode and its promotion"
else
  fail "14. decision-interview lacks the provisional mode, its status line, or Confirms: P-N"
fi

sed 's/only reason 1 stops/all four reasons stop/' "$BLOCK" > "$TMP/stopped.md"
if attended_ok "$TMP/stopped.md"; then
  fail "15. mutation did not bite; the attended chain could stop on a product decision unnoticed"
else
  pass "15. mutation: an attended chain stopping on every reason is detected"
fi

echo
echo "grounded-residue-exits: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
