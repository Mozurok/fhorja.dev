# CONTRAST_AUDIT -- link-in-body-text triad

Scope: one theme (light), one surface (page background `#FFFFFF`), one inline link rendered within body text. Three pairs audited end-to-end per WCAG 2.2.

## 1. Pairwise contrast matrix

Computed via WCAG 2.2 relative-luminance formula (sRGB linearization, `L = 0.2126·R + 0.7152·G + 0.0722·B`, ratio `(L_light + 0.05) / (L_dark + 0.05)`, rounded to two decimal places, never rounded up to clear a threshold).

| # | theme | foreground_token | background_token | fg hex | bg hex | design_context | ratio | AA threshold | AAA threshold | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | light | `color.text.primary` | `color.surface.background` | `#222222` | `#FFFFFF` | normal-text | **15.38:1** | 4.5:1 | 7:1 | **PASS-AAA** |
| 2 | light | `color.link.default` | `color.surface.background` | `#0033AA` | `#FFFFFF` | normal-text | **10.22:1** | 4.5:1 | 7:1 | **PASS-AAA** |
| 3 | light | `color.link.default` | `color.text.primary` (link vs body, SC 1.4.1 adjacency) | `#0033AA` | `#222222` | graphical-object / non-text differentiation per SC 1.4.1 | **1.50:1** | 3:1 | n/a | **FAIL-AA** |

Summary count: 3 pairs audited -- PASS-AAA: 2 -- PASS-AA: 0 -- FAIL-AA: 1 -- UNRESOLVED: 0.

Note on row 3's context label: row 3 is NOT a traditional foreground/background pair (the link sits ON the page background, not on the body text). It is scored under WCAG 2.2 SC 1.4.1 "Use of Color", which requires that when color is the only visual means of distinguishing an inline link from surrounding text, the contrast between the link color and the surrounding body text color MUST be at least 3:1 (per WCAG Technique G183 and the SC 1.4.1 understanding doc). The 3:1 threshold here is the SC 1.4.1 adjacency threshold, not a fg/bg text-contrast threshold.

## 2. WCAG SC 1.4.1 (Use of Color) analysis

SC 1.4.1 -- Use of Color (Level A) -- requires that color is NOT used as the only visual means of conveying information, indicating an action, prompting a response, or distinguishing a visual element. For inline links inside a body-text block, WCAG's Understanding document and Technique G183 give two ways to comply:

- **Path A -- additional non-color differentiator.** The link is distinguishable from surrounding text by something OTHER than color: underline, bold weight, italic, different font, an adjacent icon, or any other non-color visual cue. When any such cue is present, SC 1.4.1 is satisfied regardless of the link-vs-text contrast ratio.
- **Path B -- color-only with sufficient differentiation contrast.** The link color has a contrast ratio of at least 3:1 against the surrounding body text color, AND an additional non-color visual cue is provided on focus and on hover (so keyboard and pointer users get a non-color cue at the moment of interaction).

The documented design uses neither weight, underline, nor any other non-color cue. The only differentiator between `color.link.default` and `color.text.primary` is hue. SC 1.4.1 Path A is therefore not satisfied; Path B is the only remaining route.

Path B evaluation:

- Required: link-vs-body contrast ≥ 3:1 → measured **1.50:1** → **FAILS the 3:1 floor by a factor of 2**.
- Required: additional non-color cue on hover and focus → not documented; "color only, no underline" is asserted for the default state and no hover/focus cue is specified.

Both Path A and Path B fail. SC 1.4.1 is NOT satisfied.

## 3. Verdict -- does "color only, no underline" meet WCAG 2.2 AA?

**No.** The triad fails WCAG 2.2 AA on SC 1.4.1.

- Pair 1 (body/background) passes AAA. Not the blocker.
- Pair 2 (link/background) passes AAA for text contrast (10.22:1, well above the 4.5:1 AA floor for normal text). Reading the link against the page is not the problem.
- Pair 3 (link/body adjacency for SC 1.4.1) measures 1.50:1, well below the 3:1 floor that SC 1.4.1 requires when color is the sole differentiator. There is no underline, no weight change, no icon, no other non-color cue. The link is therefore distinguishable from body text by COLOR ALONE, and the color contrast between them is insufficient.

