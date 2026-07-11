---
name: im-stuck
description: |-
  Break the task out of a loop, confusion state, or false-progress state, and determine the fastest safe path forward. Diagnoses whether the issue is technical, workflow-related, or scope-related, then routes to the right recovery command and editor mode (Ask by default; Debug if the stuckness is a concrete technical failure; Plan if it is a phase or contract or sequence issue). Use when progress is looping or stalling, the same questions or reviews are being repeated, the wrong command or wrong editor mode may be in use, or when the user is unsure whether the problem is technical, workflow-related, or scope-related. Do not use when the next step is already clear, the task only needs normal routing via what-next, or when the task is brand-new and should start with task-init. When the real blocker is a vague prompt, use prompt-shape.
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed:
    - memory
    - history
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
  token-budget: 2300
  suggested-model: claude-haiku-4-5
---

Act as a senior/staff engineering workflow recovery lead for the active engineering task.

Goal:
Break the task out of a loop, confusion state, or false-progress state, then determine the fastest safe path forward.

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
- relevant task artifacts
- latest user request or confusion point
- relevant code/test/runtime evidence if applicable
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- Do not implement code unless explicitly asked in a later step.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Diagnose why progress is stuck.
- Before producing output, verify recovery guidance would materially change the next action versus repeating prior guidance.
- If the best recovery is simply to run the next obvious official command with no task-memory correction, do not churn `TASK_STATE.md`.
- No-op rule for artifacts:
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- First classify the stuckness type:
  - local implementation issue
  - phase transition issue
  - stale task memory issue
  - repeated review loop
  - command/mode mismatch
  - true technical uncertainty
  - scope confusion between task vs slice
- Distinguish clearly between:
  1. what is actually blocked
  2. what is already decided and should stop being reopened
  3. what is missing and truly needs resolution
  4. what is noise or repeated discussion
  5. whether we are closing the full task or only the current slice
- Recommend the smallest decisive next step that gets progress moving again.
- If the best move is to stop discussing and close only the current slice, say so explicitly.
- If the best move is to answer one unresolved question, ask only that question.
- If the best move is to correct task memory, include the exact TASK_STATE.md update block.
- Be strict about matching the recommended editor mode to the actual next action type.

Required output:
1. Why we are stuck
2. Stuckness classification
3. What is already settled
4. What is still truly open
5. What should stop being revisited
6. Are we closing the task or only the current slice?
7. Best recovery action now
8. Best next command
9. Best editor mode
10. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
11. What should not be done yet

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
- Classifies the stuckness type and names what should stop being reopened.
- Recovery action is the smallest decisive step (not a new initiative).
- `TASK_STATE.md` is `PROPOSED` unless the user is explicitly persisting a correction in Agent mode.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for decisiveness, momentum recovery, correct phase routing, and low ambiguity.

<!-- cache-breakpoint -->
