#!/usr/bin/env bash
# Assertion: Step 03 (task-init) -- validates the 5 mandatory task files exist
# with K.2 headers above each section (task-init is THE initial writer).
# Per evals/e2e/walkthrough.md Step 03.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

echo "== Step 03: task-init =="
resolve_task_dir
echo "task: $TASK_DIR"

# All 5 mandatory files exist
for f in README.md TASK_STATE.md SOURCE_OF_TRUTH.md DECISIONS.md IMPLEMENTATION_PLAN.md; do
  assert_file_exists "$TASK_DIR/$f"
done

# Sample of canonical TASK_STATE sections that task-init OWNS as initial writer
for section in "## Task summary" "## Objective" "## Source of truth"; do
  assert_section_present "$TASK_DIR/TASK_STATE.md" "$section"
  assert_k2_header       "$TASK_DIR/TASK_STATE.md" "$section" "task-init"
done

# SOURCE_OF_TRUTH single-repo emits ## Active codebase / repo (NOT ## Repositories)
assert_section_present "$TASK_DIR/SOURCE_OF_TRUTH.md" "## Active codebase / repo"
assert_k2_header       "$TASK_DIR/SOURCE_OF_TRUTH.md" "## Active codebase / repo" "task-init"

# VERIFICATION_LOG.jsonl created by task-init
log="$TASK_DIR/.wos/VERIFICATION_LOG.jsonl"
assert_file_exists "$log"

# task-init has multiple JSONL write lines (one per section)
if [[ -f "$log" ]]; then
  count=$(grep -c '"owner":"task-init"' "$log" 2>/dev/null || echo 0)
  if [[ "$count" -ge 3 ]]; then
    pass_check "task-init has $count JSONL write entries (expected >=3)"
  else
    fail "task-init JSONL count = $count; expected >=3 (one per owned section)"
  fi
fi

finish
