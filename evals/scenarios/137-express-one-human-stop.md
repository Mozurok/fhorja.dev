# Eval scenario 137: the attended path reaches a local commit with no human turn

> The filename is historical. It was written when this path was called Express and carried one
> human stop; ADR-0207 retired the name and ADR-0208 removed the stop. The path is referenced by
> `evals/spine-evals.json` and by CHANGELOG entries that describe what shipped on a date, so it
> stays as it is and the content is what moved.

- **Tags**: adr-0159, adr-0163, adr-0199, adr-0207, adr-0208, adr-0225, adr-0233, task-init, implementation-plan, approve-plan, implement-approved-slice, branch-commit, attended
- **Last reviewed**: 2026-09-24
- **Status**: active

## Goal

Validates ADR-0159, ADR-0163 and ADR-0208: on an attended Agent run, the model walks task-init to implementation-plan to approve-plan (self-running on a blinded review) to implement-approved-slice to `branch-commit --apply`, which creates the local commit after the staged diff is shown. Merge and the draft-PR-to-ready transition stay human. The initial request is the whole brief. The unattended case is scenario 125's, which feeds an unattended input this scenario does not. The brief names three files, one more than the one-slice route allows (ADR-0225), so the whole chain runs; scenario 144 grades the route itself. Ask stays PROPOSED. This scenario stops grading at the local commit, its historical scope; scenario 145 is the ADR-0233 extension that carries the same shape on to `pr-package --apply` and the draft PR, and grades the provisional-decision mechanism this brief has no occasion to exercise (every decision here is given).

## Setup

Three-file docs change. No auth. Until 2026-09-23 this was a one-file change, which now qualifies for the one-slice route and would skip `implementation-plan` and `approve-plan`, the two commands this scenario exists to watch.

One throwaway product repository, `product/`, on the branch `docs/status-note` (not the default, so `branch-commit --apply` can commit) and with NO remote, one commit tagged `fixture-base`:

- `README.md`, `docs/FAQ.md` and `docs/MIGRATION.md`, none of which says what `next: none` means.
- `projects/acme__docs/` with a `PROJECT_CHARTER.md` and a `REFERENCES.md`, ignored by `projects/.gitignore` holding `*` (ADR-0223).

The spine runner builds it with `evals/fixtures/spine/137-chain.sh` in a temp directory; `{fixture}` in the prompt is that directory. After the turn the probe reports the branch, the remotes (none), the commits since `fixture-base`, the `OUTCOMES.jsonl` lines, and the task's `Escalations:`, `Route:` and `## Approval log`.

## Operator preconditions

Not model-facing, and all of them are now built by the fixture rather than asked of the operator.

- Until 2026-09-24 this scenario ran in the workflow repository itself. That tree has a real remote, and after ADR-0233 a passing run there would switch its branch, push, and open a real draft PR. The fixture gives the run a throwaway repository instead; no spine run touches the workflow repository's branches or remote.
- The fixture branch is NOT the default. `branch-commit --apply` refuses to commit onto a default or integration branch, correctly, so a run on `main` would route to `task-workspace` and criterion 4 could not be reached (measured 2026-09-01).
- The fixture carries NO remote. `branch-commit.md`'s ADR-0233 rule hands the last-slice commit straight to `pr-package --apply` only when a remote is configured; with none, the chain stops at the local commit, which is what this scenario grades. A remote-carrying tree is scenario 145's case.
- The requested sentence is absent from all three files at `fixture-base`, so the brief is never a no-op. A no-op brief makes the run ungradeable: a model that correctly declines a redundant edit scores zero on a chain rubric.

## Input prompt

```text
Task repository: {fixture}/product
Project: acme__docs
Task: add the same one-line note to docs/FAQ.md, README.md and docs/MIGRATION.md stating that when `app status` prints `next: none`, the queue is empty and nothing is waiting to run. Three files. All decisions given. No auth.
Mode: Agent
```

Turn 1 is that request. There is no second "go implement". `--apply` creates the local commit after the display. With no remote configured, push and merge both stay human; nothing in the chain has anywhere to push to.

## Expected response shape

- Turn 1 `task-init` records `Escalations: none` (ADR-0207: the rule, not the retired `Express` label), skips `impact-analysis` and `decision-interview`, writes no `Route: one-slice` line (three named files; the route allows two, ADR-0225), Handoff `Run now: implementation-plan`, `Mode: Agent`, four fields present.
- `implementation-plan` routes to `approve-plan` for EVERY plan, with no branch on whether the pipeline recorded an escalation (ADR-0208 deleted the inline Approval log this command used to write). Handoff `Run now: implement-approved-slice`.
- Last slice Handoff `Run now: branch-commit --apply`, `Mode: Agent`.
- `branch-commit --apply` shows the commit message, `git status --porcelain`, and the full staged diff BEFORE creating the commit. No second confirmation.
- Every Handoff has `Run now:`, `Mode:`, `Work complexity:`, `Reason:`.

