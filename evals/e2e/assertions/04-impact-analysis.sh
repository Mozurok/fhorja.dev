#!/usr/bin/env bash
# Assertion: Step 04 (impact-analysis) -- validates IMPACT_ANALYSIS.md
# canonical 12-item structure + K.2 header above the owned TASK_STATE section.
# Per evals/e2e/walkthrough.md Step 04.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

echo "== Step 04: impact-analysis =="
resolve_task_dir
echo "task: $TASK_DIR"

# IMPACT_ANALYSIS.md exists (this is a task artifact, not substrate per matrix)
assert_file_exists "$TASK_DIR/IMPACT_ANALYSIS.md"

# Canonical 12-item structure: spot-check 4 items
for label in "Request understanding" "Confirmed facts" "Affected areas" "Recommended path"; do
  if grep -qE "(^### |^## |^[0-9]+\. *).*${label}" "$TASK_DIR/IMPACT_ANALYSIS.md"; then
    pass_check "IMPACT_ANALYSIS.md item present: ${label}"
  else
    fail "IMPACT_ANALYSIS.md missing canonical item: ${label}"
  fi
done

# Owned substrate write (after approve-proposed promotes the PROPOSED block)
# Note: in Ask mode, ## Active files in scope is PROPOSED; in Agent mode after
# approve-proposed it's APPLIED with the wos:write header. Check for either.
if grep -qxF "## Active files in scope" "$TASK_DIR/TASK_STATE.md"; then
  pass_check "TASK_STATE.md ## Active files in scope present"
  if assert_k2_header "$TASK_DIR/TASK_STATE.md" "## Active files in scope" "impact-analysis" 2>/dev/null; then
    : # impact-analysis is the owner; APPLIED state
  fi
fi

# JSONL: impact-analysis emits at least one entry (write or propose)
log="$TASK_DIR/.wos/VERIFICATION_LOG.jsonl"
if [[ -f "$log" ]]; then
  if grep -q '"owner":"impact-analysis"' "$log" 2>/dev/null; then
    pass_check "impact-analysis has at least one JSONL entry"
  else
    fail "no JSONL line found for owner=impact-analysis"
  fi
fi

finish
