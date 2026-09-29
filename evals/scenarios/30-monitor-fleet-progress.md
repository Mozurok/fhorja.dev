# Eval scenario 30: monitor-fleet-progress.sh helper across a finished and a running fleet

- **Tags**: monitor-fleet-progress, scripts, fleet, multi-agent, observability, timeout-safety, install-payload
- **Last reviewed**: 2026-09-29
- **Status**: active

## Goal

Validates `scripts/monitor-fleet-progress.sh`, the optional polling helper `implement-fleet` Step 8 names for a fleet dispatch, which the installer ships with the runtime payload (ADR-0242). It takes `<run_id> <task_folder> [<return_dir> ...]`. It reads `<task_folder>/.wos/fleet-inbox/<run_id>/` and each named return folder (the `.fleet-out/` a worktree-isolated worker writes in its own worktree). A worker's return is either a flat `<worker_id>.json` payload, whose `status` field it shows and which counts as terminal once written, or the older per-worker directory holding a plain-text `status` token (`pending`, `in-progress`, `completed` or `failed`), optional `partial.*` files and an optional `terminal.json` naming its outcome. The script must refuse a bad invocation, name an absent target with exit 2 instead of printing an empty summary (ADR-0214 D-3 test 2), stop on its own once every known worker is terminal, keep polling while any worker is not, and end every measured run with one `dispatch_summary` line that accounts for every worker. Its default ceiling is 15 minutes (per K.8 parallel dispatch learnings, 2026-06-04); `FLEET_MONITOR_POLL_SECONDS` and `FLEET_MONITOR_TIMEOUT_SECONDS` shorten both intervals.

## Setup

A temp task folder with three run inboxes, and two worker return folders outside it.

Run `done` (per-worker directories, every worker terminal):

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

Run `flat` (the ADR-0158 carrier):

```text
<task>/.wos/fleet-inbox/flat/
  w1.json           # {"status": "satisfied", ...}
  w2.json           # {"status": "needs_revision", ...}
```

Return folders for run `wt` (no inbox for this run id):

```text
<wt1>/.fleet-out/w1.json   # {"status": "satisfied"}
<wt2>/.fleet-out/          # empty: the worker has not returned
```

## Input prompt

```text
Run scripts/monitor-fleet-progress.sh in six cases and capture exit code, stdout, stderr and elapsed wall-clock.

Case A (bad invocation):
  scripts/monitor-fleet-progress.sh

Case B (finished fleet, per-worker directories):
  scripts/monitor-fleet-progress.sh done <task>

Case C (running fleet), bounded from outside because the default ceiling is 15 minutes:
  run scripts/monitor-fleet-progress.sh live <task> in the background and stop it after 12 seconds

Case D (absent targets):
  scripts/monitor-fleet-progress.sh r1 <a path that does not exist>
  scripts/monitor-fleet-progress.sh nosuchrun <task>

Case E (flat returns in the inbox):
  scripts/monitor-fleet-progress.sh flat <task>

Case F (return folders, one pending), with FLEET_MONITOR_POLL_SECONDS=1 FLEET_MONITOR_TIMEOUT_SECONDS=3:
  scripts/monitor-fleet-progress.sh wt <task> <wt1>/.fleet-out <wt2>/.fleet-out
```

## Expected response shape

- Case A exits 2 with a `usage:` line naming `<run_id> <task_folder> [<return_dir> ...]` on stderr.
- Case B prints one table headed `worker_id`, `status`, `partial-bytes`, `last-updated` with the three workers, stops without waiting, and ends with `dispatch_summary: 3 dispatched / 2 merge_include / 1 worker_failed / 0 worker_timeout / 0 partial_merge / 3 total`, exit 0.
- Case C prints a table on each 5-second poll, with worker-02 shown as `in-progress`, and is still polling when it is stopped at 12 seconds.
- Case D exits 2 at once for both calls, naming `no such task folder` and `no fleet inbox at ... and no return folder named`, with no `dispatch_summary` line.
- Case E stops at once and ends with `dispatch_summary: 2 dispatched / 1 merge_include / 1 worker_failed / 0 worker_timeout / 0 partial_merge / 2 total`, exit 0.
- Case F shows `w1` as `satisfied` and the empty return folder as `pending`, stops at the 3-second timeout with a `timeout:` line, and ends with `dispatch_summary: 2 dispatched / 1 merge_include / 0 worker_failed / 1 worker_timeout / 0 partial_merge / 2 total`, exit 0.

