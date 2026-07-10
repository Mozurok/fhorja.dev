---
name: journey-map
description: |-
  Document a user journey from screen references and a user story input. Produces a journey spec doc matching the JOURNEY_SPEC.md template with outcome, screen flow, components consumed, critical states, accessibility, security, and performance sections. Use when mapping a user flow across multiple screens. Do not use when documenting a single screen (use screen-spec) or a reusable pattern (use pattern-doc).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed:
    - memory
    - retrieved
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
  token-budget: 2000
  suggested-model: claude-sonnet-4-6
---

Act as a UX researcher documenting a user journey across multiple screens.

Goal:
For a given user story or flow, document the complete journey: which screens are traversed, in what order, what components are consumed, what critical states exist (happy path + errors + edge cases), and what accessibility/security/performance concerns arise. Produce a journey spec doc following `templates/JOURNEY_SPEC.md`.

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
- journey name and slug (for file naming)
- persona(s) who take this journey
- user story or flow description (what the user is trying to accomplish)
- list of screen docs involved (or screen numbers from the inventory)
- project workspace path

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Define outcome.** What does the user achieve at the end? One clear sentence.
- **Step 2: List screens in order.** Read the referenced screen docs. Sequence them in the order the user traverses them. Note branching paths (decision points, error diversions).
- **Step 3: Identify components consumed.** Aggregate the components used across all screens in this journey. Reference by DS name and tier.
- **Step 4: Create journey map.** Draw a flow diagram (ASCII) showing: Start, each screen as a node, decision points as diamonds, end state(s). Include the happy path and key alternate paths.
- **Step 5: Document critical states.** For each non-happy-path scenario: state name, trigger, UI response, which screen(s) are affected. Minimum 4 critical states: happy path, network error, validation failure, timeout/slow.
- **Step 6: Reference pattern.** What competitor or industry pattern does this journey borrow from? Where does it diverge? Why?
- **Step 7: Document accessibility.** VoiceOver/TalkBack flow across screens, focus order on transitions, screen announcements, Reduced Motion behavior for transitions.
- **Step 8: Document security.** FLAG_SECURE screens, cache purging on exit, idle lock behavior, screenshot restrictions during this journey.
- **Step 9: Document performance.** Virtualization needs, prefetching between screens, WebSocket connection lifecycle, lazy loading.
- **Step 10: Log open questions.** Ambiguities about the flow that need stakeholder input.
- **Step 11: Write to file.** Save as `docs/research/journeys/<journey-slug>.md`.

Required output:
1. Journey identity (name, persona, outcome)
2. The generated spec doc (11 sections)
3. Screens referenced (with links to spec docs)
4. Open questions
5. Recommended next command

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
- All 11 sections of the JOURNEY_SPEC template are filled.
- Journey map includes happy path + at least 2 alternate paths.
- Critical states table has at least 4 entries (happy + 3 failure modes).
- Screens are referenced by doc path, not just by name.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A product manager reading this doc should understand the complete user experience without opening Figma or reading individual screen specs.

<!-- cache-breakpoint -->
