# ADR-0245: An agent-written data rule must quote the brief

- **Status**: Accepted. The domain terms table rests on P-8 of the 2026-09-30 benchmark-driven-chain-fixes task, confirmed by that task's locked D-3. P-14 (a data or money rule the brief does not cover becomes a high-impact provisional decision) is still in force and still awaits the maintainer's confirmation: [ADR-0246](./0246-the-brief-silent-blind-reading-was-measured-and-removed.md) records a replacement that was tried and removed after it failed its measurement. The revert condition under `## Notes` is met for the brief-quote half: the rerun shipped both defects with the table and the quote in place. The review rules are maintainer-selected deliverables of that task (M1, M5).
- **Date**: 2026-09-30
- **Amends**: by reference, [ADR-0208](./0208-plan-approval-self-runs.md) on what the blinded plan review receives: the task `README.md ## Brief` joins the rubric. The review still receives no authoring context.
- **Tags**: review-hard, approve-plan, domain-terms, brief-grounding, sibling-sweep, check-plan-coverage, benchmark, measured

## Context

The 2026-09-29 benchmark (the same brief through four models, with and without Fhorja, one run per
cell) was followed by a blind code review of all eight repositories, with severities recalibrated
by a single reviewer. Two business-rule defects dominated:

- Refunds counted as income or not reducing envelope spending: 5 of 8 runs, with and without Fhorja.
- Identical real transactions inside one CSV dropped as duplicates, although the brief only asked
  to skip duplicates on re-import: 4 of 8 runs, with and without Fhorja.

The workflow did not change either rule. The model did: both Codex models wrote "identical rows are
duplicates" and "positive amounts are income" in both arms, and one Fhorja run recorded "positive
refunds count as income" as a decision. The four Fhorja task folders mention refunds zero times.

Its review did not catch them either. The Fhorja arm's internal reviews (`review-hard`, the blinded
plan review, ad-hoc reviewers) caught none of the 5 calibrated P1 defects that survived in that arm.
Each one was written in `DECISIONS.md`, asserted by a unit test, or both, and the reviewers cleared
the code against it:

- `review-hard` measures drift from the recorded decisions and never asks whether a decision is
  right for the brief.
- The blinded plan review "carries the artifact path and the rubric and NOTHING else", so it cannot
  see the brief.
- `task-init` adds its extra scrutiny only for auth, payments, compliance, PII, or multi-tenant
  isolation, and a money-tracking app with no payment flow matches none of them.

Where review did work, it worked on mechanical defects (races, validation mismatches, a CSV round
trip that corrupted data, focus bugs), and it prevented three defects that the base runs of the same
models shipped. It then fixed a defect in one place and left the same pattern in another, four
times.

## Decision

The plan and the review compare an agent-written data or money rule with the brief, and the brief's
ambiguous terms get a counter-case before implementation:

- **Brief quote (M1, P-14).** `review-hard` treats a decision the agent wrote that drops, merges, or
  reclassifies stored user data or money values as must-fix unless it quotes the brief line that
  authorizes it. `approve-plan` pastes `README.md ## Brief` into the blinded review's rubric and asks
  the same question of the plan. When no brief line covers the rule, the finding is resolved by
  recording it as a `### P-N` with `Impact: high` and `Evidence: brief silent on <term>`, which the
  draft pull request lists under decisions made without the maintainer.
- **Domain terms (P-8).** `task-init` writes `DECISIONS.md ## Domain terms` on every task: one row
  per brief term whose reading changes a stored or displayed value (the verbatim quote, a
  counter-case input that separates two readings, the chosen outcome, where it is shown), or the
  single row `none: <reason>`. `implementation-plan` turns each row into a test condition tagged
  with the term, and `scripts/check-plan-coverage.sh` fails a row that no slice covers.
- **Sibling sweep (M5).** Before `review-hard` closes a fix, it searches for the same defect pattern
  at sibling sites and lists each one found.

## Consequences

### Positive

- A rule like "identical rows are duplicates" now has to carry a brief quote, and the brief says
  "skip duplicates on re-import", so the rule surfaces as must-fix instead of being cleared as
  documented behavior.
- The counter-case ("two identical fares in one file", "a refund in an expense category") becomes a
  test before any code, which is the step the one run that got refunds right took on its own.
- A fix is less likely to leave its twin behind.

### Negative

- Every task pays for the domain terms table, at least one `none: <reason>` line.
- The blinded plan review's rubric grows by the brief. The brief is user input, not authoring
  context, so the isolation ADR-0208 depends on holds, but the rubric is longer.
- A reviewer may flag a benign data choice. The rule is scoped to stored user data and money
  values to limit that.

### Neutral

- The review still trusts a rule the brief itself states wrongly. This decision checks the agent's
  reading of the brief, not the brief.

## Alternatives considered

### Trigger the table only for finance-like briefs

- Cheaper on tasks that handle no money or stored data.
- Rejected: deciding whether a brief handles money or stored data is the judgment that failed, and
  a `none: <reason>` row costs one line.

### Add a finance surface to task-init's extra-scrutiny list

- Would pull `invariants-and-non-goals`, `test-strategy` and `review-hard` into money-tracking tasks.
- Rejected as the only fix: those commands ran in the Fhorja arm of some runs and still cleared the
  recorded rules, because none of them compared a recorded rule with the brief.

## Notes

- Provisional decisions this rests on: P-8 (the table's home and trigger, Impact: high) and P-14
  (a data or money rule the brief does not cover becomes a high-impact provisional decision,
  Impact: high; replaces P-12). The maintainer confirms or replaces them on the draft pull request.
- Revert condition: a rerun of the same brief shows the refund and in-file duplicate defects still
  shipping in the Fhorja arm with the table and the brief quote in place.

## References

- [ADR-0208](./0208-plan-approval-self-runs.md): the blinded plan review amended here.
- [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md): provisional decisions in an attended chain.
- [ADR-0235](./0235-agent-replaces-its-own-provisional-decision.md): how the agent corrects its own provisional entries.
- `commands/review-hard.md`, `commands/approve-plan.md`, `commands/task-init.md`, `commands/implementation-plan.md`, `scripts/check-plan-coverage.sh`, `wos/task-file-contracts.md`.
