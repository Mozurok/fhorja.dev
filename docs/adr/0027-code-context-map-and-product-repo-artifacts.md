# ADR-0027: code-context-map command and gitignored artifacts in the documented repo

- **Status**: Accepted
- **Date**: 2026-05-29
- **Tags**: code-context-map, discovery, product-repo-artifact, context-engineering, token-budget

## Context

AI assistants working in a codebase repeatedly re-derive the same structural picture (which files import which, where functions are defined and used, which files reach a database, an API, or a queue) before they can safely change anything. This is slow, token-expensive, and inconsistent between sessions and tools. The maintainer asked for a command that produces a durable, AI-readable "code context map" of a project so an assistant reads the map first and knows precisely what to read, index, and test, staying within the project's existing patterns.

Two forces shaped the design:

- **No existing WOS command writes into the documented product codebase.** Commands read product code and persist artifacts into task memory (for example `db-context-supabase` writes `DB_CONTEXT.md` into the task folder) or project memory. The requested map is most useful living *inside* the project it documents, so any AI tool reading that repo finds it. That is a new artifact-location pattern for the WOS and needs an explicit, recorded decision.
- **Token economy is a hard constraint, not a preference.** A prototype against a real monorepo (`fhorja-app`, 180 ts/tsx files) measured a scoped per-module map at ~825 tokens (~30% of raw source), but a flat signature-level map of the whole repo extrapolated to ~69,000 tokens, which would exceed any sane context budget and trigger context-rot. The map must be ranked, budgeted, and layered, not a flat dump.

