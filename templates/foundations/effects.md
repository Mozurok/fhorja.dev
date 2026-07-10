# Foundation: Effects

> **Status:** draft | researched | approved
> **Figma:** `<effect styles: blur, gradient, alpha overlays>`
> **Reference benchmarks:** <Apple HIG materials, Material 3 surface tint>

---

## 1. Scope

Blur, gradients, alpha-overlay tokens, surface tint variants. Does NOT cover shadows (see `elevation.md`).

## 2. Decision (TL;DR)

Which effects are first-class (blur ✓ / gradient ✓ / overlays ✓), platform support strategy (iOS blur via `react-native-blur` vs CSS backdrop-filter), performance constraints.

## 3. Tokens — Blur

| Token | Intensity | Use |
|---|---|---|
| `effect.blur.subtle` | 8 | sticky header behind content |
| `effect.blur.medium` | 16 | modal scrim |
| `effect.blur.strong` | 32 | hero glass cards |

## 4. Tokens — Alpha overlays

If supported as first-class tokens (per `color.md`), document the alpha set here for reuse:

| Token shape | Alpha | Use |
|---|---|---|
| `effect.alpha.10` | 10% | hover/press tint |
| `effect.alpha.20` | 20% | divider variant |
| `effect.alpha.40` | 40% | scrim, dim background |
| `effect.alpha.60` | 60% | strong scrim |

Combine with any base color: `color.brand.primary` + `effect.alpha.20` → `brand.primary.alpha20`.

## 5. Tokens — Gradient

If gradients are used (note: many design systems forbid them):

| Token | Stops | Use |
|---|---|---|
| `effect.gradient.brand` | `brand.primary → brand.secondary` | hero CTA |

If gradients are NOT used in this product, state so explicitly and skip this section.

## 6. Platform considerations

- **iOS**: native blur is performant via `UIVisualEffectView`; `react-native-blur` wraps it.
- **Android**: blur via `RenderEffect` (API 31+); below 31, fall back to dim overlay.
- **Web (Storybook)**: `backdrop-filter: blur()` — check browser support and provide fallback.

## 7. Performance

- Blur is expensive — avoid stacking multiple blurred layers.
- For scrolling lists, prefer flat scrim (`effect.alpha.40` over solid surface) over animated blur.
- Profile on lowest-spec target device before shipping blur-heavy screens.

## 8. Research

- Apple HIG: vibrant materials, system materials
- Material 3: surface tint at elevation
- iOS Liquid Glass (when applicable)

## 9. How to use

```tsx
import { tokens } from '@design-system/tokens';
import { BlurView } from '@design-system/atoms';

<BlurView intensity={tokens.effect.blur.medium} tint="light" />
```

## 10. Do not

- Stack 2+ blur layers (perf cliff)
- Use blur to hide content (cmds + screenshots reveal it; not a security primitive)
- Apply 80%+ alpha overlay solely for visual flair (becomes unreadable)
- Ship blur on Android <API 31 without fallback

## 11. Open questions

- [ ] `EFFECT-NN`: <pending>

## 12. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `EFFECT-NN` |
