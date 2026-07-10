---
name: screen-spec-fleet
description: Orchestrator-workers variant of screen-spec. Dispatches N Sonnet workers (1 screen each) in parallel to generate per-screen spec docs from Figma frames, then merges SCREEN_MAP.md and routes.md from per-worker partials. Use when screen count >= 6 AND Figma MCP is available AND foundations + SCREEN_MAP exist. Do not use for single screens (use screen-spec), when foundations are missing (use design-bootstrap first), or when frames have not been enumerated yet (caller must supply screen_number+slug+persona+node_id per screen).
metadata:
  category: discovery-and-scoping
  primary-cursor-mode: Agent
  multi-repo-aware: false
  context-layers-consumed: [memory, retrieved]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep, Task]
  x-wos-profiles: [full]
  provenance: first-party
  token-budget: 4500
  suggested-model: claude-sonnet-4-6
  orchestrator: true
  workers:
    - role: screen-spec-author
      tier: claude-sonnet-4-6
      contract_ref: commands/_shared/worker-contract.md
  max_fanout: 20
  convergence:
    pattern: barrier
    timeout_ms: 900000
    partial_ok: true
  merge_strategy: union
  worker_input_schema: |
    {
      "type": "object",
      "required": ["screen_number", "slug", "persona", "figma_node_id", "project_root", "screens_root"],
      "properties": {
        "screen_number": {"type": "integer", "minimum": 1},
        "slug": {"type": "string", "pattern": "^[a-z0-9-]+$"},
        "persona": {"enum": ["auth", "shared", "operative", "controller", "client", "super-admin", "single"]},
        "figma_node_id": {"type": "string"},
        "figma_file_url": {"type": "string"},
        "project_root": {"type": "string"},
        "screens_root": {"type": "string"},
        "components_root": {"type": "string"},
        "foundations_root": {"type": "string"},
        "journey": {"type": "string"},
        "route": {"type": "string"}
      }
    }
  worker_output_schema: |
    {
      "type": "object",
      "required": ["status", "spec_path", "screen_map_row"],
      "properties": {
        "status": {"enum": ["satisfied", "needs_revision", "max_iterations_reached", "failed", "interrupted"]},
        "spec_path": {"type": "string"},
        "screen_map_row": {
          "type": "object",
          "required": ["route", "persona", "screen_name", "spec_doc", "doc_status", "figma_node_id"],
          "properties": {
            "route": {"type": "string"},
            "persona": {"type": "string"},
            "screen_name": {"type": "string"},
            "spec_doc": {"type": "string"},
            "doc_status": {"enum": ["drafted", "documented", "stub"]},
            "figma_node_id": {"type": "string"},
            "notes": {"type": "string"}
          }
        },
        "new_route": {
          "type": ["object", "null"],
          "properties": {
            "path": {"type": "string"},
            "persona": {"type": "string"},
            "screen": {"type": "string"},
            "notes": {"type": "string"}
          }
        },
        "components_referenced": {"type": "array", "items": {"type": "string"}},
        "components_candidate": {"type": "array", "items": {"type": "string"}},
        "copy_strings": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}}
      }
    }
---
# screen-spec-fleet

Act as a senior/staff design system orchestrator dispatching N screen-spec-author sub-agents (one per screen) and synthesizing their partials into the canonical `SCREEN_MAP.md` index and `routes.md` table.

Goal:
For a batch of N >= 6 Figma frames from one persona+journey scope, dispatch N Sonnet workers in parallel; each worker runs the full 12-step `screen-spec` flow for ONE screen and writes its spec file directly under `docs/app/screens/<persona>/<NN>-<slug>.md`. The orchestrator then merges per-worker SCREEN_MAP rows and any new route declarations into the substrate index files. Expected wall-clock reduction vs sequential `screen-spec`: ~N/3 (Figma MCP calls dominate; partial parallelism in MCP throttling). Expected token reduction: ~2x (workers share no cross-screen context).

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
- project workspace path
- Figma file URL (one per fleet run; all screens MUST belong to the same file)
- screens manifest: array of `{screen_number, slug, persona, figma_node_id, journey?, route?}` per screen (caller pre-enumerates; orchestrator does NOT auto-discover frames)
- persona scope: single persona for the whole fleet (mixing personas in one run is FORBIDDEN -- re-run per persona)
- path to SCREEN_MAP.md (default: `docs/app/SCREEN_MAP.md`; created from `templates/SCREEN_MAP.md` if absent)
- path to routes.md (default: `docs/app/routes.md`)
- optional: explicit max_fanout override (defaults to 20)