The team's reasoning ("the color is enough") is the exact failure mode SC 1.4.1 was written to prevent: users with color-vision deficiencies (deuteranopia, protanopia, tritanopia, monochromacy) and users in low-saturation viewing conditions (sunlight glare, low-contrast displays, e-ink) cannot reliably tell `#0033AA` from `#222222` at body-text size. A 1.50:1 luminance ratio means the two colors are nearly identical in perceived lightness -- the distinction collapses entirely under a red-green or blue-yellow CVD filter.

## 4. Remediation options

Four options, in order of preference (cheapest token-level fix first, most invasive last). Each option lists the WCAG path it satisfies and the concrete token delta.

### Option A (recommended) -- Restore the underline on inline links

Re-introduce `text-decoration: underline` on `color.link.default` in body-text contexts. Optionally use `text-decoration-thickness` and `text-underline-offset` tokens to tune the visual noise the team is reacting to -- a 1px underline with 2–3px offset reads as a clean link affordance, not as visual noise.

- Satisfies SC 1.4.1 Path A -- non-color cue present in default state.
- Token change: no color change required. Add `typography.link.text-decoration: underline` (or per-component `text-decoration` rule on link atoms).
- Pair 3 ratio is irrelevant once Path A is satisfied; pairs 1 and 2 remain PASS-AAA.
- Addresses the team's "visual noise" concern by tuning thickness/offset rather than removing the cue entirely.

### Option B -- Keep no underline in default, add weight differentiation

Make inline links semibold (e.g. `font-weight: 600`) while body text stays at the default weight (e.g. 400). Weight is a non-color visual cue and satisfies SC 1.4.1 Path A.

- Satisfies SC 1.4.1 Path A -- non-color cue (weight) present in default state.
- Token change: add `typography.link.font-weight: 600` (or equivalent semantic token). No color change.
- Caveat: weight-only differentiation is weaker than underline for users with low-resolution displays or small body-text sizes; underline (Option A) is the more robust choice. Combine with a slightly heavier weight if the team wants both.

### Option C -- Darken the link color AND add a hover/focus non-color cue (Path B route)

If the team insists on "no underline, no weight change" in the default state, SC 1.4.1 Path B requires both (i) link-vs-body contrast ≥ 3:1 and (ii) a non-color cue on hover and focus. To reach 3:1 against `#222222`, the link must be substantially LIGHTER than the body text (since the body is already very dark). A darker blue cannot satisfy this -- the link must move toward white, e.g. a saturated mid-blue.

- Target: link-vs-body ratio ≥ 3:1.
- Candidate token delta: change `color.link.default` from `#0033AA` (L ≈ 0.0527) to a lighter blue such as `#4D7FFF` (L ≈ 0.245) → link-vs-body ratio ≈ (0.245 + 0.05) / (0.01831 + 0.05) = 4.32:1 → PASSES the 3:1 SC 1.4.1 floor.
- Verify pair 2 (link/background) still passes AA for normal text: `#4D7FFF` vs `#FFFFFF` → (1.05) / (0.245 + 0.05) = 3.56:1 → **PASSES AA for large text (≥3:1) but FAILS AA for normal text (<4.5:1)**. This option therefore TRADES one failure for another and is NOT viable for inline body-text links without further tuning.
- A lighter blue that satisfies both constraints simultaneously (≥3:1 vs `#222222` AND ≥4.5:1 vs `#FFFFFF`) is mathematically tight on a white surface; any color light enough to give 3:1 against near-black body text is approaching the point where it loses 4.5:1 against white. This is why the WCAG community generally recommends Path A (underline) for inline links on light surfaces rather than chasing Path B color tuning.
- Additional requirement under Path B: add a non-color cue on hover and focus (underline-on-hover, focus ring, etc.). Without this, Path B is incomplete even if the 3:1 contrast is met.

### Option D -- Darken the body text reference or lighten the surface (reframe the adjacency)

Not recommended. Moving `color.text.primary` lighter to widen the link-vs-body gap would degrade pair 1 (currently PASS-AAA at 15.38:1) and harm long-form readability. Moving the surface is even more invasive. Listed only for completeness; reject in favor of Options A or B.

### Token-delta recommendation summary

