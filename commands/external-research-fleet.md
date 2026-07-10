---
name: external-research-fleet
description: Orchestrator-workers variant of external-research for multi-modal sweep across distinct angles or source-groups of one research question. Promotes external-research's inline delegation to a first-class orchestrator with a worker contract and provenance. Sonnet orchestrator dispatches N Sonnet workers (one angle each) in parallel; each produces a structured per-angle synthesis grounded in REFERENCES.md; orchestrator merges into a single EXTERNAL_RESEARCH.md with cross-angle reconciliation (reinforcing vs contradicting vs different-framing). Use when the research question has N >= 3 distinct angles or source-groups AND the question would benefit from parallel deep reads. Do not use when 1-3 sources suffice (use external-research inline), when one source already dominates (no parallelism gain), or when sources have not yet been captured (run capture-references first).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Ask
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [retrieved]
  tools: [Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Task]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 5000
  suggested-model: claude-sonnet-4-6
  orchestrator: true
  workers:
    - role: research-angle-analyst
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
      "required": ["angle_id", "angle_name", "angle_question", "sources", "task_root", "references_path"],
      "properties": {
        "angle_id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
        "angle_name": {"type": "string"},
        "angle_question": {"type": "string", "minLength": 10},
        "parent_question": {"type": "string"},
        "sources": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["title", "url"],
            "properties": {
              "title": {"type": "string"},
              "url": {"type": "string"},
              "references_entry_status": {"enum": ["pre-existing", "newly-captured"]}
            }
          }
        },
        "task_root": {"type": "string"},
        "references_path": {"type": "string"},
        "output_structure": {"enum": ["narrative", "comparison-table", "decision-matrix", "regulatory-checklist"]}
      }
    }
  worker_output_schema: |
    {
      "type": "object",
      "required": ["status", "angle_id", "claims", "citations"],
      "properties": {
        "status": {"enum": ["satisfied", "needs_revision", "max_iterations_reached", "failed", "interrupted"]},
        "angle_id": {"type": "string"},
        "claims": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["claim", "source_ref", "confidence"],
            "properties": {
              "claim": {"type": "string"},
              "source_ref": {"type": "string"},
              "verbatim_quote": {"type": "string"},
              "confidence": {"enum": ["high", "medium", "low", "unclear-from-source"]}
            }
          }
        },
        "citations": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["source_title", "source_url"],
            "properties": {
              "source_title": {"type": "string"},
              "source_url": {"type": "string"},
              "role_in_synthesis": {"type": "string"}
            }
          }
        },
        "per_dimension_findings": {
          "type": "object",
          "additionalProperties": {"type": "string"}
        },
        "gaps": {"type": "array", "items": {"type": "string"}},
        "angle_recommendation": {"type": "string"}
      }
    }
---
# external-research-fleet

Act as a senior/staff research synthesis orchestrator dispatching N research-angle-analyst sub-agents and reconciling their per-angle findings into a single grounded EXTERNAL_RESEARCH.md.

Goal:
For research questions whose answer requires N >= 3 distinct angles (operational vs cost vs regulatory vs migration vs team-fit) OR N >= 3 source-groups (vendor docs vs independent comparisons vs community discussions vs case studies), dispatch N Sonnet workers in parallel; each worker grounds its per-angle synthesis strictly in the sources assigned to it; the orchestrator merges into a single EXTERNAL_RESEARCH.md with explicit cross-angle reconciliation per ADR-0018 (reinforcing vs contradicting vs different-framing) and emits ONE canonical recommendation visually separated from the source-grounded analysis. Expected wall-clock reduction vs sequential external-research: ~N/2 (web fetches dominate when sources are URLs; partial parallelism in MCP throttling).

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
- the parent research question (one sentence; the same question that would be passed to `external-research`)
- angles manifest: array of `{angle_id, angle_name, angle_question, sources: [{title, url, references_entry_status}, ...]}` (caller pre-decomposes the parent question into angles AND pre-assigns sources to angles; the orchestrator does NOT auto-decompose)
- path to `REFERENCES.md` at the project root
- optional: output structure hint for the merged synthesis (`narrative` / `comparison-table` / `decision-matrix` / `regulatory-checklist`)
- optional: explicit max_fanout override (defaults to 12; absolute ceiling 20)
- optional: refresh flag (`refresh` to regenerate an existing `EXTERNAL_RESEARCH.md`; default is NO_OP_TRACE if a non-stale file already exists)

