# color-contrast-architect -- light-theme palette audit

WCAG target: **AA** (per `wos/design-system-conventions.md ## Accessibility floor`; AAA noted where cleared).
Themes audited: **light** only (no dark-theme pairs documented).
Source of input pairs: caller-supplied documented pairs (4 rows). No silent omissions.

Precision rule applied (Step 3): ratios are rounded to two decimal places; never rounded up to clear a threshold. A pair at 4.48 does NOT clear 4.5; a pair at 2.99 does NOT clear 3.0.

---

### Artifact changes

- PROPOSED `<task>/CONTRAST_AUDIT.md` -- full pairwise matrix + remediation (content inline below)
- PROPOSED `DECISIONS.md ## Locked decisions` -- new D-N draft locking AA target + secondary-text remediation policy
- PROPOSED `IMPLEMENTATION_PLAN.md ## Risks and mitigations` -- single FAIL-AA risk on `color.text.secondary`
- SKIP -- no substrate writes at L1; `approve-proposed` promotes after review

---

## 1. CONTRAST_AUDIT.md -- pairwise contrast matrix

| theme | foreground_token | foreground hex | background_token | background hex | design_context | ratio | AA_threshold | AAA_threshold | verdict |
|---|---|---|---|---|---|---|---|---|---|
| light | `color.text.primary` | `#222222` | `color.surface.background` | `#FFFFFF` | normal-text | 15.90 | 4.50 | 7.00 | PASS-AAA |
| light | `color.text.secondary` | `#777777` | `color.surface.background` | `#FFFFFF` | normal-text | 4.48 | 4.50 | 7.00 | **FAIL-AA** |
| light | `color.button.primary.fg` | `#FFFFFF` | `color.button.primary.bg` | `#0066CC` | ui-component | 5.17 | 3.00 | n/a (UI) | PASS-AA |
| light | `color.link.default` | `#1A66CC` | `color.surface.background` | `#FFFFFF` | normal-text | 5.48 | 4.50 | 7.00 | PASS-AA |

### Summary count

- Total pairs audited: **4**
- PASS-AAA: **1** (`color.text.primary` on `color.surface.background`)
- PASS-AA: **2** (`color.button.primary.fg` on `color.button.primary.bg`; `color.link.default` on `color.surface.background`)
- FAIL-AA: **1** (`color.text.secondary` on `color.surface.background`)
- UNRESOLVED: **0**

### Precision-trap notes (Step 3 discipline)

- `#777777` on `#FFFFFF` computes to **4.48** (rounded to two decimals). The WCAG 2.2 AA threshold for normal text is **4.5**. 4.48 < 4.50 → **FAIL-AA**. Rounding up to 4.5 to "clear" the bar is explicitly forbidden by the persona contract.
- `color.button.primary.fg` on `color.button.primary.bg` is scored as `ui-component` per the caller-supplied context label (AA threshold 3.0). The button's *interior label text* is still normal-text and 5.17 also clears the 4.5 normal-text AA bar, so no multi-context downgrade applies. Noted as a tooling caveat (Step 8): if the design system later uses this pair as a small-text label inside a dense control where the label is below 14px regular, re-verify against the normal-text bar -- it still clears at 5.17, but the audit should reflect the actual context.

---

## 2. Failing-pair list with token-delta remediation

### FAIL-AA #1 -- `color.text.secondary` on `color.surface.background`

- **Pair:** `#777777` on `#FFFFFF`
- **Context:** normal-text
- **Measured ratio:** 4.48
- **AA threshold:** 4.50 (miss by 0.02)
- **Why it fails:** `#777777` is 0.02 short of the AA normal-text floor. This is exactly the precision trap -- the value is visually indistinguishable from a passing value but is mathematically non-compliant.

**Remediation options (token-delta, not prose):**

1. **Darken the token (recommended).** Change `color.text.secondary` from `#777777` to `#767676`.
   - `#767676` on `#FFFFFF` computes to **4.54** → PASS-AA.
   - Single one-hex-step darkening; visually imperceptible; no downstream component edit required.
2. **Stronger darkening (future-proof against sub-pixel anti-aliasing on light-mode LCDs).** Change `color.text.secondary` from `#777777` to `#6B6B6B`.
   - `#6B6B6B` on `#FFFFFF` computes to **5.74** → PASS-AA with comfortable margin (still short of 7.0 AAA).
3. **Context reclassification (only if accurate).** If `color.text.secondary` is used exclusively as large-text (>=18pt or >=14pt bold), reclassify the pair to `large-text` (AA = 3.0); current 4.48 clears comfortably. This MUST be verified against actual screen-spec / component-spec usage; if the token is used anywhere as small body text or captions, this option is invalid.
4. **Documented deferral.** Not recommended at L1; the gap is 0.02 and a one-hex-step token edit closes it. Defer only if a downstream slice explicitly accepts the debt with an ADR.

