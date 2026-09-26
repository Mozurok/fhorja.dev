# ADR-0025: Complexity-based routing at task-init

- **Status**: Accepted; the default that Express is a recommendation the user must opt into is Superseded by [ADR-0159](./0159-express-binds-by-default.md). The conservative default (when uncertain, classify as Standard) remains in force; the "classify as Standard when uncertain" tie-breaker is superseded by [ADR-0184](./0184-express-is-the-default-tier.md), which makes Express the default and requires an escalation to name its disqualifier (the four tiers and their pipelines stand). The four-tier vocabulary is Superseded in part by ADR-0207: the escalations survive, the tier labels do not.

## Context

Transcript analysis of an 8-week Fhorja development session (4,681 JSONL lines, 12 research agents) revealed that the WOS pipeline costs 37-44 user turns before the first line of code, regardless of task complexity. The same ceremony applies to a 72-line change (W4 design-first-scaffold) and a 6-slice multi-service integration (W2 agent-runtime).

External research confirms: Claude Code official guidance says "if you could describe the diff in one sentence, skip the plan"; GitHub Copilot Workspace found plan-editing was used by <20% of users; DX research shows 4+ confirmation steps cause user disengagement. The Fhorja user's questions dropped from 23% to 2% of messages as they became a "paste relay" between handoff blocks.

The WOS already permits skipping steps via task shapes (13 defined), "if needed"/"if useful" qualifiers, Core Principle 12 ("Prefer fewer workflow hops"), and the `minimal` operating mode. However, none of these are auto-applied; the user must know about them and opt in.

## Decision

`task-init` performs a complexity assessment after creating the task folder and emits a `## Recommended pipeline` section in TASK_STATE.md with one of four tiers:

- **Express**: scope in one sentence, all decisions known, <5 files. Pipeline: task-init -> implementation-plan -> implement-approved-slice -> branch-commit. Auto-suggests `minimal` mode.
- **Standard**: clear scope, some decisions may be needed. Pipeline: task-init -> impact-analysis -> implementation-plan -> implement-approved-slice. Skips `decision-interview` when impact-analysis surfaces no genuine ambiguity.
- **Disciplined**: multi-package, external deps, non-obvious tradeoffs. Full pipeline including `decision-interview`.
- **Strict**: auth/payments/compliance/multi-tenant. Full pipeline plus `invariants-and-non-goals`, `test-strategy`, `review-hard`. Auto-suggests `strict` mode.

Assessment signals: number of files/packages, external service dependencies, whether all decisions are in the user prompt, whether scope fits one sentence.

The assessment is a recommendation. The user can override by choosing a different command. Conservative default: classify as Standard when uncertain.

## Consequences

### Positive
- Reduces user turns pre-implementation by 60-85% for Express/Standard tasks
- Aligns with Core Principle 12 without requiring user knowledge of task shapes
- Auto-suggestion of operating modes reduces missed `minimal` opportunities
- Preserves full ceremony for HIGH-risk work (Disciplined/Strict)

### Negative
- Misclassification risk: Express tier on a task that needed decision-interview could miss tradeoffs (mitigated by conservative defaults)
- Adds logic to task-init, the most-invoked command (mitigated by the logic being a recommendation, not enforcement)

### Neutral
- The "Express task" shape added to `wos/workflow-shapes.md` is a new entry but follows the existing shape pattern
- Existing task shapes remain valid; Express is additive
- No changes to the mandatory file set (5 files still created at task-init)

## Model selection: moved to wos/model-routing.md

The tier-to-SKU table, its override rules, its verification cadence and its rationale now live in `wos/model-routing.md`. They moved there on 2026-08-30 under [ADR-0172](./0172-operational-tables-live-in-wos-not-in-adrs.md), because the table carries its own six-week refresh cadence and an accepted ADR is not a file anyone is allowed to update.

The decision this ADR records does not change. Work is still routed by complexity tier, the four tiers are still Express, Standard, Disciplined and Strict, and the classification rules above stand as written. What moved is a non-normative table, not a decision.

## References
- ADR-0009 (Task shape system): Express is a new shape within the existing framework
- Fhorja transcript analysis: Category A findings (A1 pipeline length, A2 double-prompt, A3 task transition)
- Fhorja transcript analysis: Category F findings (F1 paste-relay, F2 questions dropped 10x)
