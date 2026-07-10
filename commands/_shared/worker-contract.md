Canonical worker contract for any orchestrator-dispatched sub-agent (Claude Code Task tool, Cursor agent subagent, Codex agents, Anthropic Dynamic Workflows `spawn()`).

Per ADR-0034 (Substrate peers + worker contract) and ADR-0038 (Workflow tool primitive; Rule 1 mandates typed StructuredOutput transport, prose-file returns FORBIDDEN). Status taxonomy verbatim from Anthropic Outcomes API (2026-05-06).

## Input shape (orchestrator declares)

```yaml
worker_role: <persona-slug | command-name | fleet-worker-id>
worker_tier: claude-haiku-4-5 | claude-sonnet-4-6 | claude-opus-4-7 | claude-opus-4-8
context_injection:
  task_state_excerpt: <relevant TASK_STATE.md sections, read-only>
  decisions_excerpt: <relevant DECISIONS.md D-N entries, read-only>
  source_of_truth_excerpt: <relevant SOURCE_OF_TRUTH.md sections, read-only>
  parent_artifact_paths: [<path>, ...]
parent_artifacts: read-only mounted
substrate_writes: forbidden (workers NEVER write substrate directly)
fleet_inbox_artifact: fleet-inbox/<run_id>/<worker_id>   # StructuredOutput artifact key (ADR-0038 Rule 1), NOT a prose file
task_input:
  <orchestrator-specific structured input; declared in orchestrator command's frontmatter `worker_input_schema`>
timeout_ms: <integer | null>
max_iterations: <integer | null>
```

## Output shape (worker emits)

Per ADR-0038 Rule 1, the worker returns its result by invoking the `StructuredOutput` tool exactly once with `artifact=fleet-inbox/<run_id>/<worker_id>` and a JSON payload matching the orchestrator's `worker_output_schema`. Free-form prose returns and `.partial.md` file writes are FORBIDDEN; the orchestrator consumes the typed payload, not parsed prose. A typed `.partial.json` may be written only as a replay aid, never as the transport.

The payload carries these fields (orchestrator declares the full schema in `worker_output_schema`):

```json
{
  "worker_id": "<unique within run>",
  "worker_role": "<echoed from input>",
  "worker_tier": "<echoed from input>",
  "ts_started": "<ISO 8601>",
  "ts_completed": "<ISO 8601>",
  "status": "satisfied | needs_revision | max_iterations_reached | failed | interrupted",
  "deliverables": "<one or more structured findings; shape per worker_output_schema>",
  "open_questions": ["<one line each; empty array if none>"],
  "evidence": ["<file:line, URL, or transcript excerpt; one per claim that affects substrate>"],
  "notes_for_orchestrator": "<free-form, optional; orchestrator may consume or ignore>"
}
```

## Status taxonomy (verbatim Outcomes API)

- `satisfied`: worker met every declared exit criterion; deliverables are complete and ready to merge.
- `needs_revision`: worker reached partial completion; one or more deliverables need a second pass with revised input. Orchestrator may retry once with updated `task_input`; second `needs_revision` becomes `max_iterations_reached`.
- `max_iterations_reached`: worker reached the `max_iterations` cap without converging. Orchestrator merges what it has and flags the gap.
- `failed`: worker hit an unrecoverable error (tool failure, missing input, contract violation in `task_input`). Orchestrator does NOT retry; logs `event=worker_failed` and continues with remaining workers.
- `interrupted`: worker was cancelled mid-run (user Esc, timeout, fleet cancellation). Orchestrator treats interrupted partials as discarded; does not merge.

## Error shape

When `status: failed`, the StructuredOutput payload MUST also include an `error` object:

```json
"error": {
  "error_class": "tool-failure | missing-input | contract-violation | timeout | unknown",
  "error_message": "<one-line summary>",
  "error_evidence": "<stack trace, log excerpt, or other diagnostic>",
  "recoverable": true
}
```

