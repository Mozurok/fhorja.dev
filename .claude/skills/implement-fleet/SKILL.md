---
name: implement-fleet
description: |-
  Orchestrator-workers variant of implement-approved-slice that executes independent approved slices in parallel. Reads per-slice Scope and Depends-on from IMPLEMENTATION_PLAN.md, builds the slice DAG, computes parallelizable waves (ready slices whose file scopes are pairwise disjoint with no shared migration, lockfile, codegen, or barrel export), validates disjointness before dispatch, runs one worktree-isolated worker per slice per wave (each executing the implement-approved-slice contract), merges the worktrees, and runs a mandatory build + typecheck + test integration gate after each wave. Use when the active task has an approved multi-slice plan whose Execution waves show at least one wave of size 2 or more. Do not use when the slice DAG is a pure chain (use implement-approved-slice), when slices are unapproved, when Scope/Depends-on are not declared in the plan, or for single-slice tasks.
metadata:
  category: execution-and-closure
  primary-cursor-mode: Agent
  multi-repo-aware: true
  context-layers-consumed:
    - memory
  context-layers-produced:
    - memory
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Glob
    - Grep
    - Task
  x-wos-profiles:
    - full
  provenance: first-party
  suggested-model: claude-opus-4-7
  orchestrator: true
  workers:
    - role: slice-implementer
      tier: claude-sonnet-4-6
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
      "required": ["slice_id", "slice_file", "objective", "scope_files", "depends_on", "work_complexity", "product_repo_path", "base_ref", "worktree_path"],
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
      "required": ["status", "slice_id", "files_touched", "build_status", "test_status"],
      "properties": {
        "status": {"enum": ["satisfied", "needs_revision", "max_iterations_reached", "scope_violation", "failed", "interrupted", "timed_out"]},
        "slice_id": {"type": "string"},
        "files_touched": {"type": "array", "items": {"type": "string"}},
        "out_of_scope_writes": {"type": "array", "items": {"type": "string"}},
        "build_status": {"enum": ["pass", "fail", "not_run"]},
        "test_status": {"enum": ["pass", "fail", "not_run", "partial"]},
        "slice_note_path": {"type": "string"},
        "residual_risks": {"type": "array", "items": {"type": "string"}},
        "diff_summary": {"type": "string"}
      }
    }
---
> **Output contract, in brief.** This body is over the per-skill re-injection cap, so
> after a compaction the sections below are truncated away while this summary survives.
> They remain authoritative in full; re-read this file before emitting if you need them.
>
> - `Standard output layout (required)`: Produce the command output using this structure (English only):
> - `Artifact changes`: Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.
> - `Command transcript`: Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).
> - `Handoff`: Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per...
> - `Definition of done (command output)`: Wave computation is shown: the DAG, the waves, and the realized parallel width; if every wave is size one, the run is a NO_OP_TRAC...


Act as a senior/staff engineering execution orchestrator running independent approved slices in parallel for the active engineering task.

Goal:
For an approved multi-slice plan whose slice dependency graph is wider than a chain, dispatch one worktree-isolated worker per independent slice, wave by wave, each worker executing the `implement-approved-slice` contract for exactly one slice. The orchestrator computes the waves from `IMPLEMENTATION_PLAN.md` (`Scope` + `Depends-on` per slice), validates file-scope disjointness before dispatch, merges each wave's worktrees, and runs a mandatory build + typecheck + test integration gate before opening the next wave. This is a parallel orchestrator over `implement-approved-slice`, not a replacement for it; `implement-approved-slice` stays the canonical single-slice unit and the fallback. Expected wall-clock reduction is bounded by the width of the DAG: deep chains see little gain (and route back to sequential execution), wide graphs see up to the parallel-branch count.

Mandatory context bootstrap (before any output):
<!-- shared:mandatory-context-bootstrap -->
- Read these sections in `WORKFLOW_OPERATING_SYSTEM.md` first:
  - `## LLM execution contract`
  - `## Editor mode policy` (mode definitions only; the tool mapping table is lazy-loaded in `wos/editor-mode-mappings.md` and needed only for non-Claude-Code tools)
  - `## Global output contract` (including **Adaptive handoff** and **Mode selection rule**)
  - `## Cross-cutting workflow guardrails`
