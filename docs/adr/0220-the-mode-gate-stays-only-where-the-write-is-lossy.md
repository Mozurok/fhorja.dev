# ADR-0220: The mode gate stays only where the write is lossy

- **Status**: Accepted
- **Date**: 2026-09-23
- **Supersedes**: nothing. It settles the two commands ADR-0215 left pending.
- **Tags**: mode-gate, proposed, applied, compact-task-memory, self-critique-and-revise, adr-0199, adr-0215

## Context

ADR-0199 removed the ADR-0001 mode gate, and ADR-0215 finished removing it from eight commands that
still carried it. ADR-0215 left two on purpose, each with a reason that might make the gate deliberate
rather than residue, and listed them in `MODE_GATE_PENDING` in `evals/scripts/structural-evals.py`:

- `compact-task-memory` compacts `TASK_STATE.md` lossily. What it drops cannot be recovered by reading
  the file afterwards, and that recoverability is what ADR-0199 rested on.
- `self-critique-and-revise` is an evaluator-optimizer, described as built to show the critique and the
  revision before either lands.

The 2026-09-22 documentation drift audit asked the maintainer to settle both.

## Decision

The gate stays on `compact-task-memory` and goes from `self-critique-and-revise`.

A compaction removes facts from the one file a resumed session reads first. Writing it `PROPOSED`
outside Agent mode lets a person see what will be dropped before it is gone. That is the same test
ADR-0199 used, applied honestly: the write is not recoverable by reading the file, so it keeps the gate.

A self-critique revision is not lossy. It rewrites a draft plan, slice note or PR package, every line
of the original is in git, and the critique and diff summary are already part of the response. Showing
the critique is response content; it does not need the write to wait. The command now writes the
revised artifact `APPLIED` in every mode like the rest.

`MODE_GATE_PENDING` names only `compact-task-memory`, whose Artifact changes line cites this ADR.

## Consequences

### Positive

- One command carries the gate, and the reason it does is a property of its write, not of its history.
- A revision in Ask or Plan mode is on disk for the next command to read, which is what ADR-0199
  promised for task memory.

### Negative

- A user who liked reviewing a revision before it landed now reviews it after, through the diff
  summary and git.

### Neutral

- `check_task_memory_written_in_every_mode` needs no new logic. The pending list shrank by one entry,
  and the check already fails if that entry comes back without the gate.

## Alternatives considered

### Keep the gate on both and record it as deliberate

- Rejected for `self-critique-and-revise`: the reason given for it was about showing the critique,
  and the critique is shown whether or not the write waits.

### Remove the gate from both

- Rejected for `compact-task-memory`: it is the one write in the tree that a later read cannot undo.

## References

- `commands/compact-task-memory.md` and `commands/self-critique-and-revise.md`, `### Definition of done`.
- `evals/scripts/structural-evals.py`, `MODE_GATE_PENDING` and `check_task_memory_written_in_every_mode`.
- ADR-0199, ADR-0215.
