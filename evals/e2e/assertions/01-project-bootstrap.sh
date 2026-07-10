#!/usr/bin/env bash
# Assertion: Step 01 (project-bootstrap) -- validates synthetic project folder + initial files.
# Per evals/e2e/walkthrough.md Step 01.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/_lib.sh"

echo "== Step 01: project-bootstrap =="

assert_dir_exists  "$PROJECT_DIR"
assert_dir_exists  "$PROJECT_DIR/active"
assert_dir_exists  "$PROJECT_DIR/archive"

assert_file_exists "$PROJECT_DIR/PROJECT_CHARTER.md"
assert_section_present "$PROJECT_DIR/PROJECT_CHARTER.md" "## Objective"
assert_section_present "$PROJECT_DIR/PROJECT_CHARTER.md" "## Stack"
# Single-repo walkthrough: project-bootstrap omits `## Repositories` (multi-repo
# only) and records the single repo under `## Default workspace` per
# project-bootstrap.md line 109.
assert_section_present "$PROJECT_DIR/PROJECT_CHARTER.md" "## Default workspace"
assert_section_present "$PROJECT_DIR/PROJECT_CHARTER.md" "## Constraints"
assert_section_present "$PROJECT_DIR/PROJECT_CHARTER.md" "## Non-goals"

assert_file_exists "$PROJECT_DIR/REFERENCES.md"
# project-bootstrap emits REFERENCES.md with `## Format reminder` + `## Entries`
# (NOT `## References`). The substrate-peers matrix labels the owner-section as
# `## References` which is an internal inconsistency tracked as a v2.1 deferral.
# Assert the actual template's section headers.
assert_section_present "$PROJECT_DIR/REFERENCES.md" "## Format reminder"
assert_section_present "$PROJECT_DIR/REFERENCES.md" "## Entries"

# Active should be empty (task-init creates the first task folder in Step 03).
active_count=$(find "$PROJECT_DIR/active" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
if [[ "$active_count" == "0" ]]; then
  pass_check "active/ is empty (task-init not yet run -- correct)"
else
  fail "active/ should be empty after project-bootstrap; found $active_count subdir(s)"
fi

finish
