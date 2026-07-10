# Foundation: Radii

> **Status:** draft | researched | approved
> **Figma:** `<corner radius styles>`
> **Reference benchmarks:** <Material 3 shape, Apple HIG corners>

---

## 1. Scope

Border radius scale + semantic aliases (button, card, sheet, pill). Does NOT cover shadows (see `elevation.md`).

## 2. Decision (TL;DR)

Scale shape (linear / mixed), how many steps, pill convention (sharing token vs unique).

## 3. Tokens — Radius scale

| Token | Value | Use |
|---|---|---|
| `radius.none` | 0 | flush edges |
| `radius.xs` | 2 | tight inputs (rare) |
| `radius.sm` | 4 | small chips |
| `radius.md` | 8 | default button, input, card |
| `radius.lg` | 12 | larger cards |
| `radius.xl` | 16 | sheets, modals |
| `radius.2xl` | 24 | hero containers |
| `radius.pill` | 9999 | pill buttons, avatars when round |

## 4. Semantic aliases

- `radius.button.default` → `radius.md`
- `radius.button.pill` → `radius.pill`
- `radius.card` → `radius.lg`
- `radius.sheet` → `radius.xl` (top corners only typically; document override)
- `radius.input` → `radius.md`

## 5. Per-corner application

When only some corners are rounded (e.g., bottom sheets: top corners only):

- Document the convention here: top-left + top-right round to `radius.xl`, bottom corners `radius.none`.
- Avoid mixing rounded + sharp on same element without semantic reason.

## 6. Research

- Material 3 shape scale
- Apple HIG corners (system standards)
- Reference app patterns

## 7. How to use

```tsx
import { tokens } from '@design-system/tokens';

const styles = StyleSheet.create({
  button: { borderRadius: tokens.radius.button.default },
  sheet: {
    borderTopLeftRadius: tokens.radius.sheet,
    borderTopRightRadius: tokens.radius.sheet,
  },
});
```

## 8. Do not

- Hardcode `borderRadius: 8` — use `tokens.radius.md`
- Mix pill with `borderRadius` smaller than half-height (creates near-pill artifact)
- Apply `overflow: 'hidden'` solely to clip rounded corners on Android without testing perf

## 9. Open questions

- [ ] `RADII-NN`: <pending>

## 10. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `RADII-NN` |
