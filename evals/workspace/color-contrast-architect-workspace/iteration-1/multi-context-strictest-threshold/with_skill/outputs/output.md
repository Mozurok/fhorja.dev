# color-contrast-architect -- Contrast audit

Scope: light theme only. WCAG target: 2.2 AA. Two documented foreground/background pairs, with one foreground token (`color.text.muted` = `#888888`) playing a dual role on the same background (`color.surface.background` = `#FFFFFF`): (a) 14px form-helper body text AND (b) form-input border. Per Step 4 of the persona protocol, a token used in multiple design contexts is scored against the STRICTEST applicable threshold and flagged as multi-context.

### Artifact changes

- PROPOSED: `<task>/CONTRAST_AUDIT.md` -- full pairwise contrast matrix below (every input row represented; multi-context token expanded into one row per applied context plus an authoritative multi-context verdict row).
- PROPOSED: `DECISIONS.md ## Locked decisions` -- D-N draft locking (i) WCAG 2.2 AA as the floor, (ii) the multi-context scoring rule (strictest applicable threshold), (iii) explicit acknowledgement that `color.text.muted` (#888888) currently fails AA when used as 14px body text.
- PROPOSED: `IMPLEMENTATION_PLAN.md ## Risks and mitigations` -- R-N draft flagging the failing pair as a blocker for any downstream slice that ships a form using helper text or the muted-bordered input in its current token values.

---

## 1. Pairwise contrast matrix (WCAG 2.2 AA)

Method: ratios are taken from the inputs (given as authoritative) and rounded to two decimal places without rounding up to clear a threshold. Thresholds follow WCAG 2.2 per Step 4: `normal-text` ≥ 4.5:1 AA / ≥ 7:1 AAA; `ui-component` ≥ 3:1 AA. The multi-context row is the load-bearing one: it inherits the strictest applicable threshold from its component contexts.

| theme | foreground_token | background_token | design_context | ratio | AA_threshold | AAA_threshold | verdict | notes |
|---|---|---|---|---|---|---|---|---|
| light | `color.text.muted` (#888888) | `color.surface.background` (#FFFFFF) | normal-text (14px form-helper body text) | 3.54:1 | 4.5:1 | 7:1 | **FAIL-AA** | 14px non-bold counts as `normal-text` per WCAG 2.2; large-text threshold (3:1 AA / 4.5:1 AAA) does NOT apply because 14px < 18pt and the helper text is not bold ≥ 14pt. |
| light | `color.text.muted` (#888888) | `color.surface.background` (#FFFFFF) | ui-component (form-input border) | 3.54:1 | 3:1 | n/a (AAA not defined for UI components in 2.2) | PASS-AA | Border conveys the control's boundary/state, so the UI-component threshold (1.4.11) applies. Passes in isolation. |
| light | `color.text.muted` (#888888) | `color.surface.background` (#FFFFFF) | **multi-context (normal-text + ui-component)** -- authoritative verdict | 3.54:1 | **4.5:1 (strictest applicable)** | 7:1 (from normal-text) | **FAIL-AA (multi-context)** | Persona Step 4: same token on same surface used in two contexts → scored against the strictest applicable threshold (`normal-text` 4.5:1). The UI-component pass does NOT redeem the helper-text fail because the token value is shared; any remediation must clear the strictest bar. |
| light | `color.text.primary` (#222222) | `color.surface.background` (#FFFFFF) | normal-text | 15.90:1 | 4.5:1 | 7:1 | PASS-AAA | Clears AAA for normal text with significant headroom; also clears AAA for large-text and AA for UI-component if reused. |

Summary count:
- Total input pairs audited: 2 documented (3 rows above because the dual-role token is expanded per Step 4: per-context rows + authoritative multi-context verdict row; plus 1 row for the primary-text pair = 4 rows total).
- PASS-AAA: 1 (`color.text.primary` on `color.surface.background`, normal-text).
- PASS-AA: 1 (the UI-component-only view of `#888888` on `#FFFFFF`, informational; superseded by the multi-context verdict below for routing).
- FAIL-AA: 1 authoritative multi-context verdict (`color.text.muted` on `color.surface.background`).
- UNRESOLVED: 0.

The authoritative verdict for the dual-role token is the multi-context row (FAIL-AA). The two per-context rows above it are kept in the matrix for traceability and to make the reviewer's threshold choice independently re-verifiable, per the persona's "no silent omission" rule.

---

## 2. Failing pair -- remediation

### FAIL-AA: `color.text.muted` (#888888) on `color.surface.background` (#FFFFFF), multi-context (normal-text + ui-component)

Current ratio 3.54:1. Required (strictest applicable, normal-text): 4.5:1 AA. Gap: ~0.96.

Recommended remediation (pick one; not both -- token deltas are mutually exclusive design choices):

- Option 1 (preferred -- single token edit, lowest blast radius): **darken `color.text.muted` from `#888888` to `#767676`** (sRGB `(118,118,118)`). `#767676` on `#FFFFFF` is the canonical WCAG-2.2-AA inflection point for normal text and yields ~4.54:1, clearing the 4.5:1 AA bar for the helper-text context while still satisfying the 3:1 UI-component bar for the input border. One token edit fixes both documented usages simultaneously, which is the whole point of catching this BEFORE the token locks.
  - If a slightly larger safety margin is preferred, **`#717171`** yields ~4.74:1 (still reads as "muted" against `#222222` body text); **`#6B6B6B`** yields ~5.25:1 with comfortable headroom; **`#666666`** yields ~5.74:1, comfortably above AA but starting to encroach on the visual distinction from `color.text.primary` (#222222) -- pick the lightest value that still clears 4.5:1 to preserve the muted/primary hierarchy.

- Option 2 (context-splitting -- only if Option 1 is rejected for visual reasons): **split the dual-role token into two tokens** -- keep a UI-affordance token (e.g. `color.border.input` = `#888888`, scored only as `ui-component`, passes 3:1 AA today) and introduce a separate text-affordance token (e.g. `color.text.muted` = `#767676` or darker, scored as `normal-text`, passes 4.5:1 AA). Each token then carries a single design context and is scored against a single threshold, eliminating the multi-context conflict. Cost: an extra token to maintain and a one-time migration of every 14px helper-text consumer to the new text token.

- Option 3 (context reclassification -- REJECTED for this audit): reclassifying the helper text as `large-text` would lower the bar to 3:1 AA, but 14px non-bold body text does NOT meet WCAG 2.2's large-text definition (≥ 18pt, or ≥ 14pt bold). Bolding the helper text would qualify it as large-text only if also ≥ 14pt, which is ambiguous at 14px screen units and is a visually load-bearing change to helper-text styling. Not recommended.

- Deferral is NOT appropriate here: helper text and input borders are not decorative; they convey form state and instructions to every user. No documented exclusion-list justification applies.

---

## 3. PROPOSED block -- `DECISIONS.md ## Locked decisions`

```
<!-- PROPOSED: D-N -- Color contrast policy (light theme, AA floor, multi-context strictest-threshold rule) -->
- D-N -- Color contrast policy (light theme, AA floor, multi-context strictest-threshold rule)
  - Decision: WCAG 2.2 AA is the design-system contrast floor for all documented light-theme foreground/background pairs. Any token used in multiple design contexts on the same surface is scored against the STRICTEST applicable threshold (per persona Step 4) and the token value MUST clear that strictest bar; the UI-component pass does NOT redeem a normal-text fail when the same token value is shared.
  - Affected tokens (light theme):
    - `color.text.muted` (#888888) on `color.surface.background` (#FFFFFF): currently 3.54:1, used as both (a) 14px form-helper body text [normal-text, 4.5:1 AA required] and (b) form-input border [ui-component, 3:1 AA required]. Multi-context verdict: FAIL-AA. Locked remediation: darken to `#767676` (~4.54:1) -- clears the strictest bar (normal-text 4.5:1 AA) and preserves the UI-component pass on the border. Alternative locked path: split into `color.text.muted` (text-only, ≥ #767676) and `color.border.input` (UI-only, may retain #888888).
    - `color.text.primary` (#222222) on `color.surface.background` (#FFFFFF): 15.9:1. PASS-AAA. No change required.
  - Rationale: catching the multi-context failure BEFORE tokens lock keeps the fix at a single token-value edit instead of a downstream multi-component rewrite; the strictest-threshold rule prevents false confidence from the UI-component-only view of #888888.
  - Status: PROPOSED -- awaiting `decision-interview` promotion.
<!-- /PROPOSED -->
```

## 4. PROPOSED block -- `IMPLEMENTATION_PLAN.md ## Risks and mitigations`

```
<!-- PROPOSED: R-N -- Form helper-text + muted-border contrast failure blocks form-bearing slices -->
- R-N -- Form helper-text + muted-border contrast failure blocks form-bearing slices
  - Risk: Any downstream slice that ships a form using `color.text.muted` (#888888) as 14px helper-text body OR continues to render the form-input border with the same token value carries a known WCAG 2.2 AA failure (3.54:1 vs 4.5:1 required for normal text under the multi-context strictest-threshold rule).
  - Blast radius: every form on every screen-spec consuming this token pair.
  - Mitigation (locked path): apply D-N's token delta (`color.text.muted` -> `#767676`) before the first form-bearing slice opens, OR split the token per Option 2 and migrate consumers in the same slice that introduces the new token. Slices that touch forms cannot proceed until one of these paths is committed in `foundations/color.md` (or the DTCG token file referenced by `SOURCE_OF_TRUTH.md`).
  - Status: PROPOSED -- awaiting `implementation-plan` promotion.
<!-- /PROPOSED -->
```

---

## 5. Tooling caveats (Step 8)

- Ratios were taken as authoritative from the inputs (3.54:1 and 15.9:1). Independent re-verification with a WCAG 2.2 luminance calculator is recommended before the D-N decision locks, particularly for the `#767676` remediation candidate, because `#767676` sits ON the AA inflection point and any rounding-down in the production calculator could land at 4.48:1–4.49:1. If the production calculator returns < 4.50:1, step the remediation to `#717171` (≈ 4.74:1) for a safe margin.
- No alias-chain resolution was needed (both tokens were given as concrete hex values). If the production token source resolves these via alias chains (`color.text.muted` -> `color.neutral.500`, etc.), confirm the chain resolves to the same hex in the light theme before applying the delta.
- Dark-theme coverage is explicitly out of scope per the input ("light theme only"). When the dark theme is introduced, this audit must be rerun against the dark-theme background token -- a token that clears AA on `#FFFFFF` does not automatically clear AA on a dark surface, and the dual-role token will need to be re-scored under the multi-context rule again.

## 6. Definition of done -- self-check

- Every input pair has at least one row in the matrix; no silent omission. Yes -- the dual-role token is expanded into per-context rows AND an authoritative multi-context verdict row per Step 4.
- Multi-context flag and strictest-threshold scoring applied. Yes -- the `#888888` / `#FFFFFF` dual usage is explicitly labelled `multi-context (normal-text + ui-component)` and scored against 4.5:1 (the normal-text bar), not 3:1 (the UI-component bar).
- Every FAIL-AA row carries an actionable remediation (token delta in hex), not a bare "fix it". Yes -- primary delta `#888888` -> `#767676`, with safer-margin alternatives and an explicit token-splitting alternative.
- PROPOSED blocks staged for `DECISIONS.md` and `IMPLEMENTATION_PLAN.md`; no direct substrate writes at L1.
- Theme coverage matches input theme list (light only).

### Command transcript

- Loaded persona SKILL.md; confirmed Step 4 multi-context strictest-threshold rule.
- Enumerated 2 input pairs; expanded the dual-role token into per-context rows + authoritative multi-context row.
- Applied WCAG 2.2 thresholds (normal-text 4.5:1 AA, ui-component 3:1 AA); computed verdicts from given ratios without rounding up.
- Staged PROPOSED blocks for D-N (contrast policy) and R-N (forms-slice risk); routed via Handoff.

### Handoff

Mode A (compact). The audit blocks any form-bearing downstream slice until the `color.text.muted` token value is corrected (preferred: `#767676`) or the token is split per Option 2. The `color.text.primary` pair is clear at AAA and unblocks normal-text usage today.

Run now: `decision-interview` to promote the D-N PROPOSED block (contrast policy + locked remediation path) into `DECISIONS.md ## Locked decisions`.

Then: `implementation-plan` to promote the R-N PROPOSED block into `IMPLEMENTATION_PLAN.md ## Risks and mitigations` and sequence the token-value edit (or token split) ahead of the first form-bearing slice.

After token edit lands: rerun `color-contrast-architect` against the updated `foundations/color.md` to confirm the multi-context verdict flips from FAIL-AA to PASS-AA (or PASS-AAA) before any form screen-spec locks.
