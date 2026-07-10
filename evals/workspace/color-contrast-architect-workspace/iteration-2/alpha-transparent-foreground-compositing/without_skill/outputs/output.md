# Contrast Audit: `color.text.overlay-on-image` (rgba(255, 255, 255, 0.85))

## Scope and Method

The foreground token is semi-transparent white. WCAG contrast is defined on *opaque* colors, so the actual evaluated foreground is the **composed** color: `fg_rgba` painted over the effective background, producing an opaque RGB triplet. I compose using the standard Porter-Duff "source-over" with straight alpha:

```
C_out = α * C_fg + (1 - α) * C_bg
```

with α = 0.85, C_fg = (255, 255, 255). Then I compute relative luminance per WCAG 2.x (sRGB → linearize → luminance), and contrast = (L_lighter + 0.05) / (L_darker + 0.05).

Text classification: **normal text** (captions). WCAG 2.2 AA threshold: **4.5:1**. AAA: 7:1.

---

## Step 1 -- Resolve composed foreground per scenario

| Scenario | Background (hex) | Background (RGB) | Composed FG = 0.85·(255,255,255) + 0.15·BG |
|---|---|---|---|
| (a) White-dominant photo | #FFFFFF | (255, 255, 255) | (255, 255, 255) |
| (b) Mid-tone photo | #808080 | (128, 128, 128) | (236.05, 236.05, 236.05) ≈ #ECECEC |
| (c) Dark / lifestyle photo | #1A1A1A | (26, 26, 26) | (220.65, 220.65, 220.65) ≈ #DCDCDC |

(I round to the nearest integer channel for the luminance step; differences from the unrounded value are < 0.01:1 and don't change the verdict.)

---

## Step 2 -- Compute WCAG contrast per scenario

Relative luminance (sRGB):
- L(#FFFFFF) = 1.0000
- L(#ECECEC) ≈ 0.8053
- L(#DCDCDC) ≈ 0.7011
- L(#808080) ≈ 0.2159
- L(#1A1A1A) ≈ 0.0118

### (a) Composed fg over white background
- Foreground: #FFFFFF (L = 1.0000)
- Background: #FFFFFF (L = 1.0000)
- **Contrast = 1.00 : 1**

### (b) Composed fg over mid-tone background
- Foreground: ~#ECECEC (L ≈ 0.8053)
- Background: #808080 (L ≈ 0.2159)
- Contrast = (0.8053 + 0.05) / (0.2159 + 0.05) = 0.8553 / 0.2659
- **Contrast ≈ 3.22 : 1**

### (c) Composed fg over dark background
- Foreground: ~#DCDCDC (L ≈ 0.7011)
- Background: #1A1A1A (L ≈ 0.0118)
- Contrast = (0.7011 + 0.05) / (0.0118 + 0.05) = 0.7511 / 0.0618
- **Contrast ≈ 12.15 : 1**

---

## Step 3 -- Per-scenario verdict

| Scenario | Effective contrast | Normal text AA (4.5:1) | Verdict |
|---|---:|---|---|
| (a) White-dominant photo (e.g., cloud, snow, light sky) | **1.00 : 1** | Fails (catastrophically) | **FAIL** -- text is essentially invisible |
| (b) Mid-tone photo (typical product shot, skin tones, foliage) | **3.22 : 1** | Below 4.5:1 (also below 3:1 large-text threshold *if* it were large; but this is normal text) | **FAIL** |
| (c) Dark / lifestyle photo | **12.15 : 1** | Passes AA and AAA comfortably | **PASS** |

Note: the alpha=0.85 only meaningfully reduces contrast on dark backgrounds (where it lets a small amount of the dark BG through and dims the white). On light backgrounds the alpha is irrelevant to the failure -- pure opaque white on white would also be 1:1. The token is broken at both ends of the range, not just because of the alpha.

---

## Step 4 -- Overall verdict across the documented range

**FAIL.** The token `color.text.overlay-on-image` cannot be claimed to meet WCAG 2.2 AA across the documented use range. It only passes when the underlying image is dark (≈ #333 or darker across the entire caption footprint). Hero images at Fhorja are explicitly described as ranging from white-dominant to dark, and the design system has no control over which image ships. A token whose accessibility depends on uncontrolled, author-supplied image content cannot be considered AA-conformant.

Additional risk factors not captured by the worst-case math:
- Real hero photos are non-uniform. Even a mostly-dark photo can have a bright highlight (sun, sky, specular) directly under the caption, dropping local contrast to the (a) or (b) regime within a single caption.
- JPEG compression and image-CDN re-encodes shift mid-tones unpredictably; a caption that tests at 4.8:1 on a reference asset can drop below 4.5:1 in production.
- The alpha=0.85 makes the dark-background pass *weaker*, not stronger -- it's costing roughly 1.3:1 of headroom (opaque white on #1A1A1A is ~17.4:1; composed is ~12.15:1). That headroom matters once the image has bright regions.

---

## Step 5 -- Remediation

Pick one of these; do not ship the token as currently documented.

**Option 1 -- Required overlay scrim (recommended).** Treat the *image + scrim* as the background, not the raw image. Require any caption using this token to sit on top of a deterministic darkening layer:
- Linear gradient scrim from `rgba(0,0,0,0.55)` at the caption baseline fading up, OR a uniform `rgba(0,0,0,0.55)` plate behind the caption block.
- With the scrim, the effective background under the composed foreground is bounded. Worst case (composed white-on-white photo with 0.55 black scrim) yields an effective BG of (115, 115, 115), composed FG ≈ (234, 234, 234), contrast ≈ 3.9:1 -- still short. Push the scrim to `rgba(0,0,0,0.7)` (effective BG ≤ (77,77,77)), and worst-case contrast clears 4.5:1 across the documented image range.
- Document the scrim as part of the token's contract: "this token MUST be paired with `surface.overlay.scrim` at opacity ≥ 0.7, applied to the caption region."

**Option 2 -- Drop alpha; pair with a mandatory caption plate.** Replace the token with opaque `#FFFFFF` on an opaque dark plate (e.g., `#1A1A1A` 90%+). This is the "card on photo" pattern. Simpler to validate; loses the airy/transparent visual.

**Option 3 -- Per-image testing gate.** Keep the token but require every hero image to pass an automated contrast check against the caption's bounding box (tools: APCA or WCAG ratio measured on the actual pixel region). Hard to enforce in a CMS-driven hero pipeline; only viable if there's a CI step on image upload.

**Option 4 -- Text shadow / stroke fallback.** A 1-2px dark text-shadow can rescue light-background cases visually but is **not** a WCAG-compliant remediation -- WCAG 2.x contrast is measured on the glyph color vs. the background pixel directly under the glyph, and shadows are not credited. Use only as a defense-in-depth complement to Option 1, not as a primary fix.

**Recommended path:** Option 1. It keeps the existing transparency aesthetic, fixes the math, and is enforceable as a token-pairing rule in the design system rather than an image-pipeline rule.

---

## Documentation fix the design system owes

Whatever remediation is chosen, the token's documented usage rule is currently wrong. It should change from:

> "used for captions placed over hero images on the homepage and product pages"

to something enforceable, e.g.:

> "Used only on top of `surface.overlay.scrim` (≥ 0.7 black) over hero imagery. Direct use on raw imagery is prohibited; AA contrast is not guaranteed without the scrim."

Without that contract change, the token will keep being misused even after the visual fix lands.