- **Bootstrap tiers (ADR-0025):** the light-weight commands (`branch-commit`, `what-next`, `where-we-at`, `slice-closure`, `compact-task-memory`) may skip `## Editor mode policy` good-fits lists and `## Cross-cutting workflow guardrails` sequencing heuristics, reading only the mode definitions and the core guardrail rules (routing memory, command-less input triage, official command names, material change, no-op). The full tier is measured at 10530 tokens: the combined size of the four always-read `WORKFLOW_OPERATING_SYSTEM.md` sections listed above. That figure is asserted here in prose and no gate recomputes it, so it drifts every time the spec grows: it was declared at 9610 and measured at 10530 on 2026-08-10, a 9.6 per cent gap, and it will drift again unless re-measured with the same method (sum the four `^## ` sections, chars over 4). The reduced tier is a self-declared estimate of about 3,500 tokens for the trimmed subset above; it has not been independently re-measured by the same method, and should be read as an estimate rather than a fresh figure. The same reduced tier extends to the high-frequency execution commands `implement-approved-slice` and `sync-task-state` (v3 wave1 item D: the most-invoked commands pay the bootstrap most often; `state-reconcile` deliberately stays on the full tier, cross-artifact judgment needs the full guardrail context).
- **Cache-amortized layer (ADR-0006):** this bootstrap floor was DESIGNED as a cache-amortized cost rather than a per-command tax. ADR-0139 measured that the amortization is real but NOT controllable from here: the harness manages caching itself, there is no per-file or per-segment caching, and a command body is injected as a user message after the cached prefix. Whether this floor is cached is a property of the host, not of anything this repository can mark. Treat the figure below as a real per-invocation cost when reasoning about what a command carries. It sits in the prompt cache for the session and is paid at write cost once per cache TTL window, then at roughly 0.1x on cached reads inside that window. Account for it separately from any per-skill Load budget (the generated `.claude/skills/<name>/SKILL.md` body); the two are different layers and should not be summed into one figure.
- **Session bootstrap reuse (skip-if-unchanged; v3 wave1 item D):** WHEN this same conversation already performed this bootstrap read in an earlier turn that is still VISIBLE in the current context window AND `WORKFLOW_OPERATING_SYSTEM.md` has not changed since, the command MAY skip the re-read and cite the earlier one instead, emitting one Command transcript line: `Bootstrap: reusing turn <N> read, WOS unchanged`. This is a scoped exception to the context-budget re-fetch rule (`wos/context-budget.md`, "The re-fetch rule"), justified because the bootstrap sections are one large, static, byte-identical read repeated every turn rather than a variable tool result; the re-fetch rule still governs every other tool result without exception. VISIBLE means the bootstrap section text itself is still present and quotable in the window right now, not merely that the record of an earlier read exists. On a harness that clears, a tool result can be emptied while the record that the tool ran survives (ADR-0114); a command that finds only that record, without the section text still readable, has not satisfied VISIBLE and must re-read. Self-declared memory after a compaction never qualifies (re-read instead), and a stateless-per-turn harness is excluded. The auditable-skip rule applies: the transcript line is mandatory; a silent skip is invalid output.
- **Resolving a relative `wos/<topic>.md`.** Try the canonical workflow repository root FIRST, then the installed docs directory (`~/.claude/workflow-docs/wos/` or `~/.cursor/workflow-docs/wos/`). Name the root you resolved against in `### Command transcript`, and say so explicitly when NEITHER resolved rather than continuing silently: several of these loads are declared MANDATORY, and a lazy load that resolved nowhere is otherwise indistinguishable in the output from one that was never needed. Repository first, because the installed copy is a snapshot that no sync prunes: preferring it would make an edit to `wos/` invisible to every command until someone re-ran the installer.
- Read additional sections only when relevant to this command's role.
- Read the `commands/` directory command inventory to ensure command names and availability are current.
- Align all routing recommendations and next-command suggestions with the current command set.
- **Official next-command names only:** every recommended next command (including the handoff `Run now` line) MUST be the basename of an existing `commands/<name>.md` file in this workflow repository. Never invent names. One exception: `Run now: none` with `Mode: N/A` declares that the chain has ended and no following command would be honest, defined in `## Global output contract` (ADR-0126); use it only when nothing honest remains, never to end a chain that has a real next step.