External research (two rounds, captured in the task's `EXTERNAL_RESEARCH.md` and project `REFERENCES.md`) found the deterministic symbol-graph approach (aider repo map) is the proven, low-dependency design, that the industry frontier is moving away from embeddings for coding agents (Claude Code, Cline, and Sourcegraph Cody all dropped or rejected them), and that no surveyed tool ships a gitignored, human-and-AI-readable Markdown map (an under-occupied niche).

## Decision

Add an opt-in WOS command `code-context-map` (category `discovery-and-scoping`) that generates and re-syncs an AI-readable, ranked, token-budgeted, layered Markdown map of a project and writes it to a **gitignored folder inside the documented product repo**, regenerated on each invocation. The map records files, imports, signatures, invoke (who-calls-whom) edges, and typed external boundary edges (db/http/queue), framed as a seed for agentic grep rather than a replacement for reading the code.

Qualifications (canonical decisions, see the task's `DECISIONS.md` D-1..D-12):

- **Location (D-1):** the artifact lives gitignored inside the product repo (a regenerable, local, never-committed artifact). The command ensures the artifact path is gitignored; discovery pointers in `AGENTS.md`/`CLAUDE.md`/`llms.txt` may be committed even though the map is not.
- **Posture (D-3):** opt-in, not wired into default `task-init`; mirrors `db-context-supabase`.
- **Format (D-5):** Markdown-primary, optional JSON sidecar only when deterministic tooling needs it.
- **Sync (D-6):** regenerate-on-invoke with a freshness marker; no persisted incremental state in v1.
- **Layering (D-7, D-11):** Layer 1 (always, cheap): repo digest + module-to-file import adjacency. Layer 2 (per-module, budget-capped, on-demand): signatures + invoke edges + typed boundary edges. Flow-graphs (control/data) are out of v1; the schema is layered so they can be added later without rework.
- **Extraction (D-10):** ripgrep-backbone extraction assembled by the command's reasoning; no AST-parser dependency in v1 (optional JS/TS-only augmentation via `npx madge`/`dependency-cruiser` if present; tree-sitter is a documented future optimization).
- **Ranking (D-12):** import fan-in, most-relevant-first.
- **No embeddings in v1 (D-8):** no vector DB / semantic search; if ever added, cheap BM25 first, then sqlite-vec + a code-specific model fused with the graph via Reciprocal Rank Fusion, never replacing it.

The decision is operationalized by `commands/code-context-map.md` (and its generated `.claude/skills/code-context-map/SKILL.md`), validated by `scripts/lint-commands.sh` and an eval scenario.

## Consequences

### Positive

- An assistant orients from a small, ranked, structural map before editing, reducing wasted reads and keeping changes within existing patterns.
- The artifact is deterministic and regenerate-on-invoke, so it cannot silently go stale the way a committed index or embedding store does (the universal objection to indexes).
- Zero new runtime dependency in v1 (ripgrep only), keeping the WOS markdown-plus-bash-plus-small-python footprint and avoiding AGPL/CI burden.
- Dual human-and-AI readability doubles as lightweight architecture/onboarding documentation, an under-occupied niche no surveyed tool fills.

### Negative

- Introduces the first WOS pattern of a command writing an artifact into the documented product repo. Even gitignored, this is a new responsibility (the command must manage `.gitignore`) and a precedent future commands may follow. Accepted, and bounded by "gitignored only" to avoid polluting product history.
- ripgrep-heuristic extraction can miss dynamic imports, re-exports, and aliased calls. Accepted: the map is a navigation seed (it points, grep confirms), and this limitation is documented in the command's caveats.
- Per-language pattern sets mean polyglot coverage is incremental (TS/JS first, given the fhorja-app testbed); other stacks degrade gracefully rather than failing.

### Neutral

- The map is intentionally not authoritative; it is a fast structural index, not a substitute for `impact-analysis` or for reading the code.
- Embeddings and flow-graphs are deferred, not rejected forever; the layered schema and D-8/D-7 leave a clean path to add them with evidence.

## Alternatives considered

### Alternative 1: Store the map in WOS project memory (like db-context-supabase writes DB_CONTEXT.md)

- The map would live under `projects/<client>__<project>/` and never touch the product repo.
- Rejected: it breaks the core value (any AI tool opening the documented repo should find the map inside it). It would also couple a generic, reusable artifact to one workflow tool's private memory layer.

### Alternative 2: Commit the map into the product repo

- The map would be versioned and shared across the team via git.
- Rejected: diff noise on every regeneration, merge conflicts, and the stale-committed-map failure mode (a confidently wrong map is worse than none). Gitignored + regenerate-on-invoke gives the in-repo locality without these costs.

### Alternative 3: Embedding / vector-DB (ChromaDB-style) semantic index

- Chunk and embed the codebase into a local or hosted vector store for semantic retrieval.
- Rejected for v1: the frontier moved away from embeddings for agents (Claude Code and Cline reject indexing; Anthropic built and abandoned RAG; Sourcegraph Cody removed embeddings) citing staleness, chunking that tears apart logic, fuzzy false positives, privacy, and scaling cost. Embeddings also cannot regenerate-on-invoke cheaply (each chunk needs a model inference), forcing the stateful incremental index this design deliberately avoids.

### Alternative 4: tree-sitter / SCIP parser dependency for v1 extraction

- Use a real AST/index backbone for precise symbol and reference data.
- Rejected for v1: the prototype showed ripgrep alone produced a correct, useful map on real TypeScript, and no such parser is even installed locally (BSD ctags cannot parse TS). Adding one would be AGPL/CI overhead for marginal v1 benefit. tree-sitter is recorded as a future precision/scale optimization.

## References

- `WORKFLOW_OPERATING_SYSTEM.md` → `## Command categories` (`### Discovery and scoping`) and `## Command roles` (where the command is registered as normative content).
- `commands/code-context-map.md` (the command that operationalizes this decision; created in a later slice).
- Task memory: `projects/bmazurok__my-work-tasks/active/2026-05-29_code-context-map-command/DECISIONS.md` (D-1..D-12), `EXTERNAL_RESEARCH.md` (rounds 1-2), `PROTOTYPE_FINDINGS.md` (the ~69k-token measurement).
- ADR-0007 (project-level memory) and `db-context-supabase` (the closest existing context-producer pattern this command parallels).
- External prior art (accessed 2026-05-29): [aider repo map](https://aider.chat/2023/10/22/repomap.html), [Sourcegraph Cody dropped embeddings](https://sourcegraph.com/blog/how-cody-understands-your-codebase), [Chroma context rot](https://www.trychroma.com/research/context-rot), [cAST AST chunking](https://arxiv.org/abs/2506.15655), [llms.txt](https://llmstxt.org/).

## Notes

- The load-bearing empirical input was the Slice 0 prototype against `fhorja-app/packages/billing/src`: a scoped module map at ~825 tokens vs a ~69,000-token flat whole-repo extrapolation. That single measurement is why layering (D-11) is mandatory rather than optional.
- Revisit if: a precise whole-repo retrieval gap appears that ripgrep + ranking cannot close (then reconsider tree-sitter precision per D-10 or a sqlite-vec semantic layer per D-8), or if a future command needs to write a non-gitignored artifact into a product repo (that would be a new decision, not covered here).
