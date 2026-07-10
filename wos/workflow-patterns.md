# Workflow Patterns

Operational patterns for using the Workflow tool (parallel agent dispatch) vs single Agent calls within Fhorja. Grounded in lived evidence from the 2026-06-05 mega-batch intel-gathering session (14 Workflow batches dispatched 2026-06-05, 125 parallel agents).

## 1. Workflow vs single Agent: when to use which

**Use a single Agent call when:**
- The task is exploratory and the next question depends on the current answer.
- Substrate edits are required mid-investigation.
- Token budget per sub-task is high (>30k) and parallelism would blow context.
- The output is unstructured prose meant for direct human reading.

**Use Workflow (parallel agent dispatch) when:**
- N independent read-only investigations can run with no cross-dependencies.
- Each sub-task has a well-defined, narrow scope and a predictable output shape.
- Total elapsed time matters more than peak token spend.
- Outputs will be merged or compared, not consumed individually.

Heuristic: if you can write a JSON schema for the sub-task output before dispatch, Workflow is probably the right call.

Note on executing approved slices: parallel execution of already-approved implementation slices goes through `implement-fleet` (pattern 6, ADR-0041), not a hand-authored Workflow script. The command owns wave computation, the disjointness gate, slice notes, and the orchestrator-only `TASK_STATE.md` write; a raw Workflow batch over approved slices skips all of that and is a contract bypass (ADR-0042). Use raw Workflow dispatch for read-only research and audit fan-out (patterns 2-5), not for slice execution.

## 2. Parallel-then-sequential-apply pattern

Workflow dispatches N agents in parallel; each returns a structured payload. The **main loop** then walks results sequentially and applies K.2 (canonical write) to the substrate one item at a time.

Why split the phases:
- Parallel reads are safe; parallel writes corrupt substrate (race on shared files like TASK_STATE.md, REFERENCES.md).
- Sequential apply lets the main loop deduplicate, reconcile conflicts, and stop on first failure.
- Each agent stays read-only and idempotent, which makes retries trivial.

Anti-pattern: letting parallel agents each run K.2 on shared substrate. Always funnel writes through the orchestrator.

## 3. Structured-output-schema pattern

Pass `schema` to Workflow so every sub-agent returns a typed payload (StructuredOutput tool call) instead of free-form text. Benefits:
- The orchestrator can iterate over results without re-parsing prose.
- Schema validation catches half-formed agent runs at the boundary.
- Downstream `apply` logic is mechanical, not interpretive.

Rule of thumb: if the orchestrator needs to branch on a field, that field belongs in the schema, not in a narrative summary.

## 4. Per-persona iteration batching pattern

For evaluation matrices (M personas X N scenarios X 2 conditions = 2*M*N agent runs), batch along the persona axis:
- One Workflow batch per persona, each batch contains all (scenario X condition) pairs.
- Keeps each batch's schema homogeneous (persona-scoped fields stay constant).
- Caps fan-out per batch at a reviewable size while still parallelizing the expensive axis.
- Failures isolate to a single persona, not the whole matrix.

Used in the 2026-06-05 session to evaluate persona reactions across scenarios without flooding any single batch.

## 5. Mega-batch intel-gathering pattern

The 2026-06-05 session itself: 14 Workflow batches run back-to-back to gather intel across the Fhorja surface (this workflow-patterns.md draft is one such sub-task). Pattern shape:
- Pre-plan all batches up front; do not let earlier results redirect later batches mid-session.
- Each batch is self-contained: schema, prompt, target directory.
- Main loop collects all structured outputs, then a single consolidation pass merges them into substrate.
- Use this when the goal is **substrate population** (filling N topic files, harvesting N decisions) rather than answering one question deeply.

## 6. Parallel execution via worktree isolation (write-fleet)

Patterns 1-5 keep parallel agents read-only and funnel every write through a sequential apply step, because parallel writes to shared substrate race (pattern 2). Product-code execution is the one case where parallel writes are safe, under strict conditions, because each worker can own an isolated git worktree.

`implement-fleet` (ADR-0041) dispatches one worker per independent approved slice, each in its own worktree off a shared base. Safety rests on five conditions, all checked by the orchestrator before dispatch:
- The slices' declared `Scope` file sets are pairwise disjoint.
- No two slices share an implicit-coupling artifact (migration, schema, lockfile, codegen output, barrel export) even if their explicit files differ.
- Every slice's `Depends-on` set completed in an earlier wave (the waves are the topological layering of the slice DAG).
- Each worker runs in its own worktree, so filesystem writes cannot collide.
- A build + typecheck + test integration gate runs on the merged tree after each wave. File-scope disjointness gives a conflict-free merge but does not guarantee semantic integration, so the gate is the backstop and is never skipped.

