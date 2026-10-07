---
name: implement-fleet
description: Orchestrator-workers variant of implement-approved-slice that executes independent approved slices in parallel. Reads per-slice Scope and Depends-on from IMPLEMENTATION_PLAN.md, builds the slice DAG, computes parallelizable waves (ready slices whose file scopes are pairwise disjoint with no shared migration, lockfile, codegen, or barrel export), validates disjointness before dispatch, runs one worktree-isolated worker per slice per wave (each executing the implement-approved-slice contract), merges the worktrees, and runs a mandatory build + typecheck + test integration gate after each wave. Use when the active task has an approved multi-slice plan whose Execution waves show at least one wave of size 2 or more. Do not use when the slice DAG is a pure chain (use implement-approved-slice), when slices are unapproved, when Scope/Depends-on are not declared in the plan, or for single-slice tasks.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
  multi-repo-aware: true
  context-layers-consumed: [memory]
  context-layers-produced: [memory]
  tools: [Read, Write, Edit, Bash, Glob, Grep, Agent]
  x-wos-profiles: [minimal, core, full]
  provenance: first-party
  suggested-model: claude-opus-5-5
  orchestrator: true
  workers:
    - role: slice-implementer
      dispatch-role: mechanical
      contract_ref: commands/_shared/worker-contract.md
  max_fanout: 8
  convergence:
    pattern: barrier
    timeout_ms: 900000
    partial_ok: false
  merge_strategy: worktree-apply
  worker_input_schema: |
    {
      "type": "object",
      "required": ["slice_id", "slice_file", "objective", "scope_files", "depends_on", "work_complexity", "product_repo_path", "base_ref"],
      "properties": {
        "slice_id": {"type": "string"},
        "slice_file": {"type": "string"},
        "objective": {"type": "string", "minLength": 10},
        "scope_files": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "depends_on": {"type": "array", "items": {"type": "string"}},
        "work_complexity": {"enum": ["LOW", "MEDIUM", "HIGH"]},
        "product_repo_path": {"type": "string"},
        "base_ref": {"type": "string"},
        "worktree_path": {"type": "string"},
        "exit_criteria": {"type": "array", "items": {"type": "string"}}
      }
    }
  worker_output_schema: |
    {
      "type": "object",
      "required": ["worker_id", "status", "slice_id", "files_touched", "build_status", "test_status"],
      "properties": {
        "status": {"enum": ["satisfied", "needs_revision", "max_iterations_reached", "scope_violation", "failed", "interrupted", "timed_out"]},
        "slice_id": {"type": "string", "minLength": 1, "pattern": "\\S"},
        "files_touched": {"type": "array", "uniqueItems": true, "items": {"type": "string", "minLength": 1, "pattern": "\\S"}},
        "out_of_scope_writes": {"type": "array", "uniqueItems": true, "items": {"type": "string", "minLength": 1, "pattern": "\\S"}},
        "build_status": {"enum": ["pass", "fail", "not_run"]},
        "test_status": {"enum": ["pass", "fail", "not_run", "partial"]},
        "slice_note_path": {"type": "string", "minLength": 1, "pattern": "\\S"},
        "worktree_path": {"type": "string", "minLength": 1, "pattern": "\\S"},
        "commit_sha": {"type": "string", "pattern": "^([0-9a-f]{40}|[0-9a-f]{64})$"},
        "residual_risks": {"type": "array", "uniqueItems": true, "items": {"type": "string", "minLength": 1, "pattern": "\\S"}},
        "diff_summary": {"type": "string", "minLength": 1, "pattern": "\\S"},
        "worker_id": {"type": "string", "minLength": 1, "pattern": "\\S"},
        "error": {"type": "object", "required": ["error_class", "error_message", "error_evidence", "recoverable"], "properties": {"error_class": {"enum": ["tool-failure", "missing-input", "contract-violation", "timeout", "unknown"]}, "error_message": {"type": "string", "minLength": 1, "pattern": "\\S"}, "error_evidence": {"type": "string", "minLength": 1, "pattern": "\\S"}, "recoverable": {"type": "boolean"}}}
      },
      "allOf": [{"if": {"properties": {"status": {"const": "satisfied"}}, "required": ["status"]}, "then": {"required": ["slice_note_path", "worktree_path", "commit_sha"], "not": {"required": ["error"]}, "properties": {"build_status": {"enum": ["pass", "not_run"]}, "test_status": {"enum": ["pass", "not_run"]}, "out_of_scope_writes": {"maxItems": 0}}}}, {"if": {"properties": {"status": {"const": "failed"}}, "required": ["status"]}, "then": {"required": ["error"]}}]
    }
