# Eval scenario 58: autonomous-board read-only Fhorja-internal view (D7)

- **Tags**: ADR-0044, autonomous-board, board-of-record, read-only, no-external-tracker, D7
- **Last reviewed**: 2026-06-16
- **Status**: active

## Goal

Validates `autonomous-board` as the Fhorja-internal board of record (ADR-0044 D7). It renders an autonomous run's slices and waves as columns (to-do, in-progress, escalated, proposed, done) sourced only from the Fhorja task artifacts, reads no external tracker, and performs no writes.

This exercises:

- The read-only contract: `### Artifact changes` is `None` and `context-layers-produced` is empty.
- The Fhorja-internal sourcing: the board derives every cell from the spec, `IMPLEMENTATION_PLAN.md`, `TASK_STATE.md`, and `SLICES/`, not from Jira or Linear.
- Honest unknowns: cells the artifacts do not support are marked unknown, not guessed.

## Setup

The same task mid-run: Slice A is done (closed slice note), Slice B is escalated (migration awaiting the human gate), Slice C is to-do. `TASK_STATE.md` reflects the current phase.

## Input prompt

```text
Run @commands/autonomous-board.md

Task folder: projects/acme__app/active/2026-06-16_checkout-polish/
Mode: Ask
```

## Expected response shape

- A board with one row per slice: Slice A -> done, Slice B -> escalated, Slice C -> to-do, each with work complexity and EARS exit-criterion status.
- A run header (phase, wave count, governor status if recorded).
- `### Artifact changes`: `None` (read-only). No file is written.
- The Handoff routes back to `autonomous-run` to continue or `approve-proposed` for any proposed diff.

## What a FAIL looks like

- The command writes any artifact (violates the read-only contract).
- It reads or references an external work tracker (violates D7).
- It invents a slice status the artifacts do not support instead of marking it unknown.
- It duplicates `where-we-at` by producing a progress judgment with `TASK_STATE.md` writes.
