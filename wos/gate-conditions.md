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

### A closure floor needs two homes, or it does not exist

`implement-approved-slice` closes a LOW or MEDIUM slice INLINE and explicitly does not route to `slice-closure`; only a HIGH-complexity slice, or one whose exit criteria cannot be verified inline, reaches that command. So a floor written only into `slice-closure.md` never fires on the majority of slices, and it fires least on the ones a plan judged routine, which is where an unreviewed defect travels furthest.

Every generalized floor therefore ships as a pair: each floor in `wos/closure-floors.md` (ADR-0134)
carries a `slice-closure` variant and an `implement-approved-slice (inline-close)` variant, and each
command loads the generated view that `scripts/build-closure-floor-views.py` builds for it. `commit-evidence`, `experience-verdict`,
`entry-path probe`, `eval-threshold`, `integrity`, `Layer-2 review`, and `rollout-constraint reconcile` all follow
this shape, and the `task-close` variant carries the whole-task backstop for several of them.

Each home carries the floor's OWN declared behavior, read from its `On missing evidence:` line, not a
single verdict shared across floors. A floor declaring `refuse` produces `not ready to close` at the
slice-closure home and `do NOT inline-close` at the inline one. A floor declaring `record` writes
`unverified: <reason>` at both and closure proceeds; a floor declaring `reconcile` records a named
deferral at both. This paragraph named the two refuse verdicts for every floor in the list until
2026-09-16, which was true when ADR-0203 was written and stopped being true the moment it landed:
every floor named above declares `record` or `reconcile` except `commit-evidence` and `integrity`, which declare `refuse`.

When adding a floor, write both halves and keep the escape clause identical, or state in the floor
itself why one home is deliberately enough.

This is a live failure mode, not a hypothetical: the 2026-07-29 mobile dogfood proposed the Layer-2 review floor for `slice-closure.md` alone, and the plan that motivated it had 5 LOW and 3 MEDIUM slices with zero HIGH, so the floor would have been unreachable on the exact run that produced it.

### The attester-removed test

A floor's criterion names a fact, and someone attests that fact. In most floors the two are separable; in a few they are not, and which kind a floor is decides whether the attester can ever change. The test that settles it:

> Write the gate's criterion with whoever satisfies it erased.
> If a checkable fact about an artifact or an execution survives, the criterion is core and the attester is track-level.
> If the criterion evaporates or becomes a tautology, it names its attester from the inside. It is core in full, attester included, and never changes track.

What survives the erasure puts the floor in exactly one of three classes:

- `agnostic`: the surviving fact is checkable from the artifact itself with ordinary tooling, meaning a checkout and a shell. Having to RUN something to produce it does not move a floor out of this class WHERE the thing run ships in the repository: a script that exits 0 and a test suite in the tree are both ordinary tooling. A run that needs something the checkout cannot supply is not ordinary tooling and belongs to the next class. Nothing in the criterion constrains who attests it.
- `environment-bound`: the surviving fact needs a runtime a checkout cannot supply (a device, an emulator, a running app or scene, a model endpoint). Whoever holds that runtime can attest and whoever lacks it cannot, which cuts the same way for a person without the device as for a runner without it.
- `human-bound`: the criterion does not survive the erasure. It names human perception from the inside, and machine-green evidence never substitutes for it.

Each floor declares its class ONCE, in its own section in `wos/closure-floors.md` or `wos/platform-runtime-floors.md`, on a line of exactly this form:

    Attester class: <agnostic | environment-bound | human-bound>

That line starts at COLUMN ZERO and carries no emphasis markers, because a machine reads it. It is indented above only so this page renders it as a sample; a copy that keeps the indentation is not a declaration. No leading whitespace is tolerated here, deliberately unlike the `wos-godot-declaration` block, which strips up to three spaces so it can sit under a numbered step: this line has no such host and buys the stricter grammar instead. The per-home variants do not repeat it: the two-homes rule above governs where a floor's enforcement lives, and this rule governs where its class is written. Each floor also carries the criterion restated with the attester erased, on the line above its class, so a reader can check the classification against the thing it was derived from instead of taking it on trust.

## Verification layering (the three-layer quality gate)
Order the verification effort cheapest-first. Each layer must pass and be shown before the next runs; the existing no-op rules still let a layer be skipped when it genuinely adds no signal, but never silently.

- Layer 1, deterministic checks: typecheck, lint, and the relevant tests pass, with the actual command and its real output shown (per `implement-approved-slice`). A passing deterministic gate (for example a Stop or PostToolUse hook in the consuming repo) satisfies this layer.
- Layer 2, AI risk review: `review-hard` and `repo-consistency-sweep` (and `security-review` when there is a security surface) run only after Layer 1 is green.
- Layer 3, human approval: the maintainer reviews and approves before merge.

A verdict from `verify-against-rubric` is a Layer 2 signal, never Layer 1 evidence: it is a model's judgment of an artifact, and Layer 1 accepts only a deterministic check with its real output shown.

If Layer 1 fails, do not run Layer 2. If a layer is intentionally skipped as no-signal, say so.

### Interactive bounded retry (deterministic gate on a normal turn)
A deterministic gate can hold a normal interactive turn until it passes (re-check after each turn), not only an autonomous run. When it does, it MUST carry a bounded retry cap, exactly as the autonomous-run governor enforces (`wos/autonomous-track.md` D11): cap consecutive blocked retries at a small N (default 3 to 8) and, on reaching the cap, record the failure with the evidence already captured and route the fix rather than repeating the same run. The cap records and proceeds; it does not request human input (ADR-0201). A hold-until-pass note without the bounded cap reintroduces the infinite-retry loop the governor exists to prevent. The cap belongs in the hook itself (see `templates/deterministic-gate-hook.template.md`). Each retry attempt MUST restate the concrete validation failure text verbatim (never a generic "gate failed"), because that failure text is the payload the retry reasons over.

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
