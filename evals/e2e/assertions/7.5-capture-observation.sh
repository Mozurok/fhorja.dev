#!/usr/bin/env bash
# Assertion: Step 7.5 (capture-observation) -- validates dated bullet appended
# under ## Observations + K.2 header above the section.
# Per evals/e2e/walkthrough.md Step 7.5.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

echo "== Step 7.5: capture-observation =="
resolve_task_dir
echo "task: $TASK_DIR"

assert_file_exists     "$TASK_DIR/TASK_STATE.md"
assert_section_present "$TASK_DIR/TASK_STATE.md" "## Observations"
assert_k2_header       "$TASK_DIR/TASK_STATE.md" "## Observations" "capture-observation"

# At least one dated bullet matches the canonical format: - [YYYY-MM-DD] [tag] text
if grep -qE '^- \[[0-9]{4}-[0-9]{2}-[0-9]{2}\] \[[a-z]+\]' "$TASK_DIR/TASK_STATE.md"; then
  pass_check "at least one canonical observation bullet present"
else
  fail "no canonical observation bullet found (expected pattern: - [YYYY-MM-DD] [tag] ...)"
fi

# JSONL evidence
log="$TASK_DIR/.wos/VERIFICATION_LOG.jsonl"
if [[ -f "$log" ]]; then
  if grep '"owner":"capture-observation"' "$log" 2>/dev/null | grep -q '"event":"write"'; then
    pass_check "capture-observation has at least one JSONL write entry"
  else
    fail "no JSONL line found for owner=capture-observation event=write"
  fi
fi

finish
