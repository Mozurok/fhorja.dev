# Eval scenario 10: pr-feedback-ingest with Greptile-style feedback

- **Tags**: pr-feedback-ingest, traceability, corrective-scope, routing
- **Last reviewed**: 2026-05-08
- **Status**: active

## Goal

Validates that `pr-feedback-ingest` consolidates PR review feedback (Greptile, CI, bots, humans) into a structured traceable backlog aligned with `TASK_STATE.md`, `DECISIONS.md`, and `IMPLEMENTATION_PLAN.md`, classifies each item as **corrective** (under existing scope) or **needs-pivot** (changes the contract), and routes forward to `implement-approved-slice` / `implement-slice-complement` (corrective) or `post-review-pivot` (pivot) without conflating the two.

This exercises:

- The corrective-vs-pivot distinction (the canonical reason `pr-feedback-ingest` and `post-review-pivot` exist as separate commands).
- The traceability matrix (each feedback item maps to a file, slice, decision, or task-memory update).
- The Handoff routing decision based on whether all items are corrective or any are pivot-shaped.

## Setup

Assume an active task at `projects/acme__widget-pricing/active/2026-05-08_initial-price-query/` with PR #42 open against `origin/main`. PR_PACKAGE.md is the v1 of the PR description. The reviewer (Greptile, plus a human) left these comments (paste verbatim into the AI tool's context):

```text
Greptile (automated):
1. tests/handlers/prices.spec.ts:18 - The 404 test asserts `error: "no prices for customer"` but the handler in src/handlers/prices.ts:13 emits `error: "no prices for customer"` capitalized differently in error logs. Recommend lowercasing the assertion.
2. src/handlers/prices.ts:5 - `getPricesForCustomer` reads `req.params.customer_id` without input validation. Recommend adding a UUID format check; otherwise an arbitrary string can hit the DB.
3. src/routes.ts:15 - Route registration is correctly added but lacks an OpenAPI annotation; the project's other routes use `@route` JSDoc-style comments.

Human reviewer (Sarah, engineer):
4. Why are we returning 404 instead of 200 with empty array? This breaks our existing client expectations; Mobile team will need to update their parsing logic.
5. Consider caching the price lookup; we expect this endpoint to be called O(N) per page load.

CI:
6. lint: 0 errors (passing).
7. tests: 12 passed, 0 failed (passing).
```

## Input prompt

```text
Run @commands/pr-feedback-ingest.md

Active task: projects/acme__widget-pricing/active/2026-05-08_initial-price-query/
PR: https://github.com/acme/widget-pricing-api/pull/42
Mode: Ask

Feedback (paste):
[the full block above]
```

## Expected response shape

- Response begins with pr-feedback-ingest's persona line.
- Response classifies each of the 7 feedback items into **corrective** (1, 2, 3, 5, 6, 7) or **needs-pivot** (4, because it disputes a locked decision D-1: 404 vs 200 with empty array).
- Items 6 and 7 (CI passing) are noted as informational/positive signals (no action needed).
- Items 1-3, 5: corrective. Each gets a row in the proposed traceability matrix mapping it to a file (or slice, or decision) and a recommended action.
- Item 4: pivot-shaped. Response routes this to `post-review-pivot` (not addressed by `pr-feedback-ingest`).
- The proposed traceability matrix has columns like: feedback item id, source (Greptile/Sarah/CI), summary, classification (corrective/pivot/info), target file or slice, recommended action.
- `### Artifact changes` proposes a `TASK_STATE.md` patch noting the open feedback items and their pivot subset, plus possibly a slice-notes update for the corrective items.
- The Handoff routes to `implement-slice-complement` (the corrective items are micro-deltas under slice 01's intent) or `implementation-plan` (if the corrective items add up to a new slice). The Handoff also explicitly recommends `post-review-pivot` for item 4 in a follow-up note (the user runs that separately to handle the pivot).

## Pass criteria

1. **Classification distinct**: each feedback item is classified as corrective, pivot, or info. Items 1, 2, 3, 5 → corrective; item 4 → pivot (disputes D-1); items 6, 7 → info.
2. **Pivot routed to post-review-pivot**: item 4 is NOT folded into the corrective backlog. The response surfaces it as needing `post-review-pivot` first because it disputes a locked decision.
3. **Traceability matrix structured**: each corrective item has an explicit target (file/line, slice, or decision) and a recommended action (edit X; add Y; check Z).
4. **Decision references**: item 4 is grounded by reference to `D-1` in DECISIONS.md (the 404-vs-200 decision). If `D-1` is not cited explicitly, the connection is invisible.
5. **No execution leaked into ingest**: the response does NOT propose code changes for the corrective items in this run. `pr-feedback-ingest` is for ingesting and mapping; the actual edits happen in `implement-slice-complement` or `implement-approved-slice` afterward.
6. **Handoff routing**: `Run now:` is `implement-slice-complement` (or `implementation-plan` if the corrective items justify a new slice); the Handoff body includes a note that item 4 needs `post-review-pivot` separately.
7. **Info items handled lightly**: items 6 and 7 (CI passing) are noted but do not produce backlog rows or artifact changes.

## Failure modes to watch

- **Pivot folded into corrective**: response treats item 4 as just another bug to fix, ignoring that it disputes D-1. The corrective implementation would silently change a locked decision; this is the failure mode that motivates having `post-review-pivot` as a separate command.
- **Code edits in the ingest run**: response proposes the actual fixes (edits to prices.ts, etc.) instead of mapping them to follow-up commands. Conflates ingest with execution.
- **Missing decision link**: response notes "Sarah disagrees with the 404 behavior" without referencing `D-1`. The audit trail breaks; future readers cannot tell that the item is challenging a locked decision.
- **Treating CI signals as backlog**: response generates rows for items 6 and 7 even though they are positive signals. Wastes attention.
- **Wrong routing**: `Run now:` is `pr-package` (skipping the corrective work) or `post-review-pivot` (treating the whole batch as a pivot when most items are corrective).
- **No traceability matrix**: response is prose-only with no structured mapping. The traceability is the load-bearing artifact of this command.

## Notes

- Related ADRs: [ADR-0001](../../docs/adr/0001-proposed-by-default.md), [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md).
- Related commands: `commands/pr-feedback-ingest.md` (this command), `commands/post-review-pivot.md` (the pivot escalation), `commands/implement-slice-complement.md` (the typical corrective execution path).
- The corrective-vs-pivot split is one of the workflow's clearest examples of "two commands, one artifact area, distinct purposes". A future eval scenario could validate `post-review-pivot` directly against the same item 4 to close the loop.

## History

- 2026-05-08: scenario authored. Initial pass criteria defined; not yet run against a model.
