# Foundation: Color

> **Status:** draft | researched | approved
> **Figma:** `<variable collection name>` (e.g., `Brand`, `Greyscale`, `Semantic`)
> **Reference benchmarks:** <Nubank, Apple HIG system colors, Material 3 tonal palettes>

---

## 1. Scope

Brand colors, neutral greyscale ramp, semantic state colors (success/warning/danger), surface + text aliases, tinted overlays (alpha variants), and light/dark mode mapping. Does NOT cover gradients (own area if used), shadows (see `elevation.md`), or blur (see `effects.md`).

## 2. Decision (TL;DR)

3-5 lines: how many brand colors, what the neutral ramp looks like, semantic state set, dark mode strategy (parity / inverted / deferred).

## 3. Tokens — Brand

| Figma variable | Hex | Code token | Use observed |
|---|---|---|---|
| `Brand/<name>` | `#XXXXXX` | `color.brand.<name>` | <where used> |

## 4. Tokens — Greyscale ramp

| Figma variable | Hex | Code token | Use observed |
|---|---|---|---|
| `greyscale/Grey N` | `#XXXXXX` | `color.grey.N` | <where used> |

## 5. Tokens — Semantic state

| Figma variable | Hex | Code token | Meaning |
|---|---|---|---|
| `Semantic/success` | `#XXXXXX` | `color.state.success` | active, confirmation |
| `Semantic/warning` | `#XXXXXX` | `color.state.warning` | caution, offline |
| `Semantic/danger` | `#XXXXXX` | `color.state.danger` | error, destructive |

## 6. Semantic aliases (text + surface)

- `color.text.primary` → `color.grey.<N>` (light) / `color.grey.<M>` (dark)
- `color.text.secondary` → ...
- `color.surface.base` → ...
- `color.surface.elevated` → ...
- `color.border.default` → ...

## 7. Tinted overlays

If supported, document the alpha-overlay convention (e.g., 10%/20%/40% of any base color as opacity-derived tokens):

| Token shape | Alpha | Use |
|---|---|---|
| `color.<base>.alpha10` | 10% | hover/press overlay |
| `color.<base>.alpha20` | 20% | divider variant, soft fill |

## 8. Light vs Dark mode

| Token | Light | Dark | Strategy |
|---|---|---|---|
| `color.surface.base` | `#FFFFFF` | `#000000` | invert |
| `color.text.primary` | `grey.900` | `grey.50` | invert |

If dark mode is deferred, state so: "Dark mode deferred to post-design phase; today everything is light."

## 9. Accessibility

- Contrast pairs measured: `text.primary on surface.base = X:1` (target: ≥4.5:1 body AA, ≥7:1 AAA).
- Approved foreground × background table (mark pairs that PASS / FAIL).
- Color-blindness: palette verified in deuteranopia, protanopia, tritanopia (cite tool used).
- Never use color alone to convey state (always pair with icon/text/shape).

## 10. Research (references)

- Nubank: <what they do + what we borrow>
- Apple HIG / Material 3: <system convention referenced>
- Other competitors observed: <list>

## 11. How to use

```tsx
import { tokens } from '@design-system/tokens';

const styles = StyleSheet.create({
  cta: { backgroundColor: tokens.color.brand.primary },
  body: { color: tokens.color.text.primary },
});
```

## 12. Do not

- Raw hex in components (always go through tokens)
- Light token used in dark mode without semantic alias
- Color alone conveying semantic meaning (e.g., red == error)
- Off-palette colors introduced ad-hoc

## 13. Open questions

- [ ] `BRAND-NN`: <pending>

## 14. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `BRAND-NN` |
