# Audit: `color.text.muted` (`#888888`) on `color.surface.background` (`#FFFFFF`)

Computed contrast ratio: **3.54:1**

## 1. Per-context thresholds

The token is documented for three usage contexts. WCAG 2.x defines a distinct minimum contrast threshold per context:

| # | Usage context | WCAG SC | Required ratio (AA) | Required ratio (AAA) |
|---|---|---|---|---|
| 1 | 14px body text (normal text, < 18pt / < 14pt bold) | 1.4.3 Contrast (Minimum) | **4.5:1** | 7:1 |
| 2 | Form-input border (UI component / graphical object boundary) | 1.4.11 Non-text Contrast | **3:1** | (no AAA equivalent) |
| 3 | Focus-ring tertiary state (focus indicator) | 1.4.11 Non-text Contrast | **3:1** | (no AAA equivalent) |

Evaluating the measured 3.54:1 against each:

- Context 1 (14px body text, 4.5:1): **FAIL** -- 3.54 < 4.5
- Context 2 (form-input border, 3:1): **PASS** -- 3.54 >= 3.0
- Context 3 (focus-ring tertiary, 3:1): **PASS** -- 3.54 >= 3.0

## 2. Strictest applicable threshold

Because the same token is documented for all three contexts, the token must satisfy every context simultaneously. The strictest threshold dominates.

**Strictest applicable threshold: 4.5:1 (WCAG 2.1 SC 1.4.3 Contrast (Minimum) -- normal text, AA), driven by the 14px body-text context.**

The two 3:1 UI-component contexts are non-binding here; they would only become the governing threshold if the text context were removed from this token's documented usage.

## 3. Verdict (canonical enum)

Scored against the strictest applicable threshold (4.5:1):

**Verdict: `FAIL-AA`**

Rationale: 3.54:1 clears the 3:1 non-text bar but falls short of the 4.5:1 normal-text bar by ~0.96. Because the token is shared across all three contexts, a pass in two contexts does not rescue the failure in the third -- the token as documented cannot ship.

## 4. Remediation (concrete token hex)

Two viable remediation paths. Either resolves the `FAIL-AA` for the documented multi-context usage.

### Option A (recommended) -- Darken `color.text.muted` to meet 4.5:1 on `#FFFFFF`

Pick the lightest grey on `#FFFFFF` that still clears 4.5:1 so the visual "muted" intent is preserved:

- `color.text.muted = #767676` -- ratio **4.54:1** vs `#FFFFFF` -- PASS-AA (smallest visual change, common a11y-safe muted grey, also used by GOV.UK / GitHub Primer for the same reason)
- `color.text.muted = #757575` -- ratio **4.60:1** vs `#FFFFFF` -- PASS-AA (slightly safer margin)
- `color.text.muted = #6B6B6B` -- ratio **5.36:1** vs `#FFFFFF` -- PASS-AA with comfort margin against subpixel/antialiasing loss

All three also continue to satisfy the 3:1 non-text thresholds for the form-input border and focus-ring tertiary contexts, so a single token still serves all three documented uses.

### Option B -- Split the token by context

If the design intent specifically requires `#888888`'s lightness in the UI-component contexts, stop reusing one token across text + non-text. Introduce:

- `color.text.muted = #767676` -- used only for 14px body text (PASS-AA at 4.54:1)
- `color.border.muted = #888888` -- used for form-input border (PASS at 3.54:1 vs 3:1)
- `color.focus.tertiary = #888888` -- used for focus-ring tertiary state (PASS at 3.54:1 vs 3:1)

This preserves the original `#888888` exactly where its non-text contexts allow it and removes it from the text context where it cannot pass.

### Not recommended

- Leaving `#888888` for text and annotating "small text only at 14px+" -- 14px is already below the 18pt / 14pt-bold large-text exemption in SC 1.4.3, so the 4.5:1 bar applies; this would remain `FAIL-AA`.
- Relying on bolding 14px text to qualify as "large text" -- SC 1.4.3 large-text bold threshold is 14pt bold (~18.66px), not 14px bold; still `FAIL-AA`.

## Summary line for the token registry

`color.text.muted` `#888888` on `#FFFFFF` = 3.54:1 -- strictest applicable threshold 4.5:1 (14px body text, SC 1.4.3) -- **FAIL-AA** -- remediate to `#767676` (4.54:1, PASS-AA) or split the token per Option B.