---
name: what-next
description: Determine the current stage of the active task and recommend the single best immediate next command, editor mode, and work complexity. Routes based on TASK_STATE.md, DECISIONS.md, and IMPLEMENTATION_PLAN.md without reopening broad discovery. Use when the user wants a fast operational answer for what to do next, when the task already has enough state to avoid rediscovery, and when the next step is not obvious from current artifacts. Do not use when the task is brand new (use task-init), when resuming after context loss (use resume-from-state), when the user wants a comparative explanation of multiple candidates, or when the task is stuck in a loop (use im-stuck).
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: []
  tools: [Read, Bash, Glob, Grep]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  token-budget: 2000
  suggested-model: claude-haiku-4-5
---
# what-next

Act as a senior/staff workflow orchestrator for the active engineering task.

Goal:
Determine the current stage of the task and recommend the best immediate next command and editor mode.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- active task folder path
- TASK_STATE.md
- key task artifacts if relevant
- current user request

Task repository files to update:
- none

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2 2026-06-04 -- dogfood).** MANDATORY for every write to `TASK_STATE.md ## Recommended next step` (what-next is the OWNER per `wos/substrate-peers.md`). Per `commands/_shared/substrate-write-protocol.md ## Concrete computation`:
  1. Compute `sha_before` via the canonical `sha_of_section` bash helper (typically NOT null: `## Recommended next step` was initially created by task-init).
  2. Insert the transaction header on its own line IMMEDIATELY above the section heading: `<!-- wos:write owner=what-next section='## Recommended next step' run_id=<ULID-or-uuid> ts=<ISO-8601-ms-with-Z> reason=route-<short-rationale> mode=applied -->`. REPLACE any prior owner header above this section (one header per section at any given time; prior write's header gets logged with event=overwrite).
  3. Write the section content (Command + Mode + Why per the canonical 3-field shape).
  4. Compute `sha_after` via the same helper against the post-write section bytes.
  5. Append exactly one JSON line to `active/<task>/.wos/VERIFICATION_LOG.jsonl` per the 12-field schema in `wos/substrate-peers.md ## Audit trail`. `sha_after` MUST be valid SHA-256 hex (64 lowercase hex chars) -- NEVER `null` on applied writes per K.5 validator.
  6. When NO active task is present (e.g. immediately after `task-close`), what-next operates at project level: no substrate write happens; emit a NO_OP_TRACE line in `### Command transcript` and skip steps 1-5 entirely. K.4 drift-guard does not flag the no-op case.

  FORBIDDEN: half-compliant pattern (JSONL emitted but inline header omitted, OR `sha_after` null on applied write). K.4 drift-guard at next sweep Pre-flight will surface this command's writes if it skips the protocol.
- Do not reopen broad discovery unless clearly necessary.
- **Proactively offer the Express tier when its criteria are met (ADR-0025):** even when `## Recommended pipeline` in TASK_STATE.md already names a heavier tier, re-check the Express bar against the current known scope (describable in one sentence, all decisions already provided, fewer than 5 files affected). If the task now qualifies, name Express as the recommended next command sequence (`implementation-plan` -> `implement-approved-slice` -> `branch-commit`, skipping `impact-analysis` and `decision-interview`) rather than only applying it when the user separately asks for a faster path.
- Infer the current workflow stage from the latest task artifacts and unresolved gaps.
- Decide whether the task is currently in:
  - discovery
  - planning
  - contract refinement
  - contract signoff
  - test design
  - implementation
  - review
  - debug
  - delivery
- Recommend:
  1. the best next command
  2. the best editor mode
  3. **work complexity** (`LOW` | `MEDIUM` | `HIGH` | `N/A`) for that next step (definitions in `WORKFLOW_OPERATING_SYSTEM.md`; never name model SKUs)
  4. why this is the right next step
  5. what should explicitly not be done yet
- If there are 2 reasonable next steps, rank them.
- **Waves-aware routing (ADR-0042, stated verbatim wherever execution is routed):** when the active task has an approved plan and the first remaining `## Execution waves` entry has size 2 or more whose slices declare `Scope` and `Depends-on`, recommend `implement-fleet` for that wave; otherwise recommend `implement-approved-slice` for the next slice. Do not default to sequential execution when a parallelizable wave is ready (this is the gap that left the fleet unreachable from `what-next` and forced the operator to ask for parallelism).
- **Task-delivered handoff:** when the current task phase is "delivered" (all slices complete, committed/pushed) and the next action is a new task, include a ready-to-paste `task-init` prompt in the handoff body with project, task_slug, and summary pre-filled from the product spec or user context. This eliminates the "pode me retornar o prompt do task-init" round-trip.

Required output:
1. Current stage
2. What is already done
3. What is still missing
4. Recommended next command
5. Recommended mode
6. Recommended work complexity (`LOW` | `MEDIUM` | `HIGH` | `N/A`) and one-line justification
7. Why this is the best next step
8. Alternative next step, if relevant
9. What to avoid doing now

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
- Exactly one primary next command is recommended (fallback only if truly necessary).
- The recommendation matches the current phase and blockers in `TASK_STATE.md`.
- `### Artifact changes` is `None` unless there is a real reason to persist a change now.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Be practical, sequential, and workflow-aware. Optimize for reducing ambiguity and avoiding premature implementation.

<!-- cache-breakpoint -->
