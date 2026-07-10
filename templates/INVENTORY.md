# Figma Components Inventory

> Snapshot of the upstream Figma component library at a point in time. Provides "what does Figma have today vs what we've documented" delta visibility. Refreshed when design ships new screens or restructures the library.
>
> Produced by the `inventory-snapshot` command. Lives at `docs/research/_inventory/figma_components.md`.
>
> **Last refresh:** `<YYYY-MM-DD>` | **Figma file:** `<file URL or name>` | **Source variant set:** `<top-level frame name>`

---

## Coverage summary

| Tier | Figma count | Documented count | Coded count | Storyboarded count | % traceable |
|---|---|---|---|---|---|
| atoms | `<N>` | `<N>` | `<N>` | `<N>` | `<%>` |
| molecules | `<N>` | `<N>` | `<N>` | `<N>` | `<%>` |
| organisms | `<N>` | `<N>` | `<N>` | `<N>` | `<%>` |
| layouts | `<N>` | `<N>` | `<N>` | `<N>` | `<%>` |
| **total** | `<N>` | `<N>` | `<N>` | `<N>` | `<%>` |

"% traceable" = `documented AND coded AND storyboarded` / `Figma count`. Target: 100% for shipped MVP.

---

## Atoms inventory

| Figma name | Tier inferred | Spec doc | Code dir | Story file | Notes |
|---|---|---|---|---|---|
| `Avatar/Default` | atom | `docs/research/components/atoms/avatar.md` | `packages/design-system/src/atoms/Avatar/` | `apps/storybook/stories/atoms/Avatar.stories.tsx` | full traceable |
| `Button/Primary` | atom | `docs/research/components/atoms/button.md` | `packages/design-system/src/atoms/Button/` | `apps/storybook/stories/atoms/Button.stories.tsx` | full traceable |
| `Chip/Filter` | atom (proposed) | — | — | — | NEW since last snapshot |
| ... | ... | ... | ... | ... | ... |

## Molecules inventory

(Same table shape.)

## Organisms inventory

(Same table shape.)

## Layouts inventory

(Same table shape.)

---

## Delta vs previous snapshot (`<previous YYYY-MM-DD>`)

| Change type | Component | Notes |
|---|---|---|
| ADDED | `Chip/Filter` (atom) | new from design 2026-MM-DD |
| RENAMED | `Btn/Primary` → `Button/Primary` | naming standardization |
| DEPRECATED | `LegacyAlert/Top` | replaced by `Banner/Inline` |
| RESCOPED | `MediaThumbnail` atom → molecule | now wraps Avatar + label |

---

## Priority queue (next to document)

Ordered list of components to document next, derived from inventory delta + product roadmap.

| Order | Component | Reason | Estimated tier |
|-------|---|---|---|
| 1 | `Chip/Filter` | used in 8 screens, not documented | atom |
| 2 | `Banner/Inline` | replaces deprecated `LegacyAlert/Top` | molecule |
| 3 | ... | ... | ... |

## Refresh cadence

- Manually triggered via `inventory-snapshot` after every Figma library push from design.
- Recommended weekly check during active design phase; biweekly during implementation phase.

## How a new inventory entry lands as a documented component

1. Inventory shows `Chip/Filter` exists in Figma with NO spec/code/story.
2. Add to Priority queue (above).
3. Open task: `task-init` with subject `chip-filter__atom-bootstrap`.
4. `component-spec` writes `docs/research/components/atoms/chip-filter.md`.
5. `implementation-plan` → `implement-approved-slice` builds code + story.
6. Re-run `inventory-snapshot`; row updates from blank → full traceable.
