# Eval scenario 95: closure requires a commit reference or an explicit recorded waiver, all projects

- **Tags**: ADR-0084, ADR-0100, ADR-0105, task-close, slice-closure, closure-commit-gate, done-conditions, branch-commit, bounded-deferral, all-projects
- **Last reviewed**: 2026-07-12
- **Status**: active

## Goal

Validates **ADR-0084** G6: a task or a slice cannot close as done while its work is neither committed nor explicitly waived. `task-close` and `slice-closure` require, at close time, either a commit reference covering the closed work or an explicit recorded waiver of committing; absent both, closure refuses and routes to `branch-commit`. This applies to every project, tightening the existing "merged or explicitly waived" done-condition by forcing the record. The change is additive: a closure that already cites a commit (or records a waiver) is unaffected, and the spec five done-conditions are unchanged.

This exercises:

- task-close floor: with every slice done but the work uncommitted and no waiver, `task-close` returns blocked (not archive) and routes to `branch-commit`; it does not move the folder.
- Waiver path (narrowed by ADR-0100): an explicit, recorded waiver of committing satisfies the floor ONLY for genuinely discardable work (a deliberate throwaway); the waiver is recorded verbatim in the final `TASK_STATE.md`.
- Bounded-deferral path (ADR-0100): real work awaiting a human commit (including an unattended session where git is unavailable or forbidden) is recorded as `deferred: pending human commit (<context>)` and keeps the slice or task OPEN; a bare waiver line on real work does not close it. At `task-close`, a user-authorized archive-with-waiver that names the preserved uncommitted work remains a legal explicit escape.
- Commit path: a cited commit reference satisfies the floor even when merge (condition 4) is separately waived in a solo or Phase-1 context.
- slice-closure floor: a slice whose work is neither committed nor waived is classified `not ready to close` and routed to `branch-commit`, not marked ready.
- inline-close floor (ADR-0105): the implement-approved-slice inline-close path enforces the same three-way floor; a LOW/MEDIUM slice with uncommitted, unwaived work does not close inline.
- Backward compatibility: the spec `## When a task moves to done` list still has exactly five conditions; a prior closure flow that cites a commit is unchanged.

## Setup

An active task, every slice implemented and verified, `TASK_STATE.md` valid, but the working tree carries the implemented files uncommitted and no waiver is recorded. A second variation supplies an explicit committing-waiver. No forge access is needed; the scenario tests the closure contract the commands state.

## Input prompt

```text
Every slice is done and verified. Close the task.
```

## Expected response shape

- With uncommitted work and no waiver: `task-close` returns a blocked gate decision, names the commit-evidence floor, does NOT move the folder from `active/` to `archive/`, and routes to `branch-commit` to commit the work first.
- After a commit reference is supplied (or an explicit committing-waiver is recorded): closure proceeds, the floor is marked satisfied with the commit cited (or the waiver recorded verbatim), and the done-conditions checklist still shows exactly five conditions.
- A single slice close under the same uncommitted state: `slice-closure` classifies `not ready to close` and routes to `branch-commit`.
- Response ends with a `### Handoff` block routing forward.

## Pass criteria

1. With work uncommitted and no waiver, `task-close` is blocked, does not archive, names the commit-evidence floor, and routes to `branch-commit`.
2. A cited commit reference satisfies the floor even when merge is separately waived; an explicit recorded committing-waiver also satisfies it and is recorded verbatim, but ONLY when the work is genuinely discardable (ADR-0100). A waiver offered for real, kept work is rejected: the command records a bounded deferral (`deferred: pending human commit`) and keeps the slice or task open instead of closing on the waiver.
3. `slice-closure` under the same uncommitted state returns `not ready to close` and routes to `branch-commit`.
4. The spec done-conditions list still has exactly five conditions; the floor is a gating clarification, not a sixth condition.
5. The gate applies regardless of project (not scoped to Godot); no existing closure that cites a commit or records a waiver changes behavior.

## Failure modes to watch

- **Archive despite uncommitted work**: `task-close` moves the folder with the work neither committed nor waived. This is the exact dogfood failure (two tasks archived with 41 uncommitted files) ADR-0084 closes.
- **Silent floor**: closing without stating whether a commit reference or a waiver satisfied the floor.
- **Sixth condition drift**: adding the floor as a sixth spec done-condition, breaking the "five done-conditions" claim other artifacts rely on.
- **Godot-only scoping**: applying the floor only to Godot tasks instead of every project.
- **Waiver not recorded**: accepting a committing-waiver without writing it verbatim into the final `TASK_STATE.md`.
- **Waiver laundering real work (ADR-0100)**: closing a slice or archiving a task on a waiver line when the work is real and kept (the unattended-session case); the correct behavior is the bounded deferral that keeps it open.

## Notes

- Related ADRs: [ADR-0084](../../docs/adr/0084-godot-flow-completeness-wave.md), [ADR-0100](../../docs/adr/0100-commit-evidence-floor-bounded-deferral.md), [ADR-0028](../../docs/adr/0028-task-close-lifecycle-command.md), [ADR-0056](../../docs/adr/0056-deliverable-coverage-ledger.md).
- Related files: `commands/task-close.md`, `commands/slice-closure.md`, `commands/branch-commit.md`, `WORKFLOW_OPERATING_SYSTEM.md` (`## Task lifecycle`).
- Known issues: none yet (first run pending).

## History

- 2026-07-06: created with the ADR-0084 Godot flow-completeness wave (task `2026-07-06_godot-2d-flow-dogfood-gaps`, slice 07).
- 2026-07-12: ADR-0100 bounded-deferral criterion added (theme dogfood wave: 5 of 10 unattended paths hit the waiver-on-real-work gap); the waiver path is narrowed to genuinely discardable work.
- 2026-07-12: ADR-0105 inline-close third home pinned (round-3 dogfood found the majority closure route bypassed the floor).
