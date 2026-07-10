#!/usr/bin/env bash
# Assertion: Step 09 (repo-consistency-sweep) -- validates Pre-flight substrate audit + dogfood K.2 on the sweep's own TASK_STATE write.
# Per evals/e2e/walkthrough.md Step 09.
#
# This is the critical assertion of the entire walkthrough: if the prior 8
# steps all honored K.2, the substrate audit MUST report drift=0 + invalid=0.
# Any non-zero count is a regression in one of the upstream writers.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

echo "== Step 09: repo-consistency-sweep =="

resolve_task_dir
echo "task: $TASK_DIR"

# --- (1) SWEEP snapshot file written by the sweep --------------------------
sweep_dir="$TASK_DIR/REVIEW_SWEEPS"
assert_dir_exists "$sweep_dir"

# At least one SWEEP_*.md file should exist; pick the most recent.
latest_sweep=$(find "$sweep_dir" -maxdepth 1 -mindepth 1 -name 'SWEEP_*.md' -type f 2>/dev/null | sort | tail -1)
if [[ -z "$latest_sweep" ]]; then
  fail "no SWEEP_*.md snapshot found in $sweep_dir"
  finish
fi
pass_check "snapshot present: $(basename "$latest_sweep")"

# --- (2) Snapshot must include the two substrate-audit metadata lines ------
if grep -qE '^substrate_header_drift_count: [0-9]+' "$latest_sweep"; then
  pass_check "snapshot has substrate_header_drift_count line"
else
  fail "snapshot missing substrate_header_drift_count line (Step 9 didn't include Pre-flight output)"
fi
if grep -qE '^verification_log_invalid_count: [0-9]+' "$latest_sweep"; then
  pass_check "snapshot has verification_log_invalid_count line"
else
  fail "snapshot missing verification_log_invalid_count line"
fi

# --- (3) Re-run the Pre-flight scripts out-of-band; counts must be ZERO ---
# in the task folder, with a v2.1 project-level allowance.
# Known v2.1 deferral (per wos/substrate-peers.md REFERENCES.md + REVIEW_PREFERENCES.md
# K.2 applicability gap): project-level files (REFERENCES.md, INITIATIVE_INDEX.md,
# REVIEW_PREFERENCES.md at projects/<proj>/) do NOT have a canonical K.2 emission
# protocol because no .wos/ exists at the project layer. The scan correctly flags
# their H2 sections as drift; the assertion tolerates up to 4 such sections
# (2 in REFERENCES.md + 2 in INITIATIVE_INDEX.md when present).
echo
echo "Re-running substrate audit out-of-band (ground truth check)..."
PROJECT_LEVEL_DEFERRAL_CAP=4
drift_result=$(bash "$WOS_ROOT/scripts/scan-substrate-headers.sh" "$TASK_DIR" 2>&1)
drift_count=$(echo "$drift_result" | grep -oE 'substrate_header_drift_count: [0-9]+' | awk '{print $2}')
if [[ -n "$drift_count" && "$drift_count" -le "$PROJECT_LEVEL_DEFERRAL_CAP" ]]; then
  pass_check "substrate header drift = $drift_count (within v2.1 project-level deferral cap of $PROJECT_LEVEL_DEFERRAL_CAP; see wos/substrate-peers.md K.2 applicability gap)"
else
  fail "substrate header drift = ${drift_count:-?} exceeds v2.1 project-level deferral cap ($PROJECT_LEVEL_DEFERRAL_CAP); a task-folder writer likely skipped its K.2 protocol -- run with --verbose for detail"
fi
assert_verification_log_valid "$TASK_DIR/.wos/VERIFICATION_LOG.jsonl"

# --- (4) Dogfood: the sweep itself wrote ## Latest sweep with K.2 header --
# Per repo-consistency-sweep Step 10 ("Update TASK_STATE (dogfood K.2)"), the
# sweep MUST emit a wos:write header above ## Latest sweep AND append a JSONL
# line with valid SHA-256 hex. If the K.2 dogfood took, the audit above
# already validated the JSONL line; here we check the inline header.
assert_section_present "$TASK_DIR/TASK_STATE.md" "## Latest sweep"
assert_k2_header        "$TASK_DIR/TASK_STATE.md" "## Latest sweep" "repo-consistency-sweep"

# --- (5) The JSONL line for the sweep's own write must have non-null SHAs -
# Find the most recent line written by repo-consistency-sweep with event=write.
log="$TASK_DIR/.wos/VERIFICATION_LOG.jsonl"
if [[ -f "$log" ]]; then
  sweep_lines=$(grep '"owner":"repo-consistency-sweep"' "$log" 2>/dev/null | grep '"event":"write"' || true)
  if [[ -z "$sweep_lines" ]]; then
    fail "no JSONL line found for owner=repo-consistency-sweep event=write"
  else
    last_sweep_line=$(echo "$sweep_lines" | tail -1)
    if echo "$last_sweep_line" | grep -q '"sha_after":null'; then
      fail "sweep's own JSONL line has sha_after:null (dogfood K.2 failed; should be 64-char hex)"
    else
      pass_check "sweep's own JSONL line has non-null sha_after"
    fi
  fi
fi

finish
