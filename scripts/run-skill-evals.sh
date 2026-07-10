#!/usr/bin/env bash
# run-skill-evals.sh - Run baseline + with_skill evals for a skill, per K.7 eval discipline
#
# Per K.7 (joint J.11), Epic K v2.1 2026-06-04.
# Format: agentskills.io/skill-creation/evaluating-skills canonical.
#
# Reads:
#   evals/skill-evals/<skill-name>/evals.json  -- eval scenarios (canonical location for K.7+)
#   OR: commands/<skill-name>/evals/evals.json -- when skill is folder-shaped (K.3+)
#   OR: evals/scenarios/<NN>-<slug>.md         -- legacy scenarios from ADR-0019 era (auto-extracted)
#
# Writes:
#   evals/workspace/<skill-name>-workspace/iteration-<N>/<eval-id>/{with_skill,without_skill}/{outputs,timing.json,grading.json}
#   evals/workspace/<skill-name>-workspace/iteration-<N>/benchmark.json
#
# Usage:
#   bash scripts/run-skill-evals.sh <skill-name>                        # run all evals at next iteration
#   bash scripts/run-skill-evals.sh <skill-name> --eval <eval-id>       # run single eval
#   bash scripts/run-skill-evals.sh <skill-name> --baseline-only        # baseline (no skill) only
#   bash scripts/run-skill-evals.sh <skill-name> --with-skill-only      # with_skill only (skip baseline)
#   bash scripts/run-skill-evals.sh <skill-name> --iteration <N>        # override iteration number

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKILL_NAME="${1:-}"
shift 2>/dev/null || true

if [[ -z "$SKILL_NAME" ]]; then
  cat <<EOF
ERROR: skill name required.

Usage:
  bash scripts/run-skill-evals.sh <skill-name> [--eval <id>] [--baseline-only|--with-skill-only] [--iteration <N>]

Available skills with evals:
EOF
  find "$REPO_ROOT/evals/skill-evals" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | while read -r d; do
    echo "  - $(basename "$d") (canonical)"
  done
  find "$REPO_ROOT/commands" -maxdepth 2 -mindepth 2 -name "evals.json" 2>/dev/null | while read -r f; do
    skill=$(basename "$(dirname "$(dirname "$f")")")
    echo "  - $skill (folder-shaped)"
  done
  exit 1
fi

EVAL_ID=""
BASELINE_ONLY=0
WITH_SKILL_ONLY=0
ITERATION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --eval) EVAL_ID="$2"; shift 2 ;;
    --baseline-only) BASELINE_ONLY=1; shift ;;
    --with-skill-only) WITH_SKILL_ONLY=1; shift ;;
    --iteration) ITERATION="$2"; shift 2 ;;
    *) echo "ERROR: unknown arg $1" >&2; exit 1 ;;
  esac
done

# Locate evals.json
EVALS_FILE=""
if [[ -f "$REPO_ROOT/evals/skill-evals/$SKILL_NAME/evals.json" ]]; then
  EVALS_FILE="$REPO_ROOT/evals/skill-evals/$SKILL_NAME/evals.json"
  EVAL_KIND="canonical"
elif [[ -f "$REPO_ROOT/commands/$SKILL_NAME/evals/evals.json" ]]; then
  EVALS_FILE="$REPO_ROOT/commands/$SKILL_NAME/evals/evals.json"
  EVAL_KIND="folder-shaped"
else
  echo "ERROR: no evals.json found for skill '$SKILL_NAME'" >&2
  echo "  Looked at:" >&2
  echo "    $REPO_ROOT/evals/skill-evals/$SKILL_NAME/evals.json" >&2
  echo "    $REPO_ROOT/commands/$SKILL_NAME/evals/evals.json" >&2
  exit 1
fi

echo "skill: $SKILL_NAME ($EVAL_KIND)"
echo "evals: $EVALS_FILE"

# Determine workspace + iteration
WORKSPACE_BASE="$REPO_ROOT/evals/workspace/${SKILL_NAME}-workspace"
mkdir -p "$WORKSPACE_BASE"