Task repository files to update:
- `<task_root>/EXTERNAL_RESEARCH.md` (orchestrator is the SOLE writer per `wos/substrate-peers.md`; replaced in full, never partial-merged)
- `<task_root>/SOURCE_OF_TRUTH.md` append-only `## External research` cross-link if not present
- `projects/<client>__<project>/REFERENCES.md` (only when new sources are captured during this run; deduplicated by URL per `capture-references` format)
- `.wos/fleet-inbox/<run_id>/` logical artifact namespace for per-worker StructuredOutput results (typed payloads consumed by the orchestrator main loop; not free-form prose files)
- `.wos/VERIFICATION_LOG.jsonl` (one line per merged section + one per per-worker classification event; every line MUST pass `scripts/verify-log-validator.py` per the Step 9 constraints)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- **Step 1: Validate manifest.** Confirm N >= 3 angles (else NO_OP_TRACE: route to `external-research` inline). Confirm every `angle_id` unique. Confirm every angle has >= 1 source assigned. Confirm no source is assigned to more than one angle (sources may overlap across angles per ADR-0018 cross-source context, but assignment for the fleet dispatch MUST be unique to avoid double-counting in claim weighting). Confirm N <= `max_fanout`.
- **Step 2: Verify prerequisites.** `EXTERNAL_RESEARCH.md` either absent OR refresh flag explicitly set (else NO_OP_TRACE). Every assigned source URL MUST already exist in `REFERENCES.md`; any `newly-captured` URL is routed through `capture-references` by the orchestrator BEFORE dispatch (workers are not in the authorized-fetch set per the spec `### External web access (centralized)`, so a worker never fetches the web).
- **Step 3: Verify tier guard.** Orchestrator runs Sonnet-class; workers run Sonnet-class (both per the `suggested-model` frontmatter, not pinned in prose). Per `wos/sub-agent-orchestration.md ## Tier-mapping per role`: per-target deep analysis (one angle, one source-group) -> Sonnet-class; cross-target synthesis (final EXTERNAL_RESEARCH.md merge) -> Sonnet-class acceptable here because reconciliation rules are structured (ADR-0018 reinforcing/contradicting/different-framing taxonomy + explicit recommendation section). Override-down from the default Opus-class orchestrator: rationale = "merge structure is rule-based not judgment-heavy; recommendation is one paragraph; cost guard favors the lower tier". Tier guard PASS (equal tier allowed).
- **Step 4: Dispatch workers (ADR-0038 Rule 1 -- StructuredOutput transport).** For each angle entry, invoke a stateless sub-agent (Claude Code `Task` tool with `subagent_type: general-purpose`) via the Workflow tool. Pass `task_input` matching `worker_input_schema`. Each worker MUST return its result by invoking the `StructuredOutput` tool with `artifact=fleet-inbox/<run_id>/<worker_id>` and `content=<JSON payload matching worker_output_schema>`. Free-form prose responses or `.partial.md` file writes are FORBIDDEN per ADR-0038 Rule 1 (structured output mandatory); the main loop consumes typed data, not parsed prose. Workers MUST NOT touch EXTERNAL_RESEARCH.md or REFERENCES.md directly (ADR-0038 Rule 2: substrate writes sequenced through the orchestrator apply step).
- **Step 5: Each worker (instruction template).** Worker reads each assigned source from its pre-captured `REFERENCES.md` entry (workers are NOT in the authorized-fetch set per the spec `### External web access (centralized)` and MUST NOT fetch the web; any missing URL was routed through `capture-references` by the orchestrator in Step 2); extracts verbatim quotes for load-bearing claims; produces a structured per-angle response payload: `{status, angle_id, claims: [{claim, source_ref, verbatim_quote?, confidence}, ...], citations: [{source_title, source_url, role_in_synthesis}, ...], per_dimension_findings: {<dim>: <finding>}, gaps: [...], angle_recommendation: "<one-line direction inferred from this angle alone>"}` and returns it via the `StructuredOutput` tool (artifact=`fleet-inbox/<run_id>/<worker_id>`). Worker MUST mark every claim with a `source_ref` matching one of the assigned `sources` (else `confidence: unclear-from-source`). Worker MUST surface newly-discovered sources via the `citations[]` array with role_in_synthesis explaining their use (the orchestrator dedupes and routes to capture-references at merge).
- **Step 6: Wait for convergence (consume StructuredOutput results).** Barrier pattern: wait for all N workers OR `timeout_ms` (15 min default; web fetches latency-sensitive). Consume each worker's `StructuredOutput` tool-call result as typed data keyed by `artifact=fleet-inbox/<run_id>/<worker_id>`; do NOT read prose files. Classify each result per `commands/_shared/convergence-policy.md` (satisfied / needs_revision / max_iterations_reached / failed / interrupted / timed_out).
- **Step 7: Cross-angle reconciliation (per ADR-0018).** For each claim across surviving structured payloads, group by topic (semantic similarity on `claim` text, threshold conservative -- when in doubt, leave separate). Tag each group as: REINFORCING (>=2 angles agree on direction, no contradiction), CONTRADICTING (>=2 angles disagree on direction; flag as decision question), DIFFERENT-FRAMING (angles address distinct facets of the same topic; not a contradiction). Surface every CONTRADICTING group explicitly in the merged synthesis under `## Conflicts surfaced` with the angles citing each side.
- **Step 8: Merge EXTERNAL_RESEARCH.md (ADR-0038 Rule 2 -- deterministic apply).** Apply `union` merge: assemble the canonical synthesis (see `commands/external-research.md` synthesis format) with one Analysis subsection per angle (or per dimension when angles map naturally to dimensions); aggregate citations into the Sources list (deduplicate by URL); compose ONE recommendation paragraph synthesizing across angles (the orchestrator's call, visually separated from analysis); emit Open questions from union of `gaps[]` across workers minus any closed by reconciliation; record `Last refreshed: <YYYY-MM-DD>`. Replace EXTERNAL_RESEARCH.md in full. This is the single-writer sequential apply step required by ADR-0038 Rule 2.
- **Step 9: Emit VERIFICATION_LOG.jsonl.** One line per per-worker classification event plus one line for the merged EXTERNAL_RESEARCH section (`event=fleet-merge`, `partials=[worker_id, ...]`, `strategy=union`) AND one line per CONTRADICTING group with `event=fleet-merge` and a `reason` field naming the contradicting angles. Every emitted line MUST satisfy the K.5 schema (`wos/substrate-peers.md ## Audit trail`) as enforced by `scripts/verify-log-validator.py`: every `event=fleet-merge` line MUST set `owner_type=fleet-merger` (NEVER `command`), a non-empty `partials` array of worker ids, and a `strategy` from the merge-strategy enum (`union` | `last-by-timestamp` | `consensus-of-N` | `manual-review`; any other value, such as `surface`, is invalid); every `section` value MUST be a real H2 anchor starting with `## ` (for the full-file EXTERNAL_RESEARCH.md replace, use its first H2, `## Snapshot metadata`; NEVER a placeholder like `(full)`); every `reason` MUST be at most 80 characters. After emission, this command MUST run `python3 scripts/verify-log-validator.py <task_root>/.wos/VERIFICATION_LOG.jsonl` and fix every invalid line before declaring the run done; a run whose audit lines fail the validator SHALL NOT be declared done.
- **Step 10: Update SOURCE_OF_TRUTH.md.** Append `## External research` link to `./EXTERNAL_RESEARCH.md` if not already present.
- **Step 11: Update REFERENCES.md.** For each `newly-captured` source returned by workers, append per `capture-references` format. Deduplicate by URL.
- **Step 12: Scan substrate orphans (ADR-0038 Rule 3 -- orphan check post-apply).** After Steps 8 and 11 complete, run `python scripts/scan-substrate-orphans.py <task_root>/EXTERNAL_RESEARCH.md <project_root>/REFERENCES.md`. If the scanner reports any orphan bullet (a bullet without a semantic parent heading or list anchor), NO_OP_TRACE the run: surface the orphan report in the command transcript, do NOT declare success, and require a follow-up correction pass before re-applying. A clean scan (exit 0) is required to declare the apply contract satisfied. See `wos/bug-classes/substrate-bullet-orphan.md` for the failure-mode definition this gate prevents.
- Workers NEVER write EXTERNAL_RESEARCH.md or REFERENCES.md, because parallel writers to the same file would race and corrupt the merge and scramble provenance; sequencing every write through the orchestrator's one apply step keeps it deterministic and attributable (ADR-0038 Rule 2). The orchestrator is the SOLE writer of both files in fleet mode.
- A source assigned to one angle MAY be cited by other angles in their per-angle findings if discovered in-line, but the canonical "Sources" list at orchestrator-merge time deduplicates by URL.
- Contradicting claims are SURFACED, not RESOLVED. The recommendation paragraph may state which side the orchestrator favors with rationale, but the conflict remains visible in `## Conflicts surfaced` for the user to validate.

Required output:
1. Angle inventory: N angles dispatched + parent question
2. Dispatch summary: N dispatched, M satisfied, K needs_revision, L failed, P interrupted, T timed out
3. Source inventory: pre-existing + newly captured, total unique URLs
4. Reconciliation summary: REINFORCING groups, CONTRADICTING groups (flagged for follow-up), DIFFERENT-FRAMING groups
5. Path to merged EXTERNAL_RESEARCH.md
6. One-line recommendation summary (orchestrator's call)
7. Top 5 open questions
8. Orphan scan result on EXTERNAL_RESEARCH.md and REFERENCES.md (must be clean to declare success)
9. Recommended next command (typically `decision-interview` if CONTRADICTING groups surfaced, or `implementation-plan` if synthesis concluded the path)

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
- EXTERNAL_RESEARCH.md uses the canonical synthesis format from `commands/external-research.md` (Snapshot metadata, Question recap, Sources, Analysis with citations, Trade-off summary when comparing options, Recommendation visually separated, Open questions, Cross-references).
- Every claim in Analysis traces to a `source_ref` from some worker's `claims[]`; unsourced claims are invalid output and MUST be removed at merge time.
- `## Conflicts surfaced` section present when N >= 1 CONTRADICTING group detected; absent otherwise.
- Per-worker structured payloads consumed from `StructuredOutput` tool-call results keyed under `fleet-inbox/<run_id>/<worker_id>` (no prose `.partial.md` files; ADR-0038 Rule 1).
- REFERENCES.md updated for newly-captured sources, deduplicated by URL.
- Worker contract violations (mid-flight writes to EXTERNAL_RESEARCH / REFERENCES, or free-form prose responses that skip the `StructuredOutput` tool) explicitly listed in `### Command transcript`.
- Substrate peer rule respected: EXTERNAL_RESEARCH.md is owned by this command in fleet mode (single-source `external-research` retains co-ownership for sequential runs; mixed-mode is reconciled by `state-reconcile`).
- Recommendation is ONE paragraph and visually separated from Analysis; the orchestrator's call is explicit ("the model recommends X with rationale Y; the user should validate against operational context").
- `scripts/scan-substrate-orphans.py` exits 0 on the touched files (EXTERNAL_RESEARCH.md and REFERENCES.md) post-apply; any non-zero exit forces NO_OP_TRACE with the orphan report surfaced in the transcript (ADR-0038 Rule 3).
- `python3 scripts/verify-log-validator.py <task_root>/.wos/VERIFICATION_LOG.jsonl` exits 0 after Step 9; every `event=fleet-merge` line carries `owner_type=fleet-merger`, non-empty `partials`, and an enum `strategy`, every `section` starts with `## `, and every `reason` is at most 80 characters. Any invalid line MUST be fixed before the run is declared done.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
J.9 orchestrator pilot, retrofitted to ADR-0038 binding rules. The grounding integrity property of `external-research` is preserved: every claim still traces to a captured source. ADR-0038 enforces three additional invariants on this fleet variant: (Rule 1) workers return typed payloads via `StructuredOutput` so the main loop never re-parses prose; (Rule 2) only the orchestrator writes EXTERNAL_RESEARCH.md and REFERENCES.md, via the deterministic Step 8 / Step 11 apply blocks; (Rule 3) `scripts/scan-substrate-orphans.py` gates apply success, preventing the substrate-bullet-orphan failure class documented in `wos/bug-classes/substrate-bullet-orphan.md`. The novel risk specific to this command is cross-angle claim grouping at reconciliation: silent over-grouping (collapsing two distinct claims into one) hides contradictions; silent under-grouping (treating identical claims as distinct) inflates the "reinforcing" count and overweights the recommendation. When in doubt, leave separate. The output is the eval-baseline for K.7 vs `external-research` inline on the same parent question.

<!-- cache-breakpoint -->
