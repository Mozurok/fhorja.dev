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

usage() {
  cat <<'EOF'
Usage: evals/scripts/run-evals.sh [options] [NN]

Walk through the eval scenarios under evals/scenarios/.

Options:
  --list, -l     List scenarios; do not print bodies.
  --help, -h     Show this message.

Positional:
  NN             Run only the scenario whose filename starts with NN
                 (e.g. "03" runs evals/scenarios/03-*.md).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list|-l) LIST_ONLY=1 ;;
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

# The character class must admit a three-digit prefix. Until 2026-08-21 it was `[0-9][0-9]-`, which
# cannot match one, so the walk enumerated 99 of 135 scenarios and everything from 100- onward was
# invisible to the walk and to --list, while CLAUDE.md and evals/README.md both instruct a full walk
# before tagging a release. evals/README.md records the same drift class biting once before.
#
# Coverage and order are SEPARATE defects. Widening the class fixes coverage. Glob expansion is
# lexicographic, so it puts 100- immediately after 10-; the re-sort below fixes order. The
# structural-evals.py check `walker-covers-corpus` gates the coverage half by parsing this very
# assignment, so keep the glob inline here: moving it into a pipeline hides it from that guard.
shopt -s nullglob
ALL_SCENARIOS=("$SCENARIOS_DIR"/[0-9]*-*.md)
shopt -u nullglob

# Re-sort by the numeric prefix so the walk follows scenario order. Written as a read loop rather
# than mapfile, which bash 3.2 (the macOS system bash) does not have.
if [[ ${#ALL_SCENARIOS[@]} -gt 1 ]]; then
  _sorted=()
  while IFS= read -r _line; do
    _sorted+=("${_line#*$'\t'}")
  done < <(printf '%s\n' "${ALL_SCENARIOS[@]}" | awk -F/ '{print $NF"\t"$0}' | sort -V)
  ALL_SCENARIOS=("${_sorted[@]}")
  unset _sorted _line
fi

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
  if [[ $i -lt $total ]]; then
    read -r -p "Paste the input prompt above into your AI tool, validate the response against the pass criteria, then press enter to continue with the next scenario (or Ctrl-C to stop). "
  else
    echo "All $total scenario(s) printed. Run again with --list to see the index, or pass NN to focus on a single scenario."
  fi
done

exit 0
