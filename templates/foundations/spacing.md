# Foundation: Spacing

> **Status:** draft | researched | approved
> **Figma:** `<variable collection: spacing / size>`
> **Reference benchmarks:** <Tailwind, 4pt grid, Material 3 4dp>

---

## 1. Scope

Spacing scale used for gap, padding, margin, and inset tokens. Does NOT cover layout grid (see `grid.md`) — that owns containers/columns/breakpoints.

## 2. Decision (TL;DR)

Base unit (4pt or 8pt), scale shape (linear / fibonacci / hybrid), how many steps, semantic aliases (if any).

## 3. Tokens — Spacing scale

| Token | Value | Use observed |
|---|---|---|
| `spacing.xxs` | 2 | icon-to-text micro gap |
| `spacing.xs` | 4 | tight chip spacing |
| `spacing.sm` | 8 | inline elements |
| `spacing.md` | 12 | default form-field gap |
| `spacing.lg` | 16 | card content padding |
| `spacing.xl` | 24 | section spacing |
| `spacing.2xl` | 32 | page section gap |
| `spacing.3xl` | 48 | hero spacing |
| `spacing.4xl` | 64 | rare; full-page hero |

## 4. Semantic aliases (optional)

- `spacing.field.gap` → `spacing.md`
- `spacing.section.gap` → `spacing.xl`
- `spacing.card.padding` → `spacing.lg`

Use aliases when the same physical value carries different intent in different contexts. Only introduce when the semantic actually exists in design.

## 5. Touch target floor

- Minimum tap target: 44x44 pt (iOS) / 48x48 dp (Android). Use `spacing` to compose padding around icons to meet this floor.
- `IconButton` defaults: 44pt for primary actions, 32pt only when nested inside a larger 44pt+ row with hitSlop.

## 6. Research

- 4pt vs 8pt grid: tradeoff observations.
- Reference apps: spacing scale comparison.

## 7. How to use

```tsx
import { tokens } from '@design-system/tokens';

const styles = StyleSheet.create({
  card: {
    padding: tokens.spacing.lg,
    gap: tokens.spacing.md,
  },
});
```

## 8. Do not

- Raw numbers in styles (`padding: 16`) — use `tokens.spacing.lg`
- Off-scale values (introducing `padding: 18`) — pick the closest token or extend the scale via Decisions
- Mix base units within the system (don't have both `7pt` and `8pt` tokens)

## 9. Open questions

- [ ] `SPACE-NN`: <pending>

## 10. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `SPACE-NN` |
