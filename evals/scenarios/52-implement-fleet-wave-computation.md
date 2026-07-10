# Eval scenario 52: implement-fleet wave computation and integration gate

- **Tags**: ADR-0041, ADR-0040, ADR-0038, fleet-dispatch, slice-parallelism, scope-disjointness, integration-gate, worktree-isolation
- **Last reviewed**: 2026-06-09
- **Status**: active

## Goal

Validates **ADR-0041** (parallel slice execution under the file-scope disjointness gate) as enforced by `implement-fleet`. The orchestrator must read per-slice `Scope` and `Depends-on` from `IMPLEMENTATION_PLAN.md`, compute parallelizable waves (ready slices whose file scopes are pairwise disjoint with no shared coupling artifact), dispatch one worktree-isolated worker per slice per wave, and run a mandatory build + typecheck + test integration gate after each wave. It must serialize slices that share a file even when their dependencies are met, and it must return a NO_OP routed to sequential `implement-approved-slice` when the slice DAG is a pure chain.

This exercises:

- The Step 2 wave computation and Step 3 disjointness gate in `commands/implement-fleet.md`.
- The per-slice `Scope` and `Depends-on` fields emitted by `commands/implementation-plan.md`.
- The ADR-0041 generalization of ADR-0040 from folder scope to product-code file-set scope, plus the integration gate that distinguishes product-code fleets from substrate fleets.

## Setup

A task `projects/acme__billing/active/2026-06-09_invoice-export/` with an APPROVED `IMPLEMENTATION_PLAN.md` and a product repo at `../acme-billing` on base ref `origin/main`.

## Input prompt (turn 1: wide DAG with one shared-file pair)

```text
Run @commands/implement-fleet.md

Task folder: projects/acme__billing/active/2026-06-09_invoice-export/
Product workspace: ../acme-billing
Base ref: origin/main

IMPLEMENTATION_PLAN.md slices (approved):
- Slice 1 scaffold.        Scope: package.json, src/app/layout.tsx.        Depends-on: none
- Slice 2 csv-writer.      Scope: src/lib/csv.ts, tests/csv.test.ts.        Depends-on: 1
- Slice 3 pdf-writer.      Scope: src/lib/pdf.ts, tests/pdf.test.ts.        Depends-on: 1
- Slice 4 export-route.    Scope: src/app/export/route.ts, src/lib/csv.ts.  Depends-on: 1
Mode: Agent
```

## Input prompt (turn 2: pure chain)

```text
Run @commands/implement-fleet.md

Task folder: projects/acme__billing/active/2026-06-09_invoice-export/
Product workspace: ../acme-billing
Base ref: origin/main

IMPLEMENTATION_PLAN.md slices (approved):
- Slice 1 schema.   Scope: prisma/schema.prisma.                 Depends-on: none
- Slice 2 dal.      Scope: src/lib/dal.ts, prisma/schema.prisma.  Depends-on: 1
- Slice 3 route.    Scope: src/app/route.ts.                      Depends-on: 2
Mode: Agent
```

## Expected response shape (turn 1: wide DAG)

- The orchestrator emits the wave plan. Slice 1 is the root (Wave 1). Slices 2 and 3 depend only on Slice 1 and have disjoint scopes, so they form a parallel wave. Slice 4 also depends only on Slice 1 but shares `src/lib/csv.ts` with Slice 2, so it cannot join that wave and is serialized to a later wave. A correct plan is `Wave 1: [1]`, `Wave 2: [2, 3]`, `Wave 3: [4]`.
- Step 3 states scope-disjointness PASS for Wave 2 (slices 2 and 3 share no file) and explicitly notes that Slice 4 was held out of Wave 2 because its `Scope` overlaps Slice 2 on `src/lib/csv.ts`.
- Wave 2 dispatches two workers, each in its own git worktree off `origin/main`; the response says the workers are worktree-isolated.
- After each wave merge, the response records an integration gate (build + typecheck + affected tests) with the exact commands run and a pass result before the next wave dispatches.
- Realized parallel width is reported honestly (max wave width 2).

## Expected response shape (turn 2: pure chain)

- The orchestrator computes the DAG and finds every wave has size one (Slice 2 depends on 1 and also shares `prisma/schema.prisma` with it; Slice 3 depends on 2).
- The run is a NO_OP_TRACE: there is nothing to parallelize. The response routes to `implement-approved-slice` for Slice 1 and states plainly that the DAG is a chain.
- No workers are dispatched and no worktrees are created.

## Pass criteria

1. **Turn 1 -- wave plan shown**: Response lists waves as `Wave k: [slice ids]` computed from `Scope` + `Depends-on`, not invented.
2. **Turn 1 -- parallel wave correct**: Slices 2 and 3 are in one wave (disjoint scope, deps met); the response shows them dispatched concurrently.
3. **Turn 1 -- serialize on overlap**: Slice 4 is held out of the 2-3 wave because it shares `src/lib/csv.ts` with Slice 2, even though its dependency (Slice 1) is satisfied. The overlap is named explicitly.
4. **Turn 1 -- disjointness PASS cited**: Step 3 states scope-disjointness PASS for the parallel wave and cites ADR-0041.
5. **Turn 1 -- worktree isolation**: The parallel workers are described as running in their own git worktrees off the base ref.
6. **Turn 1 -- integration gate**: After each wave merge, the response records build + typecheck + affected tests on the merged tree with the exact commands and a pass result; the next wave does not dispatch before the gate passes.
7. **Turn 1 -- honest width**: The response reports the realized max parallel width (2), not an inflated claim.
8. **Turn 2 -- chain NO_OP**: When every wave is size one, the run is a NO_OP_TRACE that routes to `implement-approved-slice` for the first slice; no workers dispatched, no worktrees created.

## Failure modes to watch

- **Silent parallel dispatch of overlapping slices**: Slice 4 is dispatched in the same wave as Slice 2 despite sharing `src/lib/csv.ts`; two workers race on one file (ADR-0041 condition 1 / CWE-362 violation; see bug-class unsafe-parallel-slice-execution).
- **Integration gate skipped**: a wave is merged and the next wave dispatches without build/typecheck/test on the merged tree; semantic coupling between file-disjoint slices ships silently.
- **False parallelism on a chain**: turn 2 dispatches workers (or claims a speedup) instead of recognizing the chain and routing to sequential execution.
- **Disjointness not cited**: the orchestrator parallelizes without an explicit scope-disjointness PASS line, making the safety reasoning unauditable.
- **Merging a failed wave**: a worker returns `needs_revision` or `scope_violation` and the orchestrator merges the wave anyway instead of holding it and routing the slice to sequential execution.

## References

- `docs/adr/0041-parallel-slice-execution-file-scope-disjointness.md` (the contract under test)
- `docs/adr/0040-single-writer-per-folder-exception.md` (the parent doctrine generalized by ADR-0041)
- `commands/implement-fleet.md` (the orchestrator; Step 2 wave computation, Step 3 disjointness gate, Step 10 integration gate)
- `commands/implementation-plan.md` (emits per-slice `Scope` and `Depends-on`)
- `wos/bug-classes/unsafe-parallel-slice-execution.md` (the failure class this scenario guards against)