Required inputs:
- active task folder path
- IMPLEMENTATION_PLAN.md with an approved slice-by-slice plan that declares, per slice: `Scope` (the file paths or globs the slice creates or modifies), `Depends-on` (slice IDs or `none`), and `work complexity`. The `## Execution waves` section is read when present; otherwise the orchestrator computes waves from `Scope` + `Depends-on`.
- TASK_STATE.md (must show the plan as APPROVED; unapproved plans route to `approve-plan` first)
- DECISIONS.md, SOURCE_OF_TRUTH.md
- product workspace path (the repo where slices are implemented) and the integration base ref (example: `origin/main` or the current task branch). For multi-repo tasks, one product repo and base ref per `## Repositories` entry.
- the build, typecheck, and test commands for the product repo (for the integration gate); when absent, the orchestrator infers them from the repo and states what it ran.

Task repository files to update:
- `SLICES/<NN>_<slug>.md` (one per slice; each worker is the SOLE writer of its own slice note, per ADR-0040 single-writer-per-folder)
- `TASK_STATE.md` (orchestrator is the SOLE writer; updated once per wave with wave result and next recommended step, following the canonical 5-section pattern in `commands/_shared/task-state-slice-closure-pattern.md`)
- `.wos/fleet-inbox/<run_id>/` (gitignored; one partial per worker)
- `.wos/VERIFICATION_LOG.jsonl` (canonical events only, per `scripts/verify-log-validator.py`: one `merge_include` per satisfied worker, one `fleet-merge` per wave whose `reason` records the integration-gate result)

