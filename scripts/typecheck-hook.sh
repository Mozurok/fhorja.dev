#!/usr/bin/env bash
# typecheck-hook.sh - Claude Code PostToolUse hook for TypeScript type checking
#
# Runs tsc --noEmit after Edit/Write on .ts/.tsx files, filters out
# pre-existing errors listed in .typecheck-baseline, and surfaces only
# NEW type errors to Claude.
#
# Exit codes:
#   0 - no new errors (or not a TS file, or no tsconfig found)
#   2 - new type errors found (shown to Claude as feedback, non-blocking)
#
# Stdin: Claude Code PostToolUse JSON (contains tool_input.file_path)

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Parse the edited file path from stdin JSON
# ---------------------------------------------------------------------------
input="$(cat)"

# If stdin is empty (e.g. manual testing), exit cleanly
if [[ -z "$input" ]]; then
  exit 0
fi

file_path="$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)"

# If we couldn't extract a file path, exit cleanly
if [[ -z "$file_path" ]]; then
  exit 0
fi

# Only check .ts and .tsx files
case "$file_path" in
  *.ts|*.tsx) ;;
  *) exit 0 ;;
esac

# ---------------------------------------------------------------------------
# 2. Locate the nearest tsconfig.json
# ---------------------------------------------------------------------------
find_tsconfig() {
  local dir="$1"
  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/tsconfig.json" ]]; then
      echo "$dir/tsconfig.json"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}

file_dir="$(dirname "$file_path")"
tsconfig="$(find_tsconfig "$file_dir" 2>/dev/null || true)"

if [[ -z "$tsconfig" ]]; then
  # No tsconfig found; nothing to check
  exit 0
fi

project_dir="$(dirname "$tsconfig")"

# ---------------------------------------------------------------------------
# 3. Run tsc --noEmit
# ---------------------------------------------------------------------------
tsc_output=""
tsc_exit=0

# Prefer project-local npx, fall back to global tsc
if command -v npx &>/dev/null; then
  tsc_output="$(cd "$project_dir" && npx tsc --noEmit 2>&1)" || tsc_exit=$?
elif command -v tsc &>/dev/null; then
  tsc_output="$(cd "$project_dir" && tsc --noEmit -p "$tsconfig" 2>&1)" || tsc_exit=$?
else
  # No TypeScript compiler available
  exit 0
fi

# If tsc succeeded (no errors), exit cleanly
if [[ $tsc_exit -eq 0 ]]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# 4. Filter against baseline if it exists
# ---------------------------------------------------------------------------
baseline_file="$project_dir/.typecheck-baseline"
new_errors=""

if [[ -f "$baseline_file" ]]; then
  # Build a grep pattern file from non-empty, non-comment lines in baseline
  baseline_patterns="$(mktemp)"
  trap 'rm -f "$baseline_patterns"' EXIT
  grep -v '^\s*#' "$baseline_file" | grep -v '^\s*$' > "$baseline_patterns" || true

  if [[ -s "$baseline_patterns" ]]; then
    # Filter out lines matching any baseline pattern (grep -F for literal match)
    new_errors="$(echo "$tsc_output" | grep -vFf "$baseline_patterns" | grep -E '\.tsx?\(' || true)"
  else
    # Baseline file exists but has no patterns; all errors are "new"
    new_errors="$(echo "$tsc_output" | grep -E '\.tsx?\(' || true)"
  fi
else
  # No baseline; all errors are new
  new_errors="$(echo "$tsc_output" | grep -E '\.tsx?\(' || true)"
fi

# ---------------------------------------------------------------------------
# 5. Report results
# ---------------------------------------------------------------------------
if [[ -z "$new_errors" ]]; then
  # All errors are known/baselined; exit cleanly
  exit 0
fi

# Count new errors
error_count="$(echo "$new_errors" | wc -l | tr -d ' ')"

# Output to stderr (exit 2 sends stderr to Claude as feedback)
cat >&2 <<EOF
typecheck-hook: $error_count NEW type error(s) after editing $file_path

$new_errors

Tip: If these are pre-existing errors, add their patterns to $baseline_file
EOF

exit 2
