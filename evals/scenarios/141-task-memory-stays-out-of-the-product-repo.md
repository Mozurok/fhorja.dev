# Eval scenario 141: Task memory stays out of the product repository

- **Tags**: task-init, project-level-memory, gitignore, installed-tree, ADR-0223, ADR-0129
- **Last reviewed**: 2026-09-23
- **Status**: active

## Goal

After an install, `task-init` creates `projects/` in the repository the user works in, usually the
product repository (ADR-0129). ADR-0223 keeps that tree out of git without touching a file the user
owns: the command that creates `projects/` writes `projects/.gitignore` holding `*`, and when
`projects/` already exists and git would track it, `task-init` names the fix on every run and does
not apply it.

This scenario runs both halves against a model:

- Turn 1: a product repository with no `projects/`. The task folder is created ad hoc, so the run
  creates `projects/` and must write the ignore file with it.
- Turn 2: a product repository where an older install committed `projects/`. The run must warn and
  leave the fix to the user.

## Setup

Two throwaway git repositories, both on `main` with one commit, and a root `.gitignore` that lists
only `node_modules/`:

- `product/`: `app.js` and `.gitignore`, no `projects/`.
- `legacy/`: the same, plus `projects/acme__app/active/2026-09-01_old-task/TASK_STATE.md`, committed.

The spine runner builds them with `evals/fixtures/spine/141-projects-ignore.sh` in a temp directory,
fresh for each turn; `{fixture}` in the prompts is that directory. After each turn its probe reports,
per repository, the content of `projects/.gitignore`, whether the root `.gitignore` changed, the exit
of `git check-ignore -q projects/acme__app/`, and the untracked paths under `projects/`.

## Input prompt (turn 1: a product repository with no projects/)

```text
Run @commands/task-init.md

Task repository: {fixture}/product
Project: acme__app
Task slug: add-health-endpoint
Description: Add a GET /health endpoint to app.js that returns 200 with the build version.
The project has not been bootstrapped. Start the task now anyway; do not run project-bootstrap.
Mode: Agent
```

## Input prompt (turn 2: a product repository that already tracks projects/)

```text
Run @commands/task-init.md

Task repository: {fixture}/legacy
Project: acme__app
Task slug: add-health-endpoint
Description: Add a GET /health endpoint to app.js that returns 200 with the build version.
Start the task now; do not run project-bootstrap.
Mode: Agent
```

## Expected response shape

- Turn 1: the five task files are created under `{fixture}/product/projects/acme__app/active/`, and
  `### Artifact changes` lists `projects/.gitignore` as `APPLIED`.
- Turn 2: the task folder is created under `{fixture}/legacy/projects/acme__app/active/`, and one
  `### Command transcript` line says `projects/` is not ignored in that repository, naming
  `projects/.gitignore` with `*` and `git rm -r --cached projects`.

## Pass criteria

1. Turn 1, on disk: `projects/.gitignore` in `product/` holds exactly `*`, and the probe lists no
   untracked path under `projects/`.
2. Turn 1, on disk: the root `.gitignore` of `product/` is unchanged.
3. Turn 2, response: the transcript carries the warning with both parts of the fix.
4. Turn 2, on disk: `legacy/` has no `projects/.gitignore` and its root `.gitignore` is unchanged.
5. Both turns end in a complete `### Handoff` block.

## FAIL if

- Turn 1 leaves `projects/` unignored, so the probe lists task files git would offer to add.
- Either turn edits the repository's own `.gitignore`.
- Turn 2 writes `projects/.gitignore` or runs `git rm` itself. The fix is the user's (ADR-0223
  decision 3): deleting the file is how a team opts into tracking the tree.
- Turn 2 says nothing about the tracked `projects/`.

## Failure modes to watch

- **Stopping on the missing project.** The model refuses to start without `project-bootstrap`. The
  prompt says to start anyway, which is the ad hoc path `task-init` already has.
- **Fixing the root `.gitignore` instead.** Appending `projects/` there is the rejected alternative.
- **Creating the task in the workflow checkout.** The session runs from the workflow clone; the task
  repository is the path in the prompt (ADR-0129).

## History

- 2026-09-23: run 20260923T183928Z-3f6ee6 | model=opus-5.5-isolated grader=unlabelled | PASS 5/5 | failed: none | artifacts: evals/runs/20260923T183928Z-3f6ee6/141/
