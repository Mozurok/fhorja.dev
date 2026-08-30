# ADR-0164: Engagement provenance is redacted from the historical record

- **Status**: Accepted
- **Date**: 2026-08-29
- **Tags**: confidentiality, mirror-hygiene, adr-immutability-exception, changelog, roadmap, extends-adr-0090

## Context

Twelve lines across five tracked files named the engagement a 2026-06-05 design-discovery run
was performed for: the product it shipped on, the two flows it traced, and the phrase that
labelled a whole coverage batch after the client. The same twelve lines are present in the
public mirror. Two of the five files are ADR bodies, which the repository treats as immutable.

A public repository that names whose work it was is a confidentiality problem no reader can
undo, and it recurred: this is the fourth pass of the same class, after the three recorded in
the mirror-sanitization history.

## Decision

The product nouns are replaced by neutral ones. The workflow telemetry stays verbatim: agent
counts, token counts, wall-clock, atom and route counts. That telemetry identifies nobody and
is the empirical ground ADR-0038 and ADR-0039 cite; removing it would delete the evidence
those two decisions rest on.

Editing the body of ADR-0041 and ADR-0148 in place is recorded here as the SECOND exception to
ADR immutability. The first is recorded in ADR-0090 and its CHANGELOG entry, the 2026-07-10
in-place codename redaction. The exception is narrow: a confidentiality defect in an already
published record can only be fixed where it was written, and a successor ADR alone leaves the
leaked text in place.

The replacements are applied by `scripts/redact-engagement-provenance.py`, which substitutes
exact strings and never line numbers, so the same script runs unchanged against both trees.

## CHANGELOG audit (G5)

Measured 2026-08-29: 162113 chars over 264 lines, five `## ` version headings, `## [Unreleased]`
present, already covered by the lint forbidden-byte scan and by count markers. No structural
repair is pending; the file's only defect was the engagement provenance this ADR removes.

## Consequences

The mirror guard gains a third structural scan for this class (a separate slice), so a
reintroduction fails the build instead of waiting for a human reader.
