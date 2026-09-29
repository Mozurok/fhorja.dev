#!/usr/bin/env bash
#
# monitor-fleet-progress.sh
#
# Polls a fleet run's worker returns and prints per-worker status until every
# worker it knows about is terminal or a 15-minute timeout elapses.
#
# Usage:
#   scripts/monitor-fleet-progress.sh <run_id> <task_folder> [<return_dir> ...]
#
# Inputs:
#   run_id       Identifier of the fleet run; the script reads
#                <task_folder>/.wos/fleet-inbox/<run_id>/
#   task_folder  Absolute or relative path to the active task folder.
#   return_dir   Optional, one per worker: the return folder a worktree-isolated
#                worker writes inside its own worktree (<worktree>/.fleet-out/,
#                ADR-0242). The worker's return is the one <worker_id>.json in it;
#                until that file exists the worker counts as pending.
#
# What it reads, in the run inbox and in each return_dir:
#   <worker_id>.json          the flat return carrier (ADR-0158 D-1, ADR-0242): a
#                             payload matching the orchestrator's worker_output_schema.
#                             Its "status" field is shown; a written return is terminal.
#   <worker_id>/              the older per-worker directory layout, still read:
#     status                  plain-text token: pending | in-progress | completed | failed
#     partial.*               optional partial output, shown by size
#     terminal.json           optional { "outcome": "merge_include" | "worker_failed"
#                                        | "worker_timeout" | "partial_merge" }
#
# Behavior:
#   - Refreshes every 5 seconds; prints worker_id | status | partial-bytes |
#     last-updated (partial-bytes is the size of a flat return, or of the
#     largest partial.* in a worker directory).
#   - Exits 0 when every known worker is terminal, and exits 0 when the 15-minute
#     timeout fires after at least one worker was seen (the timeout: line and the
#     worker_timeout count carry that signal).
#   - Names what it could not read and exits 2 (ADR-0214 D-3 test 2), instead of
#     printing an empty summary: a task folder that does not exist; a run inbox
#     that does not exist when no return_dir is named (the orchestrator creates the
#     inbox before dispatch, so its absence means a wrong run id or folder); a
#     timeout with no worker ever seen.
#   - Reads no path from its own location, so an installed copy works from any
#     directory (ADR-0214 D-3 test 1).
#   - FLEET_MONITOR_POLL_SECONDS and FLEET_MONITOR_TIMEOUT_SECONDS override the two
#     intervals; the tests use them to keep a run short.
#
# Final line:
#   dispatch_summary: N dispatched / M merge_include / K worker_failed / \
#     L worker_timeout / P partial_merge / T total
#
set -uo pipefail

POLL_INTERVAL_SECONDS="${FLEET_MONITOR_POLL_SECONDS:-5}"
TIMEOUT_SECONDS="${FLEET_MONITOR_TIMEOUT_SECONDS:-900}"

usage() {
  echo "usage: $(basename "$0") <run_id> <task_folder> [<return_dir> ...]" >&2
  exit 2
}

