---
name: screen-spec-fleet
description: |-
  Generate one spec document per screen in parallel from Figma frames, dispatching one worker per screen and merging SCREEN_MAP.md and routes.md from their partials. The orchestrator-workers variant of screen-spec. Use when the screen count is 6 or more, a Figma MCP is reachable, and foundations plus SCREEN_MAP already exist. Do not use for a single screen (use screen-spec), when foundations are missing (use design-bootstrap first), or when the frames have not been enumerated yet, since the caller supplies a number, slug, persona and node id per screen.
metadata:
  category: "design-and-ui"
  primary-cursor-mode: "Agent"
  multi-repo-aware: "false"
  context-layers-consumed: "memory, retrieved"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep, Agent"
  x-wos-profiles: "full"
  provenance: "first-party"
  suggested-model: "claude-sonnet-5"
  orchestrator: "true"
  workers: "[{\"role\":\"screen-spec-author\",\"tier\":\"claude-sonnet-5\",\"contract_ref\":\"commands/_shared/worker-contract.md\"}]"
  max_fanout: "16"
  convergence: "{\"pattern\":\"barrier\",\"timeout_ms\":\"900000\",\"partial_ok\":\"true\"}"
  merge_strategy: "union"
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
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file...
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per...
> - `Definition of done (command output)`: Every manifest entry has exactly one spec file written under `docs/app/screens/<persona>/<NN>-<slug>.md`.


Act as a senior/staff design system orchestrator dispatching N screen-spec-author sub-agents (one per screen) and synthesizing their partials into the canonical `SCREEN_MAP.md` index and `routes.md` table.

Goal:
For a batch of N >= 6 Figma frames from one persona+journey scope, dispatch N Sonnet workers in parallel; each worker runs the full 12-step `screen-spec` flow for ONE screen and writes its spec file directly under `docs/app/screens/<persona>/<NN>-<slug>.md`. The orchestrator then merges per-worker SCREEN_MAP rows and any new route declarations into the substrate index files. Expected wall-clock reduction vs sequential `screen-spec`: ~N/3 (Figma MCP calls dominate; partial parallelism in MCP throttling). Expected token reduction: ~2x (workers share no cross-screen context).

Mandatory context bootstrap (before any output):
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 11678 tokens, the four always-read sections combined; the two skipped subsections are 1,035 of those (measured 2026-09-24), so the reduced tier is about 10,643. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 4841 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving `WORKFLOW_OPERATING_SYSTEM.md` and a relative `wos/<topic>.md`.** Both resolve the same way: try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/` or `~/.cursor/workflow-docs/`, the spec at that root and topics under its `wos/`). Repository first, because the installed copy is a snapshot no sync prunes; preferring it would hide a `wos/` edit from every command until a reinstall. Name the resolved root in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently, since several of these loads are MANDATORY.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares the chain ended with no honest next step, defined under `### Official command names (routing integrity)` (ADR-0126); use it only then, never to end a chain that has a real next step.

