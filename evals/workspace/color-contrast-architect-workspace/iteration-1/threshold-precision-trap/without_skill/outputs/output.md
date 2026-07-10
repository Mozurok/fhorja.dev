# Color Contrast Audit -- Light Theme Palette

**Standard:** WCAG 2.2 AA
**Scope:** Light theme only
**Method:** sRGB linearization + WCAG relative-luminance contrast formula: `(L1 + 0.05) / (L2 + 0.05)`. Ratios reported as computed (truncated, not rounded up to clear thresholds).

## WCAG 2.2 Thresholds (reference)

| Design context | AA threshold | AAA threshold |
|---|---|---|
| normal-text (< 18pt regular / < 14pt bold) | 4.5:1 | 7.0:1 |
| large-text (>= 18pt regular / >= 14pt bold) | 3.0:1 | 4.5:1 |
| ui-component (non-text UI, including button container vs adjacent surface) | 3.0:1 | n/a |

Note: For a button, the *text inside the button* is held to the text threshold (4.5:1 normal / 3:1 large). The `ui-component` 3:1 threshold governs the button's container against the surrounding surface -- not the button label against its own fill. This matters for pair #3 below.

---

## 1. Contrast Matrix

| # | Theme | Foreground token | Background token | Design context | Ratio | AA threshold | AAA threshold | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | light | `color.text.primary` (#222222) | `color.surface.background` (#FFFFFF) | normal-text | 15.90:1 | 4.5:1 | 7.0:1 | PASS AA, PASS AAA |
| 2 | light | `color.text.secondary` (#777777) | `color.surface.background` (#FFFFFF) | normal-text | 4.48:1 | 4.5:1 | 7.0:1 | FAIL AA (and AAA) |
| 3 | light | `color.button.primary.fg` (#FFFFFF) | `color.button.primary.bg` (#0066CC) | ui-component (button label is text -- held to 4.5:1) | 5.17:1 | 4.5:1 (label as text) / 3.0:1 (container) | 7.0:1 | PASS AA, FAIL AAA |
| 4 | light | `color.link.default` (#1A66CC) | `color.surface.background` (#FFFFFF) | normal-text | 5.48:1 | 4.5:1 | 7.0:1 | PASS AA, FAIL AAA |

### Precision note on pair #2

`#777777` on `#FFFFFF` computes to **4.48:1**, which is **below** the 4.5:1 AA normal-text threshold. The gap (0.02) is small enough that it is often misreported as "4.5" by tools that round to one decimal. Per the prompt's instruction, this is treated as a **fail** -- do not round up to clear the threshold.

### Precision note on pair #3

The documented design context is `ui-component`. If the only requirement were the non-text UI 3:1 rule (button container vs surrounding white surface), 5.17:1 would clear it comfortably. However, the foreground (`#FFFFFF`) is the **button label**, which is text rendered on the button fill. WCAG 2.2 SC 1.4.3 applies to that text against its background. 5.17:1 still clears the 4.5:1 normal-text AA bar, so the verdict is PASS AA either way -- but designers should not rely on the 3:1 UI threshold to justify lower-contrast button labels.

---

## 2. Failing Pairs -- Token-Level Remediation

Only **one pair fails AA**: pair #2 (`color.text.secondary` on `color.surface.background`).

### Failing pair #2: `color.text.secondary` (#777777) on `#FFFFFF`

- **Measured ratio:** 4.48:1
- **Required:** 4.5:1 (AA normal-text)
- **Shortfall:** 0.02

**Concrete remediation -- pick one:**

| Option | New token value | Resulting ratio on #FFFFFF | AA verdict |
|---|---|---|---|
| A (minimal change, recommended) | `color.text.secondary` = **#767676** | 4.54:1 | PASS AA |
| B (slightly darker, safer headroom) | `color.text.secondary` = **#757575** | 4.61:1 | PASS AA |
| C (clear AA margin, still feels "secondary") | `color.text.secondary` = **#6F6F6F** | 4.95:1 | PASS AA |
| D (AAA-compliant secondary) | `color.text.secondary` = **#595959** | 7.00:1 | PASS AAA |

**Recommendation:** Adopt **Option A (`#767676`)** as the new token value. It is the smallest visual shift from the current `#777777`, preserves the intended "secondary" hierarchy against `color.text.primary` (#222222), and clears AA with measurable headroom (4.54:1 vs 4.5:1 required).

If the design system also documents this token used on non-white surfaces (e.g., a tinted card background), re-audit each foreground/background pair with the chosen value -- `#767676` only clears AA against pure white.

---

## 3. Summary Counts

- **Total pairs audited:** 4
- **PASS AA:** 3 (pairs #1, #3, #4)
- **PASS AAA:** 1 (pair #1)
- **FAIL AA:** 1 (pair #2)
- **FAIL AAA only (still AA-compliant):** 2 (pairs #3, #4)

**Action required before shipping the light theme:** update `color.text.secondary` from `#777777` to a darker value (recommended `#767676`). All other documented pairs meet WCAG 2.2 AA.
