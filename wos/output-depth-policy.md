---
activation: always_on
description: Lean / Balanced / Deep per-command depth assignment. Small and routing-relevant.
---

# Output depth policy

To reduce context waste and token usage, commands should not all produce equally large outputs.

## Lean
Use for:
- `what-next`
- `branch-commit`
- `team-update`
- `capture-observation`
- `direction-adjust`
- `code-locate`

## Balanced
Use for:
- `capture-references`
- `impact-analysis`
- `invariants-and-non-goals`
- `targeted-questions`
- `workflow-guide`
- `incident-triage`
- `slice-closure`
- `where-we-at`
- `review-hard`
- `implement-slice-complement`
- `resume-from-state`
- `sync-task-state`
- `state-reconcile`
- `pr-feedback-ingest`
- `post-review-pivot`
- `prompt-shape`

## Deep
Use for:
- `project-bootstrap`
- `task-init`
- `decision-interview`
- `resolve-contract-gaps`
- `contract-signoff`
- `implementation-plan`
- `test-strategy`
- `pr-package`

Rule:
- create the artifact
- keep it as short as the phase allows
- do not inflate output just because a command can produce more

## Transcript brevity rule
Applies to `### Command transcript` across commands:
- do not restate file-level details already present in `### Artifact changes`
- max 4 lines in normal runs
- max 3 lines in `NO_OP` runs (including `NO_OP_TRACE`)