---
# implement-fleet

Act as a senior/staff engineering execution orchestrator running independent approved slices in parallel for the active engineering task.

Goal:
Execute each independent approved slice through `implement-approved-slice` in a harness-isolated worktree. Compute disjoint waves from Scope and Depends-on, validate returns before merging, and pass build, typecheck and tests before advancing. `implement-approved-slice` remains the sequential fallback. Speedup is bounded by DAG width; a chain does not gain parallelism.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers:** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) plus the high-frequency `implement-approved-slice` and `sync-task-state` (v3 wave1 item D) read the four sections above with two subsections of `## Cross-cutting workflow guardrails` skipped: `### External web access (centralized)` and `### Sequencing heuristics (by phase)`. Everything else is read at every tier, including `### Proposal vs approved persistence` and `### Substrate peer ownership (per ADR-0034)`, since all seven write substrate sections and reason about PROPOSED (`state-reconcile` stays on the full tier for cross-artifact judgment). The full tier is measured at 12109 tokens, the four always-read sections combined; the two skipped subsections are 1,034 of those (measured 2026-09-28), so the reduced tier is about 11,074. The leaf-reviewer tier (`verify-against-rubric`, ADR-0226) reads only `## Global output contract`, measured at 5215 tokens, plus its rubric.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this conversation already read the bootstrap sections in an earlier turn still VISIBLE in the context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. Scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), because these sections are one large, static, byte-identical read repeated every turn; every other tool result still re-fetches. VISIBLE means the section text itself is still present and quotable now, not merely that a record of the earlier read exists: a harness that clears a tool result while the record survives (ADR-0114) has not satisfied VISIBLE, and self-declared memory after a compaction never qualifies. A stateless-per-turn harness is excluded. The transcript line is mandatory; a silent skip is invalid output.
- **Resolving the spec and `wos/<topic>.md`:** canonical repository FIRST. Otherwise use active-adapter docs: `~/.claude/workflow-docs` (`CLAUDE_WORKFLOW_DOCS_DIR`), `~/.cursor/workflow-docs` (`WORKFLOW_DOCS_DIR`; project `.cursor/workflow-docs` on project installs), `~/.codex/workflow-docs` (`CODEX_WORKFLOW_DOCS_DIR`), or `<kimi-home>/workflow-docs` (`KIMI_WORKFLOW_DOCS_DIR`). Nonempty overrides win. Kimi home: `KIMI_CODE_HOME`, else existing `~/.kimi-code`, else existing `~/.kimi`, default `~/.kimi-code`. Use one root for both paths; try other adapters if absent or unknown. Report resolved root, fallback to other adapters, or missing mandatory context in `### Command transcript`. Installed snapshots refresh and prune retired topics only on sync.
- Read additional sections only when relevant to this command's role.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** recommendations, including `Run now`, use registered names from `commands/<name>.md` or `commands/<name>/SKILL.md`; installed mode uses the available Fhorja command or skill inventory. No invented aliases. `Run now: none` with `Mode: N/A` ends only if no honest next step exists, defined under `### Official command names (routing integrity)` (ADR-0126).
Required inputs:
- active task folder path
- IMPLEMENTATION_PLAN.md with an approved slice-by-slice plan that declares, per slice: `Scope` (the file paths or globs the slice creates or modifies), `Depends-on` (slice IDs or `none`), and `work complexity`. The `## Execution waves` section is read when present; otherwise the orchestrator computes waves from `Scope` + `Depends-on`.
- TASK_STATE.md (must show the plan as APPROVED; unapproved plans route to `approve-plan` first)
- DECISIONS.md, SOURCE_OF_TRUTH.md
- product workspace path (the repo where slices are implemented) and the initial integration base ref (example: `origin/main` or the current task branch; later waves use the integrated commit from Step 6). For multi-repo tasks, one product repo and base ref per `## Repositories` entry.
- the build, typecheck, and test commands for the product repo (for the integration gate); when absent, the orchestrator infers them from the repo and states what it ran.

