# Button Color Contrast Audit -- Per Interaction State

## 1. Three Contrast Pairs (label `#FFFFFF` against composed background)

Relative luminance is computed per WCAG 2.x (sRGB → linearize → `0.2126R + 0.7152G + 0.0722B`), and contrast ratio is `(L_lighter + 0.05) / (L_darker + 0.05)`.

### Pair A -- Default state
- Label: `#FFFFFF` (L ≈ 1.0)
- Background: `#0066CC` (L ≈ 0.1331)
- Contrast ratio ≈ **(1.0 + 0.05) / (0.1331 + 0.05) = 5.74:1**

### Pair B -- Hover state (12% white overlay → `#1F77D1`)
- Label: `#FFFFFF` (L ≈ 1.0)
- Background: `#1F77D1` (R=31, G=119, B=209 → L ≈ 0.1840)
- Contrast ratio ≈ **(1.0 + 0.05) / (0.1840 + 0.05) = 4.49:1**

### Pair C -- Active state (20% black overlay → `#0052A3`)
- Label: `#FFFFFF` (L ≈ 1.0)
- Background: `#0052A3` (R=0, G=82, B=163 → L ≈ 0.0815)
- Contrast ratio ≈ **(1.0 + 0.05) / (0.0815 + 0.05) = 7.99:1**

## 2. Verdict Per State

| State   | Composed bg | Ratio (vs `#FFFFFF`) | AA normal text (≥ 4.5:1) | AA UI component (≥ 3:1) |
|---------|-------------|----------------------|--------------------------|-------------------------|
| Default | `#0066CC`   | ~5.74:1              | PASS                     | PASS                    |
| Hover   | `#1F77D1`   | ~4.49:1              | **FAIL** (just under)    | PASS                    |
| Active  | `#0052A3`   | ~7.99:1              | PASS (AAA-level)         | PASS                    |

## 3. Does Any State Fail WCAG 2.2 AA?

Yes -- **the HOVER state fails the 4.5:1 AA threshold for normal-size text** at ~4.49:1. It is mathematically a fraction below the bar; WCAG does not round, so this is a real failure for body-size labels (< 18pt regular / < 14pt bold). It still clears the 3:1 UI-component minimum, so the button's *shape* contrast against an adjacent surface is not the issue -- the label-on-fill ratio is.

Default and active states both pass AA for normal text and the 3:1 UI-component threshold.

The audit therefore must NOT stop at the default state. Because the hover overlay lightens the fill, it actively erodes label contrast -- exactly the failure mode that hides when reviewers only check the resting style. State-by-state verification is required whenever overlays, opacity, or blends are part of the interaction spec.

## 4. Recommended Remediation

Pick one; do not stack them blindly:

1. **Reduce the hover overlay.** Drop white overlay from 12% to ~6–8%. At 6% white over `#0066CC` the composed bg stays closer to `#0F6FCE`, keeping the ratio above 4.5:1 while still reading as "lighter on hover."
2. **Invert the hover treatment.** Instead of lightening the fill, *darken* it on hover (e.g., 8% black overlay → similar direction as active) and reserve lightening for focus ring / elevation. White-on-darker-blue keeps contrast safely above 4.5:1.
3. **Add an outline / elevation hover signal** rather than a fill shift, leaving the composed bg at `#0066CC` and getting hover affordance from a 2px focus-style ring or shadow.
4. **Darken the base token.** Move `color.button.primary.bg` from `#0066CC` to roughly `#0059B3`. Then even with the 12% white overlay the hover composite (~`#1A6BC2`) clears 4.5:1, and default/active improve too.
5. **If the brand fill must stay `#0066CC` and the overlay must stay 12% white**, change the label to a non-pure-white that the design system already uses for elevated surfaces only if it *increases* contrast -- note that `#FFFFFF` is already maximum; the only way to fix this pair is to change the background, not the label. Document this constraint in the token notes so future overlay tweaks re-trigger the audit.

Also add a regression guard: any token whose computed value is derived from an overlay/opacity blend should be checked in all documented states (default, hover, active, focus, disabled) -- not only at rest -- and the contrast result should be stored alongside the token, not just in the resting spec.
