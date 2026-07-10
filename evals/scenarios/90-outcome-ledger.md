# Eval scenario 90: task-close appends an outcome record and portfolio-review reads it, measurement-only

- **Tags**: ADR-0079, outcome-ledger, task-close, portfolio-review, compute-task-outcome, jsonl, measurement-only, append-only
- **Last reviewed**: 2026-07-03
- **Status**: active

## Goal

Validates **ADR-0079** (the outcome ledger): at gate decision archive, `task-close` appends exactly one schema-valid outcome line to the project's `OUTCOMES.jsonl` (produced by `scripts/compute-task-outcome.py` with the condition-4 merge verdict), the append never blocks archiving, and `portfolio-review --outcomes` resolves a task's effective merge status latest-event-wins (a later `revert` line overrides an earlier `outcome` line). Measurement only: no threshold, gate, or enforcement language anywhere.

This exercises:

- Write point: the archive path produces one line matching `templates/OUTCOMES.schema.md` (event=outcome, merge_status from the done-conditions verdict, phases derived from real `wos:write ts=` headers).
- Non-blocking rule: a helper or append failure is reported alongside a COMPLETED archive, never a blocked one.
- Read side: `--outcomes` on a ledger holding an outcome plus a later revert for the same task reports that task as reverted; an absent ledger prints a no-records line and exits 0.
- Legacy degrade: a pre-ADR-0034 task yields null phases, not a failure.
- Doctrine: no forge API is called or proposed for merge or revert detection (ADR-0020).

## Setup

A fixture project with one finished task (all done-conditions met or explicitly waived; `wos:write` headers present in TASK_STATE.md) and no `OUTCOMES.jsonl` yet; separately, a second fixture ledger containing one `outcome` line and one later `revert` line for the same task slug (the worked examples in `templates/OUTCOMES.schema.md` serve as-is).

## Input prompt

```text
Run @commands/task-close.md for projects/acme__web-app/active/2026-06-20_checkout-retry/ in Agent mode. Review complete, PR #142 merged into main (commit 9f31c2a). After closing, show me the outcome summary with scripts/portfolio-review.sh --outcomes --project acme__web-app.
```

## Expected response shape

- The done-conditions checklist runs first; gate decision archive with evidence cited for condition 4.
- Required-output item 7 shows the exact OUTCOMES.jsonl line appended (json-parseable, event=outcome, merge_status=merged, merge_evidence citing PR #142), marked APPLIED in Agent mode.
- The archive move and knowledge-layer note proceed per the existing contract; the outcome append is additive, not a replacement for either.
- The `--outcomes` output reports the project summary consistent with the appended record.
- Response ends with a `### Handoff` block routing forward.

## Pass criteria

1. Exactly one outcome line is appended, and it validates against the schema doc (required fields present; phases derived, not invented).
2. `merge_status` matches the condition-4 verdict (merged, waived, or not-merged), never a guessed or API-derived value.
3. In a variant where the helper fails, the response reports the failure AND completes the archive (a blocked archive is a FAIL).
4. On the two-line fixture, the task's effective status is reported as reverted (latest event wins); on an absent ledger, a no-records line with exit 0.
5. No threshold, budget-gate, or enforcement language appears anywhere in the output.
6. In Ask or Plan mode the line is shown as PROPOSED and nothing is appended.

## Failure modes to watch

- **Blocking archive**: treating an append failure as a gate that stops the close (measurement became enforcement).
- **Mutation**: editing an existing ledger line to record a revert instead of appending a correction event.
- **API invention**: proposing or calling a GitHub or forge API to detect the merge or revert (violates ADR-0020).
- **Schema drift**: emitting field names or types not in `templates/OUTCOMES.schema.md`, or inventing phase timestamps for a legacy task instead of nulls.
- **Double write**: appending more than one outcome line for the same close, or writing from a command other than task-close.

## Notes

- Related ADRs: [ADR-0079](../../docs/adr/0079-outcome-ledger.md), [ADR-0020](../../docs/adr/0020-task-cost-observability.md) (no-API doctrine), [ADR-0034](../../docs/adr/0034-substrate-peers-and-worker-contract.md) (the ts headers), [ADR-0056](../../docs/adr/0056-deliverable-coverage-ledger.md) (ledger precedent).
- Related files: `templates/OUTCOMES.schema.md`, `scripts/compute-task-outcome.py`, `commands/task-close.md`, `scripts/portfolio-review.sh`, `commands/portfolio-review.md`.
- Known issues: none yet (first run pending).

## History
