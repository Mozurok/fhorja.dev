# color-contrast-architect -- Contrast Audit (light + dark)

WCAG target: **2.2 AA** (floor per `wos/design-system-conventions.md ## Accessibility floor`; no AAA lock detected in inputs).
Themes audited: `light`, `dark`.
Pairs audited: 2 documented usage pairs × 2 themes = 4 rows. No silent omissions.

---

### Artifact changes

PROPOSED -- `<task>/CONTRAST_AUDIT.md` (full content below; persona-owned report file, written directly per Step 5 since it is not a substrate section).

PROPOSED -- `DECISIONS.md ## Locked decisions` (new D-N draft, content below; routes through `decision-interview` for promotion).

PROPOSED -- `IMPLEMENTATION_PLAN.md ## Risks and mitigations` (new risk entry, content below; routes through `implementation-plan` for promotion because the broken alias chain blocks any dark-theme notification work).

---

## 1. Token resolution per theme (Step 2)

| Token | Theme | Alias chain | Resolved sRGB | Status |
|---|---|---|---|---|
| `color.surface.background` | light | (direct) | `#FFFFFF` | resolved |
| `color.surface.background` | dark  | (direct) | `#0F1115` | resolved |
| `color.text.primary` | light | (direct) | `#222222` | resolved |
| `color.text.primary` | dark  | (direct) | `#F5F5F5` | resolved |
| `color.notification.warning.bg` | light | (direct) | `#FFF4D6` | resolved |
| `color.notification.warning.bg` | dark  | (direct) | `#332100` | resolved |
| `color.notification.warning.fg` | light | `color.notification.warning.fg → color.semantic.warning.text.light` | `#7A4A00` | resolved |
| `color.notification.warning.fg` | **dark** | `color.notification.warning.fg → color.semantic.warning.text.dark` → **MISSING** | -- | **UNRESOLVED** |

Alias-chain caveat (Step 8): `color.semantic.warning.text` defines only the `light` key; the `dark` key is absent. The alias chain for `color.notification.warning.fg.dark` therefore terminates at a missing definition. Per Step 2 contract, this token is reported as `UNRESOLVED` rather than guessed. The persona will NOT substitute `#F5F5F5`, the light-theme value `#7A4A00`, or any computed dark-theme inversion; the missing token is a human decision.

---

## 2. Pairwise contrast matrix (Step 5)

| theme | foreground_token | background_token | design_context | ratio | AA_threshold | AAA_threshold | verdict |
|---|---|---|---|---|---|---|---|
| light | `color.text.primary` (`#222222`) | `color.surface.background` (`#FFFFFF`) | normal-text | 15.90:1 | 4.5:1 | 7.0:1 | **PASS-AAA** |
| dark  | `color.text.primary` (`#F5F5F5`) | `color.surface.background` (`#0F1115`) | normal-text | 16.50:1 | 4.5:1 | 7.0:1 | **PASS-AAA** |
| light | `color.notification.warning.fg` (`#7A4A00` via alias) | `color.notification.warning.bg` (`#FFF4D6`) | normal-text | 6.30:1 | 4.5:1 | 7.0:1 | **PASS-AA** |
| dark  | `color.notification.warning.fg` (alias → `color.semantic.warning.text.dark` **missing**) | `color.notification.warning.bg` (`#332100`) | normal-text | -- | 4.5:1 | 7.0:1 | **UNRESOLVED** |

### Summary count
- Total pairs audited: **4**
- PASS-AAA: **2**
- PASS-AA: **1**
- FAIL-AA: **0**
- UNRESOLVED: **1**

---

## 3. Failing / unresolved pair list with remediation (Step 6)

### Pair 4 -- `color.notification.warning.fg` on `color.notification.warning.bg` (dark) -- UNRESOLVED

**Root cause:** alias chain breaks in dark theme. `color.notification.warning.fg.dark` aliases `color.semantic.warning.text`, but `color.semantic.warning.text` is defined only for `light`. No dark-theme value exists at the end of the chain.

**Remediation (does NOT guess a hex value):** the missing definition is a design decision, not an arithmetic one. The persona surfaces three policy-shaped options for the token owner to choose from; each is an actionable token delta, not a vague "fix contrast". The persona refuses to pick one because the choice has semantic consequences beyond this single pair (every consumer of `color.semantic.warning.text` in dark theme is affected).

