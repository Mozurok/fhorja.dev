Additional bootstrap for orchestrator commands (commands that dispatch sub-agents per ADR-0034 worker contract). Load AFTER the standard `mandatory-context-bootstrap` and BEFORE any worker dispatch.

- Read `wos/sub-agent-orchestration.md` (orchestrator-workers pattern + tier-aware dispatch protocol + per-tool primitives).
- Read `commands/_shared/worker-contract.md` (input/output/status/error/partial shapes; status taxonomy `satisfied | needs_revision | max_iterations_reached | failed | interrupted`).
- Read `wos/substrate-peers.md` (section ownership matrix; the orchestrator-merger is the SOLE writer of substrate based on worker partials).
- Verify the orchestrator command's frontmatter declares:
  - `orchestrator: true`
  - `workers:` map of role -> tier (per `suggested-model` convention)
  - `max_fanout:` integer cap (HARD limit on concurrent workers per run; default 20; absolute ceiling 100)
  - `convergence:` map with `pattern: barrier | streaming`, `timeout_ms: <integer>`, `partial_ok: true | false`
  - `merge_strategy:` one of `union | last-by-timestamp | consensus-of-N | manual-review`
  - `worker_input_schema:` JSON-Schema-like declaration of `task_input` shape per worker role
  - `worker_output_schema:` JSON-Schema-like declaration of expected per-worker deliverables shape
- Orchestrator tier MUST be >= every worker tier per the tier-aware dispatch protocol (`wos/sub-agent-orchestration.md ## Tier-aware dispatch protocol`). Cost guard.
- Workers NEVER write to substrate directly. The orchestrator is the SOLE merger and the SOLE writer of substrate sections based on partials in `active/<task>/.wos/fleet-inbox/<run_id>/`.
- Emit one `VERIFICATION_LOG.jsonl` line per merged section with `event=fleet-merge`, `partials=[worker_id, ...]`, `strategy=<declared>`.
- If max_fanout would be exceeded (e.g., N=25 workers needed but cap is 20), STOP and NO_OP_TRACE with rationale; do not silently truncate the worker set.
- Refuse to dispatch if `worker_input_schema` is missing or vague; route to the orchestrator command author.
