#!/usr/bin/env bash
# add-suggested-model-hint.sh - Add suggested-model field to command frontmatter
#
# Per ADR-0025 addendum (2026-06-03) Model selection by tier:
#   Express     -> claude-haiku-4-5
#   Standard    -> claude-sonnet-4-6  (default for most commands)
#   Disciplined -> claude-sonnet-4-6 (escalate to opus when critical)
#   Strict      -> claude-opus-4-7
#
# Per B.3 of Fhorja improvement plan 2026-06-03.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMMANDS_DIR="${REPO_ROOT}/commands"

# Categorization (per-command override of the default Sonnet 4.6 mapping)
HAIKU_COMMANDS=(
  branch-commit
  what-next
  where-we-at
  slice-closure
  compact-task-memory
  capture-observation
  approve-proposed
  approve-plan
  resume-from-state
  sync-task-state
  prompt-shape
  team-update
  workflow-guide
  im-stuck
)

OPUS_COMMANDS=(
  security-review
  review-hard
  contract-signoff
  decision-interview
  impact-analysis
  design-bootstrap
  pr-package
  task-init
  task-close
  state-reconcile
  resolve-contract-gaps
  post-review-pivot
)

# Helper: check if value is in array
in_array() {
  local needle="$1"; shift
  local item
  for item in "$@"; do
    [[ "$item" == "$needle" ]] && return 0
  done
  return 1
}

UPDATED=0
SKIPPED=0
ALREADY_HAS=0

for cmd_file in "${COMMANDS_DIR}"/*.md; do
  cmd_name="$(basename "$cmd_file" .md)"

  # Skip if frontmatter already has suggested-model
  if grep -q "^  suggested-model:" "$cmd_file"; then
    ALREADY_HAS=$((ALREADY_HAS + 1))
    continue
  fi

  # Determine model
  if in_array "$cmd_name" "${HAIKU_COMMANDS[@]}"; then
    model="claude-haiku-4-5"
  elif in_array "$cmd_name" "${OPUS_COMMANDS[@]}"; then
    model="claude-opus-4-7"
  else
    model="claude-sonnet-4-6"
  fi

  # Insert after token-budget line (assumed present in every command)
  if grep -q "^  token-budget:" "$cmd_file"; then
    # Use awk to insert after the token-budget line
    awk -v model="$model" '
      /^  token-budget:/ {
        print
        printf "  suggested-model: %s\n", model
        next
      }
      { print }
    ' "$cmd_file" > "${cmd_file}.tmp" && mv "${cmd_file}.tmp" "$cmd_file"
    UPDATED=$((UPDATED + 1))
    printf "  added %-40s -> %s\n" "$cmd_name" "$model" >&2
  else
    SKIPPED=$((SKIPPED + 1))
    printf "  SKIPPED %-40s (no token-budget line)\n" "$cmd_name" >&2
  fi
done

echo "" >&2
echo "Summary: $UPDATED updated, $ALREADY_HAS already had field, $SKIPPED skipped" >&2
