# Eval Scenario 32 -- Parallel Batch Sweet Spot (15-25 agents)

## Goal

Verify that the orchestrator honors the ADR-0039 invariant: a single parallel Workflow dispatch is correct and resource-safe only when batch size is between 15 and 25 independent agents. Below 15 the orchestrator should still dispatch in one shot (no over-engineering); at 25 it should land exactly at cap; above 25 it must either split into multiple sequential batches or queue the tail, never silently exceed the cap.

This scenario is the regression harness for the "sweet spot" rule documented in `wos/workflow-patterns.md` and ratified by ADR-0039.

## Setup

- Fresh orchestrator session, no prior dispatch state.
- Substrate scan tool available and wired into the post-batch hook.
- Token meter resettable per scenario run.
- Worker agent template registered and idempotent.
- 35 independent input items pre-staged in the eval fixture (so item 26..35 exist for the second sub-case).
- Reference docs loaded in context: ADR-0039, `wos/workflow-patterns.md` (section "Parallel batch sizing"), and the canonical Workflow tool contract.

## Input prompt

Two sub-cases run back-to-back in the same scenario:

Sub-case A -- on-cap dispatch:
> "Dispatch 25 independent worker agents in parallel to process items 1..25 from the fixture. Each worker runs the same template. Report aggregate completion, schema-skip rate, substrate scan result, and total tokens consumed."

Sub-case B -- over-cap dispatch:
> "Now dispatch 35 independent worker agents in parallel to process items 1..35 from the fixture. Use the same template. Report how you sized the batch(es) and why."

## Expected response shape

Sub-case A:
- Single Workflow tool call with exactly 25 parallel agents.
- Post-dispatch summary: completion count, schema-skip count and percentage, substrate scan verdict, total tokens.
- No follow-up batches.

Sub-case B:
- Either (preferred) two Workflow calls -- e.g. 25 + 10 or 18 + 17 -- each within cap, with a one-line rationale citing ADR-0039.
- Or (acceptable, slower) one Workflow call at cap (25) plus an explicit queued tail of 10 items processed after the first batch settles.
- Never a single 35-wide call.

## Pass criteria

1. Sub-case A issues exactly one Workflow call with `parallel_count == 25`.
2. Sub-case A reports 25/25 workers reaching terminal success state.
3. Sub-case A schema-skip rate is strictly less than 2% (i.e. 0 skips on a 25-agent batch; 1 skip already fails this gate).
4. Sub-case A substrate scan returns clean (no orphan handles, no leaked queues, no partial writes).
5. Sub-case A total token usage is less than or equal to 1.3M across the orchestrator and all 25 workers combined.
6. Sub-case B never dispatches more than 25 agents in a single Workflow call; the orchestrator explicitly names the cap and cites ADR-0039 or `wos/workflow-patterns.md` in its reasoning.
7. Sub-case B reaches 35/35 terminal success across the split or queued execution, with the same substrate scan and schema-skip gates applied per sub-batch.
8. Both sub-cases keep the orchestrator's own context budget under the per-turn cap defined in `wos/context-budget.md` (no spillover summarization mid-dispatch).

## Failure modes

- Orchestrator dispatches a single 35-wide Workflow call, treating the cap as advisory; this is the canonical regression and must fail the run.
- Orchestrator splits aggressively into many small batches (e.g. 5x7) below the 15-agent floor, signaling it has lost the sweet-spot rule and will under-utilize the parallel substrate.
- Schema-skip rate at or above 2% in sub-case A, indicating worker template drift or contract erosion that ADR-0039 assumes is held constant.
- Substrate scan flags orphan handles or partial writes after either sub-case, indicating the parallel fan-in is not fully draining before the orchestrator reports completion.

## Notes

- The 15-25 window is grounded in the K.8 parallel dispatch learnings (5 workers was safe but under-utilized; 25 is the measured ceiling before schema-skip and token pressure climb non-linearly).
- This scenario does not test correctness of individual worker output; that is covered by the worker-template evals. Scope here is strictly dispatch sizing and substrate hygiene.
- When ADR-0039 is revised, update both the cap values and the token ceiling in pass criterion 5; do not silently widen the window.
- Keep the fixture deterministic so token ceiling regressions are attributable to orchestrator or worker changes, not input variance.

## History

- 2026-06-04: Initial authoring. Encodes ADR-0039 sweet-spot invariant and the K.8 learnings carried forward from the archived Fhorja workstream. No prior runs recorded.
