# Phase 4 -- HIGH-Complexity E2E Walkthrough Scenario Outline

## Context vs Phase 3
Phase 3 exercised LOW complexity on a 30-line Flask fixture: single persona, single slice, ~6 substrate writes, no cross-persona contention. Phase 4 must exercise the **real load shape**: multi-persona dispatch, K.2 ownership writes from 3+ owner commands, K.5 validator-gated closure, and substrate races resolvable only by the actual ownership matrix.

## Target Scope
**Scenario**: Multi-slice task on a realistic repo-shaped fixture (~800 LOC TypeScript service + 1 schema migration + 1 RLS policy + 1 Trigger.dev task). The task spans **two persona-dispatched slices** that touch overlapping substrate:

- Slice A (backend persona): schema migration + RLS update + service handler change
- Slice B (integrations persona): Trigger.dev task wiring + idempotency key strategy
- Cross-cut (DX persona): test-strategy update + repo-consistency-sweep

Both slices closed sequentially through `slice-closure`, then the task is gated through `verify-against-rubric` (K.5) before `task-close`.

## Expected Step Count (~20)
1. `task-init` (seeded from project charter)
2. `impact-analysis` (multi-repo aware)
3. `decision-interview` (2 LOCKED decisions: RLS shape, idempotency key shape)
4. `implementation-plan` (2 slices declared)
5. `approve-plan`
6. `implement-approved-slice` (Slice A)
7. `sync-task-state` mid-slice
8. `capture-observation` (RLS edge case)
9. `repo-consistency-sweep` (Slice A)
10. `review-hard` (Slice A)
11. `slice-closure` (Slice A) -- **first K.2 write contention point**
12. `implement-approved-slice` (Slice B)
13. `implement-slice-complement` (micro-delta on Slice A artifact)
14. `capture-observation` (cross-persona conflict on TASK_STATE.md)
15. `review-hard` (Slice B)
16. `slice-closure` (Slice B)
17. `where-we-at` (macro checkpoint)
18. `verify-against-rubric` (K.5 gate)
19. `pr-package`
20. `task-close`

## Substrate Writes to Validate (~50)
- TASK_STATE.md: ~14 appends (state syncs, observations, slice closures, K.5 verdict)
- DECISIONS.md: ~4 LOCKED entries
- IMPLEMENTATION_PLAN.md: ~3 slice annotations (status, evidence)
- SLICE_A_NOTES.md / SLICE_B_NOTES.md: ~10 each (evidence, exit criteria, validator output)
- SOURCE_OF_TRUTH.md: ~3 touchpoints (multi-repo subsection)
- IMPACT_ANALYSIS.md: ~2 amendments after observation capture
- PR_PACKAGE.md: 1 final write
Each write tagged with owner command per K.2 matrix; cross-owner writes must be rejected or merged per ownership rule.

## K.5 Validator Gate
Final `verify-against-rubric` must:
- Detect any drift between DECISIONS.md and implemented diff
- Confirm both slices have closure evidence
- Confirm K.2 ownership log shows zero unauthorized writes
- Block `task-close` on red verdict

## Edge Cases to Exercise
- **Cross-persona conflict**: Slice A and Slice B both attempt TASK_STATE.md append within same step window
- **Slice-closure mid-write**: `slice-closure` invoked while `implement-slice-complement` still has uncommitted notes
- **Stale plan**: `direction-adjust` mid-Slice B forces IMPLEMENTATION_PLAN.md rewrite without losing Slice A closure
- **No-op closure**: `slice-closure` invoked twice on Slice A -- second call must return no-op, not duplicate write
- **K.5 red verdict**: Inject a forced DECISIONS drift to confirm gate blocks `task-close`
- **Multi-repo write fan-out**: SOURCE_OF_TRUTH.md per-repo subsection updates from two personas in same slice