Operating rules:
- **Handoff:** end with the adaptive `### Handoff` block per `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- **ADR-0041 file-scope disjointness gate.** Parallel execution of product-code slices is licensed ONLY when, per wave: (1) the slices' `Scope` file sets are pairwise disjoint; (2) no two slices share an implicit-coupling artifact (database migration or schema, dependency lockfile, codegen output, or barrel/index export) even if their explicit file lists differ; (3) every slice's `Depends-on` set completed in an earlier wave; (4) each worker runs in its own git worktree; (5) a build + typecheck + test integration gate passes on the merged tree after the wave. If any condition fails for a pair of slices, they go to separate waves (serialize). This generalizes ADR-0040 (single-writer-per-folder) from a folder boundary to a product-code file-set boundary; the worktree merge is conflict-free by construction because scopes are disjoint, and the integration gate is the backstop for semantic coupling that file-scope disjointness cannot catch.
- **Step 1: Read the plan and slices.** Parse `Scope` and `Depends-on` for every slice from `IMPLEMENTATION_PLAN.md` (and `## Execution waves` when present). If any approved slice is missing `Scope` or `Depends-on`, NO_OP_TRACE and route to `implementation-plan` in its annotate-only retrofit mode to backfill the structured fields without re-planning (do not guess scopes; an under-declared scope defeats the disjointness gate). This is the on-ramp for an in-progress plan that predates ADR-0041.
- **Step 2: Build the DAG and compute waves.** Topologically layer slices by `Depends-on`. Within each ready layer, partition slices into a wave only when their `Scope` sets are pairwise disjoint AND they share no coupling artifact (Rule 2); slices that share any file or coupling artifact go to later waves. Emit the resulting wave list: `Wave k: [slice ids]`.
- **Step 3: Disjointness + coupling gate (pre-dispatch).** For each wave, state explicitly: scope-disjointness PASS/FAIL and coupling-artifact PASS/FAIL. A wave dispatches only on PASS. If a slice cannot share a wave with any sibling, it is a wave of one (sequential). **If every wave has size one, the DAG is a chain: NO_OP_TRACE and route to `implement-approved-slice` for the first slice.** Do not pretend to parallelize a chain.
- **Step 4: Tier guard.** Orchestrator runs Opus-class; workers run Sonnet-class (both per the `suggested-model` frontmatter, not pinned in prose). Per `wos/sub-agent-orchestration.md ## Tier-mapping per role`: cross-slice synthesis (wave computation + integration) -> Opus; per-slice execution -> Sonnet. Tier guard PASS (orch tier > worker tier).
- **Step 5: Emit the wave plan.** Show the full wave plan (waves, slice ids per wave, realized parallel width, and the disjointness/coupling PASS lines) before dispatch. The slices are already approved (plan is APPROVED per Step input and ADR-0026), so this run dispatches in Agent mode without a per-slice approval round-trip; the wave plan is the transparency surface, not a second approval gate. Before emitting the plan, run the known-gotchas preflight (the spec guardrail): consult ranked LEARNINGS and user-level memory for the dispatch tool's recorded gotchas and state in the wave plan what was applied, as one line: Gotcha preflight: <N> applied.
- **Step 6: Create worktrees and dispatch the wave.** For each slice in the wave, create an isolated git worktree off `base_ref` and dispatch one worker bound to that worktree (via the Workflow tool's `isolation: 'worktree'` per ADR-0038, or an explicit `git worktree add` per worker). Pass `task_input` matching `worker_input_schema` (including `scope_files`, `worktree_path`, `base_ref`, `exit_criteria`). Respect `max_fanout` (8) and the ADR-0039 batch sweet spot; if a single wave exceeds the fanout, split it into sub-batches. When the active task is worktree-isolated (a `## Workspace` section in `SOURCE_OF_TRUTH.md`, per ADR-0074), set `base_ref` to the task branch, not the repository base, so slice worktrees branch off the task's branch and merge back into it; this keeps the per-task and slice-level worktrees consistent and the integration gate meaningful (ADR-0074 D-3).
- **Step 7: Each worker (instruction template).** Worker executes the `implement-approved-slice` contract (see `commands/implement-approved-slice.md` Operating rules) for ONE slice inside its worktree, confined to `scope_files`. The worker MUST NOT write any file outside `scope_files`; if it must, it stops and returns `status: "scope_violation"` with the offending paths in `out_of_scope_writes` (this means the slice was mis-scoped and the wave plan is wrong). The worker runs the slice's own validation under the **validation budget (stop-loss) and suite-cost-aware validation** rules in `commands/_shared/worker-contract.md`: it iterates with path-scoped runs, runs the full suite once at the end, and when validation debugging exceeds 3 attempts or about 15 minutes it STOPS and returns `status: "needs_revision"` with the failing check, the reproduction command, and a hypothesis rather than grinding silently. The worker writes its `SLICES/<NN>_<slug>.md` note and **MUST invoke the `StructuredOutput` tool exactly once with the `worker_output_schema` payload before exit; free-form prose return is forbidden (ADR-0038 Rule 1).** End the worker prompt with that StructuredOutput reminder (ADR-0039).
- **Step 8: Wait for convergence (barrier), with progress visibility (ADR-0042).** Before waiting, emit a per-wave dispatch line: `Wave k dispatched: N workers [slice ids], expected to run up to 15 min`. During the wait, do NOT go silent: surface interim status as workers transition and on a stall. Run `scripts/monitor-fleet-progress.sh <run_id> <task_folder>` (it polls `.wos/fleet-inbox/<run_id>/` and prints a per-worker status table), or poll the inbox and report. **Stall rule:** when no worker has transitioned for the stall threshold (default 5 min) and the barrier has not tripped, emit a status summary (running workers, elapsed time, each worker's last observable action) instead of waiting silently for `timeout_ms`. Wait for all workers in the wave OR `timeout_ms` (15 min). `partial_ok` is false: if any worker returns `needs_revision`, `scope_violation`, `failed`, `interrupted`, or `timed_out`, do NOT merge the wave. Surface the failing slice(s) and route that slice to sequential `implement-approved-slice`; the wave's other worktrees are held (not merged) until the wave can complete cleanly, to keep the integration gate meaningful. On abort, kill, or timeout, persist every worker partial already in `.wos/fleet-inbox/<run_id>/` and record which slices completed before the stop, so the run is resumable and no satisfied work is lost.
- **Step 9: Merge the wave.** When all workers in the wave are `satisfied`, apply each worktree's diff to the integration branch. Because `Scope` sets are disjoint (Step 3 PASS), the applies do not conflict. Record `files_touched` per slice.
- **Step 10: Integration gate (mandatory).** On the merged tree, run the product repo's build, typecheck, and the affected test subset. Record the exact commands run and their results. **If the gate fails, STOP the fleet:** do not open the next wave, surface the failure (which slice pair most likely introduced the semantic coupling), and route to `implement-approved-slice` or `review-hard` for reconciliation. The gate is never skipped; file-scope disjointness does not guarantee semantic integration.
- **Step 11: Persist and advance.** After a passing gate, the orchestrator updates `TASK_STATE.md` once (sole writer; canonical 5-section pattern) with the wave result, completed slice ids, and the next wave. Workers' `SLICES/<NN>.md` notes are already written (single-writer-per-folder). Emit `VERIFICATION_LOG.jsonl` lines using the canonical event taxonomy ONLY (the `EVENTS` set in `scripts/verify-log-validator.py`; there is NO `wave-merge` or `integration-gate` event and inventing one fails the validator): one `event=merge_include` per satisfied worker (`owner_type=command`, `partials=["<slice id>"]`, `strategy=union`), then one `event=fleet-merge` per wave (`owner_type=fleet-merger`, a non-empty `partials` array listing every merged slice id, a `strategy` from the merge-strategy enum, and the integration-gate result folded into the `reason`, e.g. `reason="wave<k>-merged-gate-pass-build-exit0"`). A worker that did not reach `satisfied` is logged with its matching failure event (`worker_failed`, `worker_interrupted`, `worker_timeout`, `retry_needs_revision`, ...) and is not merged. Run `python3 scripts/verify-log-validator.py <task_root>/.wos/VERIFICATION_LOG.jsonl` and fix every invalid line before advancing. Then dispatch the next wave (repeat Steps 6-10) until all waves complete or a gate fails.
- **Multi-repo (per D.4):** when `SOURCE_OF_TRUTH.md` has a `## Repositories` section, run the fleet per repo (one product repo + base ref per entry); waves and the integration gate are per-repo. Do not parallelize slices across repos in one fleet run unless their scopes are disjoint per repo.
- Workers NEVER write `TASK_STATE.md` or any sibling slice's note. The orchestrator is the sole writer of `TASK_STATE.md`.
- Do NOT expand any slice's scope, introduce refactors, or implement unapproved work. The fleet executes the approved plan; scope changes route to `implementation-plan` or `post-review-pivot`.
- Each worker honors the YAGNI restraint ladder the plan applied (exist, stdlib, native, installed dep, one line, minimum viable; defined in full in `implementation-plan`), adding no abstraction, config, or dependency its slice does not require.

Required output:
1. Wave plan: the slice DAG summary and the computed waves, with realized parallel width per wave and the scope-disjointness + coupling PASS/FAIL lines.
2. Dispatch summary per wave: N dispatched, M satisfied, K needs_revision, S scope_violation, L failed, T timed_out.
3. Integration gate result per wave: exact build/typecheck/test commands run and pass/fail.
4. Per-slice: files touched, slice note path, residual risks.
5. Any slice routed to sequential `implement-approved-slice` (with the reason: dependency, scope overlap, worker failure, or gate failure).
6. Recommended next command (typically `slice-closure` per completed slice, `pr-package` when all waves pass, or `implement-approved-slice` for a held/failed slice).
7. Recommended editor mode and why this is the correct next step.

### Reference grounding (execution gate)
<!-- shared:reference-grounding -->
**Reference grounding (execution gate).** Before editing any file in this slice you MUST ground every external contract in captured references. This gate is mandatory, not advisory.

1. Detect. Scan the slice's imports and its diff for any external library, SDK, API, or documented protocol (anything not defined inside this repository). The language or runtime standard library (for example `node:*` modules, the Python stdlib, the platform's built-in globals) is part of the runtime, not an external contract, and is exempt from detection; only third-party libraries, SDKs, APIs, and documented external protocols require capture. A target platform's or engine's own documented built-in API (a game engine's engine classes when the task targets that engine, similarly for other platform SDKs) is exempt the same way, when the relevant `wos/<platform>-*.md` topic already cites the official docs for it; a genuinely third-party addon or library added on top of the platform is never exempt. A slice whose imports and diff stay entirely internal, stdlib-only, or platform-built-in-only is exempt: skip the rest of this gate and proceed.

2. Refuse when uncaptured. IF the slice uses an external contract that is not present in `projects/<client>__<project>/REFERENCES.md`, you MUST NOT edit. Stop, name the missing contract in one short refusal block, and route the user to `capture-references` to capture it (official docs, signature, version). This holds in every task tier. Do not fetch the web here; `capture-references` is the only authorized capture path.

3. Read and cite when captured. WHEN the contract is present in `REFERENCES.md`, read that entry (including any `Implementation contract` block) before you write code, and emit a `Grounded in:` line in the execution summary naming each `REFERENCES.md` entry or local doc you relied on. An edit that touches an external contract without a `Grounded in:` line is invalid output. This cite requirement is NOT conditional on capture: WHEN the thing you relied on is the dependency's own published source rather than a captured entry or a doc (the tier rule 6 admits), the `Grounded in:` line SHALL name the file path, the line range, and the version you read, whether or not that library also has a `REFERENCES.md` entry. Rule 6's case reaches here even when rule 1 stayed silent and the contract was never captured. A bare claim of having read the source is not a cite: every other tier produces a referent a reviewer can open, and this one is held to the same bar (ADR-0121, ADR-0109).

4. Design assets are external contracts too (ADR-0051). WHEN this slice implements from a design source (Figma node, screen, or component spec), pull the exact node via the design MCP (`get_design_context` / `get_screenshot` / `get_variable_defs`, `download_assets` for real assets) BEFORE editing and build from the pulled values: no placeholder boxes, guessed measurements, or assumed copy. Design-to-code slices are NOT exempt when imports are internal. IF the node is unavailable, stop and ask for the link. Placeholders need an approved `Asset-fidelity: placeholder` decision in `IMPLEMENTATION_PLAN.md`.

Do not implement an external API from memory. WHEN the captured entry and your recollection disagree, the captured entry wins (per `WORKFLOW_OPERATING_SYSTEM.md` `## Evidence priority`).

5. Live-verify a security-critical or fully-gating contract before it satisfies this gate (ADR-0108). A captured `REFERENCES.md` entry does NOT satisfy this gate on its own when BOTH of the following hold: (a) the contract governs a security-critical or fully-gating path (authentication, authorization, payment, PII handling, or any point where a wrong assumption blocks 100% of a code path rather than an edge case), AND (b) the only evidence for the exact point in question is a vendor's demo/example/sandbox payload (not a live capture of the real production delivery mechanism) OR the captured entry itself marks the point `[unclear in source]` or otherwise documents it as unconfirmed. WHEN both hold, you MUST NOT implement against the assumed shape until either a live capture (a real request/response from the actual mechanism, e.g. via a webhook capture endpoint, a sandbox call with real credentials, or a vendor support confirmation) replaces the inference, OR the assumption and its accepted risk are recorded as an explicit, named entry via `decision-interview` rather than silently built into the code. This closes the gap the 2026-07-15 tms-webhook-integration dogfood exposed: a captured reference existed and was cited, but it was evidenced only by the vendor's demo payload, and the auth-format point was already marked unconfirmed in the same reference set, yet implementation proceeded and shipped a code path that could never authenticate a real request.

6. Claim-keyed boundary test, additive to the import scan (ADR-0109, D-9). The scan in rule 1 fires on the slice's import-and-diff surface. A SECOND test fires on a load-bearing claim regardless of whether the import surface changed: WHEN you are about to assert behavior of an external library, SDK, API, or documented protocol as a basis for the edit (which version returns what, which default changed, which parameter is required), that claim MUST trace to the grounded set (a captured `REFERENCES.md` entry, a doc read this session, the dependency's own published source read this session, or a live capture per rule 5), or you MUST NOT rely on it. The published-source tier (ADR-0121) exists for the case the other tiers cannot reach: a point the vendor's documentation simply does not state, which a captured entry records as `[unclear in source]` and which does not warrant rule 5's live capture. It is ADDITIVE and never an escape hatch: rule 2 is unchanged, so an external contract absent from `REFERENCES.md` still stops the edit and still routes to `capture-references`, and reading source is not a substitute for capturing it. Cite it per rule 3. The two tests are complementary and neither replaces the other. The case each catches: rule 1 catches a NEW external contract entering via a changed import; this rule catches a fix INSIDE a library the repository already imports, where the import surface is unchanged (rule 1 stays silent) but the claim about that library's runtime behavior is outside the grounded set. For a bug fix in an already-imported library, rule 1 does not fire and this rule does. The full doctrine is `wos/active-epistemic-humility.md` and the universal block `commands/_shared/claim-grounding.md`; this rule is its execution-time face inside the grounding gate.

7. Internal claim-keyed test (ADR-0146). Rule 1's exemption for an internal-only slice exempts it from CAPTURE, not from GROUNDING. WHEN you are about to assert behavior of an in-repo module as a basis for the edit (what a helper already does on failure, which statuses a route can raise, whether any caller can reach the expression you are adding, what a cache actually holds), that claim MUST trace to a `file:line` range you read this session, and the execution summary SHALL name it. Two clauses decide the cases a plain read-it-first rule misses. (a) A partial read does not ground a claim about a complete surface: WHEN the claim quantifies over ALL of something (every error this route raises, every caller of this symbol, every path that reaches this branch), the cite SHALL be an enumeration over the whole file (a grep for every `throw`, for every call site), never a line-window read. (b) Mirroring an in-repo precedent does not ground the claim: the precedent grounds what THAT file does, not that it is correct at THIS call site, so a mirrored error path still requires the callee's own failure handling to be enumerated and cited. A claim you cannot cite this way is not a basis for the edit; record it as an assumption in the slice note and do NOT encode it in a branch. This rule adds no scan and no capture step, and it fires only when you are about to rely on an in-repo behavior claim, so a slice that asserts none pays nothing. The failure it closes: a screen handler called a pipeline internal directly and duplicated the logging and the toast the callee already owned, in a session where the search returning the canonical path had already run and the callee's own handling had already been on screen, because both claims rested on a mirrored precedent plus two line-window reads that skipped the range where the existing behavior lived.

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
Follow `## Global output contract` in `WORKFLOW_OPERATING_SYSTEM.md` for `APPLIED` / `PROPOSED` / `SKIP` rules.

### Command transcript
<!-- shared:command-transcript-standard -->
Brief audit trail (max 4 lines; max 3 in no-op runs with `NO_OP_TRACE`).

### Handoff
<!-- shared:handoff-body -->
Use the adaptive ending format from `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract` (Mode A compact or Mode B full per session state).

### Definition of done (command output)
- Wave computation is shown: the DAG, the waves, and the realized parallel width; if every wave is size one, the run is a NO_OP_TRACE routed to `implement-approved-slice`.
- Scope-disjointness and coupling-artifact checks are stated PASS per dispatched wave (ADR-0041 conditions 1 and 2); no wave dispatches on FAIL.
- Each worker ran in its own worktree confined to its `scope_files`; any `scope_violation` is surfaced and that slice is NOT merged.
- An integration gate (build + typecheck + affected tests) ran on the merged tree after every wave, with the exact commands and results recorded; a failing gate stopped the fleet and was not skipped.
- Progress was visible during each wave (ADR-0042): a per-wave dispatch line was emitted, interim status surfaced on worker transitions, and a stalled wave produced a status summary rather than silence until timeout; on abort or timeout, worker partials were persisted.
- Each worker returned a `StructuredOutput` payload conforming to `worker_output_schema`; free-form prose returns are flagged as worker-contract violations in `### Command transcript`.
- `TASK_STATE.md` was written only by the orchestrator; each `SLICES/<NN>.md` was written only by its own worker.
- VERIFICATION_LOG uses only canonical events (the `EVENTS` set in `scripts/verify-log-validator.py`): a `merge_include` per satisfied worker and a `fleet-merge` per wave whose `reason` records the integration-gate result; no invented `wave-merge` or `integration-gate` event, and the log passes `scripts/verify-log-validator.py`.
- Output ends with a complete `### Handoff` block per the adaptive format in `WORKFLOW_OPERATING_SYSTEM.md` `## Global output contract`.
- Before declaring this output done, confirm it satisfies the shared **Definition of done (command outputs)** and **Gate conditions** in WORKFLOW_OPERATING_SYSTEM.md.

Quality bar:
Pilot per ADR-0041. The highest-risk parts are scope under-declaration (a slice touches a file it did not list in `Scope`, defeating the disjointness gate) and the integration gate (where semantic coupling that file-disjointness missed actually surfaces). When in doubt about disjointness, serialize: a wave of one is always safe, and silently parallelizing coupled slices is a worse failure than a slower run. Report realized wave width honestly; never imply a speedup the dependency graph does not allow.