if [[ $# -lt 2 ]]; then
  usage
fi

run_id="$1"
task_folder="$2"
shift 2
return_dirs=("$@")

if [[ -z "$run_id" || -z "$task_folder" ]]; then
  usage
fi

if [[ ! -d "$task_folder" ]]; then
  echo "monitor-fleet-progress: not measured, no such task folder: ${task_folder}" >&2
  exit 2
fi

inbox_dir="${task_folder%/}/.wos/fleet-inbox/${run_id}"

if [[ ! -d "$inbox_dir" && ${#return_dirs[@]} -eq 0 ]]; then
  echo "monitor-fleet-progress: not measured, no fleet inbox at ${inbox_dir} and no return folder named" >&2
  exit 2
fi

# file_bytes: size of a file in bytes, portable (no stat flavor).
file_bytes() {
  wc -c < "$1" 2>/dev/null | tr -d ' ' || echo 0
}

# file_mtime: human mtime of a path, BSD stat first, then GNU date -r.
file_mtime() {
  stat -f%Sm -t "%Y-%m-%d %H:%M:%S" "$1" 2>/dev/null \
    || date -r "$1" "+%Y-%m-%d %H:%M:%S" 2>/dev/null \
    || echo "-"
}

# json_status: the "status" value of a flat return, or "unreadable".
json_status() {
  local v
  v=$(grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' "$1" 2>/dev/null \
    | head -n1 \
    | sed -E 's/.*"status"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
  echo "${v:-unreadable}"
}

# dir_status: the status token of a per-worker directory, "pending" when absent.
dir_status() {
  local raw
  if [[ -f "$1/status" ]]; then
    raw=$(tr -d '[:space:]' < "$1/status" 2>/dev/null || true)
    if [[ -n "$raw" ]]; then echo "$raw"; return; fi
  fi
  echo "pending"
}

dir_bytes() {
  local biggest=0 size f
  for f in "$1"/partial*; do
    [[ -e "$f" ]] || continue
    size=$(file_bytes "$f")
    if (( size > biggest )); then biggest=$size; fi
  done
  echo "$biggest"
}

dir_mtime() {
  local newest="" m f
  for f in "$1"/* "$1"/.[!.]*; do
    [[ -e "$f" ]] || continue
    m=$(file_mtime "$f")
    if [[ "$m" != "-" && "$m" > "$newest" ]]; then newest="$m"; fi
  done
  [[ -n "$newest" ]] || newest=$(file_mtime "$1")
  echo "$newest"
}

dir_outcome() {
  local f="$1/terminal.json"
  [[ -f "$f" ]] || { echo ""; return; }
  grep -o '"outcome"[[:space:]]*:[[:space:]]*"[^"]*"' "$f" 2>/dev/null \
    | head -n1 \
    | sed -E 's/.*"outcome"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/'
}

# collect: one tab-separated row per known worker:
#   id <TAB> status <TAB> bytes <TAB> mtime <TAB> kind <TAB> outcome
# kind is json (a written flat return), dir (per-worker directory) or pending
# (a named return folder with no return yet). A worker id seen twice (a return
# already copied into the inbox and still in its return folder) is listed once.
collect() {
  local seen="|" f d id rd found
  shopt -s nullglob
  if [[ -d "$inbox_dir" ]]; then
    for f in "$inbox_dir"/*.json; do
      id=$(basename "$f" .json)
      case "$seen" in *"|$id|"*) continue ;; esac
      seen="${seen}${id}|"
      printf '%s\t%s\t%s\t%s\tjson\t\n' "$id" "$(json_status "$f")" "$(file_bytes "$f")" "$(file_mtime "$f")"
    done
    for d in "$inbox_dir"/*/; do
      d="${d%/}"
      id=$(basename "$d")
      case "$seen" in *"|$id|"*) continue ;; esac
      seen="${seen}${id}|"
      printf '%s\t%s\t%s\t%s\tdir\t%s\n' "$id" "$(dir_status "$d")" "$(dir_bytes "$d")" "$(dir_mtime "$d")" "$(dir_outcome "$d")"
    done
  fi
  for rd in "${return_dirs[@]+"${return_dirs[@]}"}"; do
    found=""
    for f in "${rd%/}"/*.json; do
      found="$f"
      break
    done
    if [[ -n "$found" ]]; then
      id=$(basename "$found" .json)
      case "$seen" in *"|$id|"*) continue ;; esac
      seen="${seen}${id}|"
      printf '%s\t%s\t%s\t%s\tjson\t\n' "$id" "$(json_status "$found")" "$(file_bytes "$found")" "$(file_mtime "$found")"
    else
      printf '%s\tpending\t0\t-\tpending\t\n' "$rd"
    fi
  done
  shopt -u nullglob
}

is_terminal() {
  # $1 status, $2 kind
  case "$2" in
    json) return 0 ;;
    pending) return 1 ;;
  esac
  case "$1" in
    completed|failed) return 0 ;;
    *) return 1 ;;
  esac
}

print_table() {
  local rows="$1" id status bytes mtime kind outcome
  printf '\n=== fleet run %s @ %s ===\n' "$run_id" "$(date "+%Y-%m-%d %H:%M:%S")"
  printf '%-28s %-16s %-14s %s\n' "worker_id" "status" "partial-bytes" "last-updated"
  printf '%-28s %-16s %-14s %s\n' "----------------------------" "----------------" "--------------" "-------------------"
  while IFS=$'\t' read -r id status bytes mtime kind outcome; do
    [[ -n "$id" ]] || continue
    printf '%-28s %-16s %-14s %s\n' "$id" "$status" "$bytes" "$mtime"
  done <<< "$rows"
}

all_terminal() {
  local rows="$1" id status bytes mtime kind outcome any=0
  while IFS=$'\t' read -r id status bytes mtime kind outcome; do
    [[ -n "$id" ]] || continue
    any=1
    is_terminal "$status" "$kind" || return 1
  done <<< "$rows"
  (( any == 1 ))
}

count_rows() {
  local rows="$1" n=0 id rest
  while IFS=$'\t' read -r id rest; do
    [[ -n "$id" ]] && n=$((n + 1))
  done <<< "$rows"
  echo "$n"
}

print_dispatch_summary() {
  local rows="$1" total=0 mi=0 wf=0 wt=0 pm=0 id status bytes mtime kind outcome
  while IFS=$'\t' read -r id status bytes mtime kind outcome; do
    [[ -n "$id" ]] || continue
    total=$((total + 1))
    if [[ "$kind" == "json" ]]; then
      case "$status" in
        satisfied) mi=$((mi + 1)) ;;
        interrupted|timed_out) wt=$((wt + 1)) ;;
        *) wf=$((wf + 1)) ;;
      esac
      continue
    fi
    if [[ "$kind" == "pending" ]]; then
      wt=$((wt + 1))
      continue
    fi
    case "$outcome" in
      merge_include)  mi=$((mi + 1)) ;;
      worker_failed)  wf=$((wf + 1)) ;;
      worker_timeout) wt=$((wt + 1)) ;;
      partial_merge)  pm=$((pm + 1)) ;;
      *)
        case "$status" in
          completed) mi=$((mi + 1)) ;;
          failed)    wf=$((wf + 1)) ;;
          *)         wt=$((wt + 1)) ;;
        esac
        ;;
    esac
  done <<< "$rows"
  printf '\ndispatch_summary: %d dispatched / %d merge_include / %d worker_failed / %d worker_timeout / %d partial_merge / %d total\n' \
    "$total" "$mi" "$wf" "$wt" "$pm" "$total"
}

deadline=$(( $(date +%s) + TIMEOUT_SECONDS ))
seen_any=0
rows=""

while true; do
  rows=$(collect)
  if [[ "$(count_rows "$rows")" -gt 0 ]]; then
    print_table "$rows"
    if [[ -n "$(printf '%s\n' "$rows" | grep -v $'\tpending\t0\t-\tpending\t' || true)" ]]; then
      seen_any=1
    fi
    if all_terminal "$rows"; then
      break
    fi
  else
    printf '[%s] no worker return yet under %s\n' "$(date "+%Y-%m-%d %H:%M:%S")" "$inbox_dir"
  fi
  if (( $(date +%s) >= deadline )); then
    printf '\n[%s] timeout: %s seconds elapsed, stopping monitor.\n' "$(date "+%Y-%m-%d %H:%M:%S")" "$TIMEOUT_SECONDS"
    if (( seen_any == 0 )); then
      echo "monitor-fleet-progress: not measured, no worker return appeared under ${inbox_dir} or a named return folder" >&2
      exit 2
    fi
    break
  fi
  sleep "$POLL_INTERVAL_SECONDS"
done

print_dispatch_summary "$rows"
exit 0
