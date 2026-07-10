---
name: workflow-guide
description: Pedagogical onboarding helper that explains which command and editor mode should be used now, why, and the next 2-3 steps in a practical way for users still learning the workflow phases. Heavier than what-next; the heavier sequence is justified only when the user wants to understand the workflow, not just the next command. Use when the user wants a more guided explanation of the current moment, the user wants to understand the workflow rather than just the next command, a short recommended sequence for the next few steps would be useful, or the user is new to this workflow (first few sessions) or onboarding a teammate. Do not use when the user only wants a fast next-step answer (use what-next; same routing decision, lower overhead), the user is already fluent in the workflow phases (what-next is the right default), or the task is stuck and needs im-stuck instead.
metadata:
  category: state-and-navigation
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: []
  tools: [Read, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 2000
  suggested-model: claude-haiku-4-5
---
# workflow-guide

Act as a senior/staff engineering workflow coach for the active engineering task.

Goal:
Explain which command and editor mode should be used now, and why, in a practical way.

Audience and scope:
- This command is positioned as a **teaching/onboarding helper** for users who are still learning the workflow phases. Experienced users should default to `what-next` (single answer, lower overhead). The pedagogical "current phase + next 2-3 steps" sequence here is intentionally heavier than `what-next` and is justified only when the user wants to understand the workflow, not just the next command.

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
- relevant task artifacts
- current user request
- last completed step from TASK_STATE.md (command + summary)

Task repository files to update:
- none

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Before producing output, verify the guidance would materially change the user's next action versus what is already obvious from `TASK_STATE.md`.
- If guidance would be redundant, return a no-op and route to `what-next` or the best single next command instead of repeating the workflow essay.
- No-op trace rule:
  - If redundant, emit a short NO_OP trace note, then recommend the best next command.
- Explain:
  - which workflow phase the task is in
  - which command is most appropriate now
  - which editor mode fits best
  - why nearby modes are less appropriate
- If useful, provide a short recommended sequence for the next 2-3 steps.
- Keep the explanation practical, concise, and task-oriented.

Required output:
1. Current phase
2. Best command to use now
3. Best mode to use now
4. Why this choice fits
5. What would be premature
6. Next 2-3 steps

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
- Explains phase + why the mode fits (without turning into hidden routing).
- Provides a short 2-3 step sequence only when it adds clarity.
- `### Artifact changes` is `None`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Be concise, educational, and specific to the current task state.

<!-- cache-breakpoint -->
