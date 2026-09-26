#!/usr/bin/env bash
# test-check-plan-coverage.sh: does check-plan-coverage.sh actually bite?
#
# The checker exists because two coverage defects were authored in one turn on
# 2026-09-16 and survived it. A checker written in response to a defect is worth
# exactly as much as its ability to fail, so this suite runs both directions for
# each of the three rules: a clean fixture must pass, and one named mutation per
# rule must make it exit 1.
#
# Check 7 is the one to read. ADR-0206 records that rule 1 is GLOBAL, not
# per-row: the awk builds one `slicetag` set across every slice, so a tagged
# ledger row is satisfied by ANY slice carrying that tag, not by a slice that
# covers that row. The defect that motivated the checker had several slices and
# would have passed it. Check 7 pins that blind spot deliberately: it asserts the
# checker is GREEN on a plan that is wrong. When someone gives a slice an edge to
# the ledger row it covers, check 7 flips to red and says so, which is the point.
# A test that silently agreed with the checker here would inherit its blind spot.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${SCRIPT_DIR}/../check-plan-coverage.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

[ -x "$CHECKER" ] || [ -f "$CHECKER" ] || { echo "  FAIL checker not found at $CHECKER"; exit 1; }

# make_task <slug> <ledger-rows> <decisions> <slices> [provisional]; echoes the folder.
# `provisional` (P-1) is optional and defaults to an empty section: existing
# callers that pass only four arguments still get a `## Provisional decisions`
# H2 with no `### P-N` heading under it, so nprov stays 0 and their behavior
# is unchanged.
make_task() {
  local d="$TMP/projects/acme__demo/active/2026-09-16_$1"
  mkdir -p "$d"
  cat > "$d/TASK_STATE.md" <<EOF
# Task state

## Requested deliverables

$2

## Recommended next step

- Command: implementation-plan
EOF
  cat > "$d/DECISIONS.md" <<EOF
# Decisions

## Locked decisions

$3

## Provisional decisions

${5:-No provisional decisions.}

## Decision history

- 2026-09-16: nothing to revise.
EOF
  cat > "$d/IMPLEMENTATION_PLAN.md" <<EOF
# Implementation plan

## Slices

$4
EOF
  echo "$d"
}

# A slice body with every required field. slice <id> <extra-lines>
slice() {
  printf '### Slice %s (S%s): demo\n\n- Scope: one file\n- Depends-on: none\n- Status: PENDING\n- Work complexity: S\n%s- Exit criteria: WHEN the slice lands THEN the gate SHALL pass\n\n' \
    "$1" "$1" "$2"
}

LEDGER_TAGGED='- Rewrite the handoff prose [user-facing-content]'
DEC_ONE='### D-1: the chain continues

- Decision: it continues.'

COV_OUT=""; COV_CODE=0
run_cov() {  # run_cov <folder> [extra-flag]; sets COV_OUT and COV_CODE
  COV_OUT="$("$CHECKER" "$1" ${2:-} --verbose 2>&1)"
  COV_CODE=$?
}

expect_code() {  # expect_code <folder> <expected> <label> [flag]
  run_cov "$1" "${4:-}"
  if [ "$COV_CODE" = "$2" ]; then pass "$3"; else
    fail "$3 (exit $COV_CODE, expected $2)"; printf '%s\n' "$COV_OUT" | sed 's/^/       | /' | head -8
  fi
}

expect_finding() {  # expect_finding <folder> <category> <label>
  run_cov "$1"
  if printf '%s\n' "$COV_OUT" | grep -q "$2"; then pass "$3"; else
    fail "$3 (no '$2' in output)"; printf '%s\n' "$COV_OUT" | sed 's/^/       | /' | head -8
  fi
}

