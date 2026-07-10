# Focus indicator contrast audit -- primary button

WCAG 2.2 SC 1.4.11 requires the focus indicator to reach **>=3:1** against **EACH adjacent color**. For a ring sitting between the button interior and the page surface, that is two independent thresholds, both binding. Per SKILL Step 3 the ratios below use WCAG relative luminance (sRGB linearization, `L = 0.2126R + 0.7152G + 0.0722B`, ratio = `(L_light + 0.05) / (L_dark + 0.05)`), rounded to two decimals and never rounded up to clear a threshold.

## 1. Contrast matrix (3 ratios)

| # | Pair | Tokens | Hex | Ratio | Design context | AA threshold | Verdict |
|---|------|--------|-----|------:|----------------|-------------:|---------|
| 1 | Focus ring vs button interior | `color.focus.ring` / `color.button.primary.bg` | `#0099FF` / `#0066CC` | **1.86:1** | focus-indicator (inner adjacency) | 3.00:1 | **FAIL-AA** |
| 2 | Focus ring vs surrounding surface | `color.focus.ring` / `color.surface.background` | `#0099FF` / `#FFFFFF` | **2.99:1** (raw 2.9998) | focus-indicator (outer adjacency) | 3.00:1 | **FAIL-AA** |
| 3 | Button label vs button background (reference, SC 1.4.3) | `color.button.primary.fg` / `color.button.primary.bg` | `#FFFFFF` / `#0066CC` | **5.57:1** | normal-text | 4.5:1 | **PASS-AA** (fails AAA 7:1) |

## 2. Verdict per adjacency

- **Inner adjacency (ring vs `#0066CC` button interior): FAIL-AA at 1.86:1.** Both colors sit in the same blue family with very close luminance -- the ring is only ~1.07x lighter -- so it visually dissolves into the button face.
- **Outer adjacency (ring vs `#FFFFFF` surface): FAIL-AA at 2.99:1.** This is the classic "looks like it passes" trap: the raw value is 2.9998:1, which is below 3.00:1. Per SKILL Step 3, the persona MUST NOT round up to clear the threshold.
- **Label vs button (reference, not gated by SC 1.4.11): PASS-AA at 5.57:1.** Included only to confirm SC 1.4.3 is healthy and the primary-button color pair itself is not the regression source; the bug is isolated to the focus token.

## 3. Which adjacency fails

**BOTH adjacencies fail SC 1.4.11.** The inner adjacency fails by a wide margin (1.86:1 vs 3:1 required, a deficit of 1.14 contrast units). The outer adjacency fails by a hair (2.9998:1 vs 3:1 required, a deficit of 0.0002 -- but a fail is a fail; SC 1.4.11 is not a "close enough" criterion). This is the worst case for the persona's value: a token a casual eyeball check and a "we tested it on white" pass would both wave through, while real WCAG-compliant tooling rejects it.

## 4. Remediation (concrete token delta)

The geometric constraint matters here, so I show the math before the token:

> Button interior `#0066CC` has relative luminance `L_btn ≈ 0.1303`. Surface `#FFFFFF` has `L_sur = 1.0`. To clear 3:1 against the surface, the ring needs `L_ring <= 0.30`. To clear 3:1 against the button interior, the ring needs `L_ring <= 0.0101` OR `L_ring >= 0.4909`. **The intersection that satisfies both is `L_ring <= 0.0101`, i.e. a near-black ring.** A lighter ring (the intuitive "make the focus ring brighter" instinct) cannot satisfy both adjacencies simultaneously against this button+surface pair, because any color light enough to contrast with `#0066CC` from above will fail against `#FFFFFF`.

### Recommended token delta (primary remediation)

Retarget `color.focus.ring` from `#0099FF` to a near-black focus token aliased to the existing neutral ramp:

```diff
- color.focus.ring = #0099FF   // fails SC 1.4.11 on both adjacencies
+ color.focus.ring = {color.neutral.900}   // resolves to #0A0A0A (or your darkest neutral, must satisfy L <= 0.0101)
```

Verification with `#0A0A0A`:

| Pair | Ratio | Threshold | Verdict |
|------|------:|----------:|---------|
| Ring `#0A0A0A` vs button `#0066CC` | **3.56:1** | 3.00:1 | PASS-AA |
| Ring `#0A0A0A` vs surface `#FFFFFF` | **19.80:1** | 3.00:1 | PASS-AAA-equivalent |

Both adjacencies clear with margin. If `color.neutral.900` in this design system is darker than `#0A0A0A` (e.g. `#000000` at 3.77:1 / 21:1) it passes by even more; if it is lighter than `#1A1A1A` (3.13:1 / 17.4:1) it still passes; if it sits above `#212121` (2.89:1 vs button) it fails -- so the persona pins the constraint, not just the hex.

### Alternative remediation (if brand requires a colored focus ring)

A single-color blue ring cannot satisfy both adjacencies against this particular button+surface pair (see math above). Three escape hatches that keep blue:

1. **Two-layer ring (offset focus pattern):** outer ring `#FFFFFF` (matches surface, invisible) + middle ring `#0A0A0A` (the load-bearing 3:1 layer) + retain `#0099FF` as a decorative inner halo. SC 1.4.11 is satisfied by the middle ring; the blue stays as brand expression. This is the WAI-ARIA-recommended "double ring" pattern.
2. **Move the ring outside, then darken the surface adjacency only:** keep `#0099FF` as ring but introduce a 1px `#0A0A0A` outer outline. The blue meets the button (still fails 3:1 there -- so this only works if the ring is placed entirely outside the button edge, not straddling it, which changes the visual model).
3. **Darken the button bg** so a lighter ring becomes geometrically feasible (e.g. `color.button.primary.bg = #003D7A`, `L = 0.041`). This ripples through every primary-button consumer and is the highest-blast-radius option; flag for `decision-interview` before pursuing.

**Recommended path: option 1 (two-layer ring).** Lowest blast radius, preserves brand blue, makes the WCAG-load-bearing layer explicit in the token graph.

### Token-policy note for `DECISIONS.md`

Per SKILL Step 7, the contrast policy choice that needs to land in `DECISIONS.md ## Locked decisions` is: *"Focus indicator (SC 1.4.11) is evaluated against every documented adjacency, not just the surface. `color.focus.ring` MUST satisfy 3:1 against both `color.surface.background` AND every `color.*.bg` token it can sit on top of; tokens that cannot meet this with a single color MUST use the two-layer ring pattern with the load-bearing layer aliased to `color.neutral.900` or darker."* This generalizes the fix so the next colored button (success green, danger red, etc.) does not repeat the bug.
