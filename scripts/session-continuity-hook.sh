#!/usr/bin/env bash
# session-continuity-hook.sh - Claude Code SessionStart/SessionStop hook for Fhorja task memory.
#
# Keeps an active Fhorja task resumable across sessions without relying on the user
# remembering to run sync-task-state:
#   - stop  : write a bounded continuity marker to the active task's .wos/ sidecar
#             (session-end timestamp + session id). It NEVER touches authored
#             TASK_STATE.md sections (decision D-1: auto-write is sidecar-only).
#   - start : print the active task's Resume notes + Recommended next step, and,
#             when TASK_STATE.md has not been updated since the last session ended,
#             nudge the user to run sync-task-state.
#
# Mode resolution: first CLI arg ("start" | "stop"), else hook_event_name from the
# Claude Code hook JSON on stdin (SessionStart -> start, SessionStop|Stop -> stop).
#
# Task root: $WOS_TASKS_ROOT, else $CLAUDE_PROJECT_DIR/projects, else ./projects.
# The active task is the most-recently-modified projects/*/active/*/TASK_STATE.md.
#
# Advisory and non-blocking: this hook always exits 0. It prints to stdout (shown
# in the session) and never fails the turn, mirroring the typecheck-hook posture.
#
# Stdin: optional Claude Code hook JSON (session_id, hook_event_name, source).

# No `set -e`: this hook is advisory and must always exit 0 (a stray command
# failure must not turn into a non-zero exit that surfaces noise to the session).
set -uo pipefail

# ---------------------------------------------------------------------------
# 1. Read optional hook JSON from stdin (non-fatal if empty / not JSON)
# ---------------------------------------------------------------------------
input=""
if [[ ! -t 0 ]]; then
  # Read stdin only if data is actually piped (Claude Code hook JSON). A short
  # per-line timeout means a manual invocation with no piped input cannot block
  # the session waiting on an stdin that never closes.
  while IFS= read -r -t 1 _line; do
    input+="$_line"$'\n'
  done || true
fi

json_field() { # field-name -> value or empty
  [[ -z "$input" ]] && { printf ''; return; }
  printf '%s' "$input" | jq -r ".$1 // empty" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# 2. Resolve mode (start | stop)
# ---------------------------------------------------------------------------
mode="${1:-}"
if [[ -z "$mode" ]]; then
  case "$(json_field hook_event_name)" in
    SessionStart) mode="start" ;;
    SessionStop|Stop) mode="stop" ;;
    *) mode="" ;;
  esac
fi
if [[ "$mode" != "start" && "$mode" != "stop" ]]; then
  # Unknown invocation; do nothing, but never fail.
  exit 0
fi

# ---------------------------------------------------------------------------
# 3. Locate the active task folder (most-recently-modified TASK_STATE.md)
# ---------------------------------------------------------------------------
tasks_root="${WOS_TASKS_ROOT:-${CLAUDE_PROJECT_DIR:-.}/projects}"
[[ -d "$tasks_root" ]] || exit 0   # no projects tree here; nothing to do

# Portable mtime (epoch seconds), detected ONCE. The chained fallback this replaces was
# broken on GNU: `stat -f %m` exits 1 there but writes the filesystem report to STDOUT
# before failing, and `2>/dev/null` silences only stderr, so the substitution captured the
# dump concatenated with the real epoch from the second branch.
if stat -f '%m' "$0" >/dev/null 2>&1; then STAT_MTIME=(stat -f '%m'); else STAT_MTIME=(stat -c '%Y'); fi
mtime() {
  local v
  v=$("${STAT_MTIME[@]}" "$1" 2>/dev/null || echo 0)
  case "$v" in ''|*[!0-9]*) v=0 ;; esac
  echo "$v"
}

# Search scope. `projects/` holds the tasks of EVERY project, so "most recently
# modified across the tree" is not the task in hand once more than one is open.
# Wired unscoped in a tree with 32 active tasks across 84 projects, this printed
# an unrelated client task's resume notes into SessionStart context and wrote a
# session-end marker into that task's sidecar. Scope is therefore explicit:
#
#   WOS_ACTIVE_TASK     absolute path to one task folder; wins outright
#   WOS_ACTIVE_PROJECT  a projects/<name> directory; restricts the search
#
# With neither set, a single active task is unambiguous and still works. More than
# one is ambiguous, and the hook declines rather than guessing, because guessing
# costs context on the wrong task and, on stop, writes state into it.
search_root="$tasks_root"
if [[ -n "${WOS_ACTIVE_PROJECT:-}" ]]; then
  if [[ -d "$tasks_root/${WOS_ACTIVE_PROJECT}" ]]; then
    search_root="$tasks_root/${WOS_ACTIVE_PROJECT}"
  else
    # A scope that does not resolve must NOT widen back to the whole tree. Silently
    # falling back is how a typo in one variable restores the exact behavior the
    # scope was added to prevent, and the output would look like it had worked.
    [[ "$mode" == "start" ]] && echo "session-continuity: WOS_ACTIVE_PROJECT names '${WOS_ACTIVE_PROJECT}', which is not a directory under $tasks_root; standing down rather than searching the whole tree."
    exit 0
  fi
fi

active_state=""
active_mtime=0
active_count=0
if [[ -n "${WOS_ACTIVE_TASK:-}" && -f "${WOS_ACTIVE_TASK%/}/TASK_STATE.md" ]]; then
  active_state="${WOS_ACTIVE_TASK%/}/TASK_STATE.md"
  active_count=1
