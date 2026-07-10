#!/usr/bin/env bash
# edit-drift-detector-hook.sh - Claude Code PostToolUse hook detecting common Edit failure patterns
#
# Per learnings 2026-06-04 (pilot-repo session): 3 of 4 tool errors were Edit failures of
# two distinct classes -- both detectable mechanically and worth surfacing as warnings so the
# agent can self-correct on the next turn.
#
# I.1 (content drift): "String to replace not found in file." Likely cause: a prior Edit in the
#                      same turn already changed the file; the agent's cached view is stale.
# I.2 (missing read):  "File has not been read yet." The agent dispatched Edit/Write without a
#                      precedent Read in the same turn for a file Claude Code thinks needs it.
#
# Non-blocking: PostToolUse cannot block (the tool already ran/failed). Warning to stderr only.

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Parse stdin (PostToolUse payload)
# ---------------------------------------------------------------------------
input="$(cat)"

if [[ -z "$input" ]]; then
  exit 0
fi

tool_name="$(echo "$input" | jq -r '.tool_name // empty' 2>/dev/null || true)"

# Only inspect Edit/Write/NotebookEdit; ignore everything else.
case "$tool_name" in
  Edit|Write|NotebookEdit) ;;
  *) exit 0 ;;
esac

file_path="$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)"

# ---------------------------------------------------------------------------
# 2. Look for failure signature in various possible payload shapes
# ---------------------------------------------------------------------------
# Claude Code may surface errors under several keys depending on version.
err="$(echo "$input" | jq -r '
  (.tool_response.error // empty) //
  (.tool_response.message // empty) //
  (.error // empty) //
  (.tool_response.content[0].text // empty) //
  empty
' 2>/dev/null || true)"

if [[ -z "$err" ]]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# 3. Match known failure patterns and emit guidance
# ---------------------------------------------------------------------------
if echo "$err" | grep -q "String to replace not found"; then
  cat >&2 <<EOF
⚠  edit-drift (content): $tool_name on $file_path failed with "String to replace not found".
   Likely cause: a prior Edit in this turn already changed the file, so the cached content snapshot is stale.
   Fix: Read the file again with Read tool before retrying Edit. Match the new content shape.
EOF
  exit 0
fi

if echo "$err" | grep -q "File has not been read yet"; then
  cat >&2 <<EOF
⚠  edit-drift (precedent): $tool_name on $file_path failed with "File has not been read yet".
   Fix: Use Read tool on $file_path before Edit/Write. This is required for existing files that have not been Read in this turn.
EOF
  exit 0
fi

# Other Edit/Write failures: no specific guidance. Exit silently.
exit 0
