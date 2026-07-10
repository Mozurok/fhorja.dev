# ADR-0030: RN-reference-app pattern as the canonical WOS-UI reference

- **Status**: Accepted
- **Date**: 2026-06-04
- **Tags**: wos-ui, design-system, docs-split, granular-foundations, screens-by-persona, audit-cadence, reference-implementation

## Context

The WOS-UI surface (`design-system-conventions.md`, the design system commands `design-bootstrap` / `component-spec` / `screen-spec` / `journey-map` / `pattern-doc` / `foundation-audit` / `design-spec-review`, and the design system templates under `templates/`) was built incrementally as a generic atomic-design framework. It documented the right primitives (atomic tiers, semantic tokens, W3C DTCG, states, traceability rule) but lacked an opinionated shape for the broader docs and code structure that a design system actually requires.

The `rn-reference-app` project (`~/Documents/rn-reference-app`) was the first WOS-UI consumer to ship a complete design system end-to-end: `docs/research/` for universal patterns + `docs/app/` for concrete app composition, ten granular `foundations/<area>.md` files instead of one monolithic spec, screens organized by persona (`auth/`, `shared/`, `operative/`, `controller/`, `client/`, `super-admin/`), an `ATOM_AUDIT.md` table consolidating per-atom guideline compliance, a `COMPONENT_GUIDELINES.md` codifying cross-cutting rules, a `_templates/` folder colocated inside `docs/research/` instead of pointing at the repo-root `templates/`, and an `_inventory/figma_components.md` snapshot for delta tracking versus Figma.

A comparative audit on 2026-06-03 against AAA references (Spec Kit, BMAD, Kiro, Anthropic Skills, Cursor, Devin, Windsurf) plus the rn-reference-app implementation revealed that the rn-reference-app shape is the strongest WOS-UI exemplar available: it survives end-to-end use, matches the granularity Figma exposes (each foundation area is one Figma variable collection), and decomposes screen-level work cleanly per persona without forcing a single-persona product to adopt subfolders. None of the seven AAA references documented an equivalent shape; the closest (Kiro steering files + Anthropic Skills) cover different concerns.

Without this ADR, the WOS-UI shape lived implicitly in the rn-reference-app repo and was at risk of drifting per-project. New WOS-UI users would re-derive the structure on every project, or invent variants that diverge from the proven one.

## Decision

The rn-reference-app docs+packages+storybook structure is the canonical WOS-UI reference implementation. The WOS-UI commands and templates are aligned to produce it by default:

- The split `docs/research/` (universal patterns) vs `docs/app/` (concrete app composition) is normative for WOS-UI projects with more than ~10 components and is mandatory at `design-bootstrap` time.
- Foundations are documented per area in `docs/research/foundations/<area>.md` (color, typography, spacing, grid, radii, elevation, motion, iconography, effects, states), not as a single FOUNDATION_SPEC.md. Sub-templates live in `templates/foundations/`; the generic `templates/FOUNDATION_SPEC.md` becomes a meta-pointer for areas not in the canonical ten.
- Screens organize by persona under `docs/app/screens/<persona>/`. Canonical persona vocabulary: `auth`, `shared`, `operative`, `controller`, `client`, `super-admin`. Single-persona products use a flat `docs/app/screens/`.
- Three canonical audit artifacts (`ATOM_AUDIT.md`, `COMPONENT_GUIDELINES.md`, `_inventory/figma_components.md`) are templated and refreshed by dedicated commands (`atom-audit`, `inventory-snapshot`).
- Design system templates colocate inside `docs/research/_templates/` (not centralized at repo root). The repo-root `templates/` keeps the meta-templates that `design-bootstrap` copies into the project at init.

The mechanism that enforces this decision is the WOS-UI command and template set itself:

- `wos/design-system-conventions.md` (`## Repository structure (docs split)`, `## Personas and screen organization`, `## Audit cadence`) is the normative doc.
- `commands/design-bootstrap.md` produces the structure end-to-end.
- `commands/screen-spec.md` writes to the persona-scoped path.
- `commands/atom-audit.md` and `commands/inventory-snapshot.md` produce the audit artifacts.
- `templates/foundations/`, `templates/ATOM_AUDIT.md`, `templates/COMPONENT_GUIDELINES.md`, `templates/SCREEN_MAP.md`, `templates/ROUTES.md`, `templates/NAVIGATION.md`, `templates/INVENTORY.md` are the canonical templates.

## Consequences

### Positive