1. **Define `color.semantic.warning.text.dark` explicitly** in the token source. The owner must supply a hex value whose contrast vs `#332100` (the dark warning background) clears the strictest applicable threshold for this token's consumers. The persona requires the value to be re-audited (re-run this command) once chosen; no value is assumed here.
2. **Add a dark override on `color.notification.warning.fg.dark`** that bypasses the broken alias and points to a concrete hex (or to a different already-defined dark-theme token, e.g. `color.text.primary.dark` `#F5F5F5` which yields ~12.4:1 on `#332100` -- provided ONLY as a sanity reference for the owner's evaluation, not as a recommended value; the semantic mismatch between "warning text" and "primary text" is a separate decision).
3. **Document `color.semantic.warning.text` as light-only** and refactor every consumer to provide its own dark-theme value directly. This is the most invasive option and should only be chosen if the team concludes the `semantic.warning.text` abstraction does not survive dark theme.

**What the persona will NOT do:** invent a dark hex by darkening/lightening `#7A4A00`, mirror it against the light background relationship, or pick option 2's `#F5F5F5` as the answer. All three would manufacture false confidence; per Step 2 the pair stays `UNRESOLVED` until the owner decides.

---

## 4. PROPOSED block -- `DECISIONS.md ## Locked decisions`

```markdown
### D-N (PROPOSED) -- Contrast policy: WCAG 2.2 AA floor; warning-text dark-theme value unblocked by token decision

- **Target level:** WCAG 2.2 AA across light and dark themes for every documented foreground/background pair. AAA is not required but is recorded where achieved (currently `color.text.primary` on `color.surface.background` in both themes).
- **Audited pairs (4):** `color.text.primary` × `color.surface.background` (both themes, both PASS-AAA); `color.notification.warning.fg` × `color.notification.warning.bg` (light PASS-AA at 6.30:1; dark UNRESOLVED -- see risk R-N below).
- **Deferred / unresolved:** dark-theme warning text pair deferred pending definition of `color.semantic.warning.text.dark` OR an explicit override on `color.notification.warning.fg.dark`. Not deferred as "acceptable debt"; deferred as "blocks dark-theme notification UI work until resolved".
- **Context reclassifications:** none. Both documented pairs serve as `normal-text` per input.
- **Re-audit trigger:** any change to `color.semantic.warning.text`, `color.notification.warning.fg`, or `color.notification.warning.bg` in either theme requires re-running `color-contrast-architect` before the change locks.
```

---

## 5. PROPOSED block -- `IMPLEMENTATION_PLAN.md ## Risks and mitigations`

```markdown
### R-N (PROPOSED) -- Dark-theme warning text: broken alias chain blocks downstream dark-theme notification slices

- **Risk:** `color.notification.warning.fg` cannot resolve in dark theme because its alias `color.semantic.warning.text` has no `dark` entry. Any slice that ships a dark-theme warning notification will either crash at token resolution time, fall back to a runtime default that has not been contrast-audited, or silently render an undefined color. Contrast cannot be measured until the token resolves.
- **Affected scope:** every component, screen, and slice that consumes `color.notification.warning.fg` in dark theme (notifications, banners, toasts, inline form warnings, any composite that pulls from `color.semantic.warning.text`).
- **Mitigation (sequencing):** block dark-theme notification slices behind a token-level fix (one of the three remediation options in `CONTRAST_AUDIT.md ## 3`). Owner: token / foundations owner. Once the missing value is chosen, re-run `color-contrast-architect` on the updated pair and promote the result.
- **Mitigation (interim):** if a slice MUST ship before the token decision lands, scope it to light theme only and gate dark-theme rendering behind a feature flag that explicitly refuses to render the warning until the token resolves. No "best guess" hex in component code.
- **Owner:** unassigned -- surface to `decision-interview` for the token-policy decision and `implementation-plan` for the slice gate.
```

---

### Command transcript

1. Read `commands/color-contrast-architect/SKILL.md`; ran Steps 1–8 against the supplied token excerpt (2 documented pairs × `light`+`dark` = 4 rows).
2. Step 2 flagged `color.notification.warning.fg.dark` as UNRESOLVED: alias chain terminates at `color.semantic.warning.text.dark` which is not defined. Per persona contract, no value substituted.
3. Step 3–5 used supplied ratios (15.9, 16.5, 6.3); matrix emitted with one row per pair; summary count 2 PASS-AAA / 1 PASS-AA / 0 FAIL-AA / 1 UNRESOLVED.
4. Steps 6–7 produced one remediation (three policy options, none guessed), one PROPOSED `DECISIONS.md` block, one PROPOSED `IMPLEMENTATION_PLAN.md` risk; Step 8 caveat recorded on alias chain crossing theme boundaries.

---

### Handoff

**Verdict:** audit complete; 3 of 4 pairs pass (2 AAA, 1 AA); 1 pair UNRESOLVED on a missing dark-theme token, not a contrast failure. Cannot lock contrast policy or unblock dark-theme notification work until the token owner resolves `color.semantic.warning.text.dark`.

**Run now:** `decision-interview`
**Why:** the UNRESOLVED row is decision-shaped, not factual. The token owner must choose between (1) defining `color.semantic.warning.text.dark` explicitly, (2) overriding `color.notification.warning.fg.dark` to bypass the alias, or (3) refactoring `color.semantic.warning.text` to light-only. Each option has downstream consequences that exceed this one pair, so the choice belongs in `DECISIONS.md`, not in a guessed hex.

**After decision lands:** re-run `color-contrast-architect` on the updated `color.notification.warning.fg` × `color.notification.warning.bg` (dark) pair to confirm WCAG 2.2 AA (>= 4.5:1 for normal-text). Then route to `implementation-plan` to lift the dark-theme notification slice gate proposed in R-N.

**Do NOT run:** `screen-spec` or `component-spec` against any dark-theme surface that consumes `color.notification.warning.fg` until the token resolves; doing so would manufacture false confidence on an UNRESOLVED pair.
