---
activation: model_decision
description: task-init's conditional steps (sandbox write-root preflight, feature-library discovery, per-task worktree isolation, the task branch). Load when one of them fires.
---

# task-init opt-in steps

## When to load this file

`commands/task-init.md` points here instead of carrying these rules inline. Each one fires
on a condition most runs never meet, and inline they held the generated task-init skill near the
ADR-0116 Load ceiling, so the one-slice route (ADR-0225) paid for its own rule by moving them.
Read this file when any of the conditions below holds, and apply the matching rule exactly as
written. When none holds, nothing here applies and task-init behaves as its own file says.

## Sandbox write-root preflight

Conditional; harnesses with a restricted write-root only. WHEN the executing harness sandboxes
writes to a restricted root (Codex CLI today), confirm at init that this task folder lives inside
that writable root, or that both roots (product workspace and task-state repo) were declared to the
harness; on a mismatch, surface the harness guidance in
`wos/editor-mode-mappings.md ## Harness operational quirks` before the first substrate write. Inert
(zero cost) on Claude Code and any harness without a restricted write-root.

## Feature-library discovery

Optional, per ADR-0045. When the task is product work on an existing project with a defined stack
and a notable feature set (lists, camera, forms, keyboard, sheets, navigation), note in the
`## Recommended pipeline` that `feature-library-scout` (or `feature-library-scout-fleet` for more
than 3 feature problems) is a useful early discovery step before `implementation-plan`, to surface
community-vetted per-feature libraries. It is opt-in and additive; do not insert it into the
default pipeline or for non-product tasks.

## Per-task worktree isolation

Opt-in, per ADR-0074. When the user requests worktree isolation AND the target project is a git
repository, do NOT provision the worktree in `task-init` (it stays lean; provisioning lives in
`task-workspace`, D-4). Create the task memory as usual, then add `task-workspace` as the immediate
next step in `## Recommended pipeline` (before discovery) to provision the worktree and branch. When
isolation is not requested, or the project is not a git repo, behave exactly as before: no worktree,
no `## Workspace` section, single-tree default unchanged.

Only the worktree is opt-in. The task branch is not: see the next section. WHEN isolation is
requested, `task-init` SHALL NOT switch the main tree to a task branch, because git refuses to check
out one branch in two working trees; `task-workspace` creates the branch in its worktree and writes the
`Task branch:` line itself.

## Task branch (ADR-0233)

Fires WHEN the run is attended, no `Operating mode: assisted` is declared, worktree isolation is not
requested, and the product codebase is a git repository with a configured remote. Otherwise create no
branch and write no `Task branch:` line; an assisted run keeps the pre-ADR-0233 behavior, where the
person names the branch.

1. Read the current branch (`git -C <path> branch --show-current`) and cite it.
2. A branch other people may already pull is never the task branch. WHEN the current branch is the
   default branch (`origin/HEAD` when it resolves, otherwise `main` or `master`), a detached HEAD, or
   a non-default branch that exists on the remote (`git -C <path> rev-parse --abbrev-ref @{u}`
   succeeds, or `git -C <path> ls-remote --heads <remote> <branch>` prints a line), `task-init` SHALL
   create `task/<task-dir>` from it with `git -C <path> switch -c task/<task-dir>`. Working-tree edits
   carry over; a taken name gets `-2`. Cite the command output.
3. WHEN the current branch is non-default, has no upstream, and `ls-remote` prints nothing, it is a
   local branch nobody else has; `task-init` SHALL record it as the task branch and create nothing.
4. Write `Task branch: <name>` and `Base branch: <the branch it was cut from>` into
   `TASK_STATE.md ## Resume notes`. For a branch recorded under 3, the base is the remote default
   branch. `pr-package` reads `Base branch:` as the draft PR's base.
5. Editor mode. In Ask or Plan mode, do not run the switch: propose the exact command in the output,
   the way `task-workspace` proposes its `git worktree add`, and write no `Task branch:` line, since the
   branch does not exist yet. `branch-commit --apply` creates it later in Agent mode.