if [[ -z "$ITERATION" ]]; then
  # Auto-detect next iteration
  LAST=$(ls -d "$WORKSPACE_BASE"/iteration-* 2>/dev/null | sed 's|.*iteration-||' | sort -n | tail -1)
  ITERATION=$((${LAST:-0} + 1))
fi

ITERATION_DIR="$WORKSPACE_BASE/iteration-$ITERATION"
mkdir -p "$ITERATION_DIR"
echo "iteration: $ITERATION ($ITERATION_DIR)"

# Validate evals.json schema (minimal)
if ! jq -e '.skill_name and .evals and (.evals | type == "array")' "$EVALS_FILE" >/dev/null 2>&1; then
  echo "ERROR: $EVALS_FILE does not match canonical schema" >&2
  echo "  Expected: {skill_name: string, evals: [{id, prompt, expected_output, files, assertions}, ...]}" >&2
  exit 1
fi

# Enumerate evals to run
if [[ -n "$EVAL_ID" ]]; then
  EVAL_IDS=$(jq -r --arg id "$EVAL_ID" '.evals[] | select(.id == $id) | .id' "$EVALS_FILE")
  [[ -z "$EVAL_IDS" ]] && { echo "ERROR: eval id '$EVAL_ID' not in $EVALS_FILE" >&2; exit 1; }
else
  EVAL_IDS=$(jq -r '.evals[].id' "$EVALS_FILE")
fi

# Per-eval scaffolding (SHELL framework; actual model invocation is host-specific)
total=0
prepared=0
while IFS= read -r eid; do
  total=$((total + 1))
  EVAL_DIR="$ITERATION_DIR/$eid"
  mkdir -p "$EVAL_DIR/without_skill/outputs" "$EVAL_DIR/with_skill/outputs"

  # Materialize eval scenario into local files (jq selects)
  jq --arg id "$eid" '.evals[] | select(.id == $id)' "$EVALS_FILE" > "$EVAL_DIR/eval.json"

  # Prepare timing + grading scaffold (filled in by invoker)
  if [[ ! -f "$EVAL_DIR/without_skill/timing.json" ]]; then
    echo '{"start_ts": null, "end_ts": null, "duration_seconds": null, "tokens_input": null, "tokens_output": null}' > "$EVAL_DIR/without_skill/timing.json"
  fi
  if [[ ! -f "$EVAL_DIR/with_skill/timing.json" ]]; then
    echo '{"start_ts": null, "end_ts": null, "duration_seconds": null, "tokens_input": null, "tokens_output": null}' > "$EVAL_DIR/with_skill/timing.json"
  fi
  if [[ ! -f "$EVAL_DIR/without_skill/grading.json" ]]; then
    echo '{"passed": null, "rationale": "", "assertion_results": []}' > "$EVAL_DIR/without_skill/grading.json"
  fi
  if [[ ! -f "$EVAL_DIR/with_skill/grading.json" ]]; then
    echo '{"passed": null, "rationale": "", "assertion_results": []}' > "$EVAL_DIR/with_skill/grading.json"
  fi

  prepared=$((prepared + 1))
  echo "  prepared: $eid"
done <<< "$EVAL_IDS"

cat >&2 <<EOF

Scaffold prepared: $prepared / $total evals at $ITERATION_DIR

Next steps (host-driven; this script is the framework, not the invoker):
  1. For each eval/{without_skill,with_skill}/, invoke the model with the prompt + files.
     - 'without_skill': baseline (no SKILL.md loaded; only mandatory context bootstrap).
     - 'with_skill': skill loaded (SKILL.md activated per host's discovery mechanism).
  2. Write model output to outputs/. Update timing.json (start, end, duration, tokens).
  3. Run assertions per evals.json eval.assertions. Update grading.json.
  4. After all evals complete: bash scripts/compute-benchmark.sh $SKILL_NAME --iteration $ITERATION

Per agentskills.io evaluating-skills canonical format.
EOF
