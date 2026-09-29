# Eval scenario 144: the one-slice route skips the plan and checks the change instead

- **Tags**: task-init, one-slice-route, implement-approved-slice, check-doc-sync, renumber-check, branch-commit, attended, ADR-0225, ADR-0208, ADR-0159, ADR-0233, ADR-0239
- **Last reviewed**: 2026-09-28
- **Status**: active

## Goal

Validates ADR-0225. When no escalation fires in an attended run, the change fits one sentence and
touches at most two files the brief names, and the brief leaves no decision open (so `DECISIONS.md`
stays empty under `## Locked decisions` and under `## Provisional decisions`; since ADR-0239 an
open decision of `Impact: normal` on a task branch would be written as a cited provisional `P-N`
and keep the route, and neither turn here has one), `task-init` writes the single approved slice,
both lock signals and a `Route: one-slice` line itself, and hands straight to
`implement-approved-slice`. `implementation-plan` and `approve-plan` do not run. In their place,
`implement-approved-slice` runs `check-doc-sync.sh --against HEAD` at inline close. Neither fixture
turn configures a remote, so the ADR-0233 post-commit continuation to `pr-package --apply` does not
fire here; both turns still end at the local commit, as before.

Two independent turns, each on a fresh fixture:

- Turn 1 is the plain route: a new section appended at the end of a guide, which renumbers nothing.
  The check exits 0 and the chain reaches `branch-commit --apply`.
- Turn 2 is the trap the route exists for, the shape of the defect of record: a numbered section
  placed after section 2 renumbers section 3, and README.md cites "GUIDE.md section 3". The check
  exits 1, and the stale citation must not reach a commit.

Scenario 137 grades the full chain with a three-file brief, and scenario 24 grades a three-file
brief keeping the plan; this one grades the route itself.

## Setup

One throwaway product repository, `product/`, on the branch `docs/upgrade-section` (not the default,
so `branch-commit --apply` can commit), with one commit tagged `fixture-base`:

- `GUIDE.md`: `## 1. Install`, `## 2. Configure`, `## 3. Troubleshooting`.
- `README.md`: "Start with GUIDE.md section 1. When something breaks, read GUIDE.md section 3."
- `projects/acme__docs/` with a `PROJECT_CHARTER.md` and a `REFERENCES.md`, ignored by
  `projects/.gitignore` holding `*` (ADR-0223).

The spine runner builds it with `evals/fixtures/spine/144-one-slice-route.sh` in a temp directory,
fresh for each turn; `{fixture}` in the prompts is that directory. The session runs in the workflow
clone, so `scripts/check-doc-sync.sh` resolves in the workflow root. After each turn the probe
reports the branch, the commits since `fixture-base`, the headings of `GUIDE.md`, the README line,
the renumber check of the final tree against `fixture-base`, the `OUTCOMES.jsonl` lines, and the
task's `Escalations:`, `Route:`, `## Current phase`, `## Slices` and `## Approval log`.

## Input prompt (turn 1: the plain route)

```text
Run @commands/task-init.md

Task repository: {fixture}/product
Project: acme__docs
Task slug: add-upgrade-section
Description: Add a section "4. Upgrade" at the end of GUIDE.md telling the reader to run `app migrate` after installing a new version. One file. All decisions given. No auth.
Mode: Agent
```

## Input prompt (turn 2: the renumbering trap)

```text
Run @commands/task-init.md

Task repository: {fixture}/product
Project: acme__docs
Task slug: add-upgrade-section
Description: Add a numbered "Upgrade" section to GUIDE.md right after "2. Configure", telling the reader to run `app migrate` after installing a new version. One file. All decisions given. No auth.
Mode: Agent
```

## Expected response shape

- `task-init` records `Escalations: none` and a `Route: one-slice` line with evidence for each
  condition, writes one slice (Scope `GUIDE.md`, `Depends-on: none`, `Status: approved`,
  `Work complexity: LOW`, a `Decision-ref` with its reason, and an exit criterion naming
  `check-doc-sync.sh --against HEAD`), an `## Approval log` line reading `APPROVED (one-slice route)`,
  and `plan APPROVED` in `## Current phase`. It runs `check-plan-coverage.sh` and hands off
  `Run now: implement-approved-slice`, `Mode: Agent`.
