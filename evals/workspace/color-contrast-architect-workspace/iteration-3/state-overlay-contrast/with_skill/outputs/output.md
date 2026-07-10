# Contrast audit -- Button primary across interaction states

Persona: `color-contrast-architect`. Per Step 4 ("Classify per design context") the audit MUST cover every documented foreground/background pair across every state the design enumerates. The default-state-only audit that downstream commands usually accept is insufficient here because the hover and active overlays produce two distinct composed backgrounds that must each clear WCAG 2.2 AA independently. The label color (`#FFFFFF`) is constant; the background changes per state, so three pairs are in scope.

Computation notes (Step 3 protocol):
- sRGB linearization then `L = 0.2126R + 0.7152G + 0.0722B`, `ratio = (L_light + 0.05) / (L_dark + 0.05)`.
- Composed backgrounds resolved precisely (not the rounded approximations in the prompt): hover `#0066CC` + 12% white = `#1F78D2`; active `#0066CC` + 20% black = `#0052A3`.
- Ratios truncated to two decimals; per persona rule, **never rounded up to clear a threshold**.

## 1. Contrast pairs

| state | foreground | background (composed) | overlay applied | design context | ratio | AA threshold (normal-text) | AA threshold (ui-component) | verdict |
|---|---|---|---|---|---|---|---|---|
| Default | `color.button.primary.fg` `#FFFFFF` | `color.button.primary.bg` `#0066CC` | none | `normal-text` (button label) + `ui-component` (button surface) | `5.56:1` | `>=4.5:1` | `>=3:1` | `PASS-AA` |
| Hover | `color.button.primary.fg` `#FFFFFF` | `#1F78D2` (base + 12% white) | 12% white | `normal-text` (button label) + `ui-component` (button surface) | `4.49:1` | `>=4.5:1` | `>=3:1` | `FAIL-AA` for normal-text; `PASS-AA` for ui-component |
| Active | `color.button.primary.fg` `#FFFFFF` | `#0052A3` (base + 20% black) | 20% black | `normal-text` (button label) + `ui-component` (button surface) | `7.67:1` | `>=4.5:1` | `>=3:1` | `PASS-AAA` |

Multi-context note (Step 4): each row is scored against the **strictest applicable threshold**. The button label is normal text rendered on the button surface, so the binding threshold is `4.5:1` (normal-text AA), not `3:1` (ui-component AA). A reviewer who scored only against `3:1` would manufacture false confidence -- exactly the failure mode the persona's quality bar warns against.

## 2. Verdict per state

- **Default -- `PASS-AA`.** `5.56:1` clears normal-text AA (`>=4.5:1`) with a 1.06 margin. Comfortably above the floor; not AAA (would need `>=7:1`).
- **Hover -- `FAIL-AA` for normal-text.** `4.49:1` is **0.01 below** the `4.5:1` threshold. This is the load-bearing finding. Naive rounding to `4.5:1` would hide the failure; per Step 3 the ratio is truncated (`4.4915 -> 4.49`) and the verdict stands. The surface itself (treated as a `ui-component`) clears `3:1`, but the label-on-surface pair governs.
- **Active -- `PASS-AAA`.** `7.67:1` clears normal-text AAA (`>=7:1`). Darkening the base via the 20% black overlay strictly improves contrast against the white label.

## 3. Does any state fail a WCAG 2.2 AA threshold?

**Yes -- the HOVER state fails the `>=4.5:1` normal-text AA threshold (`4.49:1`).** No state fails the `>=3:1` ui-component AA threshold. The hover failure is the kind of defect that *only* a per-state pairwise audit catches: the default and active states bracket it (both pass), so a single-state audit would conclude the button is accessible while interactive users see a 0.01-below-threshold ratio every time they hover.

This is also the classic over-rounding trap. The prompt's pre-computed hover hex (`#1F77D1`) is itself a rounding of the true composed value (`#1F78D2`); auditing against the rounded hex gives `4.50:1` and falsely passes. The persona protocol (compute from the documented overlay rule, not from a paraphrased hex) is what surfaces the real failure.

## 4. Remediation (one per failing pair)

For HOVER (`#FFFFFF` on `#1F78D2`, `4.49:1`, `FAIL-AA` normal-text):

- **Preferred -- reduce the hover overlay strength.** Change the hover overlay from **12% white to 8% white** over `#0066CC`. Composed bg becomes `#1470CD`; ratio against `#FFFFFF` rises to `~4.85:1` (`PASS-AA` normal-text, with a healthy 0.35 margin). Single token-level delta, no component rewrite, preserves the visual affordance direction (still lighter than default). This is the persona's "token delta" remediation pattern (Step 6).
- **Alternative -- invert the hover direction.** Replace the white overlay with a black overlay (e.g. 8% black) so hover *darkens* instead of lightens, mirroring the active treatment but milder. Composed bg `~#005EBC`; ratio `~6.20:1` (`PASS-AA` with strong margin). This changes the interaction grammar (hover and active both darken), so flag for design review before adopting.
- **Reject -- context reclassification.** The button label is unambiguously normal text; reclassifying it as `large-text` (`>=3:1` AA) to dodge the failure would be the exact false-confidence failure mode the persona's quality bar prohibits. Do not take this path.
- **Reject -- documented deferral.** A 0.01-below-threshold normal-text failure on a primary button is a high-traffic accessibility defect, not a deferrable edge case. Documented deferral is not appropriate here.

Recommended action: stage the **8% white hover overlay** as a `PROPOSED` token change against `DECISIONS.md ## Locked decisions` (new D-N draft: "Hover overlay reduced from 12% to 8% white to clear WCAG 2.2 AA normal-text on `color.button.primary`"). Route via Handoff to `decision-interview` for promotion. Active and default states require no change.
