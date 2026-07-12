# ADR-0104: Eval-threshold closure floor (an AI_EVAL_PLAN pass threshold gates the slice that ships the feature)

- **Status**: Accepted
- **Date**: 2026-07-12
- **Tags**: eval-harness, ai-feature-eval-harness, closure-enforcement, slice-closure, implement-approved-slice, floor, extends-adr-0085-shape, dogfood-driven, theme-dogfood-wave

## Context

`ai-feature-eval-harness` (ADR-0068 wave) designs a dataset-backed eval with a pass threshold, but no closure home ever enforced that threshold's OUTCOME. The rag-docs-chat dogfood path (2026-07-11 wave, the command's first real exercise) demonstrated the loophole live: a slice exit criterion worded around the mechanism ("the harness runs end to end") was satisfiable, and satisfied, while the plan's actual quality gate (retrieval hit-rate versus threshold on the held-out set) was failing; the slice could close inline with machine-green evidence and a red eval. The same session also hit the Step 1 scope misread (a deterministic-in-execution retrieval layer whose quality depends on a model was refusable as "deterministic"), fixed as a Batch 2 patch alongside this ADR.

## Decision

Add an eval-threshold floor in the established ADR-0085/0089/0091 floor shape at the closure homes (`implement-approved-slice` inline-close path and `slice-closure`): WHEN an `AI_EVAL_PLAN.md` exists in the task folder covering the feature the closing slice ships or changes, closure requires the recorded eval OUTCOME (score against the plan's pass threshold on its held-out set) cited with the threshold met, OR an explicit one-line skip reason under the ADR-0098 bounded-vs-permanent rule. Mechanism wording never substitutes for the outcome: a green harness execution with a failing score FAILS the floor. `ai-feature-eval-harness` Step 5 requires the shipping slice to carry an EARS exit criterion keyed to the threshold, closing the loop at authoring time. The trigger signature is the presence of `AI_EVAL_PLAN.md` covering the slice's feature; tasks without one are untouched.

## Consequences

### Positive

- The eval plan becomes a commitment rather than a memo, the same doctrinal move ADR-0089's test-strategy consumption floor made for TEST_STRATEGY.md.

### Negative

- A slice shipping a model-backed feature cannot close before its eval runs at least once. Intended: that is the plan's entire point.

### Neutral

- Floor shape, skip semantics, and stand-down behavior follow the existing family; no new command.

## References

- Dogfood evidence: TF-36 (report-time P0) and TF-15 (Step 1 predicate) in `2026-07-11_theme-dogfood-wave2-triage/IMPACT_ANALYSIS.md`.
- Extends the ADR-0085 floor family; composes with ADR-0048 (the code-graded tier is Layer-1 evidence) and ADR-0098 (skip semantics).