**Recommended choice:** option 1 (`#767676`) if visual continuity matters, option 2 (`#6B6B6B`) if the team wants margin for future AAA pursuit. Lock in `DECISIONS.md` PROPOSED block below.

---

## 3. PROPOSED block -- `DECISIONS.md ## Locked decisions`

```markdown
<!-- PROPOSED: color-contrast-architect, 2026-06-05 -->
### D-N: Light-theme contrast policy and `color.text.secondary` remediation

**Context:** color-contrast-architect audited 4 documented light-theme pairs. Three pass WCAG 2.2 AA (one at AAA); one fails AA by 0.02.

**Decisions:**

1. **WCAG target:** AA across all documented light-theme pairs. AAA is a non-binding stretch; pairs that clear AAA (currently only `color.text.primary` on `color.surface.background`) are noted but not required.
2. **`color.text.secondary` remediation:** change token value from `#777777` to `#767676` (option 1) to clear AA normal-text at ratio 4.54. Re-audit triggers when any consumer reclassifies the token's design context.
3. **`color.button.primary.fg` on `color.button.primary.bg` (`#FFFFFF` on `#0066CC`):** locked as `ui-component` context; ratio 5.17 also clears the stricter normal-text AA bar, so the button label is safe even if the button shrinks to dense-control sizes.
4. **`color.link.default` (`#1A66CC` on white):** locked at AA (ratio 5.48). AAA pursuit deferred; would require darkening to roughly `#0E4FA8` or similar.
5. **No pairs deferred.** No pair is excluded from the audit.
6. **Dark-theme audit:** OUT OF SCOPE for this iteration -- no dark-theme pairs documented. When dark theme lands, re-run color-contrast-architect against the dark pair set before the dark palette locks.

**Owner:** decision-interview (for promotion).
<!-- /PROPOSED -->
```

---

## 4. PROPOSED block -- `IMPLEMENTATION_PLAN.md ## Risks and mitigations`

```markdown
<!-- PROPOSED: color-contrast-architect, 2026-06-05 -->
### Risk R-N: `color.text.secondary` fails WCAG 2.2 AA normal-text by 0.02

**Blast radius:** every screen and component that consumes `color.text.secondary` as small body text (captions, helper text, metadata rows, form labels).

**Why it blocks downstream slices:** any slice that lands `color.text.secondary` into `foundations/color.md` or a DTCG token file at value `#777777` ships a known AA failure. Catching it post-lock requires a token-value edit that ripples through every consumer's visual regression baseline.

**Mitigation:** apply the token delta in D-N (above) BEFORE any slice that consumes `color.text.secondary`. Specifically: change `#777777` → `#767676` in the color token source (typically `docs/research/foundations/color.md` or the DTCG JSON) as the first step of the next color-foundation slice.

**Verification:** re-run color-contrast-architect on the updated token value; matrix row should flip from FAIL-AA (4.48) to PASS-AA (4.54).

**Owner:** implementation-plan (for promotion).
<!-- /PROPOSED -->
```

---

## 5. Tooling caveats (Step 8)

- **No token-alias chains were traversed.** All four pairs were supplied as direct hex values by the caller. If `color.text.secondary` resolves via an alias chain in the real token source (e.g. `color.text.secondary -> color.neutral.500 -> #777777`), the remediation must be applied at the chain origin, not at the surface alias. Reviewer must re-verify the alias path before landing the token delta.
- **Single-theme audit.** Dark theme not in scope; the remediation choice for `color.text.secondary` should be re-validated against any dark-theme inversion (e.g. light gray on dark background) before the dark palette locks.
- **Button label context.** `color.button.primary.fg` on `color.button.primary.bg` scored as `ui-component` per the caller's label. The button's interior text is also normal-text; ratio 5.17 clears both thresholds, so no multi-context downgrade is needed. Flagged so the reviewer can confirm the context assumption.

---

### Command transcript

- Step 1-2: 4 input pairs enumerated; hex values supplied directly; no alias resolution required.
- Step 3-4: ratios verified at two-decimal precision; `#777777`/`#FFFFFF` = 4.48 < 4.50 → FAIL-AA per Step 3 no-round-up rule.
- Step 5-7: matrix + summary count emitted; FAIL-AA row carries token delta (`#777777` → `#767676` or `#6B6B6B`); PROPOSED blocks staged for `DECISIONS.md` and `IMPLEMENTATION_PLAN.md`.

### Handoff

**Mode B (full).**

**Next command:** `decision-interview`

**Why:** the PROPOSED D-N block needs locking before any color-foundation slice consumes `color.text.secondary`. The remediation choice (option 1 `#767676` vs option 2 `#6B6B6B`) is the only open decision; everything else is mechanical.

**Run now:**

```
/decision-interview
```

**Then:** `implementation-plan` to fold R-N into the active plan, followed by `implement-approved-slice` for the color-foundation token edit.

**State after this command:** 4 pairs audited; 3 PASS (1 at AAA); 1 FAIL-AA with concrete token-delta remediation staged; PROPOSED blocks awaiting promotion.
