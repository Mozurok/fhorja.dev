# Contrast audit -- `color.text.overlay-on-image` (alpha 0.85)

## Step 1 -- Pair scope

Documented pair under audit (light theme):

| Foreground token | Raw value | Background | Design context |
|---|---|---|---|
| `color.text.overlay-on-image` | `rgba(255, 255, 255, 0.85)` | Hero image surface (uncontrolled) | `normal-text` (captions over hero photos on homepage + product pages) |

Background is **not a design-system token** -- it is an arbitrary photographic surface. Per Step 2 token resolution, the background does not resolve to a single sRGB hex. The persona's contract requires the audit to score against the strictest applicable threshold, which here means scoring against the **worst-case background luminance the documented usage actually permits**. Because hero photos span white-dominant to dark, the audit must enumerate the range as discrete scenarios and judge the token across the full range -- a single "average" number would manufacture false confidence.

## Step 2 -- Compositing math (foreground over background through alpha 0.85)

The browser composites `rgba(255, 255, 255, 0.85)` over the backdrop **before** WCAG sees the pixel. The composed sRGB channel per Porter-Duff "source-over":

```
C_out = α · C_fg + (1 − α) · C_bg
      = 0.85 · 255 + 0.15 · C_bg
      = 216.75 + 0.15 · C_bg
```

Composed values per scenario (rounded to integer sRGB for hex display; relative luminance computed from the unrounded composed channel):

| Scenario | Backdrop | Composed foreground (sRGB) | Composed hex (approx) |
|---|---|---|---|
| (a) White-dominant photo | `#FFFFFF` (255,255,255) | (255, 255, 255) | `#FFFFFF` |
| (b) Mid-tone photo | `#808080` (128,128,128) | (236.0, 236.0, 236.0) | `#ECECEC` |
| (c) Dark lifestyle photo | `#1A1A1A` (26,26,26) | (220.65, 220.65, 220.65) | `#DCDCDC` |

WCAG 2.2 relative luminance (sRGB linearization, then `L = 0.2126 R + 0.7152 G + 0.0722 B`) and contrast ratio vs the **original backdrop** (the pixel actually behind the composed text):

| Scenario | L(composed fg) | L(backdrop) | Ratio (L_light + 0.05) / (L_dark + 0.05) |
|---|---|---|---|
| (a) over `#FFFFFF` | 1.0000 | 1.0000 | **1.00 : 1** |
| (b) over `#808080` | 0.8307 | 0.2159 | **3.16 : 1** |
| (c) over `#1A1A1A` | 0.7011 | 0.0152 | **12.71 : 1** |

(Two-decimal rounding; never rounded up to clear a threshold.)

## Step 3 -- Verdict per scenario (normal-text, WCAG 2.2 AA = 4.5:1, AAA = 7:1)

| # | Scenario | Ratio | AA (4.5:1) | AAA (7:1) | Verdict |
|---|---|---|---|---|---|
| (a) | Composed white over white photo | 1.00:1 | FAIL | FAIL | **FAIL-AA** (text effectively invisible) |
| (b) | Composed white over mid-tone `#808080` | 3.16:1 | FAIL | FAIL | **FAIL-AA** (would only pass the 3:1 large-text or UI-component bar, and this token is documented as normal-text) |
| (c) | Composed white over dark `#1A1A1A` | 12.71:1 | PASS | PASS | **PASS-AAA** |

## Step 4 -- Token-level verdict across the documented range

**FAIL-AA.**

The token is documented for `normal-text` captions over hero photos that the design system does not control. Two of three representative backdrops in the documented range fail WCAG 2.2 AA, and one of them (the white-dominant case) collapses to 1.00:1, which is a total legibility failure independent of WCAG thresholds. The token cannot be considered "passing" simply because the dark-photo case clears AAA -- accessibility is governed by the worst case a user will actually encounter, not the best case.

Equally important: alpha compositing means the **same token** produces different ratios on every page load depending on what hero image the CMS serves. A token whose contrast is a function of uncontrolled image content cannot be statically certified at all.

## Step 5 -- Compositing-aware contrast matrix (for `CONTRAST_AUDIT.md`)

| theme | foreground_token | background | design_context | composed_fg | ratio | AA | AAA | verdict |
|---|---|---|---|---|---|---|---|---|
| light | `color.text.overlay-on-image` (α 0.85) | image `#FFFFFF` | normal-text | `#FFFFFF` | 1.00:1 | 4.5 | 7 | FAIL-AA |
| light | `color.text.overlay-on-image` (α 0.85) | image `#808080` | normal-text | `#ECECEC` | 3.16:1 | 4.5 | 7 | FAIL-AA |
| light | `color.text.overlay-on-image` (α 0.85) | image `#1A1A1A` | normal-text | `#DCDCDC` | 12.71:1 | 4.5 | 7 | PASS-AAA |

Summary count: 3 scenarios audited / 1 PASS-AAA / 0 PASS-AA / 2 FAIL-AA / 0 UNRESOLVED.

## Step 6 -- Remediation (ranked by robustness)

The root cause is that **a semi-transparent foreground token can never be certified against an uncontrolled backdrop range**. Remediation must remove the dependency on the image, not adjust the alpha.