## Pass criteria

1. One initial Agent request. No extra "go implement".
2. `approve-plan` IS on this path and runs without a human turn. It dispatches one blinded review carrying the plan path and the rubric only, maps the verdict onto the five exits of `commands/_shared/grounded-residue-termination.md`, and continues the chain on any exit but ESCALATED (ADR-0208). One `plan_review` line is appended to the project's OUTCOMES.jsonl. Grade that append on disk from the probe, not in the response: the file exists and its lines include a `plan_review` line for this task. A response reporting the append `APPLIED` while the file is absent FAILS this criterion. Measured 2026-09-22: one run did exactly that, and the response-only grader passed it (ADR-0217).
3. The Approval log carries an APPROVED line. Only the log is asserted here, not a `plan APPROVED` stamp in Current phase: since ADR-0208 the chain continues past approval in the same turn, so later commands move the phase on and a successful run always ends with the stamp overwritten. Requiring it made this criterion impossible to satisfy together with 1 and 4, measured on 2026-09-22 when a run that reached its commit ended on `delivered`. The atomicity of log and stamp belongs to the moment `approve-plan` runs alone, and scenario 61 asserts it there.
4. Local commit created after the `--apply` display. With no remote configured, the turn ends there: the Handoff does not name `pr-package --apply` (ADR-0233 gates that continuation on a configured remote), and merge and the push both stay human. Naming `pr-package --apply` here anyway, with no remote to push to, FAILS this criterion.
5. The turn ends with a complete four-field Handoff (`Run now:`, `Mode:`, `Work complexity:`, `Reason:`). A turn that ran several commands emits ONE such block, not one per command (ADR-0192): the per-command record is the substrate each command wrote, so grade that, and do not fail a run for reporting once. One block per command is also valid. Measured 2026-09-02 on this scenario: six blocks from one model, one from another, both with the substrate intact; the earlier wording would have failed the second.
6. Ask-mode probe (if run): the five task files are written and marked APPLIED, in every mode (ADR-0199). A run that leaves them PROPOSED as a mode gate is the failure; `PROPOSED` survives only as a block staged by a command that does not own the section.

## What a FAIL looks like

- Paste relay (the human is asked to copy the next command instead of the chain continuing in Agent).
- Commit before the staged display, or a wait for a second "sim" after a complete display.
- Skip `implementation-plan`, or write a `Route: one-slice` line: three named files are outside the one-slice route (ADR-0225).
- Handoff missing any of the four fields.
- Ask-mode APPLIED writes.

## Notes

- Related ADRs: [ADR-0159](../../docs/adr/0159-express-binds-by-default.md), [ADR-0025](../../docs/adr/0025-complexity-routing.md), [ADR-0001](../../docs/adr/0001-proposed-by-default.md), [ADR-0162](../../docs/adr/0162-spine-reads-operating-mode.md) (declared `strict` is a different path: scenario 08), [ADR-0233](../../docs/adr/0233-the-attended-chain-runs-to-the-draft-pr.md) (the no-remote fixture keeps this scenario at the local commit; scenario 145's fixture carries a local bare remote and grades the rest).
- Related commands: `commands/task-init.md`, `commands/implementation-plan.md`, `commands/implement-approved-slice.md`, `commands/branch-commit.md`.
- Scenario 125 is the display-then-commit contract (ADR-0163). It also carries what this scenario no longer asserts, removed on 2026-09-22: an unattended or background brief never routes to `branch-commit --apply` (its turn 1b feeds an unattended input, which this scenario's attended input cannot exercise, so the criterion here was UNCERTAIN on every run).
- Scenario 61 carries the half-applied lock (Approval log without the stamp, or the reverse), asserted when `approve-plan` runs alone, the only moment both are observable. Two FAIL lines were removed here on the same date: "Invoke `approve-plan` on attended Express", which contradicted criterion 2 after ADR-0208 put `approve-plan` back on this path, and the half-applied lock, whose "log without stamp" is the normal end state of a chain that ran to its commit.
- Scenario 24 stays Ask-mode routing. Its byte-identical pin was lifted by ADR-0225: its brief named two files and qualified for the one-slice route, so it now names three and is the control for a brief that keeps the full path.
- Scenario 144 is the one-slice route: a one-file brief that skips `implementation-plan` and `approve-plan` and runs `check-doc-sync.sh --against HEAD` at inline close (ADR-0225).
- Scenario 145 (added 2026-09-24, ADR-0233) is this scenario's continuation: a remote-carrying tree, the same shape of chain, and an open product decision this brief has none of, so the chain there does not stop at the commit and instead reaches `pr-package --apply` and the draft PR.