`recoverable: true` signals the orchestrator MAY dispatch a replacement worker with the same `task_input`. `recoverable: false` means do not retry; surface in synthesis.

## Partial shape (Epic J fleet merger consumption)

The orchestrator-merger consumes ALL workers' StructuredOutput payloads (keyed by `artifact=fleet-inbox/<run_id>/<worker_id>`) after convergence (J.4) and merges per declared `merge_strategy`:

- `union`: aggregate all deliverables across workers, deduplicate by canonical key declared in `worker_output_schema`.
- `last-by-timestamp`: when two workers emit deliverables targeting the same section, keep the latest by `ts_completed`.
- `consensus-of-N`: require at least N workers to agree on each deliverable; drop dissenters with `event=consensus_drop` logged.
- `manual-review`: orchestrator emits a PROPOSED block under each section with all workers' deliverables side-by-side; user selects via `approve-proposed`.

Merger writes ONE transaction header per merged substrate section and ONE `VERIFICATION_LOG.jsonl` line per merged section with `event=fleet-merge`, `partials=[worker_id, ...]`, `strategy=<chosen>`.

## Refusal conditions (worker declines to run)

A worker MUST refuse with `status: failed`, `error_class: contract-violation` when:

- `task_input` violates the orchestrator's declared `worker_input_schema`.
- `worker_tier` is below the minimum declared in the orchestrator command's `min_worker_tier` field.
- `parent_artifact_paths` references files outside `active/<task>/` or violates read-only mount.
- `substrate_writes` is requested (impossible: workers have no Edit/Write on substrate; this is a sanity check).

## Idempotency

Workers MUST be idempotent on `task_input`: dispatching the same `task_input` twice within a run MUST produce equivalent deliverables (subject to model non-determinism noted in the synthesis). Orchestrator-mergers SHOULD deduplicate by `task_input` hash to avoid double-merging the same worker output during retry scenarios.

## Validation budget (stop-loss)

A worker debugging a failing validation step MUST bound the effort instead of grinding silently. When validation debugging exceeds 3 attempts OR about 15 minutes of wall-clock on the same failure, the worker STOPS and returns rather than continuing:

- Set `status: needs_revision` (first budget hit) or `status: max_iterations_reached` (a retried worker hits the budget again).
- Include, in the deliverable, the exact failing check, the minimal reproduction command, and a one-line hypothesis for the cause. Name the suspected coupling or shared-state source when the failure is order-dependent (see the bug-class `order-dependent-test-pollution-via-shared-async-state`).
- Do NOT keep re-running an expensive suite past the budget hoping it goes green; a slow grind that the orchestrator cannot see is indistinguishable from a hang and wastes the run.

The orchestrator consumes the honest early return and routes the slice (retry with revised input, hand to sequential `implement-approved-slice`, or surface to the user). An interrupted or killed worker returns nothing; a budgeted return preserves the structured-data contract. This is the worker-level form of the K.7 oscillation rule (ADR-0036): stop and report beats loop and hide.

## Suite-cost-aware validation

When a validation suite is slow (a full run costs minutes), the worker iterates cost-aware:

- Iterate with the narrowest scope that exercises the change: a path-scoped or name-scoped run (`-t`, a single file or directory) while debugging.
- Run the full suite exactly once at the end to confirm, not on every iteration.
- Bound every wait on a long-running command with a timeout; prefer the harness completion signal over a busy-wait poll loop (an unbounded `until grep ...` poll reads as a silent multi-minute stall).

The goal is to spend validation time on signal, not on repeatedly paying the full-suite cost; combined with the stop-loss budget above, this keeps a worker's runtime legible to the orchestrator.

## Maturity ladder gate

Per `wos/substrate-peers.md` § Maturity ladder hook, fleet workers (this contract) operate at L4 (peer equivalence) by design — they have explicit ownership of their `fleet-inbox` namespace and the orchestrator-merger has explicit ownership of substrate merges. Personas (Epic K) operate at L1-L4 depending on graduation evidence; L5 (autonomous dispatch of own workers) is reserved.
