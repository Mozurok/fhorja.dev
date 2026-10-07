# ADR-0246: The brief-silent blind reading did not hold up in the rerun and is removed

- **Status**: Accepted. The removal is the locked D-1 of the 2026-09-30 benchmark-rerun-followups task. The corrections that stay rest on that task's provisional P-6 (the round-trip test condition) and P-9 (the one-call Status write and commit proof), listed under `## Notes`, which await the maintainer's confirmation.
- **Date**: 2026-10-01
- **Amends**: by reference, [ADR-0244](./0244-the-chain-holds-slice-by-slice-in-a-headless-run.md) on how a closing command writes the slice `Status:` line. That the line is the only closure record, and that a Status write is not a plan revision, stand. Also [ADR-0242](./0242-a-fleet-worker-returns-through-its-own-worktree.md) D-2 on how a fleet worker moves its worktree to `base_ref`; the proof that HEAD equals `base_ref` stands.
- **Tags**: domain-terms, brief-grounding, check-plan-coverage, substrate-write, branch-commit, round-trip, benchmark, measured, reverted

## Context

ADR-0244 and ADR-0245 were measured on 2026-09-30 by a rerun of one brief (a local-first budget web
app) on one model: three new runs with those decisions installed against the runs made before them,
each graded by a blind code review and one calibration standard. Thirteen blind reviews in all.

What the reviews found:

- 30 calibrated P1 defects in 13 runs. 20 came from a rule the agent chose and wrote down (how
  refunds count, which rows are duplicates, what rolls over); 10 came from code with no decision
  behind it.
- On this model the two targeted defects did not move: refunds counted as income in 3 of 3 new
  runs, and identical rows inside one file dropped as duplicates in 2 of 3. The decisions were in
  the task files, quoted and tagged.
- ADR-0245's brief-silent path (record the rule as a provisional decision with `Impact: high`)
  passed every choice it targeted, because that was the state the runs were already in at plan time.

This branch tried to fix that, and each piece was written to be measured:

- Plan checker rules 6b to 6d in `scripts/check-plan-coverage.sh`. 6b wanted the word a qualifier
  (`on`, `per`, `when`, `after`, `for`) governs in a row's brief quote to appear in its
  counter-case. 6c wanted the counter-case values in the tagged exit criterion. 6d wanted a
  `## Domain terms` row for a provisional decision that drops, skips, dedups or merges records.
- A brief-silent drop or merge keeps every record, applied only within the qualifier the brief
  quote names.
- A brief-silent reclassification records both readings in its row, and `approve-plan` runs a blind
  second reading in a dispatch of its own, carrying only the brief and the rows. A different answer
  marks the row `contested`, and the reviewer's reading ships.
- `review-hard`, `pr-package` and `task-close` read or name those rows.

The same branch carried corrections and cost cuts that do not depend on that mechanism: a
round-trip test condition for a formatter and parser pair, a one-call write for a slice `Status:`
line, a one-call commit proof, and a fleet worker first act that does not need `git reset --hard`.

## Measurement

The rerun used GPT-6.1 Sol on Codex at high effort, with Fhorja installed from the head of this
branch. Three runs on the benchmark brief and one on a frozen brief from another domain. The
harness, the rubric, the blind-review prompt and the calibration standard were unchanged.

| Arm | Runs | Cost mean | Wall mean | Calibrated P1 per run | P1 mean |
|---|---|---|---|---|---|
| no workflow | G | $1.86 | 56 min | 3 | 3.0 |
| before ADR-0244 and ADR-0245 | H, L, M | $3.56 | 65 min | 3, 5, 3 | 3.7 |
| with ADR-0244 and ADR-0245 | I, J, K | $4.19 | 72 min | 2, 3, 4 | 3.0 |
| with the mechanisms above | N, O, Q | $4.60 | 73 min | 3, 3, 4 | 3.3 |

Identical rows inside one file dropped: 3 of 3 before, 2 of 3 with ADR-0244 and ADR-0245, 2 of 3
with the mechanisms above (N and O). Refund counted as income: 3 of 3 in all three arms.