# --- control ---------------------------------------------------------------
CLEAN="$(make_task clean "$LEDGER_TAGGED" "$DEC_ONE" \
  "$(slice 1 '- Deliverable-tag: user-facing-content
- Decision-ref: D-1
')")"
expect_code "$CLEAN" 0 "1. control: a complete plan passes"

# --- rule 1: deliverable-tag ----------------------------------------------
M1="$(make_task m1 "$LEDGER_TAGGED" "$DEC_ONE" "$(slice 1 '- Decision-ref: D-1
')")"
expect_code    "$M1" 1 "2. mutation: covering slice loses its Deliverable-tag"
expect_finding "$M1" "deliverable-tag" "3. ... and the finding names the rule"

# --- rule 2: decision-coverage --------------------------------------------
M2="$(make_task m2 "$LEDGER_TAGGED" "$DEC_ONE" \
  "$(slice 1 '- Deliverable-tag: user-facing-content
')")"
expect_code    "$M2" 1 "4. mutation: locked decision cited by no slice"
expect_finding "$M2" "decision-coverage" "5. ... and the finding names the rule"

# --- the PROPOSED-heading defect (fixed 2026-09-24) ------------------------
# dec_line() used to count ANY `### D-N` heading as locked, including one
# marked `(PROPOSED, not locked)`: a staged draft, not a decision the
# maintainer locked. The only decision on this plan is such a heading, and no
# slice cites it; before the fix that made rule 2 (and rule 4, since ndec > 0)
# demand a citation for a draft nobody locked. After the fix the heading is
# never counted, so the plan reads as carrying zero locked decisions and
# passes clean.
PROPOSED_HEADING='### D-5 (PROPOSED, not locked): a draft label idea

- Decision: not locked yet; awaiting the maintainer.'
PFIX="$(make_task propfix "$LEDGER_TAGGED" "$PROPOSED_HEADING" \
  "$(slice 1 '- Deliverable-tag: user-facing-content
- Decision-ref: none, because nothing is locked yet
')")"
expect_code "$PFIX" 0 "26. fix: a ### D-N (PROPOSED...) heading is not counted as locked"

# --- rule 3: slice-fields --------------------------------------------------
M3_SLICE='### Slice 1 (S1): demo

- Scope: one file
- Status: PENDING
- Work complexity: S
- Deliverable-tag: user-facing-content
- Decision-ref: D-1
- Exit criteria: WHEN the slice lands THEN the gate SHALL pass
'
M3="$(make_task m3 "$LEDGER_TAGGED" "$DEC_ONE" "$M3_SLICE")"
expect_code "$M3" 1 "6. mutation: a slice drops Depends-on:"

# --- the ADR-0206 blind spot, pinned --------------------------------------
# Slice 1 covers the ledger row and carries no tag. Slice 2 covers nothing and
# carries the tag. Rule 1 is global, so the checker is green on a plan whose
# covering slice is untagged. This is the exact shape of the defect the checker
# was written for. Asserting exit 0 records the gap instead of implying it away.
BLIND="$(make_task blind "$LEDGER_TAGGED" "$DEC_ONE" \
  "$(slice 1 '- Decision-ref: D-1
')$(slice 2 '- Deliverable-tag: user-facing-content
')")"
run_cov "$BLIND"
if [ "$COV_CODE" = "0" ]; then
  pass "7. ADR-0206 blind spot still present: rule 1 is global, not per-row"
else
  fail "7. rule 1 now appears per-row (exit $COV_CODE). If a slice-to-row edge was added, this check and ADR-0206 both need updating."
fi

# --- the 2026-09-16 defect pair, reproduced -------------------------------
# Both defects approve-plan caught that day, in one plan, reported in one run.
PAIR="$(make_task pair "$LEDGER_TAGGED" "$DEC_ONE

### D-2: the second one

- Decision: also live." "$(slice 1 '- Decision-ref: D-1
')")"
run_cov "$PAIR"
n=0
printf '%s\n' "$COV_OUT" | grep -q "deliverable-tag"   && n=$((n + 1))
printf '%s\n' "$COV_OUT" | grep -q "decision-coverage" && n=$((n + 1))
[ "$n" = "2" ] && pass "8. both 2026-09-16 defect shapes reported in one run" \
               || fail "8. expected both categories, got $n"

# --- rule 4 (ADR-0208): the inverse direction ------------------------------
# Rule 2 asks whether every locked decision reached a slice. Rule 4 asks whether
# every slice reached a decision. A slice that authorizes itself is what the
# blinded authorization review would otherwise have to catch by reading, and an
# identifier match is not a job for a language model.
R4A="$(make_task r4a "$LEDGER_TAGGED" "$DEC_ONE" \
  "$(slice 1 '- Deliverable-tag: user-facing-content
- Decision-ref: none
')")"
expect_code    "$R4A" 1 "11. mutation: a slice whose Decision-ref is a bare none"
expect_finding "$R4A" "decision-trace" "12. ... and the finding names the rule"

R4B="$(make_task r4b "$LEDGER_TAGGED" "$DEC_ONE" \
  "$(slice 1 '- Deliverable-tag: user-facing-content
- Decision-ref: none, because this slice only reformats a table
')")"
run_cov "$R4B"
printf '%s\n' "$COV_OUT" | grep -q 'decision-trace' \
  && fail "13. control: a recorded reason for citing none is wrongly flagged" \
  || pass "13. control: a recorded reason for citing none is accepted"

# The rule must be vacuous when the task locks no decisions, or every plan
# written before decisions exist would report a defect nobody can act on.
R4C="$(make_task r4c "$LEDGER_TAGGED" "# Decisions

## Locked decisions

None locked in this task." "$(slice 1 '- Deliverable-tag: user-facing-content
')")"
run_cov "$R4C"
printf '%s\n' "$COV_OUT" | grep -q 'decision-trace' \
  && fail "14. rule 4 fired on a task with no locked decisions" \
  || pass "14. rule 4 is vacuous when the task locks no decisions"

# A slice citing a provisional P-N traces (P-1): it named something, labeled
# provisional rather than authorized, which is the point of a provisional
# decision rather than the self-authorization gap rule 4 exists to catch.
# Slice 1 cites the locked D-1 (so ndec > 0 and rule 4 is live); slice 2 cites
# only P-2 and no D-token, which used to flag before this fix.
PROV_ONE='### P-2: the mechanism to try

Evidence: research file, one line.
Impact: normal. Status: provisional.'
R4P="$(make_task r4p "$LEDGER_TAGGED" "$DEC_ONE" \
  "$(slice 1 '- Deliverable-tag: user-facing-content
- Decision-ref: D-1
')
$(slice 2 '- Decision-ref: rests on provisional P-2
')" "$PROV_ONE")"
run_cov "$R4P"
[ "$COV_CODE" = "0" ] && ! printf '%s\n' "$COV_OUT" | grep -q 'decision-trace' \
  && printf '%s\n' "$COV_OUT" | grep -q '(2 slice(s)' \
  && pass "27. fix: a slice resting on a provisional P-N traces (rule 4 accepts it)" \
  || fail "27. a slice citing only a provisional P-N was flagged: $(printf '%s' "$COV_OUT" | tail -5)"

# A slice citing a P-N that DECISIONS.md does not carry is a dangling citation,
# not a trace (fixed 2026-09-24: any `P-[0-9]+` token used to count). Same shape
# as check 27, but slice 2 cites P-9 while only P-2 exists.
R4D="$(make_task r4d "$LEDGER_TAGGED" "$DEC_ONE" \
  "$(slice 1 '- Deliverable-tag: user-facing-content
- Decision-ref: D-1
')
$(slice 2 '- Decision-ref: rests on provisional P-9
')" "$PROV_ONE")"
run_cov "$R4D"
[ "$COV_CODE" = "1" ] && printf '%s\n' "$COV_OUT" | grep -q 'cites provisional P-9, which DECISIONS.md ## Provisional decisions does not carry' \
  && pass "29. fix: a slice citing a provisional P-N that does not exist is reported as dangling" \
  || fail "29. a dangling P-N citation was accepted: $(printf '%s' "$COV_OUT" | tail -5)"

# A P-N the agent replaced with a later P-N (ADR-0235) is no longer the one to
# cite: plans cite only the newest entry of a replacement chain. P-2 carries
# `Replaces: P-1`; slice 2 still cites P-1, so the checker names the slice, the
# replaced P-1 and the P-2 that replaces it, and exits 1. The control is the
# same plan with slice 2 citing P-2, which passes. The newline between the two
# slice() calls keeps slice 2 its own slice: `$(...)` strips the trailing blank
# lines, so without it the second heading lands on the first slice's last line.
PROV_CHAIN='### P-1: the first reading

Evidence: research file, one line.
Impact: normal. Status: provisional.

### P-2: the corrected reading

Replaces: P-1, because the blinded review found P-1 mislabeled.
Evidence: research file, one line.
Impact: normal. Status: provisional.'
R4R="$(make_task r4r "$LEDGER_TAGGED" "$DEC_ONE" \
  "$(slice 1 '- Deliverable-tag: user-facing-content
- Decision-ref: D-1
')
$(slice 2 '- Decision-ref: rests on provisional P-1
')" "$PROV_CHAIN")"
run_cov "$R4R"
[ "$COV_CODE" = "1" ] && printf '%s\n' "$COV_OUT" | grep -q 'decision-trace: Slice 2 (S2) cites provisional P-1, which P-2 replaces; cite P-2 instead' \
  && pass "30. mutation: a slice citing a provisional P-N that a later P-N replaces is reported with both ids" \
  || fail "30. a citation of a replaced P-N was accepted (exit $COV_CODE): $(printf '%s' "$COV_OUT" | tail -5)"

R4H="$(make_task r4h "$LEDGER_TAGGED" "$DEC_ONE" \
  "$(slice 1 '- Deliverable-tag: user-facing-content
- Decision-ref: D-1
')
$(slice 2 '- Decision-ref: rests on provisional P-2
')" "$PROV_CHAIN")"
run_cov "$R4H"
[ "$COV_CODE" = "0" ] && ! printf '%s\n' "$COV_OUT" | grep -q 'decision-trace' \
  && pass "31. control: a slice citing the newest entry of a replacement chain passes" \
  || fail "31. a citation of the chain's newest P-N was flagged (exit $COV_CODE): $(printf '%s' "$COV_OUT" | tail -5)"

# --- advisory tier never fails the build ----------------------------------
out="$("$CHECKER" --all --advisory --root "$TMP" 2>&1)"; code=$?
[ "$code" = "0" ] && pass "9. --all --advisory exits 0 with findings present" \
                  || fail "9. --all --advisory exited $code"
printf '%s\n' "$out" | tail -1 | grep -q '^Plan-coverage:' \
  && pass "10. last line is the Plan-coverage: summary lint parses" \
  || fail "10. last line is not a Plan-coverage: summary"

# --- the scanned tree is the caller's, not the script's (ADR-0224) -------------
# Until 2026-09-23 --all without --root scanned the parent of the script's own directory. An
# installed copy sits in a docs directory with no projects/, so it reported "not measured" for a
# user whose tasks were all in the directory they ran it from. A copy placed outside the fixture
# stands in for the install; the fixture tree is the working directory. The findings name a
# fixture task, so a run that scanned some other tree cannot pass.
INST="$TMP/installed/scripts"; mkdir -p "$INST"; cp "$CHECKER" "$INST/check-plan-coverage.sh"
out="$(cd "$TMP" && bash "$INST/check-plan-coverage.sh" --all 2>&1)"; code=$?
[ "$code" = "1" ] && printf '%s\n' "$out" | grep -q '2026-09-16_m1:' \
  && pass "15. --all without --root scans the working directory's projects/" \
  || fail "15. --all from the fixture tree gave exit $code: $(printf '%s' "$out" | tail -1)"

# --- nothing measured is not clean (ADR-0224) ----------------------------------
NOPLAN="$TMP/projects/acme__demo/active/2026-09-16_noplan"; mkdir -p "$NOPLAN"
printf '# Task state\n' > "$NOPLAN/TASK_STATE.md"
out="$("$CHECKER" "$NOPLAN" 2>&1)"; code=$?
[ "$code" = "2" ] && printf '%s\n' "$out" | grep -q 'not measured' \
  && pass "16. a folder with no plan exits 2 and says not measured, never 0" \
  || fail "16. a folder with no plan gave exit $code: $out"
out="$(cd "$TMP/installed" && bash "$INST/check-plan-coverage.sh" --all 2>&1)"; code=$?
[ "$code" = "2" ] && printf '%s\n' "$out" | grep -q 'not measured' \
  && pass "17. --all over a tree with no projects/ exits 2 (not measured), not 0" \
  || fail "17. --all over an empty tree gave exit $code: $out"
out="$(cd "$TMP/installed" && bash "$INST/check-plan-coverage.sh" --all --advisory 2>&1)"; code=$?
[ "$code" = "0" ] \
  && pass "18. the advisory tier still exits 0 when nothing was measured" \
  || fail "18. --all --advisory over an empty tree exited $code"

# --- rule 5 (ADR-0225): the one-slice route ------------------------------------
# task-init writes the route's single slice and its approval line itself, and no
# reviewer reads the plan. What can be read off the files is asserted here.
ROUTE_SLICE='### Slice 01: add the note
- Scope: `docs/FAQ.md`
- Depends-on: none
- Status: approved
- Work complexity: LOW
- Decision-ref: none (the brief carries every decision)
- Exit criteria: WHEN the slice diff is complete, `check-doc-sync.sh --against HEAD` SHALL exit 0.'
make_route() {  # make_route <slug> <slices> [decisions] [provisional]; echoes the folder
  local d
  d="$(make_task "$1" "- none named" "${3:-None locked in this task.}" "$2" "${4:-}")"
  printf '\n## Approval log\n- 2026-09-23: APPROVED (one-slice route). No blinded review.\n' >> "$d/IMPLEMENTATION_PLAN.md"
  echo "$d"
}

d="$(make_route route-clean "$ROUTE_SLICE")"
run_cov "$d"
[ "$COV_CODE" = "0" ] && pass "19. a route plan with one approved LOW slice naming the renumber check passes" \
  || fail "19. clean route plan refused: $(printf '%s' "$COV_OUT" | tail -3)"

d="$(make_route route-two "$ROUTE_SLICE

${ROUTE_SLICE/Slice 01/Slice 02}")"
run_cov "$d"
[ "$COV_CODE" = "1" ] && printf '%s' "$COV_OUT" | grep -q "one-slice-route: the plan carries the one-slice route and 2 slice(s)" \
  && pass "20. mutation: a second slice under the route line is refused" \
  || fail "20. a two-slice route plan passed: $(printf '%s' "$COV_OUT" | tail -3)"

d="$(make_route route-decision "$ROUTE_SLICE" "$DEC_ONE")"
run_cov "$d"
[ "$COV_CODE" = "1" ] && printf '%s' "$COV_OUT" | grep -q "DECISIONS.md locks 1 decision(s)" \
  && pass "21. mutation: a locked decision under the route line is refused" \
  || fail "21. a route plan with a locked decision passed: $(printf '%s' "$COV_OUT" | tail -3)"

d="$(make_route route-three "${ROUTE_SLICE/\`docs\/FAQ.md\`/\`docs/FAQ.md\`, \`README.md\` and \`docs/MIGRATION.md\`}")"
run_cov "$d"
[ "$COV_CODE" = "1" ] && printf '%s' "$COV_OUT" | grep -q "Scope names 3 paths" \
  && pass "22. mutation: a three-path Scope under the route line is refused" \
  || fail "22. a three-path route scope passed: $(printf '%s' "$COV_OUT" | tail -3)"

d="$(make_route route-nocheck "${ROUTE_SLICE/\`check-doc-sync.sh --against HEAD\`/the docs build}")"
run_cov "$d"
[ "$COV_CODE" = "1" ] && printf '%s' "$COV_OUT" | grep -q "does not name check-doc-sync.sh --against HEAD" \
  && pass "23. mutation: a route slice whose criterion drops the renumber check is refused" \
  || fail "23. a route slice without the renumber check passed: $(printf '%s' "$COV_OUT" | tail -3)"

d="$(make_route route-pending "${ROUTE_SLICE/Status: approved/Status: not-started}")"
run_cov "$d"
[ "$COV_CODE" = "1" ] && printf '%s' "$COV_OUT" | grep -q "Status is not approved" \
  && pass "24. mutation: a route slice not marked approved is refused" \
  || fail "24. an unapproved route slice passed: $(printf '%s' "$COV_OUT" | tail -3)"

# P-7: any provisional decision disqualifies the route the same way a locked
# one does; the route needs the brief to have settled every decision, and a
# provisional P-N is by definition one the brief did not settle.
d="$(make_route route-provisional "$ROUTE_SLICE" "None locked in this task." "$PROV_ONE")"
run_cov "$d"
[ "$COV_CODE" = "1" ] && printf '%s' "$COV_OUT" | grep -q "DECISIONS.md carries 1 provisional decision(s)" \
  && pass "28. mutation: a provisional decision under the route line is refused" \
  || fail "28. a route plan with a provisional decision passed: $(printf '%s' "$COV_OUT" | tail -3)"

# Control: the same two slices with NO route line are an ordinary plan, and rule 5 is silent.
d="$(make_task route-none "- none named" "None locked in this task." "$ROUTE_SLICE

${ROUTE_SLICE/Slice 01/Slice 02}")"
run_cov "$d"
[ "$COV_CODE" = "0" ] && pass "25. control: without a route line, rule 5 reads nothing" \
  || fail "25. rule 5 fired on a plan with no route line: $(printf '%s' "$COV_OUT" | tail -3)"

echo
echo "check-plan-coverage: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
