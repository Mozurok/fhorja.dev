# ADR-0166: Supersession is marked on the superseded ADR

- **Status**: Accepted
- **Date**: 2026-08-30
- **Tags**: adr-hygiene, structural-evals, immutability, metadata-vs-decision, extends-adr-0029

## Context

ADRs are immutable by design: a reversed decision gets a new ADR, never a patched old one.
That rule protected the DECISION text and left the METADATA unmaintained. Measured 2026-08-29,
five ADRs had been superseded in whole or in part with nothing in their own Status line saying
so, and two of the superseding ADRs declared the supersession only in body prose, invisible to
any header-level reader or guard.

A reader who opens the superseded file follows a decision that no longer holds. That is the
failure this closes.

## Decision

An ADR's Status line is maintained metadata, not immutable decision text. When ADR B supersedes
ADR A in whole or in part, B declares it in a header line within its first 15 lines, and A's
Status line names B and the scope of what was superseded. The precedent is ADR-0019, which has
carried exactly this apposition since 2026-06-04.

`check_supersession_marked` in `evals/scripts/structural-evals.py` enforces both halves. It
reads only the first 15 lines of each file, so a declaration buried in body prose does not
satisfy it: the header is where a reader looks.

The check is deliberately one-directional. It walks from a declared supersession to the target's
Status line, so an ADR that supersedes another and declares it nowhere stays invisible to it.
That blind spot is named here rather than hidden: the half worth enforcing is the one a reader
hits, and closing the other half would mean inferring intent from prose.

What stays immutable: `## Context`, `## Decision`, `## Consequences`. This ADR authorizes
editing the Status line and adding a Supersedes header line, nothing else.

## Consequences

Adding an ADR that supersedes another now means two edits, and the check fails the build if the
second one is missing.
