# ADR-0156: The nine persona commands are verifiable, closing the last routing-coverage gap

Date: 2026-08-17

Status: Accepted

## Context

ADR-0155 D-6 left one item open, and named it as the prerequisite for any further work on
description trimming:

> The 9 folder-format persona commands have no routing case in `cases-89.json` (generated from
> the 89 flat files), so their trims can pass the structural gates but cannot be verified;
> writing cases for them comes first.

That gap had already been paid once: `post-deploy-verifier` was trimmed in the ADR-0154 batch and
its trim satisfied the reference, marker and floor checks with no routing measurement behind it.

The nine are `a11y-audit`, `color-contrast-architect`, `jtbd-switch-interviewer`,
`migration-safety-steward`, `performance-budget`, `post-deploy-verifier`, `postmortem-author`,
`rls-auth-boundary-auditor`, `slo-define`.

## Decision

**D-1. Cases for the nine, written blind, split across three writers.** Same method as ADR-0152 D-1:
each writer read only a frontmatter-stripped copy of the command body, never the `description` under
test. The nine were split three-and-three rather than given to one writer, because a writer holding
`slo-define` and `performance-budget` side by side tends to calibrate one against the other and
produce a pair that separates more cleanly than real requests do. Validated mechanically against all
98 skills: 98 of 98 covered, 0 cases naming any command, 0 sharing a three-word phrase with their own
description, 0 near-duplicate pairs across the whole set.

**D-2. The case set is now complete, and both files are kept.**
`evals/fixtures/routing-probe/cases-98.json` covers every skill. `cases-89.json` stays on disk
because ADR-0152, ADR-0153 and ADR-0155 report results measured against it, and ADRs are immutable:
deleting the input would make those numbers irreproducible.

**D-3. The measurement.** All 98 commands present in every prompt, 98 cases, 3 replicates:

| Condition | All 98 | The nine personas |
|---|---|---|
| A_full | 100% | 27 of 27 |
| C_gut (opener only, 24.8% of size) | 100% | 27 of 27 |
| D_shuffled | 0% | 0 of 27 |

The control collapsed completely, so the probe reads the descriptions at this scale too. Every one of
the nine routes correctly, including under the most aggressive condition, and including the adjacent
pairs the split was designed to stress: `slo-define` against `performance-budget`, `a11y-audit`
against `color-contrast-architect`, `migration-safety-steward` against
`rls-auth-boundary-auditor`.

**D-4. `post-deploy-verifier`'s existing trim is verified retroactively.** It was trimmed in ADR-0154
without routing evidence. It now routes 3 of 3 in both A and C. The debt ADR-0154 D-4 recorded is
paid rather than merely aged.

**D-5. No collision survives in any condition.** The scrub-collision that ADR-0152 D-4 traced to the
two `-fleet` openers was fixed in commit `6347aa7`; re-checked here across all 98 in A, B and C,
identical-after-scrub groups are zero. The single misroute in the ADR-0152 run has no counterpart in
this one.

## Consequences

- Routing coverage is complete: every skill in the corpus has a case, and any future description edit
  anywhere can be verified rather than assumed.
- Trimming the nine is now possible with the same evidence standard as the other thirty. This ADR does
  not do it: ADR-0155 D-4 stopped the trim on marginal value, and that judgement is unchanged by the
  gap closing. What changed is that the option is no longer blocked.
- C_gut reaching 100 per cent across all 98 is the strongest version of the ADR-0152 D-3 finding, and
  it now rests on a complete corpus rather than on 89 of 98 with the hardest nine excluded.
- The cost of this ADR was three writer agents, nine agents of measurement, and one fixture file. That
  is the cheapest instalment in this series, because the harness and the method already existed.
