---
name: direction-adjust
description: |-
  Capture a small-to-medium course correction the user realized mid-task (not from external review), record it as a numbered D-N entry in DECISIONS.md, update TASK_STATE.md to reflect the adjusted direction, and route back to the appropriate command. Use when you are mid-task (any phase past discovery) and realize the direction needs adjustment, the realization came from your own work (not external review), the change is meaningful enough to record but does not invalidate the whole approach, and the existing slice or phase is recoverable with a small change of plan. Do not use when the trigger is external review or PR feedback (use pr-feedback-ingest or post-review-pivot), the realization invalidates the entire task scope (use task-init for a new task), the adjustment is too small to record (use capture-observation), the realization is loop or confusion (use im-stuck), the adjustment requires reopening locked decisions (use decision-interview), or no active task folder exists yet.
metadata:
  category: contract-and-decision-hardening
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed:
    - memory
  context-layers-produced:
    - memory
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
  x-wos-profiles:
    - core
    - full
  provenance: first-party
  token-budget: 3200
  suggested-model: claude-sonnet-4-6
---

Act as a senior/staff engineering direction adjustment for the active engineering task.

Goal:
Capture a small-to-medium course correction that the user realized mid-task (not from external review), record it as a decision in `DECISIONS.md`, update `TASK_STATE.md` to reflect the adjusted direction, and route back to the appropriate command to continue the work.

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
- TASK_STATE.md (must reflect current phase and last completed step)
- DECISIONS.md (current canonical decisions)
- IMPLEMENTATION_PLAN.md (current plan that is being adjusted)
- the user's description of the realization: what was being done, what was noticed, what should change
- optional: which slice or phase the adjustment affects

Task repository files to update:
- DECISIONS.md (append a new decision recording the adjustment with a `D-N: mid-task adjustment` prefix)
- TASK_STATE.md (update `Last completed step` if it is now wrong, update `Recommended next step` to reflect the adjusted direction, update `Risks to watch` if the adjustment introduces new risk)
- IMPLEMENTATION_PLAN.md (only if the adjustment changes plan text; default is to leave plan as-is and note the adjustment in `DECISIONS.md`)
- relevant SLICES/*.md (only if the active slice scope must change to reflect the adjustment)

Operating rules:
- Do not implement production code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Substrate write protocol (per ADR-0034, K.2).** MANDATORY for every substrate section this command writes (the `DECISIONS.md` section receiving the new D-N entry, e.g. `## Mid-task adjustments`, and each updated `TASK_STATE.md` section). Follow `commands/_shared/substrate-write-protocol.md`: emit the `<!-- wos:write owner=direction-adjust section='## X' ... -->` transaction header and append one JSONL line per section write to `active/<task>/.wos/VERIFICATION_LOG.jsonl`. Header placement per `commands/_shared/substrate-write-protocol.md ## Transaction header`: the transaction header goes on its own line IMMEDIATELY above the `## <section>` heading line. NEVER place it below the heading, and NEVER above a `### D-N` entry inside the section; a header placed below the heading leaves the section counted as header-less by the K.4 drift scan (`scripts/scan-substrate-headers.sh`), which checks only the line immediately preceding each `## ` heading.
- Treat the adjustment as a new decision, not a silent edit. The output must produce a numbered entry (`D-N`) for `DECISIONS.md`.
- Make the adjustment auditable: clearly show what direction was being followed before, what changed, and why.
- Validate the adjustment against existing locked decisions and invariants. If the adjustment contradicts a locked decision, surface this explicitly and route to `decision-interview` instead of silently overwriting.
- Validate the adjustment against `INVARIANTS_AND_NON_GOALS.md` if present. If the adjustment crosses a non-goal or invalidates an invariant, surface this and require user confirmation before proceeding.
- Keep the new `DECISIONS.md` entry concise: 2-5 lines covering what changed and why.
- Update `TASK_STATE.md` minimally: only fields actually affected by the adjustment. Do not rewrite unrelated sections.
- If the adjustment requires re-planning (the slice scope is now wrong, or the slice order needs to change), the recommended next command must be `implementation-plan` or `state-reconcile`, not blind continuation.
- If the adjustment is small enough that the current slice can absorb it without re-planning, the recommended next command is the slice-execution command appropriate to the phase (typically `implement-approved-slice`).
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask/Plan mode, `APPLIED` only in Agent mode.

Required output:
1. Summary of the adjustment in plain language: "before, the direction was X; now, the direction is Y; the trigger was Z".
2. The new `DECISIONS.md` entry to append, formatted as `D-N: mid-task adjustment - <one-line title>` followed by 2-5 lines of detail.
3. The updated fields in `TASK_STATE.md` (only the fields that actually change).
4. The validation result against locked decisions: `compatible`, `requires decision-interview`, or `violates invariant: <which one>`.
5. The recommended next command, with reasoning about whether the adjustment requires re-planning or fits the current slice.
6. Recommended editor mode for that next command.
7. Recommended work complexity (`LOW` | `MEDIUM` | `HIGH` | `N/A`) for the next step.

### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
- List files in `my_work_tasks/` that would change, or `None`.
- For each file, mark `APPLIED` / `PROPOSED` / `SKIP` and follow the task-memory write policy in `WORKFLOW_OPERATING_SYSTEM.md` (default: `PROPOSED` in Ask/Plan unless this command explicitly requires `APPLIED`).
- Default for this command: `PROPOSED` patches on `DECISIONS.md` and `TASK_STATE.md`; conditionally on `IMPLEMENTATION_PLAN.md` or `SLICES/*.md` only when the adjustment requires it.

### Command transcript
- Keep this section operational and brief; do not restate file content already listed in `### Artifact changes`.
- Max 4 lines in normal runs.
- Max 3 lines in no-op runs (including `NO_OP_TRACE`).
- Include `NO_OP_TRACE` (1-3 lines) if the realization is too small to record as a decision (route to `capture-observation` instead) or if the adjustment turns out to require a heavier path (route to `decision-interview` or `state-reconcile`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- The adjustment is recorded as a numbered `D-N: mid-task adjustment` entry in `DECISIONS.md` with concise reasoning.
- Every substrate write carries its `wos:write` transaction header on its own line IMMEDIATELY above the `## <section>` heading, never below the heading and never above a `### D-N` entry inside the section, per `commands/_shared/substrate-write-protocol.md ## Transaction header`.
- `TASK_STATE.md` updates are minimal and target only fields affected by the adjustment.
- Validation against locked decisions and invariants is explicit; the output names any conflict and routes to a heavier command rather than silently overwriting.
- The adjustment never overrides locked decisions in place. Conflicts route to `decision-interview`.
- The adjustment never violates invariants or crosses non-goals silently. Conflicts surface for user confirmation.
- `Artifact changes` marks each patch as `PROPOSED` in Ask/Plan mode or `APPLIED` only when explicitly in Agent.
- `Handoff` block is complete with all five fields non-empty; ending after the decision entry without a Handoff is invalid output.
- The recommended next command is appropriate to the size of adjustment: small adjustments resume current slice; medium adjustments trigger `implementation-plan` or `state-reconcile`; conflicts trigger `decision-interview`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for auditability of the direction change, protection of locked decisions and invariants, minimal disruption to in-progress work, and clear routing to the right next step based on the size of the adjustment.

<!-- cache-breakpoint -->
