# ADR-0184: Express is the default tier, and escalation names its disqualifier

- **Status**: Accepted; superseded in part by [ADR-0233](./0233-the-attended-chain-runs-to-the-draft-pr.md) on attended runs: the Disciplined disqualifier still adds `decision-interview`, which now records provisional decisions and continues instead of waiting. The default tier and the other disqualifiers stand.
- **Date**: 2026-08-31
Supersedes, in part: ADR-0025 (the "classify as Standard when uncertain" default, not the four tiers or their pipelines); ADR-0183 (its Neutral note that the conservative default is untouched)
- **Tags**: express, complexity-routing, task-init, default-tier, adr-0025, adr-0159, friction

## Context

ADR-0025 gave `task-init` four tiers and one tie-breaker: "classify as Standard when uncertain".
ADR-0159 then made Express bind rather than be offered, but only once its three criteria were
affirmatively established. The two together meant a task reached the short pipeline by proving it
deserved one, and anything the model could not confidently classify fell to Standard, which adds
`impact-analysis` before any plan.

That tie-breaker is the friction the maintainer named on 2026-08-31: the workflow stopping for
steps that the work did not need. A dogfood run of the whole Express chain the same day showed the
chain itself asks nothing, over four commands, from prompt to commit. What decides whether a task
gets that experience is one sentence in ADR-0025.

Uncertainty is a poor signal. A model that cannot tell whether a two-file docs change needs
`impact-analysis` is not expressing risk, it is expressing that it has not looked. Routing on that
buys no safety and costs a command.

## Decision

Express is the default tier. `task-init` starts there and escalates only on a NAMED disqualifier,
and the disqualifier is written into `## Recommended pipeline`. An escalation with no named signal
is invalid output.

Uncertainty is explicitly not a disqualifier. "I am not sure" leaves the tier at Express; only a
signal the model can point at moves it.

The four disqualifiers, each checkable rather than felt:

- **Standard** when the scope needs more than one sentence to state, or the change touches 5 or
  more files. Adds `impact-analysis`.
- **Disciplined** when a decision the prompt does not contain is required before the first line of
  code, or the change spans multiple packages or adds an external service dependency. Adds
  `decision-interview`.
- **Strict** when the surface is auth, payments, compliance, PII, or multi-tenant isolation. Adds
  `invariants-and-non-goals`, `test-strategy` and `review-hard`. This one is not a judgment call:
  the surface either is one of those or it is not.

What does NOT change. The four tiers and their pipelines stand. Every safety property ADR-0025
bought stays bought, because each heavier tier keeps its entry condition; what moves is the burden
of proof. The unattended, background and fleet-dispatched carve-out of ADR-0159 stands untouched,
and ADR-0044 D9 is not recut here: this ADR is about the attended default, not about autonomy.

## Consequences

### Positive

- The short pipeline is what an ordinary task gets, rather than what it earns.
- An escalation now carries its reason, so a reader can check the routing instead of trusting it.
  Under the old rule an escalation from uncertainty was unfalsifiable by construction.

### Negative

- A task that genuinely needed `impact-analysis` and shows no listed signal now runs Express and
  finds out later. The exposure is real and it is the price of the inversion. It is bounded by the
  Strict list being categorical, by every tier keeping its entry condition, and by the tier being
  re-checkable at any point: `what-next` re-reads the Express bar on the current known scope.
- "5 or more files" and "more than one sentence" are cheap to game by wording. They were the same
  criteria before, so this is inherited rather than introduced.

### Neutral

- No pipeline changed. A task classified Standard today runs exactly what it ran yesterday.
- The Express criteria of ADR-0159 are unchanged; they simply no longer have to be established
  before the tier applies.

## Alternatives considered

### Alternative 1: keep Standard as the tie-breaker and shorten Standard instead

- Rejected. It leaves the unfalsifiable routing in place and only reduces its cost.

### Alternative 2: run Express for every tier and drop the escalation list

- Rejected as unsafe. The Strict list exists because auth, payments, compliance and multi-tenant
  isolation are where a skipped `invariants-and-non-goals` is not recoverable at review.

## References

- [ADR-0025](./0025-complexity-routing.md): the tiers, and the tie-breaker this inverts.
- [ADR-0159](./0159-express-binds-by-default.md): Express binds rather than offers.
- [ADR-0183](./0183-the-express-bind-stays-at-task-init.md): the bind stays at `task-init`, which
  is where this default now lives.
- [ADR-0044](./0044-autonomous-delivery-track.md): D9 untouched; unattended runs keep their gates.
