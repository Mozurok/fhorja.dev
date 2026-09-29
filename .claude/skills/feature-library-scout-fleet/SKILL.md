---
name: feature-library-scout-fleet
description: |-
  Orchestrator-workers variant of feature-library-scout for deep per-feature-problem library research. One worker per problem ranks candidate libraries by adoption signal (registry downloads, dependents, last release, stars and trend, maintenance, platform fit) relative to the project's ecosystem, grounded in captured sources; the orchestrator is the sole writer that merges into one FEATURE_LIBRARIES.md. Stack-agnostic (npm, PyPI, crates.io, Go, Maven). Use when the product has more than 3 distinct feature problems each warranting a deep read. Do not use for 1 to 3 problems (use feature-library-scout inline), to pick stack layers (use stack-recommend), to verify framework pattern currency (use stack-currency-check), or with no active task folder (run task-init first).
metadata:
  category: "research-and-sourcing"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "false"
  context-layers-consumed: "memory, retrieved"
  context-layers-produced: "retrieved"
  tools: "Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Agent"
  x-wos-profiles: "full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5-5"
  orchestrator: "true"
  workers: "[{\"role\":\"feature-problem-analyst\",\"dispatch-role\":\"mechanical\",\"contract_ref\":\"commands/_shared/worker-contract.md\"}]"
  max_fanout: "12"
  convergence: "{\"pattern\":\"barrier\",\"timeout_ms\":\"900000\",\"partial_ok\":\"true\"}"
  merge_strategy: "union"
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
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file...
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` b...
> - `Definition of done (command output)`: FEATURE_LIBRARIES.md uses the canonical template from `templates/FEATURE_LIBRARIES.template.md` (Snapshot metadata, per-problem bl...


Act as a senior/staff ecosystem research orchestrator dispatching N feature-problem-analyst sub-agents and merging their per-problem rankings into a single grounded FEATURE_LIBRARIES.md.

Goal:
For a product whose feature set decomposes into N >= 4 distinct feature problems (large lists, camera, forms, keyboard, bottom sheets, navigation, gestures, animation, offline), dispatch N `mechanical` workers in parallel (one per feature problem); each worker ranks the candidate libraries for its problem by adoption signal, grounded strictly in sources captured in `REFERENCES.md`, and returns a typed payload through the selected carrier; the orchestrator merges into a single `FEATURE_LIBRARIES.md` and is the sole writer of that file and of `REFERENCES.md`. Recommendations are optional guidance, never mandates (ADR-0045, D-F).

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 12109 tokens, the four always-read sections combined; the two skipped subsections are 1,034 of those (measured 2026-09-28), so the reduced tier is about 11,074. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 5215 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

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
- **Step 1: Decompose and validate.** Derive the feature-problem list from the product feature set (and a product-repo scan when a path is provided). Confirm N >= 4 problems (else NO_OP_TRACE: route to `feature-library-scout` inline). Assign a unique `problem_id` per problem. Confirm N <= `max_fanout`.
- **Step 2: Verify prerequisites.** `FEATURE_LIBRARIES.md` absent OR refresh flag set (else NO_OP_TRACE).
- **Step 3: Gather and capture (orchestrator, authorized fetcher).** For each problem, identify candidate libraries and gather their adoption signals from the stack's ecosystem (package registry per the stack: npm, PyPI, crates.io, Go, Maven; plus source-host repos, official docs, AAA-company posts, reference repos). Capture every cited source into `REFERENCES.md` via `capture-references` format BEFORE dispatch, so workers read signals rather than fetch them. When a signal cannot be fetched (rate limit, private repo), record `[not fetched]`; never guess. Note any rate-limit truncation for the merged Snapshot metadata.
- **Step 4: Verify the orchestrator constraint.** Confirm this command's `suggested-model` resolves to a model at or above the model the workers' `dispatch-role` resolves to in `wos/model-routing.md ## Dispatch roles` (`wos/sub-agent-orchestration.md ## Role-aware dispatch protocol`); refuse to dispatch if it does not. Workers are `mechanical`: per-problem ranking orders candidates by captured signals. The pick each worker names sits close to a judgment, which is why the placement is a provisional decision and experiment E1 checks it; override the workers up to `judgment` when a pick carries a real trade-off. The cross-problem merge is rule-based (one recommendation per problem, dedup by URL).
- **Step 5: Dispatch workers (ADR-0038 Rule 1, typed-return transport).** For each problem, invoke a stateless sub-agent via the selected dispatch path, naming the agent type explicitly (`agentType: 'general-purpose'`). Never leave it unset: a fork inherits the whole conversation and drops the input isolation a fresh sub-agent provides. Pass `task_input` matching `worker_input_schema`. Each worker MUST return a payload matching `worker_output_schema`; free-form prose returns are FORBIDDEN. Free-form prose responses or `.partial.md` writes are FORBIDDEN (ADR-0038 Rule 1). Workers MUST NOT write `FEATURE_LIBRARIES.md` or `REFERENCES.md` (ADR-0038 Rule 2). Name the path you are on before dispatch (ADR-0158 D-1). Resolve `<task_root>/.wos/fleet-inbox/<run_id>/<worker_id>.json` for each worker and create the run inbox. On the dynamic-workflow path, declare `agent(prompt, {schema})` with `worker_output_schema`; consume the runtime's typed result and persist its JSON copy at that path. Never tell the worker to call StructuredOutput. On the `Agent` path, pass the resolved path as `fleet_inbox_artifact` in the existing worker-contract envelope, outside `task_input`; the worker writes one schema-conforming JSON payload there and the orchestrator reads it. This return-file permission grants no other writes (ADR-0158 D-2). Supply the output schema and selected-carrier instruction outside `task_input`. End the dynamic worker prompt with `Return one payload matching worker_output_schema and nothing else`; end the native worker prompt with `Write one JSON payload matching worker_output_schema to fleet_inbox_artifact and nothing else`.
- **Step 6: Each worker (instruction template).** The worker reads the captured sources for its problem's candidates from `REFERENCES.md` (it MUST NOT fetch the web); fills the adoption-signal fields per candidate from those sources; marks any unfetched signal `[not fetched]`; selects a `recommended_pick` with a one-line `recommendation_reason` grounded in the signals; lists `alternatives` with when to prefer them; surfaces `gaps`; and returns the payload by the carrier its dispatch path names (ADR-0158 D-1), never by calling a tool it was not given. Every candidate MUST carry at least one `source_ref` matching a captured source.
- **Step 7: Wait for convergence.** Barrier: wait for all N workers OR `timeout_ms` (15 min default). Consume one schema-conforming payload per expected worker from the runtime result or its assigned `<task_root>/.wos/fleet-inbox/<run_id>/<worker_id>.json`; ignore unrelated files and do not count replay copies twice. Classify each result per `commands/_shared/convergence-policy.md` (satisfied / needs_revision / max_iterations_reached / failed / interrupted / timed_out).
- **Step 8: Merge FEATURE_LIBRARIES.md (ADR-0038 Rule 2, deterministic apply).** Apply `union` merge following `templates/FEATURE_LIBRARIES.template.md`: one per-problem block per surviving worker payload (candidate table from `candidates[]`, recommended pick from `recommended_pick`, alternatives, sources); aggregate all sources into the consolidated Sources list (dedup by URL); record `Last refreshed: <YYYY-MM-DD>` and the signal-freshness line (note any `[not fetched]` or truncation). Frame all picks as optional guidance. Replace `FEATURE_LIBRARIES.md` in full. This is the single-writer sequential apply step.
- **Step 9: Emit VERIFICATION_LOG.jsonl.** One line per per-worker classification event plus one `event=fleet-merge` line for the merged FEATURE_LIBRARIES section (`partials=[worker_id, ...]`, `strategy=union`).
- **Step 10: Update SOURCE_OF_TRUTH.md.** Append the `## Feature libraries` link to `./FEATURE_LIBRARIES.md` if not already present.
- **Step 11: Update REFERENCES.md.** Append any newly-captured sources per `capture-references` format. Deduplicate by URL.
- **Step 12: Scan substrate orphans (ADR-0038 Rule 3).** After Steps 8 and 11, run `python scripts/scan-substrate-orphans.py <task_root>/FEATURE_LIBRARIES.md <project_root>/REFERENCES.md`, with `scripts/scan-substrate-orphans.py` (resolved against the WORKFLOW ROOT, ADR-0218); its exit 2 means a named file was absent, never a pass. Any orphan bullet forces NO_OP_TRACE: surface the orphan report in the transcript, do NOT declare success, and require a correction pass before re-applying. A clean scan (exit 0) is required to declare the apply contract satisfied.
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

