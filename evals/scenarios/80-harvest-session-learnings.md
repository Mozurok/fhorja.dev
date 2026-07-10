# Eval scenario 80: harvest-session-learnings appends anchored, de-duplicated lessons append-only

- **Tags**: ADR-0064, ADR-0017, learnings, reflexion, knowledge-capture, append-only, regression-guard
- **Last reviewed**: 2026-06-27
- **Status**: active

## Goal

Validates **ADR-0064** (amends ADR-0017): `harvest-session-learnings` sweeps the session and the active task's artifacts, judges which lessons generalize, and appends anchored, de-duplicated entries to the task's `LEARNINGS.md`, the produce-side counterpart to the consume path `task-init` already reads.

This exercises:

- Durability judgment: a reusable lesson (a failed approach and why, a tool gotcha) is admitted; one-off task status and decisions already in `DECISIONS.md` are rejected.
- The anchor rule: every appended entry anchors at a concrete point (`file:line`, slice header, command name, or timestamped `TASK_STATE.md` row) per `templates/LEARNINGS.md` `## Entry shape`.
- De-duplication: a candidate already present in `LEARNINGS.md` is surfaced as "already captured", not re-appended.
- Append-only: existing entries are never edited, reordered, compacted, or pruned (ADR-0017 item 6), and no other task-memory file is touched.
- NO_OP discipline: a session with nothing durable returns a NO_OP rather than a manufactured lesson.

## Setup

An active task whose session produced at least one hard-won lesson outside a slice closure (for example: an approach abandoned mid-task after a failed test, or an environment gotcha discovered while debugging), with an existing `LEARNINGS.md` that already holds one of the candidate lessons.

## Expected behavior

- WHEN the session produced a reusable, generalizable lesson not already captured, the command appends exactly that entry to `LEARNINGS.md`, anchored per `templates/LEARNINGS.md` `## Entry shape`, marked PROPOSED (Ask) or APPLIED (Agent).
- WHEN a candidate matches an existing entry (same anchor and lesson), it is reported as "already captured" and not re-appended.
- WHEN a candidate is one-off task status, a plan restatement, or a decision already in `DECISIONS.md`, it is dropped with a one-line reason.
- WHEN a lesson is genuinely cross-project, it is flagged as a pointer to `USER_MEMORY.md` and is NOT written by this command.
- WHEN the session produced nothing durable, the run is a NO_OP and routes back to the prior in-progress work.

## Failure modes (a FAIL looks like)

- Edits, reorders, compacts, or prunes an existing `LEARNINGS.md` entry (must be append-only), or writes any other task-memory file (for example `TASK_STATE.md`).
- Appends an unanchored retrospective summary, or re-appends a duplicate of an existing entry.
- Manufactures a filler lesson on a session that learned nothing durable instead of returning a NO_OP.
- Writes a cross-project lesson into the task `LEARNINGS.md` instead of flagging it as a `USER_MEMORY.md` pointer, or writes `USER_MEMORY.md` directly.