Task repository files to update:
- `SLICES/<NN>_<slug>.md` (one per slice; each worker is the SOLE author of its own slice note, per ADR-0040 single-writer-per-folder; it leaves the note in its return folder and the orchestrator copies it here, per ADR-0242)
- `TASK_STATE.md` (orchestrator is the SOLE writer; updated once per wave with wave result and next recommended step, following the canonical <!-- count:closure-pattern-sections -->5<!-- /count -->-section pattern in `commands/_shared/task-state-slice-closure-pattern.md`)
- `.wos/fleet-inbox/<run_id>/` (gitignored; one return per worker, copied in by the orchestrator)
- `.wos/VERIFICATION_LOG.jsonl` (canonical events only, per `scripts/verify-log-validator.py`: one `merge_include` per satisfied worker, one `fleet-merge` per wave whose `reason` records the integration-gate result)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- **ADR-0041 file-scope disjointness gate.** Parallel execution of product-code slices is licensed ONLY when, per wave: (1) the slices' `Scope` file sets are pairwise disjoint; (2) no two slices share an implicit-coupling artifact (database migration or schema, dependency lockfile, codegen output, or barrel/index export) even if their explicit file lists differ; (3) every slice's `Depends-on` set completed in an earlier wave; (4) each worker runs in its own git worktree; (5) a build + typecheck + test integration gate passes on the merged tree after the wave. If any condition fails for a pair of slices, they go to separate waves (serialize).
- **Step 1: Read the plan and slices.** Parse `Scope` and `Depends-on` for every slice from `IMPLEMENTATION_PLAN.md` (and `## Execution waves` when present). If any approved slice is missing `Scope` or `Depends-on`, NO_OP_TRACE and route to `implementation-plan` in its annotate-only retrofit mode to backfill the structured fields without re-planning (do not guess scopes; an under-declared scope defeats the disjointness gate). A re-invoked fleet builds waves only from slices whose plan `Status:` is not closed.
- **Step 2: Build the DAG and compute waves.** Topologically layer slices by `Depends-on`. Within each ready layer, partition slices into a wave only when their `Scope` sets are pairwise disjoint AND they share no coupling artifact (Rule 2); slices that share any file or coupling artifact go to later waves. Emit the resulting wave list: `Wave k: [slice ids]`.
- **Step 3: Disjointness + coupling gate (pre-dispatch).** For each wave, state explicitly: scope-disjointness PASS/FAIL and coupling-artifact PASS/FAIL. A wave dispatches only on PASS. If a slice cannot share a wave with any sibling, it is a wave of one (sequential). **If every wave has size one, the DAG is a chain: NO_OP_TRACE and route to `implement-approved-slice` for the first slice.** Do not pretend to parallelize a chain.
- **Step 4: Verify the orchestrator constraint.** Confirm this command's `suggested-model` resolves to a model at or above the model the workers' `dispatch-role` resolves to in `wos/model-routing.md ## Dispatch roles` (`wos/sub-agent-orchestration.md ## Role-aware dispatch protocol`); refuse to dispatch if it does not. Workers are `mechanical`: each executes an approved slice whose judgment was made and approved upstream. Wave computation and the integration gate run in this command's own session.
- **Step 5: Emit the wave plan.** Show the full wave plan (waves, slice ids per wave, realized parallel width, and the disjointness/coupling PASS lines) before dispatch. The plan is already APPROVED, so the wave plan is a transparency surface, not a second approval gate. Before emitting the plan, run the known-gotchas preflight (the spec guardrail): consult ranked LEARNINGS and user-level memory for the dispatch tool's recorded gotchas and state in the wave plan what was applied, as one line: Gotcha preflight: <N> applied.
- **Step 6: Dispatch the wave with harness isolation (ADR-0242).** Resolve the integration task branch HEAD to an exact committed SHA containing the initial base and all earlier passing waves. Checkpoint required uncommitted changes through `branch-commit --apply`, by explicit task paths, excluding unrelated edits; attended task branches and standing authorization (ADR-0244) authorize that local checkpoint. Otherwise hold the wave and route to `branch-commit`; never dispatch from an older ref. A task-isolated Workspace uses its task branch, not the repository base (ADR-0074 D-3). Record that SHA and pass it as `base_ref`. Dispatch one worker per slice with harness isolation (`isolation` on the `Agent` tool, or `agent(prompt, {isolation: 'worktree'})`); this is a per-agent option, not Workflow input. Do not create slice worktrees by hand. With no per-agent isolation option, run slices sequentially through `implement-approved-slice`. Name `agentType: 'general-purpose'` so each worker has fresh context; a fork would inherit author history. Respect `max_fanout` (8) and ADR-0039 batching. Pass schema-shaped `task_input` with scope, base and exit criteria; the harness supplies the worktree. Name the path you are on before dispatch and create `<task_root>/.wos/fleet-inbox/<run_id>/`. Each return lives in `.fleet-out/` at its own worktree root, outside scope_files, never staged or committed. On the dynamic-workflow path, declare `agent(prompt, {schema})`, consume its typed result and persist one inbox JSON copy; never mandate StructuredOutput or count the copy twice. Agent path: pass `.fleet-out/<worker_id>.json` as `fleet_inbox_artifact` in the worker envelope. Supply output schema and carrier instructions outside `task_input`, granting no other writes. End the dynamic prompt with `Return one payload matching worker_output_schema and nothing else`; end the native prompt with `Write one JSON payload matching worker_output_schema to fleet_inbox_artifact and nothing else`.
- **Step 7: Each worker (instruction template).** Before any read or edit, confirm `git rev-parse --show-toplevel` differs from `product_repo_path`, run `git reset --keep <base_ref>` (no ancestry required; never discard an edit) and verify `git rev-parse HEAD` equals base_ref. On mismatch edit nothing and return failed with nested `error.error_class: missing-input`, error_message, error_evidence and Boolean recoverable. Execute the `implement-approved-slice` contract for ONE approved slice, with explicit-path commits limited to scope_files. Return worker_id, slice_id, worktree_path, commit_sha and slice_note_path; commits after base must form one linear non-merge sequence. files_touched lists every path changed in that sequence, including rename endpoints and reverted paths. The only writes outside scope_files are `.fleet-out/<NN>_<slug>.md` and the assigned native JSON carrier in `.fleet-out/`; never stage or commit the folder, write outside the worktree or write substrate. A required extra path returns scope_violation and out_of_scope_writes. Follow the shared worker-contract stop-loss: path-scoped tests, one final full run, and after 3 attempts or about 15 minutes return needs_revision with failing check, reproduction and hypothesis. Never record provisional or locked decisions; an uncited product decision returns needs_revision and routes the orchestrator to decision-interview. Satisfied cannot report failed or partial checks, an error or out-of-scope writes; not_run remains explicit and never waives Step 10. Return one schema-conforming payload through the declared carrier; free-form prose is forbidden. End with the Step 6 carrier reminder.
- **Step 8: Wait for convergence (barrier), with progress visibility (ADR-0042).** Before waiting, emit a per-wave dispatch line: `Wave k dispatched: N workers [slice ids], expected to run up to 15 min`. During the wait, do NOT go silent: surface interim status as workers transition and on a stall. Poll the host's worker lifecycle status and each worker's `.fleet-out/` return, reporting each worker's last observed state. Learn the worktree paths right after dispatch: run `git worktree list` in the product repo and take the worktrees that were not there before, matched to their worker where the harness names it; a path the dispatch result or the returned `worktree_path` names wins, and an unmatched worker is reported as unknown, never guessed (ADR-0243). `scripts/monitor-fleet-progress.sh <run_id> <task_root> [<worktree>/.fleet-out ...]` is an optional poller for this: it reads flat `<worker_id>.json` returns in the run inbox and in each named return folder, and exits 2 naming what it could not read. Consume one schema-conforming result per expected worker from the selected carrier; a missing or invalid payload cannot satisfy the barrier. Count each worker's runtime result and any replay copy as one result. **Stall rule:** when no worker has transitioned for the stall threshold (default 5 min) and the barrier has not tripped, emit a status summary (running workers, elapsed time, each worker's last observable action) instead of waiting silently for `timeout_ms`. Wait for all workers in the wave OR `timeout_ms` (15 min). `partial_ok` is false: if any worker returns `needs_revision`, `max_iterations_reached`, `scope_violation`, `failed`, `interrupted`, or `timed_out`, do NOT merge the wave. Surface the failing slice(s) and route that slice to sequential `implement-approved-slice`; the wave's other worktrees are held (not merged) until the wave can complete cleanly, to keep the integration gate meaningful. On abort, kill, or timeout, copy every return already in a worker's `.fleet-out/` into `.wos/fleet-inbox/<run_id>/` and record which slices completed before the stop, so the run is resumable and no satisfied work is lost. The monitor is informational; its exit status never authorizes merge.
- **Step 9: Validate, collect and merge (ADR-0242).** Before any merge, run `bash scripts/validate-implement-fleet-result.sh <payload.json> <expected.json>` for EVERY expected worker. Resolve the helper from the workflow root (clone or installed docs); if absent, hold the wave. The orchestrator supplies expected worker_id, slice_id, exact base_ref, product_repo_path, harness-confirmed worktree_path, selected payload_path, assigned slice_note_path and approved scope_files independently of the payload. Scope uses Python fnmatchcase on full POSIX relative paths: `*` includes separators; a literal directory is not recursive. Exit 0 is merge-ready; exit 3 is a valid non-satisfied return that holds the entire wave; exit 2 is invalid or missing input and also holds it. No payload or monitor can bypass this gate. It verifies repository/worktree identity, HEAD, linear commits, actual scoped paths, clean tracked edits and the assigned nonempty note. It rejects committed return files. Immediately before consumption revalidate if inputs changed; copy the verified note only while its hash matches slice_note_sha256. The single task-folder writer copies each selected JSON once to the run inbox and its note to SLICES before removing worktrees. Only after every worker passes, cherry-pick every commit in its validated commit_sequence in order, or apply its scoped diff against base_ref; never cherry-pick only the tip of a multi-commit sequence. Merge slice files and never the return folder. A merged tree carrying `.fleet-out/` fails integration. Record files_touched per slice.
- **Step 10: Integration gate (mandatory).** On the merged tree, run the product repo's build, typecheck, and the affected test subset. Record the exact commands run and their results. **If the gate fails, STOP the fleet:** do not open the next wave, surface the failure (which slice pair most likely introduced the semantic coupling), and route to `implement-approved-slice` or `review-hard` for reconciliation. The gate is never skipped; file-scope disjointness does not guarantee semantic integration.
- **Step 11: Persist and advance.** After a passing gate, the orchestrator updates `TASK_STATE.md` once (sole writer; canonical <!-- count:closure-pattern-sections -->5<!-- /count -->-section pattern) with the wave result, completed slice ids, and the next wave. Each `SLICES/<NN>.md` note was copied in at Step 9 and holds its worker's text alone (single-writer-per-folder). Emit `VERIFICATION_LOG.jsonl` lines using the canonical event taxonomy ONLY (the `EVENTS` set in `scripts/verify-log-validator.py`; there is NO `wave-merge` or `integration-gate` event and inventing one fails the validator): one `event=merge_include` per satisfied worker (`owner_type=command`, `file=IMPLEMENTATION_PLAN.md`, `section='## Slices'`, `partials=["<slice id>"]`, `strategy=union`), then one `event=fleet-merge` per wave (`owner_type=fleet-merger`, `file=IMPLEMENTATION_PLAN.md`, `section='## Execution waves'`, a non-empty `partials` array listing every merged slice id, a `strategy` from the merge-strategy enum, and the integration-gate result folded into the `reason`, e.g. `reason="wave<k>-merged-gate-pass-build-exit0"`); both carry null `sha_before` and `sha_after`, since they record a merge, not a section write, so the Status write below is no sha-chain break. A worker that did not reach `satisfied` is logged with its matching failure event (`worker_failed`, `worker_interrupted`, `worker_timeout`, `retry_needs_revision`, ...) and is not merged. Run `python3 scripts/verify-log-validator.py <task_root>/.wos/VERIFICATION_LOG.jsonl` and fix every invalid line before advancing. Resolve `scripts/verify-log-validator.py` against the WORKFLOW ROOT (the clone, or the installed docs directory, which ships it per ADR-0224); when it is in neither, or exits 2 (`NOT CHECKED`), write `log: not validated (<reason>)` in `### Command transcript` and never report the log as valid. Then close each merged slice before the next wave opens (P-11): for a LOW or MEDIUM slice the orchestrator SHALL write `Status: closed` on it in `IMPLEMENTATION_PLAN.md ## Slices` (a status co-write logged at `## Slices`; workers never write it), and when a merged slice is HIGH, this run ends at a Handoff to `slice-closure` for it, which writes it and hands back to `implement-fleet` for the next wave. Otherwise dispatch the next wave (repeat Steps 6-10) until all waves complete or a gate fails.
- **Multi-repo (per D.4):** when `SOURCE_OF_TRUTH.md` has a `## Repositories` section, run the fleet per repo (one product repo + base ref per entry); waves and the integration gate are per-repo. Do not parallelize slices across repos in one fleet run unless their scopes are disjoint per repo.
- Workers NEVER write `TASK_STATE.md`, the plan `Status:` line (the orchestrator writes it at Step 11), or any sibling slice's note. The orchestrator is the sole writer of `TASK_STATE.md`.
- Do NOT expand any slice's scope, introduce refactors, or implement unapproved work. The fleet executes the approved plan; scope changes route to `implementation-plan` or `post-review-pivot`.
- Each worker honors the YAGNI restraint ladder the plan applied (exist, stdlib, native, installed dep, one line, minimum viable; defined in full in `implementation-plan`), adding no abstraction, config, or dependency its slice does not require.

Required output:
1. Wave plan: the slice DAG summary and the computed waves, with realized parallel width per wave and the scope-disjointness + coupling PASS/FAIL lines.
2. Dispatch summary per wave: committed base SHA shared by every worker, N dispatched, M satisfied, K needs_revision, S scope_violation, L failed, T timed_out.
3. Integration gate result per wave: exact build/typecheck/test commands run and pass/fail.
4. Per-slice: files touched, slice note path, residual risks.
5. Any slice routed to sequential `implement-approved-slice` (with the reason: dependency, scope overlap, worker failure, or gate failure).
6. Recommended next command (typically `slice-closure` per completed slice, `implement-approved-slice` for a held/failed slice, or, when all waves pass, `branch-commit --apply` while the merged work is uncommitted and `pr-package --apply` once it is committed, in an attended chain with a remote; never `pr-package` over uncommitted work, which it refuses; ADR-0233).
7. Recommended editor mode and why this is the correct next step.

### Reference grounding (execution gate)
<!-- shared:reference-grounding -->
**Reference grounding (execution gate).** Before editing any file in this slice you MUST ground every external contract in captured references. This gate is mandatory, not advisory.

1. Detect. Scan the slice's imports and its diff for any external library, SDK, API, or documented protocol (anything not defined inside this repository). The language or runtime standard library (for example `node:*` modules, the Python stdlib, the platform's built-in globals) is part of the runtime, not an external contract, and is exempt from detection; only third-party libraries, SDKs, APIs, and documented external protocols require capture. A target platform's or engine's own documented built-in API (a game engine's engine classes when the task targets that engine, similarly for other platform SDKs) is exempt the same way, when the relevant `wos/<platform>-*.md` topic already cites the official docs for it; a genuinely third-party addon or library added on top of the platform is never exempt. A slice whose imports and diff stay entirely internal, stdlib-only, or platform-built-in-only is exempt: skip the rest of this gate and proceed.

2. Apply the rest (lazy-loaded; `wos/reference-grounding.md`). WHEN step 1 finds an external contract, load `wos/reference-grounding.md` before you edit and apply every rule there exactly as written. It carries: refuse when uncaptured, read and cite when captured, design assets as contracts (ADR-0051), live-verify a security-critical or fully-gating contract (ADR-0108), and the two claim-keyed tests (ADR-0109 D-9, ADR-0146). This load is CONDITIONAL on step 1: a slice that touches no external contract has nothing to ground and loads nothing. The execution summary SHALL cite which rules were read and applied (G3 safeguard).
### Claim grounding (active epistemic humility)
<!-- shared:claim-grounding -->
**Claim grounding (active epistemic humility).** This block governs what you may assert and how you record it. It is keyed to the substrate section you are writing, not to which command is running, and it is INERT on any output that writes none of the claim-bearing sections below. Full contract and rationale: `wos/active-epistemic-humility.md`.

1. When this applies. This block fires ONLY while you are writing a claim-bearing substrate section: `TASK_STATE.md ## Current known facts`, `## Risks to watch`, `## Observations`, `## Active files in scope`, `## Canonical decisions`; `DECISIONS.md ## Locked decisions`; `IMPLEMENTATION_PLAN.md ## Current gaps`, `## Risks and mitigations`; `IMPACT_ANALYSIS.md`; `EXTERNAL_RESEARCH.md`; `REFERENCES.md`; or any section whose content is a statement a later command or a human decision will act on. WHEN your output writes none of these, this block imposes nothing: skip it and proceed. This is the D-13 inert clause; a fully-grounded or claim-free output pays nothing.

2. The unit is the load-bearing claim. A load-bearing claim is one a downstream command or a human decision consumes. A passing aside is not load-bearing; a statement someone will act on is. Apply the rest of this block per load-bearing claim, not per sentence.

3. Ground it or abstain. Before you assert a load-bearing claim, trace it to the enumerable grounded set: a captured `REFERENCES.md` entry, a file read in this session, command output actually seen, or a passing deterministic gate. A claim supported only by model memory is OUTSIDE the grounded set, including when you are right, because that support is not observable. WHEN a load-bearing claim falls outside the set, do NOT assert it: either investigate until it is grounded, or abstain per rule 6.

4. Status records provenance, never confidence. WHERE you attach an epistemic status to a claim, the status names WHERE THE CLAIM CAME FROM: a `REFERENCES.md` entry title, a file path plus line, or the gate output it came from. It SHALL NOT express a degree of certainty. Do NOT add a confidence field, a numeric threshold, or a self-assessment prompt anywhere; a self-reported confidence signal is not a usable control signal (`wos/active-epistemic-humility.md` Part 1.3). A status whose referent slot is empty is read as UNKNOWN, not as a weak yes.

5. Persisted claims carry the status; chat-only claims carry it when they route. Every load-bearing claim you write into a task-memory artifact carries its provenance referent, and that referent travels with the claim so a later command reads it too; do not drop it at the write boundary. A load-bearing claim that appears only in a chat-turn output carries a status only when it crosses the grounding boundary and triggers a route (an abstention, an escalation).

6. Abstain as a routed continuation, never a bare refusal. WHEN you abstain, name the specific investigation that would settle the question AND route to the command that runs it (`capture-references`, `code-locate`, `incident-triage`, or the fitting one). A withholding that stalls the work is invalid output. Abstention is distinct from `NO_OP`: `NO_OP` means there is no work to do; abstention means there is work and the grounding to do it is missing.

7. An unfired gate is not evidence. The absence of a fired check does not mean grounding existed. Do not read silence here as a pass.
### Standard output layout (required)
<!-- shared:standard-output-layout -->
Produce the command output using this structure (English only):

### Artifact changes
<!-- shared:artifact-changes-default -->
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules. Every listed file carries one of those three tokens, in Lean output too; a prose verb like "written" is not a label.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format of `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`. Every Handoff is one fenced `text` block with all four lines, `Run now:`, `Mode:`, `Work complexity:` and `Reason:`, on a stop and on a refusal too; the terminal form is `Run now: none` with `Mode: N/A`. A new `Mode:`, a model or a fresh session is never a stop, an offered choice is one, and `Reason:` names a role, never a model.
### Definition of done (command output)
- Wave computation is shown: the DAG, the waves, and the realized parallel width; if every wave is size one, the run is a NO_OP_TRACE routed to `implement-approved-slice`.
- Scope-disjointness and coupling-artifact checks are stated PASS per dispatched wave (ADR-0041 conditions 1 and 2); no wave dispatches on FAIL.
- Each worker was dispatched with the harness's per-agent isolation (or, with no such option, the slices ran in turn through `implement-approved-slice`), moved its worktree to `base_ref` and showed HEAD equal to it before editing, and stayed confined to its `scope_files` and its `.fleet-out/` return folder; any other `scope_violation` is surfaced and that slice is NOT merged.
- An integration gate (build + typecheck + affected tests) ran on the merged tree after every wave, with the exact commands and results recorded; a failing gate stopped the fleet and was not skipped.
- Progress was visible during each wave per Step 8 (ADR-0042): a dispatch line, interim status, and a status summary on a stall; on abort or timeout the returns were persisted.
- Each worker returned a payload conforming to `worker_output_schema` through the selected carrier; free-form prose returns are flagged as worker-contract violations in `### Command transcript`.
- `TASK_STATE.md`, the fleet inbox and `SLICES/` were written only by the orchestrator; each `SLICES/<NN>.md` holds only its own worker's note, and no merged commit carries `.fleet-out/`.
- VERIFICATION_LOG uses only canonical events (the `EVENTS` set in `scripts/verify-log-validator.py`): a `merge_include` per satisfied worker and a `fleet-merge` per wave whose `reason` records the integration-gate result; no invented `wave-merge` or `integration-gate` event, and the log passes `scripts/verify-log-validator.py`.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
The default path for a parallel wave (ADR-0243), under the ADR-0041 gate. The highest-risk parts are scope under-declaration (a slice touches a file it did not list in `Scope`, defeating the disjointness gate) and the integration gate (where semantic coupling that file-disjointness missed actually surfaces). When in doubt about disjointness, serialize: a wave of one is always safe, and silently parallelizing coupled slices is a worse failure than a slower run. Report realized wave width honestly; never imply a speedup the dependency graph does not allow.
