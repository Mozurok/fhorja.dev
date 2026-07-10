# ADR-0072: code-context-map optional keyword rerank (ripgrep-only, no embeddings)

- **Status**: Accepted
- **Date**: 2026-07-01
- **Tags**: code-context-map, ranking, reciprocal-rank-fusion, ripgrep, no-embeddings, extends-adr-0027, additive

## Context

`code-context-map` (ADR-0027) ranks Layer 2 symbols by internal import fan-in, most-relevant-first, and ADR-0027 D-12 locks that as the ranking rule. D-8 of the same ADR held the line on retrieval: "no vector DB / semantic search; if ever added, cheap BM25 first, then sqlite-vec + a code-specific model fused with the graph via Reciprocal Rank Fusion, never replacing it." So D-8 did two things at once. It refused embeddings for v1, and it named the shape any future lexical or semantic signal must take: cheap-first, fused with the structural graph via reciprocal rank fusion, never a replacement for fan-in.

Fan-in alone answers "what is structurally central". It does not answer "what is central to the change I am about to make". When a task carries a few obvious terms (a feature name, a table, an error string), a symbol that matches those terms can sit far down the fan-in order even though it is the first thing the implementer should read. The gap is a task-scoped relevance signal, and D-8 already described the cheapest honest way to add one.

The cost of the naive alternative is exactly what ADR-0027 rejected: an embedding model plus a vector index means a stateful store that cannot regenerate-on-invoke cheaply, staleness, and a new runtime dependency. A ripgrep term-frequency count needs none of that. It reuses the tool the command already depends on and stays inside the regenerate-on-invoke, no-install contract.

## Decision

Activate the optional task-scoped keyword rerank that ADR-0027 D-8 deferred, as a bounded extension of the D-12 ranking rule. The command gains an optional `keywords:<comma-separated-terms>` input and an optional `--explain-ranking` flag. WHEN keywords are provided, Layer 2 symbols are reranked by blending the existing import fan-in with a ripgrep keyword term-frequency count via reciprocal rank fusion, and that Layer 2 is labeled ranking source `structural + keyword`. WHEN keywords are absent, nothing changes.

Locked invariants:

- **Ripgrep-only.** The keyword signal is a case-insensitive `rg` term-frequency count over each symbol's cited `file:line` span. No parser is required and none is installed for this feature.
- **Import fan-in stays the primary signal.** The rerank reorders symbols within the same in-scope candidate set. It never adds or removes a symbol, and a symbol with zero keyword hits can never outrank a symbol that matched.
- **Blend via reciprocal rank fusion.** Fuse the fan-in rank and the keyword rank with `score(sym) = 1/(k + rank_fanin(sym)) + 1/(k + rank_keyword(sym))`, `k = 60`, sorted by descending score. This is the exact fusion shape D-8 named.
- **No embeddings and no vector index.** No embedding model, no vector DB, no sqlite-vec, no persisted keyword index. The rerank is computed at generation time and thrown away, like the rest of the regenerate-on-invoke map.
- **Default output unchanged.** WHEN no `keywords:` are provided the command emits the fan-in-only order, labeled `structural`, byte-identical to prior behavior. The rerank code path does not run.

The `--explain-ranking` flag makes a reranked order auditable: per Layer 2 symbol it shows the fan-in rank, the keyword rank, and the fused RRF score. Off by default; when off, the symbol-line format is unchanged.

This ADR **extends** ADR-0027 D-8 and D-12 by reference. It does not edit them. ADR-0027's ripgrep default, gitignored-artifact rule, regenerate-on-invoke contract, and no-embeddings posture all stay in force. Because the repo treats ADRs as immutable, the activation of D-8's deferred path is recorded here rather than patched into ADR-0027.

## Consequences

### Positive

- A task can bias the map toward the terms it cares about without leaving the ripgrep, no-install, regenerate-on-invoke envelope ADR-0027 set.
- Reciprocal rank fusion keeps fan-in dominant: the keyword signal only reorders, so the map cannot be steered into fabricated or missing symbols by a keyword choice.
- The feature is inert by default. Existing `digest`, `module:`, and `chain:` consumers that pass no keywords see the same bytes as before, so the change is safe to land without touching any existing map.

### Negative

- Ripgrep term-frequency is a coarse lexical signal. It counts textual matches, not meaning, and can over-weight a symbol that merely mentions a term in a comment. The `structural + keyword` label and `--explain-ranking` keep this visible rather than hidden.
- The command now branches on keyword presence. The fan-in-only path must stay the always-working default, which the "default output unchanged" invariant enforces.

### Neutral

- The `k = 60` constant is the conventional reciprocal-rank-fusion default and is a tuning value, not a contract; a later ADR may revisit it with evidence.
- D-8's further step (sqlite-vec plus a code-specific model) stays deferred. This ADR activates only the cheap-first, ripgrep-only half of what D-8 described; a semantic layer would be a separate decision.

## Alternatives considered

### Alternative 1: embed the codebase and rerank by cosine similarity

- Chunk and embed symbols, then rerank by vector similarity to the keywords.
- Rejected: it reintroduces the exact stateful vector store ADR-0027 D-8 refused, breaks cheap regenerate-on-invoke, and adds a runtime dependency for a signal a ripgrep count approximates well enough at zero cost.

### Alternative 2: replace fan-in with keyword score when keywords are present

- Let the keyword order win outright whenever keywords are supplied.
- Rejected: it drops the structural signal that makes the map trustworthy and contradicts D-8's "never replacing it". Reciprocal rank fusion keeps both signals in play.

### Alternative 3: a full BM25 index

- Build a proper BM25 ranking with document-length normalization and inverse document frequency.
- Rejected for now: a per-invoke ripgrep term-frequency count fused via RRF captures most of the practical lift without a persisted index, and D-8's "cheap BM25 first" is satisfied by the cheapest form that stays regenerate-on-invoke. A fuller BM25 remains open if evidence shows the term-frequency approximation is too coarse.

## References

- ADR-0027 (code-context-map; D-8 deferred this rerank and named the RRF shape, D-12 set the fan-in ranking rule this extends).
- ADR-0057 (seed-anchored evolution of code-context-map; the immediately prior extension of the same command, and the precedent for extending ADR-0027 by a new ADR rather than an edit).
- ADR-0031 (EARS phrasing for the WHEN/WHILE decision and rule sentences).
- `commands/code-context-map.md` (the command this ADR operationalizes) and `templates/CODE_CONTEXT_MAP.template.md` (the ranking-source label and per-symbol score format).

## Notes

This is a new ADR rather than an amendment to ADR-0027 even though the rerank stays inside D-8's explicitly-deferred path, because the repo records extensions as their own immutable record. The default (no keywords) output is unchanged by construction, so the regression surface is limited to runs that opt in with `keywords:`.
