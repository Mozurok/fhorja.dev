# ADR-0205: The final report lists every floor left unverified

- **Status**: Accepted
- **Date**: 2026-09-16
- **Tags**: task-close, closure-floors, reporting, adr-0203
- **Supersedes**: None

## Context

This is the visible half of the decision immediately preceding it; it replaces no decision.

ADR-0203 lets nine floors record `unverified:` and proceed. A record nobody reads is
indistinguishable from a skip, which would make that decision a quiet removal rather than a trade.

When ADR-0203 shipped, a grep over `commands/*.md` and `wos/*.md` found no carrier for the report it
assumed.

## Decision

`task-close` emits an `### Unverified floors` block: one row per floor that recorded `unverified:`
across the task's slices, naming the floor, the slice it fired on, and the reason recorded verbatim.

It is BUILT FROM those recorded lines, never re-derived at closing time. A re-derived report is a
second check, and a second check that disagrees with the first leaves the reader unable to tell which
one ran.

WHEN no floor recorded, the block reads `none` rather than being omitted. An absent block and a clean
run look identical to a reader.

## Consequences

Positive. ADR-0203's trade becomes visible at the point a person is already reading.

Negative. The block is prose a command is told to emit, not a function that runs. Nothing asserts a
real `task-close` produces it, and no eval covers it yet.

Neutral. It adds 660 characters to `task-close`, which stays outside the ADR-0116 warning band.

## Alternatives considered

Report at slice level too. Rejected: the list is a whole-task artifact, and two sources for one list
is how they diverge.

Re-derive the list at closing time. Rejected for the disagreement problem above.

## References

- ADR-0203: the decision this makes visible.
- ADR-0116: the size ceiling checked before adding to a closing command.
