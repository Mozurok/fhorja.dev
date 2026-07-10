---
name: code-context-map
description: |-
  Generate and re-sync an AI-readable code context map (a ranked, token-budgeted, layered Markdown map of files, imports, signatures, invoke edges, and typed external boundary calls: db/http/queue) for a target project (or, from a seed file, its import chain), written to a gitignored folder inside that project and regenerated on invoke. Extraction is ripgrep-based by default, with optional parser augmentation when a parser is already present; no embeddings. The map is a seed for grep, not a replacement for reading code. Opt-in; not part of default task init. Use when an assistant needs fast structural orientation before editing a codebase, when onboarding to an unfamiliar repo, or when an existing map is stale. Do not use to locate one specific behavior (use code-locate), to analyze the blast radius of a planned change (use impact-analysis), to introspect a database schema (use db-context-supabase), or without a target codebase path.
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed:
    - memory
    - retrieved
  context-layers-produced:
    - retrieved
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
  x-wos-profiles:
    - core
    - full
  provenance: first-party
  token-budget: 5200
  suggested-model: claude-sonnet-4-6
---

Act as a senior/staff engineer producing a durable, AI-readable structural map of a codebase.

Goal:
Generate a ranked, token-budgeted, layered Markdown "code context map" of a target project (files, imports, signatures, invoke edges, and typed external boundary calls), write it to a gitignored folder inside that project, and regenerate it on invoke so an AI assistant reads the map first and knows precisely what to read, index, and test before changing code. A `chain:<seed-file>` scope additionally walks one file's import chain by direction with a hop cap, extracting with ripgrep by default and with a parser when one is already present (ADR-0057 D-2, D-5). The map ORIENTS; it is a seed for `grep`, not a replacement for reading the code. Follows `templates/CODE_CONTEXT_MAP.template.md`.

This command is opt-in, not part of default task init (use it for structural orientation, onboarding, or a stale map). The governing decision is `docs/adr/0027-code-context-map-and-product-repo-artifacts.md`.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). This reduces bootstrap from ~6,750 to ~3,500 tokens for these commands.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names.

Required inputs:
- target codebase path (the project to map; the map is written inside this path). When a task is active and `SOURCE_OF_TRUTH.md` names the workspace, default to that.
- scope, one of:
  - `digest` (default): Layer 1 only (repo digest + module-to-file import adjacency + boundary summary). Cheapest; always safe for a whole repo.
  - `module:<path/glob>`: Layer 1 plus Layer 2 detail (ranked signatures, invoke edges, typed boundary edges) for the named module(s). Use for the area the current task touches.
  - `chain:<seed-file>`: Layer 1 plus a seed-anchored import-chain walk from `<seed-file>` (ADR-0057 D-5). Answers "what does this file pull in, and in what order does the wiring run". Walks by direction with a hop cap and a cycle guard.
- optional (chain scope only): `direction` one of `imports` (default), `dependents`, or `both`; `max-hops` (default 4, or `all` for an unbounded walk until no new files are reached) caps the radius; cycle edges are recorded once and not re-walked. For a whole-repo view prefer the `digest` or `module:` scopes; a `chain:` with `max-hops:all` on a large repo trips the consent-gated fleet (D-4) by design.
- optional: token budget for Layer 2 (default 1200 tokens per module; raise only when justified). Layer 1 is always generated regardless of budget.
- optional: `keywords:<comma-separated-terms>` (task-scoped) to rerank Layer 2 symbols toward the current task. WHEN set, Layer 2 symbols are reranked by ripgrep term-frequency of these terms blended with the existing import fan-in via reciprocal rank fusion (RRF), and that Layer 2's ranking source is labeled `structural + keyword`. WHEN unset, ranking is import fan-in only, the source is labeled `structural`, and the output is byte-identical to prior behavior. Ripgrep-only: no embeddings and no vector index (ADR-0072, activating the optional rerank ADR-0027 D-8 deferred).
- optional: `--explain-ranking` flag to show, per Layer 2 symbol, its fan-in rank, its keyword-frequency rank, and the fused RRF score, so a reranked order is auditable. Off by default; WHEN off, the symbol-line format is unchanged, and WHEN `keywords:` is absent the flag adds nothing beyond the fan-in rank.
- optional: language hint (defaults to auto-detect by file extension; v1 ships pattern sets for TS/JS first and degrades gracefully elsewhere).
- optional: refresh flag (`refresh` to regenerate an existing map; default behavior is regenerate-on-invoke, so a non-stale identical map yields `NO_OP` rather than a rewrite).
- optional: `--skip-secret-scan` to bypass the pre-emit secret gate (ADR-0060); the command never auto-skips, so this is the explicit human override after a confirmed false positive.
- optional flags, host-rendered with no new dependency (full behavior in Operating rules below): `diagram` (append a Mermaid import-adjacency and invoke flowchart, node-capped, ADR-0047); `sequence:<flow>` (append a Mermaid sequenceDiagram for one named runtime flow); `exemplars` (1 to 3 blessed in-repo reference snippets a greenfield slice should mirror, ranked by fan-in); `html` (also emit a self-contained interactive `MAP.html` in the same gitignored folder, ADR-0057 D-3).

