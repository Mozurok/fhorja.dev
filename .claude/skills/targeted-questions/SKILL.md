---
name: targeted-questions
description: |-
  Ask the minimum set of high-value factual questions needed to proceed safely, then persist the result in the task repository. Distinct from decision-interview (factual gaps, not decision-driven gaps). Use when impact analysis or boundary definition revealed missing facts, correctness depends on information that is not yet confirmed, or the task cannot safely move into planning or implementation without clarification. Do not use when the main problem is missing policy or behavioral decisions rather than missing facts (use decision-interview), enough information already exists to move safely into planning, or the task is already in implementation and the missing information is not correctness-critical.
metadata:
  category: discovery-and-scoping
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
  token-budget: 2400
  suggested-model: claude-sonnet-4-6
---

Act as a senior engineer reducing uncertainty for the active engineering task.

Goal:
Ask the minimum set of high-value factual questions needed to proceed safely, then persist the result in the task repository.

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
- IMPACT_ANALYSIS.md, if available
- INVARIANTS_AND_NON_GOALS.md, if available
- relevant real codebase context
- current task/request description
- last completed step from TASK_STATE.md (command + summary)

Task repository files to update:
- TASK_STATE.md
- DECISIONS.md only if some question is already resolved by explicit evidence or user input

Operating rules:
- Do not implement anything.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Do not ask broad or redundant questions.
- **No human respondent (unattended, background, or fleet-dispatched run, per ADR-0044 doctrine):** this command SHALL NOT self-answer. Record each open factual question with its candidate assumption as an inline `[NEEDS CLARIFICATION: <question>]` marker (or a PROPOSED block when an artifact must carry the assumption), note in `### Command transcript` that the run was unattended, and stall or escalate to the next human session. An agent-invented "fact" recorded as confirmed is a contract violation. An answer a human pre-supplied in the dispatching brief IS user input, recorded with the provenance note "from the dispatching brief" (per `wos/cross-cutting-workflow-guardrails.md ### Unattended sessions`); only the questions the brief leaves open stall.
- Before producing output, check whether factual gaps still exist and whether this command is still necessary based on latest artifacts and last completed step.
- If factual uncertainty is already low enough to proceed safely, do not generate filler questions; return a no-op and route to the best next command.
- No-op rule for artifacts:
  - If there are no new questions and no new confirmed facts to record, do not churn `TASK_STATE.md` or `DECISIONS.md`.
  - Still output a minimal NO_OP note for traceability, but keep it short.
- Do not ask questions that do not materially affect correctness, scope, testing, rollout, or runtime behavior.
- Distinguish clearly between:
  1. what is already confirmed
  2. what is still missing
  3. what can proceed safely now
  4. what must wait for answers
- If the answer can be grounded from code, tests, docs, or explicit task artifacts, do not ask the user.
- Group questions by category only when useful:
  - business rule
  - contract / payload
  - schema / data
  - runtime behavior
  - tests
  - rollout / operations
- Prefer fewer, higher-value questions over exhaustive question lists.
- If enough information already exists, say that no more questions are needed.
- Update `TASK_STATE.md` only when open blockers/facts/next step materially change.
- If no material state change exists, state that `TASK_STATE.md` should remain unchanged and explain why.

Required output:
1. Why the current context is sufficient or insufficient
2. Targeted questions
3. What can already be decided safely
4. What must wait for answers
5. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
6. Exact DECISIONS.md update block, or explicit "no DECISIONS.md changes needed"
7. Recommended next command
8. Recommended editor mode
9. Why this is the correct next step
10. What should explicitly not be done yet

TASK_STATE.md update must reflect:
- open questions / blockers
- current known facts, if clarified
- recommended next step
- risks to watch, if relevant

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
- Minimum question set: each question materially affects correctness, scope, validation, rollout, or runtime behavior.
- No questions answerable from existing evidence without user input.
- `DECISIONS.md` updates are rare and only for evidence-backed resolutions; otherwise `PROPOSED` only.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for minimal question count, high signal, and low ambiguity.

<!-- cache-breakpoint -->