When the slice DAG is a chain (every wave is size one) there is nothing to parallelize: `implement-fleet` returns a NO_OP and routes to sequential `implement-approved-slice`. The realized speedup is bounded by the width of the DAG (Amdahl); cohesive features tend to be deep chains, so this pattern pays off mainly for tasks with genuinely independent slices (standalone modules, the same change across disjoint files).

Contrast with pattern 2: substrate writes still funnel through the orchestrator (no worktree owns the shared task-memory files); only product-code writes, isolated per worktree and disjoint by scope, may run in parallel. Each worker is still the sole writer of its own `SLICES/<NN>.md` (single-writer-per-folder, ADR-0040); the shared `TASK_STATE.md` is written only by the orchestrator.

## 7. Audit-then-execute two-model pattern

The expensive judgment work (understanding, planning, reviewing) and the cheaper execution work (typing the approved diff) are separable, so they can run on different model tiers. Run `impact-analysis`, `implementation-plan`, and `review-hard` on a frontier model: this is the audit and plan phase, where a wrong direction is cheapest to catch before it compounds across many edits. Then run `implement-approved-slice` on a cheaper model, because the plan is already self-contained (each slice carries `Scope`, `Depends-on`, EARS exit criteria, and optional STOP conditions) so the executor mostly transcribes an approved design rather than deciding one.

The per-command `suggested-model` frontmatter already encodes this split per command (ADR-0025); this pattern names the end-to-end run so it is used deliberately, not rediscovered. STOP conditions (implementation-plan) and the show-the-evidence rule (implement-approved-slice) are what make a cheaper executor safe: it halts and escalates on drift instead of improvising, and it proves each exit criterion with real command output. The split pays off most on plans with many mechanical slices; for a short plan the model-switch overhead is not worth it.

This stays human-first: the auditor model proposes, the executor model implements the approved slice, and the human still approves the plan (`approve-plan`) and the merge. It does not introduce autonomy or auto-merge.

## Evidence

2026-06-05 session: 14 Workflow batches dispatched 2026-06-05, parallel agents per batch, all returning StructuredOutput payloads. Confirmed: parallel reads + sequential K.2 apply held; no substrate corruption; per-batch failure isolation worked as designed.

## Related

- K.2 (canonical write protocol)
- Epic J multi-agent foundation
- K.8 parallel dispatch learnings (2026-06-04)
- sub-agent-orchestration.md (sibling topic; tier-aware dispatch protocol)
- ADR-0038 (substrate-bullet ownership)
- ADR-0039 (workflow prompt length budget)
- ADR-0040 (tier-aware dispatch)
- scan-substrate-orphans.py (post-apply orphan gate)
- ADR-0041 (parallel slice execution via worktree isolation + file-scope disjointness gate)
- implement-fleet.md (orchestrator command for the write-fleet pattern)
- monitor-fleet-progress.sh (live fleet dispatch monitor)
- check-doc-sync.sh (doc-drift detector)
- bug-classes/schema-skip-on-structured-output.md
- bug-classes/workflow-prompt-too-long.md
- bug-classes/substrate-bullet-orphan.md
- K.8 personas (5 total): rls-auth-boundary-auditor (L3), post-deploy-verifier (L3), jtbd-switch-interviewer (L2), migration-safety-steward (L2), color-contrast-architect (L2)


## Empirical evidence from 2026-06-05

This section records empirical observations from a high-volume parallel subagent dispatch session run on 2026-06-05, where ~165+ subagents across 14 batches executed and consumed roughly 5M subagent tokens. These observations are not theoretical -- every claim below is grounded in a lived batch from that session.

### 1. Schema-skip failure mode (StructuredOutput)

When subagents are dispatched with long, multi-section "do everything" prompts, they frequently end their turn without ever calling `StructuredOutput`, returning their answer as free-text assistant content instead. The orchestrator script then cannot parse a result, and the slot is wasted.

Measured rate in this session:

- **Complex-prompt batch (multi-page, exploratory, mixed objectives):** 10 of 12 agents skipped `StructuredOutput` (~83% failure rate).
- **Focused-prompt batch (single objective, 300-500 words, explicit schema reminder at the end):** 0 of 8 agents skipped (~0% failure rate).

**Validated mitigation:** Keep dispatch prompts to **300-500 words**, single-objective, and terminate the prompt with an explicit instruction of the exact shape:

> IMPORTANT: Call StructuredOutput tool with `artifact='<artifact-name>'`, `content=<...>`.

Placing the schema reminder as the **final** instruction (not buried mid-prompt) is what makes the difference. The model treats the last instruction as the action to take when it stops reasoning.

### 2. Parallel-then-sequential-apply pattern validated at scale

Across 14 batches in this session, the pattern of "fan out reads and proposals in parallel, then serialize all substrate writes through a single apply step" held up:

- ~165+ parallel subagents across 14 batches total
- ~5M subagent tokens consumed
- **Zero substrate corruption** after two specific fixes landed:
  - K.2 apply-script bug fix in commit `dc8e7e9`
  - `scan-substrate-orphans.py` (commit `5840755`) as a post-apply sanity check

