# Eval scenario 28: task-close terminal lifecycle transition

- **Tags**: task-close, lifecycle, done-conditions, archive, ADR-0028
- **Last reviewed**: 2026-06-01
- **Status**: active

## Goal

Validates that `task-close` performs the terminal task lifecycle transition correctly: it gates on the spec done-conditions, moves the task folder from `active/` to `archive/` only when the gate passes (or conditions are explicitly waived), writes the final `TASK_STATE.md`, and stays distinct from `slice-closure` (slice scope) and `where-we-at` (assessment only).

This is a two-turn scenario: turn 1 hits the gate with an unmet condition (blocked, no move); turn 2 closes with an explicit waiver (archive).

## Setup

Requires an active task with every slice closed and a valid `TASK_STATE.md`, e.g. `projects/acme__widget-pricing/active/2026-05-30_add-health-endpoint/`. Turn 1: review not yet done. Turn 2: maintainer waives team-approval and merge (solo / Phase-1 context) and review is complete.

## Input prompt (turn 1: blocked)

```text
Run @commands/task-close.md

task_folder: projects/acme__widget-pricing/active/2026-05-30_add-health-endpoint/
Mode: Agent
Note: review has not been run yet.
```

## Input prompt (turn 2: archive with waiver)

```text
Run @commands/task-close.md

task_folder: projects/acme__widget-pricing/active/2026-05-30_add-health-endpoint/
Mode: Agent
Note: review-hard passed (commit abc123). Solo task: I waive team-approval and merge-to-integration for this Phase-1 context.
```

## Expected response shape (turn 1: blocked)

- Done-conditions checklist with "review complete" marked **not-met**.
- Gate decision: **blocked**. The folder is NOT moved.
- Routes to the smallest unblocking action (`review-hard`).
- Ends with a complete `### Handoff` block.

## Expected response shape (turn 2: archive)

- Done-conditions checklist: implementation/review met (with evidence), team-approval and merge marked **waived** (user-confirmed), TASK_STATE final performed by this command.
- Gate decision: **archive**. Exact `from` -> `to` path stated (`active/...` -> `archive/...`) with the move mechanism (`git mv` or `mv`).
- `### Artifact changes` marks the move and final TASK_STATE write as **APPLIED** (Agent mode).
- Waiver recorded verbatim in the final TASK_STATE.md.
- Ends with a complete `### Handoff` block.

## Pass criteria

1. **Gate blocks on unmet condition**: Turn 1 returns blocked and does NOT move the folder when review is missing and not waived.
2. **Archive on pass/waiver**: Turn 2 moves `active/<slug>/` to `archive/<slug>/` with an explicit mechanism and records the waiver.
3. **No deletion**: Closure preserves the full task record; the move is not a cleanup.
4. **Scope discipline**: The response treats this as whole-task closure, not slice closure, and does not reopen signed-off work.
5. **Idempotency awareness**: The command states it would return `NO_OP_TRACE` if the folder were already archived with final state.

## Failure modes to watch

- **Archive despite unmet, unwaived condition**: Turn 1 moves the folder anyway. Regression of the done-conditions gate.
- **Silent waiver**: Turn 2 archives without recording the team-approval/merge waiver in TASK_STATE.
- **Deletion instead of move**: Any artifact is removed rather than relocated.
- **Slice confusion**: The command behaves like `slice-closure` (slice-scoped) instead of closing the whole task.
- **Missing Handoff in either turn**.

## Notes

- Related ADR: [ADR-0028](../../docs/adr/0028-task-close-lifecycle-command.md).
- Related commands: `commands/task-close.md`, `commands/task-init.md` (symmetric counterpart), `commands/slice-closure.md` (distinct, slice-scoped).
- The spec `## When a task moves to `done`` section is the source of the five done-conditions this command gates on.

## History

- 2026-06-01: scenario authored alongside the task-close command (ADR-0028).
