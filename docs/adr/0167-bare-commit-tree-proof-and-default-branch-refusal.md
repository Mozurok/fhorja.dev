# ADR-0167: The apply commit is a bare git commit, proven by tree hash, and refuses an unnamed default branch

- **Status**: Accepted; superseded in part by [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md) on attended runs: the escape from condition 7 is the `Task branch:` line `task-init` records. The default-branch refusal, the bare commit and the tree proof stand.
- **Date**: 2026-08-30
- **Tags**: branch-commit, apply-mode, evidence, tree-hash, default-branch, human-gate, supersedes-adr-0163-in-part

Supersedes, in part: ADR-0163 (the explicit-pathspec sentence; the display-then-commit contract and the human merge and push gate stand)

## Context

ADR-0163 required the `--apply` commit to be created with an explicit pathspec, on the reasoning
that naming the paths keeps the commit narrow. Reproduced on 2026-08-30 in a throwaway repository:
with `tracked.txt` staged carrying `two`, and `three-NOT-STAGED` appended afterwards without
staging, `git diff --staged` shows only `two` and `git commit -m msg -- tracked.txt` writes both.
A pathspec does not narrow a commit. It rebuilds each named path from the WORKING TREE, so any
edit landing after the display is committed as though it had been reviewed.

Condition 3 of the same command already argued the point it needed: "identity of files says
nothing about content of the commit". Condition 6 then compared file NAMES, which is exactly the
comparison that cannot see this. `git diff --staged --name-only` returns the same list either way.

Separately, none of the six conditions read the current branch. A run satisfying all six could
create a commit on the default branch, where a later `git reset` competes with whatever anyone
else has already pulled.

## Decision

The commit is created with a bare `git commit` carrying message flags only. `-a`, `-am`, and a
pathspec are all forbidden, and the reason is written where the prohibition is.

Proof moves from names to content. The command records `git write-tree` as `T_shown` right after
the display, re-runs it before committing and refuses if it moved, and asserts after the commit
that `git rev-parse HEAD^{tree}` equals `T_shown`. Two trees can carry identical paths and
different content; only the tree hash separates them.

A new condition 7 reads `git branch --show-current`, cites it, and refuses when the branch is the
repository default and the invocation did not name it. A detached HEAD refuses the same way. The
escape is written into the condition: name the branch, or run `task-workspace`. This is breaking
on purpose, and the refusal is never a dead end.

## Consequences

A run that today commits to `main` without saying so will refuse. Every `--apply` reply now
carries `T_shown`, the post-commit tree hash, and the branch it read. ADR-0163's body is not
edited; only its Status records the partial supersession, per ADR-0166.
