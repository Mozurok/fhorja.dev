# ADR-0222: task-close writes its substrate in every mode

- **Status**: Accepted
- **Date**: 2026-09-23
- **Supersedes**: in part, [ADR-0215](./0215-finish-removing-the-mode-gate.md), its Neutral consequence about `task-close`. The `task-workspace` half of that consequence stands under the same rule.
- **Tags**: mode-gate, proposed, applied, task-close, task-workspace, knowledge-layer, outcome-ledger, adr-0199, adr-0215, adr-0220

## Context

Three September ADRs drew one line. ADR-0199 writes task memory `APPLIED` in every mode because the
write is internal and reversible. ADR-0215 extended that to project memory. ADR-0220 kept the gate on
`compact-task-memory` alone, because a compaction drops facts that no later read can recover.
Separately, `branch-commit --apply` refuses outside Agent mode, because it runs git in the product
repository.

`task-close` still carried four mode conditions. ADR-0215 named two of them in its Neutral
consequences and kept them, on the grounds that the `knowledge/` note writes to "the layer ADR-0054
reserves for humans" and that the outcome append is outside task and project memory. The other two
it did not name:

- the worktree teardown, which runs `git worktree remove` and `git worktree prune`;
- the reopen move, which moves the folder from `archive/` back to `active/` and appends a `reopen`
  event, yet was `PROPOSED` in Ask or Plan while the archive move it reverses was already `APPLIED` in
  every mode.

The ADR-0215 reasoning does not hold up for the first two either. ADR-0054 reserves the `knowledge/`
folder for human reading: the AI never auto-loads it. `task-close` was always its writer. The note and
`OUTCOMES.jsonl` both live under the gitignored `projects/` tree, which is project memory by any
reading, and neither write loses anything: the note is created once, idempotently, and the ledger is
append-only. The 2026-09-22 documentation drift audit asked the maintainer to settle the four.

## Decision

The rule, stated once: a write to the task or project substrate is `APPLIED` in every mode unless it
is lossy, and a command that runs in the product repository needs Agent mode.

Applied to `task-close`, each condition lands as follows.

- The outcome append to `OUTCOMES.jsonl` is `APPLIED` in every mode. It still never blocks the
  archive when the helper or the append fails.
- The `knowledge/` note, its deterministic links and the index entry are `APPLIED` in every mode.
  Topic links and tags stay human-confirmed per ADR-0055 D-11, auto-accepted under the solo waiver as
  before. The folder is still never auto-read.
- The reopen move and its writes are `APPLIED` in every mode, matching the archive move.
- The worktree teardown keeps Agent mode. In Ask or Plan it proposes the `git worktree` commands
  without running them, because they act on the product repository, not on the substrate.

`task-workspace` keeps its Agent-mode condition on `git worktree add` for the same reason.

The rule lives in `commands/task-close.md`. `check_no_mode_gate_phrasing` in
`evals/scripts/structural-evals.py` used to skip the whole of `task-close.md`; it now skips only the
line that runs `git worktree`, so a mode condition returning to any of the other three fails. Its
pattern also reads a sentence opening with "In Ask or Plan mode", the shape of the old reopen line,
which the lowercase form had missed even before the file was skipped whole.

## Consequences

### Positive

- An Ask-mode close leaves the ledger line and the knowledge note on disk, so `portfolio-review
  --outcomes` counts the task and the human layer records it without a second run.
- A reopen and the close it reverses behave the same in every mode.
- The mode condition that remains in `task-close` is explained by what it touches, the same test
  `branch-commit --apply` uses.

### Negative

- A user who used Ask mode to preview the knowledge note before it landed now reviews it after, in
  the file itself.

### Neutral

- The check's allowance moves from a file to a line. A new mode condition elsewhere in `task-close.md`
  that happens to share the teardown line would still pass, which is why the teardown sits in one
  bullet of its own.

## Alternatives considered

### Keep the ADR-0215 exception for the note and the ledger

- The two writes would stay `PROPOSED` outside Agent mode.
- Rejected: the reason given, that the `knowledge/` layer is reserved for humans, is about who reads
  it, not who writes it, and the ledger is an append-only file in project memory. Neither is lossy.

### Apply the teardown in every mode too

- `git worktree remove` would run in Ask and Plan.
- Rejected: it changes the product repository, the same class of act `branch-commit --apply` keeps
  behind Agent mode.

## References

- `commands/task-close.md`: the worktree teardown, reopen, knowledge-layer and outcome-record rules,
  Required output item 6, and the matching `### Definition of done` lines.
- `evals/scripts/structural-evals.py`: `MODE_GATE_OUT_OF_SCOPE` and `check_no_mode_gate_phrasing`.
- [ADR-0054](./0054-human-knowledge-layer.md), [ADR-0055](./0055-knowledge-layer-visual-organization.md),
  [ADR-0199](./0199-task-memory-is-written-not-proposed.md), [ADR-0215](./0215-finish-removing-the-mode-gate.md),
  [ADR-0220](./0220-the-mode-gate-stays-only-where-the-write-is-lossy.md).
