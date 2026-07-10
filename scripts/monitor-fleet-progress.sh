#!/usr/bin/env bash
#
# monitor-fleet-progress.sh
#
# Polls a fleet inbox directory and prints per-worker status until all workers
# reach a terminal state or a 15-minute timeout elapses.
#
# Usage:
#   scripts/monitor-fleet-progress.sh <run_id> <task_folder>
#
# Inputs:
#   run_id       Identifier of the fleet run; the script watches
#                <task_folder>/.wos/fleet-inbox/<run_id>/
#   task_folder  Absolute or relative path to the active task folder
#                (must contain .wos/fleet-inbox/<run_id>/ once dispatch starts).
#
# Layout expected inside the run inbox (one entry per dispatched worker):
#   <worker_id>/
#     status                    plain-text status token, one of:
#                               pending | in-progress | completed | failed
#     partial.md (or partial.*) optional partial-output file used for size
#     terminal.json (optional)  when present, classifies terminal outcome:
#                                 { "outcome": "merge_include"
#                                            | "worker_failed"
#                                            | "worker_timeout"
#                                            | "partial_merge" }
#
# Behavior:
#   - Refreshes every 5 seconds.
#   - Prints a table: worker_id | status | partial-bytes | last-updated.
#   - Exits 0 when every worker is terminal (completed or failed) or when the
#     15-minute wall-clock timeout fires.
#   - macOS-compatible: uses `stat -f%z` for size and `find -newer`-free
#     mtime lookup via `stat -f%Sm`.
#
# Final dispatch_summary line format:
#   dispatch_summary: N dispatched / M merge_include / K worker_failed / \
#     L worker_timeout / P partial_merge / T total
#
set -uo pipefail

readonly POLL_INTERVAL_SECONDS=5
readonly TIMEOUT_SECONDS=$((15 * 60))

usage() {
  echo "usage: $(basename "$0") <run_id> <task_folder>" >&2
  exit 2
}

