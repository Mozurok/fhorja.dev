#!/usr/bin/env bash
# audit-command-usage.sh - Per-command usage audit (one-pass, optimized)
#
# For each command in commands/*.md, counts mentions across:
#   - ~/.claude/projects/<project>/*.jsonl (last LOOKBACK_DAYS)
#   - git log of Fhorja repo (commit messages)
#   - projects/*/active|archive/*/TASK_STATE.md mentions
#
# Optimization: instead of N greps per file (slow for 600+ JSONL × 56 commands),
# we do ONE pass per file extracting all command mentions, then tally.
#
# Output: CSV at _internal/command-usage-audit-2026-06.csv
# Per Epic C.1 of Fhorja improvement plan 2026-06-03.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT="${1:-${REPO_ROOT}/_internal/command-usage-audit-2026-06.csv}"
LOOKBACK_DAYS="${2:-60}"
PROJECTS_DIR="$HOME/.claude/projects"

# Enumerate commands; build a regex alternation
COMMAND_NAMES=()
while IFS= read -r f; do
  COMMAND_NAMES+=("$(basename "$f" .md)")
done < <(find "${REPO_ROOT}/commands" -maxdepth 1 -name "*.md" -type f | sort)

TOTAL_CMDS=${#COMMAND_NAMES[@]}
echo "Auditing $TOTAL_CMDS commands, last $LOOKBACK_DAYS days, one-pass scan." >&2

# Single regex alternation for all command names (used per file)
CMD_ALT="$(IFS='|'; echo "${COMMAND_NAMES[*]}")"

# Phase 1: transcripts pass (1 grep -hoE per file, then tally)
declare -A TRANSCRIPT_COUNT
for cmd in "${COMMAND_NAMES[@]}"; do
  TRANSCRIPT_COUNT[$cmd]=0
done

if [[ -d "$PROJECTS_DIR" ]]; then
  echo "Scanning transcripts..." >&2
  # For each JSONL, extract all command name occurrences in one grep -oE pass.
  # Match /<cmd> or @commands/<cmd>.md or command-name>/<cmd>< patterns.
  while IFS= read -r jsonl; do
    # Count one mention per file per command (presence, not multi-occurrence)
    matches=$(grep -hoE "/(${CMD_ALT})\b|@commands/(${CMD_ALT})\.md|command-name>/(${CMD_ALT})<" "$jsonl" 2>/dev/null | sed -E 's|^/|::|; s|^@commands/|::|; s|\.md$||; s|^command-name>/|::|; s|<$||' | sort -u || true)
    while IFS= read -r m; do
      cmd_match="${m##*::}"
      [[ -z "$cmd_match" ]] && continue
      if [[ -n "${TRANSCRIPT_COUNT[$cmd_match]+isset}" ]]; then
        TRANSCRIPT_COUNT[$cmd_match]=$((TRANSCRIPT_COUNT[$cmd_match] + 1))
      fi
    done <<< "$matches"
  done < <(find "$PROJECTS_DIR" -name "*.jsonl" -type f -mtime -"$LOOKBACK_DAYS" 2>/dev/null)
fi

# Phase 2: git log pass (one shot)
echo "Scanning git log..." >&2
declare -A GIT_COUNT
for cmd in "${COMMAND_NAMES[@]}"; do
  GIT_COUNT[$cmd]=0
done
if git -C "${REPO_ROOT}" rev-parse --git-dir >/dev/null 2>&1; then
  git_log_text="$(git -C "${REPO_ROOT}" log --oneline --all --since="${LOOKBACK_DAYS}.days.ago" 2>/dev/null || true)"
  for cmd in "${COMMAND_NAMES[@]}"; do
    n=$(echo "$git_log_text" | grep -cE "${cmd}" 2>/dev/null || echo 0)
    n=$(echo "$n" | head -1 | tr -dc '0-9')
    GIT_COUNT[$cmd]="${n:-0}"
  done
fi

# Phase 3: TASK_STATE.md mentions
echo "Scanning TASK_STATE files..." >&2
declare -A TS_COUNT
for cmd in "${COMMAND_NAMES[@]}"; do
  TS_COUNT[$cmd]=0
done

TASK_STATE_FILES=()
while IFS= read -r f; do
  TASK_STATE_FILES+=("$f")
done < <(find "${REPO_ROOT}/projects" -name "TASK_STATE.md" -type f 2>/dev/null)

if [[ ${#TASK_STATE_FILES[@]} -gt 0 ]]; then
  for ts in "${TASK_STATE_FILES[@]}"; do
    matches=$(grep -hoE "${CMD_ALT}" "$ts" 2>/dev/null | sort -u || true)
    while IFS= read -r m; do
      [[ -z "$m" ]] && continue
      if [[ -n "${TS_COUNT[$m]+isset}" ]]; then
        TS_COUNT[$m]=$((TS_COUNT[$m] + 1))
      fi
    done <<< "$matches"
  done
fi

# Phase 4: emit CSV
echo "command,transcripts_mentions,git_log_mentions,task_state_mentions,total,classification_hint" > "$OUTPUT"
for cmd in "${COMMAND_NAMES[@]}"; do
  t="${TRANSCRIPT_COUNT[$cmd]:-0}"
  g="${GIT_COUNT[$cmd]:-0}"
  ts="${TS_COUNT[$cmd]:-0}"
  total=$((t + g + ts))
  if [[ $total -ge 10 ]]; then
    hint="ACTIVE"
  elif [[ $total -ge 3 ]]; then
    hint="DORMANT"
  elif [[ $total -eq 0 ]]; then
    hint="NEVER_USED"
  else
    hint="LOW_USE"
  fi
  echo "$cmd,$t,$g,$ts,$total,$hint" >> "$OUTPUT"
done

{
  echo ""
  echo "Done: scanned $TOTAL_CMDS commands."
  echo "  output: $OUTPUT"
  echo ""
  echo "Classification distribution:"
  awk -F, 'NR>1 {print $6}' "$OUTPUT" | sort | uniq -c | sort -rn | awk '{printf "  %-15s %s\n", $2, $1}'
  echo ""
  echo "Top 10 by total mentions:"
  sort -t, -k5 -nr "$OUTPUT" | head -10 | awk -F, '{printf "  %-35s total=%-4s transcripts=%-4s git=%-4s task_state=%s\n", $1, $5, $2, $3, $4}'
  echo ""
  echo "NEVER_USED commands (zero mentions):"
  awk -F, 'NR>1 && $5==0 {print "  -",$1}' "$OUTPUT"
} >&2
