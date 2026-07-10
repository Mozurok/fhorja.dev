---
name: screen-spec
description: Generate a screen specification from a Figma frame using MCP tools (get_design_context, get_screenshot). Produces a spec doc matching the SCREEN_SPEC.md template with layout sketch, components used, spacing observed, data dependencies, copy, accessibility notes, interactions, and error states. Use when documenting a specific screen. Do not use when the screen has no Figma frame or when the spec already exists.
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 2500
  suggested-model: claude-sonnet-4-6
---
# screen-spec

Act as a design system researcher documenting a screen specification from Figma observations.

Goal:
For a given Figma screen frame, extract its layout, identify which design system components are used, observe spacing, and generate a comprehensive screen spec doc following `templates/SCREEN_SPEC.md`. The spec must capture enough detail for a developer to build the screen from the component library without re-reading Figma.

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
- Figma frame node ID or URL
- screen number and slug (for file naming: `<NN>-<slug>.md`)
- **persona** -- one of the canonical set per `wos/design-system-conventions.md` → `## Personas and screen organization`: `auth`, `shared`, `operative`, `controller`, `client`, `super-admin`, or a custom persona declared at `design-bootstrap`. For single-persona products (no subfolders), omit persona; screens land flat under `docs/app/screens/`.
- project workspace path
- optional: route path (if known from `docs/app/routes.md`)
- optional: journey name (which journey this screen belongs to)

Persona decision rule:
- A screen reachable from multiple personas with **cosmetic differences only** (color, label tweaks) → `persona = shared`; variants documented inline in the same spec.
- A screen reachable from multiple personas with **different copy, data, or actions** → separate specs per persona (e.g., `controller/dashboard.md` + `operative/dashboard.md`), each with one-line cross-link to siblings in the spec doc.
- A screen scoped strictly to one persona → that persona's folder.
- A pre-session screen (login, signup, onboarding, password reset, biometric setup) → `persona = auth`.

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Get visual context.** Call `get_design_context` on the screen frame to get its structured representation (children hierarchy, styles, component instances).
- **Step 2: Get screenshot.** Call `get_screenshot` for visual reference (embed or reference in spec).
- **Step 3: Identify components.** Map each UI element in the frame to a design system component. For each: name, tier, variant/props observed. If a component is not in the DS inventory, note it as a candidate.
- **Step 4: Generate layout sketch.** Create an ASCII art layout sketch showing the spatial arrangement of components on the screen (header, content area, footer, FAB, bottom sheet, etc.).
- **Step 5: Observe spacing.** Extract padding, margins, and gaps between elements. Map to spacing tokens from foundation docs. Note any values that do not align with the spacing scale.
- **Step 6: Document data dependencies.** Infer what data the screen needs: REST endpoints, WebSocket events, local state. Mark as `(proposed)` since Figma does not contain data layer info.
- **Step 7: Extract copy.** List all text strings visible on the screen (titles, labels, button text, empty states, error messages). These are ready for i18n extraction.
- **Step 8: Document accessibility.** Screen announcement, focus order (top-to-bottom, left-to-right), Dynamic Type behavior.
- **Step 9: Document interactions.** For each interactive element: gesture, target, result, animation, haptic. Reference component specs for details.
- **Step 10: Document error states.** Infer: what happens on network error, validation failure, empty data. Mark as `(proposed)`.
- **Step 11: Link related screens.** Back, forward, modal relationships based on navigation context. For multi-persona variants of the same screen, add one-line cross-link to sibling specs (e.g., `controller/dashboard.md` ↔ `operative/dashboard.md`).
- **Step 12: Write to file.** Save as `docs/app/screens/<persona>/<NN>-<slug>.md` for multi-persona products, or `docs/app/screens/<NN>-<slug>.md` for single-persona products.
- **Step 13: Update SCREEN_MAP.md.** Append a row to `docs/app/SCREEN_MAP.md` with: route (or `?` if not yet decided), persona, screen name, spec doc path, status=`drafted`, Figma node ID. If the row already exists from `design-bootstrap`'s pending list, update status from `pending` to `drafted`.
- **Step 14: Update routes.md if a new route was declared.** If this spec introduces a new route, append the row to `docs/app/routes.md` per the route table convention there. Skip if route already documented or not yet decided.
- Reference components by their DS name, not by visual description.
- Mark observations vs inferences explicitly.

Required output:
1. Screen identity (number, slug, persona, route)
2. The generated spec doc (12 sections)
3. Components used (with references to existing spec docs or candidates for new specs)
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
- All 12 sections of the SCREEN_SPEC template are filled.
- Components are referenced by DS name and tier, not visual description.
- Layout sketch accurately represents the screen's spatial arrangement.
- Spacing values map to foundation tokens where possible.
- Copy is extracted verbatim and ready for i18n.
- Screen file lives under `docs/app/screens/<persona>/` (multi-persona) or `docs/app/screens/` (single-persona) per the persona decision rule.
- `docs/app/SCREEN_MAP.md` has a row for this screen (added or status updated to `drafted`).
- For multi-persona variants of the same screen, sibling specs cross-link each other.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
A developer reading only this spec doc plus the component specs it references should be able to build the screen without opening Figma.

<!-- cache-breakpoint -->
