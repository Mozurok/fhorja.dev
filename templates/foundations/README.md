# Foundation sub-templates

Granular templates for documenting each foundation area as a separate file under `docs/research/foundations/<area>.md`. The granularity matches what Figma exposes (one variable collection per area) and lets `foundation-audit` target a single area.

Each sub-template inherits the **core sections** from `../FOUNDATION_SPEC.md` (Scope, Decision, Tokens, Light vs Dark, Accessibility, Research, How to use, Do not, Open questions, Decisions). The sub-templates here only add or specialize fields that are area-specific; for everything else, follow `FOUNDATION_SPEC.md`.

## When to use which

| Area | Sub-template | Use when |
|---|---|---|
| Color | `color.md` | Brand palette, neutral ramp, semantic state colors, surfaces, tinted overlays, dark mode |
| Typography | `typography.md` | Font families, scale, weight, line-height, platform overrides |
| Spacing | `spacing.md` | Spacing scale, gap/padding/margin tokens |
| Grid | `grid.md` | Layout grid, container widths, columns, breakpoints |
| Radii | `radii.md` | Border radius scale |
| Elevation | `elevation.md` | Shadows, surface layers, z-index policy |
| Motion | `motion.md` | Animation tokens, easing curves, duration scale, reduced-motion |
| Iconography | `iconography.md` | Icon library, sizes, semantic mapping |
| States | `states.md` | Cross-component state vocabulary (default/pressed/focused/...) |
| Effects | `effects.md` | Blur, glow, gradient, alpha overlay tokens |

## When to skip

If a product does NOT use a given area (e.g., no grid for a mobile-only app), omit the file. Do NOT create stubs. The `foundations/README.md` in the product repo lists which areas are documented vs deferred.

## Convention with the meta template

`../FOUNDATION_SPEC.md` remains the generic skeleton. It is what `design-bootstrap` copies into `docs/research/_templates/` at project init. The sub-templates here are the area-specific augmentation set; `design-bootstrap` also copies these into `docs/research/_templates/foundations/` so they are colocated with the actual area docs.
