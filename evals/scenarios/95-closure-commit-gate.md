# Eval scenario 95: closure requires a commit reference or an explicit recorded waiver, all projects

- **Tags**: ADR-0084, task-close, slice-closure, closure-commit-gate, done-conditions, branch-commit, all-projects
- **Last reviewed**: 2026-07-06
- **Status**: active

## Goal

Validates **ADR-0084** G6: a task or a slice cannot close as done while its work is neither committed nor explicitly waived. `task-close` and `slice-closure` require, at close time, either a commit reference covering the closed work or an explicit recorded waiver of committing; absent both, closure refuses and routes to `branch-commit`. This applies to every project, tightening the existing "merged or explicitly waived" done-condition by forcing the record. The change is additive: a closure that already cites a commit (or records a waiver) is unaffected, and the spec five done-conditions are unchanged.

This exercises:

- task-close floor: with every slice done but the work uncommitted and no waiver, `task-close` returns blocked (not archive) and routes to `branch-commit`; it does not move the folder.
- Waiver path: an explicit, recorded waiver of committing (a deliberate throwaway) satisfies the floor and lets closure proceed, with the waiver recorded verbatim in the final `TASK_STATE.md`.
- Commit path: a cited commit reference satisfies the floor even when merge (condition 4) is separately waived in a solo or Phase-1 context.
- slice-closure floor: a slice whose work is neither committed nor waived is classified `not ready to close` and routed to `branch-commit`, not marked ready.
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
2. A cited commit reference satisfies the floor even when merge is separately waived; an explicit recorded committing-waiver also satisfies it and is recorded verbatim.
3. `slice-closure` under the same uncommitted state returns `not ready to close` and routes to `branch-commit`.
4. The spec done-conditions list still has exactly five conditions; the floor is a gating clarification, not a sixth condition.
5. The gate applies regardless of project (not scoped to Godot); no existing closure that cites a commit or records a waiver changes behavior.

## Failure modes to watch

- **Archive despite uncommitted work**: `task-close` moves the folder with the work neither committed nor waived. This is the exact dogfood failure (two tasks archived with 41 uncommitted files) ADR-0084 closes.
- **Silent floor**: closing without stating whether a commit reference or a waiver satisfied the floor.
- **Sixth condition drift**: adding the floor as a sixth spec done-condition, breaking the "five done-conditions" claim other artifacts rely on.
- **Godot-only scoping**: applying the floor only to Godot tasks instead of every project.
- **Waiver not recorded**: accepting a committing-waiver without writing it verbatim into the final `TASK_STATE.md`.

## Notes

- Related ADRs: [ADR-0084](../../docs/adr/0084-godot-flow-completeness-wave.md), [ADR-0028](../../docs/adr/0028-task-close-lifecycle-command.md), [ADR-0056](../../docs/adr/0056-deliverable-coverage-ledger.md).
- Related files: `commands/task-close.md`, `commands/slice-closure.md`, `commands/branch-commit.md`, `WORKFLOW_OPERATING_SYSTEM.md` (`## Task lifecycle`).
- Known issues: none yet (first run pending).

## History

- 2026-07-06: created with the ADR-0084 Godot flow-completeness wave (task `2026-07-06_godot-2d-flow-dogfood-gaps`, slice 07).