| option | satisfies SC 1.4.1 via | token change | downstream impact |
|---|---|---|---|
| A (recommended) | Path A (underline) | add `typography.link.text-decoration: underline` (tune thickness/offset) | none on color tokens; pair 1 and 2 unchanged PASS-AAA |
| B | Path A (weight) | add `typography.link.font-weight: 600` | none on color tokens; weaker cue than A |
| C | Path B (3:1 + hover/focus cue) | change `color.link.default` to a lighter blue AND add hover/focus cue | trades failures -- light-enough blue loses normal-text AA against `#FFFFFF`; not viable on white surface without further work |
| D | n/a | reject | degrades pair 1 |

## 5. Failing-pair list with remediation

- **Pair 3 -- link/body adjacency, FAIL-AA (1.50:1 vs 3:1 floor under SC 1.4.1).** Remediation: adopt Option A -- add `typography.link.text-decoration: underline` to the link atom token; no color-token change required; satisfies SC 1.4.1 Path A and leaves pairs 1 and 2 untouched at PASS-AAA. Acceptable fallback: Option B (weight 600). Reject Option C on a white surface unless the team accepts a normal-text AA failure on pair 2.

## 6. PROPOSED block -- DECISIONS.md ## Locked decisions

```
### D-N (PROPOSED) -- Inline link differentiation policy (WCAG 2.2 SC 1.4.1)
Status: PROPOSED -- awaiting decision-interview promotion
Context: link/body pair measured 1.50:1, well below the SC 1.4.1 3:1 floor required when color is the sole differentiator. Color-only inline links on `color.surface.background` fail WCAG 2.2 AA.
Decision: inline links inside body-text contexts MUST carry a non-color visual cue in the default state (Path A). Default policy: `typography.link.text-decoration: underline` on `color.link.default` body-text usages. Underline thickness and offset are tunable to manage visual density; removing the cue entirely is not.
Hover and focus states MUST additionally include a non-color cue (focus ring per SC 2.4.7; hover state underline thickness change or background fill) to remain robust for keyboard and pointer interaction signaling.
Out of scope: display-link styling inside hero blocks where a button-like affordance already provides a non-color cue -- those follow the button atom's policy, not this rule.
Rationale: SC 1.4.1 Path A (non-color cue) is the only route that does not require either degrading body-text contrast or sacrificing the link's normal-text AA against the page background on a white surface.
```

## 7. PROPOSED block -- IMPLEMENTATION_PLAN.md ## Risks and mitigations

```
### Risk (PROPOSED) -- Inline link SC 1.4.1 regression risk during link-token refactor
Status: PROPOSED -- awaiting implementation-plan promotion
Context: any future slice that removes the link underline, removes link weight differentiation, or changes `color.link.default` without re-running the link/body adjacency audit risks reintroducing the SC 1.4.1 failure documented in CONTRAST_AUDIT.md row 3.
Mitigation: link atom component spec MUST include an SC 1.4.1 conformance line ("non-color cue present in default state"). atom-audit should flag any link atom missing this line. Any color-token slice touching `color.link.*` must re-run color-contrast-architect on the link/body pair before merge.
Severity: medium -- failure mode is silent (visual cue removal looks like a styling improvement) and only surfaces in a late accessibility review.
```

## Command transcript

- Step 1: enumerated three explicit input pairs (body/bg, link/bg, link/body); no mining of screen-spec needed since pairs were given.
- Step 2: resolved tokens to concrete sRGB hex values per the documented design; no alias chains involved.
- Step 3–4: computed luminances and ratios per WCAG 2.2; classified each row per design context, with link/body scored under SC 1.4.1's 3:1 adjacency floor.
- Step 5–6: built matrix, flagged pair 3 as FAIL-AA, proposed four remediation options with Option A (restore underline) as the recommended path.

## Handoff

Run now: `decision-interview` -- to lock the inline-link differentiation policy (Option A: underline as default non-color cue) and promote the PROPOSED D-N block.

Then: `component-spec` on the link atom -- to capture the underline rule (thickness, offset, hover/focus behavior) and the SC 1.4.1 conformance line so downstream slices and atom-audit can enforce it.

If the team rejects underline and wants to explore Option B (weight) or Option C (color shift): re-run `color-contrast-architect` on the proposed token deltas before locking, because Option C in particular trades one WCAG failure for another on a white surface.