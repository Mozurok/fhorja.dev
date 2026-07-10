---
name: contract-signoff
description: |-
  Harden the current decision set into a clean, normative source of truth with no residual ambiguity, then persist the result in DECISIONS.md and TASK_STATE.md as explicit reviewable edits (no silent intent drift). Use when key decisions are already resolved, the task has a stable contract or policy direction, and the remaining work is to harden wording and remove interpretation risk before planning or implementation. Do not use when major ambiguities remain unresolved, the task still needs decision-interview or resolve-contract-gaps, or the task is still in broad discovery.
metadata:
  category: contract-and-decision-hardening
  primary-cursor-mode: Plan
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
  token-budget: 2500
  suggested-model: claude-opus-4-7
---

Act as a senior/staff engineer finalizing the implementation contract for the active engineering task.

Goal:
Harden the current decision set into a clean, normative source of truth with no residual ambiguity, then persist the result in the task repository as explicit, reviewable edits (no silent intent drift).

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
- relevant real codebase context
- prior analysis artifacts, if relevant
- last completed step from TASK_STATE.md (command + summary)

Operating rules:
- Do not implement code.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- Do not reopen broad discovery.
- Before producing output, verify that remaining work is truly wording/normalization rather than unresolved policy choice.
- If `DECISIONS.md` is already normative enough for safe planning, do not rewrite it for style; return a no-op and route forward.
- No-op rule for artifacts:
  - If `DECISIONS.md` would not materially change, do not rewrite it.
  - If `TASK_STATE.md` would not materially change, do not rewrite it.
  - Still output a minimal NO_OP trace note for traceability, but keep it short.
- Do not change already approved canonical decisions unless a direct contradiction still exists.
- Focus on:
  - removing ambiguous wording
  - replacing assumption language with canonical policy language
  - separating historical analysis from active rules
  - ensuring one policy voice across the document
- If any residual contradiction remains, call it out explicitly instead of silently rewriting intent.
- Keep DECISIONS.md normative, concise, and implementation-safe.
- Only apply semantic changes to `DECISIONS.md` when they are explicitly approved by the user in-chat or required to resolve a direct contradiction with evidence. Otherwise keep changes strictly editorial and reversible, or route back to `resolve-contract-gaps` / `decision-interview`.

Required output:
1. Residual ambiguities found
2. Exact wording changes recommended
3. Sections that are historical context only, if any
4. Sections that are normative / implementation source of truth
5. Exact DECISIONS.md content shown inline under its bullet in `### Artifact changes`. Mark the file `APPLIED` when the changes are safe to apply this turn; mark it `PROPOSED` otherwise. Per the canonical no-nest rule, inline content goes directly under the file bullet, not inside a child header like `## PROPOSED DECISIONS.md block`.
6. Exact TASK_STATE.md update block, or explicit `TASK_STATE: NO_CHANGE`
7. Final signoff assessment (one of `READY` / `NOT_READY` / `BLOCKED` plus a one-line reason)
8. Remaining blockers, if any
9. Recommended next command
10. Recommended editor mode
11. Why this is the correct next step
12. What should explicitly not be done yet

TASK_STATE.md update must reflect:
- canonical decisions
- current phase
- remaining blockers, if any
- recommended next step

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
- Wording changes are non-semantic unless explicitly justified; contradictions are called out, not smoothed away.
- Each wording change is shown explicitly as a current → proposed pair with a one-line rationale; rewriting `DECISIONS.md` wholesale without showing the diff is silent intent drift and invalid output.
- `DECISIONS.md` ends normative, concise, and internally consistent.
- Anything historical is isolated from active rules.
- Output includes an explicit `Final signoff assessment` with one of `READY` / `NOT_READY` / `BLOCKED` plus a one-line reason; emitting the updated `DECISIONS.md` without an explicit signoff verdict is invalid output.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. A response that ends after the proposed `DECISIONS.md` content or after the signoff assessment without a complete Handoff is invalid output.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for unambiguity, consistency, and implementation-readiness.

<!-- cache-breakpoint -->
