---
name: <kebab-case-orchestrator-name>
description: <Use when N >= 3 independent work units ... (state the threshold in this form; the fan-out floor is in wos/workflow-patterns.md ## Fan-out floor). Do not use when ...> Dispatches N <worker-role> sub-agents per the worker contract; merges partials into <target-artifact>.
metadata:
  category: <one category from WORKFLOW_OPERATING_SYSTEM.md ## Command categories, the set lint checks as VALID_CATEGORIES in scripts/lint-commands.sh; the shipped fleets use audit-and-sweep, research-and-sourcing, design-and-ui and execution-and-closure>
  primary-cursor-mode: <Ask | Plan | Agent>
  multi-repo-aware: <true | false>
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep, Agent]
  x-wos-profiles: [full]
  provenance: first-party
  suggested-model: claude-opus-5-5
  orchestrator: true
  workers:
    - role: <worker-role-slug>
      tier: claude-sonnet-5
      contract_ref: commands/_shared/worker-contract.md
  max_fanout: 20
  convergence:
    pattern: barrier
    timeout_ms: 600000
    partial_ok: false
  merge_strategy: union
  worker_input_schema: |
    {
      "type": "object",
      "required": ["target_id", "scope"],
      "properties": {
        "target_id": {"type": "string"},
        "scope": {"type": "string"}
      }
    }
  worker_output_schema: |
    {
      "type": "object",
      "required": ["status", "deliverables"],
      "properties": {
        "status": {"enum": ["satisfied", "needs_revision", "max_iterations_reached", "failed", "interrupted"]},
        "deliverables": {"type": "array"}
      }
    }
---
# <orchestrator-name>

Act as a senior/staff engineering orchestrator dispatching N <worker-role> sub-agents and synthesizing their partials into the canonical <target-artifact>.

Goal:
<One-paragraph goal statement. The orchestrator's job is to (a) enumerate work units, (b) dispatch one worker per unit, (c) wait for convergence, (d) merge partials, (e) emit the canonical artifact.>

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
<Filled by `scripts/sync-shared-blocks.sh`. After copying this template into `commands/`, run it once: it replaces every `<!-- shared:<name> -->` block with the current text of `commands/_shared/<name>.md`.>

Required inputs:
- <project workspace path>
- <enumeration source: file path, list, or query that produces the N work units>
- <optional: explicit max_fanout override (defaults to frontmatter value)>
- <optional: explicit timeout override>

Task repository files to update:
- <target canonical artifact> (sole owner of merged result per `wos/substrate-peers.md`)
- TASK_STATE.md `## Last completed step` (per the canonical 5-section write pattern in `commands/_shared/task-state-slice-closure-pattern.md`)

Operating rules:
- **Orchestrator bootstrap (before any worker dispatch):** read `commands/_shared/orchestrator-bootstrap.md` and apply it. It is read by path, not synced as a marker, because a marker placed before `Required inputs:` would be overwritten by the mandatory bootstrap sync.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- **Step 1: Enumerate work units.** Produce a list of N <work-unit> from the enumeration source. If N == 0, NO_OP_TRACE: nothing to dispatch.
- **Step 2: Verify max_fanout.** If N > `max_fanout`, split the work units into sequential sub-batches of at most `max_fanout` and continue, stating in one line how many batches the overflow produced. Never truncate silently, and do not stop for human input (ADR-0201).
- **Step 3: Verify tier guard.** Confirm orchestrator's `suggested-model` >= every declared worker tier per `wos/sub-agent-orchestration.md ## Tier-aware dispatch protocol`. If not, refuse to dispatch.
- **Step 4: Dispatch workers.** Invoke the host's stateless sub-agent primitive for each work unit (Claude Code `Agent` tool with `subagent_type: general-purpose`; a fork inherits the whole conversation and drops sub-agent input isolation, and lint fails an orchestrator that names no agent type). Pass `task_input` matching `worker_input_schema` and supply `worker_output_schema` as the return contract. Name the path you are on (ADR-0158 D-1). Resolve `<task_root>/.wos/fleet-inbox/<run_id>/<worker_id>.json` and create the run inbox before dispatch. On the dynamic-workflow path, declare `agent(prompt, {schema})` and consume the runtime's typed result; the orchestrator persists a JSON copy at that path. Never tell the worker to call StructuredOutput. On the `Agent` path, pass that resolved path as `fleet_inbox_artifact` outside `task_input` and require the worker to write its schema-conforming JSON there. End the dynamic prompt with `Return one payload matching worker_output_schema and nothing else`; end the native prompt with `Write one JSON payload matching worker_output_schema to fleet_inbox_artifact and nothing else`. Prose is not a return payload.
- **Step 5: Wait for convergence.** Per declared `convergence.pattern`:
  - `barrier`: wait for all N workers to complete OR `timeout_ms` to elapse.
  - `streaming`: process partials as they arrive; trigger merge after first one, then re-merge on each new partial.
