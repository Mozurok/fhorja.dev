# ADR-0221: The unattended track keeps its reversibility limit

- **Status**: Accepted
- **Date**: 2026-09-23
- **Supersedes**: nothing. It states the reach of ADR-0200 and narrows the merge route ADR-0044 named.
- **Tags**: autonomous-run, unattended, merge-gate, review-hard, approve-proposed, adr-0044, adr-0199, adr-0200, adr-0208

## Context

ADR-0200 changed the criterion for when an act stops the chain: an act clears when the set of people
it reaches is bounded, and "undo decides nothing, in either direction". It was written about a session
with a person in it, and it does not say whether it reaches the autonomous delivery track.

`commands/autonomous-run.md` still said the controller "MUST NOT commit, merge, deploy, or take any
irreversible step", which is the reversibility criterion ADR-0200 replaced. Its merge gate routed the
PROPOSED slice diffs to `approve-proposed` and `review-hard`. Since ADR-0199, `approve-proposed` is
invoked only for the ADR-0034 case, a non-owner's PROPOSED block inside a section it does not own. A
product diff from an unattended run is not that case.

The 2026-09-22 documentation drift audit flagged both lines and asked whether ADR-0200 covers the track.
ADR-0208 had already answered a sibling question the same way: "The autonomous delivery track keeps its
own entry gate", because its premise is that nobody is watching (ADR-0044).

## Decision

ADR-0200's bounded-audience test covers attended sessions. The unattended track keeps the ADR-0044
limit as written: the controller never commits, merges, deploys, or takes an irreversible step, and a
human merge gate stands between its diffs and any of those.

The merge gate routes the PROPOSED slice diffs to `review-hard`, and a human performs the merge.
`approve-proposed` leaves the route.

## Consequences

### Positive

- `autonomous-run` no longer hands its diffs to a command whose description excludes them.
- The track's limit and its reason agree: with nobody watching, whether an act can be undone matters,
  because nobody is there to notice it needs undoing.

### Negative

- The spine and the track now use two different criteria for the same kinds of act. A reader has to
  know which kind of session they are in.

### Neutral

- Nothing changes in the attended spine. `pr-package --apply` and `branch-commit --apply` keep the
  ADR-0200 criterion.

## Alternatives considered

### Extend ADR-0200 to the unattended track

- The limit would be written in audience terms, so a push to a task branch would clear.
- Rejected: ADR-0200 reasons from a person who can see and stop what reached a bounded audience. The
  track's premise is that no such person is present, and ADR-0208 kept the track's gates for the same
  reason.

## References

- `commands/autonomous-run.md`, the `Two gates, never auto-merge (D6)` rule and Required output items 5 and 8.
- ADR-0044 (D6), ADR-0199, ADR-0200, ADR-0208.