else
  while IFS= read -r ts_file; do
    [[ -n "$ts_file" ]] || continue
    active_count=$((active_count + 1))
    m="$(mtime "$ts_file")"
    if [[ "$m" -ge "$active_mtime" ]]; then
      active_mtime="$m"
      active_state="$ts_file"
    fi
  done < <(find "$search_root" -type f -path '*/active/*/TASK_STATE.md' 2>/dev/null)
fi

if [[ -z "$active_state" ]]; then
  # No active task. Stay quiet on stop; a light note on start is enough.
  [[ "$mode" == "start" ]] && echo "session-continuity: no active Fhorja task under $search_root."
  exit 0
fi

if [[ "$active_count" -gt 1 ]]; then
  # Ambiguous. One line on start naming the fix, nothing at all on stop: an
  # unwanted sidecar write into someone else's task is the harm worth avoiding,
  # and 20 lines about the wrong task is the cost worth avoiding.
  if [[ "$mode" == "start" ]]; then
    echo "session-continuity: $active_count active tasks under $search_root, so the task in hand is ambiguous and this hook is standing down. Set WOS_ACTIVE_PROJECT (a projects/<name> directory) or WOS_ACTIVE_TASK (a task folder) to enable it."
  fi
  exit 0
fi

task_dir="$(dirname "$active_state")"
sidecar_dir="$task_dir/.wos"
sidecar="$sidecar_dir/SESSION_CONTINUITY.json"

# ISO-8601 UTC with millisecond sentinel (matches the substrate log convention).
now_iso="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"

# ---------------------------------------------------------------------------
# 4a. stop: write the bounded continuity marker (sidecar only)
# ---------------------------------------------------------------------------
if [[ "$mode" == "stop" ]]; then
  mkdir -p "$sidecar_dir"
  session_id="$(json_field session_id)"
  tmp="$(mktemp)"
  trap 'rm -f "$tmp"' EXIT
  jq -nc \
    --arg ts "$now_iso" --arg sid "$session_id" \
    --arg task "$(basename "$task_dir")" \
    '{last_session_end:$ts, last_session_id:(if $sid=="" then null else $sid end), task:$task, note:"written by session-continuity-hook on SessionStop; advisory marker, not authoritative state"}' \
    > "$tmp"
  # No-op-if-unchanged on the non-timestamp payload: only rewrite when the task
  # or session id changed, or the sidecar is absent. This keeps churn down while
  # still recording that a session ended.
  if [[ -f "$sidecar" ]] \
    && [[ "$(jq -r '.task // ""' "$sidecar" 2>/dev/null)" == "$(jq -r '.task // ""' "$tmp")" ]] \
    && [[ "$(jq -r '.last_session_id // ""' "$sidecar" 2>/dev/null)" == "$(jq -r '.last_session_id // ""' "$tmp")" ]]; then
    # Refresh only the timestamp in place so the staleness check still works.
    # If the existing sidecar is unreadable JSON, replace it wholesale instead.
    if updated="$(jq --arg ts "$now_iso" '.last_session_end=$ts' "$sidecar" 2>/dev/null)"; then
      printf '%s\n' "$updated" > "$sidecar"
    else
      mv "$tmp" "$sidecar"
    fi
  else
    mv "$tmp" "$sidecar"
  fi
  echo "session-continuity: marked session end for $(basename "$task_dir")."
  exit 0
fi

# ---------------------------------------------------------------------------
# 4b. start: surface resume context + a staleness nudge
# ---------------------------------------------------------------------------
# Extract a single section's body from TASK_STATE.md (between '## H' and next '## ').
section_body() { # header-text
  awk -v h="## $1" '
    $0 == h        { f=1; next }
    /^## / && f    { exit }
    f              { print }
  ' "$active_state"
}

if [[ "$active_count" -gt 1 ]]; then
  echo "session-continuity: $active_count active tasks found; showing the most recently touched."
fi

echo "session-continuity: resuming $(basename "$task_dir")"
resume="$(section_body 'Resume notes' | sed '/^[[:space:]]*$/d')"
nextstep="$(section_body 'Recommended next step' | sed '/^[[:space:]]*$/d')"
[[ -n "$resume" ]] && { echo "--- Resume notes ---"; printf '%s\n' "$resume"; }
[[ -n "$nextstep" ]] && { echo "--- Recommended next step ---"; printf '%s\n' "$nextstep"; }

# Staleness: TASK_STATE.md not updated since the last recorded session end.
if [[ -f "$sidecar" ]]; then
  last_end="$(jq -r '.last_session_end // empty' "$sidecar" 2>/dev/null || true)"
  if [[ -n "$last_end" ]]; then
    # Compare TASK_STATE mtime (epoch) to last_session_end (epoch).
    end_epoch="$(date -u -j -f %Y-%m-%dT%H:%M:%S.000Z "$last_end" +%s 2>/dev/null \
      || date -u -d "$last_end" +%s 2>/dev/null || echo 0)"
    state_epoch="$(mtime "$active_state")"
    if [[ "$end_epoch" -gt 0 && "$state_epoch" -le "$end_epoch" ]]; then
      echo "--- nudge ---"
      echo "TASK_STATE.md has not changed since the last session ended ($last_end)."
      echo "Run sync-task-state to capture what happened before you continue."
    fi
  fi
fi

exit 0
