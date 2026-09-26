# ADR-0182: The minimal spine closes its own routes, at 19 commands

- **Status**: Accepted
- **Date**: 2026-08-31
- **Tags**: spine, minimal-profile, tier-routing, adr-0084, adr-0088, adr-0178

## Context

`check_tier_routing_closure` held two documented exemptions in `TIER_ROUTE_OPEN`, both opened on
2026-08-30 when the check's exemption was narrowed to require a full-only target. Both were routes
from a minimal command to a target the minimal profile does not install.

The stronger one: `review-hard -> incident-triage`. ADR-0088 makes triage the FIRST ACTION on a
runtime-debug payload, so a minimal session that pastes a crash log is told to run a command it
does not have. That is not a menu, it is an obligatory hop on a common entry.

The weaker one: `decision-interview -> capture-references`, where the abstention rule names three
investigation commands as examples and a minimal session had none of them.

The first plan was to promote `incident-triage` alone, taking the spine from 16 to 17.

## Decision

Seventeen does not close. Promoting `incident-triage` drags its own outbound routes into the tier
question: it routes to `capture-observation` and `capture-references`, both core and full. Measured
2026-08-31 by promoting and re-running the check, the count of findings went from one to two.

The transitive closure terminates at three promotions and does not cascade further:
`incident-triage`, `capture-observation`, `capture-references`. The minimal profile goes from 16 to
19 commands, `TIER_ROUTE_OPEN` becomes empty, and the check passes with no exemption at all.

Nineteen is also the coherent number rather than merely the reachable one. The abstention rule in
`commands/_shared/claim-grounding.md` is carried by 98 of 98 commands and routes to
`capture-references` when grounding is missing. A profile that can abstain but cannot run the
remedy it names is incomplete on its own terms, and `capture-references` arguably belonged in the
spine before this question was asked.

The empty dict stays in the file with a comment rather than the mechanism being deleted, so a
future cross-tier route is recorded the same way rather than reopening the argument.

## Consequences

### Positive

- The minimal profile no longer routes anywhere it cannot reach. Zero exemptions, not two.
- ADR-0088's first-action rule holds in every profile that carries `review-hard`.
- The abstention rule's remedy is installed wherever the rule is.

### Negative

- Three more commands in the smallest install. The spine's promise is that the everyday loop
  closes (ADR-0178), and this widens what "everyday" includes.
- A future promotion into minimal carries the same transitive cost, which is now visible rather
  than surprising.

### Neutral

- No command text changed. Only the `x-wos-profiles` line in three files, and the count markers
  the generators derive from them.
- The shared claim-grounding block was NOT edited. A first attempt reworded its menu to name a
  command the minimal profile had; the closure made that unnecessary, because two of the three
  commands the menu already named are now in minimal. The 98-command edit was reverted.

## Alternatives considered

### Alternative 1: promote `incident-triage` alone, spine 17

- Rejected on measurement. It leaves two findings where there was one, so it trades a documented
  exemption for an undocumented hole.

### Alternative 2: stay at 16 and keep both exemptions

- Coherent, and the honest fallback. Rejected because the stronger of the two is an obligatory
  route on a common entry, not a menu, so the exemption records a defect rather than a design.

### Alternative 3: reword `review-hard` to route within its tier

- Rejected. ADR-0088 says triage is the first action on that payload. Rewording the route makes the
  command say one thing and the ADR another.

## References

- [ADR-0084](./0084-godot-flow-completeness-wave.md): the tier-routing closure rule this satisfies.
- [ADR-0088](./0088-debug-loop-instrument-first-and-ruled-out-ledger.md): why the review-hard route is obligatory.
- [ADR-0178](./0178-where-we-at-and-test-strategy-join-the-spine.md): the previous spine change and
  the promise the spine makes.
- `evals/scripts/structural-evals.py`: `TIER_ROUTE_OPEN`, now empty.
