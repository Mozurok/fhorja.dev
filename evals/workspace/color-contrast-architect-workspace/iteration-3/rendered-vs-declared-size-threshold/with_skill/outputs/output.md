# Contrast threshold audit: rendered vs declared text size

## Inputs

- Foreground token: `color.text.helper` = `#767676`
- Background token: `color.surface.background` = `#FFFFFF`
- Computed ratio: **4.54:1** (per WCAG 2.2 relative luminance formula)
- Declared CSS: `font-size: 18pt`
- Mobile override (`max-width: 600px`): `font-size: 0.8em` → renders at ~**14.4pt**
- Usage context: mobile-first helper text under inputs

## (1) Declared-size threshold verdict

At the declared **18pt**, WCAG 2.2 classifies this as **LARGE text** (>=18pt, or >=14pt bold).

- Applicable AA threshold: **3:1**
- Measured ratio: **4.54:1**
- Verdict: **PASS-AA (large-text context)**
- Note: also passes AAA for large text (>=4.5:1 = 4.54:1, scrapes through; do not round up).

## (2) Rendered-size threshold verdict (mobile, <=600px)

At rendered **~14.4pt**, the text falls **below** the 18pt LARGE-text boundary. WCAG 2.2 does not interpolate -- the boundary is hard. 14.4pt is not >=18pt, and it is not >=14pt **bold** (helper text under inputs is regular weight by default). Therefore it classifies as **NORMAL text**.

- Applicable AA threshold: **4.5:1**
- Measured ratio: **4.54:1**
- Verdict: **PASS-AA (normal-text context), by a 0.04 margin**
- AAA verdict: **FAIL-AAA** (AAA normal text requires >=7:1).

## (3) Which verdict applies for WCAG compliance?

**The rendered-size verdict applies. Score against NORMAL text (4.5:1 AA).**

Reasoning (per WCAG 2.2 and Step 4 of this persona's classification rules):

1. **WCAG measures what the user actually sees**, not what the stylesheet declares. The Understanding documents for SC 1.4.3 (Contrast Minimum) and the definition of "large scale" in WCAG 2.2 both anchor the threshold to the **rendered** font size after CSS cascade, media queries, user agent zoom, and root font-size resolution. A declared 18pt that the responsive stylesheet itself shrinks to 14.4pt is presented to the user at 14.4pt; that is the size the accessibility evaluator must score.
2. **The page's own CSS is doing the shrinking**, not a user-side adaptation. This is not the "user zoomed out" edge case where some advocate scoring against the author's intent -- the author's stylesheet explicitly renders the smaller size on the most common viewport class (mobile, <=600px). The mobile rendering IS the design.
3. **Multi-context rule (persona Step 4):** when a pair serves multiple rendered contexts (large on desktop, normal on mobile), score against the **strictest applicable threshold**. Here that is NORMAL-text 4.5:1 AA.
4. **Token is declared as `color.text.helper` used in mobile-first helper text under inputs** -- the dominant rendering context is the smaller one. Scoring against the declared 18pt would manufacture false confidence for the primary use case.

**Compliance result: PASS-AA, but the margin is 0.04 (4.54:1 vs 4.5:1 required).** This is a fragile pass: any future tweak to either token, any sub-pixel anti-aliasing assumption, or any rendering on a lower-gamut display will likely tip it below the threshold. It also fails AAA.

## (4) Remediation (verdict differs by size)

The verdict differs (PASS-AAA at declared size; barely PASS-AA at rendered size; FAIL-AAA at rendered size). Three options, ordered from preferred to deferred:

### Option A (recommended): darken `color.text.helper` to widen the margin

Adjust the token so the rendered NORMAL-text classification passes with a defensible margin rather than scraping AA by 0.04.

- Proposed value: `#767676` → **`#717171`** raises ratio from 4.54:1 to ~4.74:1 (still AA, comfortable margin, no design change).
- Stronger option for AAA-leaning systems: `#767676` → **`#595959`** raises ratio to ~7.0:1 (PASS-AAA at both sizes).
- Token impact: single value edit in `foundations/color.md` (or DTCG JSON); propagates to every consumer of `color.text.helper`. No component rewrite.
- This is the load-bearing remediation per persona quality bar: a single token-value edit that resolves the fragile pass before the design system locks.

### Option B: remove the responsive shrink for helper text

Override the `0.8em` rule for the helper-text class so it stays at 18pt (LARGE) on mobile, preserving the 3:1 threshold and the existing 4.54:1 ratio.

- CSS impact: scoped media-query exception for `.helper-text` (or whatever class consumes `color.text.helper`).
- Trade-off: changes the visual rhythm on mobile; may conflict with the responsive type scale's intent.
- Use only if the type scale review confirms 18pt helper text is acceptable on small screens.

### Option C: reclassify and document a deferral (not recommended here)

Accept the 0.04-margin AA pass as sufficient and document it as an explicit deferral with a known-debt note in `CONTRAST_AUDIT.md`.

- This is the weakest path because the persona's value is preventing exactly this kind of fragile pass from locking. Use only if Options A and B are both vetoed by design lock-in.

## Tooling caveat (persona Step 8)

- The 14.4pt rendered size assumes the parent's computed `font-size` resolves to 18pt at the time the `0.8em` rule applies (i.e. `em` is relative to the inherited size, not the declared one on the same element). If the responsive override actually reads `font-size: 0.8em` on the same element that declared `font-size: 18pt`, the cascade order matters: the media-query rule wins and `0.8em` resolves against the **parent's** computed font-size, not 18pt. A human reviewer should confirm the rendered px size in DevTools on a <=600px viewport before locking the token delta.
- The `#767676` on `#FFFFFF` ratio of 4.54:1 is taken as given; recompute with the standard WCAG 2.2 formula if the token values change.

## Recommended next command

`decision-interview` -- to lock the contrast policy choice (Option A token darken vs Option B responsive exception) before the token locks downstream.
