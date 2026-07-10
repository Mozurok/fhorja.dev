# Focus Indicator Double-Adjacency Audit

## 1. Contrast Ratios

Computed using WCAG relative luminance formula:
- L = 0.2126·R + 0.7152·G + 0.0722·B (with sRGB linearization)
- Ratio = (L_lighter + 0.05) / (L_darker + 0.05)

Relative luminances:
- `#0066CC` (button bg) → L ≈ 0.1444
- `#FFFFFF` (surface, label) → L ≈ 1.0000
- `#0099FF` (focus ring) → L ≈ 0.3194

| Pair | Computation | Ratio |
|---|---|---|
| **Ring (`#0099FF`) vs Button interior (`#0066CC`)** | (0.3194 + 0.05) / (0.1444 + 0.05) | **≈ 1.90 : 1** |
| **Ring (`#0099FF`) vs Surface (`#FFFFFF`)** | (1.0000 + 0.05) / (0.3194 + 0.05) | **≈ 2.84 : 1** |
| Label (`#FFFFFF`) vs Button bg (`#0066CC`) -- reference | (1.0000 + 0.05) / (0.1444 + 0.05) | **≈ 5.41 : 1** |

## 2. Verdict Per Adjacency

WCAG 2.2 SC 1.4.11 (Non-text Contrast) threshold: **≥ 3:1**.

| Adjacency | Ratio | Required | Verdict |
|---|---|---|---|
| Ring vs button interior `#0066CC` | 1.90 : 1 | 3.00 : 1 | **FAIL** |
| Ring vs surface `#FFFFFF` | 2.84 : 1 | 3.00 : 1 | **FAIL** |
| Label vs button bg (reference, SC 1.4.3) | 5.41 : 1 | 4.50 : 1 | PASS |

## 3. Which Adjacency Fails

**Both adjacencies fail.** The focus ring `#0099FF`:
- Is too close in luminance to the button interior `#0066CC` (only 1.90:1 -- same hue family, both mid-luminance blues, the lighter blue does not separate enough from the darker blue).
- Is also too close in luminance to the white surface (2.84:1 -- just below threshold; a saturated mid-blue against pure white is brighter than designers often intuit, but still not bright enough relative to white).

This is the classic "single-color focus ring squeezed between a colored control and a light surface" failure mode. A single tone cannot satisfy both sides when the control's interior is a mid-luminance color and the surface is near-white, because any color light enough to clear 3:1 against `#0066CC` is too light to clear 3:1 against `#FFFFFF`, and vice versa.

## 4. Remediation (Token Delta)

A single solid ring color cannot satisfy both adjacencies here. There are three viable fixes; pick one based on design intent.

### Option A (recommended): Two-tone ring (outer dark + inner light halo)

Introduce a layered focus indicator: a dark outer stroke that contrasts against the white surface, and a light inner halo that contrasts against the button interior. This is the WAI-recommended pattern for SC 1.4.11 double-adjacency.

```diff
- color.focus.ring: "#0099FF"
+ color.focus.ring.outer: "#003D7A"   // dark navy, 2px outer stroke
+ color.focus.ring.inner: "#FFFFFF"   // 2px inner halo between ring and button fill
```

Verification:
- Outer `#003D7A` (L ≈ 0.046) vs surface `#FFFFFF`: ≈ **7.79 : 1** PASS
- Outer `#003D7A` vs button `#0066CC` (L ≈ 0.144): ≈ **2.04 : 1** -- but it is not adjacent to the button, the white halo is.
- Inner halo `#FFFFFF` vs button `#0066CC`: ≈ **5.41 : 1** PASS
- Inner halo `#FFFFFF` vs outer `#003D7A`: ≈ **7.79 : 1** PASS

All adjacent pairs ≥ 3:1. This is the cleanest WCAG-compliant solution and reads as a crisp focus state on both light and dark controls.

### Option B: Single high-contrast ring against the surface, placed outside the button with an inner gap

If a two-tone ring is not acceptable, darken the ring substantially and rely on a transparent gap (no fill) between the ring and the button so the ring's adjacency on the inner side becomes the surface, not the button.

```diff
- color.focus.ring: "#0099FF"
+ color.focus.ring: "#003D7A"   // dark navy
+ focus.ring.offset: 2px        // transparent gap; both sides of ring are surface
```

Verification:
- Ring `#003D7A` vs surface `#FFFFFF` (both sides, because offset gap = surface): ≈ **7.79 : 1** PASS

The gap converts the inner adjacency from button to surface, sidestepping the double-adjacency trap. This is the pattern Chrome / Firefox use by default for `:focus-visible`.

### Option C: Single bright ring that clears 3:1 against both `#0066CC` and `#FFFFFF`

Mathematically requires a luminance L such that:
- (L + 0.05) / (0.1444 + 0.05) ≥ 3 → L ≥ 0.533
- (1.0000 + 0.05) / (L + 0.05) ≥ 3 → L ≤ 0.300

These two constraints are **mutually exclusive** -- no single color exists that clears 3:1 against both `#0066CC` and `#FFFFFF` simultaneously. Therefore Option C is **impossible without changing the button bg or surface**. This confirms that a single-tone ring cannot fix the current token set; Option A or B is required.

### Recommended token change

Adopt **Option A** as the canonical pattern across the design system, because it generalizes to dark surfaces and colored controls without per-component tuning:

```diff
- color.focus.ring: "#0099FF"
+ color.focus.ring.outer: "#003D7A"
+ color.focus.ring.inner: "#FFFFFF"
+ focus.ring.width.outer: 2px
+ focus.ring.width.inner: 2px
```

Document in the design-system focus-indicator guidance that any single-tone ring must be validated against both adjacent surfaces at design-review time, and that the default ring is the two-tone token pair above.
