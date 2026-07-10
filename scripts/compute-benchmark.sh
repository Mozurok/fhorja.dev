#!/usr/bin/env bash
# compute-benchmark.sh - Aggregate iteration evals into benchmark.json, per K.7 (joint J.11).
#
# Per K.7 (joint J.11), Epic K v2.1 2026-06-04.
# Format: agentskills.io/skill-creation/evaluating-skills canonical.
#
# Reads:
#   evals/workspace/<skill-name>-workspace/iteration-<N>/<eval-id>/
#     {with_skill,without_skill}/{timing.json,grading.json}
#
# Writes:
#   evals/workspace/<skill-name>-workspace/iteration-<N>/benchmark.json
#
# Usage:
#   bash scripts/compute-benchmark.sh <skill-name> --iteration <N>
#   bash scripts/compute-benchmark.sh <skill-name>                    # use latest iteration

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKILL_NAME="${1:-}"
shift 2>/dev/null || true

if [[ -z "$SKILL_NAME" ]]; then
  echo "ERROR: skill name required." >&2
  echo "Usage: bash scripts/compute-benchmark.sh <skill-name> [--iteration <N>]" >&2
  exit 1
fi

ITERATION=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --iteration) ITERATION="$2"; shift 2 ;;
    *) echo "ERROR: unknown arg $1" >&2; exit 1 ;;
  esac
done

WORKSPACE_BASE="$REPO_ROOT/evals/workspace/${SKILL_NAME}-workspace"
if [[ ! -d "$WORKSPACE_BASE" ]]; then
  echo "ERROR: workspace not found: $WORKSPACE_BASE" >&2
  echo "  Run run-skill-evals.sh first." >&2
  exit 1
fi

if [[ -z "$ITERATION" ]]; then
  ITERATION=$(ls -d "$WORKSPACE_BASE"/iteration-* 2>/dev/null | sed 's|.*iteration-||' | sort -n | tail -1)
  if [[ -z "$ITERATION" ]]; then
    echo "ERROR: no iteration- dirs found in $WORKSPACE_BASE" >&2
    exit 1
  fi
fi

ITERATION_DIR="$WORKSPACE_BASE/iteration-$ITERATION"
if [[ ! -d "$ITERATION_DIR" ]]; then
  echo "ERROR: iteration dir not found: $ITERATION_DIR" >&2
  exit 1
fi

echo "skill: $SKILL_NAME"
echo "iteration: $ITERATION"
echo "dir: $ITERATION_DIR"

# Aggregate per-eval results
AGG_FILE=$(mktemp)
trap 'rm -f "$AGG_FILE"' EXIT

echo "[]" > "$AGG_FILE"

for EVAL_DIR in "$ITERATION_DIR"/*/; do
  [[ -d "$EVAL_DIR" ]] || continue
  EID=$(basename "$EVAL_DIR")
  [[ "$EID" == "benchmark.json" ]] && continue

  WS_TIMING="$EVAL_DIR/without_skill/timing.json"
  WS_GRADE="$EVAL_DIR/without_skill/grading.json"
  WK_TIMING="$EVAL_DIR/with_skill/timing.json"
  WK_GRADE="$EVAL_DIR/with_skill/grading.json"

  for f in "$WS_TIMING" "$WS_GRADE" "$WK_TIMING" "$WK_GRADE"; do
    if [[ ! -f "$f" ]]; then
      echo "  skip $EID: missing $f" >&2
      continue 2
    fi
  done

  # Build per-eval record
  RECORD=$(jq -n \
    --arg id "$EID" \
    --slurpfile ws_t "$WS_TIMING" \
    --slurpfile ws_g "$WS_GRADE" \
    --slurpfile wk_t "$WK_TIMING" \
    --slurpfile wk_g "$WK_GRADE" \
    '{
      id: $id,
      without_skill: {
        passed: $ws_g[0].passed,
        duration_seconds: $ws_t[0].duration_seconds,
        tokens_input: $ws_t[0].tokens_input,
        tokens_output: $ws_t[0].tokens_output
      },
      with_skill: {
        passed: $wk_g[0].passed,
        duration_seconds: $wk_t[0].duration_seconds,
        tokens_input: $wk_t[0].tokens_input,
        tokens_output: $wk_t[0].tokens_output
      }
    }')

  jq --argjson rec "$RECORD" '. + [$rec]' "$AGG_FILE" > "$AGG_FILE.tmp" && mv "$AGG_FILE.tmp" "$AGG_FILE"
done

# Compute aggregate metrics + deltas
BENCHMARK_JSON="$ITERATION_DIR/benchmark.json"

jq --arg skill "$SKILL_NAME" --arg iter "$ITERATION" '
  {
    skill_name: $skill,
    iteration: ($iter | tonumber),
    eval_count: length,
    results: .,
    summary: {
      without_skill: {
        pass_rate: (if length == 0 then 0 else ([.[].without_skill.passed | select(. == true)] | length) / length end),
        total_duration_seconds: ([.[].without_skill.duration_seconds | select(. != null)] | add // 0),
        total_tokens_input: ([.[].without_skill.tokens_input | select(. != null)] | add // 0),
        total_tokens_output: ([.[].without_skill.tokens_output | select(. != null)] | add // 0)
      },
      with_skill: {
        pass_rate: (if length == 0 then 0 else ([.[].with_skill.passed | select(. == true)] | length) / length end),
        total_duration_seconds: ([.[].with_skill.duration_seconds | select(. != null)] | add // 0),
        total_tokens_input: ([.[].with_skill.tokens_input | select(. != null)] | add // 0),
        total_tokens_output: ([.[].with_skill.tokens_output | select(. != null)] | add // 0)
      }
    }
  } |
  .summary.delta = {
    pass_rate: (.summary.with_skill.pass_rate - .summary.without_skill.pass_rate),
    duration_seconds: (.summary.with_skill.total_duration_seconds - .summary.without_skill.total_duration_seconds),
    tokens_input: (.summary.with_skill.total_tokens_input - .summary.without_skill.total_tokens_input),
    tokens_output: (.summary.with_skill.total_tokens_output - .summary.without_skill.total_tokens_output)
  }
' "$AGG_FILE" > "$BENCHMARK_JSON"

echo "benchmark: $BENCHMARK_JSON"
echo
jq '.summary' "$BENCHMARK_JSON"