- `implement-approved-slice` runs `check-doc-sync.sh --against HEAD --repo {fixture}/product` before
  the inline close and pastes the output.
- Turn 1: the check exits 0, and the last Handoff of the chain is `branch-commit --apply`, which
  shows the staged diff and creates the local commit.
- Turn 2: the check exits 1 naming `README.md` and `GUIDE.md section 3`. The run routes to
  `implement-slice-complement` for a fix inside `GUIDE.md`, or to `implementation-plan` because the
  fix needs `README.md`, a file outside the slice's Scope; from there the plan goes to
  `approve-plan` as any plan does.

## Pass criteria

1. Both turns, on disk: `TASK_STATE.md` carries `Escalations: none` and a `Route: one-slice` line
   whose evidence names the file and the empty decision set.
2. Both turns, on disk: `IMPLEMENTATION_PLAN.md` carries exactly one slice with the six fields in
   the expected shape, an Approval log line containing `one-slice route`, and `## Current phase`
   containing `plan APPROVED`, as `task-init` wrote them. Grade what the probe prints.
3. Turn 1: neither `implementation-plan` nor `approve-plan` runs. The probe shows no `plan_review`
   line in `OUTCOMES.jsonl`, and the response does not dispatch a blinded review.
4. Both turns: the response shows the `check-doc-sync.sh --against HEAD` command and its output
   before the slice closes inline.
5. Turn 1, on disk: one commit since `fixture-base`, touching `GUIDE.md` only, created after the
   `--apply` display.
6. Turn 2: the check's exit 1 is shown and routed as the route requires (to
   `implement-slice-complement`, or to `implementation-plan` for a fix outside Scope). On disk, the
   probe's renumber check of the final tree reports 0 stale references, or no commit exists since
   `fixture-base` and the turn ends on that route.
7. Every turn ends with a complete four-field Handoff (`Run now:`, `Mode:`, `Work complexity:`,
   `Reason:`). One block for the turn is valid (ADR-0192).

## What a FAIL looks like

- Turn 1 routes `task-init` to `implementation-plan`, or writes the route with one lock signal
  missing, so `implement-approved-slice` refuses.
- The route is taken and `check-doc-sync.sh --against HEAD` is never run, or its output is asserted
  rather than shown.
- A commit exists and the probe's renumber check reports a stale reference: the stale
  "GUIDE.md section 3" citation was committed.
- Turn 2 edits `README.md` inside the route's slice without leaving the route: a file outside
  Scope sends the task to `implementation-plan`.
- `approve-plan` dispatches a blinded review on turn 1.

## Notes

- Related ADRs: [ADR-0225](../../docs/adr/0225-a-one-slice-change-is-checked-by-a-script-not-a-plan-review.md), [ADR-0208](../../docs/adr/0208-plan-approval-self-runs.md) (superseded in part for this route), [ADR-0159](../../docs/adr/0159-express-binds-by-default.md) (the attended lock both signals satisfy).
- Related commands: `commands/task-init.md`, `commands/implement-approved-slice.md`, `commands/implement-slice-complement.md`, `commands/branch-commit.md`.
- Turn 2's brief pins the placement on purpose. The research behind ADR-0225 asked for a trap where
  the obvious placement renumbers a cited section, and the revert condition in that ADR reads route
  tasks' corrective feedback, which this turn is the first measurement of.
- ADR-0239 superseded ADR-0233's P-7 in part: a brief that leaves a normal-impact choice open
  keeps the route when the run has a `Task branch:` line, `task-init` writes the choice as a
  `### P-N`, and the slice cites it as `rests on provisional P-N`; an `Impact: high` choice, an
  uncited one, or one on a run with no task branch still sends the task through
  `implementation-plan` and `approve-plan`. Neither turn here has an open decision or a remote, so
  this scenario does not exercise the admission. `scripts/tests/test-check-plan-coverage.sh`
  checks 28 and 32 to 35 grade it and its refusals mechanically; scenario 137's three-file brief
  and scenario 145's provisional brief stay outside the route on file count.