- New WOS-UI projects inherit the proven shape automatically via `design-bootstrap`; no need to re-derive the structure per project.
- Audit artifacts (`ATOM_AUDIT.md`, `COMPONENT_GUIDELINES.md`, inventory) become first-class instead of incidental, making design system health observable.
- Granular foundations match Figma's natural granularity and enable per-area audits (`foundation-audit --area=color`) instead of monolithic re-scans.
- Persona-scoped screens decompose multi-role products cleanly without imposing overhead on single-persona ones.
- The rn-reference-app repo becomes an external reference implementation that future contributors can read to understand the intended shape.

### Negative

- More templates and commands to maintain (10 foundation sub-templates + 6 new structural templates + 2 new commands). Net surface grew from 7 to 9 WOS-UI commands and from 7 to 22 WOS-UI templates.
- Existing WOS-UI projects predating this ADR may have a flatter or different structure; they are not retroactively migrated. New work in those projects can adopt the shape incrementally, but full migration is a separate task.
- The rn-reference-app reference is an external dependency for understanding intent; if rn-reference-app drifts from this ADR (e.g., experiments with a different persona vocabulary), the ADR is the source of truth, not the repo.

### Neutral

- Single-persona products lose nothing (no subfolder ceremony imposed; flat `docs/app/screens/` is the default).
- The repo-root `templates/` still exists as the meta-template source; only the design system templates are colocated, not the generic LEARNINGS / PR_PACKAGE / OPEN_QUESTIONS templates which serve broader concerns.

## Alternatives considered

### Alternative 1: Keep WOS-UI generic (status quo)

- Continue with one FOUNDATION_SPEC.md, no persona subfolders, no canonical audit artifacts. Let each project derive its own shape.
- Rejected: every new WOS-UI project would re-derive the same patterns inefficiently, and audit artifacts that should be first-class would remain ad hoc. The rn-reference-app implementation showed the cost of doing this once was high enough to justify locking the shape.

### Alternative 2: Adopt a different reference (Material 3 / Carbon / Polaris docs structure)

- Use an industry-standard design system docs layout (Material 3, IBM Carbon, Shopify Polaris) as the reference instead.
- Rejected: those reference shapes are optimized for cross-team mega-systems and for serving as documentation to external consumers, not for solo or small-team WOS-driven engineering work. They impose ceremony that does not pay off at the scale WOS-UI typically operates.

### Alternative 3: Generate the structure dynamically without locking it

- Have `design-bootstrap` generate the structure based on Figma observations alone, without locking the canonical shape.
- Rejected: produces inconsistent results across projects; loses the operational benefit of audit commands (`atom-audit`, `inventory-snapshot`) that depend on canonical paths.

## References

- `wos/design-system-conventions.md` (`## Repository structure (docs split)`, `## Personas and screen organization`, `## Audit cadence`) -- normative doc updated to reflect this ADR.
- `commands/design-bootstrap.md` -- updated to produce the canonical structure.
- `commands/screen-spec.md` -- updated to accept `persona` parameter and write to `docs/app/screens/<persona>/`.
- `commands/atom-audit.md` -- new command introduced by this ADR.
- `commands/inventory-snapshot.md` -- new command introduced by this ADR.
- `templates/foundations/` -- 10 granular sub-templates + README introduced by this ADR.
- `templates/ATOM_AUDIT.md`, `templates/COMPONENT_GUIDELINES.md`, `templates/SCREEN_MAP.md`, `templates/ROUTES.md`, `templates/NAVIGATION.md`, `templates/INVENTORY.md` -- new templates introduced by this ADR.
- External reference implementation: `~/Documents/rn-reference-app/docs/research/`, `~/Documents/rn-reference-app/docs/app/`, `~/Documents/rn-reference-app/packages/design-system/`, `~/Documents/rn-reference-app/apps/storybook/`.
- ADR-0001 (PROPOSED-by-default) -- applies to all WOS-UI commands.
- ADR-0011 (shared canonical blocks) -- the templates pattern follows the canonical-source discipline ADR-0011 established for command blocks.
- ADR-0029 (drift guards) -- count markers track template counts where applicable.

## Notes

The WOS-UI improvement plan slice H.8 introduced this ADR after slices H.1 through H.7 shipped the supporting templates and command updates. The ADR is the last step because earlier slices had to ship first to make the references in `## Decision` and `## References` true.

Future WOS-UI changes (e.g., adding a new foundation area, a new persona to the canonical set, a new audit artifact) should reference this ADR in their commit or task notes so the chain of reasoning stays visible.
