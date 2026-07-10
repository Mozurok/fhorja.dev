# Foundation: Iconography

> **Status:** draft | researched | approved
> **Figma:** `<icon library frame / variant set>`
> **Reference benchmarks:** <Lucide, Phosphor, Material Symbols, SF Symbols>

---

## 1. Scope

Icon library source, supported sizes, stroke/fill convention, semantic-to-icon mapping table, accessibility metadata. Does NOT cover decorative illustrations or brand logos (own area).

## 2. Decision (TL;DR)

Library chosen (Lucide / Phosphor / custom set), stroke vs filled default, default size, naming convention (Figma name vs library name).

## 3. Tokens — Size scale

| Token | Value | Use |
|---|---|---|
| `icon.size.xs` | 12 | inline-with-text, badges |
| `icon.size.sm` | 16 | secondary actions, list rows |
| `icon.size.md` | 20 | default button icon |
| `icon.size.lg` | 24 | primary nav icons |
| `icon.size.xl` | 32 | feature icons |
| `icon.size.2xl` | 48 | empty-state hero icons |

## 4. Semantic-to-icon map

| Semantic | Icon name | Notes |
|---|---|---|
| `close` | `X` (Lucide) | Always 24pt min, 44pt tap target |
| `back` | `ArrowLeft` | iOS may swap with Chevron |
| `success` | `CheckCircle` | paired with `color.state.success` |
| `warning` | `AlertTriangle` | paired with `color.state.warning` |
| `danger` | `AlertOctagon` | paired with `color.state.danger` |
| `info` | `Info` | paired with `color.text.secondary` |

Extend per product. Every icon used in UI must have a semantic entry; ad-hoc icon imports are flagged by the `icon-not-semantic` bug class.

## 5. Stroke / fill convention

- Default: stroke 1.5pt, no fill
- Active/selected state: same icon filled OR stroke 2pt
- Document which icons have filled variants vs which must always be outline

## 6. Accessibility

- Every icon-only button: `accessibilityLabel` is mandatory; visible label is preferred when space permits.
- Decorative icons (e.g., divider ornaments): `accessibilityElementsHidden={true}` (iOS) / `importantForAccessibility="no"` (Android).
- Color contrast: icon color must meet 3:1 against background (large UI element threshold).

## 7. Research

- Lucide / Phosphor coverage comparison
- Custom set tradeoffs (icon ownership, sync with Figma)

## 8. How to use

```tsx
import { tokens } from '@design-system/tokens';
import { Icon } from '@design-system/atoms';

<Icon name="close" size={tokens.icon.size.md} color={tokens.color.text.primary} accessibilityLabel="Close" />
```

## 9. Do not

- Use icon name as accessibility label ("X" → speakerphone says "ex")
- Mix multiple icon libraries in one screen
- Use raw SVG inline when an icon atom exists
- Render icons below 12pt (illegibility)

## 10. Open questions

- [ ] `ICON-NN`: <pending>

## 11. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `ICON-NN` |
