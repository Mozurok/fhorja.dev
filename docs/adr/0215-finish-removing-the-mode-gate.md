# ADR-0215: Finish removing the mode gate, and extend it to project memory

- **Status**: Accepted; superseded in part by [ADR-0222](./0222-task-close-writes-its-substrate-in-every-mode.md) (the Neutral consequence about `task-close`; the `task-workspace` half stands)
- **Date**: 2026-09-22
- **Supersedes**: nothing. It completes ADR-0199 and applies its reasoning to project memory.
- **Tags**: mode-gate, proposed, applied, task-init, project-bootstrap, adr-0001, adr-0034, adr-0199

## Context

ADR-0199 removed the ADR-0001 mode gate: a command writes its task-memory files directly and marks
them `APPLIED`, in every mode. It stated its reach, "the gate reached 57 command-tree files plus the
spec", and "eight eval scenarios graded the gate as correct behavior and were rewritten". The change
was taken as done.

On 2026-09-22, while preparing to validate the new attended mode end to end, the gate was still live.
Measured across the command tree, eight commands still marked task or project memory `APPLIED` only in
Agent mode and `PROPOSED` otherwise: `task-init`, `sync-task-state`, `state-reconcile`, `task-close`,
`post-review-pivot`, `pr-feedback-ingest`, `task-workspace` and `project-bootstrap`. `task-init` is the
command ADR-0199 says it shrank by 236 characters. The spec kept a whole subsection built on the gate,
and its closing rule still told the reader the next step should be "ready to paste", the relay
ADR-0186 replaced and scenario 137 fails. The FAQ promised new users "PROPOSED-by-default writes".

Scenarios 01 and 08 had been rewritten for ADR-0190, which routed Ask to `approve-proposed`, and not for
ADR-0199, which removed that route. Scenario 01 contradicted itself: it expected the task files
`APPLIED` in one place and `PROPOSED` with an `approve-proposed` handoff in another.

A decision that declared its full reach left part of it behind, and nothing measured the residue.

## Decision

The mode gate is removed from the eight commands. Each Artifact changes line now marks its writes
`APPLIED` in every mode and names the case that is not a mode gate: a section the command does not own
gets a `<!-- PROPOSED by <command>: ... -->` block for its owner (ADR-0034). That ownership meaning of
PROPOSED is untouched, and holds in Agent mode too.

`project-bootstrap` is included although ADR-0199 named only task memory, because its reasoning covers
project memory exactly: writing two files under the gitignored `projects/` tree is internal and
reversible. It matters more there. The next `task-init` reads `PROJECT_CHARTER.md` to seed the task,
and a charter left `PROPOSED` is not on disk, so an Ask-mode bootstrap followed by an Ask-mode init, the
path scenario 01 walks, would start the task unbootstrapped.

The spec's drift subsection now describes what can still accumulate, unpromoted ownership blocks,
rather than the removed file gate. Its closing rule says an attended session is already running the
next command or has stopped for a named reason. The FAQ describes reviewability as what it is now:
every command lists what it wrote under `### Artifact changes`.

Two commands keep the gate pending a decision, each for a reason that may be deliberate rather than
residue. `compact-task-memory` compacts lossily, and what it drops cannot be recovered by reading the
file afterwards, which was the reversibility ADR-0199 rested on. `self-critique-and-revise` is an
evaluator-optimizer built to show the critique and the revision before either lands.

`check_task_memory_written_in_every_mode` fails on a mode-conditioned Artifact changes line outside
those two, reports a pending entry that no longer carries the gate so the list cannot outlive what it
names, and fails if the spec or the FAQ describes the removed gate as current.

## Consequences

### Positive

- Ask and Agent now behave the same on task and project memory, which is what ADR-0199 said they did.
- The first two documents a reader meets describe the mode they will actually get.

### Negative

- Two commands still carry the gate, and whether they should is an open question with a real argument
  on each side.
- The check matches one sentence shape, the Artifact changes line. A mode gate written in other words
  passes it, which is how three of the eight were phrased differently from the rest.

### Neutral

- `task-close` keeps a mode condition on its `knowledge/` note and on its outcome append, and
  `task-workspace` on running `git worktree`. None of those is task or project memory: the first writes
  to the layer ADR-0054 reserves for humans, and the last runs a command in the user's repository.

## Alternatives considered

### Alternative 1: leave project-bootstrap under the gate, since ADR-0199 named task memory only

- Rejected. ADR-0199's own argument covers it, and scenario 01's bootstrap-then-init path breaks
  without it.

### Alternative 2: remove the gate from compact-task-memory and self-critique-and-revise too

- Deferred rather than rejected. Each has a reason the others lack, and removing a review step from a
  lossy operation is a decision, not a cleanup.

## References

- [ADR-0199](./0199-task-memory-is-written-not-proposed.md): the decision this completes.
- [ADR-0034](./0034-substrate-peers-and-worker-contract.md): the ownership meaning of PROPOSED, which stays.
