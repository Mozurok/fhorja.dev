# Shared helpers for E2E assertion scripts. Source from each 0N-<command>.sh.
#
# Usage in an assertion script:
#   #!/usr/bin/env bash
#   set -euo pipefail
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   . "$SCRIPT_DIR/_lib.sh"
#
#   assert_file_exists "$PROJECT_DIR/PROJECT_CHARTER.md"
#   assert_section_present "$TASK_DIR/TASK_STATE.md" "## Current phase"
#   assert_k2_header "$TASK_DIR/TASK_STATE.md" "## Current phase" "task-init"
#   ...
#   pass

WOS_ROOT="${WOS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
PROJECT_DIR="${PROJECT_DIR:-$WOS_ROOT/projects/wos__e2e-test}"
ACTIVE_DIR="${ACTIVE_DIR:-$PROJECT_DIR/active}"
FAKE_APP="${FAKE_APP:-/tmp/wos-e2e-fake-app}"

# Find the (single) task folder under active/; sets TASK_DIR.
resolve_task_dir() {
  if [[ ! -d "$ACTIVE_DIR" ]]; then
    fail "active/ not found at $ACTIVE_DIR"
  fi
  local count
  count=$(find "$ACTIVE_DIR" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')
  if [[ "$count" != "1" ]]; then
    fail "expected exactly 1 task folder under active/; found $count"
  fi
  TASK_DIR=$(find "$ACTIVE_DIR" -maxdepth 1 -mindepth 1 -type d)
}

FAILURES=()

fail() {
  echo "  FAIL: $1" >&2
  FAILURES+=("$1")
}

pass_check() {
  echo "  ok:   $1"
}

# --- file existence -----------------------------------------------------------
assert_file_exists() {
  if [[ -f "$1" ]]; then
    pass_check "file exists: $1"
  else
    fail "file missing: $1"
  fi
}

assert_dir_exists() {
  if [[ -d "$1" ]]; then
    pass_check "dir exists: $1"
  else
    fail "dir missing: $1"
  fi
}

# --- section presence ---------------------------------------------------------
# Argument 1 = file, argument 2 = literal H2 line (including "## ")
assert_section_present() {
  local file="$1" section="$2"
  if [[ ! -f "$file" ]]; then
    fail "section check skipped (file missing): $file"
    return
  fi
  if grep -qxF "$section" "$file"; then
    pass_check "section present in $(basename "$file"): $section"
  else
    fail "section absent in $(basename "$file"): $section"
  fi
}

# --- K.2 transaction header ---------------------------------------------------
# Verifies that the line IMMEDIATELY above the named section is a canonical
# <!-- wos:write owner=<expected> section='## X' run_id=... ts=... reason=... mode=(applied|proposed) -->
# header. Mirrors the HEADER_REGEX from scripts/scan-substrate-headers.sh so the
# lib + scan agree byte-for-byte. Argument 3 = expected owner basename.
#
# Validates ALL canonical fields, not just the prefix:
#   - owner == expected_owner (literal match)
#   - section == "$section" (single-quoted; literal match)
#   - run_id matches [a-zA-Z0-9_-]+
#   - ts matches [0-9T:.Z-]+
#   - reason is non-empty
#   - mode in {applied, proposed}
#   - trailing ' -->' is present
assert_k2_header() {
  local file="$1" section="$2" expected_owner="$3"
  if [[ ! -f "$file" ]]; then
    fail "k2-header check skipped (file missing): $file"
    return
  fi
  local section_line
  section_line=$(grep -nxF "$section" "$file" | head -1 | cut -d: -f1)
  if [[ -z "$section_line" ]]; then
    fail "k2-header check: section not found ($section in $(basename "$file"))"
    return
  fi
  local prev_line_no=$((section_line - 1))
  if [[ "$prev_line_no" -lt 1 ]]; then
    fail "k2-header check: section is at top of file (no prior line); section=$section"
    return
  fi
  local prev_line
  prev_line=$(sed -n "${prev_line_no}p" "$file")
  # Build the full canonical regex with literal owner + literal section name.
  # Bash ERE doesn't support \< / \>; bare < and > are fine inside [[ =~ ]].
  local regex="^<!-- wos:write owner=${expected_owner} section='${section}' run_id=[a-zA-Z0-9_-]+ ts=[0-9T:.Z-]+ reason=.+ mode=(applied|proposed) -->$"
  if [[ "$prev_line" =~ $regex ]]; then
    pass_check "k2 header above $section (owner=$expected_owner; full canonical match)"
  else
    fail "k2 header missing / malformed / wrong owner above $section in $(basename "$file"): got: $prev_line"
  fi
}

# --- VERIFICATION_LOG.jsonl validity ------------------------------------------
assert_verification_log_valid() {
  local log="$1"
  if [[ ! -f "$log" ]]; then
    fail "verification log missing: $log"
    return
  fi
  local result invalid
  result=$(python3 "$WOS_ROOT/scripts/verify-log-validator.py" "$log" 2>&1)
  invalid=$(echo "$result" | grep -oE 'invalid: [0-9]+' | awk '{print $2}')
  if [[ -z "$invalid" ]]; then
    fail "verification log validator did not produce 'invalid: <N>' line; output: $result"
    return
  fi
  if [[ "$invalid" == "0" ]]; then
    pass_check "verification log valid (0 invalid lines)"
  else
    fail "verification log has $invalid invalid lines"
  fi
}

# --- Substrate header drift count ---------------------------------------------
assert_substrate_drift_zero() {
  local task="$1"
  local result drift
  result=$(bash "$WOS_ROOT/scripts/scan-substrate-headers.sh" "$task" 2>&1)
  drift=$(echo "$result" | grep -oE 'substrate_header_drift_count: [0-9]+' | awk '{print $2}')
  if [[ -z "$drift" ]]; then
    fail "scan-substrate-headers did not produce drift_count line; output: $result"
    return
  fi
  if [[ "$drift" == "0" ]]; then
    pass_check "substrate header drift = 0"
  else
    fail "substrate header drift = $drift (expected 0); run with --verbose for detail"
  fi
}

# --- Final summary ------------------------------------------------------------
finish() {
  echo
  if [[ ${#FAILURES[@]:-0} -eq 0 ]]; then
    echo "PASS: all assertions satisfied."
    exit 0
  else
    echo "FAIL: ${#FAILURES[@]} assertion(s) failed:"
    printf '  - %s\n' "${FAILURES[@]}"
    exit 1
  fi
}
