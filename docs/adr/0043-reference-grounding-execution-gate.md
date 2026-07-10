# ADR-0043: Reference grounding execution gate

- **Status**: Accepted
- **Date**: 2026-06-15
- **Tags**: reference-grounding, execution-gate, evidence-priority, shared-block, capture-references, never-read, dogfood

## Context

The workflow captured external references well but never enforced their use during execution. `capture-references` writes entries to project-level `REFERENCES.md` with freshness metadata, deduplication, and (per ADR-0018) cross-source context. ADR-0010 centralizes web access so those entries are the single audit-trailed source of external truth. The capture side worked.

The consumption side did not. A grep across the command set found that only 9 commands referenced `REFERENCES.md`, and none of them were execution commands: `implement-approved-slice`, `implement-slice-complement`, and `implement-fleet` read `SOURCE_OF_TRUTH.md` but had no step that read the captured references or the documented library contract before editing code. `## Evidence priority` ranked project-level memory at position 4 and official library docs at position 6, but its only binding rule was "if correctness depends on something not grounded, do not guess; ask or capture." Ranking is not active consumption.

The failure showed up in a real session. In a separate project, the agent implemented a voice slice against an external streaming API. It coded from a recovered older spike plus its own recollection of the API, never reading the documented contract (the relevant rule, accumulate the final transcript segments rather than replacing them, was not even captured yet). The result diverged from the documentation and the user had to ask the agent to read the docs. Only after `capture-references` ran with the verbatim API rules did a re-implementation, grounded in the captured contract, work. The failure classified as NEVER-READ: the implementer never consulted the source before coding. Notably, once the entry was read it was sufficient, so the binding constraint was consumption enforcement, not capture fidelity.

## Decision

Reference grounding becomes an enforced execution gate, single-sourced and consumed by every execution command, sequenced so consumption enforcement ships before capture-fidelity enrichment. The gate is composed of seven locked decisions:

- D1: the gate is one shared block, `commands/_shared/reference-grounding.md`, consumed via the `<!-- shared:reference-grounding -->` marker by `implement-approved-slice`, `implement-slice-complement`, and `implement-fleet`, propagated by `scripts/sync-shared-blocks.sh` so it cannot drift between commands.
- D2: when a needed external contract is absent from `REFERENCES.md`, the execution path routes the capture through `capture-references` and never performs an ad-hoc web fetch (consistent with ADR-0010).
- D3: the gate is stated in imperative MUST language and requires a visible `Grounded in:` cite line naming the entries consulted before any edit (the lesson of ADR-0035: advisory prose is ignored under load).
- D4: consumption enforcement is delivered before capture-fidelity enrichment.
- D5: a hard gate. When a slice touches an external library or API contract not present in `REFERENCES.md`, the execution command refuses to edit and routes to `capture-references`, in every task tier, before any code is written.
- D6: the implementer auto-detects external-API usage by scanning the slice's imports and diff; where such usage is detected it requires a `Grounded in:` citation. No per-slice field is added to `implementation-plan`; detection avoids false positives on internal-only slices.
- D7: `capture-references` gains an `Implementation contract` block (API signature, minimal example, version pin), populated only from the source, default-on at `detailed` depth for technical sources and omitted at `summary` depth.

The enforcement is prompt-level: these commands are prompts, not runtime code, so the gate's strength comes from imperative language plus a verifiable artifact (the `Grounded in:` line and the refusal block), not from compiled checks.

## Consequences

### Positive

- The NEVER-READ failure cannot recur silently: an edit that touches an external contract without a `Grounded in:` line is invalid output, and an uncaptured contract blocks the edit.
- Captured entries become implement-ready at `detailed` depth (signature, example, version), so a grounded implementer has the concrete contract rather than prose.
- The rule lives in one place; adding a future execution command means adding one marker, not re-authoring the gate.

### Negative

- Higher friction: a slice that merely touches an external library is blocked until its contract is captured, even when the change is small. This was an accepted tradeoff (D5 over a warn-and-proceed default).
- `implement-approved-slice` grew past its previous token budget and was rebumped (2700 to 2900); the gate adds tokens to every execution command.
- Auto-detection (D6) is a heuristic over imports and diff; it can miss an external dependency reached indirectly or over-fire on a re-exported internal module.

### Neutral

- `external-research` and `external-research-fleet` inherit the new entry format automatically because they reference "the format defined in capture-references"; no edit was needed there.
- The gate is dogfooded: this repository's own execution commands now carry it.

## Alternatives considered

### Alternative 1: warn-and-proceed instead of a hard gate

- The implementer would emit an "ungrounded" warning and proceed when a contract is uncaptured.
- Rejected: it is close to the behavior that already failed. The warning depends on a human catching it in review, which is exactly what did not happen.

### Alternative 2: capture-fidelity only (richer entries, no consumption gate)

- Enrich `capture-references` with signatures and examples and rely on the existing Evidence priority ranking.
- Rejected: a richer entry does not help an implementer who never reads it. The transcript showed the entry was sufficient once read; the gap was reading it.

### Alternative 3: pin references per slice in implementation-plan

- Add a per-slice "contracts to read" field that the gate keys off.
- Rejected in favor of D6 auto-detection: it adds a field to the plan contract and still misses contracts the planner did not foresee. Import/diff detection keys off what the slice actually touches.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## Evidence priority` (the execution-consumption obligation that points to the shared block).
- `commands/_shared/reference-grounding.md` (the canonical gate text).
- `commands/implement-approved-slice.md`, `commands/implement-slice-complement.md`, `commands/implement-fleet.md` (consumers via the shared marker).
- `commands/capture-references.md` (the `Implementation contract` block, D7).
- ADR-0010 (centralized external web access), ADR-0018 (contextual retrieval in REFERENCES.md), ADR-0035 (imperative language in shadow-mode protocols).

## Notes

Triggered by a lived NEVER-READ failure in a separate project (an external streaming-API voice slice). The decisions D1-D7 were locked in a `decision-interview` run on 2026-06-15; D1-D4 were evidence-forced by repo conventions and the impact analysis, D5-D7 were chosen by the maintainer. Revisit D5 (hard gate, all tiers) if the friction on trivial external-touching slices proves too high in practice; a tier-aware variant was the runner-up.
