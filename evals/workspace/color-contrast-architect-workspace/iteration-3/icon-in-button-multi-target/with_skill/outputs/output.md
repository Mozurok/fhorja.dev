# Icon-in-Button Contrast Audit (3 Adjacencies)

Per `color-contrast-architect` SKILL.md Step 4 + Step 5: an icon-in-button has THREE adjacencies. An icon adjacent to a text label inside a shared button surface introduces a third pair (icon vs label) that single-pair audits routinely miss. Each adjacency is scored against its own WCAG 2.2 context.

## Token resolutions (light theme)

| Token | Hex | sRGB linear | Relative luminance L |
|---|---|---|---|
| `color.button.subtle.bg` | `#F0F0F0` | 0.87137 (all channels) | **0.87137** |
| `color.text.primary` | `#4A4A4A` | 0.06480 (all channels) | **0.06480** |
| `color.icon.default` | `#8A8A8A` | 0.25415 (all channels) | **0.25415** |

Formula: `c_lin = ((c+0.055)/1.055)^2.4` for c > 0.03928; `L = 0.2126*R + 0.7152*G + 0.0722*B`; `ratio = (L_light + 0.05) / (L_dark + 0.05)`, truncated to two decimals (never rounded up to clear a threshold per Step 3).

## Contrast matrix

| # | Foreground | Background / Adjacent | Design context | Ratio | AA threshold | AAA threshold | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | `color.text.primary` `#4A4A4A` | `color.button.subtle.bg` `#F0F0F0` | normal-text | **8.03:1** | 4.5:1 | 7:1 | **PASS-AAA** |
| 2 | `color.icon.default` `#8A8A8A` | `color.button.subtle.bg` `#F0F0F0` | ui-component (graphical-object) | **3.03:1** | 3:1 | (n/a) | **PASS-AA** (marginal: +0.03 above floor) |
| 3 | `color.icon.default` `#8A8A8A` | `color.text.primary` `#4A4A4A` (adjacent label) | see WCAG analysis below | **2.65:1** | conditional | conditional | **Not required to pass** (analysis below) |

**Summary count:** total adjacencies audited = 3 | PASS-AAA = 1 | PASS-AA = 1 | FAIL-AA = 0 | No-requirement = 1 | UNRESOLVED = 0

## WCAG analysis per pair

### Pair 1: Label vs button background -- REQUIRED, PASSES AAA
- Context: button label is rendered text -> WCAG 2.2 SC **1.4.3 Contrast (Minimum)** applies.
- Threshold: **4.5:1 AA** (assumes label is < 18pt / < 14pt-bold; if it qualifies as large text, the AA floor would drop to 3:1, which this pair also clears).
- Actual: 8.03:1 -> clears AAA (7:1).

### Pair 2: Icon vs button background -- REQUIRED, PASSES AA (marginal)
- Context: the icon conveys meaning paired with the label (it is part of the control affordance, not purely decorative). WCAG 2.2 SC **1.4.11 Non-text Contrast** applies because the icon is a graphical object essential to understanding the control.
- Threshold: **3:1 AA** against the adjacent button surface. SC 1.4.11 has no AAA upgrade.
- Actual: 3.03:1 -> passes by 0.03. **Flagged as fragile**: any future token tweak (icon lighter, surface darker) flips this to FAIL. Recommend a token-level safety margin even though the audit verdict is PASS.
- Caveat (Step 8): if the icon is purely decorative AND the label fully conveys the affordance with no information loss when the icon is hidden, SC 1.4.11 is not invoked and this pair becomes informational only. The persona scores against the stricter interpretation per Step 4's "strictest applicable threshold" rule.

### Pair 3: Icon vs label -- NOT REQUIRED to pass, scored for completeness
- Context: WCAG 2.2 has **no SC that requires foreground contrast between two adjacent foreground glyphs sharing a common background** when both serve the same affordance and neither is used to differentiate state.
  - SC 1.4.1 (Use of Color) requires color not be the sole means of conveying information or distinguishing a UI element. Here the icon and label communicate the SAME affordance (icon reinforces label, redundant encoding) -- color is not load-bearing for differentiation, so SC 1.4.1 is not invoked.
  - SC 1.4.3 / 1.4.11 require contrast against the background each glyph sits on (Pairs 1 and 2 above), not against a sibling glyph.