Files to read (in the target codebase, read-only):
- source files in scope, via `rg` queries for imports, definitions/signatures, invoke sites, and boundary call-sites (db/http/queue). Never modify source, because this command produces a read-only orientation aid; writing to the target would turn a navigation map into an unreviewed code change.

Files to create or update:
- `<target-codebase>/.code-context-map/MAP.md` (the artifact; create or fully regenerate, never partial-merge).
- `<target-codebase>/.code-context-map/MAP.html` (only when the `html` flag is set: the self-contained human projection; create or fully regenerate, never partial-merge).
- `<target-codebase>/.gitignore` (append-only: ensure `.code-context-map/` is ignored if not already; the only product-repo file outside `.code-context-map/` that this command may touch).
- active task `SOURCE_OF_TRUTH.md`, when a task is active (append-only: add a single `## Code context map` section pointing to the artifact path, if not already present).

Operating rules:
- Do not implement or modify production code. This command reads code and writes only the gitignored map artifacts (MAP.md, and MAP.html when `html` is set) plus a `.gitignore` entry.
- **Gitignored artifact (D-1, ADR-0027):** the map lives in `<target-codebase>/.code-context-map/` and MUST be gitignored. Before writing, ensure `.code-context-map/` is present in the target repo's `.gitignore`; if not, append it. Never commit the map; never write it outside the gitignored folder.
- **Pre-emit secret gate (ADR-0060):** before writing MAP.md (and MAP.html), run `scripts/secret-scan-gate.sh <target-codebase-path>` over the in-scope path, because the map summarizes a repo that may hold credentials and the gate is a hard stop, not advisory text. It is presence-gated (ADR-0027): gitleaks if present (a finding BLOCKS the write, exit 1), else trufflehog `--no-verification` (offline; a finding BLOCKS), else a built-in rg pattern scan that WARNS only (coarse regex is too false-positive-prone to gate on). On a BLOCK, do NOT write the map: surface the findings, tell the user to revoke or whitelist (`gitleaks:allow`), and require the explicit `--skip-secret-scan` input to proceed. The command never auto-skips.
- **Regenerate-on-invoke (D-6):** always regenerate from the live working tree. Record `Last generated: YYYY-MM-DD on <branch>@<short-sha>` in the artifact. If the freshly generated map is byte-identical to the existing one, report `NO_OP` and do not rewrite.
- **Layering (D-7, D-11):** always generate Layer 1 (repo digest + module import adjacency + boundary summary). Generate Layer 2 detail only for in-scope module(s) and only within the token budget. Never emit a flat signature-level dump of an entire large repo (it blows the budget and causes context rot).
- **Extraction (D-10, amended by ADR-0057 D-2):** use ripgrep-based extraction (imports, definitions/signatures, invoke sites, boundary call-sites) assembled by reasoning. Do NOT require or install an AST parser, vector DB, or embedding model. Optional, only-if-already-present augmentation: `npx madge` / `dependency-cruiser`, or a tree-sitter already present, for a precise JS/TS file-import graph. For the `chain:` scope, WHERE such a parser is already present use it to resolve barrels, default and dynamic imports, and aliases in the chain; WHILE only ripgrep is available, label the chain `grep-seed (non-authoritative)` and do not present it as a faithful import chain. Never install a parser; the ripgrep walk is always the working default.
- **Layer 2 compression (presence-gated, ADR-0027 no-install + ADR-0057 D-2):** WHERE `repomix` is already present in the target repo, run `npx repomix --compress` to source Layer 2 from its tree-sitter signatures-only extraction (function and method signatures, interface and type definitions, class shapes; implementations, loop and conditional bodies, and internal variables stripped; roughly 70% fewer tokens than full files) and label that Layer 2 `source: repomix --compress`. WHILE `repomix` is absent, fall back to the ripgrep signature heuristics labeled `source: ripgrep (heuristic)`. Never install repomix; this is opt-in augmentation and the labeled fallback keeps the default path unchanged.
- **Chain walk (ADR-0057 D-5):** for `chain:<seed-file>`, start at the seed and follow imports breadth-first by `direction` up to `max-hops` (or until no new files are reached when `max-hops:all`); record each file once (cycle guard), rank modules within a hop by import fan-in, and stop at the cap. The import chain is additive to Layer 1; never emit a flat whole-repo signature dump for a chain scope.
- **Generation path (ADR-0057 D-4; Workflow tool, ADR-0038):** generate the map in a single pass by default. WHERE the traversal needed to satisfy the scope is estimated to exceed a single context window (starting heuristic, adjustable: more than ~150 in-scope files to read, or a `chain:` walk that would pull more than ~80 files or ~25k tokens of source in one pass), STOP before generating and present a consent prompt naming the scope, the estimated worker count, what each worker will read, and that partials are merged by one writer. Only on explicit user consent dispatch a Workflow fleet (ADR-0038): one worker per disjoint sub-tree or module-group, each writing a partial, merged into the single MAP.md (and MAP.html when `html` is set) by this command as the sole writer. IF the user declines THEN produce a single-pass bounded map: cap the traversal at the budget and label it `bounded (partial)` in the artifact. Never fan out without explicit consent.
- **Ranking (D-12, extended by ADR-0072):** rank symbols and modules by internal import fan-in, most-relevant-first. WHEN no `keywords:` are provided, this fan-in-only order is the default, that Layer 2 is labeled ranking source `structural`, and the output is byte-identical to prior behavior (no keyword rerank runs). WHEN `keywords:` are provided, rerank Layer 2 symbols by blending fan-in with ripgrep keyword term-frequency via reciprocal rank fusion (see the keyword rerank rule below) and label that Layer 2 ranking source `structural + keyword`. Import fan-in stays the primary structural signal; the keyword signal only reorders within the same candidate set, it never adds or removes symbols. No embeddings and no vector index (ADR-0027 D-8, extended by ADR-0072); the only lexical signal is a ripgrep term-frequency count.
- **Keyword rerank blend (ADR-0072, optional):** this fires only WHEN `keywords:` are provided and touches Layer 2 symbol ordering only (Layer 1 and module ranking stay fan-in). Build two ranked lists over the same in-scope symbols: (1) the existing import fan-in order, and (2) a keyword order by ripgrep term-frequency, counting case-insensitive `rg` matches of the supplied terms across each symbol's cited `file:line` span (sum across terms; ties broken by fan-in). Fuse the two ranks with reciprocal rank fusion: `score(sym) = 1/(k + rank_fanin(sym)) + 1/(k + rank_keyword(sym))` with `k = 60`, then sort by descending score. A symbol with zero keyword hits is absent from list (2) and keeps only its fan-in term, so it can never outrank a symbol that matched. This is ripgrep-only: no embeddings, no vector index, and no persisted keyword index. WHEN no `keywords:` are provided, skip this rule entirely and emit the fan-in-only order unchanged. Under `--explain-ranking`, show each symbol's `rank_fanin`, `rank_keyword` (or `none`), and fused score.
- **Typed boundary edges:** detect db/http/queue/cache/external-api call-sites by pattern and record each as `kind | target | file:line`. Do not infer dataflow; record call-sites only.
- **No flow-graphs, no embeddings (D-7, D-8):** control/data-flow graphs and any vector/semantic layer are out of v1 scope. Do not add them.
- **Mermaid diagram emit (optional, ADR-0047):** when a diagram flag is set, render the ALREADY-EXTRACTED edges as Mermaid text appended to MAP.md. `diagram` renders module import adjacency and invoke edges as a flowchart (transitive-reduced, node-capped; collapse to module level above the cap rather than dumping). `sequence:<flow>` orders the extracted invoke and boundary edges for one named flow into a sequenceDiagram. This renders extracted edges only; it does not compute a control or data-flow graph (D-7/D-8 hold) and carries the grep-seed framing (a seed to verify; ripgrep is weakest on dynamic dispatch and async, so a sequence may be incomplete).
- **Exemplar retrieval (optional, W-18):** when `exemplars` is set, surface 1 to 3 blessed in-repo reference snippets (each a real file:line) an implementer should mirror for a slice with no internal precedent, chosen by import fan-in and convention fit. This is "copy this concrete in-repo pattern", distinct from `stack-currency-check` (external framework currency); the implementer cites the chosen exemplar in slice notes.
- **Human HTML projection (optional, ADR-0057 D-3):** when `html` is set, also write `MAP.html`, a single self-contained interactive HTML file (graph data and rendering inline; prefer no view-time external network dependency) into the gitignored `.code-context-map/` folder. It renders the ALREADY-EXTRACTED module/import edges (and, for `chain:` scope, the seed-anchored import chain) as a directed node-link graph with zoom, filter, hover-highlight, and click-to-open; node-cap large graphs (collapse to module level above the cap) so it stays readable. Regenerate on invoke like MAP.md (byte-identical yields `NO_OP`). It renders extracted edges and is a navigation seed, not authoritative (D-7/D-8 still hold), and lives only in the gitignored folder per the D-1 rule above.
- **Grep-seed framing:** the artifact must state that it orients the reader and that `grep`/reading the cited `file:line` is the source of truth; the code wins over the map on any disagreement.
- **Honesty about extraction limits:** ripgrep heuristics can miss dynamic imports, re-exports, and aliased calls. Record this in the artifact's limitations section; never present the map as exhaustive.
- Do not fabricate files, symbols, imports, or boundary edges. Every entry must trace to a real `file:line` in the target codebase.
- Cross-link policy: when a task is active, `SOURCE_OF_TRUTH.md` gets at most one `## Code context map` section with a single pointer to the artifact path. Do not duplicate map content into task memory.
- Treat task-memory write policy per `WORKFLOW_OPERATING_SYSTEM.md`: `PROPOSED` in Ask/Plan mode, `APPLIED` only in Agent mode. The map artifact itself is a product-repo file and follows repo reality, not the task-memory write policy.
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full). Default `Run now`: when a task is active, route to `impact-analysis` (use the map to scope a change) or `code-locate` (find a specific behavior); when no task is active, default to `what-next`.

