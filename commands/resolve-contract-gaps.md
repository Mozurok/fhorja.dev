---
name: resolve-contract-gaps
description: Turn unresolved or contradictory behavior, contract, or policy gaps into one canonical implementation-safe decision set, then persist the result in DECISIONS.md and TASK_STATE.md as explicit reviewable proposals (not silent intent changes). Use when key ambiguities have already been identified, the task has enough facts to compare options safely, contradictory rules or assumptions or interpretations still exist, and planning cannot proceed safely until one canonical rule set is established. Do not use when the task is still missing basic factual context, the current need is broad discovery or impact analysis, or there are still unanswered decision questions that must be resolved first (use decision-interview).
metadata:
  category: contract-and-decision-hardening
  primary-cursor-mode: Plan
  multi-repo-aware: false
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [core, full]
  provenance: first-party
  token-budget: 2700
  suggested-model: claude-opus-4-7
---
# resolve-contract-gaps

Act as a senior/staff engineer resolving contract ambiguities for the active engineering task.

Goal:
Turn unresolved or contradictory behavior, contract, or policy gaps into one canonical, implementation-safe decision set, then persist the result in the task repository as explicit, reviewable proposals (not silent intent changes).

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
- DECISIONS.md, if available
- relevant real codebase context
- any explicit user answers to prior questions
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Do not reopen broad discovery unless strictly necessary for correctness.
- Before producing output, verify this is still the correct command based on `TASK_STATE.md` and whether contract gaps truly remain.
- If contract gaps are already resolved enough for safe planning, do not rewrite `DECISIONS.md` or churn `TASK_STATE.md`; return a no-op and route forward.
- No-op rule for artifacts:
  - If `DECISIONS.md` would not materially change, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Focus only on unresolved or contradictory contract/policy issues.
- For each issue:
  - explain the ambiguity
  - list viable options
  - explain trade-offs
  - recommend one canonical rule
  - state the exact implementation consequence
  - state the exact test consequence
- Produce a decision table when there are 2 or more entwined issues, when input/condition variations matter for runtime or data behavior, or whenever it would reduce interpretation risk; otherwise state explicitly why a table is not useful for this set of issues:
  - input condition -> action -> expected runtime / data effect
- Explicitly identify invariants and non-goals.
- Only record decisions in `DECISIONS.md` when they are explicitly approved by the user in-chat, already explicitly approved in authoritative artifacts, or are purely non-semantic editorial hardening that does not change meaning (rare). Otherwise, label proposals clearly and route to `contract-signoff` / user confirmation.

Required output:
1. Issues to resolve
2. Viable options per issue
3. Recommended canonical decision
4. Decision table (or an explicit one-line note explaining why a decision table is not useful for this set of issues)
5. Invariants
6. Non-goals
7. Exact DECISIONS.md content shown inline under its bullet in `### Artifact changes`. Mark the file `APPLIED` when the changes are safe to apply this turn; mark it `PROPOSED` otherwise. Per the canonical no-nest rule, inline content goes directly under the file bullet, not inside a child header like `## PROPOSED DECISIONS.md block`.
8. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
9. Remaining open questions, if any
10. Recommended next command
11. Recommended editor mode
12. Why this is the correct next step
13. What should explicitly not be done yet

TASK_STATE.md update must reflect:
- canonical decisions
- open blockers, if any remain
- recommended next step
- constraints / things that must not change
- risks to watch

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
- Each issue lists explicitly: viable options, trade-offs, recommended canonical rule, exact implementation consequence, exact test consequence. Recommending a decision without showing the alternatives considered is invalid output.
- Contradictions are resolved into one implementation-safe rule set with explicit consequences (code + tests).
- Semantic `DECISIONS.md` changes are `PROPOSED` unless explicit in-chat approval (or already authoritative).
- No silent drift: any ambiguity remains explicitly open with a routing next step.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends after the proposed `DECISIONS.md` content without a complete Handoff is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for clarity, unambiguity, implementation safety, and low downstream interpretation risk.

<!-- cache-breakpoint -->