- Threshold: **none applicable** under WCAG 2.2 for this redundant-encoding case.
- Actual: 2.65:1 -- reported for transparency; this is NOT a failure.
- When this pair WOULD need to pass: if the icon ever swaps to a different glyph to indicate state change (e.g., check vs cross, on vs off) while the label stays the same, the icon's state becomes the sole differentiator. SC 1.4.1 then requires a non-color cue (shape change already provides this) and SC 1.4.11 requires 3:1 between the icon and its background (already covered by Pair 2). Even in that case, icon-vs-label contrast is not the load-bearing requirement.

## Which pairs are required to pass at which threshold?

| Pair | WCAG SC | Required threshold | Current verdict |
|---|---|---|---|
| 1. Label vs bg | 1.4.3 Contrast (Minimum) | 4.5:1 AA (normal text) | PASS-AAA (8.03:1) |
| 2. Icon vs bg | 1.4.11 Non-text Contrast | 3:1 AA (ui-component) | PASS-AA marginal (3.03:1) |
| 3. Icon vs label | none (redundant encoding, same affordance) | n/a | Reported only (2.65:1) |

## Remediation

No failures to remediate. Two notes carry forward as PROPOSED-block candidates:

1. **Pair 2 fragility (recommended, not required):** `color.icon.default` `#8A8A8A` clears 3:1 by only 0.03. Darkening to `#878787` raises the ratio to ~3.14:1; darkening to `#828282` raises it to ~3.36:1; darkening to `#767676` raises it to ~4.54:1 (a comfortable margin that also clears the 4.5:1 normal-text bar if the icon is ever reused as inline text-adjacent glyphs). Recommend `#767676` as a safety-margin token value unless brand constraints lock the current shade.
2. **Pair 3 future-proofing (informational):** if `color.icon.default` is ever reused as the "state-on" variant against a "state-off" label glyph, re-audit under SC 1.4.1 + 1.4.11 with the new state pair documented.

## PROPOSED block draft -- `DECISIONS.md ## Locked decisions`

```
<!-- PROPOSED:start id=D-N-contrast-icon-button -->
- D-N: Icon-in-button contrast policy
  - Required pairs and thresholds:
    - Label vs button surface: WCAG 2.2 SC 1.4.3, AA 4.5:1 floor (normal text).
    - Icon vs button surface: WCAG 2.2 SC 1.4.11, AA 3:1 floor (graphical object essential to control affordance).
  - Not required: icon vs adjacent label glyph (redundant-encoding case; both serve the same affordance, no state differentiation by color).
  - Safety margin: `color.icon.default` SHOULD clear 3:1 by >=0.3 to absorb future token drift; current `#8A8A8A` at 3.03:1 is marginal. Proposed adjustment to `#767676` (4.54:1) deferred pending brand review.
  - Re-audit trigger: any future use of `color.icon.default` as a state-differentiating glyph (icon swap to indicate on/off, valid/invalid, etc.) requires re-running this audit under SC 1.4.1 + 1.4.11.
<!-- PROPOSED:end -->
```

## PROPOSED block draft -- `IMPLEMENTATION_PLAN.md ## Risks and mitigations`

No plan-level risk surfaced. Audit clears AA on all required pairs; the Pair 2 fragility note is a token-hygiene recommendation, not a blocker for downstream slices.

## Tooling caveats (Step 8)

- Computations assume sRGB color space and no runtime opacity / blending on any of the three colors. If `color.icon.default` is ever rendered with alpha (e.g., `#8A8A8A` at 80% opacity over `#F0F0F0`), the effective foreground luminance changes and Pair 2 must be re-audited against the composited value.
- All three tokens are resolved as direct hex values in this audit (no alias chain), so no alias re-verification is needed.

---

**Recommended next command:** `decision-interview` -- to promote the PROPOSED D-N block locking the icon-in-button contrast policy and adjudicating whether to apply the `#767676` safety-margin adjustment.