---
name: <kebab-case-orchestrator-name>
description: <Use when ... Do not use when ...> Dispatches N <worker-role> sub-agents per the worker contract; merges partials into <target-artifact>.
metadata:
  category: <discovery-and-scoping | planning-and-validation | execution-and-closure | state-and-navigation>
  primary-cursor-mode: <Ask | Plan | Agent>
  multi-repo-aware: <true | false>
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  token-budget: <integer>
  suggested-model: claude-opus-4-7
  orchestrator: true
  workers:
    - role: <worker-role-slug>
      tier: claude-sonnet-4-6
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
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Orchestrator bootstrap (before any worker dispatch):
<!-- shared:orchestrator-bootstrap -->

Required inputs:
- <project workspace path>
- <enumeration source: file path, list, or query that produces the N work units>
- <optional: explicit max_fanout override (defaults to frontmatter value)>
- <optional: explicit timeout override>

Task repository files to update:
- <target canonical artifact> (sole owner of merged result per `wos/substrate-peers.md`)
- TASK_STATE.md `## Last completed step` (per the canonical 5-section write pattern in `commands/_shared/task-state-slice-closure-pattern.md`)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- **Step 1: Enumerate work units.** Produce a list of N <work-unit> from the enumeration source. If N == 0, NO_OP_TRACE: nothing to dispatch.
- **Step 2: Verify max_fanout.** If N > `max_fanout`, STOP with NO_OP_TRACE listing the overflow. Do not silently truncate.
- **Step 3: Verify tier guard.** Confirm orchestrator's `suggested-model` >= every declared worker tier per `wos/sub-agent-orchestration.md ## Tier-aware dispatch protocol`. If not, refuse to dispatch.
- **Step 4: Dispatch workers.** For each work unit, invoke the host's stateless sub-agent primitive (Claude Code `Task` tool with `subagent_type: general-purpose`; Cursor agent mode; Codex agents). Pass `task_input` matching `worker_input_schema`. Each worker MUST return its result via the `StructuredOutput` tool keyed `artifact=fleet-inbox/<run_id>/<worker_id>` (ADR-0038 Rule 1; prose `.partial.md` returns FORBIDDEN, a typed `.partial.json` is replay-only) per the worker contract.
- **Step 5: Wait for convergence.** Per declared `convergence.pattern`:
  - `barrier`: wait for all N workers to complete OR `timeout_ms` to elapse.
  - `streaming`: process partials as they arrive; trigger merge after first one, then re-merge on each new partial.
- **Step 6: Handle partials.** Read all files in `active/<task>/.wos/fleet-inbox/<run_id>/`. For each, parse YAML header and body per worker contract. Classify by `status`:
  - `satisfied`: include in merge.
  - `needs_revision`: optionally re-dispatch once with revised input (single retry only); second `needs_revision` becomes `max_iterations_reached`.
  - `max_iterations_reached`: include partial in merge; flag the gap in synthesis.
  - `failed`: log `event=worker_failed`; do not retry unless `recoverable: true`.
  - `interrupted`: discard partial.
- **Step 7: Merge.** Apply declared `merge_strategy` to surviving partials. Produce single canonical artifact.
- **Step 8: Emit transaction headers + VERIFICATION_LOG.jsonl.** One transaction header per substrate section written; one `VERIFICATION_LOG.jsonl` line per merged section with `event=fleet-merge`, `partials=[...]`, `strategy=<chosen>`.
- **Step 9: Update TASK_STATE.md.** Per the canonical 5-section write pattern (`commands/_shared/task-state-slice-closure-pattern.md`).
- **Step 10: Clean fleet-inbox.** After merge, the orchestrator MAY leave partials in `active/<task>/.wos/fleet-inbox/<run_id>/` for audit; cleanup is the responsibility of `slice-closure` or `task-close`.
- Workers NEVER write substrate. The orchestrator is the SOLE writer.
- If the orchestrator itself violates the worker contract (e.g., dispatches a worker with `task_input` not matching `worker_input_schema`), the worker MUST refuse with `status: failed`, `error_class: contract-violation`.

Required output:
1. Enumeration summary: N work units identified
2. Dispatch summary: N workers dispatched, M satisfied, K needs_revision, L failed, P interrupted
3. Merge summary: which sections written, which strategy applied, conflicts encountered
4. Canonical artifact: path + sections updated
5. Recommended next command

### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- N work units enumerated and dispatched (or NO_OP_TRACE if N == 0 or N > max_fanout).
- All non-failed/non-interrupted partials merged per declared `merge_strategy`.
- Transaction headers emitted for every substrate section written.
- `VERIFICATION_LOG.jsonl` updated with one line per `event=fleet-merge`.
- TASK_STATE.md updated per the canonical 5-section write pattern.
- Worker contract violations (if any) explicitly listed in `### Command transcript`.
- Shared contract: **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The orchestrator is the only writer of substrate. The orchestrator is the only merger of partials. If the orchestrator cannot determine which section a partial maps to, it refuses to merge that partial and flags the ambiguity. Silent dropping is forbidden.

<!-- cache-breakpoint -->
