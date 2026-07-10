# Color Contrast Audit -- WCAG 2.2 AA

Scope: documented foreground/background pairs across LIGHT and DARK themes, with alias resolution honored. Pairs whose tokens cannot be resolved in a given theme are reported as `UNRESOLVED`, with the broken alias chain printed verbatim. No values are guessed for missing tokens.

## 1. Resolution Notes

Alias chains resolved before contrast computation:

- `color.notification.warning.fg` → `$alias: color.semantic.warning.text`
  - LIGHT: `color.semantic.warning.text.light` = `#7A4A00` → resolves.
  - DARK: `color.semantic.warning.text.dark` is **not defined** in the token source → alias chain breaks. No fallback is documented for this token, so the dark variant of `color.notification.warning.fg` has no resolvable color value.

- `color.notification.warning.bg`
  - LIGHT: `#FFF4D6` (literal)
  - DARK: `#332100` (literal)

- `color.text.primary`
  - LIGHT: `#222222` (literal)
  - DARK: `#F5F5F5` (literal)

- `color.surface.background`
  - LIGHT: `#FFFFFF` (literal)
  - DARK: `#0F1115` (literal)

## 2. Contrast Matrix (one row per (pair, theme))

WCAG 2.2 AA thresholds applied:
- Normal text: ≥ 4.5:1
- Large text (≥ 18pt / 14pt bold): ≥ 3:1
- Non-text UI components & graphical objects (1.4.11): ≥ 3:1

All documented pairs below are `normal-text`, so the AA threshold is **4.5:1**.

| # | Foreground (token → resolved) | Background (token → resolved) | Theme | Context | Ratio | AA (normal-text, 4.5:1) | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | `color.text.primary` → `#222222` | `color.surface.background` → `#FFFFFF` | LIGHT | normal-text | ~15.9:1 | PASS | PASS |
| 2 | `color.text.primary` → `#F5F5F5` | `color.surface.background` → `#0F1115` | DARK  | normal-text | ~16.5:1 | PASS | PASS |
| 3 | `color.notification.warning.fg` → (alias → `color.semantic.warning.text.light`) → `#7A4A00` | `color.notification.warning.bg` → `#FFF4D6` | LIGHT | normal-text | ~6.3:1 | PASS | PASS |
| 4 | `color.notification.warning.fg` → (alias → `color.semantic.warning.text.dark`) → **UNDEFINED** | `color.notification.warning.bg` → `#332100` | DARK  | normal-text | n/a | n/a | **UNRESOLVED** |

### Broken alias chain (row 4)

```
color.notification.warning.fg [dark]
  └─ $alias → color.semantic.warning.text [dark]
       └─ (no value) ✗ UNDEFINED
```

Because the chain terminates without a color literal in dark theme, no contrast ratio can be computed against `color.notification.warning.bg [dark] = #332100`. The pair is reported as **UNRESOLVED** rather than assigned a guessed value.

## 3. Findings Summary

- 3 of 4 (pair, theme) combinations resolve and pass WCAG 2.2 AA for normal text.
- 1 of 4 combinations (`color.notification.warning.fg` on `color.notification.warning.bg`, DARK) is **UNRESOLVED** due to a missing dark-theme definition for `color.semantic.warning.text`.
- Risk: any dark-theme surface that renders a warning notification will currently have no defined foreground color. Depending on the runtime fallback (CSS default, transparent, inherited text color, or runtime error), this can cause invisible text, illegible text, or a render failure. None of these are acceptable for an accessibility-critical component (warnings).

## 4. Recommendation (unresolved pair only)

Do **not** guess a value. The fix is a token-source change owned by the design-system team:

1. **Define `color.semantic.warning.text.dark`** in the token source as a first-class value (literal hex, or a documented alias to another already-defined dark-theme semantic token). This is the canonical fix because `color.notification.warning.fg` is intentionally an alias of `color.semantic.warning.text`, and the semantic layer is where dark-theme parity must exist.
2. Once defined, re-run this matrix for row 4 against `color.notification.warning.bg [dark] = #332100` and confirm the resulting ratio meets WCAG 2.2 AA for normal text (≥ 4.5:1). If the chosen value does not clear 4.5:1 against `#332100`, either the foreground or the background (or both) must be adjusted at the semantic layer so the warning surface meets AA in dark theme as it does in light theme (~6.3:1).
3. Add a token-source lint / CI check that fails the build when any alias resolves in one theme but not in the other, so this class of break (light-only semantic definition aliased from a theme-agnostic component token) is caught at authoring time rather than at audit time.
4. Until the dark variant is defined and verified, treat the dark-theme warning notification as a release blocker for accessibility sign-off.

No interim hex value is proposed here. Selecting the dark-theme warning text color is a semantic design decision (brand, hierarchy, paired-surface contrast across all warning surfaces, not just this one notification background) and must be made at the `color.semantic.warning.text` layer by the design-system owner, not inferred from a single pairing.
