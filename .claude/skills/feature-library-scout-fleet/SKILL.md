---
name: feature-library-scout-fleet
description: |-
  Orchestrator-workers variant of feature-library-scout for deep per-feature-problem library research. The orchestrator derives the feature-problem list and dispatches one Sonnet worker per problem; each worker ranks candidate libraries by adoption signal (registry downloads, dependents, last release, stars and trend, maintenance, framework/platform fit) relative to the project's ecosystem, grounded in captured REFERENCES.md sources, and returns a typed payload via StructuredOutput; the orchestrator is the sole writer that merges into one FEATURE_LIBRARIES.md and runs the orphan-scan gate (ADR-0038, ADR-0045). Stack-agnostic (npm, PyPI, crates.io, Go, Maven). Use when the product has 3 or more distinct feature problems that each warrant a deep multi-angle read. Do not use for 1-3 problems (use feature-library-scout inline), to pick stack layers (use stack-recommend), to verify framework pattern currency (use stack-currency-check), or with no active task folder (run task-init first).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
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
    - WebFetch
    - WebSearch
    - Task
  x-wos-profiles:
    - full
  provenance: first-party
  token-budget: 5000
  suggested-model: claude-sonnet-4-6
  orchestrator: true
  workers:
    - role: feature-problem-analyst
      tier: claude-sonnet-4-6
      contract_ref: commands/_shared/worker-contract.md
  max_fanout: 12
  convergence:
    pattern: barrier
    timeout_ms: 900000
    partial_ok: true
  merge_strategy: union
  worker_input_schema: |
    {
      "type": "object",
      "required": ["problem_id", "problem_name", "candidate_libraries", "task_root", "references_path"],
      "properties": {
        "problem_id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
        "problem_name": {"type": "string"},
        "stack": {"type": "string"},
        "candidate_libraries": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["name"],
            "properties": {
              "name": {"type": "string"},
              "source_urls": {"type": "array", "items": {"type": "string"}}
            }
          }
        },
        "task_root": {"type": "string"},
        "references_path": {"type": "string"}
      }
    }
  worker_output_schema: |
    {
      "type": "object",
      "required": ["status", "problem_id", "candidates", "recommended_pick"],
      "properties": {
        "status": {"enum": ["satisfied", "needs_revision", "max_iterations_reached", "failed", "interrupted"]},
        "problem_id": {"type": "string"},
        "candidates": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["library", "source_refs"],
            "properties": {
              "library": {"type": "string"},
              "registry_downloads": {"type": "string"},
              "dependents": {"type": "string"},
              "last_release": {"type": "string"},
              "release_cadence": {"type": "string"},
              "stars_and_trend": {"type": "string"},
              "maintenance_health": {"type": "string"},
              "framework_platform_fit": {"type": "string"},
              "license": {"type": "string"},
              "source_refs": {"type": "array", "items": {"type": "string"}}
            }
          }
        },
        "recommended_pick": {"type": "string"},
        "recommendation_reason": {"type": "string"},
        "alternatives": {"type": "array", "items": {"type": "string"}},
        "gaps": {"type": "array", "items": {"type": "string"}}
      }
    }
---

Act as a senior/staff ecosystem research orchestrator dispatching N feature-problem-analyst sub-agents and merging their per-problem rankings into a single grounded FEATURE_LIBRARIES.md.

Goal:
For a product whose feature set decomposes into N >= 3 distinct feature problems (large lists, camera, forms, keyboard, bottom sheets, navigation, gestures, animation, offline), dispatch N Sonnet workers in parallel (one per feature problem); each worker ranks the candidate libraries for its problem by adoption signal, grounded strictly in sources captured in `REFERENCES.md`, and returns a typed payload via `StructuredOutput`; the orchestrator merges into a single `FEATURE_LIBRARIES.md` and is the sole writer of that file and of `REFERENCES.md`. Recommendations are optional guidance, never mandates (ADR-0045, D-F).

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
- active task folder path
- the chosen stack (from `SOURCE_OF_TRUTH.md`, `STACK_RECOMMENDATION.md`, or `PROJECT_CHARTER.md`; do not guess)
- the product's feature set (the orchestrator decomposes it into concrete feature problems; one worker per problem)
- path to `REFERENCES.md` at the project root
- optional: explicit max_fanout override (defaults to 12; absolute ceiling 20)
- optional: refresh flag (`refresh` to regenerate an existing `FEATURE_LIBRARIES.md`; default is NO_OP_TRACE if a non-stale file already exists)

