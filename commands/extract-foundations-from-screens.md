---
name: extract-foundations-from-screens
description: Extract canonical foundations docs (`foundations/color.md`, `foundations/typography.md`, `foundations/spacing.md`, `foundations/radii.md`) from a batch of existing SCREEN_SPECs. Idempotent: re-runs only add new tokens, never overwrite existing role mappings, and route conflicts to a Review queue. Use when SCREEN_SPECs already document raw values and you need to converge them into role tokens. Do not use when foundations are already curated and screens already reference role tokens (run `foundation-audit` instead).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 3200
  suggested-model: claude-sonnet-4-6
---
# extract-foundations-from-screens

Act as a design system extractor that turns a cross-screen inventory of raw values into canonical Foundations docs.

Goal:
Read a set of `SCREEN_SPEC.md` files, union the raw values they carry (hex colors, typography tuples, spacing pixels, radii pixels), bucket each value into a role token per the per-foundation rules below, and write or update `foundations/color.md`, `foundations/typography.md`, `foundations/spacing.md`, `foundations/radii.md` against the existing FOUNDATION templates. The operation is idempotent: re-running on a superset of screens only adds new tokens; existing role tokens are never overwritten; conflicts land in a `## Review queue` section instead of being silently resolved.

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
- SCREEN_SPECs source: explicit list of paths OR glob (e.g. `design/screens/**/SCREEN_SPEC.md`).
- Design system folder root (e.g. `docs/research/`). The command writes under `<ds-root>/foundations/`.
- Optional: list of foundations to extract (default: all four -- `color`, `typography`, `spacing`, `radii`).

Task repository files to update:
- `<ds-root>/foundations/color.md`
- `<ds-root>/foundations/typography.md`
- `<ds-root>/foundations/spacing.md`
- `<ds-root>/foundations/radii.md`
- TASK_STATE.md (append extraction summary: N specs read, N tokens added, N review entries)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full).
- **Step 1: Resolve SCREEN_SPEC set.** Expand the glob or accept the explicit list. Fail fast if zero files match. For each spec, record its path; it becomes the provenance link for every token it contributes.
- **Step 2: Parse raw values.** For each SCREEN_SPEC, extract:
  - Colors: every hex (`#RRGGBB` / `#RGB`) regardless of section.
  - Typography tuples: `(family, weight, size_px, line_height_px)` from the Typography section.
  - Spacing values: every px integer found in spacing / layout sections.
  - Radii values: every px integer found in radius / corner sections.
  Record source spec path per value for provenance.
- **Step 3: Load existing foundations (idempotency anchor).** If `<ds-root>/foundations/<area>.md` exists, parse its `## Tokens` table. Existing role-to-value mappings are LOCKED -- they MUST be preserved verbatim. Any new candidate that collides with a locked role goes to the `## Review queue`, never overwrites.
- **Step 4: Apply per-foundation extraction rules.**
  - **Color** -- union all hexes. Bucket by inferred role from SCREEN_SPEC context (largest-area surfaces → `surface/canvas`, `surface/raised`, `surface/inverse`; foreground on surfaces → `text/default`, `text/muted`, `text/inverse`; CTA / link / focus → `accent/default`, `accent/strong`, `accent/soft`, `accent/stroke`). For each candidate hex, count usage across specs. Conflicts (e.g. `#0D0D0D` vs `#18181B` both arguing for `surface/inverse`) are NOT silently resolved -- both go to `## Review queue` with usage counts.
  - **Typography** -- collapse by `(family, weight, size, line-height)` tuple. Map size buckets to roles: `display` (≥32), `heading/lg|md|sm` (20-28), `body/lg|md|sm` (14-18), `caption` (12). Hold family constant when one family dominates; flag secondary families to `## Review queue`.
  - **Spacing** -- round every observed value to the nearest 4px grid step. Emit ordered scale `xxs(4) / xs(8) / sm(12) / md(16) / lg(24) / xl(32)`. Off-grid values (6, 10, 14, …) are reported under `## Review queue` as drift -- NEVER silently rounded into the scale.
  - **Radii** -- same shape as spacing on an `8 / 12 / 16 / 24` progression → `sm / md / lg / xl`. Values outside the observed scale go to `## Review queue`.
- **Step 5: Render foundation docs.** For each of the four areas, render against the matching template in `docs/research/_templates/foundations/<area>.md`. The `## Tokens` table MUST contain: role name, value, source SCREEN_SPECs (relative paths), usage count. Append a `## Review queue` section listing conflicts and off-rule values with the same columns plus a `Reason` cell (`conflict`, `off-grid`, `family-mismatch`, …). If a foundation has zero new entries and zero review items, do NOT rewrite the file -- emit `SKIP` per the global output contract.
- **Step 6: Idempotency check.** Diff the produced files against the on-disk version. If a re-run on the same input would produce byte-identical output, emit a `NO_OP_TRACE`. The acceptance contract: re-running with a screen that introduces no new values is a no-op on disk.
- **Step 7: Update TASK_STATE.md.** Append a one-line summary: `extract-foundations-from-screens: N specs, +Ac colors / +At typography / +As spacing / +Ar radii, R review`.
- Never overwrite a locked role-to-value mapping from a prior run; always route the collision to `## Review queue`.
- Never silently round spacing or radii off-grid values into the scale.
- Never invent role names beyond the vocabulary above; semantic refinement is a human review step.
- Do not write Tailwind config, CSS variables, or any code artifact -- that belongs to a later `emit-foundations-tokens` command (non-goal here).

Required output:
1. Summary: N SCREEN_SPECs read, per-area token counts added vs preserved, review queue size.
2. Per-foundation breakdown: color / typography / spacing / radii -- added roles, preserved roles, review entries.
3. Provenance check: confirm every new token cites at least one source SCREEN_SPEC.
4. Idempotency verdict: `NO_OP` if nothing changed, otherwise list of files touched.
5. Recommended next command (typically `foundation-audit` to verify the extraction against code, or `component-spec` to start consuming the new role tokens).

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
- Every raw value from every SCREEN_SPEC is accounted for: it either appears in the `## Tokens` table of the matching foundation OR in the `## Review queue` of that foundation. No value is dropped silently.
- Every new token in `## Tokens` cites at least one source SCREEN_SPEC (provenance).
- No locked role-to-value mapping from a prior run was overwritten.
- Conflicts (color), off-grid values (spacing, radii), and secondary families (typography) live in `## Review queue`, not in the canonical scale.
- A re-run on the same SCREEN_SPEC set is byte-identical (`NO_OP_TRACE`).
- TASK_STATE.md has the extraction summary line.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Every token is grounded in at least one SCREEN_SPEC and one explicit per-foundation rule. When a value is ambiguous (conflicting hexes, off-grid pixel, second font family), prefer routing it to `## Review queue` over making a silent call. Foundations are the single source of truth downstream -- wrong silently is worse than slow loudly.

<!-- cache-breakpoint -->
