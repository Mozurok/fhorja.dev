# Eval scenario 19: routing-edge: pr-feedback-ingest vs post-review-pivot

- **Tags**: routing-edge, pr-feedback-ingest, post-review-pivot, corrective-vs-pivot, mixed-feedback
- **Last reviewed**: 2026-05-18
- **Status**: active

## Goal

Validates that the model distinguishes corrective PR feedback (bugs, style, missing tests under the existing contract) from pivot-shaped feedback (disputes a locked decision or proposes a different direction). The scenario presents MIXED feedback where most items are corrective but one item is pivot-shaped; the model must surface the pivot item and route it to `post-review-pivot` separately, not fold it into the corrective backlog.

## Setup

Active task at `projects/acme__widget-pricing/active/2026-05-08_initial-price-query/`. PR is open at github.com/acme/widget-pricing-api/pull/42. The user pastes Greptile-style feedback below.

## Input prompt

```text
PR feedback came in. Which command do I run?

Active task: projects/acme__widget-pricing/active/2026-05-08_initial-price-query/
PR: https://github.com/acme/widget-pricing-api/pull/42
Mode: Ask

Feedback (Greptile + 1 human):

[Greptile, item 1]: Missing null check on `customer.tier` in src/handlers/prices.ts:42. Will crash if customer record is missing tier.

[Greptile, item 2]: Test file tests/discount/tiers.spec.ts has a typo in describe block ("Tirers" instead of "Tiers").

[Greptile, item 3]: src/discount/tiers.ts uses `let` for the tier-rate map; should be `const`. Style fix per project ESLint config.

[Sarah (engineer), item 4]: Why are we returning 404 for no-prices instead of 200 with empty array? This breaks Mobile team's parsing logic. Disputes D-1 in our DECISIONS.md.
```

## Expected response shape

- Response classifies each item as corrective (under existing contract) or pivot (disputes contract).
- Response routes items 1, 2, 3 to `pr-feedback-ingest` (corrective).
- Response routes item 4 to `post-review-pivot` (pivot; disputes D-1).
- The two commands are run separately, NOT merged into one.

## Pass criteria

1. **Items 1, 2, 3 classified as corrective**: missing null check, typo, style fix - all under the existing contract. None disputes a locked decision.
2. **Item 4 classified as pivot**: explicitly disputes D-1 (the locked decision on 404 vs 200 with empty array). The reviewer asks "why" in a way that proposes a different direction, not a fix-within-current-direction.
3. **Routes to pr-feedback-ingest for items 1-3**: `Run now:` is `pr-feedback-ingest` with the 3 corrective items in the handoff block.
4. **Item 4 surfaced separately for post-review-pivot**: response explicitly states that item 4 needs `post-review-pivot` SEPARATELY, not as part of the corrective ingest. Acceptable: handoff routes to pr-feedback-ingest primary AND names that post-review-pivot must run after for item 4.
5. **D-1 reference preserved**: response names that item 4 disputes D-1 by reference; does not silently re-decide the response shape.
6. **No invented items**: response does not add corrective items beyond the 3 Greptile items, and does not split item 4 into smaller pieces.
7. **Mode aligned**: Mode is Ask (review-shaped); both commands operate in Ask by default.

## Failure modes to watch

- **All 4 items in pr-feedback-ingest**: pivot signal folded into corrective backlog. The pr-feedback-ingest command will produce a corrective patch that silently overrides D-1 without the formal supersession ceremony. This is the highest-cost failure mode.
- **All 4 items in post-review-pivot**: corrective items treated as pivots. Heavy ceremony for a typo and a missing null check.
- **Item 4 dropped**: response addresses items 1-3 only and silently ignores item 4. Audit trail violation.
- **Item 4 routed to decision-interview directly**: skips the pivot digest step; `post-review-pivot` is the canonical first step when feedback disputes a decision; decision-interview is downstream of the pivot digest.

## Notes

- Related ADRs: [ADR-0001](../../docs/adr/0001-proposed-by-default.md), [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md).
- Related commands: `commands/pr-feedback-ingest.md`, `commands/post-review-pivot.md`, `commands/decision-interview.md`.
- Related scenarios: scenario 10 (pr-feedback-ingest with Greptile feedback; pure corrective), scenario 13 (post-review-pivot continuation of 10's item 4). This scenario 19 is the routing-edge version: the model must SURFACE the split itself, not have it pre-classified.

## History

- 2026-05-18: scenario authored as routing-edge test 4 of 4 in slice 08.
