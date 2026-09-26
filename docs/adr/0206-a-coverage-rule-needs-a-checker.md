# ADR-0206: A coverage rule needs a deterministic checker

- **Status**: Accepted
- **Date**: 2026-09-16
- **Tags**: coverage, deterministic-gate, plan-coverage, guard-mutation, adr-0056, adr-0103
- **Supersedes**: None.

## Context

Two coverage rules existed only as prose in the command files: every tagged deliverable row has a
covering slice carrying the matching tag (ADR-0103), and every locked decision is implemented by some
slice. Both were checked at the approval boundary and nowhere else.

On 2026-09-16 both failed on a real plan, and the failure is the argument. Four mechanical defects
were authored in one turn. The two with a deterministic checker, both protocol-level, were caught in
the same call. The two coverage defects survived a full turn and surfaced only when a human invoked
`approve-plan`.

## Decision

WHERE a rule requires that every item of one kind carries a corresponding item of another kind, the
workflow SHALL provide a deterministic checker for it, and SHALL NOT rely on a downstream command's
refusal condition as its only enforcement.

`scripts/check-plan-coverage.sh` is that checker for the task substrate. It runs FAIL-tier from
`implementation-plan`, so a coverage defect dies in the call that creates it, and advisory in the
lint, where a task folder may be absent.

Scope limit: this covers coverage rules over the task substrate. The five existing lint guards already
cover coverage relations between versioned files and are not reopened.

## Consequences

Positive. A defect that used to cost a human turn now costs a call.

Negative, and measured during the same session. The checker's deliverable-tag rule is GLOBAL rather
than per row: it asserts that SOME slice carries the tag, not that the slice covering a given row
does. It would not have caught the defect that motivated it. The root cause is a missing edge in the
model: `Decision-ref:` links a slice to a decision and nothing links a slice to the ledger row it
covers. Closing that needs a new per-slice field and is not done here.

Neutral. It reports the specific unmatched pair rather than a count, because a count is not
actionable.

## Alternatives considered

Keep the rules in prose and rely on `approve-plan`. Rejected on the measurement: that is exactly what
failed, and it costs a human turn per defect.

Make the checker FAIL-tier in the lint too. Rejected: `projects/` is gitignored, so CI would report
`not measured` and a local failure would block unrelated work.

## References

- ADR-0056, ADR-0103: the coverage rules this enforces.
- `evals/scripts/guard-mutation.py`: the harness whose premise is that a check is trusted when it
  fails on a mutation, which this checker's own validation used.
