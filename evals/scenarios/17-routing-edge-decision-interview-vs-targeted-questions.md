# Eval scenario 17: routing-edge: decision-interview vs targeted-questions

- **Tags**: routing-edge, decision-interview, targeted-questions, decision-vs-factual-gap
- **Last reviewed**: 2026-05-18
- **Status**: active

## Goal

Validates that the model correctly distinguishes decision-driven gaps (would change runtime behavior, data integrity, rollout safety, test strategy) from factual gaps (information not yet confirmed; no policy choice). The scenario presents an ambiguous prompt that could be read as either; the model must read it carefully and pick the right command.

## Setup

Active task at `projects/acme__widget-pricing/active/2026-05-09_customer-tier-discount/`. Impact-analysis just ran and surfaced open items. The user pastes the four items below and asks which command to run next.

## Input prompt

```text
Impact-analysis just produced these open items. Which command do I run next?

Item 1: I do not yet know whether the `customers` table has a `tier` column or if it is computed at query time.
Item 2: We have not decided whether tier discounts apply BEFORE or AFTER promotional discounts.
Item 3: The exact list of customers grandfathered out of the new tier policy is documented somewhere; I have not pulled it yet.
Item 4: We have not chosen whether to expose tier as a customer-facing field in the API response.

Active task: projects/acme__widget-pricing/active/2026-05-09_customer-tier-discount/
Mode: Ask
```

## Expected response shape

- Response classifies each of the 4 items as either a **decision** (would change behavior; affects runtime / data / rollout / tests) or a **fact** (information that can be looked up; no policy choice).
- Response routes to `decision-interview` for the decisions and `targeted-questions` for the facts, in the correct order (decisions usually first because they shape what facts matter).
- If items are mixed, response may run both commands sequentially via the Handoff (`Run now: /decision-interview` first, then route to `targeted-questions` after).

## Pass criteria

1. **Items classified correctly**: items 1 and 3 are FACTS (looking up the schema; looking up the documented list). Items 2 and 4 are DECISIONS (apply-before-or-after; expose-or-not).
2. **Decisions before facts**: response recommends `decision-interview` first (or names that decisions usually dominate the routing because they shape which facts are load-bearing).
3. **Both commands surface**: response names both `decision-interview` and `targeted-questions`. Picking only one fails this criterion.
4. **Handoff routes to one primary**: `Run now:` is `decision-interview` (the heavier of the two; more leverage if decisions dominate). adaptive handoff block for decision-interview includes items 2 and 4 verbatim.
5. **No fabricated answers**: response does not invent what the decisions would be (e.g., "tier discount applies first") or what the facts would be (e.g., "the customers table has a tier column").
6. **Mode aligned**: Mode is Ask (decision-driven discovery; not Plan; not Agent).

## Failure modes to watch

- **All items lumped into one command**: fails the classification test; the value of the routing edge is precision.
- **Items 1 and 3 routed to decision-interview**: factual gaps treated as decision-driven; wrong tool.
- **Items 2 and 4 routed to targeted-questions**: decision-driven gaps treated as factual; the questions can be asked but the answers are policy choices, not lookups.
- **Picks one command and silently drops the other**: the workflow's distinctness is the value; merging defeats it.
- **Fabricates the decision outcomes**: response writes "the tier discount applies AFTER promotions because..." without the user having decided.

## Notes

- Related ADRs: [ADR-0002](../../docs/adr/0002-paste-this-next-contract.md).
- Related commands: `commands/decision-interview.md`, `commands/targeted-questions.md`.

## History

- 2026-05-18: scenario authored as routing-edge test 2 of 4 in slice 08.
