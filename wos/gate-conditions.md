---
activation: model_decision
description: Six phase-gate checklists. Load when validating command output shape against a phase gate.
---

# Gate conditions

Transition checks for phase boundaries. If a command choice is ambiguous, resolve against `## Command roles` first.

## Before planning
Only move into planning if:
- the task is understood well enough
- boundaries are known well enough
- correctness-critical ambiguity is reduced enough

## Before implementation
Only move into implementation if:
- a valid `IMPLEMENTATION_PLAN.md` exists
- the slice is explicit and approved
- correctness-critical ambiguity is already resolved
- files in scope are known
- the next step is a real code change

## Before slice closure
Only close a slice if:
- the approved slice goal was achieved
- slice-level validation is sufficient
- remaining issues are follow-ups, not blockers inside the slice
- the slice is not being confused with full task completion

## Verification layering (the three-layer quality gate)
Order the verification effort cheapest-first. Each layer must pass and be shown before the next runs; the existing no-op rules still let a layer be skipped when it genuinely adds no signal, but never silently.

- Layer 1, deterministic checks: typecheck, lint, and the relevant tests pass, with the actual command and its real output shown (per `implement-approved-slice`). A passing deterministic gate (for example a Stop or PostToolUse hook in the consuming repo) satisfies this layer.
- Layer 2, AI risk review: `review-hard` and `repo-consistency-sweep` (and `security-review` when there is a security surface) run only after Layer 1 is green.
- Layer 3, human approval: the maintainer reviews and approves before merge.

If Layer 1 fails, do not run Layer 2. If a layer is intentionally skipped as no-signal, say so.

### Interactive bounded retry (deterministic gate on a normal turn)
A deterministic gate can hold a normal interactive turn until it passes (re-check after each turn), not only an autonomous run. When it does, it MUST carry a bounded retry cap and an escalate-on-N-fails rule, exactly as the autonomous-run governor enforces (`wos/autonomous-track.md` D11): cap consecutive blocked retries at a small N (default 3 to 8) and, on reaching the cap, STOP and escalate to the human rather than looping. A hold-until-pass note without the bounded cap reintroduces the infinite-retry loop the governor exists to prevent. The cap belongs in the hook itself (see `templates/deterministic-gate-hook.template.md`). Each retry attempt MUST restate the concrete validation failure text verbatim (never a generic "gate failed"), because that failure text is the payload the retry reasons over.

## Before PR packaging
Only prepare a PR if:
- the base branch is explicit
- the diff is stable
- the relevant task scope is complete enough
- major blockers are resolved
- the task is actually near delivery
- no external-vendor contract point on a security-critical or fully-gating path (auth, payment, PII, delivery mechanism) is riding into the PR body as an ordinary accepted-trade-off note while still unconfirmed against the vendor's real behavior (ADR-0108). Such a point is either already live-verified, or it is a structurally distinct, named blocker (not folded into a flat notes list), not silently packaged alongside genuine judgment calls.

## After PR review feedback (corrective)
Only drive narrow follow-up implementation if:
- material feedback is mapped to paths or slices and tagged for severity
- conflicts with `DECISIONS.md` are escalated (`decision-interview`, `post-review-pivot`) rather than "fixed" by reinterpretation
- if feedback changes product or contract direction, run `post-review-pivot` (and replan) before treating items as incremental fixes

## Before moving a task to done
Only move a task to `done` if:
- review is complete
- team approval is complete
- merge into the target branch happened
- final task state was recorded
