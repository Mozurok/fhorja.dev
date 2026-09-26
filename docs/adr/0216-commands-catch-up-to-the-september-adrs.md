# ADR-0216: The commands catch up to the September ADRs

- **Status**: Accepted
- **Date**: 2026-09-22
- **Supersedes**: nothing. It completes ADR-0200, ADR-0207 and ADR-0208 in the command tree.
- **Tags**: conformance, tier-label, escalations, stop-reasons, implement-approved-slice, adr-0200, adr-0207, adr-0208

## Context

Three decisions on 2026-09-16 changed how the attended chain routes and when it stops. ADR-0200 made
a bounded audience, not reversibility, the test for an act that may proceed. ADR-0207 retired the tier
labels (Express, Standard, Disciplined) and had `task-init` record the conditions that fired, as
`Escalations:`. ADR-0208 removed the inline Approval log `implementation-plan` wrote on the
no-escalation path, so every plan reaches `approve-plan`.

Swept on 2026-09-22 against the commands and the `wos/` topics, which are what a model reads at run
time. The most serious finding was a rule that could no longer fire. `implement-approved-slice` routed
the last slice to `branch-commit --apply` only "when the pipeline is Express", and `what-next` re-checked
"the Express tier". After ADR-0207 the pipeline records `Escalations: none` and never names a tier, so
neither condition could be true. The last-slice commit still happened in scenario 137 because the model
read `Escalations: none` as the old name. That is inference standing in for the rule, and a more literal
model would not have committed.

The same sweep found the ADR-0200 wording still in a shared block and so in five commands: a chain
stops for "an outward or irreversible act". It found `task-init-fleet`'s worker contract still carrying
an enum of the retired tier names, which a worker running today's `task-init` cannot honestly fill, and
`wos/operating-modes.md` describing strict mode's precedence over an inline Approval log ADR-0208
removed.

## Decision

Each rule keyed on a retired tier name is translated to the escalations that replaced it, preserving
its scope exactly. "The pipeline is Express" becomes "the pipeline records `Escalations: none`", which is
what Express meant under ADR-0184. Whether the last-slice commit should also fire on a path with
escalations is a separate decision and is not taken here.

The shared block's stop reason now reads "an act whose audience is not bounded", propagated to its five
commands. `task-init-fleet` emits `escalations` (a list, empty for none) instead of a tier. The strict
precedence note describes what strict decides now, what comes before `approve-plan`.

`check_no_condition_on_a_retired_tier_name` fails on a command that gates behavior on a tier name in a
conditional position, and spares a line that names the tier as retired, so the history notes stay.

## Consequences

### Positive

- The last-slice commit rests on the rule rather than on a model's reading of a renamed field.
- A future rule keyed on a retired name fails the build instead of dying quietly, the way these did for
  six days.

### Negative

- The check matches a conditional shape. A condition on a retired name phrased another way passes it.
- Translating preserved scope, which means the commit still fires only on the no-escalation path. That was
  the rule before ADR-0207 too; this does not decide whether it is the right scope.

### Neutral

- A sweep of the scenarios, the user docs and the command tree for the September vocabulary now comes back
  clean apart from lines that name a retired term in order to say it is retired.

## References

- [ADR-0207](./0207-the-default-behavior-has-no-name.md): the labels this removes the last live uses of.
- [ADR-0208](./0208-plan-approval-self-runs.md): the inline Approval log.
- [ADR-0200](./0200-bounded-audience-replaces-reversibility.md): the stop reason.
