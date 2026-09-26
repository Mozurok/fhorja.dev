# Eval scenario 30: monitor-fleet-progress.sh helper across a finished and a running fleet

- **Tags**: monitor-fleet-progress, scripts, fleet, multi-agent, observability, timeout-safety
- **Last reviewed**: 2026-09-23
- **Status**: active

## Goal

Validates `scripts/monitor-fleet-progress.sh`, the optional polling helper an operator runs during a fleet dispatch to see per-worker status. It takes two positional arguments, `<run_id> <task_folder>`, and watches `<task_folder>/.wos/fleet-inbox/<run_id>/`, where each worker has its own directory holding a plain-text `status` token (`pending`, `in-progress`, `completed` or `failed`), optional `partial.*` files, and an optional `terminal.json` naming its outcome. The script must refuse a bad invocation, stop on its own once every worker is terminal, keep polling while any worker is not, and end every run with one `dispatch_summary` line that accounts for every worker. Its own wall-clock ceiling is a fixed 15 minutes (per K.8 parallel dispatch learnings, 2026-06-04).

## Setup

A temp task folder with two run inboxes.

Run `done` (every worker terminal):

```text
<task>/.wos/fleet-inbox/done/
  worker-01/
    status          # completed
    partial.md      # a few hundred bytes
  worker-02/
    status          # completed
    terminal.json   # { "outcome": "merge_include" }
  worker-03/
    status          # failed
```

Run `live` (one worker still running):

```text
<task>/.wos/fleet-inbox/live/
  worker-01/
    status          # completed
  worker-02/
    status          # in-progress
```

The script accepts no flags. The poll interval (5 seconds) and the timeout (15 minutes) are constants in the script.

## Input prompt

```text
Run scripts/monitor-fleet-progress.sh in three cases and capture exit code, stdout, stderr and elapsed wall-clock.

Case A (bad invocation):
  scripts/monitor-fleet-progress.sh

Case B (finished fleet):
  scripts/monitor-fleet-progress.sh done <task>

Case C (running fleet), bounded from outside because the script's own ceiling is 15 minutes:
  run scripts/monitor-fleet-progress.sh live <task> in the background and stop it after 12 seconds
```

## Expected response shape

- Case A exits 2 with a `usage:` line naming `<run_id> <task_folder>` on stderr.
- Case B prints one table headed `worker_id`, `status`, `partial-bytes`, `last-updated` with the three workers, stops without waiting, and ends with `dispatch_summary: 3 dispatched / 2 merge_include / 1 worker_failed / 0 worker_timeout / 0 partial_merge / 3 total`, exit 0.
- Case C prints a table on each 5-second poll, with worker-02 shown as `in-progress`, and is still polling when it is stopped at 12 seconds.

## Pass criteria

1. **Bad invocation refused**: Case A exits 2, stderr carries the usage line, and no table is printed.
2. **Finished fleet stops on its own**: Case B exits 0 within 7 seconds, without being stopped from outside.
3. **Table rendered**: Case B stdout carries the `worker_id | status | partial-bytes | last-updated` header and exactly 3 worker rows; worker-01 shows a non-zero `partial-bytes`, the others 0.
4. **Outcome read before status**: worker-02 counts as `merge_include` from its `terminal.json`; worker-01, which has no `terminal.json`, counts as `merge_include` inferred from `completed`; worker-03 counts as `worker_failed` inferred from `failed`.
5. **Summary accounts for every worker**: the Case B `dispatch_summary` line reads exactly as in the expected shape, and `dispatched` equals `total`.
6. **A running worker keeps the poll alive**: Case C prints at least two tables in 12 seconds and has not exited when it is stopped.
7. **Missing inbox waits instead of failing**: pointed at a run id with no inbox directory, the script prints `waiting for inbox dir:` and keeps polling rather than exiting non-zero.

## Failure modes to watch

- **Stops while a worker is still running**: Case C exits before it is stopped, which would make the monitor report a finished fleet that is not finished.
- **Summary drops a worker**: a worker with no `terminal.json` is left out of the counts instead of being inferred from its `status`.
- **Flags documented that the script does not read**: `--inbox`, `--interval` or `--timeout` in a doc or a caller. The script takes positional arguments only; an unknown invocation is a usage error.
- **Timeout mistaken for success**: when the 15-minute ceiling fires the script still exits 0, and the only signal is the `timeout:` line and the non-terminal workers counted as `worker_timeout` in the summary. A caller that reads the exit code alone cannot tell a timeout from a clean finish. That is the current contract, recorded here so a change to it is deliberate.

## Notes

- Related learnings: `learnings_k8_parallel_dispatch.md` (5 reusable lessons from the first lived multi-agent dispatch, 2026-06-04). Lesson 4 (workers fail independently) and lesson 5 (operator needs visibility into stalled workers) motivate this helper.
- No command invokes the script today. `implement-fleet` Step 8 does its own progress reporting by polling the flat `.json` return files ADR-0158 assigns; the script reads a per-worker directory layout and is documented for operators in `docs/MIGRATION.md` and `wos/entry-points.md`.

## History

- 2026-06-05: scenario authored as first coverage for monitor-fleet-progress.sh, grounded in K.8 parallel dispatch learnings.
- 2026-09-23: rewritten against the script as it ships. The first version invoked `--inbox`, `--interval` and `--timeout` flags, read a `status.json` per worker and expected a STALLED state and an exit 2 on timeout, none of which the script has.
