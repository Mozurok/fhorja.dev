# ADR-0141: A pre-compaction snapshot replaces the git-only reversibility pointer

Date: 2026-08-11

Status: Accepted

Supersedes decision 4 of ADR-0015 (`Reversible via git only`).

## Context

ADR-0015 made `compact-task-memory` safe to run by pairing a lossy edit with an audit trail, and
decision 4 named the escape hatch: the pre-compaction bytes are recoverable via
`git show <SHA>:TASK_STATE.md`, and the Compaction history entry records the SHA. That escape is
what made a one-way edit acceptable.

The premise is false for every task this command actually runs on. `projects/` is gitignored
(`.gitignore`), so a task living there has no commit holding its `TASK_STATE.md` and `git show`
resolves to nothing. The command knew: it prescribed the git pointer and then admitted the
gitignore four lines later, in the same file.

The contradiction was not theoretical. Measured 2026-08-11 across the active tasks in this
repository: seven `Reversible via` pointers in six tasks, naming three different invented
snapshot paths (`.wos/pre-compaction/`, `.wos/snapshots/`, a scratchpad path) and, twice, "this
session's conversation transcript", which no longer exists. The model had been improvising the
contract for weeks, differently each time, because the contract as written could not be obeyed.
`evals/scenarios/20-compact-task-memory-multi-slice.md` scored the broken form as a pass
criterion, so the eval defended the defect.

A second gap surfaced with it. The preserve and filter lists named 16 of the 20 template sections
declared in `commands/sync-task-state.md` (ADR-0111), leaving `Quick reanchor`,
`Requested deliverables`, `Recommended pipeline` and `Current status` in neither bucket. Two more
sections created by their own decisions, `## Ruled-out hypotheses` (ADR-0088) and
`## Observations`, were absent from the template list and from both buckets. A literal execution
could drop a ledger that exists specifically to survive compaction. The command also preserves
`## Last completed step` verbatim and never writes to it, so after a compaction the field names
whatever ran before, which is the one field a cold session reads to decide whether to warn about
context rot.

This was found by the 2026-08-11 journey-validation run, six end-to-end command chains executed
in isolated worktrees and graded by independent judges. Two separate journeys hit it.

## Decision

The snapshot is the primary reversibility route, and it is written before the prune.

1. Copy the current `TASK_STATE.md` byte for byte to
   `<task-root>/.wos/compaction/<ISO-8601-timestamp>_TASK_STATE.md`, then prune, then cite that
   path in `Reversible via`.
2. Cite `git show <SHA>:TASK_STATE.md` in addition, and only when the task folder is git-tracked.
3. A compaction that can cite neither is invalid output: the pruned file is not written.

The section buckets become total. Every section is preserved or filtered, and a section the
command does not recognize is preserved verbatim and named in the compaction history entry.
`## Requested deliverables` and `## Ruled-out hypotheses` are preserve-verbatim by name, because
both are coverage ledgers whose whole purpose is to outlive the working memory around them.

`compact-task-memory` records itself in `## Last completed step`.

## Consequences

- Reversibility becomes real for tasks under `projects/`, which is where every task in this
  repository lives. Before this, the field was a promise with nothing behind it.
- **The snapshot is a local undo, not a backup, and the ADR says so rather than letting a reader
  assume otherwise.** `.wos` is gitignored too. The bytes survive between sessions on one
  machine, not across machines and not in any remote. A task folder that is git-tracked gets the
  stronger guarantee through route 2; a task under `projects/` does not, and this ADR does not
  close that gap. Moving task memory out of gitignore is a larger decision and is not taken here.
- The invalid-output condition is a real refusal path. A compaction that cannot write the
  snapshot (no write permission, no `.wos`) now stops instead of producing a pruned file with a
  pointer to nothing. That is the intended trade: a refused compaction is recoverable, a
  compaction with a dead pointer is not.
- `evals/scenarios/20-compact-task-memory-multi-slice.md` gains criterion 6b, which fails a
  response citing only a git SHA. Without that edit the eval would have reverted this decision on
  the next run.
- Four template sections and two ledgers move from unspecified to specified. The catch-all rule
  means the next section added to the template is safe by default rather than silently droppable,
  which is the failure mode that produced this ADR.
- ADR-0015 stays as written and is not patched. Its decision 4 is superseded here; its audit-trail
  reasoning and the ADR-0093 provenance chain are unchanged and still carry the trace-level
  recovery path.
- Not addressed here: the compaction trigger and the compaction gate still use opposite metrics,
  so a discovery-phase task can be routed to a command that refuses it by definition. That is a
  separate defect from the same run and needs its own decision.
