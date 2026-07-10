# ADR-0039: Workflow Batch Dispatch Empirical Sweet Spot

- Status: Accepted
- Date: 2026-06-05
- Tags: orchestration, workflow-tool, batch-dispatch, empirical, parallelism

## Context

Following ADR-0038 (Workflow tool as orchestration primitive), the open question
was: how many parallel subagents should a single `workflow` invocation dispatch
per batch for read-only or independent documentation work?

Three failure modes shape the answer:

1. Concurrency cap saturation. The workflow runtime caps in-flight subagents at
   `min(16, cpu_cores - 2)` per invocation. Dispatching > 25 agents queues the
   tail behind the cap, eliminating the parallelism benefit while still paying
   the orchestration cost (substrate writes, apply step, token spend).
2. StructuredOutput schema-skip. Subagents occasionally emit a text response
   instead of calling `StructuredOutput`. This shows up post-apply as missing
   artifacts and forces re-dispatch. Observed rate correlates with prompt
   length and ambiguity, not batch size directly, but compounds with batch
   size because more agents = more chances to skip.
3. Substrate write contention. Subagent artifact writes must serialize through
   a deterministic apply step (ADR-0038 Rule 2). Larger batches lengthen the
   apply tail, raising the chance of mid-apply interruption.

Lived evidence from the 2026-06-05 session across 5+ batches, ~165 parallel
subagents total:

- Batch `w59uu3zym` : 12 agents, mixed re-dispatch, 1 schema-skip after
  focused-prompt mitigation was applied late. Remaining 11 succeeded.
- Mid-session batch : 8 agents, 0 schema-skips, 100% success, fastest
  apply tail of the session.
- Batch `w6jozlzky` : 10 agents, 0 schema-skips, 100% success.
- Two follow-on batches at 15 and 18 agents both completed with 0 skips
  once focused-prompt template was standardized.
- Each batch consumed 400k to 1.3M subagent tokens. Cost scales roughly
  linearly with batch size; latency does not (capped at ~16 in-flight).

The skip-rate collapse to 0 came from prompt shape, not size reduction:
focused prompts of 300 to 500 words with an explicit StructuredOutput call
reminder at the bottom eliminated skips across the remaining 4 batches.

## Decision

For read-only or independent documentation work dispatched via the workflow
tool:

1. Default batch size is 15 to 25 agents per workflow invocation.
2. Below 10 agents per batch, the orchestration overhead (apply step,
   substrate scan, token accounting) dominates the parallelism win. Prefer
   inlining the work or combining with an adjacent batch.
3. Above 25 agents per batch, the runtime cap `min(16, cpu_cores - 2)`
   serializes the tail behind already-running agents with no latency gain.
   Split into two batches instead.
4. Every dispatched subagent prompt MUST be focused (300 to 500 words) and
   MUST end with an explicit reminder to call `StructuredOutput` exactly
   once. This is the single highest-leverage mitigation against schema-skip.
5. After each batch applies, run `scan-substrate-orphans.py` against the
   batch manifest before dispatching the next batch. Orphan artifacts
   (written but not declared, or declared but not written) indicate either
   schema-skip or apply-step interruption and must be resolved before the
   next batch.
6. Batches that mutate shared state (cross-file refactors, lockfile edits,
   schema migrations) are out of scope for this ADR; use the conservative
   sequential path from ADR-0038 instead.

## Consequences

Positive:

- Predictable per-batch latency. With the cap at 16 in-flight, a 15 to 25
  agent batch completes in roughly 1.5 to 2 wall-clock units of a single
  agent.
- 0% schema-skip rate is achievable and was observed across 4 consecutive
  batches once the focused-prompt template was adopted.
- Orphan scan post-apply gives a fast pass/fail signal before committing
  to the next batch, preventing cascading drift.

Negative:

- Authors of subagent prompts must hold the 300 to 500 word discipline.
  Longer prompts will silently raise skip rate without warning.
- Cost grows linearly with batch size even when latency does not. Operators
  must weigh token spend against wall-clock urgency.
- The 15 to 25 range is calibrated to the current runtime cap. If the cap
  changes (different hardware, runtime upgrade), this ADR must be revisited.

## Alternatives Considered

- Fixed batch size of 10. Rejected: leaves ~6 concurrent slots idle on
  every batch, paying full orchestration cost for partial throughput.
- Unbounded batch size (50+). Rejected: tail saturates behind cap, apply
  step balloons, and any single schema-skip taints a larger blast radius.
- Sequential dispatch (batch size 1). Rejected by ADR-0038 for independent
  doc work; this ADR refines the parallel default rather than re-litigating
  it.
- Dynamic batch sizing based on live cpu probe. Deferred: adds runtime
  complexity for marginal gain over the static 15 to 25 window.

## References

- ADR-0038 : Workflow tool as orchestration primitive (especially Rule 2
  on deterministic apply step serialization).
- `wos/workflow-patterns.md` : canonical patterns for workflow dispatch,
  to be updated with the 15 to 25 default.
- Session log 2026-06-05 : batches `w59uu3zym`, `w6jozlzky`, plus three
  unnamed batches at 8, 15, and 18 agents.
- `scan-substrate-orphans.py` : post-apply verification script.

## Notes

The 15 to 25 window is empirical, not theoretical. It assumes the current
`min(16, cpu_cores - 2)` cap and the current focused-prompt template. Revisit
this ADR if either changes, or if a future batch run shows skip rate > 0
under the standard template (which would indicate prompt template drift).
