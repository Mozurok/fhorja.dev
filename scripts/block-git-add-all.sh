#!/usr/bin/env bash
# block-git-add-all.sh - Claude Code PreToolUse hook to block unsafe git add patterns
#
# Blocks any Bash command containing `git add -A`, `git add --all`, `git add .`,
# `git add ./`, or `git add *` (with optional cd prefix or && chaining).
#
# Fhorja rule reference: MEMORY.md feedback_git_add_specific_files
# Incident triggering the rule: 58-file contamination on 2026-05-28
#
# Output:
#   Exit 0 + JSON to stdout with permissionDecision: "deny" when blocking
#   Exit 0 with no output when allowing
#
# Stdin: Claude Code PreToolUse JSON (contains tool_input.command for Bash)

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Parse command from stdin JSON
# ---------------------------------------------------------------------------
input="$(cat)"

# If stdin is empty (manual testing), allow
if [[ -z "$input" ]]; then
  exit 0
fi

command_str="$(echo "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"

# Not a Bash tool or missing command field; allow
if [[ -z "$command_str" ]]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# 2. Match unsafe git add patterns
# ---------------------------------------------------------------------------
# Pattern requires:
#   - Optional prefix: start-of-string OR whitespace OR "&& " (chained command)
#   - Literal: "git add" + whitespace
#   - Dangerous arg: -A | --all | . | ./ | *
#   - Followed by: whitespace OR end-of-string
#
# This avoids false positives for:
#   - git add path/to/file.txt
#   - git add --                (separator only)
#   - git add 'src/*.tsx'       (quoted glob, user-specified path)
#   - git diff --stat           (different subcommand)

if [[ "$command_str" =~ (^|[[:space:]]|\&\&[[:space:]]*)git[[:space:]]+add[[:space:]]+(-A|--all|\.|\./|\*)([[:space:]]|$) ]]; then
  jq -n '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": "Blocked per Fhorja rule: git add -A, --all, ., ./, or * not allowed. List explicit paths instead. See MEMORY.md feedback_git_add_specific_files (incident: 58-file contamination 2026-05-28)."
    }
  }'
  exit 0
fi

# ---------------------------------------------------------------------------
# 3. Default: allow
# ---------------------------------------------------------------------------
exit 0
