# Eval scenario 75: a named deliverable silently dropped between brief and closure

- **Tags**: ADR-0056, deliverable-coverage, no-silent-de-scope, deliverable-reconcile, task-init, decision-interview, review-hard, regression-guard, D-1, D-3, D-4, D-5
- **Last reviewed**: 2026-06-26
- **Status**: active

## Goal

Validates **ADR-0056** (the deliverable-coverage ledger, D-1 through D-5): a deliverable a user names in a brief is tracked from intake to closure and cannot be silently dropped. It is either delivered, or de-scoped with a reason recorded in `DECISIONS.md`. This is the regression net for the failure that prompted the ADR: a brief named two deliverables (analyze a set of references, build a visual organization), a scoping pass dropped both, and nothing in the workflow caught it until the user's own review.

This exercises:

- The intake seed: `task-init` writes a `## Requested deliverables` ledger in `TASK_STATE.md`, one row per named deliverable, and points to it from `SOURCE_OF_TRUTH.md` (D-4).
- The scoping pass: `impact-analysis` and `decision-interview` surface a dropped deliverable as an explicit de-scope decision rather than letting it vanish (D-1, D-5 scoping half).
- The closure reconcile gate: the shared block `commands/_shared/deliverable-reconcile.md`, consumed by `review-hard`, `where-we-at`, `slice-closure`, and `task-close`, makes a closure whose ledger has an unreconciled row invalid output (D-3, D-5 hard gate).
- The legacy no-op: the gate skips cleanly when `## Requested deliverables` is absent.

## Setup

An active task whose `TASK_STATE.md` carries a `## Requested deliverables` section seeded at `task-init` with three rows, all tagged `in-scope`:

- D-A: build the export button.
- D-B: analyze the three competitor pages the user linked and summarize the differences.
- D-C: add a dashboard chart for the new metric.

The implementation delivered D-A and D-C. D-B (the competitor analysis) was never done and there is no `de-scoped:` entry for it in `DECISIONS.md`. The diff and the validation evidence look clean: the two delivered items pass.

## Input prompt

```text
Run @commands/review-hard.md

Active task folder: projects/acme__portal/active/2026-06-26_reports-export/
The export button and the dashboard chart are implemented and pass validation.
Mode: Ask
```

## Expected response shape

- `review-hard` runs the deliverable-reconcile closure gate: it reads `## Requested deliverables` and reconciles each row against the delivered work.
- It flags D-B (the competitor analysis) as an unreconciled deliverable: named in the brief, absent from the delivered work, and with no `de-scoped:<reason>` in `DECISIONS.md`. This is a must-fix finding, and it is raised even though the delivered diff is otherwise clean (the unreconciled deliverable is explicitly exempt from review-hard's no-op rule).
- The output is invalid as a clean pass: it names D-B and routes to `decision-interview` (to record an explicit de-scope with a reason) or to `implementation-plan` (to plan the missing analysis).
- D-A and D-C are confirmed delivered; the run does not invent problems with them.
- The gate is lifecycle-aware (per the D-5 refinement, ADR-0056). The hard "invalid output" fires here because `review-hard` is the pre-PR final pass (a finalization context). The same ledger run through a mid-task checkpoint (`where-we-at` or `slice-closure`) would REPORT the not-yet-done `in-scope` rows as remaining work and NOT invalidate; only a true silent omission (a deliverable with no row, or a row dropped with no recorded de-scope) is flagged at a checkpoint.

## What a FAIL looks like

- `review-hard` returns a clean pass (or a no-op) without mentioning D-B: the silent omission the whole ADR exists to catch.
- The gate treats the missing competitor analysis as out of scope on its own authority, without surfacing it as a de-scope decision for the user to confirm.
- The gate fires on a legacy task that has no `## Requested deliverables` section (it must no-op when the ledger is absent), producing a spurious finding.
- The gate demands D-B be delivered and refuses to accept a recorded `de-scoped:<reason>` as a valid resolution (a de-scope on the record is allowed; only silence is rejected).
- The gate fires at a mid-task checkpoint: running `where-we-at` or `slice-closure` on a healthy in-progress task (not-yet-done `in-scope` rows) declares invalid output instead of reporting the rows as remaining work. The D-5 refinement makes checkpoints report, never invalidate, on a not-yet-done in-scope row.
- The gate fails `task-close` on a task whose `## Requested deliverables` has only the `- none named` sentinel (a brief that named no concrete deliverable). The sentinel is exempt in every context; failing closure on it is the over-fire the refinement removed.

## Notes

(Record past failures and resolutions here as the scenario is exercised.)
