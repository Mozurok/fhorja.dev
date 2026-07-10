# Eval scenario 24: Express shape routing from task-init complexity assessment

- **Tags**: task-init, complexity-routing, express-shape, ADR-0025
- **Last reviewed**: 2026-05-26
- **Status**: active

## Goal

Validates that `task-init` performs a complexity assessment and correctly routes a well-scoped, simple task to the Express pipeline (skipping `impact-analysis` and `decision-interview`). Exercises the complexity-based routing mechanism from ADR-0025 and the Express task shape from `wos/workflow-shapes.md`.

## Setup

Requires an existing project folder `projects/<client>__<project>/` with a `PROJECT_CHARTER.md`. The task description must be unambiguously simple: all decisions provided upfront, scope describable in one sentence, fewer than 5 files affected.

## Input prompt

```text
Run @commands/task-init.md

Project: acme__widget-pricing
Task slug: 2026-05-26_add-health-endpoint
Description: Add a GET /health endpoint to the existing Express server that returns { status: "ok", timestamp: Date.now() }. No auth required. Single file change in src/routes/health.ts (new) plus one import line in src/app.ts.
Mode: Ask
```

## Expected response shape

- `### Artifact changes` lists exactly 5 PROPOSED files (standard task-init output).
- The proposed `TASK_STATE.md` contains a `## Recommended pipeline` section (or equivalent inline in `## Recommended next step`) that identifies the task as **Express** tier.
- `## Recommended next step` routes to `implementation-plan` (NOT `impact-analysis`), because Express tier skips impact-analysis.
- The response suggests `Operating mode: minimal` (either explicitly in the artifacts or as a recommendation in the transcript).
- `### Handoff` block ends with `Run now: /implementation-plan`, NOT `/impact-analysis` or `/decision-interview`.

## Pass criteria

1. **Complexity assessment present**: TASK_STATE.md or the command transcript explicitly identifies the task as Express (or equivalent low-complexity tier).
2. **Correct routing**: Recommended next command is `implementation-plan`, not `impact-analysis`. The Express shape skips `impact-analysis` and `decision-interview`.
3. **Minimal mode suggested**: The response suggests or recommends `Operating mode: minimal` for this task.
4. **No fabrication**: The response does not invent additional scope, risks, or decisions beyond what the one-sentence description provides.
5. **Standard file set**: All 5 mandatory files are PROPOSED (the Express shape does not reduce the file set, only the pipeline).
6. **Valid handoff**: `### Handoff` block is present with `Run now: /implementation-plan`.

## Failure modes to watch

- **Over-routing**: task-init routes to `impact-analysis` despite the trivially simple scope. This is the exact friction pattern ADR-0025 exists to prevent.
- **Missing complexity assessment**: task-init produces standard output without any tier recommendation, ignoring the ADR-0025 mechanism.
- **Skipping too much**: task-init routes directly to `implement-approved-slice` without an `implementation-plan` step. Express tier still requires a plan.
- **Strict mode suggested**: suggesting `Operating mode: strict` for a health endpoint is a misclassification.

## Notes

- Related ADRs: [ADR-0025](../../docs/adr/0025-complexity-routing.md), [ADR-0009](../../docs/adr/0009-task-shape-system.md).
- Related commands: `commands/task-init.md`.
- Related topic files: `wos/workflow-shapes.md` (Express task shape), `wos/operating-modes.md` (auto-suggestion).

## History

- 2026-05-26: scenario authored as part of wos-friction-reduction task (Slice 6).
