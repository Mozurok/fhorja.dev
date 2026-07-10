# Component: `<ComponentName>`

> **Tier:** atom | molecule | organism | layout
> **Status:** draft | researched | approved | implemented
> **Figma:** `<Component/FrameName>` (node IDs: `<fileKey:nodeId>`)
> **Used in screens:** <list of screen docs that consume this component>
> **Reference benchmarks:** <Apple HIG, Material 3, Nubank, Coinbase, etc.>

---

## 1. Purpose and when to use

<What this component does. When to reach for it vs alternatives. 2-3 sentences max.>

## 2. Anatomy (from Figma)

<Visual breakdown: background, label, icon slots, borders, padding. Reference Figma observations. Include dimensions observed.>

## 3. Variants

| Variant | Background | Label color | Border | Used in | Source |
|---|---|---|---|---|---|
| `<name>` | `<token>` | `<token>` | `<none / 1pt token>` | `<screen>` | `<Figma / proposed>` |

## 4. Sizes

| Size | Height | Min width | Label role | Padding-x | Touch target |
|---|---|---|---|---|---|
| `lg` (confirmed) | `<pt>` | `<pt>` | `<typography token>` | `<pt>` | `<meets 44pt?>` |
| `md` (proposed) | | | | | |
| `sm` (proposed) | | | | | |

44pt minimum touch target (Foundation spacing). Sizes below 44pt must compensate via hit-slop padding.

## 5. States (CRITICAL)

| State | Visual | Trigger | Notes |
|---|---|---|---|
| default | per variant table | initial render | |
| pressed | background darkens 8-10% lightness | onPressIn | scale 0.97 in 150ms ease-out |
| focused | 2pt ring `color.focus.ring`, 4pt offset | tab / VoiceOver focus | required for AAA |
| disabled | opacity 0.4, no press feedback | `disabled` prop | aria-disabled="true" |
| loading | spinner replaces icon or label fades to 0.6 | `loading` prop | blocks onPress; announce "Loading" |
| error | (if applicable) red border, error icon | validation failure | aria-invalid="true" |
| empty | (if applicable) placeholder content | no data | |
| offline | (if applicable) grey out, "offline" indicator | no network | |

## 6. Accessibility

- **Role:** `<button / link / textbox / etc.>`
- **Accessible label:** required. Defaults to `label` prop; accepts `accessibilityLabel` override.
- **Touch target:** `<dimensions>` (above/below 44pt threshold?)
- **Contrast:** `<foreground on background = ratio>` (AA pass / AAA pass?)
- **Dynamic Type:** label must wrap or shrink one step, never truncate with ellipsis.
- **Reduced Motion:** animation disabled; press feedback becomes 1-frame color flash.
- **VoiceOver/TalkBack:** `"<label>, <role>"`. If loading: `"<label>, <role>, loading"`.

## 7. Motion

- Press feedback: scale `<from>` to `<to>` in `<ms>` `<easing>`.
- Background color shift: `<ms>` linear.
- Loading spinner: standard platform spinner; rotation honored unless Reduced Motion.

## 8. Haptics

| Variant | Haptic style | When |
|---|---|---|
| primary | `ImpactFeedbackStyle.Light` | onPressIn |
| danger | `ImpactFeedbackStyle.Heavy` | onPressIn |
| disabled / loading | none | |

## 9. Platform-specific

| Concern | iOS | Android | Web (Storybook) |
|---|---|---|---|
| Font weight | SemiBold maps to 600 | 600 via fontFamily | CSS font-weight: 600 |
| Shadow | NSShadow | elevation | box-shadow |
| Haptics | expo-haptics | ReactNative Vibration | not available |

## 10. Security

<If component handles sensitive content: FLAG_SECURE screen, no screenshot, cache purging. "N/A" for non-sensitive components.>

## 11. Performance

<Memoization strategy, re-render avoidance, virtualization notes. "Standard" for simple components.>

## 12. TypeScript API

```tsx
interface <ComponentName>Props {
  variant: '<variant1>' | '<variant2>';
  size?: '<sm>' | '<md>' | '<lg>';
  disabled?: boolean;
  loading?: boolean;
  // ...
}
```

## 13. Usage examples

```tsx
<ComponentName variant="primary" size="lg" onPress={handleSubmit}>
  Submit
</ComponentName>
```

## 14. Do not

- Do not use `<ComponentName>` for <wrong use case>. Use `<Alternative>` instead.
- Do not override tokens with inline styles.
- Do not skip the loading state for async actions.

## 15. Decisions

| Date | Decision | Rationale | Resolves |
|---|---|---|---|
| `<YYYY-MM-DD>` | `<what>` | `<why>` | `<OPEN_QUESTIONS ID>` |
