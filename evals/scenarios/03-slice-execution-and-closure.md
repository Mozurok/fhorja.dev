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

## Input prompt (turn 1: implement-approved-slice for slice 01)

```text
Run @commands/implement-approved-slice.md

Active task: projects/acme__widget-pricing/active/2026-05-08_initial-price-query/
Slice: Slice 01 (wire the read handler)
Mode: Agent
Product workspace: ~/code/widget-pricing-api
```

## Input prompt (turn 2: slice-closure, after reviewing turn 1)

```text
Run @commands/slice-closure.md

Active task: projects/acme__widget-pricing/active/2026-05-08_initial-price-query/
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
3. **Turn 1 - Handoff**: `Run now:` is `slice-closure` or `review-hard`; Mode B `Resume context:` includes the task path.
4. **Turn 2 - closure decision**: response makes an explicit close-or-not call, not a non-committal "looks good".
5. **Turn 2 - exit criteria check**: response references the slice 01 exit criteria (both tests, lint, PR draft) and grounds the closure decision in them.
6. **Turn 2 - routing on gap**: if a gap exists, the recommended next step is `implement-slice-complement` (not `implement-approved-slice` or `pr-package`).
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
