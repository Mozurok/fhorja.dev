#!/usr/bin/env bash
# Assertion: Phase 4 rollup -- validates the complete Phase 4 walkthrough output.
# Per evals/e2e/walkthrough.md Phase 4.
#
# Phase 4 exercises the multi-persona writer surface (L1/L2/L3 + report-file
# owners) end-to-end. This rollup is the integration check: if every Phase 4
# step honored K.2, respected L3 ownership boundaries, and emitted the expected
# substrate, the audits MUST be clean. Any nonzero count is a regression in
# one of the upstream persona writers.
#
# Validates:
#  (1) all expected SCREEN_SPECs + IMPLEMENTATION_PLAN sections written
#  (2) K.2 transaction headers above every persona-attributed write
#  (3) K.5 validator: zero invalid VERIFICATION_LOG.jsonl lines
#  (4) scan-substrate-orphans.py returns exit 0
#  (5) substrate-header-drift count == 0
#  (6) L3 ownership respected (no L1/L2 wrote to rls-owned ## Risks to watch)
#  (7) report-file ownerships correctly attributed
#      (POST_DEPLOY_PLAN, CONTRAST_AUDIT, JTBD_INTERVIEWS, MIGRATION_SAFETY)
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

echo "== Phase 4 rollup =="

resolve_task_dir
echo "task: $TASK_DIR"

# --- (1) Expected SCREEN_SPECs + IMPLEMENTATION_PLAN sections --------------
screens_dir="$TASK_DIR/SCREEN_SPECS"
assert_dir_exists "$screens_dir"

# Phase 4 fixture walkthrough produces these three screen specs.
for screen in "login.md" "dashboard.md" "settings.md"; do
  assert_file_exists "$screens_dir/$screen"
done

plan="$TASK_DIR/IMPLEMENTATION_PLAN.md"
assert_file_exists "$plan"
assert_section_present "$plan" "## Slices"
assert_section_present "$plan" "## Validation strategy"
assert_section_present "$plan" "## Risks"

# --- (2) K.2 transaction headers above every persona-attributed write -----
# Each report file's owning persona must have emitted a canonical wos:write
# header above its top-level section. Mirrors HEADER_REGEX in _lib.sh.
declare -a HEADERED_WRITES=(
  "$TASK_DIR/POST_DEPLOY_PLAN.md|## Post-deploy checks|post-deploy-verifier"
  "$TASK_DIR/CONTRAST_AUDIT.md|## Contrast findings|color-contrast-architect"
  "$TASK_DIR/JTBD_INTERVIEWS.md|## Interviews|jtbd-switch-interviewer"
  "$TASK_DIR/MIGRATION_SAFETY.md|## Migration plan|migration-safety-steward"
  "$plan|## Slices|implementation-plan"
)
for spec in "${HEADERED_WRITES[@]}"; do
  IFS='|' read -r file section owner <<<"$spec"
  assert_k2_header "$file" "$section" "$owner"
done

# --- (3) K.5 validator: zero invalid VERIFICATION_LOG.jsonl lines ---------
log="$TASK_DIR/.wos/VERIFICATION_LOG.jsonl"
assert_verification_log_valid "$log"

# --- (4) scan-substrate-orphans.py exits 0 --------------------------------
echo
echo "Running scan-substrate-orphans.py (ground truth check)..."
orphan_script="$WOS_ROOT/scripts/scan-substrate-orphans.py"
if [[ ! -f "$orphan_script" ]]; then
  fail "orphan scan script missing: $orphan_script"
else
  if python3 "$orphan_script" "$TASK_DIR" >/dev/null 2>&1; then
    pass_check "scan-substrate-orphans.py exit 0 (no orphans)"
  else
    fail "scan-substrate-orphans.py returned non-zero (orphan substrate present)"
  fi
fi

# --- (5) substrate-header-drift count == 0 (strict) ----------------------
# Phase 4 rollup is stricter than Step 09: Phase 4 only writes inside the task
# folder, so no project-level deferral applies. Drift MUST be exactly zero.
assert_substrate_drift_zero "$TASK_DIR"

# --- (6) L3 ownership: no L1/L2 wrote to rls-owned ## Risks to watch ------
# Per command-roles.md, ## Risks to watch in TASK_STATE.md is owned by the L3
# rls-auth-boundary-auditor. L1 (task-init, impact-analysis, ...) and L2
# (implementation-plan, decision-interview, ...) MUST NOT emit wos:write
# headers naming themselves as owner of that section.
task_state="$TASK_DIR/TASK_STATE.md"
if [[ -f "$task_state" ]]; then
  # Find every wos:write header for "## Risks to watch" and check the owner.
  # Allowed owner: rls-auth-boundary-auditor (or its alias rls).
  bad_owners=$(grep -E "^<!-- wos:write owner=[^ ]+ section='## Risks to watch'" "$task_state" 2>/dev/null \
    | grep -vE "owner=(rls-auth-boundary-auditor|rls) " || true)
  if [[ -z "$bad_owners" ]]; then
    pass_check "L3 ownership respected for ## Risks to watch (only rls-auth-boundary-auditor)"
  else
    fail "L3 ownership violated for ## Risks to watch; non-rls owner(s) wrote:"
    while IFS= read -r line; do
      [[ -n "$line" ]] && fail "  $line"
    done <<<"$bad_owners"
  fi
else
  fail "TASK_STATE.md missing; cannot verify L3 ownership"
fi

# --- (7) Report-file ownerships attributed correctly ---------------------
# Cross-check the VERIFICATION_LOG.jsonl: each report file MUST have at least
# one event=write line authored by its canonical owner persona.
declare -a REPORT_OWNERS=(
  "POST_DEPLOY_PLAN.md|post-deploy-verifier"
  "CONTRAST_AUDIT.md|color-contrast-architect"
  "JTBD_INTERVIEWS.md|jtbd-switch-interviewer"
  "MIGRATION_SAFETY.md|migration-safety-steward"
)
if [[ -f "$log" ]]; then
  for entry in "${REPORT_OWNERS[@]}"; do
    IFS='|' read -r report owner <<<"$entry"
    # JSONL field shapes per K.5 spec: "owner":"<persona>" + "target":"<path>".
    matches=$(grep "\"owner\":\"$owner\"" "$log" 2>/dev/null \
      | grep "\"event\":\"write\"" \
      | grep -F "$report" || true)
    if [[ -n "$matches" ]]; then
      pass_check "ownership attributed: $report -> $owner"
    else
      fail "ownership missing in JSONL: $report has no event=write line owned by $owner"
    fi
  done
else
  fail "VERIFICATION_LOG.jsonl missing; cannot cross-check report ownerships"
fi

finish