External web access:
- This command (the orchestrator) is in the authorized-command set in the spec `## Cross-cutting workflow guardrails ### External web access (centralized)`, scoped to per-feature library discovery and adoption-signal gathering. Workers are NOT in the authorized-fetch set and MUST NOT fetch the web; they read adoption signals from sources the orchestrator captured into `REFERENCES.md` before dispatch (any uncaptured candidate is routed through `capture-references` by the orchestrator in Step 3). The orchestrator funnels every fetched source into `REFERENCES.md` (capture-references format, deduplicated by URL).

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- **Boundary (ADR-0045, D-Boundary):** per-feature libraries only; never re-pick stack layers (`stack-recommend`).
- **Step 1: Decompose and validate.** Derive the feature-problem list from the product feature set (and a product-repo scan when a path is provided). Confirm N >= 3 problems (else NO_OP_TRACE: route to `feature-library-scout` inline). Assign a unique `problem_id` per problem. Confirm N <= `max_fanout`.
- **Step 2: Verify prerequisites.** `FEATURE_LIBRARIES.md` absent OR refresh flag set (else NO_OP_TRACE).
- **Step 3: Gather and capture (orchestrator, authorized fetcher).** For each problem, identify candidate libraries and gather their adoption signals from the stack's ecosystem (package registry per the stack: npm, PyPI, crates.io, Go, Maven; plus source-host repos, official docs, AAA-company posts, reference repos). Capture every cited source into `REFERENCES.md` via `capture-references` format BEFORE dispatch, so workers read signals rather than fetch them. When a signal cannot be fetched (rate limit, private repo), record `[not fetched]`; never guess. Note any rate-limit truncation for the merged Snapshot metadata.
- **Step 4: Tier guard.** Orchestrator Sonnet-class; workers Sonnet-class (per the `suggested-model` frontmatter, not pinned in prose). Per-problem ranking is structured analysis (rank by captured signals), so Sonnet workers are correct; the cross-problem merge is rule-based (one recommendation per problem, dedup by URL), so a Sonnet orchestrator is acceptable. Tier guard PASS (equal tier allowed).
- **Step 5: Dispatch workers (ADR-0038 Rule 1, StructuredOutput transport).** For each problem, invoke a stateless sub-agent via the Workflow tool. Pass `task_input` matching `worker_input_schema`. Each worker MUST return its result by invoking the `StructuredOutput` tool with `artifact=fleet-inbox/<run_id>/<worker_id>` and `content=<JSON matching worker_output_schema>`. Free-form prose responses or `.partial.md` writes are FORBIDDEN (ADR-0038 Rule 1). Workers MUST NOT write `FEATURE_LIBRARIES.md` or `REFERENCES.md` (ADR-0038 Rule 2).
- **Step 6: Each worker (instruction template).** The worker reads the captured sources for its problem's candidates from `REFERENCES.md` (it MUST NOT fetch the web); fills the adoption-signal fields per candidate from those sources; marks any unfetched signal `[not fetched]`; selects a `recommended_pick` with a one-line `recommendation_reason` grounded in the signals; lists `alternatives` with when to prefer them; surfaces `gaps`; and returns the payload via `StructuredOutput` (artifact=`fleet-inbox/<run_id>/<worker_id>`). Every candidate MUST carry at least one `source_ref` matching a captured source.
- **Step 7: Wait for convergence.** Barrier: wait for all N workers OR `timeout_ms` (15 min default). Classify each result per `commands/_shared/convergence-policy.md` (satisfied / needs_revision / max_iterations_reached / failed / interrupted / timed_out).
- **Step 8: Merge FEATURE_LIBRARIES.md (ADR-0038 Rule 2, deterministic apply).** Apply `union` merge following `templates/FEATURE_LIBRARIES.template.md`: one per-problem block per surviving worker payload (candidate table from `candidates[]`, recommended pick from `recommended_pick`, alternatives, sources); aggregate all sources into the consolidated Sources list (dedup by URL); record `Last refreshed: <YYYY-MM-DD>` and the signal-freshness line (note any `[not fetched]` or truncation). Frame all picks as optional guidance. Replace `FEATURE_LIBRARIES.md` in full. This is the single-writer sequential apply step.
- **Step 9: Emit VERIFICATION_LOG.jsonl.** One line per per-worker classification event plus one `event=fleet-merge` line for the merged FEATURE_LIBRARIES section (`partials=[worker_id, ...]`, `strategy=union`).
- **Step 10: Update SOURCE_OF_TRUTH.md.** Append the `## Feature libraries` link to `./FEATURE_LIBRARIES.md` if not already present.
- **Step 11: Update REFERENCES.md.** Append any newly-captured sources per `capture-references` format. Deduplicate by URL.
- **Step 12: Scan substrate orphans (ADR-0038 Rule 3).** After Steps 8 and 11, run `python scripts/scan-substrate-orphans.py <task_root>/FEATURE_LIBRARIES.md <project_root>/REFERENCES.md`. Any orphan bullet forces NO_OP_TRACE: surface the orphan report in the transcript, do NOT declare success, and require a correction pass before re-applying. A clean scan (exit 0) is required to declare the apply contract satisfied.
- Workers NEVER write `FEATURE_LIBRARIES.md` or `REFERENCES.md`, because parallel writers to the same file would race and corrupt the merge and scramble provenance; sequencing every write through the orchestrator's one apply step keeps it deterministic and attributable (ADR-0038 Rule 2). The orchestrator is the SOLE writer of both in fleet mode.
- Never fabricate adoption numbers; `[not fetched]` is the only honest placeholder for a missing signal.