## Pass criteria

1. **Bad invocation refused**: Case A exits 2, stderr carries the usage line, and no table is printed.
2. **Finished fleet stops on its own**: Case B exits 0 within 7 seconds, without being stopped from outside.
3. **Table rendered**: Case B stdout carries the `worker_id | status | partial-bytes | last-updated` header and exactly 3 worker rows; worker-01 shows a non-zero `partial-bytes`, the others 0.
4. **Outcome read before status**: worker-02 counts as `merge_include` from its `terminal.json`; worker-01, which has no `terminal.json`, counts as `merge_include` inferred from `completed`; worker-03 counts as `worker_failed` inferred from `failed`.
5. **Summary accounts for every worker**: the Case B `dispatch_summary` line reads exactly as in the expected shape, and `dispatched` equals `total`.
6. **A running worker keeps the poll alive**: Case C prints at least two tables in 12 seconds and has not exited when it is stopped.
7. **An absent target is named, never summarized**: both Case D calls exit 2 within 5 seconds with the absence named and no `dispatch_summary` line, and a timeout with no worker ever seen also exits 2 with `no worker return appeared`. Until 2026-09-29 a missing inbox was polled for 15 minutes and then reported as `0 dispatched` with exit 0.
8. **The flat carrier is read**: Case E counts `satisfied` as `merge_include` and `needs_revision` as `worker_failed`, and Case F counts the empty return folder as `worker_timeout`.

## Failure modes to watch

- **Stops while a worker is still running**: Case C or Case F exits before its timeout while a worker is pending, which would make the monitor report a finished fleet that is not finished.
- **Summary drops a worker**: a worker with no `terminal.json`, or a named return folder with no return yet, is left out of the counts.
- **Flags documented that the script does not read**: `--inbox`, `--interval` or `--timeout` in a doc or a caller. The script takes positional arguments only; the two intervals move only through their environment variables.
- **Timeout mistaken for success**: when the ceiling fires after at least one worker was seen, the script still exits 0, and the only signal is the `timeout:` line and the non-terminal workers counted as `worker_timeout`. A caller that reads the exit code alone cannot tell that timeout from a clean finish. That is the current contract, recorded so a change to it is deliberate.
- **Shipped but unrunnable**: the installer ships the script (`SHIPPED_SCRIPTS`), so `scripts/tests/test-install-payload.sh` runs an installed copy against an empty target; a version that polls instead of naming the absence hangs that probe.

## Notes

- Related learnings: `learnings_k8_parallel_dispatch.md` (5 reusable lessons from the first lived multi-agent dispatch, 2026-06-04). Lesson 4 (workers fail independently) and lesson 5 (operator needs visibility into stalled workers) motivate this helper.
- `implement-fleet` Step 8 names the script as an optional poller; the orchestrator still polls the host's worker lifecycle status itself. During a wave a worktree-isolated worker's return lives in its own `.fleet-out/`, so the useful call names those folders; the orchestrator copies them into the inbox only after the barrier (ADR-0242).
- `scripts/tests/test-shipped-helpers-absence.sh` checks 9 to 14 run the absent, flat, return-folder, empty-timeout and directory cases on every test run.

## History

- 2026-06-05: scenario authored as first coverage for monitor-fleet-progress.sh, grounded in K.8 parallel dispatch learnings.
- 2026-09-23: rewritten against the script as it ships. The first version invoked `--inbox`, `--interval` and `--timeout` flags, read a `status.json` per worker and expected a STALLED state and an exit 2 on timeout, none of which the script has.
- 2026-09-29: the script reads the flat return carrier and named return folders, names an absent target with exit 2, and ships in the install payload (ADR-0242). Criterion 7 inverted (a missing inbox no longer waits), criterion 8 and cases D to F added.
