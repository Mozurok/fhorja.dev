#!/usr/bin/env bash
# test-plan-authorization-review.sh: the contract around the blinded approval review.
#
# WHAT THIS CANNOT TEST, said first so the rest is read correctly. A sub-agent's
# judgment is not deterministic and this suite does not pretend to measure it.
# Asserting what the reviewer concluded would produce a flaky suite that everyone
# learns to ignore, which is worse than no suite. Whether the review rejects what
# a person would reject is answered by sampling the `plan_review` records across
# tasks over time, and `TEST_STRATEGY.md` records that as an open gap rather than
# implying a suite closes it.
#
# WHAT IT DOES TEST is the contract the command states, which is deterministic
# and is where every failure mode worth catching lives: that the dispatch is
# isolated, that the exit set is the shared one rather than a private copy, that
# exactly one exit reaches a person, that the Strict surface list has not
# drifted from the two other files carrying it, and (ADR-0233) that the rubric
# keeps `## Locked decisions` as the only authorization while a provisional P-N
# passes labeled, with its evidence checked on the task branch.
#
# Check 2 is worth reading. The five exits are READ from the shared block, never
# spelled here. A test that hardcoded them would keep passing after the block
# changed, which is the drift class it exists to catch.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CMD="${REPO}/commands/approve-plan.md"
SHARED="${REPO}/commands/_shared/grounded-residue-termination.md"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

for f in "$CMD" "$SHARED"; do
  [ -f "$f" ] || { echo "  FAIL missing $f"; exit 1; }
done

# The canonical exit set, read from the block that defines it.
EXITS="$(grep -oE '^   - [A-Z_]+\.' "$SHARED" | tr -d ' -.' | sort -u)"
N_EXITS="$(printf '%s\n' "$EXITS" | grep -c .)"

# audit <command-file>: one finding per line, empty when the contract holds.
audit() {
  local f="$1" out="" e
  # The review block, delimited so a mutation elsewhere in the file is not read as one here.
  local blk
  blk="$(awk '/Blinded authorization review/,/^- When proceeding:/' "$f")"
  [ -n "$blk" ] || { printf 'no blinded-review rule at all'; return; }

  printf '%s' "$blk" | grep -qiE 'artifact path and the rubric and NOTHING else' \
    || out="${out}\n      does not restrict the dispatch to the artifact path and the rubric"
  printf '%s' "$blk" | grep -qiE '[Nn]ever the conversation that produced the plan' \
    || out="${out}\n      does not forbid passing the authoring conversation"

  while IFS= read -r e; do
    [ -n "$e" ] || continue
    printf '%s' "$blk" | grep -q "$e" || out="${out}\n      exit ${e} is not mapped"
  done <<EOF
$EXITS
EOF
  # A sixth label at the same nesting is an exit this command invented.
  local extra
  extra="$(printf '%s' "$blk" | grep -oE '^    - [A-Z][A-Z_]{3,}\.' | tr -d ' -.' | sort -u \
           | grep -vxF "$EXITS" || true)"
  [ -n "$extra" ] && out="${out}\n      exit label(s) outside the shared set: $(printf '%s' "$extra" | tr '\n' ' ')"

  printf '%s' "$blk" | grep -qiE 'ONLY exit that hands back' \
    || out="${out}\n      does not name exactly one exit as the hand-back"
  printf '%s' "$blk" | grep -qiE 'no confidence field' \
    || out="${out}\n      does not forbid gating on self-reported certainty"

  # Provisional decisions (ADR-0233). The agent writes P-N entries, so a rubric
  # that read them as authorization would approve the agent's own choices. The
  # four clauses below are what keeps the review from becoming circular.
  printf '%s' "$blk" | grep -qF '`## Locked decisions` is the only authorization' \
    || out="${out}\n      does not keep Locked decisions as the only authorization"
  printf '%s' "$blk" | grep -qiE 'Provisional decisions`? (is|are|counts? as) (an? |the )?(only )?authori' \
    && out="${out}\n      reads Provisional decisions as authorization"
  printf '%s' "$blk" | grep -qF 'passes only LABELED' \
    && printf '%s' "$blk" | grep -qF 'never counts as authorization' \
    || out="${out}\n      does not pass a provisional P-N labeled and never as authorization"
  printf '%s' "$blk" | grep -qiE 'evidence .*exist on the task branch' \
    || out="${out}\n      does not ask whether each P-N's evidence exists on the task branch"
  printf '%s' "$blk" | grep -qF 'Unattended, background and fleet-dispatched runs keep the hand-back' \
    || out="${out}\n      does not keep the unattended hand-back unchanged"

  # The rubric returns three values and only two are exits. A mapping that names
  # `failed` alone lets `needs_revision` fall through to RESOLVED, which is how
  # the first live run nearly approved a plan carrying the defect the review had
  # just found. All three must appear.
  local v
  for v in satisfied needs_revision failed; do
    printf '%s' "$blk" | grep -q "$v" || out="${out}\n      rubric value ${v} is unmapped"
  done

  printf '%s' "$out"
}

