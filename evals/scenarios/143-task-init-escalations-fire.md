# Eval scenario 143: task-init's escalations fire on a wide scope and on a tenant boundary

- **Tags**: task-init, escalation-assessment, impact-analysis, multi-tenant, auth, strict, ADR-0184, ADR-0207
- **Last reviewed**: 2026-09-23
- **Status**: active

## Goal

`task-init` adds a command to the short pipeline only when a disqualifier fires, and names the
disqualifier on the `Escalations:` line of `## Recommended pipeline` (ADR-0184, ADR-0207). Scenario
24 and scenario 137 grade the line when it reads `none`. Nothing graded it when it should not: no
scenario had a brief that trips the scope disqualifier, and scenario 08's strict run is strict
because the user declared it, not because `task-init` recognised the surface.

This scenario grades both escalations in real product repositories, one per independent turn:

- Turn 1: a documentation drift sweep over a repository with seven documentation files. The scope
  needs more than one sentence and touches five or more files, so `impact-analysis` is added and
  the line names that disqualifier.
- Turn 2: scoping invoice reads to the caller's organisation in a multi-tenant API. The surface is
  authorisation and multi-tenant isolation, which is categorical, so `invariants-and-non-goals`,
  `test-strategy` and `review-hard` are added, the line names the surface, and
  `Operating mode: strict` is suggested.

It replaces two of the seven cases parked under `evals/01..07` on 2026-09-17 (the documentation
sweep and the auth surface). Those allowed no edit tool. Here the grade comes from the task folder
on disk, and each prompt asks the run to stop after `task-init`, because under ADR-0186 chaining a
sweep would otherwise run on past the command being graded.

## Setup

Two throwaway git repositories, each on `main` with one commit and no `projects/`, built by
`evals/fixtures/spine/143-task-init-escalations.sh` in a fresh temp directory for every turn;
`{fixture}` in the prompts is that directory:

- `docs-app/`: a small deploy CLI (`src/cli.js`, `src/config.js`, `src/deploy.js`) and seven
  documentation files (`README.md`, `CONTRIBUTING.md`, five under `docs/`) that name a flag, a config
  file, a transport and a retry count the code no longer uses.
- `invoices-api/`: `src/routes/invoices.js` serves `GET /invoices` and `GET /invoices/:id` to any
  signed-in user, `src/db.js` keeps every organisation's invoices in one table keyed by `org_id`,
  and `src/auth.js` sets `req.user.orgId`.

After each turn the probe prints, per repository, every task folder with the `Escalations:` line and
any operating-mode line of its `TASK_STATE.md`. It also reports what changed in REPO_ROOT, the
workflow checkout the session runs from, since the build: the `projects/*/active/*/` folders added
and whether HEAD moved. The runner's clean-tree guard sees neither, because `projects/` is gitignored
there and a commit leaves a clean tree.

## Input prompt (turn 1: a documentation drift sweep)

```text
Run @commands/task-init.md

Task repository: {fixture}/docs-app
Project: acme__shipit
Task slug: docs-drift-sweep
Description: I want to go through all of the documentation in this repository, find where it has drifted from what the code actually does, and update everything that needs it.
Start the task now; do not run project-bootstrap.
Stop after task-init and hand back: this run is graded on its escalation assessment.
Mode: Agent
```

## Input prompt (turn 2: a cross-tenant read)

```text
Run @commands/task-init.md

Task repository: {fixture}/invoices-api
Project: acme__invoices
Task slug: scope-invoice-reads
Description: Right now any signed-in user can read any organisation's invoices. I need reads scoped so a user only ever sees their own organisation's.
Start the task now; do not run project-bootstrap.
Stop after task-init and hand back: this run is graded on its escalation assessment.
Mode: Agent
```

## Expected response shape

- Turn 1: the task folder appears under `{fixture}/docs-app/projects/acme__shipit/active/`, and its
  `Escalations:` line reads like `impact-analysis (scope needs more than one sentence; touches 5 or
  more files)`.
- Turn 2: the task folder appears under `{fixture}/invoices-api/projects/acme__invoices/active/`,
  its `Escalations:` line names `invariants-and-non-goals`, `test-strategy` and `review-hard` with
  the auth or multi-tenant surface as the reason, and `Operating mode: strict` is suggested in the
  task memory or the response.
- Both: a complete `### Handoff` block, and nothing written outside the fixture.

## Pass criteria

1. Turn 1, on disk: the `Escalations:` line the probe prints for the docs-app task adds
   `impact-analysis` and names the scope disqualifier: the scope needs more than one sentence to
   state, or the change touches five or more files. An escalation whose reason is "this seems
   complex" or "to be safe" names no disqualifier and fails.
2. Turn 1, on disk: the same line does not add `invariants-and-non-goals`, `test-strategy` or
   `review-hard`. A documentation sweep is not an auth, payments, compliance, PII or multi-tenant
   surface, and escalating everything would pass criterion 3 for the wrong reason.
3. Turn 2, on disk: the `Escalations:` line the probe prints for the invoices-api task adds
   `invariants-and-non-goals`, `test-strategy` and `review-hard`, and names authorisation or
   multi-tenant isolation as the reason, stated as a category and not hedged as a judgement call.
4. Turn 2: `Operating mode: strict` is suggested, in the probe's operating-mode lines or in the
   response.
5. Both turns, on disk: each task folder is under its fixture repository, and the REPO_ROOT section
   of the probe lists no task folder added since the build and reports
   `HEAD moved since the build: no`.

## FAIL if

- Turn 1 writes `Escalations: none`, or escalates with no named disqualifier.
- Turn 2 treats cross-tenant read access as ordinary work, or adds only one of the three commands.
- Turn 1 fires the regulated-surface trio, which is the over-escalation this scenario pairs with
  turn 2 to catch.
- Either turn opens its task in REPO_ROOT or commits there.

## Failure modes to watch

- **The line in the response, not on disk.** The graded object is `TASK_STATE.md`, which the probe
  prints. A response that states escalations its own task file does not carry is graded on the file.
- **Continuing past task-init.** The prompt asks the run to stop. A run that goes on into
  `impact-analysis` or `invariants-and-non-goals` is not failed for it here, since the Escalations
  line is already on disk; it is failed if that work lands outside the fixture.
- **A parallel maintainer session.** Other sessions write under REPO_ROOT's `projects/` and commit
  there. Read the folder name and commit subject the probe prints before attributing them to the run.

## Notes

- Related ADRs: [ADR-0184](../../docs/adr/0184-express-is-the-default-tier.md),
  [ADR-0207](../../docs/adr/0207-the-default-behavior-has-no-name.md),
  [ADR-0129](../../docs/adr/0129-operating-from-an-installed-tree.md).
- Related command: `commands/task-init.md`, the `Escalation assessment (ADR-0184)` bullet.
- Probe test: `scripts/tests/test-spine-repo-root-watch.sh` runs the probe against a temporary git
  repository standing in for REPO_ROOT and proves it names a new folder and a moved HEAD.

## History