The gain criterion was fixed before the runs: duplicates in 0 of 3, every run at 2 or fewer P1,
mean cost at or below $4.19, mean wall time at or below 72 minutes. It was not met on any of its
four parts (2 of 3, 4 P1 in one run, $4.60, 73 minutes). The revert condition, duplicates in 2 or
more of 3 runs, was met. The measured version cost $0.41 more per run than ADR-0244 and ADR-0245 and
$1.04 more (29 percent) than the version before them, with no gain in quality on either
comparison. Run Q (89 minutes, $5.58) is the outlier; without it the mean is $4.11 and 65 minutes,
still above the version before ADR-0244.

Why the rows passed the checks without facing the ambiguity:

- Run N wrote a `deduplicate` row quoting "skips duplicates on re-import" with the counter-case
  "re-import same date/description/amount but different category". The qualifier word was in the
  counter-case, so rule 6b passed, and the counter-case never tested rows inside one file, which is
  the reading that matters. The check verifies that a word is present, not that the counter-case
  sits on the other side of the qualifier.
- No run wrote a refund row. With no reclassification row, the blind reading had nothing to read.
- The probe run's table had no quote column, so rule 6b had nothing to compare and the checker
  reported clean. Its row for "skips duplicates on re-sync" chose "repeated rows collapse", and its
  import drops identical sessions inside one file: the same defect in a domain with no money in
  it. The keep-every-record reading is not an overfit to the benchmark. It was not applied.
- The model chooses the domain reading: refund as income in 10 of 10 runs on this brief across all
  arms, in-file dropping in 8 of 10. Text rules and lexical checks over the agent's own table did
  not change that choice, because the agent writes rows that pass the checks.

What did work: the round-trip test condition fired on the probe (its plan asserts
`parse(format(x))` for 29/02/2024 and a 24:00 duration), the one new mechanism seen working in a
run. In the three benchmark runs the app's own formatter still produced one negative amount its
parser rejected (run Q), against two in the runs with ADR-0244 and ADR-0245.

## Decision

The mechanisms the measurement did not support are removed. The corrections stay.

Removed:

- Rules 6b, 6c and 6d of `scripts/check-plan-coverage.sh`, their cases in
  `scripts/tests/test-check-plan-coverage.sh`, and the row-contract text for them in
  `wos/task-file-contracts.md`, including the qualifier sentence on the counter-case.
- The readings the brief does not settle: keep-every-record for a brief-silent drop or merge, both
  readings for a reclassification, and the `contested` mark, in `wos/task-file-contracts.md` and the
  co-writer text for them in `wos/substrate-peers.md`.
- The blind reading and its `contested` path in `approve-plan`, the domain-terms reading in
  `review-hard` (and its line in the definition of done), and the naming of unlocked domain terms in
  `pr-package` and `task-close`. Those paragraphs return to their text at the ADR-0245 merge.
- Eval scenarios 152 and 153, which graded removed mechanisms, and the structural pins and guards
  in `evals/scripts/structural-evals.py` for that text. Scenario 148 returns to its ADR-0245
  expectations and keeps the fixture builder and probe added for it.

ADR-0245's brief-silent path is in force again: a data or money rule the brief does not cover is
recorded as a `### P-N` with `Impact: high` and `Evidence: brief silent on <term>`. The earlier
measurement showed that path never changed a choice, and this decision puts nothing in its place.

Stays:

- **Round trip (P-6).** WHEN a slice adds or changes code that both formats and parses the same kind
  of value, `implementation-plan` gives it a `Test condition:` asserting that parsing the formatted
  value returns the original for a boundary value, and for a negative value where the type has a
  sign. The rule names no currency.
- **Status line in one call (P-9).** `slice-closure` and `implement-approved-slice` write a slice
  `Status:` line through `scripts/emit-substrate-write.sh status`, which replaces that one line in
  place and appends the `## Slices` log line. A plain edit would change the section after its last
  logged write and print a content-vs-log drift on every close. It stays as a correction. The
  measurement showed no saving from it at this sample size. The approval lock keeps reading the plan
  revision from the log, and the `implement-fleet` orchestrator's Status write is unchanged.
- **Commit proof in one call (P-9).** `branch-commit --apply` runs the display, `git write-tree`,
  the commit and the post-commit proof in one shell call, with every check it ran before.
- **Fleet worker first act.** An `implement-fleet` worker moves its worktree to `base_ref` with
  `git reset --keep <base_ref>`, which needs no ancestry and aborts rather than discard a local
  edit, then proves HEAD equals `base_ref` as before. ADR-0242 D-2's `git reset --hard` is denied by
  the permission system, and the fast-forward that replaced it fails whenever the default branch
  has moved past the task branch.
