---
name: resume-from-state
description: Resume the task from TASK_STATE.md and linked task artifacts, reconstruct the current truth, and determine the best next step. Used to bring back full task context after a session break or chat switch. Use when work is resuming in a new chat or session, the task was paused and needs fast reconstruction, or the user wants to continue without rereading the whole history. Do not use when this is a brand-new task that has not been initialized (use task-init), the current need is only to sync task memory after new progress (use sync-task-state), or the task state is obviously stale or contradictory across artifacts and must first be corrected (use sync-task-state for narrow drift, or state-reconcile when drift is wide).
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, history]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 2000
  suggested-model: claude-haiku-4-5
---
# resume-from-state

Act as a senior/staff engineer resuming work from task memory for the active engineering task.

Goal:
Resume the task from TASK_STATE.md and linked task artifacts, reconstruct the current truth, and determine the best next step.

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
- SOURCE_OF_TRUTH.md
- DECISIONS.md
- IMPLEMENTATION_PLAN.md
- other relevant task artifacts if present

Task repository files to update:
- none by default
- recommend sync-task-state explicitly if the state is stale, contradictory, or incomplete

Operating rules:
- Do not implement code yet.
- **Workspace path resolution (before reading any files):** the task folder (under `projects/<client>__<project>/active/...`) may live in a Fhorja/task-memory repo that is separate from the product codebase. Before reading product code or assuming file locations:
  1. Read `SOURCE_OF_TRUTH.md` in the task folder for `## Product workspace` or `## Repositories` paths.
  2. If those are absent, read `PROJECT_CHARTER.md` two levels up from the task folder for `## Default workspace` or `## Repositories`.
  3. Read task artifacts (TASK_STATE.md, DECISIONS.md, IMPLEMENTATION_PLAN.md, SLICES/) from the task folder in the Fhorja repo. Read product code from the resolved workspace path. Never assume the two share the same root.
  4. If neither source yields a workspace path and the task references product code, ask the user for the workspace path (one targeted question) instead of failing with file-not-found errors.
- **Archived task path (ADR-0105):** WHEN the given task path resolves under `archive/` (or the legacy `done/`) instead of `active/`, do not fail. Route to `task-close`'s reopen mode first (the folder moves back to `active/` and the final state is reset), then resume normally from the reopened state.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Context-rot guardrail (ADR-0023):** before producing the output, estimate the current TASK_STATE.md token count (excluding the `## Compaction history` section). Compare against the phase threshold from `wos/context-budget.md ## Context-rot thresholds` (discovery: 3000; planning: 5000; implementation: 8000; review/closure/delivery: 6000). If current count exceeds the threshold, emit a single-line warning in `### Command transcript`: `WARN: TASK_STATE.md is ~Ntokens (phase threshold: Mthreshold). Consider running compact-task-memory before continuing.` The warning is INFORMATIONAL; proceed with the normal output. Suppress the warning if the immediately prior step was `compact-task-memory`.
- Treat TASK_STATE.md as the operational memory for the task.
- Treat linked plan/decision/test artifacts as the current source of truth.
- Reconstruct:
  - what has already been done
  - what decisions are locked
  - which phase the task is in
  - what remains
  - **work complexity** for the next step (`TASK_STATE.md` section if present; otherwise infer using `WORKFLOW_OPERATING_SYSTEM.md` definitions; never name model SKUs)
- If TASK_STATE.md is missing, stale, or contradictory, say so explicitly.
- If artifacts disagree, identify the conflict clearly and recommend the smallest corrective next step.
- Avoid broad rediscovery unless the saved state is not trustworthy enough to continue safely.

Required output:
1. Current phase
2. Confirmed source of truth
3. What is completed
4. What is still pending
5. Any stale or conflicting state
6. Recommended next command
7. Recommended editor mode
8. Recommended work complexity (`LOW` | `MEDIUM` | `HIGH` | `N/A`) for that next step
9. Why this is the correct next step
10. What should explicitly not be done yet

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
- Reconstruction is grounded in `TASK_STATE.md` plus linked artifacts (no broad rediscovery).
- Conflicts are surfaced with the smallest corrective next step.
- `### Artifact changes` is `None` unless a correction must be persisted (then justify why not `sync-task-state`).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for fast, correct resumption with minimal ambiguity and minimal repeated analysis.

<!-- cache-breakpoint -->
