---
name: component-spec
description: |-
  Generate a 15-section component specification from a Figma component using MCP tools (get_design_context, get_screenshot, get_variable_defs). Produces a spec doc matching the COMPONENT_SPEC.md template with anatomy, variants, sizes, states, accessibility, motion, haptics, platform, security, performance, and API sections pre-filled from Figma observations. Use when documenting a design system component. Do not use when the component has no Figma representation or when the spec already exists (edit manually instead).
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
  token-budget: 3000
  suggested-model: claude-sonnet-4-6
---

Act as a design system researcher documenting a component specification from Figma observations.

Goal:
For a given Figma component, extract its visual properties (dimensions, colors, typography, spacing, variants) via MCP tools and generate a comprehensive 15-section spec doc following `templates/COMPONENT_SPEC.md`. Mark every observation as `confirmed` (directly from Figma) or `proposed` (inferred from patterns or industry conventions). The spec must be detailed enough for a developer to implement the component without re-reading the Figma file.

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
- Figma component node ID or URL (e.g., `figma.com/design/:fileKey/:fileName?node-id=:nodeId`)
- atomic tier: atom | molecule | organism | layout
- project workspace path
- optional: existing foundation docs (for token cross-referencing)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Get visual context.** Call `get_design_context` on the component node to get a structured representation (layout, styles, children).
- **Step 2: Get screenshot.** Call `get_screenshot` for the component to capture visual reference.
- **Step 3: Get variables.** Call `get_variable_defs` on the component to extract which tokens it uses (colors, typography, spacing).
- **Step 4: Analyze anatomy.** From the design context, identify: background shape, label text, icon slots, padding, border, border-radius. Document dimensions observed.
- **Step 5: Identify variants.** If the Figma component has variants (component set), list each variant with its visual differences and when to use it. Cross-reference tokens.
- **Step 6: Derive sizes.** If multiple size variants exist, document height, min-width, label typography role, and padding per size. Flag 44pt touch target compliance.
- **Step 7: Document states.** Apply the mandatory 6-state checklist from `wos/design-system-conventions.md`: default, pressed, focused, disabled, loading, error. For states NOT visible in Figma (common: Figma rarely shows focused or loading), mark as `(proposed)` with industry-standard recommendations.
- **Step 8: Document accessibility.** Role, accessible label source, touch target dimensions, contrast ratios (compute from token values), Dynamic Type behavior, Reduced Motion fallback, VoiceOver announcement.
- **Step 9: Document motion and haptics.** Press feedback, transitions, spinner behavior. Reference foundation motion tokens. If not in Figma, propose based on `wos/design-system-conventions.md` and industry conventions.
- **Step 10: Document platform specifics.** iOS vs Android vs Web differences (font rendering, shadow API, haptics availability).
- **Step 11: Propose TypeScript API.** From variants, sizes, and states, draft the props interface.
- **Step 12: Write usage example.** One code snippet showing the most common usage.
- **Step 13: Write anti-patterns.** What not to do with this component (based on its purpose and design system role).
- **Step 14: Link open questions.** If ambiguities were found during extraction, create entries in `OPEN_QUESTIONS.md` with the appropriate prefix.
- **Step 15: Write to file.** Save as `docs/research/components/<tier>/<component-name>.md`.
- Mark every observation explicitly: `confirmed` (from Figma) or `(proposed)` (inferred).
- Reference foundation tokens by semantic name, not raw values.
- Do not invent visual properties not present in Figma; propose them explicitly when industry conventions justify it.

Required output:
1. Component name, tier, and Figma source
2. The generated spec doc (15 sections)
3. Open questions identified
4. Recommended next command (usually: next component from inventory, or `screen-spec`)

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
- All 15 sections of the COMPONENT_SPEC template are filled (no empty sections; use "N/A" or "(proposed)" where data is unavailable).
- Tokens are referenced by semantic name from foundations, not raw hex/pt values.
- States include the 6 mandatory states; Figma-unobserved states are marked `(proposed)`.
- Accessibility section includes computed contrast ratios and touch target dimensions.
- Open questions are logged in OPEN_QUESTIONS.md with appropriate prefix IDs.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A developer reading only this spec doc should be able to implement the component without opening Figma. Every claim traces to a Figma observation or an explicit proposal.

<!-- cache-breakpoint -->