Required inputs:
- project workspace path
- Figma file URL (one per fleet run; all screens MUST belong to the same file)
- screens manifest: array of `{screen_number, slug, persona, figma_node_id, journey?, route?}` per screen (caller pre-enumerates; orchestrator does NOT auto-discover frames)
- persona scope: single persona for the whole fleet (mixing personas in one run is FORBIDDEN -- re-run per persona)
- path to SCREEN_MAP.md (default: `docs/app/SCREEN_MAP.md`; created from `templates/SCREEN_MAP.md` if absent)
- path to routes.md (default: `docs/app/routes.md`)
- optional: explicit max_fanout override (defaults to 16; absolute ceiling 20)

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
- **Step 4: Verify tier guard.** Orchestrator runs Sonnet (`claude-sonnet-5`); workers run Sonnet (`claude-sonnet-5`). Per `wos/sub-agent-orchestration.md ## Tier-mapping per role`: per-target deep analysis (one screen) -- Sonnet (orchestrator pays cost; correctness wins). Tier guard PASS (orch tier >= worker tier; equal is allowed).
- **Step 5: Dispatch workers.** For each manifest entry, dispatch a stateless sub-agent through the selected carrier's dispatch primitive, naming the agent type explicitly (`agentType: 'general-purpose'` on the workflow path, `subagent_type: general-purpose` on the `Agent` path). Never leave it unset: a fork inherits the whole conversation and drops the input isolation a fresh sub-agent provides. Pass `task_input` matching `worker_input_schema`. Each worker writes its spec file directly to `<screens_root>/<persona>/<NN>-<slug>.md` AND MUST return exactly one typed payload matching `worker_output_schema`, through the selected carrier (ADR-0038 Rule 1 and ADR-0158 D-1). After validating that payload, the orchestrator alone writes its normalized `<task_root>/.wos/fleet-inbox/<run_id>/<worker_id>.partial.json` copy for the existing merge reader. That copy is not a second worker result. Name the path you are on before dispatch (ADR-0158 D-1). Resolve `<task_root>/.wos/fleet-inbox/<run_id>/<worker_id>.json` for each worker and create the run inbox. On the dynamic-workflow path, declare `agent(prompt, {schema})` with `worker_output_schema`; consume the runtime's typed result and persist its JSON copy at that path. Never tell the worker to call StructuredOutput. On the `Agent` path, pass the resolved path as `fleet_inbox_artifact` in the existing worker-contract envelope, outside `task_input`; the worker writes one schema-conforming JSON payload there and the orchestrator reads it. This return-file permission grants no other writes (ADR-0158 D-2). Supply the output schema and selected-carrier instruction outside `task_input`. End the dynamic worker prompt with `Return one payload matching worker_output_schema and nothing else`; end the native worker prompt with `Write one JSON payload matching worker_output_schema to fleet_inbox_artifact and nothing else`.
- **Step 6: Each worker (instruction template).** Worker executes the standard 12-step `screen-spec` flow (see `commands/screen-spec.md` Operating rules) for ONE screen: `get_design_context` -> `get_screenshot` -> identify components -> layout sketch -> spacing -> data -> copy -> a11y -> interactions -> error states -> related screens -> write file. Worker MUST NOT touch SCREEN_MAP.md or routes.md (substrate-peer rule); instead, return the `screen_map_row` + optional `new_route` through the selected carrier. End with the corresponding Step 5 reminder. The payload is `{status: "satisfied", spec_path: "<path>", screen_map_row: {...}, new_route: {...} | null, components_referenced: [...], components_candidate: [...], copy_strings: [...], open_questions: [...]}`.
- **Step 7: Wait for convergence.** Barrier pattern: wait for all N workers OR `timeout_ms` (15 min default; Figma MCP latency can be high). Validate each expected worker's runtime result or assigned native `.json` before creating its parent-owned `.partial.json` copy. Read only those validated copies from `<task_root>/.wos/fleet-inbox/<run_id>/`, once per expected worker. Classify per `commands/_shared/convergence-policy.md` failure table. Workers whose selected carrier supplies no valid payload (schema-skip) are classified `failed` and excluded from merge.
- **Step 8: Merge SCREEN_MAP rows.** Apply `union` merge: collect all `screen_map_row` entries from surviving typed partials. Deduplicate by `(persona, screen_name)` key. If a row already exists in SCREEN_MAP.md with the same key but different `spec_doc` or `figma_node_id`, REFUSE that row and log `event=fleet-merge` with conflict details. Sort merged output by persona ASC, then screen_number ASC. Per ADR-0038 Rule 2 (substrate writes sequenced through deterministic apply step in main loop), this merge runs serially in the orchestrator -- never in a worker.
- **Step 9: Merge routes.** Collect every non-null `new_route` from typed partials. Deduplicate by `path` key. If a route exists in routes.md with a different persona/screen, REFUSE that route and log conflict. Append surviving new routes to routes.md per its table convention.
- **Step 10: Write SCREEN_MAP.md.** Emit transaction header above the rows section; replace the section content per the canonical SCREEN_MAP table shape (Route | Persona | Screen name | Spec doc | Status | Figma frame | Notes). Preserve rows from outside this fleet's persona scope unchanged. Anchor every appended row to an existing parent heading or list per ADR-0038 Rule 3; refuse any row whose anchor is not located.
- **Step 10.5: Scan substrate orphans.** Confirm both resolved SCREEN_MAP and routes targets from Required inputs exist, then run `python3 scripts/scan-substrate-orphans.py <resolved-screen-map-path> <resolved-routes-path>`, with `scripts/scan-substrate-orphans.py` (resolved against the WORKFLOW ROOT, ADR-0218); its exit 2 means a named file was absent, never a pass against those just-written files, quoting each path (ADR-0038 Rule 3: the apply step MUST detect and prevent the substrate-bullet-orphan failure mode per `wos/bug-classes/substrate-bullet-orphan.md`). On a missing target or non-zero exit: REFUSE the merge transaction, log `event=refuse` with `orphan_scan=failed` and the missing paths or orphan list to `VERIFICATION_LOG.jsonl`, restore both resolved targets to their pre-merge state, and surface the exact scanned paths and failure in `### Command transcript`. Proceed to Step 11 only when both files were scanned and the exit was 0; a warning that skipped a missing file is not a clean scan.
- **Step 11: Emit VERIFICATION_LOG.jsonl.** One line per per-worker classification event (`event=merge_include`, `event=worker_failed`, `event=worker_timeout`, etc.; a worker that skipped for a missing Figma frame or schema is `event=worker_missing` with the skip cause in `reason`, NOT a bespoke `schema_skip` event, which is not in the canonical taxonomy) plus one line for the merged SCREEN_MAP section AND one for routes.md (`event=fleet-merge`, `partials=[worker_id, ...]`, `strategy=union`).
- **Step 12: Update TASK_STATE.md.** Per the canonical 5-section write pattern. Include the fleet summary: total screens specced, persona, new routes appended, components referenced, components candidate (not yet in DS), top open questions.
- Workers NEVER write SCREEN_MAP.md or routes.md. Workers DO write their own spec file directly (no overlap by construction).
- Mixing personas in one fleet run is FORBIDDEN. Re-run per persona to keep merge keys unambiguous.
- Do NOT implement screens here. This command produces spec docs only; implementation flows through normal slice pipeline (`task-init` per screen group -> `implementation-plan` -> `implement-approved-slice`).