if [[ $# -ne 2 ]]; then
  usage
fi

run_id="$1"
task_folder="$2"

if [[ -z "$run_id" || -z "$task_folder" ]]; then
  usage
fi

inbox_dir="${task_folder%/}/.wos/fleet-inbox/${run_id}"

# read_status: echoes the status token for a worker dir, or "pending" when the
# status file is missing or empty.
read_status() {
  local worker_dir="$1"
  local status_file="${worker_dir}/status"
  if [[ -f "$status_file" ]]; then
    local raw
    raw=$(tr -d '[:space:]' < "$status_file" 2>/dev/null || true)
    if [[ -n "$raw" ]]; then
      echo "$raw"
      return
    fi
  fi
  echo "pending"
}

# partial_size_bytes: prints size in bytes of the largest partial.* file in the
# worker dir, or 0 when none exists. Uses macOS-flavored stat.
partial_size_bytes() {
  local worker_dir="$1"
  local biggest=0 size
  local f
  for f in "$worker_dir"/partial*; do
    [[ -e "$f" ]] || continue
    size=$(stat -f%z "$f" 2>/dev/null || echo 0)
    if (( size > biggest )); then
      biggest=$size
    fi
  done
  echo "$biggest"
}

# last_updated: prints the most recent mtime (human format) across files in the
# worker dir; falls back to the dir's own mtime, then "-" if missing.
last_updated() {
  local worker_dir="$1"
  local newest="" mtime f
  for f in "$worker_dir"/* "$worker_dir"/.[!.]*; do
    [[ -e "$f" ]] || continue
    mtime=$(stat -f%Sm -t "%Y-%m-%d %H:%M:%S" "$f" 2>/dev/null || true)
    if [[ -n "$mtime" && "$mtime" > "$newest" ]]; then
      newest="$mtime"
    fi
  done
  if [[ -z "$newest" ]]; then
    newest=$(stat -f%Sm -t "%Y-%m-%d %H:%M:%S" "$worker_dir" 2>/dev/null || echo "-")
  fi
  echo "$newest"
}

# terminal_outcome: prints the outcome label found in terminal.json, or "".
terminal_outcome() {
  local worker_dir="$1"
  local f="${worker_dir}/terminal.json"
  [[ -f "$f" ]] || { echo ""; return; }
  grep -o '"outcome"[[:space:]]*:[[:space:]]*"[^"]*"' "$f" 2>/dev/null \
    | head -n1 \
    | sed -E 's/.*"outcome"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/'
}

is_terminal_status() {
  case "$1" in
    completed|failed) return 0 ;;
    *) return 1 ;;
  esac
}

print_table() {
  local now_label="$1"
  printf '\n=== fleet run %s @ %s ===\n' "$run_id" "$now_label"
  printf '%-28s %-13s %-22s %s\n' "worker_id" "status" "partial-bytes" "last-updated"
  printf '%-28s %-13s %-22s %s\n' "----------------------------" "-------------" "----------------------" "-------------------"
  local worker_dir worker_id status bytes updated
  shopt -s nullglob
  for worker_dir in "$inbox_dir"/*/; do
    worker_id=$(basename "$worker_dir")
    status=$(read_status "$worker_dir")
    bytes=$(partial_size_bytes "$worker_dir")
    updated=$(last_updated "$worker_dir")
    printf '%-28s %-13s %-22s %s\n' "$worker_id" "$status" "$bytes" "$updated"
  done
  shopt -u nullglob
}

all_workers_terminal() {
  local worker_dir status any=0
  shopt -s nullglob
  for worker_dir in "$inbox_dir"/*/; do
    any=1
    status=$(read_status "$worker_dir")
    if ! is_terminal_status "$status"; then
      shopt -u nullglob
      return 1
    fi
  done
  shopt -u nullglob
  # Treat "no workers yet" as not-terminal so we keep polling for late arrivals.
  if (( any == 0 )); then
    return 1
  fi
  return 0
}

print_dispatch_summary() {
  local total=0 merge_include=0 worker_failed=0 worker_timeout=0 partial_merge=0
  local worker_dir status outcome
  shopt -s nullglob
  for worker_dir in "$inbox_dir"/*/; do
    total=$((total + 1))
    status=$(read_status "$worker_dir")
    outcome=$(terminal_outcome "$worker_dir")
    case "$outcome" in
      merge_include)  merge_include=$((merge_include + 1)) ;;
      worker_failed)  worker_failed=$((worker_failed + 1)) ;;
      worker_timeout) worker_timeout=$((worker_timeout + 1)) ;;
      partial_merge)  partial_merge=$((partial_merge + 1)) ;;
      "")
        # No explicit outcome: infer from final status so the summary still
        # accounts for every dispatched worker.
        case "$status" in
          completed) merge_include=$((merge_include + 1)) ;;
          failed)    worker_failed=$((worker_failed + 1)) ;;
          *)         worker_timeout=$((worker_timeout + 1)) ;;
        esac
        ;;
    esac
  done
  shopt -u nullglob

  printf '\ndispatch_summary: %d dispatched / %d merge_include / %d worker_failed / %d worker_timeout / %d partial_merge / %d total\n' \
    "$total" "$merge_include" "$worker_failed" "$worker_timeout" "$partial_merge" "$total"
}

start_epoch=$(date +%s)
deadline=$((start_epoch + TIMEOUT_SECONDS))
timed_out=0

while true; do
  now_epoch=$(date +%s)
  now_label=$(date "+%Y-%m-%d %H:%M:%S")

  if [[ ! -d "$inbox_dir" ]]; then
    printf '[%s] waiting for inbox dir: %s\n' "$now_label" "$inbox_dir"
  else
    print_table "$now_label"
    if all_workers_terminal; then
      break
    fi
  fi

  if (( now_epoch >= deadline )); then
    printf '\n[%s] timeout: 15 minutes elapsed, stopping monitor.\n' "$now_label"
    timed_out=1
    break
  fi

  sleep "$POLL_INTERVAL_SECONDS"
done

print_dispatch_summary

if (( timed_out == 1 )); then
  exit 0
fi
exit 0
