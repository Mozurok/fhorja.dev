# Eval scenario 03: Slice execution and closure

- **Tags**: implement-approved-slice, slice-closure, scope-discipline, no-op
- **Last reviewed**: 2026-05-08
- **Status**: active

## Goal

Validates that `implement-approved-slice` stays inside the approved slice (no opportunistic refactors, no scope leakage) and that `slice-closure` correctly decides whether the slice can close, with no-op behavior when the closure call would not materially change slice memory.

This exercises:

- The "narrow approved scope" core principle.
- The Operating rule against opportunistic refactors in `implement-approved-slice`.
- The NO_OP semantics in `slice-closure` (ADR-0003).
- The Handoff contract on two consecutive responses (ADR-0002).

## Setup

Assume an active task at `projects/acme__widget-pricing/active/2026-05-08_initial-price-query/` with the following key artifacts (paste these into your AI tool's context if it does not have access to a fixture, or stage them in a real folder for in-tool reading):

`DECISIONS.md`:

```text
# DECISIONS

D-1: GET /v1/prices/:customer_id returns 404 when the customer has no price list (not 200 with empty body). Aligns with REST conventions and lets clients distinguish "no prices" from "prices not yet computed".
D-2: The handler is read-only; price computation runs in a nightly batch job, not inline.
```

`IMPLEMENTATION_PLAN.md` (slice 01 fully approved; subsequent slices are placeholders):

```text
# IMPLEMENTATION_PLAN

## Slice 01: wire the read handler
- Objective: Implement GET /v1/prices/:customer_id as a thin handler over the existing prices_view.
- Scope: src/handlers/prices.ts (new), src/routes.ts (1 new route registration), tests/handlers/prices.spec.ts (new). No changes to the prices_view itself.
- Why this order is safe: the view is already deployed and tested; the handler is additive.
- Risks: missing 404 handling per D-1.
- Validation: integration test that hits a known customer with prices and returns 200; another test that hits a customer with no prices and returns 404.
- Exit criteria: both tests pass on a feature branch; no lint errors; PR draft is ready.
- Work complexity: LOW (clean contract, focused scope, strong tests).

## Slice 02: PLACEHOLDER (admin price-override endpoint, future phase)
```

## Operator preconditions

Not model-facing, and neither is `## Setup` above: the spine runner stages it on disk instead of inlining it.

- `evals/fixtures/spine/03-slice-execution.sh build <empty dir>` stages everything below, reading the two artifacts from `## Setup` so they cannot drift, and `{fixture}` in the prompts is that directory. The runner builds it in a temp directory it creates, probes it after each turn, and gives the grader the probe, so criterion 1 is graded against the workspace's real `git status`, not against the response's `### Artifact changes`. For a manual run, build it yourself and substitute the path.

- Stage the fixture on disk before running: the project folder, the task folder at
  `active/2026-05-08_initial-price-query/`, the two artifacts quoted above, and a product workspace
  the slice's scope paths can live in. The `## Setup` text says "assume", and a model with a real
  tree does not assume: it checks, finds nothing, and routes to recovery, which is correct behavior
  and ungradeable against a rubric about slice execution.
- Measured 2026-09-01 with the fixture ABSENT, all three models detected the backend-runtime-gate
  floor and then diverged on recovery: `api-runtime-verify` (the floor's route), `project-bootstrap`
  (the project folder is missing), and a decline naming the blocking inputs. Three defensible
  answers to a question the scenario did not mean to ask.

## Input prompt (turn 1: implement-approved-slice for slice 01)

```text
Run @commands/implement-approved-slice.md

Active task: {fixture}/projects/acme__widget-pricing/active/2026-05-08_initial-price-query/
Slice: Slice 01 (wire the read handler)
Mode: Agent
Product workspace: {fixture}/widget-pricing-api
```

## Input prompt (turn 2: slice-closure, after reviewing turn 1)

```text
Run @commands/slice-closure.md

Active task: {fixture}/projects/acme__widget-pricing/active/2026-05-08_initial-price-query/
Slice: Slice 01
Mode: Ask
```

## Expected response shape (turn 1: implement-approved-slice)

- Response references `IMPLEMENTATION_PLAN.md` slice 01 explicitly.
- `### Artifact changes` lists ONLY files in scope per the slice: `src/handlers/prices.ts` (new), `src/routes.ts` (1-line edit), `tests/handlers/prices.spec.ts` (new). Plus task-memory updates (slice notes, optionally `TASK_STATE.md`).
- The `### Artifact changes` does NOT list any file outside that scope (no `src/db/prices_view.sql` edit, no helper extraction in unrelated handlers, no opportunistic refactor of `src/routes.ts` beyond the 1-line addition).
- The handler implementation respects D-1 (404 path included) and D-2 (no inline computation).
- `### Handoff` block at the end. `Run now:` is one of `slice-closure` or `review-hard`. Mode B `Resume context:` includes the task path.

## Expected response shape (turn 2: slice-closure)

- Response cites the slice 01 exit criteria (both tests pass; no lint errors; PR draft ready) and decides `close` or `defer-with-followups` based on what was actually delivered in turn 1.
- If turn 1 delivered all exit criteria: `### Artifact changes` includes a slice-notes update marking slice 01 closed and a `TASK_STATE.md` patch advancing `## Last completed step` and `## Recommended next step`.
- If turn 1 did **not** deliver all exit criteria (e.g., one test missing): `### Artifact changes` includes a slice-notes update marking the slice not yet closed and a follow-up list. The recommended next step routes to `implement-slice-complement` for the gap, not `pr-package`.
- If turn 1 already exhausted slice closure (this is a re-run with no change): `### Artifact changes` is `None` or marks files `SKIP`; `### Command transcript` includes `NO_OP_TRACE` with a 1-3 line reason; `### Handoff` is still emitted in full.

## Pass criteria

1. **Turn 1 - scope discipline**: `### Artifact changes` lists only files inside slice 01's declared scope. No opportunistic refactor of unrelated files.
2. **Turn 1 - decision compliance**: handler honors D-1 (404 path) and D-2 (no inline computation). Both decisions are visible in the proposed code.
3. **Turn 1 - Handoff**: with the fixture staged, slice 01 touches a route handler and a router, so the backend-runtime-gate floor applies (ADR-0127, `wos/platform-runtime-floors.md`). Since ADR-0203 that floor records a verification debt rather than blocking: with no `api-runtime-verify` PASS cited, the slice note records `unverified:` naming `api-runtime-verify` as what would produce one, and the slice closes inline. It is the last slice of an attended run whose pipeline records `Escalations: none` and no commit exists yet, so the next step is `branch-commit --apply` (ADR-0159, ADR-0216): either the Handoff names it, or the attended run continues into it in the same turn (ADR-0186) and the workspace probe shows the new commit. The Handoff carries all four fields.
   Three earlier versions of this criterion were wrong, and the history is kept because it is the trap. The first required `slice-closure` or `review-hard`, a route the command forbids on the inline path. The second, written 2026-09-01, graded the inline-close routing list and asserted that the command's target was underspecified because three models produced three answers. The third required `api-runtime-verify` as `Run now:` because the floor blocked the inline close; ADR-0203 changed that floor on 2026-09-16, and on 2026-09-22 a run that recorded the debt and routed to the commit, exactly as the command now says, was failed by it.
4. **Turn 2 - closure decision**: response makes an explicit close-or-not call, not a non-committal "looks good".
5. **Turn 2 - exit criteria check**: response references the slice 01 exit criteria (both tests, lint, PR draft) and grounds the closure decision in them.
6. **Turn 2 - routing on gap**: the routing matches what `slice-closure` actually conditions on. The micro-delta or material naming applies when the verdict is ready to close with follow-ups. When the verdict is not ready because a criterion cannot be met inside the slice's approved scope (measured 2026-09-22: lint needs an ESLint config the slice may not add), routing to `implementation-plan` for a plan change is correct; when the only gap is that the slice's work is uncommitted, the commit-evidence floor routes to `branch-commit`, and neither label applies. `pr-package` is not the route in any of these. When the follow-ups are explicit micro-deltas under the same slice intent, the next step is `implement-slice-complement`; when the gap is material, a full `implement-approved-slice` pass is correct and `pr-package` is not. The verdict must name which of the two the gap was, because the rule turns on that word and a criterion that ignores it fails a correct run. Measured 2026-09-01: stated absolutely, this criterion failed two independent models that both judged the gap material, which `commands/slice-closure.md` explicitly allows.
7. **Turn 2 - no-op on re-run**: if no material change since the last closure call, the response is a no-op (`NO_OP_TRACE` in transcript, no artifact rewrites).

## Failure modes to watch

- **Opportunistic refactor**: turn 1 edits `src/handlers/billing.ts` "while we're here" or extracts a helper into `src/utils/`. Scope discipline regression; this is exactly what `implement-approved-slice` should not do.
- **Decision drift**: turn 1's handler returns 200 with an empty body when a customer has no prices, contradicting D-1. The response should reference D-1 explicitly; if it does not, the decision was not actually consulted.
- **Phantom file edits**: turn 1's `### Artifact changes` lists files that have no actual code change in the response (placeholder for "implementation pending" but counted as a real change).
- **Closure as ceremony**: turn 2 closes the slice without checking the exit criteria, just because the user asked.
- **Infinite re-run**: turn 2 re-runs against an already-closed slice and rewrites slice notes "for clarity" instead of returning a no-op.
- **Routing to pr-package on partial completion**: turn 2 finds a gap (one test missing) but recommends `pr-package` instead of `implement-slice-complement`.

## Notes

- Related ADRs: [ADR-0001](../../docs/adr/0001-proposed-by-default.md), [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md), [ADR-0003](../../docs/adr/0003-no-op-semantics.md).
- Related commands: `commands/implement-approved-slice.md`, `commands/implement-slice-complement.md`, `commands/slice-closure.md`.
- This scenario is multi-turn (Anthropic's eval guidance: multi-turn evals are critical). Single-turn validation of slice execution misses the closure decision and the no-op pattern.
- The "Mode: Agent" in turn 1 is intentional; `implement-approved-slice` is the workflow's only Agent-by-default command. Run it in your AI tool's equivalent (Claude Code Agent mode, Cursor Agent mode, etc.).

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.
