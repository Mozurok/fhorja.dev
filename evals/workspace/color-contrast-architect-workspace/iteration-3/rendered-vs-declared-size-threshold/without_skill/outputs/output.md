# Rendered vs Declared Size -- WCAG 2.2 Contrast Threshold Audit

## Inputs

- **Foreground token**: `color.text.helper` = `#767676`
- **Background token**: `color.surface.background` = `#FFFFFF`
- **Measured ratio**: `#767676` on `#FFFFFF` ≈ **4.54:1**
- **CSS**:
  ```css
  font-size: 18pt;
  @media (max-width: 600px) { font-size: 0.8em; }
  ```
- **Usage context**: mobile-first helper text under form inputs.

## WCAG 2.2 Size Thresholds (recap)

WCAG 2.2 SC 1.4.3 (Contrast Minimum, AA) defines:

- **Large text**: ≥ 18pt (or ≥ 14pt bold) → **3:1** AA
- **Normal text**: everything smaller → **4.5:1** AA

The threshold is determined by the size at which text is **actually presented to the user** (rendered size), not the size declared in source CSS. This is implicit in the WCAG definition of "large-scale text" -- the spec describes what the user sees, not what the author wrote. The W3C Understanding doc for 1.4.3 talks about text "at 18 point" as a property of the text the reader perceives.

## (1) Declared-size verdict (18pt)

- Declared size: 18pt → qualifies as **LARGE**.
- Threshold: **3:1 AA**.
- Measured ratio 4.54:1 ≥ 3:1.
- **Verdict at declared size: PASS (AA Large).**

## (2) Rendered-size verdict on mobile (≤ 600px viewport)

- Mobile rule applies `font-size: 0.8em` against the inherited 18pt cascade.
- Effective rendered size: 18pt × 0.8 = **14.4pt**.
- 14.4pt is **below the 18pt large-text boundary** (and below the 14pt-bold boundary, since helper text is not specified as bold).
- Therefore rendered text is classified as **NORMAL**.
- Threshold: **4.5:1 AA**.
- Measured ratio 4.54:1 ≥ 4.5:1 -- but only by **0.04**, which is within the rounding noise of typical contrast calculators. Different tools rounding to 1 vs 2 decimal places will report this as 4.5:1 (pass) or 4.54:1 (pass) but any small token shift (e.g., #777) drops it below.
- **Verdict at rendered size: TECHNICAL PASS, but borderline / fragile.**

## (3) Which verdict applies for WCAG compliance?

**The rendered-size verdict applies.** WCAG conformance is evaluated against the experience delivered to users on the device/viewport in question. On viewports ≤ 600px (the dominant case for "mobile-first helper text"), the helper text is rendered at ~14.4pt and must therefore meet the **NORMAL 4.5:1** threshold, not the LARGE 3:1 threshold suggested by the declared 18pt.

Per the persona's Step 4 framing: **rendered size wins over declared size.** Authoring intent does not override what assistive-tech users and low-vision users actually perceive.

So the operative verdict for this token-in-context is: **passes 4.5:1 by a 0.04 margin** -- technically conforming on `#FFFFFF` but with effectively zero engineering safety margin.

## (4) Remediation

Because the verdict is materially different at rendered size (3:1 LARGE → 4.5:1 NORMAL) and the current ratio sits on the edge of the 4.5:1 boundary:

1. **Darken the helper text token.** Move `color.text.helper` from `#767676` to at least `#757575` (≈4.6:1) or preferably `#717171` (≈4.74:1) / `#6E6E6E` (≈4.9:1) to create a genuine engineering margin above 4.5:1 and survive rounding, antialiasing, and downstream background shifts.
2. **Stop relying on the 18pt LARGE classification for this token.** Since `0.8em` at the mobile breakpoint forces it into NORMAL, design and review the token against 4.5:1 globally -- do not let the desktop 18pt rendering hide the mobile failure mode.
3. **Audit all surfaces using `color.text.helper`.** If any surface is not pure `#FFFFFF` (e.g., a tinted card background, a disabled-state surface), the ratio drops below 4.5:1 immediately. Either restrict the token to `#FFFFFF` backgrounds via lint rules, or pick a value that passes against the darkest legitimate background as well.
4. **Reconsider the responsive shrink.** `0.8em` on already-small helper text degrades legibility independently of contrast. Consider keeping helper text at the base size on mobile and shrinking only decorative/secondary type.
5. **Document the rule in the design-system contrast doc**: contrast thresholds are evaluated at **rendered** size across all breakpoints; declared `pt`/`px` sizes are not a defense.

## Summary table

| Layer | Size | Class | Threshold | Ratio | Verdict |
|---|---|---|---|---|---|
| Declared (CSS source) | 18pt | LARGE | 3:1 | 4.54:1 | Pass (misleading) |
| Rendered (≤600px viewport) | ~14.4pt | NORMAL | 4.5:1 | 4.54:1 | Pass -- borderline / fragile |
| **Governing verdict** | rendered | NORMAL | **4.5:1** | 4.54:1 | **Pass by 0.04 -- remediate** |
