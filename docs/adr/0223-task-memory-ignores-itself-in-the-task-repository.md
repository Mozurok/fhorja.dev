# ADR-0223: Task memory ignores itself in the task repository

- **Status**: Accepted
- **Date**: 2026-09-23
- **Tags**: project-level-memory, gitignore, installed-tree, task-init, project-bootstrap, adr-0007, adr-0129

## Context

ADR-0007 made `projects/` per-user memory that never enters a shared history. In the workflow
checkout that holds because the checkout's own `.gitignore` lists `projects/`. ADR-0129 then
recorded the installed layout: the user's tasks live under a `projects/` tree inside whatever
repository they are working in, and README.md tells them to open their product repository and run
`task-init` there. Nothing in that repository ignores `projects/`.

So an installed user who runs `git add .` in their product repository commits their task memory,
which can hold client names, decisions and research, and pushes it with the code. The docs said
`projects/` "is gitignored" without naming the layout, which made the gap read as covered. It was
found on 2026-09-23 while writing the site's usage guide, and missed by the documentation audit the
day before.

## Decision

1. The command that creates the `projects/` directory in a task repository writes
   `projects/.gitignore` in the same batch, holding the single line `*`. Today that is `task-init`,
   when it creates a project folder ad hoc, and `project-bootstrap`. The rule is one shared block,
   `commands/_shared/projects-ignore.md`, so both carry the same text.
2. No command edits the repository's own `.gitignore`.
3. No command writes `projects/.gitignore` into a `projects/` that already exists. Deleting the
   file is how a user opts into tracking the tree, and a command that put it back would overrule
   that choice.
4. When `projects/` already exists, `task-init` runs
   `git -C <task repository> check-ignore -q projects/<client>__<project>/` once. Exit 1 prints one
   transcript line naming the fix, including `git rm -r --cached projects` for files already
   committed. Exit 0 and exit 128 (not a git repository) print nothing. It warns on every run and
   never writes the fix.

## Why a file inside projects/

A `*` pattern in `projects/.gitignore` ignores every path below it, the file included. Checked in
a scratch repository on 2026-09-23: `git check-ignore -v` attributed both `projects/.gitignore` and
a nested `TASK_STATE.md` to `projects/.gitignore:1:*`, and `git add projects` staged nothing. The
product repository's history and its tracked files are untouched, and every existing statement that
calls `projects/` gitignored becomes true in both layouts without being rewritten.

## Alternatives rejected

- **Append `projects/` to the repository's `.gitignore`.** Visible to the team and conventional,
  but it writes a file the user owns, and the change lands in their next product commit.
- **Warn only.** Writes nothing, and leaves the gap for anyone who does not read the line.
- **Have the installer write it under `--project PATH`.** Covers only that install path. The
  default install mirrors skills to user-level directories and never sees the product repository.
- **Warn once per project and record it.** Less noise, but it needs stored state for a one-call
  check. The maintainer chose the stateless warning.

## Consequences

- Positive: a fresh install keeps task memory out of the product history with no step for the user.
- Negative: the rule is invisible to teammates, since nothing tracked records it. A team that wants
  `projects/` in git deletes one file.
- Neutral: an ignore rule does not untrack files already committed. Decision 4 is what reaches
  those installs; the new file does not.
- Measured by `evals/scenarios/141-task-memory-stays-out-of-the-product-repo.md` and the structural
  check `check_projects_ignore_in_creators`.
