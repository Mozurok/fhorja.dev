#!/usr/bin/env bash
# hook-integrity-check.sh - Claude Code SessionStart hook (advisory).
#
# Diffs the live .claude/settings.json hook command strings against a committed
# .claude/hooks-baseline.json allow-list and warns on any hook command that is
# not in the baseline. This catches an unexpected hook added to settings.json
# (a config-tamper / supply-chain signal): a hook runs an arbitrary command on
# every session, which the pre-install skill-vet check (ADR-0046) cannot see
# because it inspects a candidate skill, not the host's live hook wiring.
#
# Posture: advisory and non-blocking. It ALWAYS exits 0, prints to stdout, and
# stays silent when no baseline exists (so it is inert until a repo opts in).
# This mirrors session-continuity-hook.sh; the why for exit-0-always is that a
# security NUDGE must never itself break a session or escalate into agent action.
#
# Mode: acts only on SessionStart (resolved from the hook JSON hook_event_name,
# or from a "start" CLI arg for manual testing). Any other event is a no-op.
#
# Stdin: optional Claude Code hook JSON (hook_event_name, session_id).

# No `set -e`: advisory hook, must always exit 0.
set -uo pipefail

# ---------------------------------------------------------------------------
# 1. Read optional hook JSON from stdin (non-fatal if empty / not JSON)
# ---------------------------------------------------------------------------
input=""
if [[ ! -t 0 ]]; then
  while IFS= read -r -t 1 _line; do
    input+="$_line"$'\n'
  done || true
fi

json_field() { # field-name -> value or empty
  [[ -z "$input" ]] && { printf ''; return; }
  printf '%s' "$input" | jq -r ".$1 // empty" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# 2. Resolve mode; act only on SessionStart
# ---------------------------------------------------------------------------
mode="${1:-}"
if [[ -z "$mode" ]]; then
  case "$(json_field hook_event_name)" in
    SessionStart) mode="start" ;;
    *) mode="" ;;
  esac
fi
# With no stdin and no arg (manual run), default to start so the check is testable.
[[ -z "$mode" && -z "$input" ]] && mode="start"
[[ "$mode" == "start" ]] || exit 0

# ---------------------------------------------------------------------------
# 3. Locate settings + baseline; bail quietly when prerequisites are absent
# ---------------------------------------------------------------------------
proj="${CLAUDE_PROJECT_DIR:-.}"
settings="$proj/.claude/settings.json"
baseline="$proj/.claude/hooks-baseline.json"

[[ -f "$baseline" ]] || exit 0          # not opted in; stay inert
[[ -f "$settings" ]] || exit 0          # nothing to compare against
command -v jq >/dev/null 2>&1 || exit 0 # jq is the only dependency; degrade silently

# ---------------------------------------------------------------------------
# 4. Extract live hook command strings and the baseline allow-list
# ---------------------------------------------------------------------------
# Every object carrying a "command" key anywhere under settings.json (covers all
# event arrays: PostToolUse, SessionStart, Stop, etc.).
live="$(jq -r '[.. | objects | select(has("command")) | .command] | sort | unique[]' "$settings" 2>/dev/null || true)"
[[ -z "$live" ]] && exit 0  # no hooks wired; nothing to flag

# Baseline accepts either a bare JSON array or an object with an "allowed" array.
allowed="$(jq -r 'if type=="array" then .[] else (.allowed // [])[] end' "$baseline" 2>/dev/null || true)"

# ---------------------------------------------------------------------------
# 5. Diff: any live command not present verbatim in the allow-list is unexpected
# ---------------------------------------------------------------------------
unexpected=""
while IFS= read -r cmd; do
  [[ -n "$cmd" ]] || continue
  if ! printf '%s\n' "$allowed" | grep -Fxq -- "$cmd"; then
    unexpected+="  - ${cmd}"$'\n'
  fi
done <<< "$live"

if [[ -n "$unexpected" ]]; then
  echo "hook-integrity-check: WARNING -- hook command(s) in .claude/settings.json are not in .claude/hooks-baseline.json:"
  printf '%s' "$unexpected"
  echo "If you added these on purpose, refresh the baseline (see templates/hook-integrity-check.template.md)."
  echo "If you did not, inspect them now: a hook runs an arbitrary command on every session."
fi

exit 0
