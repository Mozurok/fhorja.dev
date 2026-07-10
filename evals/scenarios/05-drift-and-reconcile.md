# Eval scenario 05: Drift detection and state-reconcile

- **Tags**: state-reconcile, drift-detection, minimum-patch, no-op
- **Last reviewed**: 2026-05-08
- **Status**: active

## Goal

Validates that `state-reconcile` correctly detects material drift between `TASK_STATE.md` and other task artifacts, proposes the **minimum** set of updates (not a full rewrite), and routes forward appropriately. Also validates the no-op behavior when no material drift exists.

This exercises:

- The "material change" definition (spec `## Cross-cutting workflow guardrails` → `### Material change (definition)`).
- The minimum-patch principle in `state-reconcile`.
- The NO_OP semantics (ADR-0003).
- The distinction between `sync-task-state` (small incremental updates) and `state-reconcile` (cross-artifact drift detection).

## Setup

Assume an active task at `projects/acme__widget-pricing/active/2026-05-08_initial-price-query/` with the following deliberate inconsistencies (paste these into your AI tool's context).

`TASK_STATE.md` (deliberately stale; says current phase is `planning` but plan is already approved and one slice is implemented):

```text
# TASK_STATE

## Task summary
Implement GET /v1/prices/:customer_id endpoint.

## Current phase
planning

## Objective
GET /v1/prices/:customer_id returns the customer's effective price list, with 404 for customers with no prices.

## Source of truth
- IMPLEMENTATION_PLAN.md
- DECISIONS.md
- src/handlers/prices.ts (newly added)

## Current known facts
- prices_view exists in the DB and returns rows by customer_id.
- The handler is a thin wrapper over the view.

## Canonical decisions
- (see DECISIONS.md)

## Open questions / blockers
- None.

## Last completed step
- Command: implementation-plan
- Mode: Plan
- Summary: Wrote slice 01 plan; awaiting execution.

## Current status
### Completed
- (none yet)

### In progress
- Slice 01 planning

### Not started
- Slice 01 execution

## Active files in scope
- src/handlers/prices.ts
- src/routes.ts
- tests/handlers/prices.spec.ts

## Constraints / things that must not change
- prices_view definition.

## Risks to watch
- 404 handling per D-1.

## Recommended next step
- Command: implement-approved-slice
- Mode: Agent
- Why: slice 01 is approved and ready.

## Work complexity (for next execution step)
LOW

## Resume notes
Plan was just signed off. Resume with implement-approved-slice for slice 01.

## Task scope level
full task

## Current closure target
Slice 01 delivery.
```

`IMPLEMENTATION_PLAN.md` (slice 01 marked completed; subsequent slices are placeholders):

```text
# IMPLEMENTATION_PLAN

## Slice 01: wire the read handler [COMPLETED 2026-05-08]
- Objective: Implement GET /v1/prices/:customer_id as a thin handler over the existing prices_view.
- Scope: src/handlers/prices.ts (new), src/routes.ts (1 new route registration), tests/handlers/prices.spec.ts (new).
- Exit criteria: both tests pass on a feature branch; no lint errors.
- Delivered 2026-05-08: handler created; route registered; both tests green; lint clean. Slice closed.

## Slice 02: PLACEHOLDER (admin price-override endpoint, future phase)
```

`SLICES/01_wire-read-handler.md`:

```text
# Slice 01: wire the read handler

Status: CLOSED 2026-05-08

## Files touched
- src/handlers/prices.ts (new, 28 lines)
- src/routes.ts (+2 lines: import + route registration)
- tests/handlers/prices.spec.ts (new, 42 lines)

## Validation
- vitest: 2 / 2 tests pass.
- pnpm lint: 0 errors.

## Next
Closure decided. Recommended next: pr-package (the task is essentially complete after slice 01).
```

The drift: `TASK_STATE.md` says `## Current phase: planning`, `## Last completed step: implementation-plan`, `## In progress: Slice 01 planning`, `## Not started: Slice 01 execution`, but the plan and slice notes both say slice 01 is **closed and delivered**. The recommended next step in `TASK_STATE.md` is `implement-approved-slice` even though that work is done.

## Input prompt

```text
Run @commands/state-reconcile.md

Active task: projects/acme__widget-pricing/active/2026-05-08_initial-price-query/
Mode: Ask

I noticed TASK_STATE.md disagrees with IMPLEMENTATION_PLAN.md and SLICES/01_wire-read-handler.md after the slice was closed. Want a clean reconcile pass.
```

## Expected response shape

- Response begins with state-reconcile's persona line.
- Response identifies the specific drifted fields in `TASK_STATE.md`: at minimum `## Current phase`, `## Last completed step`, `## Current status` (Completed / In progress / Not started), `## Recommended next step`. The response calls these out explicitly, not vaguely as "TASK_STATE is stale".
- `### Artifact changes` proposes a `TASK_STATE.md` patch that updates exactly those drifted fields. It does NOT rewrite the entire file.
- The patch updates `## Current phase` to `delivery` (or `review` if reviewing the slice further) - not to `planning`, not to `implementation`.
- The patch updates `## Last completed step` to `slice-closure` (or `implement-approved-slice` followed by `slice-closure`).
- The patch updates `## Current status` to move slice 01 from `In progress` / `Not started` to `Completed`.
- The patch updates `## Recommended next step` to `pr-package` (per the slice notes' recommendation), not `implement-approved-slice`.
- The patch does NOT touch `IMPLEMENTATION_PLAN.md` or `SLICES/01_wire-read-handler.md` (those were the source of truth; reconcile patches the stale artifact, not the fresh ones).
- `### Handoff` block at the end. `Run now:` is `pr-package` (the new recommended next step). Mode B `Resume context:` includes the active task path and the base branch input that `pr-package` requires.

## Pass criteria

1. **Drift identified specifically**: response names the drifted fields by their `## Section name` headers, not vaguely as "the file is stale".
2. **Minimum patch**: `### Artifact changes` proposes ONLY changes to the drifted fields in `TASK_STATE.md`. It does not propose rewriting unchanged sections (Source of truth, Active files in scope, Constraints, etc.) for stylistic improvement.
3. **Correct phase**: new `## Current phase` is `delivery` or `review` (not `planning`, not `implementation` - slice 01 is closed; the task is in delivery prep).
4. **Correct last completed step**: new `## Last completed step` reflects slice closure, not implementation-plan.
5. **Status accuracy**: slice 01 moves to `Completed`. `In progress` / `Not started` adjusted accordingly (probably empty if no slice 02 is in flight).
6. **Routing forward**: new `## Recommended next step` is `pr-package` (per the slice notes), not a re-recommendation of work that is already done.
7. **Handoff intact**: response ends with a complete Handoff. `Run now:` is `pr-package`; adaptive handoff block has the task path and the `Base branch:` input that `pr-package` requires.
8. **No source-of-truth disruption**: `IMPLEMENTATION_PLAN.md` and `SLICES/01_wire-read-handler.md` are NOT in `### Artifact changes`. They are the source of truth that surfaced the drift; reconcile patches the stale artifact.

## Failure modes to watch

- **Full rewrite**: response proposes rewriting `TASK_STATE.md` entirely "to clean it up". Minimum-patch is the principle; rewrites are wasteful and noisy in `git diff`.
- **Wrong direction**: response patches `IMPLEMENTATION_PLAN.md` or `SLICES/01_wire-read-handler.md` to match the stale `TASK_STATE.md`. The fresher artifacts are the source of truth; reconcile goes the other way.
- **Phase ambiguity**: response sets `## Current phase` to `implementation` even though slice 01 is closed. Phase should advance to `delivery` (or `review` if a `review-hard` step is desired before delivery).
- **Wrong next step**: response recommends `implement-approved-slice` again, not noticing the slice is already closed.
- **Vague drift report**: response says "there is some drift" without naming which fields. The user has to read both files themselves to understand what to fix.
- **Routing to sync-task-state**: response defers to `sync-task-state` for the patch ("you should run sync-task-state next"). For cross-artifact drift, `state-reconcile` IS the right command; routing forward to `sync-task-state` would be regressing the routing distinction.

## Notes

- Related ADRs: [ADR-0003](../../docs/adr/0003-no-op-semantics.md) (no-op semantics; this scenario does NOT exercise the no-op path because the drift is real and material; a follow-up scenario would test the no-op path against a clean task).
- Related commands: `commands/state-reconcile.md`, `commands/sync-task-state.md` (distinct: sync is incremental; reconcile is cross-artifact).
- The drift in this scenario is the canonical "after-many-edits" case the spec's multi-edit lazy file describes. Real tasks accumulate this drift slowly; the eval surfaces it deliberately.

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.
