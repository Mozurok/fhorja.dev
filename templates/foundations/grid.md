# Foundation: Grid

> **Status:** draft | researched | approved
> **Figma:** `<grid styles + breakpoints variable collection>`
> **Reference benchmarks:** <Material 3, Apple HIG layout, Tailwind container queries>

---

## 1. Scope

Layout grid, container widths, column counts, gutters, breakpoints, and how content flows across device classes. Does NOT cover spacing tokens (see `spacing.md`).

## 2. Decision (TL;DR)

Mobile-first vs desktop-first, single-column mobile vs columned, breakpoint set, container max-widths, gutter strategy.

## 3. Breakpoints

| Token | Min width | Device class |
|---|---|---|
| `grid.bp.xs` | 0 | small phone |
| `grid.bp.sm` | 380 | default mobile (this product's base) |
| `grid.bp.md` | 768 | tablet portrait |
| `grid.bp.lg` | 1024 | tablet landscape / small desktop |
| `grid.bp.xl` | 1440 | desktop |

## 4. Container widths

| Breakpoint | Container max-width | Columns | Gutter |
|---|---|---|---|
| xs / sm | 100% (edge-to-edge with `spacing.lg` padding) | 1 | 0 |
| md | 720 | 8 | 16 |
| lg | 960 | 12 | 16 |
| xl | 1200 | 12 | 24 |

## 5. Page padding (mobile)

- Left + right: `spacing.lg` (16) by default
- Top: respect SafeAreaView
- Bottom: SafeAreaView + bottom tab bar height

## 6. Research

- Material 3 layout grids
- Apple HIG layout (Compact / Regular size classes)
- Reference apps observed (Nubank, Coinbase, etc.)

## 7. How to use

```tsx
import { tokens } from '@design-system/tokens';

const styles = StyleSheet.create({
  page: {
    paddingHorizontal: tokens.spacing.lg,
  },
});
```

## 8. Do not

- Hardcode breakpoint values in components
- Use a 12-column grid on mobile (1 column is the right default)
- Forget SafeAreaView on iOS (notch + dynamic island)
- Mix container widths within the same screen without explicit reason

## 9. Open questions

- [ ] `GRID-NN`: <pending>

## 10. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `GRID-NN` |
