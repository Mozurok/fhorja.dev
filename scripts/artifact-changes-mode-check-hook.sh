#!/usr/bin/env bash
# artifact-changes-mode-check-hook.sh - Claude Code PostToolUse hook validating ADR-0001
#
# When an Edit/Write modifies a task artifact (.md inside projects/*/active/*/), this
# hook checks the `### Artifact changes` block for inconsistencies with ADR-0001
# (PROPOSED-by-default):
#
#   - permission_mode = "plan" with APPLIED tags  -> warn (should be PROPOSED)
#   - permission_mode = "agent" with PROPOSED tags -> warn (should be APPLIED)
#   - items without tag                            -> warn (missing tag)
#
# Non-blocking: PostToolUse cannot block anyway (the write already happened).
# Warnings go to stderr and are visible in the transcript for the agent to act on.
#
# Scope filter: only fires for files matching projects/*/active/*/*.md to avoid
# false positives on commands/*.md, docs/**, wos/**, templates/**, _internal/**.
#
# Per ADR-0001 (PROPOSED-by-default) + ADR-0024 (approve-proposed-idiom).

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Parse stdin (PostToolUse payload)
# ---------------------------------------------------------------------------
input="$(cat)"

if [[ -z "$input" ]]; then
  exit 0
fi

file_path="$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)"
permission_mode="$(echo "$input" | jq -r '.permission_mode // "agent"' 2>/dev/null || echo "agent")"

if [[ -z "$file_path" ]]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# 2. Scope filter — only task artifacts under projects/*/active/*/
# ---------------------------------------------------------------------------
# Quick path match; avoids spending time on non-task files
if [[ ! "$file_path" =~ /projects/[^/]+/active/[^/]+/.+\.md$ ]]; then
  exit 0
fi

# File must exist on disk (post-write); if deleted, skip
if [[ ! -f "$file_path" ]]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# 3. Extract the ### Artifact changes block (if present)
# ---------------------------------------------------------------------------
# Block starts at line matching `### Artifact changes` and ends at next H2/H3 heading
# or EOF. Use awk to extract.

block="$(awk '
  /^### Artifact changes[[:space:]]*$/ { inblock=1; next }
  inblock && /^(#|##|###)[[:space:]]/ { exit }
  inblock { print }
' "$file_path")"

if [[ -z "$block" ]]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# 4. Count tags in the block
# ---------------------------------------------------------------------------
applied_count=$(echo "$block" | grep -c -E '(\*\*APPLIED\*\*|APPLIED:|- APPLIED)' || true)
proposed_count=$(echo "$block" | grep -c -E '(\*\*PROPOSED\*\*|PROPOSED:|- PROPOSED)' || true)
skip_count=$(echo "$block" | grep -c -E '(\*\*SKIP\*\*|SKIP:|- SKIP)' || true)

# Count bullet items in the block to detect items missing tags
# A bullet is a line starting with `- ` (after optional whitespace)
item_count=$(echo "$block" | grep -c -E '^[[:space:]]*-[[:space:]]' || true)
tagged_count=$((applied_count + proposed_count + skip_count))
untagged_count=$((item_count - tagged_count))

# ---------------------------------------------------------------------------
# 5. Decide if we need to warn
# ---------------------------------------------------------------------------
warnings=""

# Mode inconsistency check
case "$permission_mode" in
  "plan"|"plan_mode"|"ask"|"acceptEdits")
    if [[ "$applied_count" -gt 0 ]]; then
      warnings+="   - permission_mode=$permission_mode but found $applied_count APPLIED tag(s); ADR-0001 expects PROPOSED in Ask/Plan modes.\n"
    fi
    ;;
  "agent"|"agent_mode"|"bypassPermissions")
    if [[ "$proposed_count" -gt 0 ]]; then
      warnings+="   - permission_mode=$permission_mode but found $proposed_count PROPOSED tag(s); ADR-0001 expects APPLIED in Agent mode (except task-init/project-bootstrap).\n"
    fi
    ;;
esac

# Untagged items check (only if block has items at all)
if [[ "$item_count" -gt 0 && "$untagged_count" -gt 0 ]]; then
  warnings+="   - $untagged_count item(s) in '### Artifact changes' lack PROPOSED/APPLIED/SKIP tag.\n"
fi

if [[ -z "$warnings" ]]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# 6. Emit warning to stderr (visible in transcript)
# ---------------------------------------------------------------------------
{
  echo "⚠  artifact-changes-mode-check: inconsistencies in $file_path"
  printf "%b" "$warnings"
  echo "   See ADR-0001 (PROPOSED-by-default) and ADR-0024 (approve-proposed-idiom)."
} >&2

exit 0
