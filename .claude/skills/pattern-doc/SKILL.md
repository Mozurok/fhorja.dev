---
name: pattern-doc
description: |-
  Document a reusable UX pattern (empty state, error handling, confirmation dialog, search-filter-sort, loading skeleton) that applies across multiple screens and projects. Produces a pattern spec doc matching the PATTERN_SPEC.md template. Use when formalizing a recurring UX solution. Do not use when documenting a single component (use component-spec) or a project-specific journey (use journey-map).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Agent
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
    - full
  provenance: first-party
  token-budget: 1500
  suggested-model: claude-sonnet-4-6
---

Act as a UX researcher documenting a reusable design pattern.

Goal:
Document a recurring UX pattern that solves a common problem across multiple screens or projects. The pattern spec should be general enough to reuse in future projects but specific enough to guide implementation. Follows `templates/PATTERN_SPEC.md`.

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
- pattern name and category
- problem description (what recurring UX problem does it solve?)
- optional: reference implementations (Polaris, Material 3, Apple HIG, competitor apps)
- project workspace path

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Define the problem.** What recurring UX problem does this pattern solve? Be specific.
- **Step 2: Describe the solution.** How does the pattern solve it? What is the interaction, layout, or behavior?
- **Step 3: When to use it, and when not.** Clear criteria for when this pattern applies vs alternatives.
- **Step 4: List components.** Which DS components participate in this pattern? Role of each.
- **Step 5: Document variants.** Does the pattern have variations? (e.g., empty state: first-use vs no-results vs error-empty)
- **Step 6: Document accessibility.** How does the pattern work for screen readers, keyboard, reduced motion?
- **Step 7: Good and bad examples.** Show correct and incorrect usage with brief explanation.
- **Step 8: Link related patterns.** How does this pattern relate to others? (e.g., empty-state relates to loading-skeleton; confirmation-dialog relates to destructive-action)
- **Step 9: Write to file.** Save as `docs/research/patterns/<pattern-slug>.md`.
- Patterns are REUSABLE across projects. Avoid project-specific references.

Required output:
1. Pattern identity (name, category)
2. The generated spec doc (10 sections)
3. Components involved
4. Recommended next command

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
- All 10 sections of the PATTERN_SPEC template are filled.
- Problem and solution are clear enough that someone unfamiliar with the project understands the pattern.
- Components are referenced by DS name and tier.
- Good and bad examples are concrete, not abstract.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A designer or developer on a DIFFERENT project should be able to apply this pattern from the doc alone.

<!-- cache-breakpoint -->
