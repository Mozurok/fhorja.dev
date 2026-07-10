# Eval scenario 30: monitor-fleet-progress.sh helper across empty and stalled fleets

- **Tags**: monitor-fleet-progress, scripts, fleet, multi-agent, observability, timeout-safety
- **Last reviewed**: 2026-06-05
- **Status**: active

## Goal

Validates `scripts/monitor-fleet-progress.sh`, the polling helper that reports per-worker status for fleet commands (atom-audit-fleet, task-init-fleet, external-research-fleet, verify-against-rubric-fleet, screen-spec-fleet). The script must exit cleanly on empty fleets, render a status table when workers exist, distinguish DONE vs STALLED workers, and never enter an infinite loop -- a 15min hard timeout is the canonical safety net (per K.8 parallel dispatch learnings, 2026-06-04).

## Setup

Two independent fixtures under a temp directory.

Fixture A (empty fleet):

```text
/tmp/fleet-empty/
  (no subfolders, no status.json)
```

Fixture B (mixed fleet with 3 workers):

```text
/tmp/fleet-mixed/
  worker-01/
    status.json   # { "state": "DONE", "updated_at": "2026-06-05T10:02:00Z" }
  worker-02/
    status.json   # { "state": "DONE", "updated_at": "2026-06-05T10:03:00Z" }
  worker-03/
    status.json   # { "state": "RUNNING", "updated_at": "2026-06-05T09:30:00Z" }
                  # stale: > 10min since last update -> STALLED per heuristic
```

The script lives at `scripts/monitor-fleet-progress.sh` and accepts `--inbox=<path> --interval=<dur> --timeout=<dur>`. Default interval is 30s; default timeout is 15min.

## Input prompt

```text
Run scripts/monitor-fleet-progress.sh against two fixtures and capture exit code, stdout, and elapsed wall-clock.

Case A (empty):
  scripts/monitor-fleet-progress.sh --inbox=/tmp/fleet-empty --interval=2s --timeout=10s

Case B (mixed):
  scripts/monitor-fleet-progress.sh --inbox=/tmp/fleet-mixed --interval=2s --timeout=20s
```

## Expected response shape

- Case A exits 0 within 12s wall-clock, prints a single "no workers detected" status line, no table, no infinite loop.
- Case B prints a per-worker table with columns `worker | state | last_update | age`, marks worker-03 as `STALLED` (age > 10min), worker-01 and worker-02 as `DONE`, and exits 0 once all non-stalled workers are DONE (or the 15min timeout fires).
- Stderr is empty on the happy path; warnings (stale status.json, malformed JSON) route to stderr without aborting the poll loop.
- Exit codes: 0 on clean completion (all DONE or empty), 2 on timeout reached with workers still RUNNING, 1 on unrecoverable setup error (inbox path missing).

## Pass criteria

1. **Empty inbox exits cleanly**: Case A exit code is 0, elapsed wall-clock is between 0s and 12s, stdout contains the literal substring `no workers` (case-insensitive), stderr is empty.
2. **No infinite loop on empty**: Case A terminates without requiring SIGINT; the `--timeout=10s` is the hard ceiling and the script must exit at or before it.
3. **Per-worker table rendered**: Case B stdout contains a table header with `worker`, `state`, and `age` columns and exactly 3 data rows (worker-01, worker-02, worker-03).
4. **DONE workers identified**: worker-01 and worker-02 rows show `state=DONE`; their `age` column reflects the difference between now and their `updated_at`.
5. **STALLED detection works**: worker-03 row shows `state=STALLED` (not `RUNNING`), because its `updated_at` is older than the staleness threshold (10min default). The staleness rule fires on `age > threshold AND state != DONE`.
6. **Exit semantics on mixed fleet**: Case B exits 0 if the script treats STALLED as terminal (all 3 workers in a terminal state), OR exits 2 if STALLED is treated as still-running and the `--timeout=20s` fires. Either contract is defensible -- the scenario locks whichever the script implements and the README documents.
7. **No SIGINT required**: both cases terminate on their own; the test harness does not need to kill the process.
8. **Stderr discipline**: malformed or missing status.json for a single worker produces a stderr warning but does NOT abort the poll loop or change the overall exit code (graceful degradation per K.8 learning 4: workers fail independently).

## Failure modes to watch

- **Infinite loop on empty inbox**: script polls forever when no worker subfolders exist; the `--timeout` is the only safety net and a missing or broken timeout check is a P0 bug.
- **STALLED misclassified as RUNNING**: worker-03 stays `RUNNING` because the staleness heuristic compares the wrong timestamp (e.g., file mtime vs `updated_at` field); operator cannot tell a wedged worker from a slow one.
- **Single bad status.json aborts the loop**: one worker with malformed JSON kills the whole monitor instead of producing a stderr warning and continuing -- violates the independent-failure contract.
- **Exit code drift**: script exits 0 on timeout (Case B) instead of 2, hiding the fact that workers were still running when the deadline hit.

## Notes

- Related learnings: `learnings_k8_parallel_dispatch.md` (5 reusable lessons from first lived multi-agent dispatch, 2026-06-04). Lesson 4 (workers fail independently) and lesson 5 (operator needs visibility into stalled workers) directly motivate this scenario.
- Related commands: `atom-audit-fleet`, `task-init-fleet`, `external-research-fleet`, `verify-against-rubric-fleet`, `screen-spec-fleet` -- all consume this helper for progress visibility.
- The 10min staleness threshold and 15min hard timeout are canonical defaults; the script must accept overrides via flags for test ergonomics.

## History

- 2026-06-05: scenario authored as first coverage for monitor-fleet-progress.sh, grounded in K.8 parallel dispatch learnings.
