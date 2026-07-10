#!/usr/bin/env bash
# track-model-usage.sh - Parse Claude Code transcripts to produce model usage baseline
#
# Walks ~/.claude/projects/<project>/*.jsonl, extracts per-session: model used (mode),
# message count, tool use count, started/ended timestamps, project folder.
#
# Output: CSV at _internal/model-usage-baseline-2026-06.csv (or path passed as $1).
#
# Per ADR-0025 model selection by tier — establishes the baseline for measuring whether
# routing recommendations are being followed (B.4 of Fhorja improvement plan 2026-06-03).
#
# Usage:
#   bash scripts/track-model-usage.sh                       # default output path
#   bash scripts/track-model-usage.sh /tmp/usage.csv        # custom output
#   bash scripts/track-model-usage.sh /tmp/usage.csv 30     # custom output + lookback days (default 14)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT="${1:-${REPO_ROOT}/_internal/model-usage-baseline-2026-06.csv}"
LOOKBACK_DAYS="${2:-14}"
PROJECTS_DIR="$HOME/.claude/projects"

if [[ ! -d "$PROJECTS_DIR" ]]; then
  echo "ERROR: $PROJECTS_DIR does not exist" >&2
  exit 1
fi

# CSV header
echo "session_id,project_folder,started_at,ended_at,model_main,message_count,tool_use_count,file_bytes" > "$OUTPUT"

session_count=0
total_messages=0
total_tools=0

while IFS= read -r jsonl; do
  session_id=$(basename "$jsonl" .jsonl)
  project_folder=$(basename "$(dirname "$jsonl")")

  # Skip empty/tiny files
  file_bytes=$(wc -c < "$jsonl" | tr -d ' ')
  [[ "$file_bytes" -lt 200 ]] && continue

  # First and last timestamps (graceful failure if missing)
  started_at=$(head -1 "$jsonl" 2>/dev/null | jq -r '.timestamp // empty' 2>/dev/null || true)
  ended_at=$(tail -1 "$jsonl" 2>/dev/null | jq -r '.timestamp // empty' 2>/dev/null || true)

  # Model most used (mode across messages)
  model_main=$(grep -o '"model":"[^"]*"' "$jsonl" 2>/dev/null | sort | uniq -c | sort -rn | head -1 | sed 's/.*"model":"\([^"]*\)".*/\1/' || true)
  [[ -z "$model_main" ]] && model_main="unknown"

  # Message count (line count is a proxy for messages in JSONL)
  message_count=$(wc -l < "$jsonl" | tr -d ' ')

  # Tool use count (force single-value output; some grep versions emit per-file counts)
  tool_use_count=$(grep -c '"type":"tool_use"' "$jsonl" 2>/dev/null | head -1 | tr -d '\n ' || true)
  [[ -z "$tool_use_count" ]] && tool_use_count=0

  # Escape CSV: replace comma in timestamps (shouldn't have any) just in case
  started_at="${started_at//,/_}"
  ended_at="${ended_at//,/_}"

  echo "$session_id,$project_folder,$started_at,$ended_at,$model_main,$message_count,$tool_use_count,$file_bytes" >> "$OUTPUT"

  session_count=$((session_count + 1))
  total_messages=$((total_messages + message_count))
  total_tools=$((total_tools + tool_use_count))
done < <(find "$PROJECTS_DIR" -name "*.jsonl" -type f -mtime -"$LOOKBACK_DAYS" 2>/dev/null)

# ---------------------------------------------------------------------------
# Summary to stderr
# ---------------------------------------------------------------------------
{
  echo "track-model-usage: scanned last $LOOKBACK_DAYS days"
  echo "  sessions:       $session_count"
  echo "  total messages: $total_messages"
  echo "  total tool uses: $total_tools"
  echo "  output:         $OUTPUT"
} >&2

# Quick aggregation by model (printed to stderr)
if [[ "$session_count" -gt 0 ]]; then
  echo "" >&2
  echo "  Sessions by model_main:" >&2
  awk -F, 'NR>1 {print $5}' "$OUTPUT" | sort | uniq -c | sort -rn | awk '{printf "    %-30s %s sessions\n", $2, $1}' >&2
fi