# --- the contract, on the real command -------------------------------------
r="$(audit "$CMD")"
[ -z "$r" ] && pass "1. the dispatch contract holds in commands/approve-plan.md" \
            || { fail "1. commands/approve-plan.md:"; printf "$r\n"; }

[ "$N_EXITS" = "5" ] && pass "2. the shared block defines 5 exits and the mapping reads them from it" \
                     || fail "2. the shared block defines $N_EXITS exits, expected 5"

# --- the Strict surface list, across every file that carries it ------------
LIST='the surface is auth, payments, compliance, PII, or multi-tenant isolation'
miss=""
for f in commands/approve-plan.md commands/task-init.md; do
  grep -qF "$LIST" "${REPO}/${f}" || miss="$miss $f"
done
[ -z "$miss" ] && pass "3. the Strict surface list is byte-identical across its carriers" \
               || fail "3. the list differs or is absent in:$miss"

grep -qiE 'INVARIANTS_AND_NON_GOALS\.md' "$CMD" \
  && pass "4. the Strict round names the invariants artifact as its second rubric" \
  || fail "4. the Strict round does not name a second rubric"

grep -qiE 'ESCALATED exit naming its absence' "$CMD" \
  && pass "5. an absent invariants artifact escalates instead of running one pass" \
  || fail "5. an absent invariants artifact does not escalate"

# --- mutations: every clause must be load-bearing --------------------------
mutate() {  # mutate <label> <sed-expr> <expected-fragment>
  sed "$2" "$CMD" > "$TMP/m.md"
  local r; r="$(audit "$TMP/m.md")"
  if printf '%s' "$r" | grep -q "$3"; then pass "$1"; else
    fail "$1 (did not bite; findings: $(printf '%s' "$r" | tr '\n' ' ' | cut -c1-80))"
  fi
}
mutate "6. mutation: the isolation clause removed is detected" \
       's/artifact path and the rubric and NOTHING else/whatever context is available/' \
       'artifact path and the rubric'
mutate "7. mutation: the authoring-context prohibition removed is detected" \
       's/[Nn]ever the conversation that produced the plan/including the conversation that produced the plan/' \
       'authoring conversation'
mutate "8. mutation: an exit dropped from the mapping is detected" \
       's/^    - BUDGET\./    - REMOVED./' \
       'BUDGET is not mapped'
mutate "9. mutation: a sixth exit added is detected" \
       's/^    - ENVIRONMENT\./    - ENVIRONMENT.\n    - DEFERRED. invented here./' \
       'outside the shared set'
mutate "10. mutation: the single-hand-back clause removed is detected" \
       's/ONLY exit that hands back/one exit that hands back/' \
       'exactly one exit'
mutate "11. mutation: the confidence prohibition removed is detected" \
       's/no confidence field/a confidence field/' \
       'self-reported certainty'
# The first live run's actual near-miss, pinned: a mapping that names `failed`
# and not `needs_revision` approves a plan the review has just faulted.
mutate "12. mutation: an unmapped rubric value is detected" \
       's/needs_revision/omitted_value/g' \
       'needs_revision is unmapped'

