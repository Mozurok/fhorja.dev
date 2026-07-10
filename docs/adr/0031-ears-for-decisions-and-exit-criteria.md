# ADR-0031: EARS notation for DECISIONS.md entries and slice exit criteria

- **Status**: Accepted
- **Date**: 2026-06-04
- **Tags**: contract-clarity, requirements-notation, ears, decisions, exit-criteria, ambiguity-prevention

## Context

The WOS already separates decisions (`DECISIONS.md`) from facts (`SOURCE_OF_TRUTH.md`) and routes ambiguity recovery through `resolve-contract-gaps`. But the canonical sentence used to record a decision or an exit criterion was free-form prose, which let weasel words slip in: "the system should support multi-region", "exit criteria: feature works as expected", "the API may handle retries appropriately".

Free-form prose has two failure modes:

1. **Ambiguity discovered late.** `resolve-contract-gaps` exists to catch ambiguity, but by the time it runs the gap has often already shaped `IMPLEMENTATION_PLAN.md` and `SLICES/`. Catching ambiguity at the entry point in `decision-interview` and at slice definition in `implementation-plan` is cheaper.
2. **No structural signal that the sentence is normative.** A future reader of `DECISIONS.md` cannot quickly distinguish a load-bearing commitment from supporting prose. The canonical sentence reads the same as the rationale.

The AWS Kiro adoption (internationally GA 2026-05-07) made EARS notation widely known in agentic engineering tools. Kiro reported a 60% defect rate in first-draft requirements when EARS was not used, dropping sharply when EARS templates were enforced. The notation is also documented at `alistairmavin.com/ears` and is the established style in safety-critical engineering communities. Adopting EARS in WOS is a low-cost notation upgrade with empirically validated benefits and zero infrastructure cost.

## Decision

Canonical sentences in `DECISIONS.md` entries and slice exit criteria in `IMPLEMENTATION_PLAN.md` MUST use one of the five EARS templates:

- **Ubiquitous:** `The <system> SHALL <response>`
- **Event-driven:** `WHEN <trigger> the <system> SHALL <response>`
- **State-driven:** `WHILE <state> the <system> SHALL <response>`
- **Optional feature:** `WHERE <feature included> the <system> SHALL <response>`
- **Unwanted behavior:** `IF <trigger> THEN the <system> SHALL <response>`

Free-form prose for rationale, alternatives considered, and supporting context is OK around the canonical sentence. The canonical sentence itself must use SHALL and must not contain weasel-word softeners:

- Banned in canonical sentence: `should`, `may`, `appropriate`, `sensible`, `reasonable`.

For slice exit criteria, event-driven form is preferred because slices have observable triggers (a build completes, a test passes, a file lands): `WHEN pnpm -r typecheck completes the build SHALL exit 0`. The rationale and acceptance details live around the sentence.

Enforcement is in command files:

- `commands/decision-interview.md` Operating rules require EARS in DECISIONS.md updates.
- `commands/implementation-plan.md` per-slice exit-criteria field requires EARS.

Future opportunity (not enforced by this ADR): `scripts/lint-commands.sh` could grep for SHALL-less canonical sentences in `DECISIONS.md` / `IMPLEMENTATION_PLAN.md` under `projects/*/active/*/` and warn. Tracked as a follow-up.

## Consequences

### Positive

- Ambiguity caught at the decision/plan entry point instead of at `resolve-contract-gaps` (cheaper to fix).
- DECISIONS.md becomes machine-scannable: every canonical sentence has SHALL; rationale prose does not. Future tooling (lint, retrieval) can target the SHALL lines.
- Exit criteria become verifiable: an EARS-shaped exit criterion either passes or fails; "feature works" cannot pretend to pass.
- Matches the notation that Kiro users already know, reducing cognitive load for engineers who switch between tools.

### Negative

- Slightly more ceremony per decision entry. Writers must pick a template and rephrase to avoid softeners.
- Some edge-case decisions are awkward in pure EARS (e.g., "we will use library X" -- ubiquitous works but feels stilted). Acceptable cost; the alternative is a notation that catches no ambiguity.

### Neutral

- Existing entries in `DECISIONS.md` are not retroactively rewritten. New entries adopt EARS; old entries remain in their existing prose until the next time they would be edited anyway.
- Adopting EARS does not change which commands run or when they run; it only constrains the canonical sentence shape inside entries those commands produce.

## Alternatives considered

### Alternative 1: Stay with free-form prose

- Rejected: documented failure mode of `resolve-contract-gaps` catching ambiguity that should have been caught at `decision-interview`. Kiro's 60% defect-on-first-draft data is consistent.

### Alternative 2: Adopt a heavier formal-methods notation (TLA+, Alloy, Z)

- Rejected: too heavy for solo-founder WOS work. EARS is a notation upgrade; formal methods are a different engineering discipline that the WOS does not need.

### Alternative 3: Free-form with banned-word list only (no SHALL requirement)

- Rejected: removes some ambiguity but does not provide a structural marker for "this is the load-bearing sentence". Half measure with most of the cost and less of the benefit.

## References

- `commands/decision-interview.md` -- enforces EARS in DECISIONS.md entries.
- `commands/implementation-plan.md` -- enforces EARS in slice exit criteria.
- `alistairmavin.com/ears` -- canonical EARS reference.
- ADR-0001 (PROPOSED-by-default) -- DECISIONS.md update policy that this ADR extends.
- AWS Kiro v0.12 (released 2026-05-07) -- production adoption proving EARS pays off in agentic-engineering tooling.
