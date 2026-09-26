# ADR-0172: Operational tables live in wos/, not inside ADRs

- **Status**: Accepted; moves the non-normative model-selection table out of ADR-0025 without changing the decision ADR-0025 records.
- **Date**: 2026-08-30
- **Tags**: adr-immutability, wos-topics, model-routing, maintenance, adr-0025

## Context

ADR-0025 gained an addendum on 2026-06-03: a table mapping each pipeline tier to a recommended model SKU, with override rules, a verification cadence and a rationale. The table is useful and the routing it supports is real.

The addendum also carries, in its own prose, the rule that condemned it: "Every 6 weeks, check the latest coding-model SWE-Bench numbers and update the recommended SKUs in this table. Stale SKUs degrade the routing more than no routing at all."

Two cadences went by and nothing was updated. The cause is not neglect, it is structural. This repository treats an accepted ADR as immutable, so the only honest way to refresh the table was to edit a file the rules say not to edit. Faced with that, an editor does the third thing: nothing.

The same shape shows up whenever a document that records a decision also carries the operational detail that implements it. The decision is stable by design. The detail has a shelf life. Putting both in a file that must not change means the shelf life wins and the file goes stale while still reading as authoritative.

## Decision

An operational table that needs periodic maintenance lives in `wos/`, not inside an ADR. The ADR records the decision and points at the topic; the topic carries the numbers and gets updated.

Applied now: the model-selection table, its override rules, its verification cadence and its rationale move from ADR-0025 into `wos/model-routing.md`, verbatim. ADR-0025 keeps its decision, which is that work is routed by complexity tier, and gains a pointer plus a sentence saying the decision is unchanged.

This is an edit to the body of an accepted ADR, which the repository otherwise refuses. Three things make it the narrow case rather than a precedent for editing ADRs freely. The moved content is an addendum added three months after the original decision, so the ADR was already amended once. The decision itself is untouched: no tier changes, no routing rule changes, nothing that a reader of ADR-0025 relied on stops being true. And the move is authorized by this successor ADR rather than done quietly, so the history of the file explains itself.

The test for a future case: if a section of an ADR contains numbers that a named cadence says to refresh, it is operational and belongs in `wos/`. If it records what was decided and why, it stays.

## Consequences

### Positive

- The table can be updated by the person who notices it is stale, without asking whether they are allowed to edit an ADR.
- ADR-0025 gets shorter and says one thing: work is routed by tier.
- The topic is lazy-loaded, so the SKU table costs nothing until a model decision is actually being made.

### Negative

- One more file. A reader of ADR-0025 now needs one hop to reach the table, which the pointer makes explicit.
- Editing the body of an accepted ADR sets a shape someone could stretch. The three conditions above are the boundary, and they are narrow on purpose.

### Neutral

- The content moves verbatim, including its own staleness. Refreshing the numbers is a separate act by whoever picks up the cadence, not something smuggled into a move.
- The vendor-neutral rule that commands never emit SKU names in handoff lines is unchanged.

## Alternatives considered

### Alternative 1: leave the table in ADR-0025 and refresh it by writing a new ADR each time

- Every six weeks, a successor ADR restating the table with new SKUs.
- Rejected: an ADR per routine refresh turns the decision record into a changelog, and the ADR index becomes unreadable for the decisions that matter.

### Alternative 2: leave it and accept the staleness

- Treat the cadence as aspirational.
- Rejected: the addendum itself says stale SKUs degrade the routing more than no routing at all. Keeping a table nobody may update is worse than not having one.

### Alternative 3: delete the table

- Drop model selection entirely and let the user decide with no default.
- Rejected: the default exists to counter a real waste pattern, running the strongest model on trivial work. The problem was where the table lived, not that it existed.

## References

- [ADR-0025](./0025-complexity-routing.md): the decision this leaves intact; the addendum is what moved.
- `wos/model-routing.md`: where the table lives now.
- `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` -> `### Work complexity (capability routing)`: the vendor-neutral handoff rule, unchanged.

## Notes

The moved text keeps its own inaccuracies, including a command count from when it was written and a script described as planned that now exists. Correcting them is the first job of whoever takes the cadence back up, and doing it in the move would have hidden the correction inside a refactor.
