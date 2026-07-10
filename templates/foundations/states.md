# Foundation: States

> **Status:** draft | researched | approved
> **Figma:** N/A (states are cross-component, derived from component variants)
> **Reference benchmarks:** <Material 3 interaction states, Apple HIG interaction>

---

## 1. Scope

Cross-component state vocabulary that every interactive component spec must address. Defines names, triggers, and visual changes for the canonical state set. Does NOT define per-component visual treatments (those live in each component spec).

## 2. Decision (TL;DR)

Standard state set (default / pressed / focused / disabled / loading / error / empty / offline / selected / skeleton), how each is signaled visually, what tokens are involved.

## 3. Canonical state set

| State | Trigger | Visual change | Token role |
|---|---|---|---|
| **default** | Initial render | Base appearance per variant | base tokens |
| **pressed** | Touch / click down | Bg darken, scale 0.97 (via motion preset) | `effect.alpha.10` overlay, `motion.preset.press` |
| **focused** | Keyboard tab / screen-reader focus | Focus ring 2pt outline | `color.border.focus`, `radius.*` matching component |
| **disabled** | `disabled` prop | Opacity 0.5, no interaction, cursor: not-allowed (web) | opacity 0.5 (cross-platform constant) |
| **loading** | `loading` prop | Spinner replaces content / label fades | spinner atom + label fade via opacity 0.5 |
| **error** | Validation fail / API error | Red border, error message associated | `color.state.danger`, message slot |
| **empty** | No data | Empty-state component (icon + message + CTA) | `iconography` + body typography + button atom |
| **offline** | No network | OfflineBanner organism appears | banner with `color.state.warning` |
| **selected** | Multi-select context | Filled variant + check icon | `color.brand.primary` + check icon |
| **skeleton** | Loading placeholder | Shimmer layout matching final content | skeleton atom |

## 4. State combinations

| Combination | Allowed? | Resolution priority |
|---|---|---|
| disabled + loading | NO | disabled wins; loading suppressed |
| disabled + selected | YES | both visible (faded selected) |
| focused + pressed | YES | both visible (focus ring + press transform) |
| error + disabled | YES | both visible (faded error) |
| loading + error | NO | last terminal state wins; loading must clear before error shows |

## 5. Per-component state checklist

When writing a component spec, every interactive atom/molecule MUST document:

- [ ] default state
- [ ] pressed state (transform + bg change)
- [ ] focused state (focus ring)
- [ ] disabled state (opacity + no interaction)
- [ ] error state (if validation possible)
- [ ] loading state (if async action possible)

Decorative components (Icon, Divider, Skeleton itself) are exempt from the interactive checklist but must document `accessibilityElementsHidden` policy.

## 6. Accessibility

- `focused` state: 2pt focus ring minimum, contrast ≥3:1 against background, never solely color-based (must include outline or shape change).
- `pressed`/`disabled`/`error` states must each have `accessibilityState` reflected.
- Loading state: `accessibilityHint` includes "Loading..." for screen readers.

## 7. Reduced motion

- `pressed` state's scale transform: skip on `prefers-reduced-motion` → use opacity dip instead.
- `loading` spinner: use opacity pulse fallback (skeleton already meets the bar).

## 8. Research

- Material 3 interaction state layers (hover / focus / press as overlay opacities)
- Apple HIG: control state guidance

## 9. How to use

```tsx
import { tokens } from '@design-system/tokens';
import { useReducedMotion } from '@design-system/hooks';

const reduceMotion = useReducedMotion();
const pressedStyle = reduceMotion
  ? { opacity: 0.7 }
  : { transform: [{ scale: 0.97 }] };
```

## 10. Do not

- Invent new state names per component (Pressed vs Active vs Touched — pick one across system)
- Use only color to signal state (always pair with shape/icon/text)
- Forget `accessibilityState` on custom interactive elements
- Combine disabled + loading on same element

## 11. Open questions

- [ ] `STATE-NN`: <pending>

## 12. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `STATE-NN` |
