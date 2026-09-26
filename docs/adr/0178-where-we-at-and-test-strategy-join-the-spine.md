# ADR-0178: where-we-at and test-strategy join the minimal spine

- **Status**: Accepted; supersedes in part the minimal list of [ADR-0059](./0059-tiered-install-profiles.md) and the count in [ADR-0160](./0160-minimal-profile-skills-install.md).
- **Date**: 2026-08-30
- **Tags**: profiles, minimal-spine, tier-routing, install, adr-0059, adr-0084, adr-0160, dead-end

## Context

The minimal profile is the everyday loop, and the promise it makes is that the loop closes: a run
that starts inside minimal can always reach its next step without asking the operator to install
more. Two routes broke that promise, both of them unconditional and both inside minimal commands.

`commands/implement-approved-slice.md` routes the LAST slice of a multi-slice task to
`where-we-at`, on a line whose own words are "never dead-end the final slice".
`commands/approve-plan.md` routes to `test-strategy` when no `TEST_STRATEGY.md` exists and the
plan's changes carry regression risk. Both targets were `[core, full]`. Measured 2026-08-30, a
`--profile=minimal --dry-run` install copies neither, so both routes named a command the operator
did not have.

The defect was invisible from inside the repository twice over. `check_tier_routing_closure`
reported zero findings, because the exemption it carries was wider than its own docstring says.
And an installed machine did not feel it either: skills mirror at 98 regardless of the command
profile, so the agent could still reach `where-we-at` through the skill even with no command file.
That masking is why this survived; it also means the ADR-0160 follow-up that makes skills inherit
the profile would have turned a paper dead-end into a real one.

This is the third time the same shape has been fixed. ADR-0084's commit-evidence floor made
`branch-commit` and `implement-slice-complement` spine in practice while ADR-0059's list, written
ten days earlier, still said otherwise; D-7 retagged both on 2026-07-25 and made
`tier-routing-closure` a hard check on the strength of it.

## Decision

`where-we-at` and `test-strategy` are `x-wos-profiles: [minimal, core, full]`. The minimal spine is
16 commands.

The rule the retag follows, and the one D-7 followed before it: a command that a minimal command
routes to UNCONDITIONALLY is spine, whatever the tag says. The tag records the tier; it does not
decide it. A conditional route into an opt-in capability cluster stays cross-tier and correct, which
is the distinction `check_tier_routing_closure` already draws.

The count lives in the `count:commands-minimal` marker, not in prose. Every hand-written "14"
describing the spine moves with it, in `README.md`, `scripts/sync-workflow-slash-commands.sh` and
`scripts/tests/test-install-payload.sh`.

## Consequences

### Positive

- The everyday loop closes. A minimal install can finish a multi-slice task and can reach the
  test-strategy gate that `approve-plan` sends it to.
- The ADR-0160 follow-up that makes the skills mirror inherit the profile becomes safe to ship.
  Before this, it would have removed the mask and exposed the dead-end on real machines.
- `check_tier_routing_closure` can have its exemption narrowed to `full`-only targets, which is the
  next item and was blocked on this one.

### Negative

- The minimal install is two commands larger, which is the cost of the promise it makes. Both
  additions are lifecycle commands, not capability-cluster ones, so the surface a newcomer meets
  grows by two familiar names rather than by a new concept.
- Two ADRs now have a superseded number in their body text. Neither body is edited; the Status
  lines carry the supersession, per ADR-0166.

### Neutral

- No command file gains or loses behavior. This is a tag change plus the prose that quotes the count.

## Alternatives considered

### Alternative 1: rewrite the two routes so they never name a non-minimal command

- Have `implement-approved-slice` and `approve-plan` route only within their own tier.
- Rejected: it pays with the two routes that matter most. The last-slice route exists precisely so
  the final slice does not dead-end, and the test-strategy gate exists so a risky plan does not
  reach implementation untested. Removing either to satisfy a tag inverts which one serves the user.

### Alternative 2: leave the tags and widen the check's exemption

- Accept cross-tier routes from minimal as normal.
- Rejected: that is the shape D-7 already refused. It turns the check into a record of what the tree
  happens to do rather than a statement of what it must do, and the dead-end stays for whoever
  installs minimal.

### Alternative 3: make the skills mirror the mask on purpose

- Keep the spine at 14 and rely on skills shipping at 98 so the agent can always route.
- Rejected: it makes correctness depend on an inconsistency between two surfaces, and ADR-0160's own
  direction is to remove that inconsistency.

## References

- [ADR-0059](./0059-tiered-install-profiles.md): the tiered profiles and the original minimal list.
- [ADR-0160](./0160-minimal-profile-skills-install.md): the 14-command figure this supersedes.
- [ADR-0084](./0084-godot-flow-completeness-wave.md): the D-7 precedent that retagged two commands for the same reason.
- `evals/scripts/structural-evals.py`: `check_tier_routing_closure`.
