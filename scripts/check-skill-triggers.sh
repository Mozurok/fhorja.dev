#!/usr/bin/env bash
# check-skill-triggers.sh (W-19)
#
# Advisory (warn-only, NEVER fails the build) coverage check for trigger evals.
# evals/skill-evals/README.md documents an optional "trigger_evals" block
# (should_trigger / should_not_trigger) that validates a command description's
# invocation accuracy, not just its output. Nothing checked for the block, so
# the discipline stayed documentation-only. This script reports how many skills
# carry the block so the gap is visible, consistent with the natural-voice and
# instruction-budget advisory precedent.
#
# Mirrors scripts/check-instruction-budget.sh: prints a single summary line and,
# under --verbose, per-skill detail. ALWAYS exits 0. lint-commands.sh surfaces
# the summary line as an informational advisory; it never flips the exit code.
#
# Dependency-free: greps for the literal "trigger_evals" key, no jq required.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERBOSE=0
[[ "${1:-}" == "--verbose" || "${1:-}" == "-v" ]] && VERBOSE=1

# Canonical and folder-shaped eval locations (see evals/skill-evals/README.md).
# Globs that match nothing expand to the literal pattern, so the [[ -f ]] test
# filters them out and the array only holds real files.
EVAL_FILES=()
for f in "${REPO_ROOT}"/evals/skill-evals/*/evals.json; do
  [[ -f "$f" ]] && EVAL_FILES+=("$f")
done
for f in "${REPO_ROOT}"/commands/*/evals/evals.json; do
  [[ -f "$f" ]] && EVAL_FILES+=("$f")
done

with=0
without=0
missing=()
# Guard the loop: an empty array under `set -u` would abort on bash 3.2 (macOS).
if (( ${#EVAL_FILES[@]} > 0 )); then
  for f in "${EVAL_FILES[@]}"; do
    # Skill name = the skill folder (parent of evals.json, or its evals/ parent).
    name="$f"
    name="${name%/evals.json}"
    name="${name%/evals}"
    name="${name##*/}"
    if grep -q '"trigger_evals"' "$f" 2>/dev/null; then
      with=$((with+1))
    else
      without=$((without+1))
      missing+=("  [skill-triggers] ${name}: evals.json has no trigger_evals block (description invocation accuracy unchecked)")
    fi
  done
fi

echo "Skill-triggers: ${with} skill(s) with trigger evals, ${without} without (advisory)"
if (( VERBOSE == 1 && without > 0 )); then
  printf '%s\n' "${missing[@]}"
fi
exit 0
