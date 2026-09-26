# Eval scenario 24: the short pipeline is what task-init produces when no disqualifier fires

> Retitled 2026-09-16. The filename is historical: ADR-0207 retired the tier names, so what this grades is the pipeline `task-init` produces when its `Escalations:` line reads `none`, not a tier it assesses its way into.

- **Tags**: task-init, escalation-assessment, short-pipeline, one-slice-route, ADR-0025, ADR-0184, ADR-0207, ADR-0225
- **Last reviewed**: 2026-09-23
- **Status**: active

## Goal

Validates that `task-init` runs the ADR-0184 escalation assessment on a well-scoped, simple task, names no disqualifier, and routes to the short pipeline, skipping `impact-analysis` and `decision-interview`. ADR-0025 supplied the original four-tier vocabulary; ADR-0207 retired the labels and kept the escalations, so what is graded here is the `Escalations: none` line and the pipeline it produces, not a tier name.

## Setup

Requires an existing project folder `projects/<client>__<project>/` with a `PROJECT_CHARTER.md`. The task description must be unambiguously simple: all decisions provided upfront, scope describable in one sentence, three named files: more than the two the one-slice route allows (ADR-0225) and fewer than the five that add `impact-analysis`.

## Input prompt

```text
Run @commands/task-init.md

Project: acme__widget-pricing
Task slug: 2026-05-26_add-health-endpoint
Description: Add a GET /health endpoint to the existing Express server that returns { status: "ok", timestamp: Date.now() }. No auth required. Single file change in src/routes/health.ts (new) plus one import line in src/app.ts and a test in src/routes/health.test.ts (new).
Mode: Ask
```

## Expected response shape

- `### Artifact changes` lists exactly 5 files, written and marked `APPLIED` (standard task-init output; ADR-0199, so Ask mode changes nothing).
- `TASK_STATE.md` contains a `## Recommended pipeline` section whose `Escalations:` line reads `none`, and no tier name (ADR-0207).
- `## Recommended next step` routes to `implementation-plan` (NOT `impact-analysis`), because no disqualifier fired, so the short pipeline skips impact-analysis.
- No `Route: one-slice` line and no `## Approval log`: the brief names three files, so the one-slice route does not apply (ADR-0225).
- The response suggests `Operating mode: minimal` (either explicitly in the artifacts or as a recommendation in the transcript).
- `### Handoff` block ends with `Run now: /implementation-plan`, NOT `/impact-analysis` or `/decision-interview`.

## Pass criteria

1. **Escalation assessment present**: TASK_STATE.md records `Escalations: none`, and neither it nor the transcript names a tier.
2. **Correct routing**: Recommended next command is `implementation-plan`, not `impact-analysis` and not `implement-approved-slice`. The short pipeline skips `impact-analysis` and `decision-interview`, and three named files keep the plan (ADR-0225).
3. **Minimal mode suggested**: The response suggests or recommends `Operating mode: minimal` for this task.
4. **No fabrication**: The response does not invent additional scope, risks, or decisions beyond what the one-sentence description provides.
5. **Full file set**: All 5 mandatory files are written and marked `APPLIED` (the short pipeline does not reduce the file set, only the pipeline).
6. **Valid handoff**: `### Handoff` block is present with `Run now: /implementation-plan`.

## Failure modes to watch

- **Over-routing**: task-init routes to `impact-analysis` despite the trivially simple scope. This is the exact friction pattern ADR-0184 exists to prevent.
- **Missing escalation assessment**: task-init produces standard output with no `Escalations:` line, ignoring the ADR-0184 mechanism.
- **Tier name returns**: the output labels the task Express, or any other retired tier name (ADR-0207).
- **Skipping too much**: task-init routes directly to `implement-approved-slice` without an `implementation-plan` step, or writes a `Route: one-slice` line. The one-slice route allows at most two named files and this brief names three (ADR-0225), so the plan is still required.
- **Strict mode suggested**: suggesting `Operating mode: strict` for a health endpoint is a misclassification.

## Notes

- Related ADRs: [ADR-0225](../../docs/adr/0225-a-one-slice-change-is-checked-by-a-script-not-a-plan-review.md) (the one-slice route this brief stays outside), [ADR-0184](../../docs/adr/0184-express-is-the-default-tier.md), [ADR-0207](../../docs/adr/0207-the-default-behavior-has-no-name.md), [ADR-0025](../../docs/adr/0025-complexity-routing.md) (the retired four-tier vocabulary), [ADR-0009](../../docs/adr/0009-task-shape-system.md).
- Related commands: `commands/task-init.md`.
- Related topic files: `wos/workflow-shapes.md` (Well-scoped task, no escalation fired), `wos/operating-modes.md` (auto-suggestion).

## History

- 2026-05-26: scenario authored as part of wos-friction-reduction task (Slice 6).
- 2026-09-23: the brief gains a third file (ADR-0225). With two files it qualified for the one-slice route, and this scenario grades the path that keeps the plan. Scenario 137's note that this file must stay byte-identical was lifted by the same ADR.
