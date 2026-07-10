# Eval scenario 96: the Godot runtime-gate is enforced at closure, and never fires on a non-Godot task

- **Tags**: ADR-0085, godot-cluster, runtime-gate, slice-closure, implement-approved-slice, task-close, closure-enforcement, enforces-adr-0084
- **Last reviewed**: 2026-07-06
- **Status**: active

## Goal

Validates **ADR-0085** (enforcing the ADR-0084 runtime-gate adoption rule at closure): a runtime-observable Godot slice cannot close, and a Godot task cannot archive, while the behavior was neither runtime-verified nor explicitly skipped. The check is enforced at three homes (slice-closure, the implement-approved-slice inline-close path, and task-close), blocks and routes to godot-runtime-verify, reuses the D-7 commit-floor block-and-route idiom, reads recorded evidence without running a scene, and never fires on a non-Godot task or a slice with no runtime surface. The change is additive: the task-close done-conditions list still has exactly five numbered conditions.

This exercises:

- slice-closure block: a Godot slice whose scope touched a `.tscn`/`.gd` with no recorded godot-runtime-verify PASS and no explicit skip is classified `not ready to close` and routed to godot-runtime-verify.
- inline-close block (the load-bearing home): a LOW/MEDIUM Godot slice does NOT close inline via implement-approved-slice without a recorded PASS or a skip; it routes to godot-runtime-verify first, rather than closing inline and bypassing slice-closure.
- task-close backstop: a Godot task with any runtime-observable slice missing both a PASS and a skip is blocked (not archived) and routed to godot-runtime-verify.
- Skip and verified paths: a recorded godot-runtime-verify PASS satisfies the check; a one-line explicit skip reason in the slice notes satisfies it for a no-runtime-surface slice (a pure `.tres` data resource, a `project.godot` settings change, or docs).
- No-fire cases: a non-Godot task (a backend/frontend slice) and a Godot slice with no `.tscn`/`.gd` scope never trigger the check.
- Backward compatibility: the spec `## Task lifecycle` is unchanged; the task-close done-conditions list still has five numbered conditions (the floor is a bullet, not a sixth condition).

## Setup

Three variations, no engine needed (the scenario tests the closure contract the commands state): (a) a Godot task with a `.gd`/`.tscn` slice implemented but no GODOT_RUNTIME_VERIFY PASS and no skip line; (b) the same after a PASS is recorded, or after an explicit skip line is added for a data-only slice; (c) a non-Godot backend task closing a slice.

## Input prompt

```text
Close this slice. (Variation a: Godot slice touched Ball.gd and Ball.tscn, no runtime-verify PASS recorded, no skip note. Variation b: a GODOT_RUNTIME_VERIFY PASS is now recorded. Variation c: a Python backend slice.)
```

## Expected response shape

- Variation a (slice-closure or the implement-approved-slice inline-close path): the slice is classified `not ready to close` (or is NOT closed inline), the response names the Godot runtime-gate floor, and routes to godot-runtime-verify; the slice is not marked done.
- Variation b: with a recorded PASS (or an explicit skip line for a data-only slice), the check is satisfied and closure proceeds normally.
- Variation c: the check does not fire; the backend slice closes on its normal criteria with no mention of godot-runtime-verify.
- A task-close on a Godot task with an unverified, unskipped runtime-observable slice returns blocked (not archived) and routes to godot-runtime-verify; the done-conditions checklist still shows five numbered conditions.
- Response ends with a `### Handoff` block routing forward.

## Pass criteria

1. A runtime-observable Godot slice with neither a recorded PASS nor a skip is blocked at slice-closure AND does not close inline via implement-approved-slice; both route to godot-runtime-verify.
2. A recorded godot-runtime-verify PASS, or an explicit one-line skip for a no-runtime-surface slice, satisfies the check and closure proceeds.
3. task-close blocks (does not archive) a Godot task with any runtime-observable slice missing both, routing to godot-runtime-verify.
4. The check never fires on a non-Godot task or a Godot slice with no `.tscn`/`.gd` scope.
5. The task-close done-conditions list still has exactly five numbered conditions (the floor is a bullet, not a sixth condition); the spec `## Task lifecycle` is unchanged.
6. The check reads recorded evidence and never runs a scene.

## Failure modes to watch

- **Inline-close bypass**: implement-approved-slice closing a runtime-observable Godot LOW/MEDIUM slice inline without a PASS or skip. This is the load-bearing failure ADR-0085 exists to close.
- **False fire**: the check blocking a non-Godot task, or a data-only/config Godot slice, instead of passing.
- **Sixth condition drift**: adding the floor as a sixth numbered task-close done-condition, breaking the "five done-conditions" claim.
- **Scene run**: the closure command attempting to run a scene itself instead of reading a recorded PASS.
- **Silent close**: closing a runtime-observable Godot slice as done without stating whether a PASS or a skip satisfied the floor.

## Notes

- Related ADRs: [ADR-0085](../../docs/adr/0085-godot-runtime-gate-enforcement.md), [ADR-0084](../../docs/adr/0084-godot-flow-completeness-wave.md), [ADR-0028](../../docs/adr/0028-task-close-lifecycle-command.md), [ADR-0031](../../docs/adr/0031-ears-for-decisions-and-exit-criteria.md).
- Related files: `commands/slice-closure.md`, `commands/implement-approved-slice.md`, `commands/task-close.md`, `commands/godot-runtime-verify.md`.
- Known issues: none yet (first run pending).

## History

- 2026-07-06: created with the ADR-0085 runtime-gate enforcement (task `2026-07-06_godot-runtime-gate-enforcement`, slice 03).
