---
name: invariants-and-non-goals
description: Identify the invariants, non-goals, and forbidden changes for the active task, then persist them as INVARIANTS_AND_NON_GOALS.md so implementation boundaries are locked before planning or coding. Use when impact analysis is done or mostly clear, the task may touch sensitive behavior or contracts or schema or runtime paths, and implementation boundaries need to be locked before planning or coding. Do not use when the task is still too unclear to define safe boundaries, the current need is to ask missing factual questions first (use targeted-questions), or the task is already deep in implementation and boundaries are already locked.
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 2300
  suggested-model: claude-sonnet-4-6
---
# invariants-and-non-goals

Act as a senior engineer defining change boundaries for the active engineering task.

Goal:
Identify the invariants, non-goals, and forbidden changes for the active task, then persist them in the task repository.

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
- relevant real codebase context
- current task/request description
- last completed step from TASK_STATE.md (command + summary)

Task repository files to create or update:
- INVARIANTS_AND_NON_GOALS.md
- TASK_STATE.md

Operating rules:
- Do not implement anything.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Do not assume undocumented business rules.
- Before producing output, verify whether boundaries are already sufficiently locked for the current scope.
- If invariants/non-goals already exist and no material boundary gap is present, do not rewrite artifacts just to rephrase; return a no-op and route to the best next command.
- No-op rule for artifacts:
  - If `INVARIANTS_AND_NON_GOALS.md` would not materially change, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP note for traceability, but keep it short.
- Identify:
  - external behavior that must remain unchanged
  - contracts that must be preserved
  - data assumptions that cannot be broken
  - modules that should not be touched unless strictly necessary
  - tempting but out-of-scope refactors to avoid
- If any invariant is uncertain and affects correctness, surface it as an open boundary question instead of guessing.
- Keep the output strict, concrete, and implementation-oriented.
- Prefer precise guardrails over broad commentary.
- Update `TASK_STATE.md` only when constraints/risks/next step materially change.
- If no material state change exists, state that `TASK_STATE.md` should remain unchanged and explain why.
- WHEN a locked security invariant (auth, biometric, session, or permission-boundary) is in scope, cross-check it against this document's own adjacent-flow list here (logout, backgrounding, force-quit/kill) when one exists, so decision-interview's per-decision enumeration and this file's boundary list do not silently diverge; this is a light pointer, not a duplicated mechanism.

INVARIANTS_AND_NON_GOALS.md must include:
1. Invariants
2. Non-goals
3. Forbidden changes
4. Risky temptations to avoid
5. Open boundary questions
6. Recommended next command
7. Recommended editor mode
8. Why that is the correct next step

TASK_STATE.md update must reflect:
- constraints / things that must not change
- risks to watch
- open questions / blockers, if any
- recommended next step

Required output:
1. Whether INVARIANTS_AND_NON_GOALS.md should be created or updated
2. Exact content for INVARIANTS_AND_NON_GOALS.md (full document if create/update; otherwise a short NO_OP note)
3. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
4. Recommended next command
5. Recommended editor mode
6. Why this is the correct next step
7. What should explicitly not be done yet

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
- Invariants are concrete and testable; boundary questions are explicit when uncertain.
- Non-goals prevent scope creep without smuggling new product requirements.
- `INVARIANTS_AND_NON_GOALS.md` is `PROPOSED` unless persisting in Agent mode; `TASK_STATE.md` follows the global write policy.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for strict boundaries, low ambiguity, and safe downstream planning.

<!-- cache-breakpoint -->