- **Step 6: Handle partials.** Consume one payload per expected worker from the selected carrier: the runtime result or the assigned `<task_root>/.wos/fleet-inbox/<run_id>/<worker_id>.json`. Validate it against `worker_output_schema`; unrelated files and duplicate replay copies are not worker results. A missing or malformed payload is a contract violation, not success. Classify valid payloads by `status`:
  - `satisfied`: include in merge.
  - `needs_revision`: optionally re-dispatch once with revised input (single retry only); second `needs_revision` becomes `max_iterations_reached`.
  - `max_iterations_reached`: include partial in merge; flag the gap in synthesis.
  - `failed`: log `event=worker_failed`; do not retry unless `recoverable: true`.
  - `interrupted`: discard partial.
- **Step 7: Merge.** Apply declared `merge_strategy` to surviving partials. Produce single canonical artifact.
- **Step 8: Emit transaction headers + VERIFICATION_LOG.jsonl.** One transaction header per substrate section written; one `VERIFICATION_LOG.jsonl` line per merged section with `event=fleet-merge`, `partials=[...]`, `strategy=<chosen>`.
- **Step 9: Update TASK_STATE.md.** Per the canonical 5-section write pattern (`commands/_shared/task-state-slice-closure-pattern.md`).
- **Step 10: Clean fleet-inbox.** After merge, the orchestrator MAY leave partials in `active/<task>/.wos/fleet-inbox/<run_id>/` for audit; cleanup is the responsibility of `slice-closure` or `task-close`.
- Except for the assigned native return file, workers NEVER write substrate. The orchestrator is the SOLE writer of merged artifacts. The run-inbox exception grants no other write permission (ADR-0158 D-2).
- If the orchestrator itself violates the worker contract (e.g., dispatches a worker with `task_input` not matching `worker_input_schema`), the worker MUST refuse with `status: failed`, `error_class: contract-violation`.

Required output:
1. Enumeration summary: N work units identified
2. Dispatch summary: N workers dispatched, M satisfied, K needs_revision, L failed, P interrupted
3. Merge summary: which sections written, which strategy applied, conflicts encountered
4. Canonical artifact: path + sections updated
5. Recommended next command

### Claim grounding (active epistemic humility)
<!-- shared:claim-grounding -->
<Filled by `scripts/sync-shared-blocks.sh`.>

### Standard output layout (required)
<!-- shared:standard-output-layout -->
<Filled by `scripts/sync-shared-blocks.sh`.>

### Artifact changes
<!-- shared:artifact-changes-default -->
<Filled by `scripts/sync-shared-blocks.sh`.>

### Command transcript
<!-- shared:command-transcript-standard -->
<Filled by `scripts/sync-shared-blocks.sh`.>

### Handoff
<!-- shared:handoff-body -->
<Filled by `scripts/sync-shared-blocks.sh`.>

### Definition of done (command output)
- N work units enumerated and dispatched, in sequential sub-batches of at most `max_fanout` when N exceeds it (or NO_OP_TRACE if N == 0).
- All non-failed/non-interrupted partials merged per declared `merge_strategy`.
- Transaction headers emitted for every substrate section written.
- `VERIFICATION_LOG.jsonl` updated with one line per `event=fleet-merge`.
- TASK_STATE.md updated per the canonical 5-section write pattern.
- Worker contract violations (if any) explicitly listed in `### Command transcript`.
- Shared contract: **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The orchestrator is the only writer of substrate. The orchestrator is the only merger of partials. If the orchestrator cannot determine which section a partial maps to, it refuses to merge that partial and flags the ambiguity. Silent dropping is forbidden.
