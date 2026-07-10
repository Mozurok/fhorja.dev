# Color Contrast Audit -- WCAG 2.2 AA

Scope: Light theme only. Two documented foreground/background pairs. One token (`color.text.muted`) plays a dual role and must be evaluated under the **strictest applicable threshold** rule.

## 1. Pairwise Contrast Matrix

| # | Foreground token | FG hex | Background token | BG hex | Measured ratio | Design context(s) | AA threshold applied | Multi-context? | Result |
|---|---|---|---|---|---|---|---|---|---|
| 1a | `color.text.muted` | #888888 | `color.surface.background` | #FFFFFF | 3.54:1 | Normal text (14px form-helper body text -- under 18pt/14pt-bold large-text threshold) | **4.5:1** (normal text) | Yes (also used as UI component -- see 1b) | **FAIL** |
| 1b | `color.text.muted` | #888888 | `color.surface.background` | #FFFFFF | 3.54:1 | UI component (form-input border -- non-text graphical/UI boundary) | 3:1 (UI component, SC 1.4.11) | Yes (also used as normal text -- see 1a) | PASS in isolation, but see multi-context rule below |
| 1-effective | `color.text.muted` | #888888 | `color.surface.background` | #FFFFFF | 3.54:1 | **Multi-context (normal text + UI component)** | **Strictest = 4.5:1** | **YES** | **FAIL** |
| 2 | `color.text.primary` | #222222 | `color.surface.background` | #FFFFFF | 15.9:1 | Normal text | 4.5:1 (normal text) | No | PASS |

### Multi-context scoring rule applied

`color.text.muted` is documented for two distinct WCAG contexts that carry different AA thresholds:

- Normal text (SC 1.4.3) → 4.5:1
- UI component / non-text contrast (SC 1.4.11) → 3:1

Per the strictest-applicable-threshold rule, the token must be evaluated against **4.5:1** (the stricter of the two). At 3.54:1, the token fails that combined requirement. It cannot be considered "AA-compliant for borders only" while still being shipped as body-text color -- a single token cannot satisfy one context and silently fail the other without producing accessibility debt.

## 2. Failing Pair List with Remediation

### Failure 1 -- `color.text.muted` (#888888) on `color.surface.background` (#FFFFFF)

- **Measured:** 3.54:1
- **Required (strictest applicable):** 4.5:1 (normal text, SC 1.4.3)
- **Gap:** ~0.96 ratio points short for body text. (Passes the 3:1 UI-component threshold for the border usage in isolation, but the token's dual role forces the stricter threshold.)
- **Affected usages:**
  - (a) 14px form-helper body text under input fields
  - (b) Form-input border
- **Remediation options (in order of preference):**
  1. **Split the token (recommended).** Introduce two purpose-specific tokens so each can be tuned to its own context:
     - `color.text.muted` → darken to satisfy 4.5:1 on #FFFFFF. Candidate values: **#767676** (~4.54:1, minimal change) or **#717171** (~4.83:1, small safety margin). Use for the 14px form-helper text.
     - `color.border.input` → keep around #888888 (3.54:1) or normalize to a dedicated border token; it already satisfies the 3:1 UI-component threshold. This preserves visual hierarchy between text and chrome.
  2. **Single-token darken.** If splitting is not desired, darken `color.text.muted` to ~#767676 or darker so it passes 4.5:1. Both text and border will become slightly darker, but both contexts remain compliant.
  3. **Do not** keep #888888 as body text and rely on the border-only threshold -- that violates the strictest-applicable rule and leaves SC 1.4.3 failing for form-helper text.
- **Verification after change:** re-measure the new foreground vs #FFFFFF and confirm ≥ 4.5:1; re-check any other surfaces the token lands on (cards, alt backgrounds) for the same threshold.

## 3. Summary Count

- Total documented pairs evaluated: **2** (with pair 1 spanning 2 contexts → 3 context evaluations)
- Distinct tokens reviewed: **2** (`color.text.muted`, `color.text.primary`)
- Multi-context tokens flagged: **1** (`color.text.muted`)
- Pairs/contexts passing AA under the strictest applicable threshold: **1** (`color.text.primary` on #FFFFFF)
- Pairs/contexts failing AA under the strictest applicable threshold: **1** (`color.text.muted` on #FFFFFF -- fails 4.5:1 normal-text threshold; the same token would pass 3:1 if used as a border only, but the multi-context rule forces the stricter threshold)
- Tokens requiring remediation: **1** (`color.text.muted`)
- Recommended action: split into `color.text.muted` (darkened to ≥ 4.5:1, e.g. #767676) and `color.border.input` (existing #888888 acceptable for 3:1 UI-component contrast), OR darken the single token to ≥ 4.5:1.
