# Color Contrast Audit: `color.text.error` on `color.surface.background`

Audit target: text token `color.text.error` rendered on background token `color.surface.background`, normal-weight body text, evaluated in both LIGHT and DARK themes.

## 1. Token Resolution

| Token | Theme | Resolution chain | Resolved value |
|---|---|---|---|
| `color.surface.background` | light | direct literal | `#FFFFFF` |
| `color.surface.background` | dark | direct literal | `#0F1115` |
| `color.text.error` | light | alias -> `color.semantic.error.fg` (light) -> `#B5453A` | `#B5453A` |
| `color.text.error` | dark | alias -> `color.semantic.error.fg` (dark) -> **UNDEFINED** | **UNRESOLVED** |

The dark-theme alias chain is broken: `color.text.error.dark` points to `color.semantic.error.fg`, but that semantic token has no `dark` value defined. There is no fallback declared in the source.

## 2. Per-Theme Contrast Matrix

| Theme | Foreground (resolved) | Background (resolved) | Contrast ratio | WCAG 2.2 normal text (4.5:1) | WCAG 2.2 large text (3:1) | Verdict |
|---|---|---|---|---|---|---|
| Light | `#B5453A` | `#FFFFFF` | **4.83:1** | Pass | Pass | PASS (AA normal) |
| Dark  | **UNRESOLVED** | `#0F1115` | n/a | n/a | n/a | **UNRESOLVED -- cannot evaluate** |

### Light-theme math (sanity check)

- `#B5453A` relative luminance L1 approx 0.1564
- `#FFFFFF` relative luminance L2 = 1.0000
- Ratio = (1.0000 + 0.05) / (0.1564 + 0.05) approx **4.83:1**
- Passes WCAG 2.2 AA for normal text (>= 4.5:1). Does not pass AAA (< 7:1).

## 3. Light Theme -- Verdict

- Pair: `#B5453A` on `#FFFFFF`
- Ratio: approx 4.83:1
- WCAG 2.2 AA normal text: **PASS**
- WCAG 2.2 AA large text: PASS
- WCAG 2.2 AAA normal text: FAIL (would need >= 7:1)
- Status: shippable for body copy at AA; not safe for AAA targets without a darker red.

## 4. Dark Theme -- Verdict

**UNRESOLVED.**

`color.text.error` in dark theme aliases to `color.semantic.error.fg`, which has no `dark` value in the provided source. No fallback is declared. Per audit policy (Step 2 + Step 5), an unresolved token must not be guessed, substituted with the light value, or assumed to inherit. Therefore:

- Resolved foreground: **none**
- Contrast ratio: **not computable**
- WCAG verdict: **not assessable**
- Status: **blocking defect in the token source**, not a contrast failure.

Do not infer that dark theme "probably reuses the light value" -- token systems explicitly require per-theme declarations, and silent fallback is exactly the failure mode this audit is meant to catch.

## 5. Recommendations

1. **Fix the token source first (blocking).** Define `color.semantic.error.fg.dark` explicitly. This is a token-system bug, not a styling preference.
2. **Suggested dark-theme value (for design review, not auto-applied).** On `#0F1115` background, a normal-text error color needs roughly L >= 0.36 to clear 4.5:1. Candidates worth testing: `#FF8A7A`, `#FF9A8A`, or a tuned `#F28B7E`. Each must be re-measured against the actual background after the designer picks one -- do not ship any of these without verification.
3. **Re-run this audit after the dark value is defined.** Produce a new matrix row for dark and confirm AA (and AAA if that is the bar).
4. **Add a lint / CI check** that fails the build when any alias resolves to `undefined` in any theme, so this class of break is caught at token-build time rather than at visual review.
5. **Audit siblings.** If `color.semantic.error.fg.dark` is missing, check whether `color.semantic.warning.fg.dark`, `color.semantic.success.fg.dark`, and `color.semantic.info.fg.dark` have the same gap -- broken alias chains usually cluster.
6. **Light theme is acceptable at AA** for normal body text. If the product target is AAA (e.g. long-form reading, regulated content), darken the light red until ratio >= 7:1 (roughly `#9A2F25` range, to be re-measured).

## Summary

- Light: `#B5453A` on `#FFFFFF` = 4.83:1, **PASS AA normal**.
- Dark: **UNRESOLVED** -- alias chain `color.text.error.dark -> color.semantic.error.fg.dark` terminates at an undefined token. Blocking. Fix the source, then re-audit.
