# ADR-0074: Opt-in per-task git worktree isolation

- **Status**: Accepted
- **Date**: 2026-07-01
- **Tags**: git-worktree, workspace-isolation, parallel-tasks, task-lifecycle, opt-in, additive, task-workspace, task-close

## Context

The WOS holds many concurrent task folders (`portfolio-review` is a board across every active task), but every execution command assumes one product working tree on one branch. Even multi-repo support serializes per workspace (`wos/multi-repo-support.md` I2: "No concurrent multi-workspace execution"). So two tasks that touch the same repository collide: starting task B disturbs task A's working tree and checked-out branch. The existing worktree machinery (`implement-fleet`, ADR-0041) isolates parallel slices inside one task and is ephemeral, torn down at the wave merge; it does not give a human a durable per-task workspace.

External research for the task that produced this ADR (`EXTERNAL_RESEARCH.md`) found three independent tools (the Codex app, shadcn/improve, Superpowers) that use git worktrees for parallel isolation, which confirms the pattern. All three isolate ephemeral execution behind an automated merge gate, closer to `implement-fleet` than to a durable per-task worktree, so the durable, human-owned variant is the novel part. The git mechanics are stable and documented (the git-scm `git worktree` man page, captured in `REFERENCES.md`): a branch checks out in only one worktree at a time, a new worktree starts from committed HEAD, `refs/` and config are shared while HEAD and the index are per-worktree, and only clean worktrees remove without `--force`.

## Decision

Add opt-in, git-gated per-task worktree isolation, recorded as decisions D-1 through D-6 in the task's `DECISIONS.md`.

- Provision (D-1, D-4). A new dedicated command, `task-workspace`, provisions one git worktree and one task branch for an opted-in task, persisting for the whole life of the task. It runs standalone to retrofit a task already in progress, and `task-init` can invoke it during initialization. Provisioning lives in this command, not inside `task-init`, to keep `task-init` lean and give the lifecycle a single home.
- Opt-in and git-gated (D-2). When isolation is not requested, or the project is not a git repository, every command behaves exactly as today (single working tree, single branch, no overhead). This mirrors the multi-repo v1 additive posture.
- Distinct from fleet (D-3). Per-task worktrees stay separate from the slice-level worktrees `implement-fleet` creates. When a task worktree is active, fleet slice worktrees branch from the task branch rather than the repository base, so the fleet integration gate still holds.
- Teardown (D-5). WHEN a task with a provisioned worktree is closed, `task-close` runs `git worktree remove` followed by `git worktree prune` for that task's worktree.
- Teardown guard (D-6). IF the worktree has uncommitted changes or the task branch is unmerged, `task-close` halts the removal and surfaces the state instead of forcing it. No `--force`.

The `SOURCE_OF_TRUTH.md` schema gains an optional worktree-path and task-branch field, documented in the WOS spec and `wos/multi-repo-support.md`. Conventions: command name `task-workspace`; the branch and worktree are named from the full task-folder name `YYYY-MM-DD_<task-slug>` (the `active/` directory name, not the bare slug) for cross-date uniqueness, giving task branch `task/YYYY-MM-DD_<task-slug>` and worktree location `../<repo>-worktrees/YYYY-MM-DD_<task-slug>`.

## Consequences

- `count:commands` increments by one (`task-workspace`). The command is registered in all four registries and its generated skill is rebuilt in the consolidation slice, not here.
- Additive. The default single-tree path is byte-unchanged; the feature is opt-in only, so the common single-task case pays nothing.
- `task-close` gains a teardown responsibility gated by the unclean-or-unmerged guard. Teardown is the make-or-break the research flagged: without it, stale worktrees accumulate.
- The feature applies to any git-backed product repo. The WOS markdown meta-repo does not opt in, since its tasks are folders, not code branches.
- Disk cost scales with the number of active worktrees (N working copies plus their build caches). Acceptable because it is opt-in per task and the operator chooses when to pay it.

## Alternatives considered

- NO_OP, rely on `implement-fleet` plus manual git. Rejected: fleet isolation is ephemeral and slice-scoped, so it gives no durable per-task workspace, and the reported blocking is real (many concurrent task folders serialize on one working tree).
- Docs-only recipe (a manual `git worktree add` recipe plus a `SOURCE_OF_TRUTH.md` convention). Rejected: no teardown safety net, so stale worktrees accumulate; the research named automated teardown as the deciding factor, and a docs-only path leaves that burden on the user.
- Extend `task-init` with a flag instead of a dedicated command. Rejected: it loads `task-init` with git lifecycle and cannot retrofit a task already in progress. A dedicated command keeps `task-init` lean and is reusable standalone.