Required output:
1. Problem inventory: N feature problems decomposed + the stack.
2. Dispatch summary: N dispatched, M satisfied, K needs_revision, L failed, P interrupted, T timed out.
3. Source inventory: pre-existing + newly captured, total unique URLs.
4. Path to merged FEATURE_LIBRARIES.md.
5. One-line recommended pick per feature problem.
6. Top open questions (union of worker `gaps[]`).
7. Orphan scan result on FEATURE_LIBRARIES.md and REFERENCES.md (must be clean to declare success).
8. Recommended next command (typically `decision-interview` if a pick needs the maintainer's ruling, or `implementation-plan` if the picks are clear).

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
- FEATURE_LIBRARIES.md uses the canonical template from `templates/FEATURE_LIBRARIES.template.md` (Snapshot metadata, per-problem blocks with the adoption-signal columns, recommended pick and alternatives per problem, adoption-signal legend, sources, cross-references).
- Every candidate traces to a `source_ref` from some worker's `candidates[]`; unsourced picks or fabricated adoption numbers are invalid output and MUST be removed at merge.
- Per-worker payloads consumed from `StructuredOutput` tool-call results keyed under `fleet-inbox/<run_id>/<worker_id>` (no prose `.partial.md` files; ADR-0038 Rule 1).
- The orchestrator is the SOLE writer of FEATURE_LIBRARIES.md and REFERENCES.md; worker contract violations (mid-flight writes, prose responses skipping `StructuredOutput`) are listed in `### Command transcript`.
- Picks are framed as optional guidance; none is mandatory (D-F). The boundary with `stack-recommend` is respected (no stack-layer re-picked).
- `scripts/scan-substrate-orphans.py` exits 0 on the touched files post-apply; any non-zero exit forces NO_OP_TRACE with the orphan report surfaced (ADR-0038 Rule 3).
- The basename in the `Run now:` line corresponds to a real file in `commands/<name>.md`.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The grounding integrity of `feature-library-scout` is preserved: every pick still traces to a captured source and no adoption number is invented. ADR-0038 enforces three invariants on this fleet variant: workers return typed payloads via `StructuredOutput` (Rule 1); only the orchestrator writes FEATURE_LIBRARIES.md and REFERENCES.md (Rule 2); `scripts/scan-substrate-orphans.py` gates apply success (Rule 3). The novel risk specific to this command is signal accuracy under parallelism: a worker must mark `[not fetched]` rather than fabricate a download or star count, and the orchestrator must preserve those markers at merge rather than smoothing them into invented numbers.

<!-- cache-breakpoint -->
