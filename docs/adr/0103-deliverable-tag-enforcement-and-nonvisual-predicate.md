# ADR-0103: Deliverable-tag propagation enforcement and the non-visual tagging predicate

- **Status**: Accepted
- **Date**: 2026-07-12
- **Tags**: experience-gate, deliverable-tag, approve-plan, implementation-plan, task-init, w-09, extends-adr-0091, enforcement-of-existing-rule, dogfood-driven, theme-dogfood-wave

## Context

ADR-0091's deliverable tags (`user-facing-content`, `new-user-facing-surface`) have two independent write sites: the `## Requested deliverables` ledger seeded at `task-init` and the per-slice `Deliverable-tag:` field written at `implementation-plan`, with no propagation rule and no cross-check between them. In the mcp-server dogfood path (2026-07-11 wave) the plan silently dropped a tag the ledger carried; only `slice-closure`'s backstop clause caught it, on a deliberately careful closure pass, exactly the late-catch shape ADR-0085 exists to prevent for the runtime gate. Separately, four paths (mcp-server, realtime-game, ai-devtool, pix-checkout) found the tagging predicate ("user-facing product content or a new user-facing surface") carries no operational test for non-visual surfaces, leaving developer CLIs and machine-to-machine APIs to guesswork; the ai-devtool CLI went untagged at seeding and was caught only by the backstop.

## Decision

Three additive changes, enforcement-of-existing-rule shape (ADR-0085 precedent):

1. **Derive-from-ledger at plan time** (`implementation-plan`): every ledger row tagged `user-facing-content` or `new-user-facing-surface` SHALL have its covering slice(s) carry the matching `Deliverable-tag:`; dropping a ledger-carried tag is flagged in the transcript.
2. **Blocking cross-check at approval** (`approve-plan`, the W-09 consistency gate): a ledger-carried tag with no covering slice tag is a blocking mismatch, named and routed before approval. Eval scenario 61 is updated in the same change. The gate also gains the optional per-slice `Decision-ref:` field as its mechanical trace path (a slice cites the D-N it implements, or `none` with a reason; content-level tracing remains the fallback), and the none-locked case is settled: a plan on a task whose DECISIONS.md holds no locked decisions PASSES the trace sub-check, there being nothing to trace.
3. **Operational tagging test** at the three tagging sites (`task-init` ledger rule and template, `implementation-plan` tag bullet): the tag applies when a human end user experiences the content or reaches the surface through ANY client, visual or not (an MCP prompt surface reached via chat tags); machine-to-machine APIs and developer-facing CLIs do not tag. This extends the ADR-0091 D-1 predicate on the record; eval scenarios 103 and 105 were rechecked for wording consistency.

## Consequences

### Positive

- A ledger tag can no longer be silently lost between intake and execution; the failure moves from a closure-time backstop catch to an approval-time block, where the fix is cheap.
- Non-visual surfaces get a decidable predicate instead of per-session judgment; unattended runs stop guessing.

### Negative

- One more blocking condition at approve-plan. Bounded: it fires only on a tag the user's own brief put on the ledger.

### Neutral

- The closure-time backstop remains as the last line; this ADR adds the earlier gates, it does not move the floor.

## References

- Dogfood evidence: TF-35, TF-38, TF-40 in `2026-07-11_theme-dogfood-wave2-triage/IMPACT_ANALYSIS.md`.
- Extends ADR-0091 (a) D-1; enforcement precedent ADR-0085; W-09 gate pinned by eval scenario 61 (updated).
