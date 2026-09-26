# ADR-0219: A staged index is the selection

- **Status**: Accepted
- **Date**: 2026-09-22
- **Supersedes**: nothing. It completes ADR-0167's rule 5 in `branch-commit`, which says how to stage and never said what.
- **Tags**: branch-commit, apply, staging, untracked, index, adr-0163, adr-0167

## Context

`branch-commit --apply` commits with a bare `git commit`, so the commit is exactly the index that was
displayed (ADR-0167). Rule 5 says staging names each path explicitly, "including a path that is
currently untracked". It never says which paths to stage.

Scenario 125 stages `+two` in `tracked.txt`, then edits the same file again and creates an untracked
`untracked.txt`. Its criterion 4 required `untracked.txt` in the commit. Two isolated runs of Opus 5.5
against the same fixture on 2026-09-22 did different things: one staged `untracked.txt` by name and
committed it, the other committed only the staged edit and left the file out. Both kept the unstaged
edit out, which the scenario requires. A criterion that one of two correct-looking runs fails, on a
point the command does not decide, measures chance.

## Decision

WHEN the index already holds staged changes on entry, that staged set is the selection. The command
adds nothing to it, and the display names every unstaged edit and untracked path it leaves out, so
nothing leaves the commit unseen. WHEN the index is empty, the command stages the paths the task's work
changed, by name.

The first case is the same reason the unstaged edit already stays out: a person who staged part of a
change chose what goes in. Sweeping in an untracked file is also how a scratch file or a credential
lands in history, which is why naming each path was required in the first place.

Scenario 125's criterion 4 now asserts the staged edit alone plus both omissions named. Its failure mode
"the untracked file quietly vanishes" keeps its meaning: leaving the file out is correct, leaving it out
unnamed is not.

## Consequences

### Positive

- The command decides the case, so the scenario grades the command and not the draw.
- A curated index is never widened by the tool.

### Negative

- A user who expected a new file to ride along has to stage it or run with an empty index. The display
  names it, so the omission is visible before HEAD moves.
- The empty-index case still leans on "the paths the task's work changed", which a run with no task
  scope has to infer. This does not settle that case.

### Neutral

- Nothing changes for a run that starts with an empty index and no untracked files.
