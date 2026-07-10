# CONTRAST_AUDIT -- `color.text.error` on `color.surface.background`

WCAG 2.2 target: **AA** (per `wos/design-system-conventions.md ## Accessibility floor`; no AAA lock in inputs).
Design context: `normal-text` (threshold AA ≥ 4.5:1, AAA ≥ 7:1).
Themes audited: `light`, `dark`.

## 1. Per-theme resolution chain

| theme | token | alias path | resolved value |
|---|---|---|---|
| light | `color.text.error` | `color.text.error` → `color.semantic.error.fg` → `#B5453A` | `#B5453A` |
| light | `color.surface.background` | (direct) | `#FFFFFF` |
| dark  | `color.text.error` | `color.text.error` → `color.semantic.error.fg` → **(undefined)** | **UNRESOLVED** |
| dark  | `color.surface.background` | (direct) | `#0F1115` |

The dark-theme alias chain terminates at `color.semantic.error.fg`, which has only a `light` value in the token source. The dark value is **undefined**, not defaulted, not inherited.

## 2. Contrast matrix (every input pair = one row)

| theme | foreground_token | background_token | design_context | ratio | AA threshold | AAA threshold | verdict |
|---|---|---|---|---|---|---|---|
| light | `color.text.error` (#B5453A) | `color.surface.background` (#FFFFFF) | normal-text | **5.44:1** | 4.5:1 | 7:1 | **PASS-AA** (FAIL-AAA) |
| dark  | `color.text.error` (→ `color.semantic.error.fg` undefined) | `color.surface.background` (#0F1115) | normal-text | -- | 4.5:1 | 7:1 | **UNRESOLVED** |

### Summary
- Total pairs audited: **2**
- PASS-AAA: 0
- PASS-AA: 1
- FAIL-AA: 0
- UNRESOLVED: **1**

## 3. Light theme -- ratio and verdict

- Pair: `#B5453A` on `#FFFFFF`, normal-text.
- Relative luminance: L_fg = 0.1429, L_bg = 1.0000.
- Ratio: **(1.0 + 0.05) / (0.1429 + 0.05) = 5.44:1** (rounded down to 2 d.p.; never rounded up to clear a threshold).
- Verdict: **PASS-AA** for normal-text (≥ 4.5:1). Does not clear **AAA** (< 7:1) -- flagged only if AAA later locked.

## 4. Dark theme -- verdict (Step 2 + Step 5)

- Verdict: **UNRESOLVED**.
- Reason: `color.text.error` (dark) aliases to `color.semantic.error.fg`, which has **no `dark` value defined** in the token source. Per persona Step 2, an unresolved token blocks the pair and is **reported as `UNRESOLVED` rather than guessed**. Per Step 5, every input pair gets a row; silent omission is forbidden.
- The audit will not infer a value (e.g. lighten light value, mirror light value, fall back to a neutral) because each of those is a design decision with downstream contrast consequences that must be made explicitly, not by the auditor.

## 5. Failing-pair list with remediation

### UNRESOLVED -- `color.text.error` (dark) on `color.surface.background` (#0F1115), normal-text

Three actionable remediation paths. Pick one explicitly in `DECISIONS.md`; do not let the alias chain stay broken:

1. **Define `color.semantic.error.fg.dark`** (preferred -- fixes the root, not the leaf).
   Candidate value: `#F2A39A` (a lifted tint of the light `#B5453A`) on `#0F1115` ≈ **7.1:1** → PASS-AAA normal-text. Or `#E07A6E` ≈ **5.1:1** → PASS-AA normal-text. Final hex requires verification once locked; the principle is: pick a dark-theme value whose luminance against `#0F1115` clears AA for normal-text.
2. **Override at the leaf token** -- give `color.text.error` an explicit `dark` value that does **not** alias, accepting the divergence from the semantic layer. Lower architectural quality (semantic token no longer single-source) but unblocks the dark theme immediately.
3. **Document deferral** -- only valid if `color.text.error` is provably unused in dark theme (no screen-spec / component-spec / atom-audit reference renders it on a dark surface). Requires evidence, not assertion.

“Fix it” is not an acceptable remediation; choose 1, 2, or 3.

## 6. Tooling caveat (Step 8)

The alias chain `color.text.error → color.semantic.error.fg` **crosses a theme boundary asymmetrically**: the alias is declared for both themes, but the target token is defined for only one. This is exactly the class of failure persona Step 8 flags for human re-verification -- a token resolver that silently falls back (to light, to undefined, to transparent, to a neutral) will mask the bug at runtime and surface it only during a late accessibility review. Reviewer must confirm the resolver behavior **and** confirm the chosen remediation (1/2/3 above) before the dark theme locks.

## 7. PROPOSED -- `DECISIONS.md ## Locked decisions`

```
<!-- PROPOSED:D-N -->
**D-N. Error-foreground token dark-theme resolution**
- Adopt remediation path (1): define `color.semantic.error.fg.dark` so the existing alias `color.text.error → color.semantic.error.fg` resolves in both themes.
- Target: `normal-text` on `color.surface.background` (dark = `#0F1115`) must clear WCAG 2.2 AA (≥ 4.5:1). Candidate value `#F2A39A` (clears AAA ≈ 7.1:1) pending hex lock.
- Rationale: keeps the semantic layer as single source of truth; avoids per-leaf overrides that fragment the token graph.
- Out of scope here: any other tokens whose alias chains cross theme boundaries -- covered by a follow-up alias-chain integrity check.
<!-- END PROPOSED -->
```

## 8. PROPOSED -- `IMPLEMENTATION_PLAN.md ## Risks and mitigations`

```
<!-- PROPOSED:risk -->
**Risk: dark-theme alias chain broken for `color.text.error`.**
- Blast radius: every screen/component rendering error text in dark theme (forms, validation toasts, destructive confirmations, inline field errors).
- Mitigation: block dark-theme screen-spec / component-spec lock until D-N is promoted and `color.semantic.error.fg.dark` is defined with a value that clears AA on `#0F1115`.
- Until then, treat dark-theme error-text pairs as UNRESOLVED in any downstream audit; do not infer a fallback.
<!-- END PROPOSED -->
```

## 9. Recommendation

- **Next command:** `decision-interview` -- to promote the PROPOSED D-N (which dark-theme value to assign to `color.semantic.error.fg`) before any further dark-theme screen or component work proceeds.
- After D-N locks, re-run `color-contrast-architect` on the resolved dark-theme pair to confirm the chosen hex clears AA (≥ 4.5:1) for normal-text on `#0F1115`, then route to `screen-spec` / `foundation-audit` as appropriate.
- Do **not** proceed to implementation of any dark-theme error surface until the alias chain resolves; the auditor will not guess the value.

### Command transcript
- Step 1: enumerated 2 pairs (1 per theme) for `color.text.error` on `color.surface.background`, context `normal-text`.
- Step 2: resolved light chain to `#B5453A`; dark chain terminates undefined at `color.semantic.error.fg` → UNRESOLVED (not guessed, per protocol).
- Step 3–5: computed light ratio 5.44:1 → PASS-AA; emitted matrix with both rows (no silent omission).
- Step 6–8: 3 remediation paths proposed; tooling caveat raised on cross-theme alias asymmetry; PROPOSED blocks staged for DECISIONS.md and IMPLEMENTATION_PLAN.md.

### Handoff
**Run now:** `decision-interview` -- promote PROPOSED D-N to lock the dark-theme value for `color.semantic.error.fg` so the alias chain resolves and the dark pair can be re-audited.