Required output:
1. Screen count + persona + journey scope
2. Dispatch summary: N dispatched, M satisfied, K needs_revision, L failed, P interrupted, T timed out, S skipped (no frame; logged `worker_missing`)
3. Merge summary: SCREEN_MAP rows merged + dedup count + conflict count; routes appended + conflict count; orphan-scan result (exit code + orphan list if any)
4. Components inventory: unique components referenced across all specs; candidates not yet in DS
5. Copy roll-up: total copy strings ready for i18n (count only; full list lives in spec files)
6. Top 5 open questions across the fleet
7. Path to updated SCREEN_MAP.md and list of new spec files
8. Recommended next command (typically `journey-map` if the fleet covered a complete journey, or `task-init` per screen group for implementation)

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
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state). Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`.

### Definition of done (command output)
- Every manifest entry has exactly one spec file written under `docs/app/screens/<persona>/<NN>-<slug>.md`.
- SCREEN_MAP.md has one row per surviving worker output; conflicts REFUSED and logged.
- routes.md has new routes appended (one per `new_route` returned); conflicts REFUSED and logged.
- All 12 sections of the SCREEN_SPEC template are filled per spec file.
- Per-worker partials persisted as typed JSON in `.wos/fleet-inbox/<run_id>/<worker_id>.partial.json` (never `.partial.md`).
- Every worker supplied one payload conforming to the declared schema through the selected carrier; schema-skip workers (no Figma frame) logged as `event=worker_missing` with the skip cause in `reason` and excluded from merge (ADR-0038 Rule 1).
- `scripts/scan-substrate-orphans.py` returned exit 0 against SCREEN_MAP.md and routes.md after the merge (ADR-0038 Rule 3). Non-zero exit triggers REVERT and `event=refuse` with `orphan_scan=failed`.
- VERIFICATION_LOG.jsonl has one line per classification event + one per merged section + one for the orphan-scan result.
- Worker contract violations (mid-flight writes to SCREEN_MAP / routes) explicitly listed in `### Command transcript`.
- No code implemented by this command; output explicitly says "produces specs + index only; implementation flows through task-init".
- Substrate peer rule respected: SCREEN_MAP.md and routes.md are owned by this command in fleet mode (single-screen `screen-spec` retains co-ownership for sequential runs; mixed-mode is reconciled by `state-reconcile`).
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
This is the J.7 PILOT -- the second real orchestrator under ADR-0034, and the maintainer's primary multi-agent scenario (designer hands off a 12-30 screen Figma file; specs land in minutes not hours). A developer reading any merged spec doc plus the components it references must be able to build the screen without opening Figma. Silent dropping is forbidden: every manifest entry either produces a spec file with all 12 sections OR appears explicitly in the failure classification with a reason. The fleet is the eval-baseline for K.7 -- the harness compares wall-clock + tokens + per-spec completeness against `screen-spec` sequential on identical manifests. This command MUST comply with **ADR-0038** (`docs/adr/0038-workflow-tool-as-parallel-orchestration-primitive.md`): Workflow tool as the dispatch primitive (Rule 1: typed output mandatory through the ADR-0158 carrier), parallel-then-sequential-apply (Rule 2: substrate writes sequenced through the orchestrator main loop), and post-apply orphan scan via `scripts/scan-substrate-orphans.py` (Rule 3: prevent the `wos/bug-classes/substrate-bullet-orphan.md` failure mode that produced 8 orphans in pilot-repo during K.2).
