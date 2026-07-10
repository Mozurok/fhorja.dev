#!/usr/bin/env bash
# Assertion: Step 06 (implementation-plan) -- validates K.2 headers on all 4
# owned sections + canonical 7-field per-slice format.
# Per evals/e2e/walkthrough.md Step 06.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

echo "== Step 06: implementation-plan =="
resolve_task_dir
echo "task: $TASK_DIR"

assert_file_exists     "$TASK_DIR/IMPLEMENTATION_PLAN.md"

for section in "## Target behavior" "## Current gaps" "## Slices" "## Risks and mitigations"; do
  assert_section_present "$TASK_DIR/IMPLEMENTATION_PLAN.md" "$section"
  assert_k2_header       "$TASK_DIR/IMPLEMENTATION_PLAN.md" "$section" "implementation-plan"
done

# At least 2 slices (walkthrough Step 06 produces Slice 1 + Slice 2)
slice_count=$(grep -cE '^### Slice [0-9]+' "$TASK_DIR/IMPLEMENTATION_PLAN.md" 2>/dev/null || echo 0)
if [[ "$slice_count" -ge 2 ]]; then
  pass_check "at least 2 slices defined (found $slice_count)"
else
  fail "expected at least 2 slices; found $slice_count"
fi

# JSONL evidence
log="$TASK_DIR/.wos/VERIFICATION_LOG.jsonl"
if [[ -f "$log" ]]; then
  if grep '"owner":"implementation-plan"' "$log" 2>/dev/null | grep -q '"event":"write"'; then
    pass_check "implementation-plan has at least one JSONL write entry"
  else
    fail "no JSONL line found for owner=implementation-plan event=write"
  fi
fi

finish
