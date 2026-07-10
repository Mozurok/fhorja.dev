#!/usr/bin/env bash
# auto-pilot-reset-hook.sh - UserPromptSubmit hook resetting the auto-pilot counter
#
# Companion to auto-pilot-checkpoint-hook.sh. When the user submits a prompt that is NOT
# a slash command (i.e., they typed real text), reset the consecutive-turn counter to 0.
# This means:
#   - 20 slash-command-only turns in a row -> counter climbs to 20.
#   - User types "wait, let me check something" -> counter resets to 0.
#
# Non-blocking: exits 0 always.

set -euo pipefail

input="$(cat)"
if [[ -z "$input" ]]; then
  exit 0
fi

# Get the prompt content
prompt=$(echo "$input" | jq -r '.prompt // empty' 2>/dev/null || true)

if [[ -z "$prompt" ]]; then
  exit 0
fi

# Detect if this is a slash command invocation:
# - Starts with <command-name> tag
# - Starts with <command-message>
# - Starts with /<word> on the first line
# - Is purely a command body (starts with "# <command-name>" pattern)
is_slash_command=0

if [[ "$prompt" =~ ^[[:space:]]*\<command- ]]; then
  is_slash_command=1
elif [[ "$prompt" =~ ^[[:space:]]*/[a-z-]+ ]]; then
  is_slash_command=1
elif [[ "$prompt" =~ ^#[[:space:]]+[a-z-]+ ]] && [[ "$prompt" == *"Act as"* ]]; then
  is_slash_command=1
fi

if [[ "$is_slash_command" -eq 1 ]]; then
  exit 0
fi

# User typed real text -- reset counter
STATE_DIR="$HOME/.claude/wos-state"
STATE_FILE="$STATE_DIR/auto-pilot.json"
mkdir -p "$STATE_DIR"
echo '{"slice_count": 0}' > "$STATE_FILE"

exit 0