**R1 (recommended) -- Introduce a guaranteed opaque scrim layer between image and text.**
Define a new token `color.scrim.overlay-on-image = rgba(0, 0, 0, 0.55)` (or a linear gradient `rgba(0,0,0,0.7) -> rgba(0,0,0,0.2)`) rendered as a full-bleed layer behind the caption. Change `color.text.overlay-on-image` to fully opaque `#FFFFFF` (α 1.0). The contrast pair becomes "opaque white over the composed scrim+image surface", and the scrim guarantees the effective backdrop luminance stays in a range where 4.5:1 is met. Document the scrim as a **required co-token**: the caption token cannot be used without the scrim token. This is the only remediation that survives an uncontrolled CMS image pipeline.

**R2 -- Replace alpha with a text-shadow or stroke that brings its own contrast.**
Keep `color.text.overlay-on-image` opaque `#FFFFFF` and add a token `effect.text.overlay-shadow = 0 1px 3px rgba(0,0,0,0.85)`. WCAG-wise this is weaker than R1 because text-shadow is not a substitute for foreground/background contrast under the spec, but for typography it materially improves legibility on mid-tone and light backdrops. Use R2 **only in combination with R1**, not as a substitute.

**R3 -- Reclassify the design context and accept the deferral, with hard guardrails.**
If product genuinely needs the translucent aesthetic, reclassify the token as `large-text` (18pt+ or 14pt+ bold) AND constrain the documented usage to "hero captions where editorial verifies a hero image of luminance ≤ 0.18 (i.e. clearly dark)". Even then, the white-over-white scenario still fails -- so this requires a CMS-side constraint (e.g. lint hero image average luminance at upload time, reject anything above a threshold). This pushes the accessibility guarantee out of the design system and into the content pipeline, which is acceptable only if the pipeline actually enforces it. Without that enforcement, R3 is a documented FAIL dressed up as policy.

**Not recommended -- adjusting alpha alone.**
Raising alpha to 1.0 fixes (a) and (b) only because it eliminates the compositing problem entirely. At that point the token is just opaque white, and the legibility on light photos still fails (1.00:1). Alpha is not the lever; the scrim is.

## Step 7 -- PROPOSED blocks

```markdown
### PROPOSED -- DECISIONS.md ## Locked decisions (D-N: overlay-on-image contrast policy)
- Contrast target: WCAG 2.2 AA for all normal-text tokens, including overlay-on-image.
- Semi-transparent foreground tokens applied over uncontrolled surfaces (CMS images, user-uploaded media) are PROHIBITED unless paired with a required opaque scrim token that guarantees the composed backdrop luminance falls in a range where the token meets its applicable WCAG threshold.
- `color.text.overlay-on-image` is promoted to fully opaque (`#FFFFFF`, α 1.0) and renamed to require co-token `color.scrim.overlay-on-image` in every documented usage.
- New token: `color.scrim.overlay-on-image = rgba(0, 0, 0, 0.55)` (or gradient equivalent), required behind every overlay caption.
- Deferred-with-policy: hero captions on existing pages may continue to render without the scrim for one release cycle, tracked as accessibility debt in IMPLEMENTATION_PLAN.md ## Risks and mitigations.
```

```markdown
### PROPOSED -- IMPLEMENTATION_PLAN.md ## Risks and mitigations
- Risk: `color.text.overlay-on-image` at α 0.85 fails WCAG 2.2 AA on white-dominant and mid-tone hero images (1.00:1 and 3.16:1 respectively). Two of three representative backdrops fail; full token range cannot be statically certified because background luminance is image-dependent.
- Mitigation: introduce required `color.scrim.overlay-on-image` co-token and migrate all hero-caption consumers to render the scrim before the caption. Token migration is a single design-system release; consumer migration is N components (audit via `atom-audit`).
- Until migration completes, treat every hero-caption surface as accessibility debt. Do not ship new hero-caption surfaces using the un-scrimmed token.
```

## Step 8 -- Tooling caveats

- The mid-tone (`#808080`) and dark (`#1A1A1A`) scenarios are representative samples, not exhaustive. A real hero image is a per-pixel luminance distribution; the composed text overlays many backdrop luminances simultaneously. The 3.16:1 and 12.71:1 numbers describe the **uniform-backdrop case** only. In practice the worst pixel under the text governs perceived legibility, and that worst pixel is unknown at token-definition time. This reinforces R1: only an opaque scrim makes the math deterministic.
- Compositing math assumes the browser performs alpha blending in sRGB space (the web platform default). Some design tools blend in linear-light space and will report slightly different composed values; the WCAG ratio is computed on the rendered sRGB pixel, so the sRGB-space math above is the audit-of-record.
- WCAG 2.2 does not currently model alpha explicitly; it scores the rendered composed pixel against the backdrop. The persona has applied this interpretation consistently. APCA (WCAG 3 draft) would score this pair differently but is not the locked target.

## Recommended next command

`decision-interview` -- the contrast policy choice (prohibit α<1.0 foreground tokens over uncontrolled surfaces without a required scrim) is a load-bearing design-system rule that needs explicit owner sign-off before the token rename and scrim introduction land in `foundations/color.md`.
