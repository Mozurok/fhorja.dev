# ADR-0187: The ADR corpus is the record, not the rulebook

- **Status**: Accepted
- **Date**: 2026-09-01
- **Tags**: adr-corpus, change-policy, agents-md, accretion, adr-0166, adr-0172, friction

## Context

The maintainer named the cost on 2026-08-31: writing ADR-899998897 because ADR-1 holds a rule that
no longer fits. He chose the route that separates the historical record from the normative source.

The pressure is structural. When a rule lives inside an ADR body and ADR bodies are immutable, the
only way to change the rule is a new ADR. The corpus grows once per rule change rather than once
per decision, and a reader has to reconstruct the current rule by walking a supersession chain.

ADR-0172 already made this move for one shape: an operational table that needs maintenance lives in
`wos/`, not in an ADR. This generalizes it from tables to rules.

## Decision

A rule lives in an editable surface: `WORKFLOW_OPERATING_SYSTEM.md`, `wos/`, `commands/`, or
`AGENTS.md`. An ADR records why a decision was made. Changing a rule means editing the surface that
holds it, and an ADR is written when the decision is load-bearing, not because the text needs to
move.

`AGENTS.md` gains section 6, the live home for the change policy: where a rule lives, when an ADR
is warranted, how supersession is marked (ADR-0166), and that an uncited ADR stating no rule is
finished rather than neglected.

`docs/adr/README.md` keeps the Index and the status vocabulary and loses the policy prose. Its
Format section now says plainly that the directory is the record, not the rulebook.

## What the measurement changed about this wave

The plan this ADR closes promised seventeen Decision-block hoists over about 1410 lines, "one
judgment each, not batchable". Measured on disk 2026-09-01, against a live surface set of the spec,
`wos/`, `commands/`, `templates/`, `AGENTS.md`, `CLAUDE.md`, `README.md`, the eval scenarios and the
scripts:

- 185 ADRs on disk.
- 27 carry RFC-2119 normative language in their Decision block.
- 26 are cited from no live surface at all.
- The intersection, an ADR whose rule has no live home, is **two**.

Both were given one here. ADR-0092's read-only guarantee for `scripts/flow-audit.py` and its
advisory lint line, and ADR-0169's interface rule for removing or renaming a command or changing
the `### Handoff` block shape, are now stated in `AGENTS.md` where they can be edited and read.

The other 24 uncited ADRs state no rule. They are the historical record working as intended and
need nothing, which is what this decision says out loud so a later reader does not mistake them for
a backlog.

A first attempt to find the orphan set by matching normative sentences verbatim against the live
corpus returned 27 of 27, which is an artifact: an ADR states a rule in its own words and a spec
states it in its own. That measurement was discarded rather than reported.

## Consequences

### Positive

- A rule change edits one surface. The corpus stops growing once per wording change.
- The change policy is in the file every agent working in this tree already reads, instead of at
  the bottom of a 243-line index nothing links to. Nothing outside `docs/adr/README.md` referenced
  the three policy sections, measured before the move.
- The uncited-and-ruleless class is named, so 24 files stop looking like unfinished work.

### Negative

- `AGENTS.md` grows from 61 lines to 88. It is the always-read build file for this tree, so every
  line there is paid on every session that touches the repo. Accepted because the policy it now
  carries was already being paid, indirectly, as ADRs nobody could edit.
- "Load-bearing" stays a judgment. This decision does not make the ADR-or-not call mechanical, and
  a maintainer who writes one too many still ends up where the complaint started.

### Neutral

- No ADR is deleted, renumbered, or rewritten. Immutability of Decision text is unchanged and
  restated.
- The Index, the count marker, the index-row guard and `check-doc-sync.sh` are untouched: 185 files,
  185 rows, all references still resolve.

## Alternatives considered

### Alternative 1: a new `## Change policy` H2 in the spec

- Rejected. The spec is the workflow contract a Fhorja user consumes; how this repository's own ADRs
  are written is not part of it. `AGENTS.md` is already declared as the home for build and writing
  rules in this tree, and it already carried the immutability bullet this replaces.

### Alternative 2: hoist all 27 normative Decision blocks

- Rejected on measurement. 25 of the 27 are cited from a live surface that already carries the rule,
  so hoisting them would duplicate text rather than relocate it, and duplicated normative text is
  the drift this repository keeps paying for.

### Alternative 3: delete the 24 uncited ADRs

- Rejected. It is the route the maintainer did not choose, it buys nothing the freeze does not, and
  `check_adr_indexed` reads `docs/adr/README.md` with no existence guard, so a corpus deletion takes
  the whole structural runner down rather than failing one check.

## References

- [ADR-0166](./0166-supersession-is-marked-on-the-superseded-adr.md): the Status line is maintained
  metadata, which this depends on.
- [ADR-0172](./0172-operational-tables-live-in-wos-not-in-adrs.md): the same move, for tables.
- [ADR-0092](./0092-flow-audit-dryrun-and-healthy-spine.md): one of the two rules given a live home.
- [ADR-0169](./0169-external-read-only-consumer-of-the-command-surface.md): the other.
- `docs/DELETION_LEDGER.md`: what came out of `docs/adr/README.md` and why.
