#!/usr/bin/env bash
# evals/scripts/run-evals.sh
#
# Walks through the eval scenarios under evals/scenarios/, printing each
# in turn so you can paste the input prompt into your AI tool of choice
# and read the response against the pass criteria.
#
# This script does NOT call any model API. The eval loop is intentional
# manual:
#   1. Print the scenario.
#   2. You copy the input prompt section into your AI tool.
#   3. You read the response against the pass criteria.
#   4. You record pass / fail in the History section of the scenario file
#      (or in your own notes).
#
# Usage:
#   ./evals/scripts/run-evals.sh                # walk through all scenarios
#   ./evals/scripts/run-evals.sh 03             # run only scenario 03
#   ./evals/scripts/run-evals.sh --list         # list scenarios; do not print bodies
#
# Exit codes:
#   0 = success
#   1 = invocation error (no scenarios found, etc.)
#   2 = unknown option

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SCENARIOS_DIR="${REPO_ROOT}/evals/scenarios"

LIST_ONLY=0
ONLY_NN=""
USE_JUDGE=0
JUDGE_TOOL=""

usage() {
  cat <<'EOF'
Usage: evals/scripts/run-evals.sh [options] [NN]

Walk through the eval scenarios under evals/scenarios/.

Options:
  --list, -l     List scenarios; do not print bodies.
  --judge        After each scenario, prompt for the model's response and
                 pipe it through evals/scripts/judge.py (OPTIONAL second
                 pass per ADR-0019; never replaces manual review).
  --tool CMD     Override the default judge tool command (default:
                 "claude code --print"). Only meaningful with --judge.
  --help, -h     Show this message.

Positional:
  NN             Run only the scenario whose filename starts with NN
                 (e.g. "03" runs evals/scenarios/03-*.md).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list|-l) LIST_ONLY=1 ;;
    --judge) USE_JUDGE=1 ;;
    --tool) shift; JUDGE_TOOL="$1" ;;
    -h|--help) usage; exit 0 ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -n "$ONLY_NN" ]]; then
        echo "Only one scenario number can be specified at a time." >&2
        exit 2
      fi
      ONLY_NN="$1"
      ;;
  esac
  shift
done

if [[ ! -d "$SCENARIOS_DIR" ]]; then
  echo "Scenarios dir not found: $SCENARIOS_DIR" >&2
  exit 1
fi

shopt -s nullglob
ALL_SCENARIOS=("$SCENARIOS_DIR"/[0-9][0-9]-*.md)
shopt -u nullglob

if [[ ${#ALL_SCENARIOS[@]} -eq 0 ]]; then
  echo "No scenarios found in $SCENARIOS_DIR" >&2
  exit 1
fi

# Filter if a specific NN was requested.
if [[ -n "$ONLY_NN" ]]; then
  shopt -s nullglob
  FILTERED=("$SCENARIOS_DIR"/"${ONLY_NN}"-*.md)
  shopt -u nullglob
  if [[ ${#FILTERED[@]} -eq 0 ]]; then
    echo "No scenario matches prefix '${ONLY_NN}-*' under $SCENARIOS_DIR" >&2
    exit 1
  fi
  ALL_SCENARIOS=("${FILTERED[@]}")
fi

if [[ "$LIST_ONLY" -eq 1 ]]; then
  echo "Eval scenarios under $SCENARIOS_DIR:"
  for f in "${ALL_SCENARIOS[@]}"; do
    name="$(basename "$f")"
    title="$(head -n1 "$f" | sed 's/^# Eval scenario //')"
    echo "  ${name%.md}  ${title}"
  done
  exit 0
fi

total=${#ALL_SCENARIOS[@]}
i=0
for f in "${ALL_SCENARIOS[@]}"; do
  i=$((i + 1))
  echo ""
  echo "================================================================================"
  echo "Scenario $i of $total: $(basename "$f")"
  echo "================================================================================"
  echo ""
  cat "$f"
  echo ""
  echo "================================================================================"
  echo ""
  if [[ $USE_JUDGE -eq 1 ]]; then
    echo ""
    echo "Paste the input prompt above into your AI tool, copy the model's response, then save it to a temporary file."
    read -r -p "Path to the response file (or empty to skip judging this scenario): " response_path
    if [[ -n "$response_path" ]]; then
      if [[ -f "$response_path" ]]; then
        echo ""
        echo "--- Judge verdict (ADR-0019; OPTIONAL second pass) ---"
        judge_args=("--scenario" "$f" "--output" "$response_path")
        if [[ -n "$JUDGE_TOOL" ]]; then
          judge_args+=("--tool" "$JUDGE_TOOL")
        fi
        python3 "${SCRIPT_DIR}/judge.py" "${judge_args[@]}" || echo "Judge failed; fall back to manual review."
        echo "--- End judge verdict ---"
      else
        echo "Response file not found: $response_path; skipping judge for this scenario."
      fi
    fi
  fi

  if [[ $i -lt $total ]]; then
    read -r -p "Paste the input prompt above into your AI tool, validate the response against the pass criteria, then press enter to continue with the next scenario (or Ctrl-C to stop). "
  else
    echo "All $total scenario(s) printed. Run again with --list to see the index, or pass NN to focus on a single scenario."
  fi
done

exit 0
