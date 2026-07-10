# Eval scenario 68: a11y-audit (whole-surface WCAG conformance ledger)

- **Tags**: a11y-audit, wcag-2.2, accessibility, conformance-ledger, machine-vs-manual, contrast-delegation, surface-type, planning-and-validation, wave-1-capability-expansion
- **Last reviewed**: 2026-06-24
- **Status**: active

## Goal
Verify that the a11y-audit persona produces a whole-surface WCAG 2.2 conformance ledger at a named level rather than an ad hoc spot-check, and that its load-bearing guardrails hold:
- Every applicable success criterion for the named level gets a row; none is silently omitted.
- Each row is labeled `machine` | `manual` | `delegated` | `n/a`; no machine verdict is asserted for a manual-judgment criterion.
- Contrast (1.4.3 and 1.4.11) is delegated to color-contrast-architect, never recomputed.
- When no checker tool report is supplied, machine-checkable rows are `MANUAL-REVIEW`, never a guessed PASS or FAIL.
- Surface type is labeled and honored (web ARIA and DOM vs native accessibility API); no DOM assumption on a native surface.
- A no-UI-surface task returns a SKIP/NO_OP verdict, not an empty ledger.

## Setup
An active task with a SOURCE_OF_TRUTH.md naming a React Native (native-mobile) screen as the surface in scope, an AA target, and no checker tool report attached. A sibling task in the same project has a docs-only change with no UI surface.

## Input prompt (turn 1: audit a native screen, no checker report)
"Run a11y-audit on the Checkout screen. Target AA. No axe/Lighthouse run yet."

## Input prompt (turn 2: a docs-only task)
"Run a11y-audit on this task (the README copy edit)."

## Expected response shape (turn 1: native screen, no checker)
- Produces `<task>/ACCESSIBILITY_AUDIT.md` with one row per applicable WCAG 2.2 AA criterion plus a summary count; no criterion silently dropped (non-applicable ones are `N/A` with a one-line reason).
- Labels the surface type `native-mobile` and references the platform accessibility API (`accessibilityRole`, `accessibilityLabel`), NOT the DOM or ARIA, for native criteria.
- Marks machine-checkable criteria `MANUAL-REVIEW` because no checker report was supplied; does not emit a guessed PASS or FAIL.
- Lists 1.4.3 and 1.4.11 as `delegated` rows, citing CONTRAST_AUDIT.md when present or routing to color-contrast-architect when absent; does not recompute contrast.
- Every FAIL row (if any from evidence in the provided files) carries a concrete remediation (e.g. add an `accessibilityLabel` to the icon button at file:line); none reads "fix it".
- Stages a PROPOSED block for the conformance target/scope under DECISIONS.md and routes via Handoff (no direct substrate write at L1).
- Routes Handoff to color-contrast-architect (contrast pending) or implementation-plan (slice remediation).

## Expected response shape (turn 2: docs-only task)
- Returns a SKIP/NO_OP verdict ("no UI surface in scope"), routing to decision-interview; does NOT manufacture an empty or all-N/A ledger.

## What a FAIL looks like
- The ledger covers only a handful of "obvious" criteria (alt text, contrast) and omits the rest of the AA set (the spot-check failure this persona exists to prevent).
- A machine PASS/FAIL is asserted for a manual-judgment criterion, or for any criterion when no checker ran.
- Contrast is recomputed inline instead of delegated to color-contrast-architect.
- The native screen is audited against DOM/ARIA assumptions.
- The docs-only task gets a fabricated empty ledger instead of a SKIP/NO_OP.
