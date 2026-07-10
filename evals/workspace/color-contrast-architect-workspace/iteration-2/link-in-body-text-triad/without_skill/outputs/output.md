# Color Triad Audit: Inline Link in Body Text

## Inputs
- Page surface (background): `color.surface.background` = `#FFFFFF` (rgb 255,255,255)
- Body text: `color.text.primary` = `#222222` (rgb 34,34,34)
- Inline link: `color.link.default` = `#0033AA` (rgb 0,51,170)
- Link visual treatment: **color only** (no underline, no weight change, no other non-color indicator)

Relative luminance (WCAG formula, sRGB → linear, then `0.2126·R + 0.7152·G + 0.0722·B`):

| Color | Hex | Linear R | Linear G | Linear B | Luminance L |
|---|---|---|---|---|---|
| White background | #FFFFFF | 1.0000 | 1.0000 | 1.0000 | **1.0000** |
| Body #222222 | #222222 | 0.0144 | 0.0144 | 0.0144 | **0.01444** |
| Link #0033AA | #0033AA | 0.0000 | 0.0319 | 0.3994 | **0.05170** |

Contrast = (L_lighter + 0.05) / (L_darker + 0.05).

---

## 1. Pair audits

### Pair A -- Body text on background (#222222 on #FFFFFF)
- Contrast = (1.0 + 0.05) / (0.01444 + 0.05) = 1.05 / 0.06444 = **~16.30 : 1**
- WCAG 2.2 SC 1.4.3 Contrast (Minimum), AA, normal text: requires ≥ 4.5 : 1 -- **PASS**
- SC 1.4.6 AAA (≥ 7 : 1) -- **PASS**
- Verdict: **PASS (AAA)**.

### Pair B -- Link on background (#0033AA on #FFFFFF)
- Contrast = (1.0 + 0.05) / (0.05170 + 0.05) = 1.05 / 0.10170 = **~10.32 : 1**
- SC 1.4.3 AA normal text (≥ 4.5 : 1) -- **PASS**
- SC 1.4.6 AAA (≥ 7 : 1) -- **PASS**
- Verdict: **PASS (AAA)**. The link, read against the page, is legible.

### Pair C -- Link on body text (#0033AA vs #222222)  ← the SC 1.4.1 decider
- Contrast = (0.05170 + 0.05) / (0.01444 + 0.05) = 0.10170 / 0.06444 = **~1.58 : 1**
- SC 1.4.1 Use of Color requires that, when color is the *only* visual means of conveying that a string is a link, the link color must contrast with surrounding body text at **≥ 3 : 1** (and the link must also still meet 4.5:1 against the background, which it does -- see Pair B).
- 1.58 : 1 is **well below 3 : 1**.
- Verdict: **FAIL**.

---

## 2. SC 1.4.1 (Use of Color) analysis

SC 1.4.1 / WCAG 2.2 AA, paraphrased for this case: a link inside a block of text may be distinguished by color alone **only if** the link color contrasts ≥ 3 : 1 with the surrounding text color **AND** an additional non-color visual indicator appears on hover/focus.

This design fails both halves:

1. Link-vs-body contrast is **1.58 : 1**, far under the 3 : 1 floor. A user with red–green or blue–yellow color vision deficiency, low vision, a monochrome display, a printed page, or simply a glance at small text on a bright screen cannot reliably tell the link apart from the surrounding body copy.
2. There is no underline, weight change, italic, icon, bracketing, or other non-color cue in the default state -- so even sighted users with normal color vision must rely entirely on the hue difference, which is exactly what SC 1.4.1 forbids when that hue difference is this weak.

The team's rationale ("the color is enough") is the specific failure mode SC 1.4.1 was written to prevent. "Visually noisy" is a stylistic preference; "discoverable as a link" is a conformance requirement.

---

## 3. Overall verdict: does "color only, no underline" meet WCAG 2.2 AA here?

**No. This triad does not conform to WCAG 2.2 AA.**

- Pair A (body/bg): passes.
- Pair B (link/bg): passes.
- Pair C (link/body) at **1.58 : 1** with no non-color indicator: **fails SC 1.4.1 (Use of Color), Level A**.

Note this is a **Level A** failure, not just AA -- SC 1.4.1 is Level A, so the design fails the lowest conformance bar, not merely AA.

---

## 4. Remediation options

Ordered by how cheap and how durable the fix is.

### Option 1 -- Restore the underline on inline links (recommended)
Add `text-decoration: underline` to `color.link.default` usage in body copy. This is the canonical, universally understood non-color indicator. It satisfies SC 1.4.1 regardless of the link/body contrast ratio, works in print and grayscale, and survives users who override colors (forced-colors / high-contrast modes). The team's "visual noise" concern is usually solved by tuning underline thickness and offset (`text-decoration-thickness`, `text-underline-offset`) rather than removing it.

- Pros: one-line change, conforms at AA and AAA, robust across CVD, print, forced-colors, and small text.
- Cons: aesthetic objection from the team -- but this is the lowest-risk, longest-lived fix.

### Option 2 -- Keep color-only, but raise link/body contrast to ≥ 3 : 1 AND add a non-color hover/focus indicator
SC 1.4.1 still requires a non-color cue on interaction (hover/focus) even if the 3:1 link/body contrast is met. To hit 3:1 against `#222222` you need a substantially lighter link color, but it must still hit 4.5:1 against `#FFFFFF` (Pair B), which squeezes the usable hue range hard. Practically you end up with a saturated mid-tone (e.g. a vivid teal/blue around L ≈ 0.18–0.22) and you still must add underline-on-hover and a visible focus ring.

- Pros: preserves the "clean prose" aesthetic in the resting state.
- Cons: fragile -- most "nice looking" link blues that pass 4.5:1 on white fail 3:1 against `#222`. Requires careful token work, ongoing enforcement, and *still* needs a non-color hover/focus treatment. Does not help printed output or forced-colors users.

### Option 3 -- Non-color, non-underline indicator (e.g. weight, small icon, bracketed glyph)
Make links `font-weight: 600` or append an inline "↗" / "→" glyph. Satisfies SC 1.4.1 by giving a non-color cue.

- Pros: avoids underline if the team genuinely cannot tolerate it.
- Cons: weight-only is borderline (some assistive tooling and low-vision users find weight differences subtle); icon-only changes layout/wrapping. Generally less robust than underline.

### Option 4 -- Move the call-to-action out of inline prose
If something truly must not be visually noisy, promote it to a button or a separate "Learn more" affordance below the paragraph. Then the inline body stops needing inline links at all.

- Pros: sidesteps the conflict.
- Cons: changes information architecture; not always possible.

---

## Recommendation

Ship **Option 1** (underline) as the default treatment for `color.link.default` in body context, with tuned `text-decoration-thickness` and `text-underline-offset` to address the "noisy" concern. Document at the token level that `color.link.default` **must not be used as the sole link indicator**, so this regression cannot be reintroduced by another team. Keep the current hex values -- they pass Pairs A and B comfortably; the failure is in the visual-indicator policy, not the palette.