# --- control ---------------------------------------------------------------
cp "$CMD" "$TMP/clean.md"
[ -z "$(audit "$TMP/clean.md")" ] \
  && pass "13. control: an unmutated copy reports nothing" \
  || fail "13. control fixture reported a finding, so the mutations prove nothing"

# --- B0b: the coverage check is RUN, not merely cited --------------------------
# The command cited `check-plan-coverage.sh` for months and never invoked it,
# approving on the assumption that an earlier command had run it against a plan
# that may have changed since. These three checks separate citing from running.
COV="${REPO}/scripts/check-plan-coverage.sh"

grep -qE 'bash scripts/check-plan-coverage\.sh <task-folder>' "$CMD" \
  && pass "14. approve-plan invokes the coverage checker, not just names it" \
  || fail "14. approve-plan does not invoke scripts/check-plan-coverage.sh"

sed 's|bash scripts/check-plan-coverage\.sh <task-folder>|the coverage checker|' "$CMD" > "$TMP/nocov.md"
grep -qE 'bash scripts/check-plan-coverage\.sh <task-folder>' "$TMP/nocov.md" \
  && fail "15. mutation: invocation downgraded to a citation was NOT detected" \
  || pass "15. mutation: invocation downgraded to a citation is detected"

# The control that matters. Prose asserting a checker exists proves nothing about
# the checker. Build a task whose brief names a deliverable no slice carries and
# require a refusal, then cover it and require a pass. Both exit codes are shown.
FIX="$TMP/cov"; mkdir -p "$FIX"
# Format read off templates/TASK_STATE.template.md, not invented: bullet rows with
# bracketed tags. The corpus's one real ledger uses a markdown TABLE instead, which
# is off-contract and is why rule 1 has never fired on real data.
cat > "$FIX/TASK_STATE.md" <<'TS'
## Requested deliverables

- the page the maintainer named [in-scope] [user-facing-content]
TS
cat > "$FIX/DECISIONS.md" <<'DC'
## Locked decisions

None locked in this task.
DC
plan() {  # plan <deliverable-tag-line>
  cat > "$FIX/IMPLEMENTATION_PLAN.md" <<PL
## Slices

### S1: does something else entirely

- Scope: \`somewhere/else.md\`
- Depends-on: none
- Status: not started
${1}
- Work complexity: LOW
- Exit criterion: WHEN S1 lands, the tree SHALL still lint clean
PL
}

plan "- Decision-ref: none locked; nothing to trace"
"$COV" "$FIX" > "$TMP/cov_bad.txt" 2>&1; bad=$?
plan "- Deliverable-tag: user-facing-content
- Decision-ref: none locked; nothing to trace"
"$COV" "$FIX" > "$TMP/cov_good.txt" 2>&1; good=$?

if [ "$bad" -ne 0 ] && [ "$good" -eq 0 ]; then
  pass "16. control: uncovered deliverable refused (exit $bad), covered one passes (exit $good)"
else
  fail "16. control: expected refuse-then-pass, got exit $bad then exit $good"
  sed -n '1,4p' "$TMP/cov_bad.txt"
fi

# --- provisional decisions (ADR-0233): labeled, never authorization ---------
# Each clause the audit asserts must be load-bearing, so each one is removed or
# inverted once and the audit must name it.
mutate "17. mutation: Locked decisions no longer the only authorization is detected" \
       's/`## Locked decisions` is the only authorization/`## Locked decisions` and `## Provisional decisions` are the authorization/' \
       'only authorization'
mutate "18. mutation: Provisional decisions read as authorization is detected" \
       's/and it never counts as authorization/and `## Provisional decisions` counts as authorization/' \
       'reads Provisional decisions as authorization'
mutate "19. mutation: the labeled pass dropped is detected" \
       's/passes only LABELED/passes/' \
       'labeled and never as authorization'
mutate "20. mutation: the per-P-N evidence question dropped is detected" \
       's/exist on the task branch/look plausible/' \
       'evidence exists on the task branch'
mutate "21. mutation: unattended runs losing the hand-back is detected" \
       's/Unattended, background and fleet-dispatched runs keep the hand-back/Every run drops the hand-back/' \
       'unattended hand-back unchanged'

echo
echo "plan-authorization-review: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
