# TASK_PREFERENCES

Per-task delivery preferences that delivery commands consume (`pr-package`, `branch-commit`).
Copy into a task folder when a durable preference surfaces; gitignored (lives under `projects/`,
per ADR-0007). Edit by hand: commands READ this file, they do not write it.

This is the consume side of `capture-observation`. A durable cross-command preference recorded
here is honored by the delivery commands, unlike a free-form `## Observations` bullet, which no
command reads back. (Careers-page dogfooding 2026-06-23: a captured "git add -A" preference was logged
to Observations and then ignored by pr-package; this file is where consumable preferences live.)

## Git staging
- Stage explicit paths only. The `git add -A` / `.` / `*` guardrail is absolute: a global Claude
  Code hook (`scripts/block-git-add-all.sh`) blocks it, and it contaminates commits with local
  tooling files. `pr-package` stages every task file by explicit path, so a wildcard is never
  needed. There is no per-task opt-in to `-A`.

## Delivery
- Base branch: [default per SOURCE_OF_TRUTH.md / PROJECT_CHARTER.md]
- PR template: [path to the product repo's `.github/PULL_REQUEST_TEMPLATE.md`, or `none`]
- Commit convention: [e.g. conventional-commits; default per repo]
