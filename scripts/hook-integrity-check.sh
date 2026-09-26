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
baseline="$proj/.claude/hooks-baseline.json"

# Claude Code resolves hooks from three files, and tampering only has to land on
# one of them. Watching the project file alone leaves the user-level surface
# unchecked, which is the one that reaches every session in every repository, so
# a guard that reads only the project file reports clean while the broadest
# surface goes uninspected.
surfaces=(
  "$proj/.claude/settings.json"
  "$proj/.claude/settings.local.json"
  "$HOME/.claude/settings.json"
)

[[ -f "$baseline" ]] || exit 0          # not opted in; stay inert
command -v jq >/dev/null 2>&1 || exit 0 # jq is the only dependency; degrade silently

# Machine-specific prefixes are normalized on BOTH sides before comparing. A
# baseline that stores absolute paths only matches the machine that wrote it, so
# every other clone would see its own legitimate hooks as unexpected and learn to
# ignore the warning. Both placeholders are also what makes the file committable.
# `proj` may be a relative "."; resolve it first, because substituting a bare dot
# would rewrite every character in the string.
projabs="$(cd "$proj" 2>/dev/null && pwd || true)"
normalize() {
  if [[ -n "$projabs" ]]; then
    sed -e "s|${projabs}|\$CLAUDE_PROJECT_DIR|g" -e "s|${HOME}|~|g"
  else
    sed -e "s|${HOME}|~|g"
  fi
}

# ---------------------------------------------------------------------------
# 4. Read the baseline allow-list
# ---------------------------------------------------------------------------
# Baseline accepts either a bare JSON array or an object with an "allowed" array.
allowed="$(jq -r 'if type=="array" then .[] else (.allowed // [])[] end' "$baseline" 2>/dev/null | normalize || true)"

# ---------------------------------------------------------------------------
# 5. Diff every surface: any live command not in the allow-list is unexpected
# ---------------------------------------------------------------------------
unexpected=""
missing=""
for settings in "${surfaces[@]}"; do
  [[ -f "$settings" ]] || continue
  # Every object carrying a "command" key anywhere under the file (covers all
  # event arrays: PostToolUse, SessionStart, Stop, etc.).
  live="$(jq -r '[.. | objects | select(has("command")) | .command] | sort | unique[]' "$settings" 2>/dev/null | normalize || true)"
  [[ -z "$live" ]] && continue
  while IFS= read -r cmd; do
    [[ -n "$cmd" ]] || continue
    if ! printf '%s\n' "$allowed" | grep -Fxq -- "$cmd"; then
      unexpected+="  - [${settings/#$HOME/~}] ${cmd}"$'\n'
    fi
    # A hook whose script no longer exists fails SILENTLY: the harness logs it and
    # the session continues, so a guard that only checks the allow-list reports
    # clean while the hook has stopped running. This is the ordinary outcome of
    # moving or renaming a repository that user-level hooks point into by absolute
    # path, which is how they are usually wired.
    # Expand the variables a hook command legitimately uses BEFORE extracting the
    # path. Matching the raw string instead reports `$HOME/x.sh` as missing,
    # because the regex lands on the `/` after the variable and tests a path that
    # was never meant to be absolute. That false positive is worse than no check:
    # a guard that cries wolf on a healthy config teaches the reader to ignore it.
    # `cmd` arrives ALREADY normalized (step 4 rewrote $HOME to ~ and the project
    # dir to $CLAUDE_PROJECT_DIR), so the tilde must be expanded wherever it sits,
    # including inside quotes as in `[ -f '~/x/y.sh' ]`. Anchoring on a leading
    # space instead leaves the tilde in place, the regex then matches from the
    # slash AFTER it, and a healthy absolute path is reported missing.
    expanded="${cmd//\~\//$HOME/}"
    expanded="${expanded//\$HOME/$HOME}"
    expanded="${expanded//\$\{HOME\}/$HOME}"
    expanded="${expanded//\$CLAUDE_PROJECT_DIR/${projabs:-$proj}}"
    expanded="${expanded//\$\{CLAUDE_PROJECT_DIR\}/${projabs:-$proj}}"
    script_path="$(printf '%s' "$expanded" | grep -oE '/[^ "'"'"']*\.(sh|py|js|ts)' | head -1)"
    if [[ -n "$script_path" && ! -e "$script_path" ]]; then
      missing+="  - [${settings/#$HOME/~}] ${script_path/#$HOME/~}"$'\n'
    fi
  done <<< "$live"
done

if [[ -n "$unexpected" ]]; then
  echo "hook-integrity-check: WARNING -- hook command(s) are not in .claude/hooks-baseline.json:"
  printf '%s' "$unexpected"
  echo "If you added these on purpose, refresh the baseline (see templates/hook-integrity-check.template.md)."
  echo "If you did not, inspect them now: a hook runs an arbitrary command on every session."
fi

if [[ -n "$missing" ]]; then
  echo "hook-integrity-check: WARNING -- hook script(s) wired but not present on disk:"
  printf '%s' "$missing"
  echo "These hooks are not running. A wired path that no longer resolves fails quietly,"
  echo "so the guard reports it rather than leaving the gap to be noticed later."
fi

exit 0