- The `test-guard-mutation.sh` fix (three mutations still looked for the end of `SHIPPED_SCRIPTS`
  before `check-slice-order.sh` was appended to it), the `code-locate` return to the slice whose gate
  sent it, closed-slice stubs in `self-critique-and-revise`, the remote wording for standing
  authorization, the non-finance examples in `wos/task-file-contracts.md`, the fixture builders for
  scenarios 148, 150 and 151, and a structural pin on the kept command text.

## Consequences

### Positive

- A smaller change to the always-loaded command text. Against the default branch the four skills are
  smaller: `approve-plan` by 1,260 characters, `review-hard` by 281, `task-close` by 224 and
  `pr-package` by 171.
- Fewer plan rewrites. A checker rule that fails the plan costs a rewrite of about one to two turns
  each time it fires (an estimate made before the rerun), and rules 6b to 6d had no measured effect
  on what the agent chose.
- The removed mechanisms no longer add turns to a run. The rerun measured the whole version, kept parts included, so no run isolates how much of the extra cost they caused.

### Negative

- The two defects the rerun targeted are not addressed. A brief-silent data rule is again resolved
  by recording it as `Impact: high`, which passes. Nothing in the workflow changes the model's
  reading of refunds or of identical rows.
- The branch removed after the measurement is not itself measured. It differs from the measured one
  by dropping mechanisms, so the earlier measurement of ADR-0244 and ADR-0245 is the nearest
  evidence for how it behaves.

### Neutral

- A user-written project conventions file stays a candidate for later. A domain defaults file
  (refund as spending, identical rows kept) would flip both measured defects by construction, which
  grades the rules with their own answer key, so it was not tried.

## Alternatives considered

### Keep the branch as measured

- The checks and the blind reading stay for another round.
- Rejected: every pre-registered gain test failed and the revert condition was met. The version
  measured costs more per run than the one before it.

### Remove everything the branch added

- Also drop the round-trip condition, the Status write and the commit proof.
- Rejected: the round-trip condition fired on the probe at about one turn, the Status write fixes a
  drift a plain edit would cause, and the fleet first act and the other corrections are fixes, not
  cost cuts.

### Keep rules 6b to 6d and drop only the blind reading

- The checker keeps reading the counter-case.
- Rejected: the one row that mattered passed 6b, and the probe's table gave 6b nothing to read. The
  rules check that a word is present, which the agent can satisfy without facing the ambiguity.

### Stop the run for the maintainer before code

- The person decides the brief-silent term.
- Rejected earlier and not reopened here: under standing authorization nobody answers, so the run
  stalls or the agent answers itself.

## Notes

- Provisional decisions the kept parts rest on, from the 2026-09-30 benchmark-rerun-followups task:
  P-6 (the round-trip test condition) and P-9 (the Status helper and one-call commit proof, which
  replaces P-5), both `Impact: high`. The maintainer confirms or replaces them on the draft pull
  request. P-2, P-3, P-10 and P-11, the removed mechanisms, are superseded by that task's locked
  D-1.
- Left out of the measurement and still open: a check for an absent-period default (a rule like
  "does not repeat" with no counter-case for the empty period) and a `review-hard` scan-set line
  naming the domain terms table.
- The criteria in the revert conditions for the kept parts were fixed before the runs and are
  unchanged: a run that starts a slice with an unclosed dependency or leaves a slice without
  `Status: closed` reverts the Status helper, a commit whose tree differs from the tree shown
  reverts the one-call commit, and the round-trip class shipping with the test condition present
  reverts the round-trip obligation.

## References

- [ADR-0245](./0245-agent-written-data-rules-must-quote-the-brief.md): the brief-quote rule and the brief-silent path in force again.
- [ADR-0244](./0244-the-chain-holds-slice-by-slice-in-a-headless-run.md): the closure record whose write this amends.
- [ADR-0242](./0242-a-fleet-worker-returns-through-its-own-worktree.md): the fleet worker whose first act this amends.
- `scripts/check-plan-coverage.sh`, `scripts/emit-substrate-write.sh`, `wos/task-file-contracts.md`, `commands/implementation-plan.md`, `commands/slice-closure.md`, `commands/implement-approved-slice.md`, `commands/branch-commit.md`, `commands/implement-fleet.md`.
