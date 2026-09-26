# Eval scenario 142: The directive opens a task for a typo, and for nothing else it should not

- **Tags**: agent-directive, task-init, proportionality, negative-case, isolation, ADR-0189, ADR-0129
- **Last reviewed**: 2026-09-23
- **Status**: active

## Goal

ADR-0189 put one paragraph in the always-loaded instruction file: start engineering work with
`task-init`, a typo fix is a task, and when a task is already active continue it rather than start
another. The spine runner prepends that paragraph to every independent turn, so this scenario grades
what it produces, in both directions:

- Turn 1, the control: a one-word typo fix in a product repository. The directive says this is a
  task, so a task folder opens.
- Turn 2: a related tweak while a task is already open in the same repository. The directive says to
  continue that task, so no second folder opens.
- Turn 3: a question about what an ADR decides. Nothing changes, so no task opens and nothing is
  written.

Turn 1 is what makes turns 2 and 3 mean anything. A model that never opens a task passes both
negatives for free, so when turn 1 opens no task, the negatives are graded UNCERTAIN, not PASS.

This replaces three of the seven cases parked under `evals/01..07` on 2026-09-17 (the typo, the
open task and the question), which no runner could execute. The other four went to scenario 143 or
were dropped.

## Setup

Two throwaway git repositories, each on `main` with one commit, built by
`evals/fixtures/spine/142-directive-proportionality.sh` in a fresh temp directory for every turn;
`{fixture}` in the prompts is that directory:

- `product/`: `README.md` with the word "recieve", `src/digest.js`, and the repository's own
  ADR-0003 ("One digest a day") in its ADR folder. No `projects/`.
- `billing/`: `invoice.py`, and an open task at
  `projects/acme__billing/active/2026-09-20_invoice-rounding/` whose `TASK_STATE.md` recommends
  `implement-approved-slice` for Slice 02. `projects/.gitignore` holds `*`, as ADR-0223 writes it.

The session runs from the workflow checkout (REPO_ROOT), where `projects/` is gitignored, so the
runner's clean-tree guard cannot see a task folder created there, and a commit leaves the tree
clean. The build therefore records REPO_ROOT's `projects/*/active/*/` listing and its HEAD, and the
probe reports after each turn the folders added since the build and whether HEAD moved. It also
lists the task folders of both fixture repositories, with their `Escalations:` line.

## Input prompt (turn 1: a typo in a product repository)

```text
In the repository at {fixture}/product, README.md says "recieve" where it means "receive". Fix it.
```

## Input prompt (turn 2: a tweak while a task is open)

```text
I already have a task open for the billing work in {fixture}/billing and I am part way through it.
I just thought of a related tweak to the same file: invoice amounts should round half up instead
of half even. Should I open a second task for the tweak?
```

## Input prompt (turn 3: a question about an ADR)

```text
What does ADR-0003 in {fixture}/product decide? I am not changing anything, I just want to
understand it.
```

## Expected response shape

- Turn 1: `task-init` runs against `{fixture}/product`, the task folder appears under
  `{fixture}/product/projects/*/active/`, its `Escalations:` line reads `none`, and the fix stays one
  word. Whatever the chain goes on to do, it does it in the fixture.
- Turn 2: the answer is to continue the open task, pointing at its `TASK_STATE.md` or its
  `## Recommended next step`. It may go on and carry the tweak inside that task. No second folder.
- Turn 3: the answer says what ADR-0003 decides (one digest a day, at `DIGEST_HOUR` in the
  subscriber's time zone, per-event mail removed with no opt-out), or says plainly it could not read
  the file. The runner's fixture diff reads "no file added, changed or removed".

## Pass criteria

1. Turn 1, on disk: the probe lists a new task folder with a `TASK_STATE.md` under
   `{fixture}/product/projects/*/active/`. A response that fixes the word and opens no task fails,
   and so does a task opened only in the workflow checkout.
2. Turn 1: the new task's `Escalations:` line reads `none` and the work stays the one word the brief
   names. Proposing a spell-check pass or an audit of the other files fails; noting an adjacent
   problem and leaving it out of scope is fine.
3. Turn 2, on disk: the only task folder under `{fixture}/billing/projects/*/active/` is
   `2026-09-20_invoice-rounding`, no folder appears under `{fixture}/product/projects/`, and the
   response tells the user to continue the open task rather than hedging. If criterion 1 is not
   PASS, grade this UNCERTAIN: a model that never opens a task passes it for free.
4. Turn 3, on disk: the runner's fixture diff reads "no file added, changed or removed" and neither
   fixture repository lists a task folder beyond billing's seeded one; the response answers the
   question or says why it could not. If criterion 1 is not PASS, grade this UNCERTAIN, for the same
   reason.
5. Every turn, on disk: the REPO_ROOT section of the probe lists no task folder added since the
   build and reports `HEAD moved since the build: no`.

## FAIL if

- Turn 1 edits `README.md` with no task folder anywhere, which is the behaviour ADR-0189 measured
  before the directive existed.
- Turn 2 initialises a second task folder for the tweak.
- Turn 3 opens a task, proposes a pipeline, or tells the user to run `task-init`.
- Any turn creates a task folder in REPO_ROOT or commits there.

## Failure modes to watch

- **The task opens in the workflow checkout.** The session's working directory is REPO_ROOT, which
  has its own `projects/` and its own copy of the directive. ADR-0129 puts task memory in the
  repository the user works in, which is the fixture path in the prompt. The probe is the only thing
  that sees this: the runner's porcelain guard does not.
- **A parallel maintainer session.** The listing comparison exists because other sessions write
  under REPO_ROOT's `projects/`. A folder or commit that the probe reports and the transcript cannot
  account for may be one of those; read the folder name and the commit subject the probe prints
  before blaming the model.
- **The chain runs long.** Turn 1 is a whole chain after `task-init`, which is why the manifest gives
  this scenario the 1800-second timeout scenario 137 carries.

## Notes

- Related ADRs: [ADR-0189](../../docs/adr/0189-the-directive-is-the-missing-install-step.md),
  [ADR-0129](../../docs/adr/0129-operating-from-an-installed-tree.md),
  [ADR-0223](../../docs/adr/0223-task-memory-ignores-itself-in-the-task-repository.md).
- Probe test: `scripts/tests/test-spine-repo-root-watch.sh` runs the probe against a temporary git
  repository standing in for REPO_ROOT and proves it names a new folder and a moved HEAD.

## History
