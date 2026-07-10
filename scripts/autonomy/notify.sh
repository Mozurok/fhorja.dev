#!/usr/bin/env bash
# notify.sh -- Fhorja autonomy track presence-gated desktop notifier (D-3 of
# projects/bmazurok__my-work-tasks/active/2026-07-03_background-autonomous-run/DECISIONS.md).
#
# The canonical completion/escalation signal for a background autonomous run
# is the runs-feed file plus the board (ADR-0080) and the contract-mandated
# TASK_STATE.md writes. This notifier is a best-effort local extra layered on
# top, never load-bearing: it must not depend on any hosted infrastructure and
# must never block or fail the caller.
#
# Presence-gated (ADR-0027 pattern): tries terminal-notifier when it is on
# PATH, else osascript's "display notification" when that is on PATH, else
# no-ops. No configuration, no network, no dependencies beyond what the
# machine already has.
#
# Usage:  notify.sh <title> <message>
# Output: none on success or on absence of a notifier; whatever the chosen
#         notifier prints is discarded so the call stays silent either way.
# Exit:   always 0 (best-effort; safe to call from a backgrounded process).

set -uo pipefail

title="${1:-Fhorja}"
message="${2:-}"

if command -v terminal-notifier >/dev/null 2>&1; then
  terminal-notifier -title "$title" -message "$message" >/dev/null 2>&1
elif command -v osascript >/dev/null 2>&1; then
  # Escape backslashes then double quotes so the title/message can't break
  # out of the AppleScript string literal.
  esc_title="${title//\\/\\\\}"
  esc_title="${esc_title//\"/\\\"}"
  esc_message="${message//\\/\\\\}"
  esc_message="${esc_message//\"/\\\"}"
  osascript -e "display notification \"${esc_message}\" with title \"${esc_title}\"" >/dev/null 2>&1
fi
# No notifier on PATH: fall through silently, no output, no error.

exit 0
