# Contrast Audit: `color.text.disabled` Cross-Context Misuse

**Token under audit:** `color.text.disabled` = `#999999`
**Surface:** `color.surface.background` = `#FFFFFF`
**Computed ratio (WCAG 2.2, sRGB linearized):** `2.85:1` (rounded to two decimals, never rounded up across a threshold per Step 3)

---

## Per-usage verdict (Step 4 -- classify per design context)

| # | Usage | Design context | WCAG threshold | Ratio | Verdict | Notes |
|---|---|---|---|---|---|---|
| 1 | Disabled-button label | `ui-component` (disabled state, incidental text) | N/A -- WCAG 1.4.3 incidental-text exception applies | 2.85:1 | **PASS-with-exception** | Per WCAG 2.2 §1.4.3, text that is part of an inactive UI component is exempt from the 4.5:1 minimum. The token is being used as DESIGNED. |
| 2 | Small print legal disclaimer under signup form | `normal-text` (active, must-read content) | AA: 4.5:1 / AAA: 7:1 | 2.85:1 | **FAIL-AA** | Disclaimers are user-facing, must-read prose. Not incidental. Not decorative. Not inactive. The 1.4.3 exception does **not** apply -- users are legally and operationally required to consume this text. |

### Why the exception cannot stretch to cover usage #2 (Step 4 + Step 8 discipline)

WCAG 2.2 §1.4.3 lists narrow exceptions: logos, incidental text, inactive UI components, pure decoration. A signup-form legal disclaimer fails all four tests:

- **Not incidental:** disclaimers carry consent, liability, and regulatory weight (TOS, privacy notice, marketing consent).
- **Not inactive:** the surrounding form is active; the disclaimer governs the active interaction.
- **Not decoration:** it conveys meaning the user must read to make an informed choice.
- **Not a logo:** self-evident.

Scoring usage #2 against `ui-component` (3:1) instead of `normal-text` (4.5:1) would be the exact failure mode the persona's Quality Bar calls out: "a pair scored as `ui-component` when it is actually serving as small body text is worse than no audit, because it manufactures false confidence." Per Step 4's multi-context rule, when a token serves multiple contexts the audit scores against the **strictest applicable threshold** -- for usage #2, that is `normal-text` AA at 4.5:1, which `2.85:1` fails decisively.

---

## Canonical enum per usage (Step 4 labels)

- **Usage 1 -- Disabled-button label:** `ui-component` → with WCAG 1.4.3 incidental/inactive exception explicitly invoked. Recorded verdict: `PASS-with-exception` (a documented variant of `PASS-AA`, NOT `PASS-AA` unqualified, because the pass is conditional on the inactive-component scope).
- **Usage 2 -- Signup disclaimer copy:** `normal-text` → AA 4.5:1 threshold. Recorded verdict: `FAIL-AA`. No exception is available.

Both rows belong in `<task>/CONTRAST_AUDIT.md` as separate entries even though the token and surface are identical -- per Step 5, every documented pair × context combination is one row; silent omission or row-merging across contexts is forbidden.

---

## Remediation -- can one token serve both contexts? (Step 6)

**No. Fork the token.** A single value cannot simultaneously satisfy:

1. The DESIGN intent of `color.text.disabled` -- visually communicate "this control is inactive" by being deliberately low-contrast against the surface. Darkening it to clear AA (e.g. `#767676` at ~4.54:1) destroys the affordance: disabled buttons start looking enabled, which is a worse accessibility outcome (cognitive / state-recognition failure trades one WCAG concern for another).
2. The READING requirement of small-print disclaimer copy -- clear AA against the surface so users can actually read the consent text.

These intents are mutually exclusive at one hex value. The remediation is structural, not numeric.

### Recommended token delta

Introduce a distinct token whose name encodes its **purpose**, not its **appearance**:

| Token | Value (proposed) | Ratio on `#FFFFFF` | Design context | Verdict at proposed value |
|---|---|---|---|---|
| `color.text.disabled` (keep) | `#999999` | 2.85:1 | `ui-component` / inactive -- 1.4.3 exception | PASS-with-exception |
| `color.text.subtle` *(new)* -- for small print, captions, helper text, legal disclaimers | `#595959` | 7.00:1 | `normal-text` -- AAA-clean for small-print legibility | PASS-AAA |

Rationale for `#595959` rather than the minimum-viable `#767676`: small print is typically rendered below the body font size, and the multi-context rule from Step 4 plus the small-text legal-reading use case argue for AAA headroom rather than just-barely-AA. Picking the minimum at `#767676` (4.54:1 AA) leaves no margin if the type ever drops to 12px or below, or if any consumer renders this token at reduced opacity.

### Why not "just override at usage site"?

Overriding `color.text.disabled` to a darker value at the disclaimer call-site re-introduces exactly the downstream rework loop the persona is designed to prevent (Quality Bar): the token's documented intent and its rendered appearance diverge, every future consumer has to re-decide which value to use, and the next reviewer sees `color.text.disabled` applied to active body copy with no semantic signal that it has been re-purposed. A new purpose-named token (`color.text.subtle`) is the load-bearing remediation; raw hex overrides at the call-site are the failure mode.

### Migration step for the disclaimer call-site

Replace `color.text.disabled` with `color.text.subtle` at the signup-disclaimer usage. The disabled-button usage stays on `color.text.disabled` unchanged. No surface or layout change required.

---

## Tooling caveats surfaced (Step 8)

- The 2.85:1 ratio assumes the disclaimer is rendered directly on `color.surface.background` with no overlay, no reduced opacity, and no background-image blend. If the signup form sits on a tinted card surface (`color.surface.subtle` or similar), the audit must be re-run against that effective background -- the failing verdict for usage #2 only gets worse on any non-white surface, never better.
- If `color.text.disabled` is referenced via an alias chain (e.g. `color.text.disabled → color.neutral.500 → #999999`), the proposed fork must be applied at the **semantic** layer (`color.text.subtle` as a new top-level semantic token aliasing to a neutral palette stop), not at the neutral-palette layer. Editing `color.neutral.500` would silently retune every other consumer of that neutral stop.
- WCAG 2.2 §1.4.11 (non-text contrast, 3:1) governs the disabled button's **border or shape** against the surrounding surface -- out of scope for this audit, but the reviewer should confirm a separate row exists in `CONTRAST_AUDIT.md` for the disabled-button border-vs-surface pair if the disabled state is conveyed by anything other than the label color alone.

---

## Summary

- **Usage 1:** `PASS-with-exception` -- keep token, keep value, keep usage. WCAG 1.4.3 incidental/inactive carve-out is correctly invoked.
- **Usage 2:** `FAIL-AA` -- token misapplied to a context the exception does not cover. Same hex on the same surface produces the same ratio; the WCAG verdict differs because the **design context** differs, which is the whole point of Step 4.
- **Remediation:** fork the token. Introduce `color.text.subtle = #595959` (PASS-AAA at 7.00:1) for must-read small print; preserve `color.text.disabled = #999999` for inactive-component labels. Single-token reuse across these two contexts is not recoverable by any numeric adjustment.