# ADR-0229: The minimal profile reaches its reviewer, at 23 commands

- **Status**: Accepted
- **Date**: 2026-09-23
- **Supersedes**: nothing. It follows ADR-0178 and ADR-0182 and narrows the exemption ADR-0178 set in `check_tier_routing_closure`.
- **Tags**: spine, minimal-profile, tier-routing, verify-against-rubric, adr-0145, adr-0178, adr-0182, adr-0208

## Context

Two minimal commands dispatch `verify-against-rubric`. `approve-plan` runs one blinded review
before it appends the approval log (ADR-0208), on every plan. `review-hard` SHALL route to it when
a verdict names zero findings on a product diff (ADR-0145). Until today `verify-against-rubric`
was tagged `[full]`, so a minimal install approved plans and closed reviews against a reviewer it
did not have. ADR-0182 had recorded that "the minimal profile no longer routes anywhere it cannot
reach", and the check that was meant to keep that true reported nothing.

The check was blind for a reason. ADR-0178 narrowed its exemption for gated routes to targets
that are full-only, on the reasoning that `full` partitions by cluster membership, so a full-only
target is an opt-in cluster command. `verify-against-rubric` is full-only and belongs to no
cluster. `review-hard -> verify-against-rubric` reads "WHEN this review's verdict names zero
must-fix ...", so it passed as a gated entry into a cluster. `approve-plan`'s dispatch is not seen
at all, because it says "dispatch" and the check reads "route to"; adding "dispatch" to the
pattern was tried and does not help.

## Decision

`verify-against-rubric` joins the minimal and core profiles with its transitive closure. Retagging
it alone fails the hard check, measured today: it routes to `direction-adjust` and
`resolve-contract-gaps`, both `[core, full]`, and once those two move, `resolve-contract-gaps`
routes to `contract-signoff`. The closure stops at four commands, so minimal goes from 19 to 23
and core from 50 to 51. The four skill descriptions add about 740 tokens to the minimal listing,
measured from `docs/command-catalog.json` on the same day.

The exemption in `check_tier_routing_closure` stops inferring cluster membership from a tag. A
gated route is exempt only when its target is named in `CAPABILITY_CLUSTERS` in
`evals/scripts/structural-evals.py` and is still full-only. A member later retagged into core
therefore loses the exemption instead of keeping it, and a gated route into a full-only command
that no cluster names is a finding. The registry lists the six clusters a gated route from a lower
tier reaches today, each with all of its members.

Every pair the old exemption covered was checked before the change:

- `approve-plan`, `implement-approved-slice` and `implementation-plan` to `implement-fleet`: the
  fleet, gated on a remaining wave of size 2 or more. The in-tier path is `implement-approved-slice`,
  one slice at a time. Stays exempt.
- `branch-commit` to `task-workspace`: opt-in per-task worktree isolation (ADR-0074), offered beside
  the in-tier choice of naming the branch. Stays exempt.
- `implement-approved-slice` to `web-runtime-verify`: runtime verification, gated on the web
  signature. Stays exempt, with the cost named below.
- `implementation-plan` to `unity-scene-plan`: game development, gated on a Unity target. Stays exempt.
- `incident-triage` to `postmortem-author`: reliability, gated on a significant resolved incident.
  Stays exempt.
- `security-review` to `mcp-server-vet`: third-party vetting, gated on an agent or MCP surface. The
  router is core. Stays exempt.
- `review-hard` to `verify-against-rubric`: not a cluster command. Closed by this retag.

A guard mutation retags `verify-against-rubric` back to `[full]` over a fixture of the real
`review-hard` and the four commands, and the check has to fail. Run against the check as it stood
before this change, that mutation did not bite.

## Consequences

### Positive

- A minimal install carries the reviewer `approve-plan` and `review-hard` dispatch, so ADR-0182's
  sentence is true again, and it is true for the ADR-0208 approval as well as ADR-0145.
- Cluster membership is written down. Adding a full-only persona that is not in a cluster no longer
  widens the exemption silently.

### Negative

- Four more commands and about 740 more listing tokens in the smallest install. Same trade as
  ADR-0182: the spine's promise is that the loop closes, and closing it costs what the closure costs.
- `CAPABILITY_CLUSTERS` is a hand-kept list. A new gated route into an unlisted cluster fails until
  someone adds the cluster, which is the point, and also a chore.
- A minimal install on a web task still meets a runtime floor it cannot satisfy without adding the
  runtime-verification cluster. That is an opt-in cluster by design, and this ADR leaves it that way.

### Neutral

- Only the `x-wos-profiles` line of the four commands changes. No command body is edited.
- `approve-plan`'s dispatch stays invisible to the check's route patterns. The retag closes the gap
  it would have shown; the pattern is unchanged.

## Alternatives considered

### Alternative 1: retag `verify-against-rubric` alone

- Rejected on measurement. The hard check fails with two findings, then one, until all four move.

### Alternative 2: keep the full-only exemption and add the reviewer to `TIER_ROUTE_OPEN`

- It would record the gap and leave it open. The route is a SHALL on a common path, and the
  approval dispatch fires on every plan, so this is a defect rather than a menu. ADR-0182 rejected
  the same shape for the same reason.

### Alternative 3: derive the registry from `metadata.category`

- The categories are a lifecycle partition, not clusters. The seven fleet variants sit in six categories,
  and `planning-and-validation` holds both `verify-against-rubric` and `release-plan`. A category
  test would repeat the mistake the full-only test made.

## References

- [ADR-0145](./0145-a-zero-finding-verdict-is-not-terminal.md): the review-hard route.
- [ADR-0178](./0178-where-we-at-and-test-strategy-join-the-spine.md): the full-only exemption this narrows.
- [ADR-0182](./0182-the-minimal-spine-closes-its-own-routes.md): the previous closure and its promise.
- [ADR-0208](./0208-plan-approval-self-runs.md): the approval dispatch.
- `evals/scripts/structural-evals.py`: `CAPABILITY_CLUSTERS` and `check_tier_routing_closure`.
- `evals/scripts/guard-mutation.py`: `mutate_reviewer_back_to_full`.
