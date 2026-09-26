#!/usr/bin/env bash
# auto-pilot-checkpoint-hook.sh - Stop hook recording consecutive turns
#
# Increments a counter on every Stop event. The companion UserPromptSubmit hook resets
# the counter when the user types a non-slash-command prompt (i.e., they checked in
# manually). At the thresholds below the hook prints the streak length and nothing else.
#
# The thresholds were 10 and 15 and the message recommended running a Fhorja command.
# Both came from a 2026-06-04 learning (pilot-repo session F1, 22 consecutive slice
# executions behind 1 user-typed message) taken when every turn was typed by a human, so
# a long streak was an anomaly. Under an automatic chain a long streak is the normal case,
# which made the old numbers fire constantly and the old message a stop injected by the
# harness at the exact moment the handoff is emitted. The counter still records the streak;
# it no longer recommends anything.
#
# Non-blocking: emits to stderr, exits 0.

set -euo pipefail

# Discard stdin (Stop event payload is just {stop_reason})
cat > /dev/null

# Counter lives in the active profile's config dir, so parallel Claude Code
# profiles each track their own auto-pilot streak.
STATE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/wos-state"
STATE_FILE="$STATE_DIR/auto-pilot.json"
# First report, then one report every REARM_INTERVAL turns past it. Both sit well above
# the old 10 and 15, because a continuous chain reaches those numbers in ordinary work.
REPORT_THRESHOLD=50
REARM_INTERVAL=25

mkdir -p "$STATE_DIR"

# Read current state (initialize if missing)
if [[ ! -f "$STATE_FILE" ]]; then
  echo '{"slice_count": 0}' > "$STATE_FILE"
fi

current=$(jq -r '.slice_count // 0' "$STATE_FILE" 2>/dev/null || echo 0)
[[ -z "$current" ]] && current=0
new=$((current + 1))

# Persist
jq --argjson n "$new" '.slice_count = $n' "$STATE_FILE" > "${STATE_FILE}.tmp" 2>/dev/null && mv "${STATE_FILE}.tmp" "$STATE_FILE"

# Report the streak once at the threshold, then every REARM_INTERVAL turns past it rather
# than going silent. One line, one number, no recommended next step.
if (( new == REPORT_THRESHOLD )) \
  || (( new > REPORT_THRESHOLD && (new - REPORT_THRESHOLD) % REARM_INTERVAL == 0 )); then
  cat >&2 <<EOF
auto-pilot: $new consecutive turns since the last user-typed prompt.
EOF
fi

exit 0
