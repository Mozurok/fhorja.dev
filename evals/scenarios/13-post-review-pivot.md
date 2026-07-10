# Eval scenario 13: post-review-pivot after pivot-shaped feedback

- **Tags**: post-review-pivot, pivot-digest, decision-revision, re-planning
- **Last reviewed**: 2026-05-09
- **Status**: active

## Goal

Validates that `post-review-pivot` correctly absorbs PR or team feedback that disputes a locked decision, produces a structured pivot digest separating "keep" vs "revert/replace", proposes the smallest safe set of updates to task memory and follow-on work, and does NOT implement product code in this run (implementation happens in a separate `implement-approved-slice` after re-planning).

This exercises:

- The "pivot digest before re-implementation" rule.
- The keep-vs-revert separation (a pivot is rarely "throw it all away"; usually most of the work stands and a specific contract changes).
- The decision revision flow (a `D-N` entry in `DECISIONS.md` records the supersession).
- The Handoff routing to `decision-interview` / `resolve-contract-gaps` / `implementation-plan` rather than directly to `implement-approved-slice`.

## Setup

This scenario continues from scenario 10 (`pr-feedback-ingest with Greptile-style feedback`). Item 4 in that scenario was pivot-shaped: human reviewer Sarah disputed locked decision D-1 (404 for no-prices vs 200 with empty array, which breaks Mobile team's parsing). Scenario 10's response should have surfaced item 4 as needing `post-review-pivot` separately.

Now run `post-review-pivot` against the same task:

`projects/acme__widget-pricing/active/2026-05-08_initial-price-query/` is the same task. The corrective items from scenario 10 may or may not be addressed yet (this scenario does not depend on their status). The pivot signal is item 4.

## Input prompt

```text
Run @commands/post-review-pivot.md

Active task: projects/acme__widget-pricing/active/2026-05-08_initial-price-query/
PR: https://github.com/acme/widget-pricing-api/pull/42
Mode: Ask

Pivot signal (verbatim from PR review):
"Why are we returning 404 instead of 200 with empty array? This breaks our existing client expectations; Mobile team will need to update their parsing logic."
- Reviewer: Sarah (engineer)
- This disputes locked decision D-1.
```

## Expected response shape

- Response begins with post-review-pivot's persona line.
- Response produces a pivot digest with an explicit `## Keep` and `## Revert / Replace` separation:
  - **Keep**: the handler implementation (slice 01 work); the route registration; the test infrastructure; everything not touching the response-shape decision.
  - **Revert / Replace**: D-1 is superseded. The new D-N (e.g., `D-3`) records the change: 200 with empty array (or empty prices field) instead of 404. The handler's 404 branch is replaced with a 200 + empty response; the test that asserts 404 is replaced with one that asserts the new shape.
- The proposed `### Artifact changes` includes:
  - `DECISIONS.md` patch superseding D-1 with a new D-N entry. The original D-1 is not deleted; it is marked superseded with a reference to the new D-N.
  - `TASK_STATE.md` patch noting the pivot in `## Last completed step` and reverting `## Current phase` to a planning-or-implementation phase (since slice 01 needs partial re-execution).
  - `IMPLEMENTATION_PLAN.md` patch updating slice 01 (or adding a slice 02) to cover the response-shape change.
- The proposed digest does NOT propose code edits to `src/handlers/prices.ts` directly (that is implement-approved-slice's job after re-planning).
- The Handoff routes to `decision-interview` (formal supersession), `resolve-contract-gaps` (if any other decisions are now in tension), `contract-signoff` (to lock the new decision), or `implementation-plan` (if the supersession is clean and the next step is just to re-plan slice 01). Not to `implement-approved-slice` directly.

## Pass criteria

1. **Pivot digest structured**: response has explicit `## Keep` and `## Revert / Replace` sections (or equivalent labels). Mixed prose without the separation is invalid.
2. **D-1 superseded, not deleted**: `DECISIONS.md` patch marks D-1 as superseded by the new D-N. The original entry remains in the file with a `superseded by D-N` annotation.
3. **New D-N recorded**: a new numbered decision entry captures the new direction (200 with empty array). The rationale references Sarah's feedback (audit trail).
4. **No code edits in this run**: the pivot is digest + decision + plan update; product code edits happen in a follow-on `implement-approved-slice` run.
5. **Plan or slice updated**: `IMPLEMENTATION_PLAN.md` (or a new slice file) is patched to cover the response-shape change. The change is named explicitly; not a generic "implement Sarah's feedback".
6. **Routing to upstream commands**: `Run now:` is `decision-interview` / `resolve-contract-gaps` / `contract-signoff` / `implementation-plan`, not `implement-approved-slice`.
7. **Handoff intact**: response ends with a complete Handoff. adaptive handoff block has the task path.

## Failure modes to watch

- **Throw-it-all-away pivot**: response recommends scrapping slice 01 and starting over. Most pivots preserve the bulk of the work; the keep/replace separation should make this visible.
- **D-1 silently overwritten**: response edits D-1 in place ("change 404 to 200") without recording the supersession. Loses the audit trail; the decision history becomes unreadable.
- **Code edits inline**: response proposes the actual TypeScript change in `prices.ts`. That conflates pivot with execution; the right path is digest then re-plan then implement.
- **Routing to implement-approved-slice**: response treats the pivot as if it were a corrective item. The whole reason post-review-pivot is a separate command is that pivot-shaped feedback needs re-planning, not direct execution.
- **Generic plan update**: the new slice or plan entry says "address PR review feedback" without specifying the response-shape change. Loss of grounding.
- **Pivot without slice impact assessment**: response notes the new decision but does not propose what slice 01's work needs (which tests change, which handler branch is replaced). The next implement-approved-slice has to redo this analysis.

## Notes

- Related ADRs: [ADR-0001](../../docs/adr/0001-proposed-by-default.md), [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md).
- Related commands: `commands/post-review-pivot.md`, `commands/pr-feedback-ingest.md` (the corrective sibling; scenario 10), `commands/decision-interview.md`, `commands/resolve-contract-gaps.md`, `commands/contract-signoff.md`, `commands/implementation-plan.md`.
- This scenario is the second half of the PR-feedback story. Pairing 10 (corrective) and 13 (pivot) gives full coverage of the post-PR loop's split.

## History

- 2026-05-09: scenario authored. Initial pass criteria defined; not yet run against a model.
