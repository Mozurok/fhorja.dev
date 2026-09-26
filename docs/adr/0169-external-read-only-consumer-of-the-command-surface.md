# ADR-0169: An external read-only consumer of the command surface

- **Status**: Accepted
- **Date**: 2026-08-30
- **Tags**: commands, command-catalog, read-only-interface, external-consumer, mit-boundary, catalog-cut

## Context

A separate execution layer, built and maintained outside this repository, reads this repository. It opens `commands/*.md` and `docs/command-catalog.json`, parses the `### Handoff` block a command emits, and drives its own loop from what it read. It never writes into this tree, it opens no pull request here, and its roadmap is not this repository's roadmap. This file calls it an external read-only consumer and names nothing about it, on purpose.

The relationship was real but undeclared. A 2026-08-29 audit found the consequence: a plan to remove commands from the catalog treated `commands/` as an internal surface with no readers outside an editor session. That is false. Deleting or renaming a command file here can break a parser that lives in no file of this repository and is covered by none of its tests.

The consumer parses fail-closed by design: an input it cannot parse is a refusal, not a guess. That is a safety property where it runs and a hazard here, because a rename this repository considers cosmetic arrives there as a refusal.

Two things are already true and stay true. This repository is MIT and the consumer is not distributed under it; nothing flows from the consumer into this tree. And the spec here already describes obligations of an execution layer it does not implement: `ref-attested` in `wos/closure-floors.md`, the commit route in `wos/autonomous-track.md`, and the `### Handoff` contract. Describing an obligation is not implementing one.

## Decision

`commands/*.md` and `docs/command-catalog.json` are a read-only interface with at least one declared external consumer. What the interface promises is what those files say; this repository keeps deciding its own contents and adds nothing because an outside consumer wants it.

Four rules follow:

- Read-only in one direction. No external consumer writes into this repository, and no feature is added here to serve one.
- Removing a command, renaming a command, or changing the shape of the `### Handoff` block is an interface change. A slice that does any of those SHALL record, in its own ADR or in its slice notes, that the paired check against the external consumer was run and what it returned, or that the owner authorized the change with the consumer left untouched. A cut with neither record is incomplete, not merely risky.
- The prose in this repository that describes an execution layer's obligations stays. Deleting it would break the contract the consumer tests against, and it costs this repository nothing to keep.
- No tracked file in this repository names the external consumer, its repository, its file paths, or the machine it runs on. `an external read-only consumer` is the term.

## Consequences

### Positive

- A catalog cut has a declared blast radius. The paired check is part of the slice, not something someone remembers.
- The MIT boundary now lives in a tracked file. Archiving the planning notes that carried it loses nothing.
- A reader of this repository learns that `commands/` is an interface, which is the fact that was missing when the cut was first planned.

### Negative

- One extra verification step per removal or rename, run by hand by someone with access to the consumer. CI cannot run it.
- This repository records a dependency it does not control and cannot test. The rule is procedural and depends on the executor honouring it.

### Neutral

- The catalog stays free to shrink. This is a record-and-check rule, not a veto.
- The rule is written for any external consumer, not for one. A second consumer needs no new ADR.

## Alternatives considered

### Alternative 1: leave the relationship undeclared

- Nothing is written down; whoever cuts the catalog is expected to remember.
- Rejected: that is the state that produced the defect. An audit had to rediscover the consumer from planning notes that were about to be archived.

### Alternative 2: add the consumer to this repository's CI

- A CI job checks out the consumer and runs its parser against the catalog.
- Rejected: the consumer is private and CI has no access, and it would make an MIT repository's build depend on a repository nobody outside can clone.

### Alternative 3: freeze `commands/` as a stable public API

- Command names and the `### Handoff` shape become immutable.
- Rejected: it hands the evolution of the catalog to a single consumer and forbids removals this repository has good reasons to make.

## References

- `commands/` and `docs/command-catalog.json` (the interface this ADR describes).
- `wos/closure-floors.md` and `wos/autonomous-track.md` (the execution-layer obligations the spec describes but does not implement).
- `LICENSE` (MIT; the boundary this ADR records in a tracked file).

## Notes

Written before any catalog cut, so the cut waves can cite it. Revisit if this repository ever gains an in-tree execution layer of its own, which would make the reading direction bidirectional and this ADR incomplete.
