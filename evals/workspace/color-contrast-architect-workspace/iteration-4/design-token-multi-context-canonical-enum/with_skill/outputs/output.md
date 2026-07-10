# CONTRAST_AUDIT -- `color.text.muted` over `color.surface.background`

## Inputs

- **Foreground token:** `color.text.muted` = `#888888`
- **Background token:** `color.surface.background` = `#FFFFFF`
- **Theme:** `light` (only theme provided)
- **WCAG target:** AA (per `wos/design-system-conventions.md ## Accessibility floor`)
- **Computed ratio (WCAG 2.2):** **3.54:1** (relative luminance, two-decimal, never rounded up)

This is ONE token pair documented across THREE design contexts. Per Step 4 of the persona protocol, multi-context pairs are scored against the STRICTEST applicable threshold and noted as multi-context.

## Per-context threshold analysis

| # | Design context | Concrete usage | AA threshold | AAA threshold | Ratio | Verdict at context |
|---|---|---|---|---|---|---|
| 1 | `normal-text` | 14px body text (under 18pt / under 14pt-bold) | **>=4.5:1** | >=7:1 | 3.54:1 | FAIL-AA |
| 2 | `ui-component` | Form-input border (state-conveying boundary) | >=3:1 | n/a (AAA does not extend to UI components in WCAG 2.2) | 3.54:1 | PASS-AA |
| 3 | `focus-indicator` | Focus ring tertiary state, against adjacent surface `#FFFFFF` AND focused element interior | >=3:1 (against EACH adjacent color) | n/a | 3.54:1 vs `#FFFFFF` adjacent surface | PASS-AA (against the documented `#FFFFFF` adjacent; interior side requires separate verification -- flagged in caveats) |

## Strictest applicable threshold

Of the three contexts, **`normal-text` (>=4.5:1 AA)** is the strictest applicable threshold. The pair must clear 4.5:1 to be approvable for the union of its documented uses.

- 14px body text governs because the same `color.text.muted` token is documented as a foreground for it; you cannot ship a token whose strictest documented use fails its own context.

## Contrast matrix (canonical enum)

| theme | foreground_token | background_token | design_context | ratio | AA_threshold | AAA_threshold | verdict |
|---|---|---|---|---|---|---|---|
| light | `color.text.muted` (`#888888`) | `color.surface.background` (`#FFFFFF`) | normal-text + ui-component + focus-indicator (multi-context; scored at strictest) | 3.54:1 | 4.5:1 | 7:1 | **FAIL-AA** |

Summary count: total pairs audited = 1 (multi-context). PASS-AAA = 0. PASS-AA = 0. **FAIL-AA = 1.** UNRESOLVED = 0.

The verdict `FAIL-AA` is canonical per the persona's enum (`PASS-AAA | PASS-AA | FAIL-AA | UNRESOLVED`). Even though the pair would PASS-AA in isolation against the ui-component and focus-indicator contexts, the single token is documented as serving normal-text -- so the strictest applicable threshold rules and the token-level verdict is FAIL-AA.

## Remediation (concrete token-hex deltas)

Two paths. Pick one; do not ship both.

### Option R1 -- Darken `color.text.muted` to clear normal-text AA (recommended)

Lower the L\* of the muted gray until the pair clears 4.5:1 against `#FFFFFF`. Concrete candidates (all computed against `#FFFFFF`):

- `#767676` → ratio **4.54:1** -- minimum that clears AA for normal-text. Tight; any future background shift breaks it.
- `#717171` → ratio **4.83:1** -- comfortable AA headroom; recommended default.
- `#595959` → ratio **7.00:1** -- clears AAA for normal-text; future-proofs against AAA escalation.

Recommended single edit: **`color.text.muted` = `#717171`** (PASS-AA across all three documented contexts; preserves muted character vs jumping to AAA-dark).

### Option R2 -- Split the token by context

If the visual design needs `#888888` to stay muted in the UI-component / focus-indicator contexts (where it already PASS-AAs at 3.54:1 >= 3:1), split:

- `color.text.muted` (normal-text use only) → **`#717171`** (PASS-AA at 4.83:1)
- `color.border.muted` (form-input border, ui-component context) → keep **`#888888`** (PASS-AA at 3.54:1 >= 3:1)
- `color.focus.tertiary` (focus-indicator) → keep **`#888888`** against the documented `#FFFFFF` adjacent (PASS-AA at 3.54:1 >= 3:1); re-verify against the focused element's INTERIOR color separately per WCAG 2.4.11 / 2.4.13.

R2 is the token-system-correct fix when the muted gray carries semantic weight in non-text contexts. R1 is the smaller blast-radius fix when no consumer depends on the muted gray staying visually muted at `#888888` for borders.

## Tooling caveats (Step 8)

- The focus-indicator threshold is scored against the documented adjacent surface `#FFFFFF` only. WCAG 2.2 requires >=3:1 against **each** adjacent color -- the focused element's interior fill must be re-verified separately. If the focused element's interior is anything other than `#FFFFFF` or near-white, this audit does not cover that side and a follow-up pair is required.
- AAA does not extend to UI components or focus indicators in WCAG 2.2; the `AAA_threshold` column is left as n/a for those contexts and is not a gap in the audit.
- Ratio computed via standard sRGB linearization + `(L_light + 0.05) / (L_dark + 0.05)`, two-decimal truncation (never rounded up to clear a threshold).

## Verdict

**FAIL-AA** (canonical enum). Strictest applicable threshold = normal-text 4.5:1; computed 3.54:1 misses by 0.96. Recommended remediation: **`color.text.muted` = `#717171`** (single-edit path; ratio 4.83:1 against `#FFFFFF`).
