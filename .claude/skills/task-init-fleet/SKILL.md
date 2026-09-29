---
name: task-init-fleet
description: |-
  Orchestrator-workers variant of task-init for decomposing a complex brief into N parallel independent sub-tasks. Orchestrator validates the decomposition (no overlap, clear scope per sub-task, cross-links justified); N mechanical-role workers each run a full task-init in parallel producing one task folder with 5 mandatory files. Use when the user's brief contains N >= 3 logically independent work streams (e.g., REST->GraphQL migration across api-server + mobile-app + web-app; or implement-X for 4 distinct features that share infra but not delivery). Do not use for one cohesive task (use task-init), for sequential dependencies that can't run in parallel, or when sub-task scopes are still unclear (run decision-interview on the parent first).
metadata:
  category: "state-and-navigation"
  primary-cursor-mode: "Ask"
  multi-repo-aware: "true"
  context-layers-consumed: "memory"
  context-layers-produced: "memory"
  tools: "Read, Write, Edit, Bash, Glob, Grep, Agent"
  x-wos-profiles: "full"
  provenance: "first-party"
  suggested-model: "claude-opus-5-5"
  orchestrator: "true"
  workers: "[{\"role\":\"task-initializer\",\"dispatch-role\":\"mechanical\",\"contract_ref\":\"commands/_shared/worker-contract.md\"}]"
  max_fanout: "10"
  convergence: "{\"pattern\":\"barrier\",\"timeout_ms\":\"600000\",\"partial_ok\":\"true\"}"
  merge_strategy: "union"
  worker_input_schema: |
    {
      "type": "object",
      "required": ["sub_task_slug", "sub_task_objective", "client_project", "project_root", "scope_files", "scope_repos"],
      "properties": {
        "sub_task_slug": {"type": "string", "pattern": "^[a-z0-9-]+$"},
        "sub_task_objective": {"type": "string", "minLength": 10},
        "client_project": {"type": "string", "pattern": "^[a-z0-9-]+__[a-z0-9-]+$"},
        "project_root": {"type": "string"},
        "task_folder_date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
        "scope_files": {"type": "array", "items": {"type": "string"}},
        "scope_repos": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["identifier", "path", "base_branch", "role"],
            "properties": {
              "identifier": {"type": "string", "pattern": "^[a-z0-9-]+$"},
              "path": {"type": "string"},
              "base_branch": {"type": "string"},
              "role": {"enum": ["backend", "frontend", "shared", "infra", "mobile", "other"]}
            }
          }
        },
        "escalations": {"type": "array", "items": {"type": "string"}},
        "cross_links": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "sibling_task": {"type": "string"},
              "relation": {"enum": ["shares-contract", "shares-data-model", "blocks", "blocked-by", "cosmetic-sibling"]}
            }
          }
        }
      }
    }
  worker_output_schema: |
    {
      "type": "object",
      "required": ["status", "task_folder_path", "files_created"],
      "properties": {
        "status": {"enum": ["satisfied", "needs_revision", "max_iterations_reached", "failed", "interrupted"]},
        "task_folder_path": {"type": "string"},
        "files_created": {
          "type": "array",
          "items": {"enum": ["README.md", "TASK_STATE.md", "SOURCE_OF_TRUTH.md", "DECISIONS.md", "IMPLEMENTATION_PLAN.md"]},
          "minItems": 5,
          "maxItems": 5
        },
        "recommended_next_command": {"type": "string"},
        "escalations_emitted": {"type": "array", "items": {"type": "string"}},
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
> - `Handoff`: Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` b...
> - `Definition of done (command output)`: Every sub-task in the decomposition has exactly one task folder under `projects/<client>__<project>/active/` with all 5 mandatory...


Act as a senior/staff engineering workflow orchestrator decomposing a complex multi-stream brief into N parallel independent sub-tasks.

Goal:
For briefs whose scope is N >= 3 logically independent work streams, dispatch N `mechanical` workers in parallel; each worker runs the full `task-init` flow for ONE sub-task and creates one task folder under `projects/<client>__<project>/active/YYYY-MM-DD_<sub-task-slug>/`. The orchestrator validates the decomposition pre-dispatch (scopes are disjoint, dependencies declared as cross_links, no sub-task is trivially mergeable into another) and emits the cross-task index post-merge. Expected wall-clock reduction vs sequential `task-init`: ~N/2 (each task-init touches project-level memory which is shared; some serialization unavoidable). Use case: REST-to-GraphQL migration across 3-5 repos; multi-feature initiatives kicked off in one prompt; coordinated frontend + backend + mobile bootstraps.

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
- the user's full brief (verbatim; the orchestrator decomposes from it)
- client and project identifier (`<client>__<project>`; same for all sub-tasks)
- optional: explicit decomposition (caller may supply the sub-task list directly: `[{slug, objective, scope_files, scope_repos, escalations?, cross_links?}, ...]`; when present, orchestrator skips its own decomposition step and proceeds to validation)
- optional: shared repository list (single repo or multi-repo set; inherited by every sub-task unless overridden per-entry)
- optional: explicit max_fanout override (defaults to 10; absolute ceiling 20 to keep parallel project-memory access manageable)

Task repository files to update:
- `projects/<client>__<project>/active/YYYY-MM-DD_<sub-task-slug>/` (one per worker; each worker is the SOLE writer of its own folder)
- `projects/<client>__<project>/INITIATIVE_INDEX.md` (orchestrator is the SOLE writer; created if absent; one row per sub-task with date, slug, objective one-liner, status=`initialized`, cross-links)
- `.wos/fleet-inbox/<run_id>/` directory (gitignored; one partial per worker)
- `.wos/VERIFICATION_LOG.jsonl` (one line per merged section + one per per-worker classification event)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- **ADR-0038 Rule 2 exception (per-worker direct folder write):** workers write the 5 mandatory files directly into their own task folder rather than returning PROPOSED blocks for a sequential apply step. This is a narrow, documented exception to ADR-0038 Rule 2 (parallel-then-sequential-apply for substrate) justified by the single-writer-per-folder invariant: Step 2 validates scope disjointness across sub-tasks, and each worker is the SOLE writer of its own folder (no two workers can race on the same file). This exception applies ONLY to per-worker task folders. The shared `INITIATIVE_INDEX.md` is the canonical apply target and MUST be written sequentially by the orchestrator in Step 9 (single-writer apply step per ADR-0038 Rule 2). This is not a general escape hatch; any fleet command that cannot prove single-writer-per-folder via pre-dispatch scope validation MUST use the canonical parallel-then-sequential-apply pattern.
- **Step 1: Decompose (or accept decomposition).** If the caller supplied a sub-task list, skip to Step 2. Otherwise: analyze the brief and emit a proposed decomposition. Each sub-task MUST be describable in one sentence, have a distinct slug, have a scope (files OR repos) that does not fully overlap with any other sub-task, and have a stated reason it cannot be folded into a sibling. If N < 3 after decomposition, NO_OP_TRACE: route to `task-init` single-instance.
- **Step 2: Validate decomposition.** Check: (a) all slugs unique; (b) no two sub-tasks share ALL scope files (true overlap, not partial); (c) cross_links between sub-tasks form a DAG (no cycles); (d) escalations (per ADR-0184 and ADR-0207) declared per sub-task or inferable, empty meaning none fired; (e) coverage (per ADR-0056): every concrete work-stream or deliverable named in the brief maps to at least one sub-task. Disjointness (b) catches overlap; coverage (e) catches the opposite failure, omission, where a named work-stream silently maps to no sub-task and drops at decomposition. If any check fails (including a coverage gap), NO_OP_TRACE with the failure list (name each unmapped work-stream); route to `decision-interview` on the parent brief to fold the missing stream in or record an explicit de-scope. Scope-disjointness PASS here is the precondition that licenses the per-worker direct folder write exception above.
- **Step 3: Verify prerequisites.** Confirm `projects/<client>__<project>/` exists (else warn and route to `project-bootstrap`). Confirm `PROJECT_CHARTER.md` present (else warn but proceed; workers will run with explicit placeholders). Confirm no existing task folder at any target path (else NO_OP_TRACE listing collisions; either re-slug or use `resume-from-state`).
- **Step 4: Verify the orchestrator constraint.** Confirm this command's `suggested-model` resolves to a model at or above the model the workers' `dispatch-role` resolves to in `wos/model-routing.md ## Dispatch roles` (`wos/sub-agent-orchestration.md ## Role-aware dispatch protocol`); refuse to dispatch if it does not. Workers are `mechanical`: each initializes one sub-task from the validated decomposition. The decomposition and the cross-link merge run in this command's own session.
- **Step 5: Dispatch workers.** For each sub-task entry, invoke a stateless sub-agent (Claude Code `Agent` tool with `subagent_type: general-purpose`). Pass `task_input` matching `worker_input_schema`. Each worker writes the 5 mandatory files directly into its own folder AND returns a typed payload matching `worker_output_schema` (ADR-0038 Rule 1; free-form prose returns FORBIDDEN). Name the path you are on before dispatch (ADR-0158 D-1). Resolve `<project_root>/active/.wos/fleet-inbox/<run_id>/<worker_id>.json` for each worker and create the run inbox. On the dynamic-workflow path, declare `agent(prompt, {schema})` with `worker_output_schema`; consume the runtime's typed result and persist its JSON copy at that path. Never tell the worker to call StructuredOutput. On the `Agent` path, pass the resolved path as `fleet_inbox_artifact` in the existing worker-contract envelope, outside `task_input`; the worker writes one schema-conforming JSON payload there and the orchestrator reads it. This return-file permission grants no other writes (ADR-0158 D-2). Supply the output schema and selected-carrier instruction outside `task_input`. End the dynamic worker prompt with `Return one payload matching worker_output_schema and nothing else`; end the native worker prompt with `Write one JSON payload matching worker_output_schema to fleet_inbox_artifact and nothing else`.
- **Step 6: Each worker (instruction template).** Worker executes the standard `task-init` flow (see `commands/task-init.md` Operating rules and Files to generate) for ONE sub-task with the given slug and objective. Worker MUST NOT touch INITIATIVE_INDEX.md (substrate-peer rule); the orchestrator owns the cross-task index. Worker emits the per-sub-task `## Recommended pipeline` section in TASK_STATE.md per ADR-0025 complexity-tier rules. Worker MUST supply one payload matching `worker_output_schema` through the selected carrier before exit; end its prompt with the Step 5 carrier-specific reminder. Free-form prose is forbidden (ADR-0038 Rule 1, ADR-0158 D-1). The structured return shape is `{status: "satisfied", task_folder_path: "<path>", files_created: ["README.md", ...], recommended_next_command: "<basename>", escalations_emitted: ["<added command> (<condition that fired>)", ...], open_questions: [...]}`. The assigned `<project_root>/active/.wos/fleet-inbox/<run_id>/<worker_id>.json` is the native carrier; any additional `.partial.json` replay copy is orchestrator-owned and is not a second result.
- **Step 7: Wait for convergence.** Barrier pattern: wait for all N workers OR `timeout_ms` (10 min default). Consume and validate one payload per expected worker from the runtime result or the assigned `<project_root>/active/.wos/fleet-inbox/<run_id>/<worker_id>.json`, according to the selected carrier. Ignore unrelated files and duplicate replay copies. Classify per `commands/_shared/convergence-policy.md`.
- **Step 8: Merge.** Apply `union` merge: collect all surviving `task_folder_path` entries. Build the INITIATIVE_INDEX.md row set: one row per sub-task with `<date> | <slug> | <objective one-liner> | initialized | <cross_links cell> | <recommended_next_command>`. Sort by slug ASC for determinism.
  - **Cross-links cell format (ADR-0125).** The cell SHALL preserve each link's typed `relation` rather than flattening the set into prose, because the type is already computed and DAG-validated at Step 2 and `portfolio-review --initiative` has to read the blocking subset back out. Write one labelled group per relation present, groups separated by `; `, slugs within a group separated by `,` and no space: `blocked-by: <slug>[,<slug>...]; shares-contract: <slug>[,<slug>...]`. Emit `none` when the sub-task has no cross-links. Normalize the `blocks` relation into the blocked-by direction on the row of the sub-task that IS blocked, so a reader never has to invert an edge. The four non-blocking relations (`shares-contract`, `shares-data-model`, `cosmetic-sibling`, and any future informational value) carry their own label and are never read as dependencies. Free prose in this cell is not an error and still parses under the reader's fallback, but a new row SHALL use the labelled form.
- **Step 9: Write INITIATIVE_INDEX.md.** Emit transaction header above `## Initiatives` section; merge new rows with existing rows preserved (initiative index accumulates across runs; the fleet only appends or updates rows for THIS run's slugs). This is the canonical sequential apply step for the shared substrate file per ADR-0038 Rule 2.
- **Step 9.5: Scan substrate orphans (ADR-0038 Rule 3).** Run `python scripts/scan-substrate-orphans.py projects/<client>__<project>/INITIATIVE_INDEX.md`, with `scripts/scan-substrate-orphans.py` (resolved against the WORKFLOW ROOT, ADR-0218); its exit 2 means a named file was absent, never a pass. If the scanner reports any orphan bullets (bullets not anchored under an existing heading or parent list), REVERT the append from Step 9 (restore the pre-append file content) and NO_OP_TRACE listing the offending bullets and the revert in the trace. Do NOT emit a VERIFICATION_LOG event for the failed scan: there is no `orphan_scan_fail` event in the canonical taxonomy and nothing was merged. Cross-reference `wos/bug-classes/substrate-bullet-orphan.md` for the failure class. Do NOT proceed to Step 10 unless orphan-scan PASS.
- **Step 10: Emit VERIFICATION_LOG.jsonl.** One line per per-worker classification event plus one line for the merged INITIATIVE_INDEX section (`event=fleet-merge`, `partials=[worker_id, ...]`, `strategy=union`), with the orphan-scan result folded into that `fleet-merge` line as an additive `orphan_scan=passed` field (the validator tolerates additive fields; there is NO `event=orphan_scan` in the canonical taxonomy, so never emit it as its own line), matching `verify-against-rubric-fleet`.
- **Step 11: Cross-link sweep.** For every `cross_links` entry returned by workers, verify the named sibling task folder exists (post-dispatch). If a referenced sibling is missing (worker_failed or never dispatched), log `event=merge_with_gap` with the dangling link. Do NOT delete or rewrite worker-emitted cross-links; leave the gap visible for `state-reconcile` or a follow-up `resume-from-state` per sibling.
- Workers NEVER write INITIATIVE_INDEX.md. The orchestrator is the SOLE writer of the cross-task index.
- Do NOT implement code, decisions, or plans here. This command initializes task folders only; each sub-task continues via its recommended next command (`implementation-plan` when no escalation fired, otherwise the first command an escalation added, per ADR-0184 and ADR-0207).
- Mixing client_project across sub-tasks in one fleet run is FORBIDDEN. Re-run per client_project to keep INITIATIVE_INDEX writes scoped.

Required output:
1. Decomposition summary: N sub-tasks identified, brief one-liner per sub-task
2. Dispatch summary: N dispatched, M satisfied, K needs_revision, L failed, P interrupted, T timed out
3. Per-sub-task: task folder path, escalations emitted (empty for none, otherwise each added command with the condition that fired it), recommended next command
4. Cross-link graph: ASCII or bullet-list summary of dependencies between sub-tasks
5. INITIATIVE_INDEX.md path and merged row count
6. Top open questions across the fleet (max 5)
7. Recommended next command per sub-task; recommended overall coordination move (typically `where-we-at` on each in sequence, or `decision-interview` if cross-task conflicts surfaced)

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
- Every sub-task in the decomposition has exactly one task folder under `projects/<client>__<project>/active/` with all 5 mandatory files.
- INITIATIVE_INDEX.md has one row per surviving worker output; existing rows from prior runs preserved.
- **Orphan-scan PASS on INITIATIVE_INDEX.md after Step 9** (ADR-0038 Rule 3); if FAIL, the append from Step 9 was reverted and the run NO_OP_TRACEd.
- Cross-link gaps (referenced siblings missing) explicitly logged in VERIFICATION_LOG with `event=merge_with_gap`.
- Per-worker partials persisted in `.wos/fleet-inbox/<run_id>/`.
- Every worker returned a payload conforming to `worker_output_schema` through the selected carrier; free-form prose returns explicitly flagged as worker-contract violations in `### Command transcript`.
- Worker contract violations (mid-flight writes to INITIATIVE_INDEX) explicitly listed in `### Command transcript`.
- No production code or decisions implemented; output explicitly says "initialization only".
- Substrate peer rule respected: INITIATIVE_INDEX.md is owned by this command per the substrate ownership matrix (folded entry added in K.2 retrofit).
- Decomposition validation (uniqueness, scope disjointness, DAG check, escalations, and deliverable coverage per ADR-0056) explicitly stated as PASS before dispatch. A coverage gap (a work-stream named in the brief mapping to no sub-task) is NO_OP_TRACE to decision-interview, never a silent proceed.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
J.8 orchestrator pilot. The decomposition step is the highest-risk part: if the orchestrator silently folds two distinct sub-tasks into one (or splits one cohesive task into two), the downstream cost is creating wrong task folders the user must manually merge. When in doubt, NO_OP_TRACE and route to `decision-interview` for the user to confirm decomposition before dispatch. Silent over-splitting is a worse failure mode than under-splitting; prefer fewer task folders + cleaner scope over more task folders + ambiguous overlap. ADR-0038 binding rules apply: structured output (Rule 1) is enforced in Step 6, per-worker folder writes are the documented Rule 2 exception (single-writer-per-folder, validated in Step 2), the shared INITIATIVE_INDEX.md write is the sequential apply step, and `scripts/scan-substrate-orphans.py` is run in Step 9.5 against INITIATIVE_INDEX.md to prevent the `wos/bug-classes/substrate-bullet-orphan.md` failure class (Rule 3).
