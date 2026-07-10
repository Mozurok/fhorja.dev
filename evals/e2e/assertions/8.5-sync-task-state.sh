#!/usr/bin/env bash
# Assertion: Step 8.5 (sync-task-state) -- validates K.2 header on each section
# sync-task-state writes during the walkthrough.
# Per evals/e2e/walkthrough.md Step 8.5.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

echo "== Step 8.5: sync-task-state =="
resolve_task_dir
echo "task: $TASK_DIR"

assert_file_exists     "$TASK_DIR/TASK_STATE.md"

# Owned sections per wos/substrate-peers.md TASK_STATE.md table
for section in "## Current known facts" "## Canonical decisions" "## Last completed step" "## Current status" "## Risks to watch"; do
  assert_section_present "$TASK_DIR/TASK_STATE.md" "$section"
  assert_k2_header       "$TASK_DIR/TASK_STATE.md" "$section" "sync-task-state"
done

# JSONL evidence
log="$TASK_DIR/.wos/VERIFICATION_LOG.jsonl"
if [[ -f "$log" ]]; then
  if grep '"owner":"sync-task-state"' "$log" 2>/dev/null | grep -q '"event":"write"'; then
    pass_check "sync-task-state has at least one JSONL write entry"
  else
    fail "no JSONL line found for owner=sync-task-state event=write"
  fi
fi

finish
