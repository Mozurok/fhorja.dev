#!/usr/bin/env bash
# runs-feed.sh -- Fhorja runs-feed v1 producer helper (ADR-0080 D-4).
#
# Owns the producer lifecycle of .wos/runs/<run_id>.json, the contract the
# generated portfolio board (scripts/build-portfolio-board.py) reads to
# render running background runs. One file per run; the producer rewrites it
# in place as the run progresses and removes it when the run ends (a
# terminal outcome belongs in the outcome ledger per ADR-0080, not the feed).
#
# Subcommands:
#   start  <run_id> <task> <current_step>     create the feed file (state=starting)
#   update <run_id> [--state S] [--step STEP] refresh last_update_ts, optionally state/step
#   end    <run_id>                           remove the feed file (idempotent)
#   check                                     exit non-zero if a fresh run exists
#
# The check subcommand backs the D-4 one-run-at-a-time launcher guard: a
# fresh heartbeat means "already running" and refuses a second launch; a
# stale heartbeat (last_update_ts older than STALE_MINUTES) is reported as a
# warning and never treated as running.
#
# Paths resolve relative to the repo root (this script's grandparent dir), so
# the launcher may invoke it from anywhere.
#
# Usage:
#   runs-feed.sh start  <run_id> <task> <current_step>
#   runs-feed.sh update <run_id> [--state STATE] [--step STEP]
#   runs-feed.sh end    <run_id>
#   runs-feed.sh check
# Env:  STALE_MINUTES (default 15) overrides the staleness threshold, for tests.
# Exit: start/end -> 0 on success. update -> 0 on success, 1 for an unknown
#       run_id. check -> 0 no fresh run, 1 a fresh run exists. 2 = usage error.

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$DIR/../.." && pwd)"
RUNS_DIR="$REPO/.wos/runs"
STALE_MINUTES="${STALE_MINUTES:-15}"

usage() {
  echo "usage: runs-feed.sh {start <run_id> <task> <current_step>|update <run_id> [--state S] [--step STEP]|end <run_id>|check}" >&2
  exit 2
}

# now_iso_ms -> current UTC time as ISO 8601 with milliseconds and a Z suffix,
# e.g. 2026-07-04T12:34:56.789Z. One datetime.now() call so the printed
# milliseconds match the printed seconds (no split-second race).
now_iso_ms() {
  python3 -c '
import datetime
n = datetime.datetime.now(datetime.timezone.utc)
print(n.strftime("%Y-%m-%dT%H:%M:%S.") + f"{n.microsecond // 1000:03d}Z")
'
}

# age_minutes <iso8601-ms-Z timestamp> -> minutes elapsed since, or "nan" if
# the timestamp does not match the expected format.
age_minutes() {
  python3 -c '
import sys, datetime
ts = sys.argv[1]
try:
    dt = datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc)
except ValueError:
    print("nan")
    sys.exit(0)
now = datetime.datetime.now(datetime.timezone.utc)
print((now - dt).total_seconds() / 60.0)
' "$1"
}

cmd="${1:-}"; shift || true

case "$cmd" in
  start)
    run_id="${1:-}"; task="${2:-}"; step="${3:-}"
    [[ -z "$run_id" || -z "$task" || -z "$step" ]] && usage
    mkdir -p "$RUNS_DIR"
    ts="$(now_iso_ms)"
    jq -n \
      --argjson schema_version 1 \
      --arg run_id "$run_id" \
      --arg task "$task" \
      --arg state "starting" \
      --arg started_ts "$ts" \
      --arg last_update_ts "$ts" \
      --arg current_step "$step" \
      '{schema_version: $schema_version, run_id: $run_id, task: $task,
        state: $state, started_ts: $started_ts, last_update_ts: $last_update_ts,
        current_step: $current_step}' \
      > "$RUNS_DIR/$run_id.json"
    echo "started: $RUNS_DIR/$run_id.json"
    ;;

  update)
    run_id="${1:-}"; shift || true
    [[ -z "$run_id" ]] && usage
    file="$RUNS_DIR/$run_id.json"
    if [[ ! -f "$file" ]]; then
      echo "runs-feed: unknown run_id '$run_id' (no feed file at $file)" >&2
      exit 1
    fi
    new_state=""; new_step=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --state) new_state="${2:-}"; shift 2 ;;
        --step)  new_step="${2:-}"; shift 2 ;;
        *) echo "runs-feed: unknown update arg $1" >&2; exit 2 ;;
      esac
    done
    ts="$(now_iso_ms)"
    tmp="$(mktemp "$RUNS_DIR/.${run_id}.XXXXXX")"
    jq \
      --arg last_update_ts "$ts" \
      --arg new_state "$new_state" \
      --arg new_step "$new_step" \
      '.last_update_ts = $last_update_ts
       | if ($new_state | length) > 0 then .state = $new_state else . end
       | if ($new_step | length) > 0 then .current_step = $new_step else . end' \
      "$file" > "$tmp"
    mv "$tmp" "$file"
    echo "updated: $file"
    ;;

  end)
    run_id="${1:-}"
    [[ -z "$run_id" ]] && usage
    file="$RUNS_DIR/$run_id.json"
    if [[ -f "$file" ]]; then
      rm -f "$file"
      echo "ended: $file"
    else
      echo "runs-feed: warning: no feed file for run_id '$run_id' at $file (already ended)" >&2
    fi
    exit 0
    ;;

  check)
    if [[ ! -d "$RUNS_DIR" ]]; then
      echo "check: no runs directory ($RUNS_DIR); no fresh run"
      exit 0
    fi
    fresh_found=0
    shopt -s nullglob
    for f in "$RUNS_DIR"/*.json; do
      last_update_ts="$(jq -r '.last_update_ts // empty' "$f" 2>/dev/null || true)"
      if [[ -z "$last_update_ts" ]]; then
        echo "check: warning: $f has no last_update_ts (ignored)" >&2
        continue
      fi
      age="$(age_minutes "$last_update_ts")"
      if [[ "$age" == "nan" ]]; then
        echo "check: warning: $f has unparsable last_update_ts '$last_update_ts' (ignored)" >&2
        continue
      fi
      is_stale="$(python3 -c "print(1 if float('$age') > float('$STALE_MINUTES') else 0)")"
      if [[ "$is_stale" == "1" ]]; then
        echo "check: warning: stale run '$(basename "$f" .json)' (last update ${age%.*} min ago, threshold ${STALE_MINUTES} min)" >&2
      else
        echo "check: fresh run '$(basename "$f" .json)' (last update ${age%.*} min ago)"
        fresh_found=1
      fi
    done
    if [[ "$fresh_found" -eq 1 ]]; then
      exit 1
    fi
    echo "check: no fresh run"
    exit 0
    ;;

  *)
    usage
    ;;
esac