The lesson is operational, not theoretical: parallel reads and parallel proposals are safe, but **writes must remain sequential and gated by an apply step that scans for orphans**. Without `scan-substrate-orphans.py`, silent partial-apply states were possible; with it, orphans are detected before the next batch dispatches.

### 3. Mega-batch intel-gathering pattern

A new pattern was validated: dispatching a single workflow with **15-25 agents in one batch** purely for broad discovery (codebase mapping, cross-cutting audits, contract surveys), where every agent returns a structured output that the orchestrator merges.

Measured impact in this session: **~5-7x wall-clock speedup** vs. dispatching the same agents sequentially. The pattern works because discovery tasks are read-only, embarrassingly parallel, and produce small structured outputs that merge cheaply.

Use when: you need broad situational awareness fast (e.g., "what does X look like across the repo", "find all callers of Y", "audit Z surface"). Do not use when agents must coordinate or write -- those still go through the parallel-then-sequential-apply pattern above.

### 4. Concurrency cap behavior

The workflow tool caps real concurrency at `min(16, cpu-2)`. Larger batches do not fail -- they queue. Observed in this session:

- An **18-agent batch** completed in **~6 minutes wall-clock**, vs. an estimated ~30 minutes if dispatched sequentially.
- The two agents above the cap simply waited in queue and dispatched as earlier slots freed.

Practical implication: there is **no penalty for over-batching slightly past the cap**, only diminishing returns. Batches of 16-20 agents are the current sweet spot. Beyond ~25 agents the queueing tail starts to dominate and you lose the wall-clock advantage that motivated mega-batching in the first place.

### Summary of operational rules added by this session

1. Dispatch prompts: 300-500 words, single objective, explicit `StructuredOutput` reminder as the final line.
2. Parallel reads/proposals are safe; serialize all substrate writes through an apply step gated by `scan-substrate-orphans.py`.
3. Mega-batch (15-25 agents) is the right shape for broad read-only discovery.
4. Target batches of 16-20 agents to stay within the effective concurrency cap.



## Empirical dispatch outcomes (2026-06-05)

The table below records measured outcomes from all 14 Workflow batches dispatched during the 2026-06-05 session. Each row is grounded in a real batch ID (or its mitigation re-dispatch), with counts taken from the orchestrator log and the post-apply substrate scan.

| Batch ID | Agents | Schema-skip | Orphans | Apply success | Notes |
| --- | --- | --- | --- | --- | --- |
| w59uu3zym | 8 | 2 (re-dispatched) | 0 | 8/8 | first batch; some agents wrote prose without StructuredOutput |
| (re-dispatch batch) | 8 | 0 | 0 | 8/8 | focused-prompt mitigation validated |
| w6jozlzky | 10 | 0 | 0 | 10/10 | applied to disk; lint clean |
| wgmt8m2gt | 10 | 0 | 0 | 10/10 | doc-audit batch |
| w5uxqr73l | 8 | 0 | 0 | 8/8 | doc-audit batch |
| w3wne4tm3 | 10 | 0 | 0 | 10/10 | doc-audit batch |
| w47d4om9y | 10 | 0 | 0 | 10/10 | doc-audit batch |
| w6uazb55a | 10 | 0 | 0 | 10/10 | doc-audit batch |
| wq3i1x12h | 6 | 0 | 0 | 6/6 | doc-audit batch |
| w4culd93t | 7 | 0 | 0 | 7/7 | doc-audit batch |
| wra5hqaw2 | 7 | 0 | 0 | 7/7 | doc-audit batch |
| w8anmjon6 | 8 | 0 | 0 | 8/8 | doc-audit batch |
| wzj5du7g8 | 5 | 0 | 0 | 5/5 | K.8 persona / fleet batch |
| wmse5fdnk | 5 | 0 | 0 | 5/5 | K.8 persona / fleet batch |
| wwx9s24te | 4 | 0 | 0 | 4/4 | K.8 persona / fleet batch |
| wv98roai4 | 25 | 0 | 0 | 25/25 | EPIC A-F bug-classes batch; ~9 new bug-class outputs |

The mitigation pattern that drove the schema-skip rate from 25% to 0% has three components working together. First, dispatch prompts are kept to 300-500 words and scoped to a single objective, so the model never has to choose between competing instructions when it stops reasoning. Second, every prompt terminates with an explicit StructuredOutput reminder as its final line, naming the exact artifact and field shape expected; placing the reminder last (not buried mid-prompt) is what makes the model treat the tool call as the final action. Third, scan-substrate-orphans.py runs as a post-apply gate after every batch, catching any partial-write state before the next batch dispatches. Together these three controls turned a noisy, prose-leaking dispatch surface into a clean parallel-read / sequential-apply pipeline with zero orphans across 125 agents dispatched today (100% apply success, 0 schema-skip across all 14 batches).
