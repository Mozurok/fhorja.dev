#!/usr/bin/env bash
# governor.sh -- Fhorja autonomy track runtime governor (ADR-0044, D11).
#
# Deterministic, in-process limits that bound an autonomous run so it cannot
# run away: a maximum-iteration count, a wall-clock timeout, and an
# identical-command loop detector. The per-task token/cost ceiling is enforced
# by the executing harness (the Workflow tool budget); this script covers the
# parts a markdown+bash Fhorja can enforce on its own.
#
# Call once per slice attempt. It updates a small state file and decides
# whether the run may continue.
#
# Usage:
#   governor.sh <state-file> --max-iter N --timeout-sec S --command "CMD"
# Time source: $AUTONOMY_NOW_EPOCH if set (for tests), else `date +%s`.
# Exit:  0 = continue, 20 = halt (reason printed). 2 = usage error.

set -euo pipefail

state="" ; max_iter=0 ; timeout_sec=0 ; cmd=""
state="${1:-}"; shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-iter)    max_iter="${2:-}"; shift 2 ;;
    --timeout-sec) timeout_sec="${2:-}"; shift 2 ;;
    --command)     cmd="${2:-}"; shift 2 ;;
    *) echo "governor: unknown arg $1" >&2; exit 2 ;;
  esac
done
[[ -z "$state" || -z "$max_iter" || -z "$timeout_sec" ]] && { echo "governor: usage: <state-file> --max-iter N --timeout-sec S --command CMD" >&2; exit 2; }

now="${AUTONOMY_NOW_EPOCH:-$(date +%s)}"

# State file format (one key=value per line): start=<epoch> iter=<n> last1/last2/last3=<cmd>
start="$now"; iter=0; last1=""; last2=""; last3=""
if [[ -f "$state" ]]; then
  # shellcheck disable=SC1090
  while IFS='=' read -r k v; do
    case "$k" in
      start) start="$v" ;; iter) iter="$v" ;;
      last1) last1="$v" ;; last2) last2="$v" ;; last3) last3="$v" ;;
    esac
  done < "$state"
fi

iter=$((iter + 1))
elapsed=$((now - start))

# Slide the command window (last3 is the oldest).
last3="$last2"; last2="$last1"; last1="$cmd"

{
  echo "start=$start"
  echo "iter=$iter"
  echo "last1=$last1"
  echo "last2=$last2"
  echo "last3=$last3"
} > "$state"

if [[ "$iter" -gt "$max_iter" ]]; then
  echo "HALT: max iterations exceeded ($iter > $max_iter)"; exit 20
fi
if [[ "$timeout_sec" -gt 0 && "$elapsed" -ge "$timeout_sec" ]]; then
  echo "HALT: wall-clock timeout ($elapsed s >= $timeout_sec s)"; exit 20
fi
if [[ -n "$cmd" && "$last1" == "$last2" && "$last2" == "$last3" ]]; then
  echo "HALT: identical-command loop detected (3x \"$cmd\")"; exit 20
fi

echo "CONTINUE: iter=$iter elapsed=${elapsed}s"
exit 0
