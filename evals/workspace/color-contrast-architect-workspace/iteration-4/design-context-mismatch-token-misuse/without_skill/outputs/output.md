# Token Context Audit: `color.text.disabled` (`#999999` on `#FFFFFF`)

**Measured contrast ratio:** ~2.85:1
**WCAG 2.1 AA thresholds:** 4.5:1 normal text, 3:1 large text (>=18pt regular or >=14pt bold)
**Relevant exception:** WCAG 1.4.3 -- text that is part of an **inactive UI component**, pure decoration, not visible, or part of a picture containing significant other visual content, has **no contrast requirement**.

---

## 1. Per-usage verdicts

### Usage 1 -- Disabled-button label

- **Verdict:** `PASS-with-exception`
- **Reasoning:** The label belongs to an inactive UI component. WCAG 1.4.3 explicitly exempts inactive components from the contrast minimum. 2.85:1 is intentionally low to signal "not interactable" -- this is the **designed semantic** of the token.
- **Caveat:** The exception is a floor, not a ceiling on quality. Some teams still target ~3:1 on disabled controls for usability, but it is not an AA failure.

### Usage 2 -- Small-print legal disclaimer under signup form

- **Verdict:** `FAIL-AA`
- **Reasoning:**
  - The disclaimer is **active, meaningful body content** the user is expected (and often legally required) to read.
  - It is **not** an inactive component, not decoration, not invisible -- none of the 1.4.3 exception clauses apply.
  - Small print is almost certainly <18pt regular / <14pt bold, so the 4.5:1 normal-text threshold governs.
  - 2.85:1 < 4.5:1 → fails WCAG 2.1 AA (1.4.3).
- **Aggravating factors:**
  - Legal/consent text carries downstream risk (GDPR, FTC, ToS enforceability) when illegible.
  - Small print is exactly the size class where low contrast does the most readability damage.

---

## 2. Canonical enum per usage

Using a standard design-system token-audit verdict enum:

| Usage | Enum | Notes |
|---|---|---|
| 1. Disabled-button label | `CORRECT_USE` (intent matches token semantic; passes via 1.4.3 exception) | Token is used in the context it was designed for. |
| 2. Legal disclaimer small print | `CONTEXT_MISMATCH` / `MISUSED_TOKEN` (and downstream `WCAG_AA_FAIL`) | Disabled-state token reused for active body text -- semantic of token ("this thing is inactive") contradicts the semantic of the surface ("read this carefully"). |

Two distinct failure classes, even though only one fails AA numerically:

- **Semantic misuse** (token meaning vs. usage meaning) -- present in Usage 2.
- **Contrast failure** (ratio vs. AA threshold) -- present in Usage 2.

Usage 1 has neither; Usage 2 has both.

---

## 3. Remediation -- can one token serve both contexts?

**No. They must fork.** The two contexts have **contradictory** requirements:

| Concern | Disabled control | Active small print |
|---|---|---|
| Communicates "non-interactive"? | Yes (required) | No (must not) |
| Subject to WCAG 1.4.3 contrast minimum? | No (exempt) | Yes |
| Target ratio on white | ~2.85:1 is acceptable | >=4.5:1 required |
| User must read it? | No | Yes |

A single token cannot simultaneously be "low enough to read as disabled" and "high enough to satisfy AA body text." Forcing one shared value will either:

- raise disabled contrast so high it stops signaling "disabled," or
- keep disclaimer contrast illegal and unreadable.

### Recommended token split

Introduce **two semantic tokens** (semantic, not raw color):

1. `color.text.disabled` -- keep `#999999` (~2.85:1). Scope strictly to inactive controls / disabled form fields / inactive nav items. Document the 1.4.3 exception in the token description so future consumers do not reuse it as "muted body text."
2. `color.text.secondary` (or `color.text.muted` / `color.text.subtle`) -- a new token for de-emphasized but **active** copy: disclaimers, helper text, captions, metadata, timestamps.
   - On `#FFFFFF` background, pick a value at **>=4.5:1** for normal text. Examples in that band:
     - `#767676` ≈ 4.54:1 (just clears AA -- tight, prefer darker)
     - `#737373` ≈ 4.74:1
     - `#6B6B6B` ≈ 5.25:1 (comfortable margin; recommended)
     - `#595959` ≈ 7.0:1 (clears AAA 7:1 -- safest for legal copy)
   - For legal/consent text specifically, target **AAA (7:1)** when feasible -- it is high-risk content and users span a wide accessibility range.

### Migration / enforcement

- Replace the disclaimer usage with `color.text.secondary` (or the AAA-grade legal variant if you create one, e.g. `color.text.legal`).
- Add a lint / Figma-token-audit rule: `color.text.disabled` is only valid on nodes whose component state is `disabled` (or inside `Button[state=disabled]`, `Input[state=disabled]`, etc.). Any other usage flags as `CONTEXT_MISMATCH`.
- Update the token's documentation with an explicit **"Do NOT use for"** list: body text, helper text, captions, disclaimers, placeholder text on active inputs, timestamps.
- Audit the codebase for other `color.text.disabled` references and re-classify each into `disabled` vs `secondary` vs `legal`.
- Consider a parallel `color.text.placeholder` token -- placeholder text is another frequent misuse site of `disabled` and has its own contrast nuances (it must look de-emphasized but remain legible on an **active** input).

### Bottom line

Usage 1 is correct. Usage 2 is both a **semantic token misuse** and a **WCAG 2.1 AA failure**. Fix by forking the token: keep `color.text.disabled` for inactive components only, and introduce a separate `color.text.secondary` (>=4.5:1) -- ideally an AAA-grade variant for legal copy -- for the disclaimer and any other active de-emphasized text.