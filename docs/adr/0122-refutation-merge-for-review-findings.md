# ADR-0122: Refutation merge and two-field verdicts for review findings

- **Status**: Accepted
- **Date**: 2026-07-29
- **Tags**: review, verification, consensus, refutation, sub-agents, extends-adr-0073, dogfood-mobile-2026-07

## Context

ADR-0073 added the opt-in `--consistency N` mode to `review-hard` and `security-review`: run N independent review passes over the same diff, then merge by `consensus-of-N`, with the deliberate softening that a singleton is kept as a labeled advisory rather than dropped. The merge strategy itself came from `commands/_shared/worker-contract.md`, where it was designed for workers producing content partials.

The 2026-07-29 mobile dogfood, a long-running React Native task in a consuming repo whose own multi-phase review pipeline ran five times, surfaced two problems with applying that shape to findings.

**Agreement between review passes is correlated, not independent.** Several passes reading the same file with the same instructions notice the same things for the same reasons. A finding two passes share is evidence that it is salient, not that it is true. Under a consensus merge, salience gets promoted and nothing tests correctness. The run's own report put it plainly: "A verification pass that only ever confirms is not verifying."

**A finding is not one claim, it is two.** The run produced two findings whose premise was real and whose proposed fix was actively harmful. One was recorded as a refuted fix: the proposed change would have introduced the exact second-writer hazard a comment at the call site forbade. The other survived on premise but dropped from HIGH to LOW severity, because the proposed split traded a fail-safe behavior for a fail-open one. With a single-field verdict, both outcomes have nowhere to live: the reviewer must either adopt a fix that makes the code worse or discard a true finding.

Both correct outcomes on that run came from a stage whose instruction was to disprove, and that stage agreed 3-0 with itself and against the raise passes that had proposed the change. Adversarial verification removed work rather than adding it.

That pipeline ran a fixed refuter count over the whole finding set, not one refuter per finding. That distinction is load-bearing: `wos/context-budget.md` measures 400k to 1.3M tokens per 10-agent batch, and the run carried 35 queued fixes, so per-finding fan-out would have cost more than the review it was checking.

## Decision

Extend `--consistency N` with a refutation stage and a two-field verdict, and give `worker-contract.md` a merge strategy for claim-shaped deliverables.

- **Two-field verdict.** A finding is recorded as `premise` (stands | falls) and `proposed fix` (take | refuted, with reason). A refuted fix on a standing premise leaves the finding open with no adopted remedy, which is the honest state.
- **Stage 2 refuters, bounded.** After the N raise passes and before findings are handed on, a fixed small refuter count (default 3) runs ONCE over the whole surviving must-fix and should-fix set, instructed to disprove each finding and to default to refuted when uncertain. Every killed finding is recorded with the citation that disproved it, never dropped silently.
- **No per-finding fan-out.** One refuter pass over the set. The cost guard of ADR-0073 applies to this stage too.
- **`refute-then-keep` merge strategy** added to `commands/_shared/worker-contract.md`, scoped to workers whose deliverable is a claim about a reviewed artifact. `consensus-of-N` remains correct for content partials and is unchanged.

This **extends** ADR-0073 and does not reverse it. The N raise passes, the opt-in default-off trigger, the `N=3` recommendation, the cost guard, and the keep-singletons-as-advisory softening all stay in force. What changes is what happens after the raise passes: agreement no longer ends the process. Because ADRs are immutable, this is a new ADR rather than an edit to ADR-0073.

## Consequences

### Positive

- The mode can now express the outcome that actually occurred twice on the source run: a real problem with a bad proposed fix.
- Findings are tested rather than counted, which is what a reviewer wanted from `--consistency N` in the first place.
- Killed findings leave a record with their disproving citation, so a later reader can tell a refuted finding from one nobody looked at.
- The bounded refuter count keeps the added cost roughly flat in the number of findings rather than linear in it.

### Negative

- `--consistency N` costs more than before: N raise passes plus one refuter pass. The mode was already opt-in and expensive; this widens the gap between it and a single review.
- A refuter instructed to default to refuted when uncertain will sometimes kill a true finding. The recorded citation is the mitigation: a wrongly killed finding is visible and arguable, not silent.
- Two merge strategies now exist for what looks superficially like one situation, so `worker-contract.md` has to draw the content-versus-claim line clearly enough that an author picks correctly.

### Neutral

- The default refuter count (3) is a starting value matched to the configuration observed on the source run, not a measured optimum.
- `review-hard` ran zero times on that dogfood, so this amends a path the run never exercised. The evidence for the mechanism comes from the consuming repo's equivalent stage, and the value here is prospective.

## Alternatives considered

- **Raise the consensus threshold** (require all N passes rather than `ceil(N/2)`). Rejected: it makes the same correlated signal stricter without making it independent, and it drops more true findings.
- **One refuter per finding.** Rejected on cost: the token measurement in `wos/context-budget.md` against a 35-finding set puts this above the cost of the review being checked.
- **Give each raise pass a distinct lens** (correctness, security, performance) instead of adding a refuter stage. Not rejected, and complementary: diverse lenses reduce correlation on the raise side, while refutation tests the survivors. Deferred rather than adopted here because it changes the raise contract, and this ADR keeps ADR-0073's raise stage untouched.
- **Make refutation the default for every review.** Rejected: it would multiply the cost of the common single-pass review, the same reason ADR-0073 made the base mode opt-in.
