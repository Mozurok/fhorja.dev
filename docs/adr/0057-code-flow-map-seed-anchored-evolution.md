# ADR-0057: Seed-anchored code-flow map, evolving code-context-map

- **Status**: Accepted
- **Date**: 2026-06-26
- **Tags**: command, code-context-map, code-flow-map, import-chain, hybrid-extraction, human-html, fleet-orchestration, extends-adr-0027, additive

## Context

`code-context-map` (ADR-0027) produces a ripgrep-based, gitignored, fan-in-ranked Markdown map of a target repo at two scopes (`digest` and `module:<glob>`). It does not walk a single file's import chain, has no human-readable projection, and is ripgrep-only by contract (ADR-0027 D-10).

A user asked for a capability that, from a seed file, follows the import chain across the repo to a chosen scope, then produces two outputs: an AI-readable structure that captures how the project is wired and the order in which files reference each other, and a human-readable HTML map. The heavy traversal would run as an opt-in multi-agent workflow gated behind an explicit consent prompt.

A four-angle `external-research-fleet` run (the task's `EXTERNAL_RESEARCH.md`) surveyed prior art:

- Static dependency-graph tooling: madge, dependency-cruiser, Sourcegraph SCIP, LSP. All faithful tools use a real parser; dependency-cruiser's `--focus`/`--reaches` is the seed-anchored walk; a regex-only walk silently drops barrels, default and dynamic imports, and path aliases.
- AI-agent code maps: aider's tree-sitter repo-map ranked by personalized PageRank with a token budget; Repomix; Claude Code's agentic ripgrep search ("outperformed everything. By a lot."); Cody dropped embeddings for search. Industry drift is away from embeddings.
- AAA code-graph at scale: Kythe, Glean, GitHub stack graphs. They converge on a graph of named symbols with a defines/references edge; the raw graph is machine-facing, with a thin human projection layered on top; freshness is O(changes).
- Human visualization and living docs: CodeSee, C4, dependency-cruiser's self-contained interactive HTML, DocAgent. A single embedded HTML file is a publishable deliverable; multi-agent doc generation helps, but the measured lift comes from dependency-aware ordering and one-hop context, not agent headcount.

The repo had already circled this capability: `REFERENCES.md` carries a 2026-05-29 code-map research cluster and a 2026-06-23 C4 entry tagged a c4-architecture-map candidate. That argues for evolving the existing command rather than shipping a near-duplicate.

The one genuine conflict the research surfaced was extraction fidelity: ripgrep-only is cheap and dependency-free but lossy for an import-chain walk, while AST or LSP is faithful but heavier. That conflict, not the output shape, was the gating decision.

## Decision

Evolve `code-context-map` into a seed-anchored code-flow map rather than ship a new command, and fold in the previously-scoped c4-architecture-map candidate as the human layer. Locked as D-1 through D-9 in the task's `DECISIONS.md`:

- **D-1 (shape).** The capability is delivered as an evolution of `code-context-map`, not a new standalone command. No new registry entries are required.
- **D-2 (extraction, the gating decision).** Extraction uses ripgrep by default. WHERE a parser is already available in the target repo (tree-sitter, or an installed madge or dependency-cruiser) the chain is resolved faithfully (barrels, default and dynamic imports, aliases). WHILE only ripgrep is available the import chain is labeled a non-authoritative grep-seed.
- **D-3 (human HTML).** WHEN invoked the command regenerates a self-contained interactive HTML map into the gitignored artifact folder, after confirming that folder is in the target repo's `.gitignore`.
- **D-4 (generation path).** Generation is single-pass by default. WHERE the dependency chain exceeds a single context window the command offers a consent-gated multi-agent fleet; IF the user declines THEN it falls back to a single-pass bounded map.
- **D-5 (walk scoping).** The walk is scoped from the seed by direction (transitive imports, optionally transitive dependents) with a hop cap and a cycle guard, not a blunt global max-depth.
- **D-6 (no embeddings).** Selection and ranking use structural signals only; no embeddings or vector index in v1.
- **D-7 (ranking).** Rank by internal import/reference fan-in, most-referenced first.
- **D-8 (freshness).** Regenerate on invoke; report NO_OP when the freshly generated artifact is byte-identical.
- **D-9 (AI-readable format).** The AI-readable output stays the ranked, layered Markdown map, with an optional JSON sidecar for programmatic consumers; no new primary format.

This ADR **extends** ADR-0027; it does not reverse it. The ripgrep default and the gitignored-artifact rule stay in force. The additions are the seed-anchored chain scope, the optional parser augmentation (which stays inside ADR-0027's optional-if-already-present clause), the human HTML projection, and the opt-in fleet path. Because ADRs are immutable, this is a new ADR rather than an edit to ADR-0027.

## Consequences

### Positive

- The user's import-chain-walk request is met by extending a command that already has the ranked, no-embeddings, regenerate-on-invoke foundation, so the net-new surface is small.
- The extraction-fidelity conflict is resolved honestly: the chain is faithful when a parser is present and is explicitly labeled a seed when only ripgrep is available, so the map never overclaims.
- The two-artifact split (machine map + human HTML) matches what every AAA system does, and the HTML is a self-contained, publishable deliverable.
- Single-pass-by-default keeps the common case cheap; the fleet is reserved for the case the evidence says justifies it.

### Negative

- Three features (chain walk, HTML projection, fleet path) land on one command, widening it. The implementation plan slices them so each ships and reviews alone.
- D-2's graceful degradation adds branching: detect a parser, use it, or fall back and relabel. The ripgrep path must stay the always-working default.
- A self-contained interactive HTML map needs zoom and filtering to stay readable on a large graph; a flat dump would be noise.

### Neutral

- The concrete fan-out threshold for D-4 is a tuning value chosen during implementation, not locked here.
- The AI-readable map keeps the existing format, so existing `digest` and `module:` consumers are unaffected; the chain scope is additive.

## Alternatives considered

### Alternative 1: a new standalone command

- A fully separate command with its own extractor.
- Rejected: it duplicates the code-context-map engine, adds a fourth registry entry, and reopens every ADR-0027 question. D-1 chose evolution.

### Alternative 2: pure ripgrep-only as the sole extraction path

- Keep ADR-0027 D-10 untouched and never parse.
- Rejected as the sole approach: a regex-only walk silently drops the exact edges an import-chain promises to show. It is kept as the always-working default under D-2, with the grep-seed label, but it is not the only path.

### Alternative 3: tree-sitter or LSP as a hard dependency

- Require a parser in every target repo for a always-faithful chain.
- Rejected: it forces a dependency on arbitrary product repos and is the biggest departure from ADR-0027. D-2's optional-if-present augmentation gets most of the fidelity without the mandate.

### Alternative 4: always multi-agent

- Fan out by default with the up-front consent prompt.
- Rejected: DocAgent shows the quality lift comes from dependency-aware ordering and one-hop context, not agent headcount, so fan-out is justified only past the context-window wall. D-4 makes it opt-in.

## References

- ADR-0027 (code-context-map; the command this ADR extends).
- ADR-0038 (Workflow tool as the canonical parallel-orchestration primitive; the fleet mechanism for D-4).
- ADR-0047 (Mermaid diagram-as-code) and ADR-0049 (generated HTML over the audit log); precedents for the diagram and HTML surfaces.
- ADR-0031 (EARS for the decision and exit-criteria sentences).
- ADR-0029 (lint drift guards: index rows and count markers).
- Task artifacts: `DECISIONS.md` (D-1..D-9), `EXTERNAL_RESEARCH.md` (the four-angle prior-art synthesis), `REFERENCES.md` 2026-05-29 code-map cluster and the c4-architecture-map candidate.

## Notes

This is a new ADR rather than an amendment to ADR-0027 even though D-2's hybrid stays within 0027's optional-if-already-present clause, because the repo treats ADRs as immutable and records extensions as their own record. The implementation is sliced (ADR, hybrid extractor + seed-walk, gitignored HTML, fleet path, eval + docs); slices 2 through 4 all edit `commands/code-context-map.md`, so they run sequentially rather than as a fleet.
