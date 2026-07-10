# ADR-0047: Diagram-as-code with Mermaid (rendering extracted edges, not a flow-graph engine)

- **Status**: Accepted
- **Date**: 2026-06-22
- **Tags**: diagramming, code-context-map, impact-analysis, mermaid, zero-dependency, seed-to-verify, additive

## Context

The WOS had no diagramming capability. `code-context-map` produces a ripgrep-derived text map (module import adjacency, invoke edges, typed boundary calls) but no diagram; `impact-analysis` describes blast radius in prose; `journey-map` and `screen-spec` draw ASCII; the `db-context-*` commands explicitly forbid ER diagrams; the Figma cluster handles UI, not code structure.

The `2026-06-21_wos-improvement-research` task surfaced this gap (W-08, W-22, W-23, W-18) and found that the 2026 frontier converged on diagram-as-code in Mermaid: the agent writes text that the host (GitHub, GitLab, most IDEs) renders natively, with no rendering dependency. The grounding reference (`Agents365-ai/drawio-skill`) is more capable but requires the draw.io desktop CLI plus Graphviz plus Python, which collides head-on with ADR-0027's zero-new-runtime-dependency stance (ADR-0027 rejected even tree-sitter for `code-context-map`). The research recommended the Mermaid path and dropped the draw.io toolchain (REJECTED-BY ADR-0027) and the auto-commit-in-CI pattern (conflicts with the human-first stance).

There is a real tension with ADR-0027's "no flow-graphs, no embeddings" decision. That decision excluded computing control or data-flow graphs as an authoritative analysis. The question this ADR answers: can the WOS render the edges `code-context-map` already extracts as a diagram without crossing that line?

## Decision

Add an optional, dependency-free Mermaid diagram-as-code capability that RENDERS already-extracted edges; it does not compute a new flow analysis. Three additive modes plus one retrieval helper, all opt-in:

- `code-context-map` gains `diagram` (a Mermaid flowchart of the extracted module import adjacency and invoke edges, transitive-reduced and node-capped) and `sequence:<flow>` (a Mermaid sequenceDiagram ordering the extracted invoke and boundary edges for one named runtime flow). Both append to the gitignored `MAP.md` (W-08, W-22).
- `impact-analysis` gains an optional Mermaid blast-radius subgraph (the changed module plus its inbound and outbound edges and boundary touch points), strictly the dependency subgraph of the change, not a whole-repo redraw (W-23).
- `code-context-map` also gains `exemplars`: surface 1 to 3 blessed in-repo reference snippets a greenfield slice should mirror (W-18). This is retrieval, not diagramming, but ships in the same cluster because it shares the code-context-map extraction.

Load-bearing constraints:

- Renders extracted edges, not a computed graph. The sequence and flowchart modes order and draw the invoke and boundary edges `code-context-map` already records. They do NOT add control or data-flow analysis; ADR-0027's "no flow-graphs, no embeddings" decision still holds for any authoritative analysis.
- Zero new dependency. Mermaid is text the host renders. No draw.io binary, no Graphviz, no renderer is added. The draw.io plus Graphviz toolchain is rejected (REJECTED-BY ADR-0027).
- Seed to verify, never authoritative. Diagrams carry the same grep-seed framing as the map: ripgrep heuristics are weakest across dynamic dispatch and async boundaries, so a diagram may be incomplete; the cited `file:line` and the code win on any disagreement.
- Legibility budget. Flowcharts are transitive-reduced with a node-count cap (default ~40); above the cap they collapse to module level rather than emitting an unreadable dump, protecting the token and review budget ADR-0027 guarded.
- Human-first. Diagrams are emitted as part of a reviewed artifact (the gitignored map, or the task's IMPACT_ANALYSIS.md). They are never auto-regenerated-and-committed in CI (that pattern is rejected; it conflicts with ADR-0044's no-auto-merge posture).

## Consequences

### Positive

- The WOS gains a reviewable visual layer over structure it already extracts, at zero dependency cost.
- The capability is opt-in and additive: existing `code-context-map` and `impact-analysis` runs are unchanged unless a flag is set.
- Diagram drift detection (research item DEF-07) becomes possible later, once committed Mermaid diagrams exist; deferred until then.

### Negative

- A Mermaid sequence diagram of ripgrep-extracted edges can mislead on dynamic dispatch and async; the seed-to-verify framing mitigates this but does not remove it.
- Three new modes plus a retrieval helper widen the `code-context-map` surface; the node cap and the opt-in flags keep the default behavior unchanged.

### Neutral

- The diagrams live in the same gitignored artifact (`MAP.md`) or the task folder; no new persistence layer.
- The vision self-validation loop from the grounding skill (research item) is deferred: it presupposes a render-to-image step the WOS does not own (the host renders Mermaid, so there is no PNG to inspect).

## Alternatives considered

### Alternative 1: adopt the draw.io plus Graphviz toolchain wholesale

- Rejected (REJECTED-BY ADR-0027). It requires the draw.io desktop CLI, Graphviz, and Python beyond the helper footprint, breaking the zero-new-runtime-dependency stance. Mermaid gets most of the value with no dependency.

### Alternative 2: auto-regenerate and commit diagrams in CI

- Rejected. Auto-committing a generated artifact conflicts with the human-first stance (ADR-0044 forbids auto-merge) and reintroduces the stale-or-confidently-wrong committed-diagram failure mode ADR-0027 rejected for the map.

### Alternative 3: treat the sequence diagram as a new control-flow analysis

- Rejected as a contradiction with ADR-0027. The decision here is deliberately narrow: render extracted edges in call order, framed as non-authoritative. No control or data-flow graph is computed.

## References

- `projects/<client>__<project>/active/2026-06-21_wos-improvement-research/WOS_IMPROVEMENT_BACKLOG.md` (W-08, W-22, W-23, W-18) and `EXTERNAL_RESEARCH.md` (Angle 6), with captured sources in the project `REFERENCES.md` (Mermaid Chart Copilot integration, The New Stack on Anthropic choosing code-generation over image-generation, CodeBoarding, the architecture-drift article, the drawio-skill primary source).
- ADR-0027 (code-context-map; zero-new-runtime-dependency; no flow-graphs, no embeddings) which this ADR reconciles with by rendering extracted edges rather than computing a graph.
- ADR-0044 (no auto-merge), which is why the auto-regenerate-and-commit pattern is rejected.
- `commands/code-context-map.md` and `commands/impact-analysis.md` (the commands this ADR governs).

## Notes

Locked in the `2026-06-21_implement-wos-improvement-backlog` task (Wave 4, Bundle 4). Status stays Proposed until the maintainer signs off. Diagram drift detection (DEF-07) and the vision self-validation loop (research defer) are follow-ups, not part of this ADR; revisit DEF-07 once a diagram-source convention and committed diagrams exist.