Task repository files to update:
- `docs/app/screens/<persona>/<NN>-<slug>.md` (one per worker; each worker is the SOLE writer of its file -- no overlap risk by construction since the orchestrator validates uniqueness of `screen_number+persona+slug` triples pre-dispatch)
- SCREEN_MAP.md (orchestrator is the SOLE writer per `wos/substrate-peers.md`; rows merged from worker partials)
- routes.md (orchestrator is the SOLE writer; rows appended for any `new_route` returned by workers)
- TASK_STATE.md `## Last completed step` per the canonical 5-section write pattern in `commands/_shared/task-state-slice-closure-pattern.md`
- `.wos/fleet-inbox/<run_id>/` directory (gitignored; one partial per worker)
- `.wos/VERIFICATION_LOG.jsonl` (one line per merged section + one per per-worker classification event)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- **Step 1: Validate manifest.** Confirm N >= 6 (else NO_OP_TRACE: route to `screen-spec` sequential). Confirm one persona across all entries (else NO_OP_TRACE: list mixed personas; re-run per persona). Confirm every triple `(screen_number, persona, slug)` is unique (else NO_OP_TRACE: list duplicates). Confirm every `figma_node_id` is non-empty. Confirm N <= `max_fanout` (else NO_OP_TRACE: list overflow; suggest splitting by journey).
- **Step 2: Verify prerequisites.** SCREEN_MAP.md exists (or create from template); routes.md exists (or create with header); foundations dir present per `wos/design-system-conventions.md`; components dir present. If foundations are missing, NO_OP_TRACE: route to `design-bootstrap`.
- **Step 3: Verify Figma MCP availability.** Confirm `get_design_context` and `get_screenshot` tools are reachable; else NO_OP_TRACE: instruct caller to enable Figma MCP.
- **Step 4: Verify tier guard.** Orchestrator runs Sonnet (`claude-sonnet-4-6`); workers run Sonnet (`claude-sonnet-4-6`). Per `wos/sub-agent-orchestration.md ## Tier-mapping per role`: per-target deep analysis (one screen) -- Sonnet (orchestrator pays cost; correctness wins). Tier guard PASS (orch tier >= worker tier; equal is allowed).
- **Step 5: Dispatch workers via the Workflow tool.** For each manifest entry, dispatch a stateless sub-agent through the **Workflow tool** (the canonical parallel-orchestration primitive per ADR-0038). Pass `task_input` matching `worker_input_schema`. Each worker writes its spec file directly to `<screens_root>/<persona>/<NN>-<slug>.md` AND MUST invoke the **StructuredOutput tool exactly once** with `artifact='<worker_id>.partial.json'` and typed `content` matching `worker_output_schema` (per ADR-0038 Rule 1: structured output is mandatory; free-form prose is forbidden). The main loop persists the partial to `active/<task>/.wos/fleet-inbox/<run_id>/<worker_id>.partial.json` as typed JSON, not Markdown, so the apply step consumes typed data rather than re-parsing prose.
- **Step 6: Each worker (instruction template).** Worker executes the standard 12-step `screen-spec` flow (see `commands/screen-spec.md` Operating rules) for ONE screen: `get_design_context` -> `get_screenshot` -> identify components -> layout sketch -> spacing -> data -> copy -> a11y -> interactions -> error states -> related screens -> write file. Worker MUST NOT touch SCREEN_MAP.md or routes.md (substrate-peer rule); instead, return the `screen_map_row` + optional `new_route` via StructuredOutput. Final instruction to every worker: `Return STRUCTURED OUTPUT with artifact='<worker_id>.partial.json' content=<worker_output_schema payload>` where the payload is `{status: "satisfied", spec_path: "<path>", screen_map_row: {...}, new_route: {...} | null, components_referenced: [...], components_candidate: [...], copy_strings: [...], open_questions: [...]}`.
- **Step 7: Wait for convergence.** Barrier pattern: wait for all N workers OR `timeout_ms` (15 min default; Figma MCP latency can be high). Read all `.partial.json` files in `active/<task>/.wos/fleet-inbox/<run_id>/`. Classify per `commands/_shared/convergence-policy.md` failure table. Workers that did not invoke StructuredOutput (schema-skip) are classified `failed` and excluded from merge.
- **Step 8: Merge SCREEN_MAP rows.** Apply `union` merge: collect all `screen_map_row` entries from surviving typed partials. Deduplicate by `(persona, screen_name)` key. If a row already exists in SCREEN_MAP.md with the same key but different `spec_doc` or `figma_node_id`, REFUSE that row and log `event=fleet-merge` with conflict details. Sort merged output by persona ASC, then screen_number ASC. Per ADR-0038 Rule 2 (substrate writes sequenced through deterministic apply step in main loop), this merge runs serially in the orchestrator -- never in a worker.
- **Step 9: Merge routes.** Collect every non-null `new_route` from typed partials. Deduplicate by `path` key. If a route exists in routes.md with a different persona/screen, REFUSE that route and log conflict. Append surviving new routes to routes.md per its table convention.
- **Step 10: Write SCREEN_MAP.md.** Emit transaction header above the rows section; replace the section content per the canonical SCREEN_MAP table shape (Route | Persona | Screen name | Spec doc | Status | Figma frame | Notes). Preserve rows from outside this fleet's persona scope unchanged. Anchor every appended row to an existing parent heading or list per ADR-0038 Rule 3; refuse any row whose anchor is not located.
- **Step 10.5: Scan substrate orphans.** Run `python3 scripts/scan-substrate-orphans.py docs/app/SCREEN_MAP.md docs/app/routes.md` against the just-written files (ADR-0038 Rule 3: the apply step MUST detect and prevent the substrate-bullet-orphan failure mode per `wos/bug-classes/substrate-bullet-orphan.md`). On non-zero exit (one or more orphans detected): REFUSE the merge transaction, log `event=fleet-merge-orphan-refused` with the orphan list to `VERIFICATION_LOG.jsonl`, REVERT both SCREEN_MAP.md and routes.md to their pre-merge state, and surface the orphan list in `### Command transcript`. On exit 0: proceed to Step 11.
- **Step 11: Emit VERIFICATION_LOG.jsonl.** One line per per-worker classification event (`event=merge_include`, `event=worker_failed`, `event=worker_timeout`, `event=schema_skip`, etc.) plus one line for the merged SCREEN_MAP section AND one for routes.md (`event=fleet-merge`, `partials=[worker_id, ...]`, `strategy=union`).
- **Step 12: Update TASK_STATE.md.** Per the canonical 5-section write pattern. Include the fleet summary: total screens specced, persona, new routes appended, components referenced, components candidate (not yet in DS), top open questions.
- Workers NEVER write SCREEN_MAP.md or routes.md. Workers DO write their own spec file directly (no overlap by construction).
- Mixing personas in one fleet run is FORBIDDEN. Re-run per persona to keep merge keys unambiguous.
- Do NOT implement screens here. This command produces spec docs only; implementation flows through normal slice pipeline (`task-init` per screen group -> `implementation-plan` -> `implement-approved-slice`).

