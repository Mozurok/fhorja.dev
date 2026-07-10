# ADR-0061: Spec-ingest mode for implementation-plan (--spec)

- **Status**: Accepted
- **Date**: 2026-06-27
- **Tags**: implementation-plan, spec-ingest, prd, deliverable-coverage, slicing, no-silent-omission, ecosystem-adoption, additive

## Context

The 2026-06-26 ecosystem research (Taskmaster `parse-prd`, round 1 rank 9 / round 2 rank 4) flagged that the WOS has no path from a written spec, PRD, or requirements document to a sliced plan. A user pastes a spec into a free-form task description, and the named items can silently drop during planning. ADR-0056 already makes user-named deliverables a tracked invariant from intake to closure; a spec is a dense source of exactly those deliverables, so the coverage machinery exists but nothing feeds the spec into it.

Two shapes were considered: a new `spec-ingest` command, or a mode of the existing `implementation-plan`. The round-4 decision (D-13) chose the mode: the only thing that differs from normal planning is the SOURCE of the slices (a spec versus a free-form description); the slice format, the approval gate, and the substrate ownership are all unchanged.

## Decision

Add a `--spec <path>` mode to `implementation-plan` (not a new command). When the caller passes `--spec <path>` to a spec, PRD, or requirements document:

1. Enumerate every named feature, requirement, or acceptance item as a discrete `spec item`, keeping the spec's own wording as the label so coverage stays auditable.
2. Map each spec item to one or more slices. The mapping is many-to-many but total: every spec item must trace to at least one slice ID.
3. Run the ADR-0056 deliverable-coverage check: seed or extend the `## Requested deliverables` ledger in `TASK_STATE.md` with one row per spec item, then assert each row maps to a slice. An uncovered item surfaces as a `[NEEDS CLARIFICATION: spec item "<label>" maps to no slice -- in scope?]` marker rather than being dropped; an explicit de-scope needs a `DECISIONS.md` entry.
4. Emit a `## Spec coverage` table (`spec item -> slice id(s)`) in `IMPLEMENTATION_PLAN.md` so the trace is reviewable at approval; `approve-plan`'s cross-artifact consistency check reads it.

The mode composes with the normal slicing rules (`Scope`, `Depends-on`, the Execution waves subsection, and EARS exit criteria all remain required). The spec is treated as an external contract for grounding: a spec's reference to an external library or API still goes through the reference-grounding gate at execution time; the spec text alone does not satisfy it.

## Consequences

- The WOS gains a deterministic spec-to-plan path that reuses the existing planning surface, approval gate, and deliverable ledger instead of adding a parallel command.
- Keeping it a mode avoids a four-registry new-command registration and a `count:commands` bump, and keeps `approve-plan` as the single approval boundary (the `## Spec coverage` table becomes part of what that gate verifies).
- The no-silent-omission guarantee from ADR-0056 now covers spec items, not just deliverables the user typed into a brief: a requirement that maps to no slice blocks approval as a NEEDS CLARIFICATION marker.
- This ADR is additive; default free-form planning is unchanged, and the mode is inert unless `--spec` is passed.
