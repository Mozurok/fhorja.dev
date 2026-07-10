Convergence and failure handling primitive for orchestrator commands per ADR-0034. Declares HOW the orchestrator decides "all workers done, time to merge" and how it handles partial / failed / timed-out / cancelled workers.

Orchestrator commands MUST declare these fields in their frontmatter:

```yaml
metadata:
  convergence:
    pattern: barrier | streaming | quorum-N-of-M
    timeout_ms: <integer>           # per-run total budget
    partial_ok: true | false        # may orchestrator merge with fewer than expected partials?
    quorum:                          # required only when pattern = quorum-N-of-M
      threshold: <integer>           # min workers that must report `status: satisfied` to proceed
      total_expected: <integer>      # M (orchestrator dispatched M; needs threshold satisfied)
  retry:
    needs_revision_max_attempts: 1   # default 1; second `needs_revision` -> `max_iterations_reached`
    failed_recoverable_retries: 0    # default 0; only retry when worker emits `recoverable: true`
    timeout_retries: 0               # default 0; timed-out workers do NOT retry by default
  per_worker_timeout_ms: <integer>   # per-worker cap (separate from run total)
```

## Pattern semantics

### `barrier` (default for fleet commands with bounded N)

Orchestrator dispatches all N workers, waits for ALL to reach a terminal status (`satisfied | needs_revision | max_iterations_reached | failed | interrupted`) OR for `timeout_ms` to elapse, whichever comes first.

- Progress visibility during the wait (per ADR-0042, the spec `## Global output contract` -> `### Long-running execution visibility`): when the wait is expected to exceed about 10 minutes, emit a dispatch line up front (worker count, expected upper-bound duration) and do NOT go silent. Surface interim status as workers transition; when no worker transitions for the stall threshold (default 5 min), emit a status summary (running workers, elapsed, last observable action) instead of waiting silently for `timeout_ms`. On abort or timeout, persist worker partials already in the fleet inbox. This is a reporting duty layered on the barrier; it does not change the `partial_ok` semantics below.
- If timeout elapses first and `partial_ok: false`: orchestrator emits `WORKER_TIMEOUT` summary for non-terminated workers and refuses to merge. Result: `NO_OP_TRACE` with full diagnostic.
- If timeout elapses first and `partial_ok: true`: orchestrator merges what is available, flags the gap explicitly in synthesis, logs `event=partial_merge` in `VERIFICATION_LOG.jsonl`.
- All terminated workers go through Step 6 classification per the orchestrator template.

### `streaming` (for incremental orchestrators)

Orchestrator dispatches workers as work units are enumerated; processes each partial as it arrives; re-merges substrate sections after each `satisfied` partial lands. Useful when workers are slow and intermediate results matter (e.g., research synthesis where early findings inform later searches).

- `timeout_ms` is per-run total.
- `partial_ok` MUST be `true` (streaming inherently produces partial states).
- The final merge after the last worker terminates is treated as a fresh full merge; intermediate state is replaced, not appended.

### `quorum-N-of-M` (for consensus/voting orchestrators)

Orchestrator dispatches M workers; waits for at least N (`quorum.threshold`) to report `status: satisfied`. As soon as N is reached, merge proceeds with those N partials; remaining M-N workers are interrupted (their partials discarded with `event=quorum_discard`).

- Useful for consensus patterns: 3-of-5 verification, majority-vote synthesis.
- N MUST be > M/2 to avoid split votes (rounded up).
- Workers that report `failed` count against the M total but do not contribute to the threshold; if (M - failed) < N, orchestrator refuses to merge with `NO_OP_TRACE: quorum unreachable`.

## Failure classification (per partial)

Per the worker contract status taxonomy:

| Status | Orchestrator action | Logged event |
|---|---|---|
| `satisfied` | Include in merge | `event=merge_include` |
| `needs_revision` (1st time) | Re-dispatch single retry with revised `task_input` | `event=retry_needs_revision` |
| `needs_revision` (2nd time) | Promote to `max_iterations_reached`; include partial in merge with gap flag | `event=max_iterations_promoted` |
| `max_iterations_reached` | Include partial; flag gap in synthesis | `event=merge_with_gap` |
| `failed` + `recoverable: true` | Optional single retry per `retry.failed_recoverable_retries` | `event=retry_failed_recoverable` |
| `failed` + `recoverable: false` | Skip; record in synthesis | `event=worker_failed` |
| `interrupted` | Discard; do not merge | `event=worker_interrupted` |
| Timeout (no terminal status) | If `timeout_retries > 0`: re-dispatch; else skip and flag | `event=worker_timeout` |

## Retry rules (hard limits)

- `needs_revision` retries: 1 (single retry; second occurrence becomes `max_iterations_reached`). Override via `retry.needs_revision_max_attempts` only with rationale in command body.
- `failed + recoverable` retries: 0 by default (no automatic recovery; surfaces upstream). Override only with rationale.
- Timeout retries: 0 by default (silent timeouts often indicate worker contract violation; surfaces upstream). Override only with rationale.
- Total retries across all workers in one run: `max_fanout * 2` ceiling (retries count toward effective fanout for cost-guard purposes).

## Partial-result merge flow

When `partial_ok: true` and orchestrator merges with fewer than M partials:

1. Identify missing workers (no terminal status, no terminated-but-failed status).
2. For each missing worker, log one `event=worker_missing` line with last-known state.
3. Apply declared `merge_strategy` to surviving partials per the worker contract.
4. In synthesis output, explicitly list gaps with format `[GAP: worker <id> did not contribute; reason: <classification>]`.

Silent dropping of missing workers is FORBIDDEN. The gap MUST be explicit.

## Cancellation semantics

- User-initiated cancellation (Esc, `/cancel`): orchestrator marks all in-flight workers as `interrupted`, discards partials, exits with `NO_OP_TRACE: user-cancelled`.
- Orchestrator-initiated cancellation (quorum reached, timeout, fatal error): orchestrator marks remaining workers as `interrupted` with the specific reason.
- Worker self-cancellation: workers SHOULD self-cancel and emit `status: interrupted` when they detect the orchestrator is no longer waiting (e.g., parent process exit). Not enforced; best-effort.

## Idempotency

Re-running the same orchestrator command with the same enumeration source should produce equivalent merged output (subject to worker non-determinism). Orchestrators SHOULD deduplicate by `task_input` hash on retry to avoid double-counting the same worker output.
