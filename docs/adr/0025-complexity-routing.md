# ADR-0025: Complexity-based routing at task-init

Status: Accepted (2026-05-26)

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

## Model selection by tier (addendum 2026-06-03)

Each tier maps to a recommended Claude model. This is non-normative guidance — the user may override at runtime — but defaults reduce the "always use Opus" anti-pattern (Claude Max 20x users routinely waste plan capacity by running Opus for Express tasks).

| Tier | Default model | Rationale |
|---|---|---|
| **Express** | `claude-haiku-4-5` | Single-file, known decisions, <5 files. Haiku 4.5 is >4x faster output and handles trivial-to-moderate edits without quality loss. |
| **Standard** | `claude-sonnet-4-6` | Multi-file, some research. Sonnet 4.6 hit 79.8% SWE-Bench at ~1/10 the cost of Opus 4.7. Sweet spot for most coding work. |
| **Disciplined** | `claude-sonnet-4-6` (default) → `claude-opus-4-7` (escalate) | Multi-package or non-obvious tradeoffs. Start Sonnet; escalate to Opus when integration risk is high. |
| **Strict** | `claude-opus-4-7` or `claude-opus-4-8` | Auth/payments/compliance/multi-tenant. Opus 4.8 (released 28-mai-2026) is 88.6% SWE-Bench Verified and ~4x less likely to miss failures. Worth the cost when blast radius is large. |

### Override rules

- Escalating UP (Express → Standard, Standard → Disciplined → Strict) is always valid. When in doubt, pick stronger.
- Demoting DOWN past Disciplined (Strict → Sonnet) is NOT recommended. If the user feels the tier is wrong, fix the tier classification at task-init; do not demote the model.
- Override is per-task, not per-session. The chosen model is recorded in `TASK_STATE.md` next to the tier so it survives session breaks.

### Verification cadence

Every 6 weeks, check Anthropic's latest coding-model SWE-Bench numbers and update the recommended SKUs in this table. Coding-model SOTA moves fast (Claude 4.7 → 4.8 was 6 weeks; GPT-5 → 5.5 was months). Stale SKUs degrade the routing more than no routing at all.

### Why hardcode SKUs here

The "no model SKUs in handoff lines" rule in `WORKFLOW_OPERATING_SYSTEM.md` → `## Global output contract` → `### Work complexity (capability routing)` exists for *runtime handoff lines* read by external tools (Cursor, others) that need vendor-neutral routing. This ADR is the project-level configuration ADR where SKU choice belongs; updating one file is cheaper than updating handoff lines across 53 commands when SOTA shifts.

### Tracking

`scripts/track-model-usage.sh` (planned, B.4 of WOS improvement plan 2026-06-03) emits per-task records of `{tier, model_used, token_estimate}` so the team can measure whether the routing recommendation is being followed and what cost delta it produces.

## References
- ADR-0009 (Task shape system): Express is a new shape within the existing framework
- Fhorja transcript analysis: Category A findings (A1 pipeline length, A2 double-prompt, A3 task transition)
- Fhorja transcript analysis: Category F findings (F1 paste-relay, F2 questions dropped 10x)
