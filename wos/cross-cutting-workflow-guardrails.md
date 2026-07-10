---
activation: model_decision
description: Heuristics + external-web motivation + NEEDS CLARIFICATION marker. Load on phase-by-phase sequencing ambiguity.
---

# wos/cross-cutting-workflow-guardrails.md

Lazy reference for selected supplements to `## Cross-cutting workflow guardrails` in the spec.

Load this file when:
- phase-by-phase command sequencing is unclear and the `## Command roles` index plus `## Default workflow` are not enough to choose the next command
- the motivation behind the centralized external web access rule is being challenged or being explained to a contributor (the rule itself, with its enforcement bullets, lives in the spec and is always read)

The normative rules of `## Cross-cutting workflow guardrails` (Routing memory, Official command names, Material change, No-op execution rule, Proposal vs approved persistence, External web access Rules) remain in `WORKFLOW_OPERATING_SYSTEM.md` and apply to every command run regardless of whether this file is loaded.

---

### Sequencing heuristics (by phase)

Discovery/scoping:
- Run `code-locate` when the first step is "where is this code?" and `SOURCE_OF_TRUTH.md` does not yet name specific files in scope; routes to `impact-analysis` once candidates are confirmed.
- Run `impact-analysis` when blast radius is still unclear.
- Run `invariants-and-non-goals` when boundaries are not explicit enough for safe planning.
- Run `targeted-questions` when missing facts block safe progress.
- Run `decision-interview` when behavior/policy choices are still undecided.

Contract/decision hardening:
- If facts are the blocker, route to `targeted-questions`.
- If policy/decisions are the blocker, route to `decision-interview`.
- Run `resolve-contract-gaps` only when contradictions/options still block a single implementation-safe rule set.
- Run `contract-signoff` only when remaining work is normalization/precision, not unresolved policy choice.

Planning/validation:
- Confirm `DECISIONS.md` is stable enough for planning; if not, route to contract/decision commands.
- Run `implementation-plan` only when phases/slices/exit criteria would materially improve safety versus current artifacts.
- Run `test-strategy` only when validation choices are not already sufficiently explicit in `IMPLEMENTATION_PLAN.md` for the risk level (or when skipping must be explicit).

Execution/closure:
- Confirm `IMPLEMENTATION_PLAN.md` exists and the slice is explicit and approved.
- Run `implement-fleet` when the approved plan's `## Execution waves` show a remaining wave of size 2 or more whose slices declare `Scope` and `Depends-on`; it executes the independent slices in parallel under the file-scope disjointness gate (ADR-0041, reached per ADR-0042). Fall back to `implement-approved-slice` when the slice DAG is a chain.
- Run `implement-approved-slice` only when there is real approved work left to execute for the current slice (the canonical single-slice path and the fleet fallback).
- Run `implement-slice-complement` only when remaining work is an explicit micro-delta anchored to an already-executed slice and still within `DECISIONS.md`.
- Run `slice-closure` after implementation + slice-level validation evidence exists.
- Run `review-hard` when risk warrants a focused pre-PR check; skip when it would not materially change conclusions.
- Run `where-we-at` for macro checkpoints on multi-slice tasks; avoid it when `slice-closure` is the correct scope. When the completed slice is the last in the plan, route to `where-we-at` (multi-slice) or `task-close` rather than dead-ending.
- When background execution (a fleet or a long-running step) is in flight and a decision surfaces, prefer persisting choices as PROPOSED and routing to `approve-proposed` over a blocking `AskUserQuestion`: a modal question stalls the thread and discards in-flight progress signals while it waits.

Debug/incident:
- Run `incident-triage` when there is a concrete observed technical failure (stack trace, error output, failing test, runtime symptom, or production alert) and it is unclear whether the fix needs full ceremony or a hotfix.
- Do not use `im-stuck` for failures with a clear failure signal; `im-stuck` is for confusion or loops, not concrete failures.
- A `BLOCKING_PROD` plus `HOTFIX` outcome may legitimately skip ceremony, but only when the triage produces an explicit `Why this skip is safe` justification.

Delivery/communication:
- Run `pr-package` only when the diff is stable and the task is genuinely near delivery.
- Run `state-reconcile` before `pr-package` when task-memory drift could make the delivery narrative wrong (optional but recommended when trust is low).
- Run `pr-feedback-ingest` when a PR exists and feedback is mostly corrective under the current decisions/plan (map items to slices before coding).
- Run `post-review-pivot` when review or team feedback invalidates part of the packaged approach but the work continues on the same task thread.
- `pr-package` must always use an explicit git base branch for diffing (never assume a default remote branch).
- Run `branch-commit` only when lightweight naming is the real bottleneck and there is an actual diff to read; refuse to invent names from a task summary alone.
- Run `team-update` only when there is meaningful new progress worth communicating to teammates or reviewers (any channel).
- Run `workflow-guide` when pedagogy helps; avoid it when `what-next` is sufficient.
- Run `prompt-shape` when prompt precision materially improves the next step; avoid rewriting prompts for style.
- Run `im-stuck` when recovery is needed; avoid it when routing is already obvious.

