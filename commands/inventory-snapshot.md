---
name: inventory-snapshot
description: Snapshot the upstream Figma component library into docs/research/_inventory/figma_components.md. For each Figma component: name, inferred tier, node ID, and whether a spec/code/story exists in the WOS-UI surface. Produces delta vs previous snapshot. Use after design ships a Figma library update or to seed the inventory at project start. Do not use when no Figma source is available or when only auditing one component (use design-spec-review instead).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 2000
  suggested-model: claude-sonnet-4-6
---
# inventory-snapshot

Act as a design system auditor maintaining a current view of the Figma component library and its mapping to the WOS-UI surface (spec docs, code dirs, Storybook stories).

Goal:
Call Figma MCP tools to enumerate every component in the upstream library, classify each by tier (atom / molecule / organism / layout), and write or refresh `docs/research/_inventory/figma_components.md`. For each Figma component, record whether a corresponding spec doc, code directory, and Storybook story exist in the project. Produce a delta report vs the previous snapshot. Refresh the priority queue with components that need attention next.

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
- project workspace path
- Figma file URL (e.g., `https://figma.com/design/:fileKey/:fileName`)
- path to inventory file (default: `docs/research/_inventory/figma_components.md`; created from `templates/INVENTORY.md` if absent)
- optional: scope to a specific Figma page or top-level frame

Task repository files to update:
- TASK_STATE.md (add inventory summary: total components, % traceable, delta vs previous)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Read previous snapshot.** If `figma_components.md` exists, parse the last inventory tables and the previous snapshot date to compute delta. If absent, create from `templates/INVENTORY.md`.
- **Step 2: Enumerate Figma components.** Call `get_libraries` (preferred for published libraries) or `get_metadata` (scan component sets from frames) to list every Figma component. Capture name, node ID, and any variant set info.
- **Step 3: Classify by tier.** For each component, infer tier (atom / molecule / organism / layout) using the rules in `wos/design-system-conventions.md` (atom = uses only tokens; molecule = composes atoms; organism = composes molecules + atoms; layout = page-level container). When ambiguous, mark `(proposed)` and surface as an open question.
- **Step 4: Check WOS-UI traceability.** For each component, check whether the corresponding artifacts exist:
  - spec doc: `docs/research/components/<tier>/<kebab-name>.md`
  - code dir: `packages/design-system/src/<tier>/<PascalName>/`
  - story file: `apps/storybook/stories/<tier>/<PascalName>.stories.tsx`
  Mark each as present or empty in the inventory row.
- **Step 5: Compute counts.** Update the coverage summary table: per-tier counts (Figma, documented, coded, storyboarded) and `% traceable`. The target for shipped MVP is 100%.
- **Step 6: Compute delta vs previous.** Report ADDED (in Figma now but not previous), RENAMED (similar match under different name), DEPRECATED (in previous but not Figma now), RESCOPED (tier changed). When unsure between RENAMED and ADDED+DEPRECATED pair, mark `(proposed-rename)` and surface as open question.
- **Step 7: Refresh priority queue.** Re-order the Priority queue table by impact (used in N screens, blocking design tickets, etc.) plus delta status. Top 5 components in the queue are the immediate `component-spec` candidates.
- **Step 8: Write to file.** Update `docs/research/_inventory/figma_components.md` with new Last refresh date, refreshed tables, and delta section.
- Do NOT modify spec docs, code, or stories. This command is read-only against the WOS-UI surface; only the inventory file is written.
- If `figma_components.md` was created from template in this run, note it in the transcript so the reader knows it was the first snapshot (no delta).

Required output:
1. Summary: N Figma components total (per tier), % traceable overall
2. Delta vs previous snapshot (ADDED / RENAMED / DEPRECATED / RESCOPED counts)
3. Top 5 priority queue entries with rationale
4. Open questions surfaced (ambiguous tier, proposed-rename pairs, etc.)
5. Recommended next command (typically `component-spec` on the #1 priority entry)

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
- Every Figma component present in the source is represented as a row in the inventory file.
- Each row has tier inferred + node ID + spec/code/story columns filled (present or empty).
- Coverage summary recomputed with current counts and `% traceable`.
- Delta section reflects ADDED / RENAMED / DEPRECATED / RESCOPED vs previous snapshot (or "first snapshot" note).
- Priority queue refreshed; top 5 entries have rationale.
- No code, spec, or story files modified by this command (read-only against the WOS-UI surface).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Every claim about traceability ("spec exists" / "code exists" / "story exists") must reflect actual file presence checked at runtime, not inferred from past inventory state.

<!-- cache-breakpoint -->