### Claim grounding (active epistemic humility)
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
Produce the command output using this structure (English only):

### Artifact changes
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- FEATURE_LIBRARIES.md uses the canonical template from `templates/FEATURE_LIBRARIES.template.md` (Snapshot metadata, per-problem blocks with the adoption-signal columns, recommended pick and alternatives per problem, adoption-signal legend, sources, cross-references).
- Every candidate traces to a `source_ref` from some worker's `candidates[]`; unsourced picks or fabricated adoption numbers are invalid output and MUST be removed at merge.
- Per-worker payloads consumed from the selected carrier and recorded in `<task_root>/.wos/fleet-inbox/<run_id>/<worker_id>.json` (no prose `.partial.md` files; ADR-0038 Rule 1).
- The orchestrator is the SOLE writer of FEATURE_LIBRARIES.md and REFERENCES.md; worker contract violations (mid-flight writes, missing or invalid payloads on the selected carrier) are listed in `### Command transcript`.
- Picks are framed as optional guidance; none is mandatory (D-F). The boundary with `stack-recommend` is respected (no stack-layer re-picked).
- `scripts/scan-substrate-orphans.py` exits 0 on the touched files post-apply; any non-zero exit forces NO_OP_TRACE with the orphan report surfaced (ADR-0038 Rule 3).
- The basename in the `Run now:` line corresponds to a real file in `commands/<name>.md`.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The grounding integrity of `feature-library-scout` is preserved: every pick still traces to a captured source and no adoption number is invented. ADR-0038 enforces three invariants on this fleet variant: workers return typed payloads through the selected carrier (Rule 1); only the orchestrator writes FEATURE_LIBRARIES.md and REFERENCES.md (Rule 2); `scripts/scan-substrate-orphans.py` gates apply success (Rule 3). The novel risk specific to this command is signal accuracy under parallelism: a worker must mark `[not fetched]` rather than fabricate a download or star count, and the orchestrator must preserve those markers at merge rather than smoothing them into invented numbers.
