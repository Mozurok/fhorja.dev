# Eval scenario 27: code-context-map output contract

- **Tags**: code-context-map, discovery-and-scoping, gitignored-artifact, token-budget, ADR-0027, ADR-0195
- **Last reviewed**: 2026-09-07
- **Status**: active

## Goal

Validates that `code-context-map` produces a ranked, token-budgeted, layered Markdown map written to a gitignored folder inside the target repo, regenerated on invoke, framed as a seed for grep, with no parser dependency, no embeddings, and no flow-graphs. Exercises the contract locked in ADR-0027 and decisions D-1..D-12.

This is a two-turn scenario: turn 1 uses the default `digest` scope (Layer 1 only); turn 2 uses `module:` scope (Layer 1 + Layer 2 for one module).

## Setup

Requires a target codebase path with multiple source files, at least one cross-module import, and at least one external boundary call (database, HTTP API, or queue). An active task is optional; when present, a single `## Code context map` cross-link may be added to `SOURCE_OF_TRUTH.md`.

## Input prompt (turn 1: digest scope)

```text
Run @commands/code-context-map.md

target_codebase: ~/code/acme-platform
scope: digest
Mode: Agent
```

## Input prompt (turn 2: module scope)

```text
Run @commands/code-context-map.md

target_codebase: ~/code/acme-platform
scope: module:packages/billing/src
Mode: Agent
```

## Expected response shape (turn 1: digest)

- Writes `~/code/acme-platform/.code-context-map/MAP.md` and confirms `.code-context-map/` is gitignored (already present, or an entry was appended).
- The map contains Layer 1 only: repo digest + module-to-module import adjacency + boundary summary. No Layer 2 detail.
- Header records `Last generated: <date> on <branch>@<sha>`, a token-budget line, and the grep-seed framing ("orients you; grep/read file:line is the source of truth").
- `### Artifact changes` lists the map as a product-repo write and (if a task is active) at most one `## Code context map` cross-link as `APPLIED` (Agent mode).

## Expected response shape (turn 2: module)

- Regenerates the map with Layer 1 plus Layer 2 detail for `packages/billing/src` only: fan-in-ranked symbols with signatures, invoke edges, and a typed boundary-edges table (kind | target | file:line).
- Layer 2 respects the per-module token budget; no flat whole-repo signature dump.
- Every symbol, import, invoke edge, and boundary edge traces to a real `file:line`. A "Known limitations" section notes ripgrep-heuristic gaps.

## Pass criteria

1. **Gitignored location**: the artifact is written only under `<target>/.code-context-map/`, and the response confirms that folder is gitignored (appended if missing). It is never committed and never written elsewhere.
2. **Layering**: turn 1 emits Layer 1 only; turn 2 adds Layer 2 for the named module only. Neither turn emits a flat signature dump of the whole repo.
3. **Freshness + framing**: both maps carry `Last generated` with `branch@sha` and the grep-seed framing (map orients; code wins on disagreement).
4. **Ranking**: Layer 2 symbols are ordered by import fan-in, most-relevant-first.
5. **No forbidden mechanisms**: no embeddings/vector DB, no flow-graphs, and no required AST-parser install are introduced. Extraction is ripgrep-based.
6. **Evidence-grounded**: every entry maps to a real `file:line`; nothing is fabricated; limitations are stated.
7. **Handoff**: both turns end with a complete `### Handoff` block routing to `impact-analysis` / `code-locate` (task active) or `what-next` (no task).

## Failure modes to watch

- **Committed or mislocated artifact**: the map is written outside `.code-context-map/`, or the folder is not gitignored, or the command stages it for commit.
- **Flat whole-repo dump**: turn 1 or 2 emits signature-level detail for the entire repo, blowing the token budget (the ~69k-token failure the layering decision prevents).
- **Forbidden mechanism creep**: the response proposes embeddings/vector search, a flow-graph, or mandates installing tree-sitter/ctags.
- **Fabricated entries**: symbols/imports/boundaries that do not trace to a real `file:line`.
- **Missing freshness or grep-seed framing**: the artifact omits `Last generated` `branch@sha` or presents itself as an authoritative/exhaustive index.
- **Missing Handoff**: either turn ends without a complete `### Handoff` block.

## Keyword ordering subcase

Exercise the Layer 2 ordering step after extraction, using these already-established ranks from
one in-scope module. This fixture isolates ranking; it does not stand in for source extraction or
the full map generation exercised above. Compare the relative order of these three candidates
within the larger candidate set. Keyword ranks refer to matching candidates only.

| Candidate | Fan-in rank | Keyword rank | Expected RRF score with k=60 |
|---|---:|---:|---:|
| hub | 1 | none | 0.01639344 |
| weak-match | 500 | 100 | 0.00803571 |
| strong-match | 2 | 1 | 0.03252247 |

- With `keywords:` and `--explain-ranking`, expect `strong-match`, then `hub`, then `weak-match`
  in relative order, with the ranks and scores shown. Rounded scores must not reverse that order.
- With keywords but without explanations, expect the same order without score annotations.
- With keywords absent, expect fan-in order: `hub`, then `strong-match`, then `weak-match`, and
  ranking source `structural`.
- With keywords present but no matches anywhere, every keyword rank is `none`, every score is
  its fan-in term, and relative order is fan-in order. The ranking source remains
  `structural + keyword`, because the keyword path was selected.
- Repeat with every candidate in the module matching: include both terms for each candidate
  and sort by descending RRF. Preserve the original candidate set in every variant.
- Layer 1, module order and import-chain traversal do not change when keywords are supplied.

A failure groups every matching symbol before `hub`, excludes `hub`, gives it a keyword term,
changes the no-keyword path, or reports explanations inconsistent with the actual order.

## Notes

- Related ADR: [ADR-0027](../../docs/adr/0027-code-context-map-and-product-repo-artifacts.md).
- Related command: `commands/code-context-map.md`; template `templates/CODE_CONTEXT_MAP.template.md`.
- Distinct from `code-locate` (ephemeral per-behavior search) and `db-context-supabase` (DB schema into task memory). The map is a durable, gitignored code-structure producer.

## History

- 2026-05-30: scenario authored as part of the code-context-map task (Slice 5).
- 2026-09-07: added the global RRF counterexample and keyword-path variants under ADR-0195.
