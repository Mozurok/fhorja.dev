# Foundation: Elevation

> **Status:** draft | researched | approved
> **Figma:** `<effect styles / drop shadow variables>`
> **Reference benchmarks:** <Material 3 elevation, Apple HIG depth>

---

## 1. Scope

Shadow tokens, surface layer hierarchy, z-index policy. Does NOT cover blur (see `effects.md`).

## 2. Decision (TL;DR)

Shadow style (Material 3 tonal vs iOS drop shadow), number of elevation steps, dark-mode strategy (shadows may need adjustment or tonal swap).

## 3. Tokens — Shadow scale

| Token | Shadow (CSS / RN equivalent) | Use |
|---|---|---|
| `elevation.none` | none | flat surfaces |
| `elevation.sm` | `0 1px 2px rgba(0,0,0,0.05)` | dividers, slight raise |
| `elevation.md` | `0 4px 8px rgba(0,0,0,0.08)` | cards, raised buttons |
| `elevation.lg` | `0 8px 16px rgba(0,0,0,0.10)` | floating action button, popovers |
| `elevation.xl` | `0 16px 32px rgba(0,0,0,0.12)` | modals, dialogs |
| `elevation.dialog` | (alias of `elevation.xl`) | semantic |
| `elevation.dropdown` | (alias of `elevation.lg`) | semantic |

## 4. Semantic surface layers

| Layer | Tokens used | Examples |
|---|---|---|
| base | `surface.base`, `elevation.none` | screen background |
| raised | `surface.elevated`, `elevation.sm` | card on page |
| floating | `surface.elevated`, `elevation.lg` | FAB |
| overlay | `surface.overlay`, `elevation.xl` | modal, dialog |

## 5. Z-index policy

Avoid arbitrary z-index numbers. Use a documented stack:

| Token | Value | Use |
|---|---|---|
| `zIndex.base` | 0 | content |
| `zIndex.sticky` | 10 | sticky headers |
| `zIndex.dropdown` | 100 | menus, popovers |
| `zIndex.modal` | 1000 | dialogs |
| `zIndex.toast` | 2000 | notifications |
| `zIndex.tooltip` | 3000 | tooltips above all |

## 6. Dark mode

Shadows on dark surfaces are typically less visible — consider tonal elevation (slight surface color shift) instead of, or in addition to, drop shadow.

## 7. Research

- Material 3 tonal elevation
- Apple HIG depth + materials
- iOS blur (vibrant materials) — links to `effects.md`

## 8. How to use

```tsx
import { tokens } from '@design-system/tokens';

const styles = StyleSheet.create({
  card: {
    backgroundColor: tokens.color.surface.elevated,
    ...tokens.elevation.md,  // spreads shadowColor/Offset/Opacity/Radius on RN
  },
});
```

## 9. Do not

- Use raw `boxShadow` strings
- Apply `elevation` (Android numeric) without matching iOS shadow (asymmetric appearance)
- Layer shadows (rendering perf hit on Android)

## 10. Open questions

- [ ] `ELEV-NN`: <pending>

## 11. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `ELEV-NN` |
