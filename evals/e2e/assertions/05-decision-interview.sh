#!/usr/bin/env bash
# Assertion: Step 05 (decision-interview) -- validates D-1 entry + K.2 header.
# Per evals/e2e/walkthrough.md Step 05.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

echo "== Step 05: decision-interview =="
resolve_task_dir
echo "task: $TASK_DIR"

assert_file_exists     "$TASK_DIR/DECISIONS.md"
assert_section_present "$TASK_DIR/DECISIONS.md" "## Locked decisions"
assert_k2_header       "$TASK_DIR/DECISIONS.md" "## Locked decisions" "decision-interview"

# At least one D-N entry must exist (walkthrough Step 05 locks D-1)
if grep -qE '^### D-[0-9]+' "$TASK_DIR/DECISIONS.md"; then
  pass_check "at least one D-N entry present"
else
  fail "no ### D-N entry in DECISIONS.md ## Locked decisions"
fi

# JSONL evidence
log="$TASK_DIR/.wos/VERIFICATION_LOG.jsonl"
if [[ -f "$log" ]]; then
  if grep '"owner":"decision-interview"' "$log" 2>/dev/null | grep -q '"event":"write"'; then
    pass_check "decision-interview has at least one JSONL write entry"
  else
    fail "no JSONL line found for owner=decision-interview event=write"
  fi
fi

finish