---

### NEEDS CLARIFICATION inline marker

When an artifact (`DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, `SOURCE_OF_TRUTH.md`, slice files) has a gap that should block downstream work, encode it inline using the canonical marker shape:

```
[NEEDS CLARIFICATION: <what is undefined> | <decision required> | <candidate resolutions>]
```

The three pipe-separated fields are mandatory: what is missing, what choice is needed, what the candidate resolutions are (even if the answer is "ask the user"). The marker exists so that:

- A reader of the artifact sees the gap without having to remember it.
- `scripts/lint-commands.sh` greps `projects/*/active/*/*.md` for the marker and reports counts per task folder.
- `approve-plan` (see ADR-0032) refuses to lock `IMPLEMENTATION_PLAN.md` while markers remain.
- `implement-approved-slice` refuses to execute when the current slice file contains markers.

Resolution path:

- For decision gaps: route to `decision-interview`. Resolver must remove the marker AND record the decision as a `D-N` entry in `DECISIONS.md`.
- For factual gaps: route to `targeted-questions`. Resolver must remove the marker AND record the fact in `SOURCE_OF_TRUTH.md`.

Do not silently delete a `[NEEDS CLARIFICATION: ...]` marker without recording the resolution in `DECISIONS.md` or `SOURCE_OF_TRUTH.md`. Silent removal hides the gap.

---

### Why external web access is centralized

(Originally a sub-block of `### External web access (centralized)` in the spec. The enforceable rules of that subsection remain in the spec and apply unconditionally; the motivation below is supplementary and explanatory.)

- one auditable choke point for external information (URL + accessed date + summary recorded in `REFERENCES.md`)
- prevents silent re-fetching across commands and across tasks
- prevents ungrounded "research-fishing" inside discovery, planning, or implementation commands
- preserves the principle that the codebase + task memory + project memory drive decisions
- forces every external finding to become reusable project memory rather than disposable single-turn context


---

## Parallel-dispatch rules

Operational invariants for any command that fans work out to multiple sub-agents in parallel (implement-fleet, atom-audit-fleet, task-init-fleet, screen-spec-fleet, verify-against-rubric-fleet, external-research-fleet, and any future fleet command). These rules are enforceable and apply regardless of which orchestrator is dispatching.

1. Never dispatch agents that write to the same artifact in parallel: every parallel batch must target disjoint output files, and any shared artifact (e.g. a single canonical index, TASK_STATE.md, REFERENCES.md) must be funneled through a serial apply step that runs after the batch completes. Concurrent writers to one file is the classic last-writer-wins data-loss pattern (see bug-classes/concurrent-write-clobber.md) and is the substrate-level reason ADR-0038 mandates per-agent output paths.

2. Every dispatched agent prompt MUST include an explicit StructuredOutput call reminder: the parent reads only the StructuredOutput payload, so an agent that emits its answer as a text response is treated as an empty result and silently drops work. This is enforced by ADR-0040 (sub-agent contract); see bug-classes/missing-structured-output.md for the failure mode and the K.8 parallel dispatch learnings (2026-06-04) for the first lived incident.

3. Post-apply, every batch MUST run scripts/scan-substrate-orphans.py against any touched substrate files: parallel fan-out is the highest-risk surface for orphaned references (one agent renames, another agent still points at the old name) and the scan is the cheapest detection layer. Required by ADR-0039 step 5 and the No-op execution rule in the spec -- a batch that skips this scan is not considered closed.

4. Batches of more than 25 agents must be split per ADR-0039: above 25 the orchestrator hits context-window pressure on the apply step, the StructuredOutput parse error rate climbs, and partial-failure recovery becomes ambiguous. Split into sub-batches of <=25, apply each sub-batch's outputs, then dispatch the next sub-batch; do not raise the cap without a new ADR.

5. Re-dispatch instead of editing prompts mid-flight if the batch is already running: mutating the prompt template after dispatch produces a mixed-cohort batch where some agents ran under the old contract and some under the new, which makes the apply step unsound and the substrate-orphan scan results untrustworthy. Cancel the batch (or let it complete and discard), fix the prompt, re-dispatch as a fresh cohort. See bug-classes/mid-flight-prompt-mutation.md.
