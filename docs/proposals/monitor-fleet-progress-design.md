# scripts/monitor-fleet-progress.sh -- Design Outline

## Purpose

Portable bash monitor for a running Epic J fleet orchestrator (e.g. `screen-spec-fleet`, `atom-audit-fleet`, `task-init-fleet`). Polls the run's fleet-inbox directory and renders a per-worker status table updated every 5 seconds until convergence is reached, then emits a final `dispatch_summary` matching the N/M/K/L/P/T counters defined in `packages/wos-engine/internal/wos/sub-agent-orchestration.md`. Lets the operator confirm liveness without tailing N worker logs by hand; replaces ad-hoc `watch ls` invocations and gives the orchestrator a deterministic signal that all subagents have either reported or hard-failed.

## Inputs

- `<run_id>` -- required positional. Maps 1:1 to `.wos/fleet-inbox/<run_id>/`.
- `<task_folder>` -- required positional. Absolute or repo-relative path to the active task folder used to resolve the dispatch manifest (`<task_folder>/fleet/<run_id>/manifest.json`) and the convergence target N.
- Optional flags: `--interval <seconds>` (default 5), `--timeout <seconds>` (default 0 = no timeout), `--no-color`, `--once` (single snapshot, no loop).

## Output table format

Rendered to stdout, re-drawn in place when on a TTY (clear + reprint), appended once per tick otherwise:

```
run_id: <run_id>   target N: <N>   elapsed: <hh:mm:ss>
worker_id              status        size      last_updated
---------------------  ------------  --------  --------------------
worker-01              completed     12.4 KB   2026-06-04 14:22:11
worker-02              in-progress    3.1 KB   2026-06-04 14:22:09
worker-03              pending         0  B    --
worker-04              failed         0  B    2026-06-04 14:21:58
```

Status derived from the inbox slot: missing file = `pending`, file exists but no trailing sentinel (`"status":` field absent or `in_progress`) = `in-progress`, valid JSON with terminal `status` = `completed`, marker `.failed` sibling = `failed`.

## Convergence detection

Convergence = `completed + failed == N` (from manifest). Linux path uses `inotifywait -m -e close_write,create,moved_to,delete` on the inbox directory and recomputes counts on each event. macOS / BSD fallback polls `stat`/`ls -l --time-style=+%s` every `--interval` seconds. On convergence the script prints the final `dispatch_summary`:

```
dispatch_summary: N=<N> M=<completed> K=<failed> L=<late> P=<partial> T=<elapsed_seconds>
```

`L` (late) = workers that completed after a soft deadline, `P` (partial) = completed workers whose output JSON failed the manifest's schema check (when `jq` is available). Non-zero exit if `K > 0` so CI / orchestrator can branch.

## Bash skeleton (with comments)

```bash
#!/usr/bin/env bash
# scripts/monitor-fleet-progress.sh -- poll .wos/fleet-inbox/<run_id> until convergence.
set -euo pipefail

usage() { echo "usage: $0 <run_id> <task_folder> [--interval s] [--timeout s] [--no-color] [--once]"; exit 2; }
[[ $# -lt 2 ]] && usage
RUN_ID=$1; TASK_FOLDER=$2; shift 2
INTERVAL=5; TIMEOUT=0; ONCE=0; COLOR=1
while [[ $# -gt 0 ]]; do case "$1" in
  --interval) INTERVAL=$2; shift 2;;
  --timeout)  TIMEOUT=$2;  shift 2;;
  --no-color) COLOR=0; shift;;
  --once)     ONCE=1; shift;;
  *) usage;;
esac; done

INBOX=".wos/fleet-inbox/${RUN_ID}"
MANIFEST="${TASK_FOLDER}/fleet/${RUN_ID}/manifest.json"
[[ -d "$INBOX" ]]    || { echo "inbox not found: $INBOX" >&2; exit 3; }
[[ -f "$MANIFEST" ]] || { echo "manifest not found: $MANIFEST" >&2; exit 3; }

N=$(jq -r '.workers | length' "$MANIFEST")
WORKERS=$(jq -r '.workers[].id' "$MANIFEST")
START=$(date +%s)

classify() { # echoes "<status>\t<size>\t<mtime>"
  local id=$1 slot="$INBOX/$1.json" fail="$INBOX/$1.failed"
  if   [[ -f "$fail" ]];  then printf "failed\t0\t%s" "$(stat -f %m "$fail" 2>/dev/null || stat -c %Y "$fail")"
  elif [[ ! -f "$slot" ]];then printf "pending\t0\t-"
  else
    local size mtime; size=$(wc -c <"$slot"); mtime=$(stat -f %m "$slot" 2>/dev/null || stat -c %Y "$slot")
    if jq -e '.status == "completed"' "$slot" >/dev/null 2>&1
    then printf "completed\t%s\t%s" "$size" "$mtime"
    else printf "in-progress\t%s\t%s" "$size" "$mtime"; fi
  fi
}

render() {
  local elapsed=$(( $(date +%s) - START )) done=0 fail=0
  printf '\033[H\033[2J' # clear when on TTY; harmless otherwise
  printf 'run_id: %s   target N: %s   elapsed: %ds\n' "$RUN_ID" "$N" "$elapsed"
  printf '%-22s %-12s %-9s %s\n' worker_id status size last_updated
  while IFS= read -r id; do
    IFS=$'\t' read -r st sz mt < <(classify "$id")
    [[ "$st" == completed ]] && done=$((done+1))
    [[ "$st" == failed    ]] && fail=$((fail+1))
    local human_ts="-"; [[ "$mt" != "-" ]] && human_ts=$(date -r "$mt" '+%F %T' 2>/dev/null || date -d "@$mt" '+%F %T')
    printf '%-22s %-12s %-9s %s\n' "$id" "$st" "$sz" "$human_ts"
  done <<<"$WORKERS"
  echo "$done $fail"
}

# Main loop: inotifywait on linux, polling fallback elsewhere.
USE_INOTIFY=0; command -v inotifywait >/dev/null && [[ "$(uname)" == Linux ]] && USE_INOTIFY=1
while :; do
  read -r DONE FAIL < <(render | tail -n1)
  TOTAL=$((DONE + FAIL))
  if (( TOTAL >= N )); then
    ELAPSED=$(( $(date +%s) - START ))
    printf 'dispatch_summary: N=%d M=%d K=%d L=0 P=0 T=%d\n' "$N" "$DONE" "$FAIL" "$ELAPSED"
    (( FAIL > 0 )) && exit 1 || exit 0
  fi
  (( ONCE == 1 )) && exit 0
  if (( TIMEOUT > 0 )) && (( $(date +%s) - START > TIMEOUT )); then
    echo "timeout before convergence" >&2; exit 4
  fi
  if (( USE_INOTIFY == 1 )); then
    inotifywait -qq -t "$INTERVAL" -e close_write,create,moved_to,delete "$INBOX" || true
  else
    sleep "$INTERVAL"
  fi
done
```
