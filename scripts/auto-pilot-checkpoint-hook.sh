#!/usr/bin/env bash
# auto-pilot-checkpoint-hook.sh - Stop hook tracking consecutive auto-pilot turns
#
# Per learnings 2026-06-04 (pilot-repo session F1): 22 consecutive slice executions
# with 1 user-typed message indicate maximal paste-relay -- valuable throughput but risk
# of cumulative drift without checkpoint.
#
# Increments a counter on every Stop event. The companion UserPromptSubmit hook resets
# the counter when the user types a non-slash-command prompt (i.e., they checked in
# manually). When the counter crosses thresholds, this hook emits a warning suggesting
# /where-we-at to anchor the session.
#
# Non-blocking: emits to stderr, exits 0.

set -euo pipefail

# Discard stdin (Stop event payload is just {stop_reason})
cat > /dev/null

STATE_DIR="$HOME/.claude/wos-state"
STATE_FILE="$STATE_DIR/auto-pilot.json"
WARN_THRESHOLD=10
URGENT_THRESHOLD=15

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

# Emit warning only when threshold is crossed (not on every subsequent turn)
if [[ "$new" -eq "$WARN_THRESHOLD" ]]; then
  cat >&2 <<EOF
⚠  auto-pilot: $new consecutive turns without user-typed checkpoint.
   Cumulative drift risk grows with each auto-pilot slice. Consider running /where-we-at to anchor session state.
EOF
elif [[ "$new" -eq "$URGENT_THRESHOLD" ]]; then
  cat >&2 <<EOF
⚠  auto-pilot URGENT: $new consecutive turns without user-typed checkpoint.
   Strongly recommend /where-we-at before continuing -- 22 slices in one auto-pilot run is the empirical ceiling (pilot-repo 2026-06-04). Past 15, drift becomes hard to detect.
EOF
fi

exit 0