Required output:
1. Screen count + persona + journey scope
2. Dispatch summary: N dispatched, M satisfied, K needs_revision, L failed, P interrupted, T timed out, S schema_skip
3. Merge summary: SCREEN_MAP rows merged + dedup count + conflict count; routes appended + conflict count; orphan-scan result (exit code + orphan list if any)
4. Components inventory: unique components referenced across all specs; candidates not yet in DS
5. Copy roll-up: total copy strings ready for i18n (count only; full list lives in spec files)
6. Top 5 open questions across the fleet
7. Path to updated SCREEN_MAP.md and list of new spec files
8. Recommended next command (typically `journey-map` if the fleet covered a complete journey, or `task-init` per screen group for implementation)

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
- Every manifest entry has exactly one spec file written under `docs/app/screens/<persona>/<NN>-<slug>.md`.
- SCREEN_MAP.md has one row per surviving worker output; conflicts REFUSED and logged.
- routes.md has new routes appended (one per `new_route` returned); conflicts REFUSED and logged.
- All 12 sections of the SCREEN_SPEC template are filled per spec file.
- Per-worker partials persisted as typed JSON in `.wos/fleet-inbox/<run_id>/<worker_id>.partial.json` (never `.partial.md`).
- Every worker invoked the StructuredOutput tool exactly once with the declared schema; schema-skip workers logged as `event=schema_skip` and excluded from merge (ADR-0038 Rule 1).
- `scripts/scan-substrate-orphans.py` returned exit 0 against SCREEN_MAP.md and routes.md after the merge (ADR-0038 Rule 3). Non-zero exit triggers REVERT and `event=fleet-merge-orphan-refused`.
- VERIFICATION_LOG.jsonl has one line per classification event + one per merged section + one for the orphan-scan result.
- Worker contract violations (mid-flight writes to SCREEN_MAP / routes) explicitly listed in `### Command transcript`.
- No code implemented by this command; output explicitly says "produces specs + index only; implementation flows through task-init".
- Substrate peer rule respected: SCREEN_MAP.md and routes.md are owned by this command in fleet mode (single-screen `screen-spec` retains co-ownership for sequential runs; mixed-mode is reconciled by `state-reconcile`).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
This is the J.7 PILOT -- the second real orchestrator under ADR-0034, and the maintainer's primary multi-agent scenario (designer hands off a 12-30 screen Figma file; specs land in minutes not hours). A developer reading any merged spec doc plus the components it references must be able to build the screen without opening Figma. Silent dropping is forbidden: every manifest entry either produces a spec file with all 12 sections OR appears explicitly in the failure classification with a reason. The fleet is the eval-baseline for K.7 -- the harness compares wall-clock + tokens + per-spec completeness against `screen-spec` sequential on identical manifests. This command MUST comply with **ADR-0038** (`docs/adr/0038-workflow-tool-as-parallel-orchestration-primitive.md`): Workflow tool as the dispatch primitive (Rule 1: structured output mandatory via StructuredOutput tool), parallel-then-sequential-apply (Rule 2: substrate writes sequenced through the orchestrator main loop), and post-apply orphan scan via `scripts/scan-substrate-orphans.py` (Rule 3: prevent the `wos/bug-classes/substrate-bullet-orphan.md` failure mode that produced 8 orphans in pilot-repo during K.2).

<!-- cache-breakpoint -->
