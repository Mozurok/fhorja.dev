Additional bootstrap for orchestrator commands (commands that dispatch sub-agents per ADR-0034 worker contract). Load AFTER the standard `mandatory-context-bootstrap` and BEFORE any worker dispatch.

- Read `wos/sub-agent-orchestration.md` (orchestrator-workers pattern + role-aware dispatch protocol + per-tool primitives).
- Read `commands/_shared/worker-contract.md` (input/output/status/error/partial shapes; status taxonomy `satisfied | needs_revision | max_iterations_reached | failed | interrupted`).
- Read `wos/substrate-peers.md` (section ownership matrix; the orchestrator-merger is the SOLE writer of substrate based on worker partials).
- Verify the orchestrator command's frontmatter declares:
  - `orchestrator: true`
  - `workers:` list, each entry a `role` slug plus a `dispatch-role` of `mechanical` or `judgment` (never a model id; `wos/model-routing.md ## Dispatch roles` resolves it, ADR-0236)
  - `max_fanout:` integer cap (HARD limit on concurrent workers per run; default 12; ceiling 20). The ceiling is the platform's, not a preference: Claude Code documents that "when 20 subagents are running in a session, spawning another with the Agent tool fails with `Concurrent subagent limit reached`, and the error tells Claude not to retry", configurable via `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`. A prior "absolute ceiling 100" here was five times a limit that fails closed with no retry. Note that retries count toward effective fanout, so a run declaring exactly 20 has no headroom for one.
  - `convergence:` map with `pattern: barrier | streaming`, `timeout_ms: <integer>`, `partial_ok: true | false`
  - `merge_strategy:` one of `union | last-by-timestamp | consensus-of-N | manual-review`
  - `worker_input_schema:` JSON-Schema-like declaration of `task_input` shape per worker role
  - `worker_output_schema:` JSON-Schema-like declaration of expected per-worker deliverables shape
- The orchestrator's `suggested-model` MUST resolve to a model at or above the model every worker's `dispatch-role` resolves to (`wos/sub-agent-orchestration.md ## Role-aware dispatch protocol`). Apply each worker's row at dispatch: pass its `model`, and its `effort` where the call takes one; where it does not, write `effort: inherited from session` in the transcript. Cost guard.
- Workers NEVER write to substrate directly. The orchestrator is the SOLE merger and the SOLE writer of substrate sections based on partials in `active/<task>/.wos/fleet-inbox/<run_id>/`.
- Emit one `VERIFICATION_LOG.jsonl` line per merged section with `event=fleet-merge`, `partials=[worker_id, ...]`, `strategy=<declared>`.
- If max_fanout would be exceeded (e.g., N=25 workers needed but cap is 20), split the worker set into sequential sub-batches of at most max_fanout and continue, stating in one line how many batches the overflow produced. Do NOT silently truncate the worker set, and do NOT stop for human input: the cap bounds concurrency, not the work (D-6).
- Refuse to dispatch if `worker_input_schema` is missing or vague; route to the orchestrator command author.
