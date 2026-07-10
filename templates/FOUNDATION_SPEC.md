# Foundation: `<name>`

> **Generic foundation template.** This is the meta-skeleton used when a foundation area does NOT have a dedicated sub-template under `templates/foundations/<area>.md`. Prefer the area-specific sub-template when one exists — it has fields tuned to that area's vocabulary.
>
> **Sub-templates available** (per `wos/design-system-conventions.md` → `## Repository structure (docs split)` → `### Granular foundations`):
> - `templates/foundations/color.md`
> - `templates/foundations/typography.md`
> - `templates/foundations/spacing.md`
> - `templates/foundations/grid.md`
> - `templates/foundations/radii.md`
> - `templates/foundations/elevation.md`
> - `templates/foundations/motion.md`
> - `templates/foundations/iconography.md`
> - `templates/foundations/effects.md`
> - `templates/foundations/states.md`
>
> Use THIS generic template only for foundation areas not in the canonical 10 (e.g., a product introduces `haptics.md` or `gradient.md` as its own area).

---

> **Status:** draft | researched | approved
> **Upstream:** Foundation section `<N>` in Project Foundation.md
> **Figma:** `<variable collection name>` (node IDs if relevant)
> **Reference benchmarks:** <Apple HIG, Material 3, Nubank, etc.>

---

## 1. Scope

<What this foundation owns. One sentence.>

## 2. Decision (TL;DR)

<Key decision in 1-2 sentences. What was chosen and why.>

## 3. Tokens

| Token | Value | Usage | Notes |
|---|---|---|---|
| `<category>.<semantic>.<variant>` | `<value>` | `<where used>` | `<confirmed / proposed>` |

## 4. Light vs Dark mode

<How tokens change between modes. If dark mode is deferred, state so explicitly.>

## 5. Accessibility

<Minimum contrast pairs, touch targets, reduced motion/transparency rules relevant to this foundation.>

## 6. Research

<References consulted: Apple HIG section, Material 3 section, Nubank patterns, competitor screenshots. Link or cite each.>

## 7. How to use (code example)

```tsx
// Example of consuming this foundation token in a component
import { <tokens> } from '@/tokens/<category>';
```

## 8. Do not (anti-patterns)

- Do not <anti-pattern 1>.
- Do not <anti-pattern 2>.

## 9. Open questions

<Link to OPEN_QUESTIONS.md entries with this foundation's prefix. Example: `BRAND-01`, `TYPE-02`.>

## 10. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what was decided>` | `<why>` | `<OPEN_QUESTIONS ID>` |
