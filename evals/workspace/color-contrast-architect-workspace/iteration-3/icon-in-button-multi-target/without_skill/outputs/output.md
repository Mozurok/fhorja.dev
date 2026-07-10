# Icon-in-Button Multi-Target Contrast Audit

## 1. Computed Contrast Ratios

All ratios computed with the WCAG 2.x relative-luminance formula (sRGB, `(L1 + 0.05) / (L2 + 0.05)`).

| # | Pair | Foreground | Background / Adjacent | Ratio |
|---|------|------------|-----------------------|-------|
| 1 | Label vs button bg | `#4A4A4A` | `#F0F0F0` | **7.78 : 1** |
| 2 | Icon vs button bg  | `#8A8A8A` | `#F0F0F0` | **3.03 : 1** |
| 3 | Icon vs label (adjacent) | `#8A8A8A` | `#4A4A4A` | **2.57 : 1** |

## 2. Per-Pair Verdict

### Pair 1 -- Label vs button background (`#4A4A4A` on `#F0F0F0`)
- **Ratio: 7.78 : 1**
- Context: body/label text inside a button -- normal-size text.
- WCAG 2.2 **SC 1.4.3 Contrast (Minimum)** AA threshold for normal text = **4.5 : 1**.
- AAA threshold (SC 1.4.6) for normal text = **7.0 : 1**.
- **Verdict: PASS AA and PASS AAA.** No action needed.

### Pair 2 -- Icon vs button background (`#8A8A8A` on `#F0F0F0`)
- **Ratio: 3.03 : 1**
- Context: the icon is a graphical part of a user-interface component (an actionable button affordance).
- WCAG 2.2 **SC 1.4.11 Non-text Contrast** AA threshold for UI components and meaningful graphical objects = **3.0 : 1**.
- **Verdict: PASS AA, but only by 0.03.** This is a knife-edge pass -- any token drift (e.g. bg lightening, icon lightening, anti-aliased rendering, or a hover/disabled state that shifts either token) will tip it under 3.0 : 1. Treat as a token-stability risk even though it technically conforms today.
- Note: WCAG has no AAA equivalent for non-text contrast, so 3.0 : 1 is the ceiling requirement.

### Pair 3 -- Icon vs label (`#8A8A8A` adjacent to `#4A4A4A`)
- **Ratio: 2.57 : 1**
- Context: two foreground elements sitting side-by-side inside the same button, both contributing to the same single affordance ("[icon] Action label"). The icon is decorative-redundant relative to the label -- it does not communicate a different state, a different control, or a different meaning.
- **WCAG analysis:** there is **no SC 1.4.3 or SC 1.4.11 contrast requirement between two adjacent foregrounds that serve the same affordance.** Both 1.4.3 and 1.4.11 are defined against the *background*, not against each other. The candidate SC that *could* apply is **SC 1.4.1 Use of Color**: it would only bite if the icon-vs-label color difference were the *sole* means of conveying information, state, or distinguishing one control from another. Here it is not -- the label text itself carries the meaning, and the icon is supportive.
- **Verdict: NO WCAG VIOLATION** for this pair as designed. The 2.57 : 1 ratio is informational only.
- Caveat: if a future variant uses the same icon+label pattern to encode a *differentiable state* (e.g. icon color is the only signal that the button is "active" vs "inactive", or icon color distinguishes "save" from "delete"), then SC 1.4.1 and arguably SC 1.4.11 (as a "meaningful graphical object" conveying state) would kick in and 3.0 : 1 between the differentiating elements would become required.

## 3. WCAG Requirements Summary

| Pair | WCAG SC | Required Threshold | Measured | Status |
|------|---------|-------------------|----------|--------|
| Label vs bg | 1.4.3 (AA) / 1.4.6 (AAA) | 4.5 : 1 / 7.0 : 1 | 7.78 : 1 | PASS AA + AAA |
| Icon vs bg  | 1.4.11 (AA) | 3.0 : 1 | 3.03 : 1 | PASS AA (marginal) |
| Icon vs label | 1.4.1 (conditional) | n/a unless icon is sole state signal | 2.57 : 1 | Not required to pass |

**Required to pass:** Pairs 1 and 2.
**Not required to pass (as designed):** Pair 3.

## 4. Remediation

No hard WCAG failure exists today, but two issues warrant action.

### Required-fix candidate: Pair 2 token stability
The 3.03 : 1 icon-vs-bg ratio passes by a margin of 0.03, which is below the precision of typical color-token review. Recommended adjustments (pick one):

- **Darken the icon token** `color.icon.default` from `#8A8A8A` toward roughly `#767676` (≈ 4.5 : 1 on `#F0F0F0`), giving a one-step buffer against future bg lightening and matching the common "icon = text-secondary" pairing.
- **Darken the bg token** `color.button.subtle.bg` from `#F0F0F0` toward `#E8E8E8` or `#E5E5E5` -- preserves the icon color but is usually undesirable because subtle-bg is a global token used elsewhere.
- Preferred: change the icon token, not the bg token (smaller blast radius).

### Optional-fix: Pair 3 perceptual hierarchy
Even without a WCAG requirement, the 2.57 : 1 icon-vs-label ratio means the icon reads as *lower visual weight* than the label -- which is usually the intended design (label-led button, icon supporting). No remediation needed unless the design intent is "icon and label are co-equal" or "icon is primary affordance signal," in which case the icon must be darkened to at least match label luminance.

### Future-state guardrail
If this icon-in-button pattern is ever extended so the icon color encodes a *state* (active/inactive, on/off, success/error) independent of the label, re-audit Pair 3 against SC 1.4.1 and SC 1.4.11 -- the bar becomes 3.0 : 1 between the two state colors, and the current `#8A8A8A` icon would fail against most plausible state pairings.

### Recommended single change
Update `color.icon.default` from `#8A8A8A` to approximately `#767676`. This:
- Lifts Pair 2 from a marginal 3.03 : 1 to roughly 4.5 : 1 (comfortable AA + future-proof).
- Lifts Pair 3 from 2.57 : 1 to roughly 1.7 : 1 -- still no requirement, and arguably *worse* for icon/label differentiation, which is fine because they share an affordance.
- Touches a single token, not the subtle-bg surface.
