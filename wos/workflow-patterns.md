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

On the dynamic-workflow path, pass `schema` to `agent(prompt, {schema})` so the runtime supplies the typed result; never ask the worker to call StructuredOutput. On the `Agent` path, assign `fleet_inbox_artifact` to the resolved run-inbox `<worker_id>.json`; the worker writes the typed payload there and the parent validates it (ADR-0158 D-1). Benefits:
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

This stays human-first where a person adds something: the auditor model proposes, the executor model implements the approved slice, and the human still approves the merge. Plan approval self-runs on a blinded review (ADR-0208); the merge does not, because its audience is not bounded. It does not introduce autonomy or auto-merge.

## Fan-out floor

The fan-out floor is 3.

Three is the number of independent items below which dispatching a fleet costs more than it saves. It is derived from what the commands already declare rather than picked: two of the <!-- count:fleet-commands -->7<!-- /count --> fleet commands sit exactly there, and no command sits below it except the one registered below. Per-command thresholds MAY be higher (`verify-against-rubric-fleet` is 4, `atom-audit-fleet` and `screen-spec-fleet` are 6), never lower.

The spec names the same number in `### When to use` and `### When NOT to use`, and `check_fanout_floor_consistency` in `evals/scripts/structural-evals.py` fails the build if those two sentences, this line, and the commands stop agreeing. See [ADR-0173](../docs/adr/0173-one-fan-out-floor.md).

### Registered exceptions

- `implement-fleet`, wave of 2. A worker there carries a whole slice, so dispatch overhead is negligible against the payload. That is the opposite of a fleet whose worker reads one file, which is what the floor is calibrated for. The wave-of-2 trigger is contract, per [ADR-0042](../docs/adr/0042-waves-aware-routing-and-progress-visibility.md).

A number below the floor belongs in this list with its reason, not alone in a command file.

## Evidence

2026-06-05 session: 14 Workflow batches dispatched 2026-06-05, parallel agents per batch, all returning typed payloads (through the `StructuredOutput` call that ADR-0158 later replaced on the `Agent` path). Confirmed: parallel reads + sequential K.2 apply held; no substrate corruption; per-batch failure isolation worked as designed.

## Related

- K.2 (canonical write protocol)
- Epic J multi-agent foundation
- K.8 parallel dispatch learnings (2026-06-04)
- sub-agent-orchestration.md (sibling topic; tier-aware dispatch protocol)
- ADR-0038 (the Workflow tool as the parallel-orchestration primitive; Rule 3 is substrate-bullet ownership)
- ADR-0039 (the empirical batch-dispatch sweet spot)
- ADR-0040 (the single-writer-per-folder exception to ADR-0038)
- tier-aware dispatch (J.3 under ADR-0034; `wos/sub-agent-orchestration.md ## Tier-aware dispatch protocol`)
- scan-substrate-orphans.py (post-apply orphan gate)
- ADR-0041 (parallel slice execution via worktree isolation + file-scope disjointness gate)
- implement-fleet.md (orchestrator command for the write-fleet pattern)
- monitor-fleet-progress.sh (live fleet dispatch monitor)
- check-doc-sync.sh (doc-drift detector)
- bug-classes/schema-skip-on-structured-output.md
- bug-classes/workflow-prompt-too-long.md
- bug-classes/substrate-bullet-orphan.md
- personas and their current levels: the canonical table in `wos/maturity-ladder.md ## Per-persona current-level tracking` (<!-- count:personas-gated -->5<!-- /count --> personas are at L3 and <!-- count:personas-shadow -->4<!-- /count --> at L1)

## Parallel dispatch failures: schema-skip and substrate orphans

Moved here from `docs/FAQ.md` on 2026-09-23: this is operator material for anyone writing or running a fleet dispatch, not a newcomer's question.

### Schema-skip

Schema-skip is when a dispatched subagent finishes its work but returns prose instead of the typed payload, so the orchestrator gets no parseable artifact. The mitigation is the canonical worker contract in `commands/_shared/worker-contract.md` (ADR-0038 Rule 1, carrier decided in ADR-0158 D-1), which requires every dispatched worker to return a payload matching `worker_output_schema` and forbids prose either way; the `templates/ORCHESTRATOR_COMMAND.template.md` reinforces it on the dispatch side.

The failure has two shapes because the carrier depends on the dispatch path, and knowing which one you are on is half the fix. On the dynamic-workflow path the script declares the shape via `agent(prompt, {schema})` and the runtime performs a `StructuredOutput` call, so schema-skip there is the worker answering in prose anyway. On the `Agent`-tool path there is no typed-return primitive at all (`Agent` takes no schema), so the worker writes `fleet-inbox/<run_id>/<worker_id>.json` and schema-skip is a missing or unparseable file. A dispatch prompt that mandates `StructuredOutput` while dispatching through `Agent` is instructing a worker to call a tool it does not have, which reads as a skip and is not one. `## Empirical dispatch evidence (2026-06-05)` below, and ADR-0039, record how prompt shape moved the schema-skip rate in the session that set these numbers. If you write a custom dispatch prompt, copy the explicit typed-return reminder verbatim and name the path it applies to; paraphrasing it has historically degraded compliance.

### Checking a batch for dropped or corrupted substrate writes

ADR-0040 (`docs/adr/0040-single-writer-per-folder-exception.md`) requires every parallel batch to honor single-writer-per-folder discipline; run `python3 scripts/scan-substrate-orphans.py <task-folder>` after the batch settles, or pass the exact files the batch wrote (`python3 scripts/scan-substrate-orphans.py <file-1> <file-2> ...`), which is the form the fleet apply-step gate uses to catch substrate-bullet-orphan instances (`wos/bug-classes/substrate-bullet-orphan.md`). The failure mode it catches is the `substrate-bullet-orphan` bug-class, where two workers race on the same parent and one bullet ends up dangling. If the scan reports any orphans, do not advance phases: re-dispatch the affected workers individually with the orphan IDs passed as input, and re-run the scan until it returns clean.

## Empirical dispatch evidence (2026-06-05)

One session on 2026-06-05 dispatched 14 Workflow batches (125 agents in the batch log, about 165 counting re-dispatches) and set the numbers ADR-0039 ratified. Long multi-objective prompts lost the typed return in 10 of 12 agents; focused prompts of 300 to 500 words with the return instruction as the final line lost it in 0 of 8, and every later batch that day came back clean. Parallel reads with a sequential apply step gated by `scan-substrate-orphans.py` left no substrate orphan. The dynamic-workflow runtime caps real concurrency at `min(16, cpu-2)` and queues the rest, so batches of 16 to 20 agents are the sweet spot and a batch past 25 should be split, because the queueing tail eats the wall-clock gain. That queueing does not transfer to the `Agent`-tool path the fleet commands dispatch on: there the 21st concurrent sub-agent fails with `Concurrent subagent limit reached` and the error instructs no retry. The operational rules that survived the session:

1. Dispatch prompts are 300 to 500 words with a single objective, and the last line is the return instruction of ADR-0158: `Return one payload matching worker_output_schema and nothing else` on the dynamic-workflow path, `Write one JSON payload matching worker_output_schema to fleet_inbox_artifact and nothing else` on the `Agent` path. Never instruct a worker to call `StructuredOutput`.
2. Parallel reads and proposals are safe; serialize all substrate writes through an apply step gated by `scan-substrate-orphans.py`.
3. Mega-batch (15 to 25 agents) is the right shape for broad read-only discovery.
4. Target batches of 16 to 20 agents to stay within the effective concurrency cap.

The per-batch table and the full narrative stay in the repository history at commit `052440cb`; ADR-0039 is the decision they support.
