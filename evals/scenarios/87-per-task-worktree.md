# Eval scenario 87: per-task git worktree isolation (task-workspace provision + task-close teardown)

- **Tags**: ADR-0074, task-workspace, task-close, git-worktree, workspace-isolation, opt-in, git-gated, additive
- **Last reviewed**: 2026-07-01
- **Status**: active

## Goal

Validates **ADR-0074** as delivered by `task-workspace` (provision) and `task-close` (teardown). Given a git-backed project and a task that opts in, `task-workspace` must provision exactly one durable git worktree and a `task/<task-slug>` branch off the base, record them in a `## Workspace` section in `SOURCE_OF_TRUTH.md`, and never tear down. On a non-git project, or when isolation is not requested, it must be a no-op with a trace. At closure, `task-close` must remove and prune the worktree when the tree is clean and merged, and halt (never `--force`) when it is unclean or unmerged. The feature is additive: a task that does not opt in behaves exactly as today.

This exercises:

- The git-gate: a non-git project returns `NO_OP_TRACE` and no worktree is created.
- The opt-in rule: a worktree is provisioned only on an explicit request, never as a side effect.
- The naming conventions: branch `task/<task-slug>`, worktree `../<repo-basename>-worktrees/<task-slug>`.
- The branch-collision rule: a branch already checked out in another worktree is not `--force`d; the collision is surfaced.
- The `## Workspace` substrate write into `SOURCE_OF_TRUTH.md`.
- The teardown split: `task-workspace` never removes; `task-close` runs `git worktree remove` + `prune` with the unclean/unmerged halt guard.
- The fleet distinction: per-task worktrees are not `implement-fleet` slice worktrees; when a task worktree is active, fleet slice worktrees branch off the task branch.

## Setup

A git-backed product repo at `~/code/acme-app` (base branch `main`) with an active task `2026-07-01_add-search`. `SOURCE_OF_TRUTH.md` names the repo and base branch and has no `## Workspace` section yet.

## Input prompt (turn 1: provision, opt-in, git repo)

```text
Run @commands/task-workspace.md for the active task 2026-07-01_add-search.
Action: provision. Isolation: requested. Repo: ~/code/acme-app (base main).
Mode: Agent
```

## Input prompt (turn 2: same command on a non-git project)

```text
Run @commands/task-workspace.md for a task whose target project is a plain folder (not a git repo).
Action: provision.
Mode: Agent
```

## Input prompt (turn 3: close the task with the worktree present)

```text
Run @commands/task-close.md for 2026-07-01_add-search. Done-conditions met (merged). The worktree is clean.
Mode: Agent
```

## Expected response shape (turn 1: provision)

- Confirms the git-gate passed, then provisions with `git worktree add -b task/2026-07-01_add-search ../acme-app-worktrees/2026-07-01_add-search main`.
- Runs the branch-collision check before `add`; does not pass `--force`.
- Writes a `## Workspace` section to `SOURCE_OF_TRUTH.md` (worktree path, task branch `task/2026-07-01_add-search`, base branch `main`) with a substrate transaction header and one audit line.
- Never tears anything down; routes forward to the task's discovery step.

## Expected response shape (turn 2: non-git)

- Returns `NO_OP_TRACE` naming the git-gate; creates no worktree, writes no `## Workspace` section; the task continues on the single working tree unchanged.

## Expected response shape (turn 3: close)

- Reads the `## Workspace` section, checks the worktree is clean and the branch merged, then runs `git worktree remove ../acme-app-worktrees/2026-07-01_add-search` and `git worktree prune`.
- Would halt the removal and surface the state (no `--force`) if the tree were unclean or unmerged.
- Proceeds with the normal archive move; a task without a `## Workspace` section closes exactly as today.

## Failure signals

- Provisioning without an explicit opt-in, or on a non-git project; passing `--force` on `add` or `remove`; `task-workspace` removing a worktree (teardown belongs to `task-close`); no `## Workspace` section written on a successful provision; conflating the per-task worktree with an `implement-fleet` slice worktree; or a non-opted task's default flow changing.