Map format (canonical):
- Follow `templates/CODE_CONTEXT_MAP.template.md` exactly: header (generated-by, `Last generated` freshness with `branch@sha`, scope, token budget, grep-seed framing), Layer 1 (repo digest, module import adjacency, boundary summary), Layer 2 (per in-scope module: ranked signatures with the ranking-source label `structural` or `structural + keyword`, plus optional per-symbol scores under `--explain-ranking`, invoke edges, typed boundary edges), the typed boundary-edges table, an Excluded section, and a Known limitations section.
- For `chain:<seed-file>` scope, emit the `## Import chain` section from the template (seed, per-hop import edges, the fidelity label, the cycle-guard note) in addition to Layer 1.
- Sections with no content for the chosen scope (for example Layer 2 when scope is `digest`, or the import chain when scope is `digest` or `module:`) must be omitted rather than left empty.

Required output:
1. Resolved target codebase path and resolved scope (`digest`, `module:<...>`, or `chain:<seed-file>` with its `direction`/`max-hops`), token budget, and, when supplied, the resolved `keywords:` with the resulting Layer 2 ranking source (`structural` or `structural + keyword`).
2. Whether this is a `create`, a `refresh`, or a `NO_OP` (freshly generated map identical to the existing one), and whether it was generated single-pass or, with explicit consent, via a fleet.
3. Gitignore status: whether `.code-context-map/` was already ignored or an entry was appended.
4. Exact content for `.code-context-map/MAP.md` using the canonical map format (or the delta summary on refresh); when `html` is set, confirm `MAP.html` was (re)generated in the same gitignored folder.
5. Exact patch to the active task `SOURCE_OF_TRUTH.md` adding the `## Code context map` cross-link, or `SKIP` if none is active or it is already present.
6. Recommended next command (must exist in `commands/*.md`; verify against directory listing before output).
7. Recommended editor mode for that next command.
8. Why that is the correct next step.

### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- The artifact is written only inside `<target-codebase>/.code-context-map/` (MAP.md, and MAP.html when `html` is set), and `.code-context-map/` is confirmed present in the target repo's `.gitignore` (or appended).
- Layer 1 is always present; Layer 2 appears only for in-scope module(s) and respects the token budget; no flat whole-repo signature dump is produced.
- When `html` is set, `MAP.html` is a single self-contained file in the gitignored folder, renders only already-extracted edges, is node-capped for readability, and is never written outside `.code-context-map/`.
- Generation is single-pass by default; a fleet is dispatched only after an explicit consent prompt (scope, worker count, what each reads), and a decline yields a single-pass map labeled `bounded (partial)`. The fleet never runs without consent.
- For `chain:` scope, the import chain respects `max-hops` and the cycle guard, ranks within a hop by fan-in, and is labeled either faithful (with the parser named) or `grep-seed (non-authoritative)` when only ripgrep was used.
- Every file, symbol, import, invoke edge, and boundary edge traces to a real `file:line`; nothing is fabricated; extraction limits are stated in the artifact.
- The artifact records `Last generated` with `branch@sha`, the grep-seed framing, and the Known limitations section.
- No production source is modified; the only product-repo writes are the map and (at most) one `.gitignore` line.
- When a task is active, at most a single `## Code context map` cross-link is added to `SOURCE_OF_TRUTH.md`; otherwise `SKIP`.
- `### Artifact changes` marks task-memory patches as `PROPOSED` in Ask mode or `APPLIED` only when the user authorized Agent persistence; the product-repo map follows repo reality.
- The basename in the `Run now:` line corresponds to a real file in `commands/<name>.md`.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Optimize for token economy (ranked, layered, budgeted), fidelity to real `file:line` evidence, zero new runtime dependencies, and a map that is honestly a navigation seed rather than an authoritative or exhaustive index.

<!-- cache-breakpoint -->
