# Proposal: extract-foundations-from-screens command

## Context

Phase 6 pilot ran SCREEN_SPEC generation across 5 pilot screens and surfaced a concrete, repeatable token inventory the screens kept rediscovering independently:

- **Colors**: `#0B1426`, `#0D0D0D`, `#FFFFFF`, `#FAFAFA`, `#18181B`, `#71717A`, `#2563EB`, `#EFF6FF`, `#BFDBFE`
- **Typography**: Geist family, sizes `12 / 14 / 16 / 18 / 20 / 36`
- **Spacing**: `4 / 8 / 12 / 16 / 24 / 32` (clean 4px grid)
- **Radii**: `8 / 12 / 16 / 24`

The screens carry these as raw values. Without a Foundations layer, every new SCREEN_SPEC re-extracts them from Figma, drift creeps in (`#0D0D0D` vs `#18181B` as "near-black"), and downstream component specs reference values instead of role tokens. We need a deterministic extractor that turns the cross-screen inventory into canonical Foundations docs.

## Proposed command

A new `commands/extract-foundations-from-screens.md` that:

1. **Input**: a list of SCREEN_SPEC paths (explicit list, or glob across `design/screens/**`) plus the project's design system folder root.
2. **Output**: writes / updates `foundations/color.md`, `foundations/typography.md`, `foundations/spacing.md`, `foundations/radii.md` against the existing FOUNDATION templates.
3. **Mode**: idempotent. Re-running on a superset of screens only adds tokens; existing role token names are preserved unless the underlying hex/size/grid value moved.

## Per-foundation extraction rules

**Color** -- union all hex values across SCREEN_SPECs, then bucket by inferred role:
- Backgrounds (largest-area surfaces per screen): `surface/canvas`, `surface/raised`, `surface/inverse`.
- Text (foreground on each surface): `text/default`, `text/muted`, `text/inverse`.
- Accent (CTA / link / focus): `accent/default`, `accent/strong`, `accent/soft`, `accent/stroke`.
- Each role lists candidate hexes with usage count; conflicts (e.g. `#0D0D0D` vs `#18181B`) are flagged as `REVIEW` instead of silently picking one.

**Typography** -- collapse by `(family, weight, size, line-height)` tuple, then map to roles:
- `display` (≥32), `heading/lg|md|sm` (20-28), `body/lg|md|sm` (14-18), `caption` (12).
- Family is held constant when one family dominates (Geist here); secondary families flagged.

**Spacing** -- round every observed value to the nearest 4px grid step; drop duplicates; emit ordered scale `xxs(4) / xs(8) / sm(12) / md(16) / lg(24) / xl(32)`. Off-grid values (e.g. 6, 10) are reported as drift, not silently rounded into the scale.

**Radii** -- same shape as spacing on an 8/12/16/24 progression: `sm / md / lg / xl`. Values not on the observed scale go to `REVIEW`.

## Acceptance criteria

- Given the 5 pilot SCREEN_SPECs, running the command produces 4 foundations files where every token in the inventory above maps to exactly one role.
- Re-running with a 6th screen that introduces no new values is a no-op on disk.
- Introducing a conflicting near-duplicate (e.g. `#0E0E0E`) does not overwrite an existing role; it lands in a `## Review queue` section in `color.md`.
- Each foundations file links back to the source SCREEN_SPECs that contributed each token (provenance).
- Output validates against the FOUNDATION templates' required sections.

## Integration

Two integration points, with different cost profiles:

- **One-shot at init (design-bootstrap)**: when bootstrapping a design system from an existing set of screens, design-bootstrap invokes extract-foundations-from-screens over all current SCREEN_SPECs to seed `foundations/*.md`. This is the cheapest path to a coherent baseline and matches how the pilot surfaced the inventory.
- **Incremental (post screen-spec batch)**: after `screen-spec-fleet` or a manual batch of `screen-spec` runs, the command re-runs over the new + existing specs. Outputs a diff summary (`+2 colors, +1 spacing step, 1 review`) so the operator decides whether to accept additions or push back on Figma drift.

Recommended default: one-shot at design-bootstrap, then incremental after each fleet run. Foundations stay the single source of truth; SCREEN_SPECs converge on referencing role tokens instead of raw hex.

## Non-goals

- No Figma round-trip (does not write tokens back to Figma).
- No code generation (no Tailwind config, no CSS variables) -- that belongs to a later `emit-foundations-tokens` command.
- No semantic naming inference beyond the role buckets above; naming refinement stays a human review step on the `REVIEW` queue.
