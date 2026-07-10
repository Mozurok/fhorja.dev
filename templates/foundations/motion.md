# Foundation: Motion

> **Status:** draft | researched | approved
> **Figma:** `<variable collection: motion / duration / easing>`
> **Reference benchmarks:** <Apple HIG motion, Material 3 motion, Reanimated docs>

---

## 1. Scope

Duration scale, easing curves, semantic role aliases (enter/exit/microinteraction/page-transition), reduced-motion fallback strategy. Does NOT cover gestures (own area if used).

## 2. Decision (TL;DR)

Animation library (Reanimated vs Animated core vs CSS transitions), duration scale (linear/exponential), how reduced-motion is honored (instant snap vs cross-fade fallback).

## 3. Tokens — Duration

| Token | Value (ms) | Use |
|---|---|---|
| `motion.duration.instant` | 0 | reduced-motion fallback |
| `motion.duration.fast` | 150 | microinteraction (press, hover) |
| `motion.duration.normal` | 250 | enter/exit |
| `motion.duration.slow` | 400 | page transition |
| `motion.duration.deliberate` | 600 | onboarding moments |

## 4. Tokens — Easing

| Token | Curve | Use |
|---|---|---|
| `motion.easing.standard` | `cubic-bezier(0.4, 0.0, 0.2, 1)` | most enter/exit |
| `motion.easing.decelerate` | `cubic-bezier(0.0, 0.0, 0.2, 1)` | enter from off-screen |
| `motion.easing.accelerate` | `cubic-bezier(0.4, 0.0, 1, 1)` | exit to off-screen |
| `motion.easing.emphasized` | `<value>` | hero moments |

## 5. Semantic aliases

- `motion.preset.press` → duration: `fast`, easing: `standard`, transform: scale(0.97)
- `motion.preset.modal.enter` → duration: `normal`, easing: `decelerate`
- `motion.preset.modal.exit` → duration: `fast`, easing: `accelerate`

## 6. Reduced motion

- Respect `prefers-reduced-motion` (web), `UIAccessibility.isReduceMotionEnabled` (iOS), Settings → Accessibility → Remove animations (Android).
- Reduced-motion fallback: replace transform/translate animations with opacity cross-fade OR instant snap. Document which.
- Every interactive atom must check `useReducedMotion()` hook before triggering scale/transform.

## 7. Research

- Apple HIG motion section
- Material 3 motion guidelines
- Reanimated 4 best practices (UI thread, gesture handler integration)

## 8. How to use

```tsx
import { tokens } from '@design-system/tokens';
import { useReducedMotion } from '@design-system/hooks';

const reduceMotion = useReducedMotion();
const scale = withTiming(0.97, {
  duration: reduceMotion ? 0 : tokens.motion.duration.fast,
  easing: tokens.motion.easing.standard,
});
```

## 9. Do not

- Hardcode duration (`duration: 200`) — use `tokens.motion.duration.*`
- Animate without reduced-motion check on transforms/translates
- Use `LayoutAnimation` for anything more than container resize (not configurable on Reanimated path)
- Run animations on JS thread when Reanimated UI-thread variants exist

## 10. Open questions

- [ ] `MOTION-NN`: <pending>

## 11. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `MOTION-NN` |
