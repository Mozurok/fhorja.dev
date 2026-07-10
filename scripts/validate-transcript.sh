#!/usr/bin/env bash
# validate-transcript.sh
#
# Validates one live Fhorja command transcript (a markdown file, passed as $1)
# against the Standard command output layout contract in
# WORKFLOW_OPERATING_SYSTEM.md -> ## Global output contract. It checks:
#   - presence and order of ### Artifact changes, ### Command transcript,
#     ### Handoff
#   - the Handoff block carries the fields Run now, Mode, Work complexity,
#     Reason
#   - the Work complexity value is exactly one of LOW, MEDIUM, HIGH, N/A
#   - the "Run now: /<name>" basename resolves to a real commands/<name>.md
#   - NO_OP outputs (NO_OP_TRACE in the Command transcript) and Mode B
#     handoffs (a Resume context: block) are conforming, not special cases:
#     they pass the same checks as any other transcript, no extra branches
#
# On failure: prints the exact missing or malformed element, one line per
# failure, and exits 1. This mirrors instructor's validate-then-retry
# pattern (REFERENCES.md "Instructor: Re-asking and validation"): the error
# message IS the retry payload, so the caller can feed it straight back.
# On success: silent, exit 0.
#
# Usage:
#   validate-transcript.sh <transcript.md> [commands_dir]
#   validate-transcript.sh --self-test
#
# The commands dir is resolved relative to this script's location
# (../commands) by default. Override with the second positional argument,
# or the WOS_COMMANDS_DIR environment variable (the positional argument
# wins when both are given).
#
# Exit codes:
#   0 = transcript (or, under --self-test, every fixture) conforms
#   1 = at least one mandated block, field, or enum value is missing or
#       malformed (or, under --self-test, a fixture behaved unexpectedly)
#   2 = invocation error (missing transcript file argument)
#
# Bash 3.2 compatible (macOS default): no associative arrays, no mapfile.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_COMMANDS_DIR="${SCRIPT_DIR}/../commands"
VALID_COMPLEXITY_VALUES=(LOW MEDIUM HIGH N/A)

# ---------------------------------------------------------------------------
# validate_transcript <transcript_file> <commands_dir>
#
# Prints one failure line per missing or malformed element to stdout.
# Returns 0 when the transcript conforms, 1 otherwise.
# ---------------------------------------------------------------------------
validate_transcript() {
  local transcript_file="$1"
  local commands_dir="$2"
  local has_failure=0

  if [[ ! -f "$transcript_file" ]]; then
    printf '%s\n' "missing transcript file: ${transcript_file}"
    return 1
  fi

  local artifact_line transcript_line handoff_line
  artifact_line="$(grep -n '^### Artifact changes$' "$transcript_file" | head -1 | cut -d: -f1 || true)"
  transcript_line="$(grep -n '^### Command transcript$' "$transcript_file" | head -1 | cut -d: -f1 || true)"
  handoff_line="$(grep -n '^### Handoff$' "$transcript_file" | head -1 | cut -d: -f1 || true)"

  if [[ -z "$artifact_line" ]]; then
    printf '%s\n' "missing mandated block: ### Artifact changes"
    has_failure=1
  fi
  if [[ -z "$transcript_line" ]]; then
    printf '%s\n' "missing mandated block: ### Command transcript"
    has_failure=1
  fi
  if [[ -z "$handoff_line" ]]; then
    printf '%s\n' "missing mandated block: ### Handoff"
    has_failure=1
  fi

  if [[ -n "$artifact_line" && -n "$transcript_line" && -n "$handoff_line" ]]; then
    if [[ ! ( "$artifact_line" -lt "$transcript_line" && "$transcript_line" -lt "$handoff_line" ) ]]; then
      printf '%s\n' "mandated blocks out of order: expected ### Artifact changes (line ${artifact_line}) before ### Command transcript (line ${transcript_line}) before ### Handoff (line ${handoff_line})"
      has_failure=1
    fi
  fi

  if [[ -n "$handoff_line" ]]; then
    local handoff_body next_heading_offset
    handoff_body="$(sed -n "${handoff_line},\$p" "$transcript_file" | tail -n +2)"
    next_heading_offset="$(printf '%s\n' "$handoff_body" | grep -n '^### ' | head -1 | cut -d: -f1 || true)"
    if [[ -n "$next_heading_offset" ]]; then
      handoff_body="$(printf '%s\n' "$handoff_body" | sed -n "1,$((next_heading_offset - 1))p")"
    fi

    local run_now_line mode_line complexity_line reason_line
    run_now_line="$(printf '%s\n' "$handoff_body" | grep -m1 '^Run now:' || true)"
    mode_line="$(printf '%s\n' "$handoff_body" | grep -m1 '^Mode:' || true)"
    complexity_line="$(printf '%s\n' "$handoff_body" | grep -m1 '^Work complexity:' || true)"
    reason_line="$(printf '%s\n' "$handoff_body" | grep -m1 '^Reason:' || true)"

    if [[ -z "$run_now_line" ]]; then
      printf '%s\n' "Handoff missing required field: Run now"
      has_failure=1
    fi
    if [[ -z "$mode_line" ]]; then
      printf '%s\n' "Handoff missing required field: Mode"
      has_failure=1
    fi
    if [[ -z "$complexity_line" ]]; then
      printf '%s\n' "Handoff missing required field: Work complexity"
      has_failure=1
    fi
    if [[ -z "$reason_line" ]]; then
      printf '%s\n' "Handoff missing required field: Reason"
      has_failure=1
    fi

    if [[ -n "$complexity_line" ]]; then
      local complexity_value is_valid v
      complexity_value="$(printf '%s' "$complexity_line" | sed -E 's/^Work complexity:[[:space:]]*//')"
      is_valid=0
      for v in "${VALID_COMPLEXITY_VALUES[@]}"; do
        if [[ "$complexity_value" == "$v" ]]; then
          is_valid=1
          break
        fi
      done
      if [[ "$is_valid" -ne 1 ]]; then
        printf '%s\n' "invalid Work complexity value: '${complexity_value}' (must be exactly one of LOW, MEDIUM, HIGH, N/A)"
        has_failure=1
      fi
    fi

    if [[ -n "$run_now_line" ]]; then
      local run_now_value command_basename
      run_now_value="$(printf '%s' "$run_now_line" | sed -E 's/^Run now:[[:space:]]*//')"
      case "$run_now_value" in
        /*) command_basename="${run_now_value#/}" ;;
        *)  command_basename="$run_now_value" ;;
      esac
      command_basename="$(printf '%s' "$command_basename" | tr -d '[:space:]')"

      if [[ -z "$command_basename" ]]; then
        printf '%s\n' "Handoff Run now field names no command: '${run_now_value}'"
        has_failure=1
      elif [[ ! -f "${commands_dir}/${command_basename}.md" ]]; then
        printf '%s\n' "Run now basename does not resolve to a real command: ${command_basename} (expected ${commands_dir}/${command_basename}.md)"
        has_failure=1
      fi
    fi
  fi

  return "$has_failure"
}

# ---------------------------------------------------------------------------
# Self-test: an embedded fixture suite (conforming, NO_OP, Mode B, plus four
# mutations) exercised against validate_transcript. Reports pass/fail per
# fixture; exits 0 only when every fixture behaves as expected.
# ---------------------------------------------------------------------------
check_fixture() {
  local name="$1"
  local file="$2"
  local expected_exit="$3"
  local expected_substring="$4"
  local commands_dir="$5"
  local actual_output actual_exit

  actual_output="$(validate_transcript "$file" "$commands_dir")" && actual_exit=0 || actual_exit=$?

  if [[ "$actual_exit" -ne "$expected_exit" ]]; then
    printf 'FAIL: %s (expected exit %s, got %s)\n' "$name" "$expected_exit" "$actual_exit"
    printf '%s\n' "$actual_output"
    return 1
  fi

  if [[ -n "$expected_substring" ]]; then
    if ! printf '%s\n' "$actual_output" | grep -qF "$expected_substring"; then
      printf 'FAIL: %s (expected failure output to contain: %s)\n' "$name" "$expected_substring"
      printf 'actual output:\n%s\n' "$actual_output"
      return 1
    fi
  fi

  printf 'PASS: %s\n' "$name"
  return 0
}

run_self_test() {
  local self_test_dir overall_rc=0
  local self_test_commands_dir="$DEFAULT_COMMANDS_DIR"
  self_test_dir="$(mktemp -d "${TMPDIR:-/tmp}/validate-transcript-selftest.XXXXXX")"
  trap 'rm -rf "$self_test_dir"' RETURN

  cat >"${self_test_dir}/conforming.md" <<'EOF'
### Artifact changes
- TASK_STATE.md: PROPOSED

### Command transcript
Reviewed current state; no material change beyond routing.

### Handoff
Run now: /task-init
Mode: Agent
Work complexity: LOW
Reason: Starting a fresh task folder.
EOF

  cat >"${self_test_dir}/no_op.md" <<'EOF'
### Artifact changes
None

### Command transcript
NO_OP_TRACE: no material change since last run; routing unchanged.

### Handoff
Run now: /what-next
Mode: Ask
Work complexity: N/A
Reason: Nothing changed; re-check routing next session.
EOF

  cat >"${self_test_dir}/mode_b.md" <<'EOF'
### Artifact changes
- TASK_STATE.md: APPLIED

### Command transcript
Slice 2 implemented; state synced ahead of a session break.

### Handoff
Run now: /slice-closure
Mode: Agent
Work complexity: MEDIUM
Reason: Slice work is done; closure judgment is next.
Resume context:
- Task: projects/acme__demo/active/2026-07-01_example-task/
- Workspace: /path/to/product/repo
- Current slice: 02 example-slice
- Key decisions: D-1
EOF

  cat >"${self_test_dir}/mutation_missing_handoff.md" <<'EOF'
### Artifact changes
None

### Command transcript
NO_OP_TRACE: nothing changed.
EOF

  cat >"${self_test_dir}/mutation_swapped_order.md" <<'EOF'
### Command transcript
Some transcript text.

### Artifact changes
None

### Handoff
Run now: /task-init
Mode: Agent
Work complexity: LOW
Reason: test.
EOF

  cat >"${self_test_dir}/mutation_invalid_complexity.md" <<'EOF'
### Artifact changes
None

### Command transcript
Some transcript text.

### Handoff
Run now: /task-init
Mode: Agent
Work complexity: SEVERE
Reason: test.
EOF

  cat >"${self_test_dir}/mutation_invented_command.md" <<'EOF'
### Artifact changes
None

### Command transcript
Some transcript text.

### Handoff
Run now: /definitely-not-a-real-command
Mode: Agent
Work complexity: LOW
Reason: test.
EOF

  check_fixture "conforming (Mode A)" "${self_test_dir}/conforming.md" 0 "" "$self_test_commands_dir" || overall_rc=1
  check_fixture "NO_OP with NO_OP_TRACE" "${self_test_dir}/no_op.md" 0 "" "$self_test_commands_dir" || overall_rc=1
  check_fixture "Mode B with Resume context" "${self_test_dir}/mode_b.md" 0 "" "$self_test_commands_dir" || overall_rc=1
  check_fixture "mutation: missing Handoff" "${self_test_dir}/mutation_missing_handoff.md" 1 "### Handoff" "$self_test_commands_dir" || overall_rc=1
  check_fixture "mutation: swapped section order" "${self_test_dir}/mutation_swapped_order.md" 1 "out of order" "$self_test_commands_dir" || overall_rc=1
  check_fixture "mutation: invalid Work complexity value" "${self_test_dir}/mutation_invalid_complexity.md" 1 "invalid Work complexity value" "$self_test_commands_dir" || overall_rc=1
  check_fixture "mutation: invented command basename" "${self_test_dir}/mutation_invented_command.md" 1 "does not resolve to a real command" "$self_test_commands_dir" || overall_rc=1

  if [[ "$overall_rc" -eq 0 ]]; then
    printf 'self-test: all fixtures behaved as expected\n'
  else
    printf 'self-test: one or more fixtures behaved unexpectedly\n'
  fi
  return "$overall_rc"
}

main() {
  if [[ "${1:-}" == "--self-test" ]]; then
    run_self_test
    exit $?
  fi

  if [[ $# -lt 1 ]]; then
    printf 'usage: %s <transcript.md> [commands_dir]\n' "$(basename "$0")" >&2
    printf '       %s --self-test\n' "$(basename "$0")" >&2
    exit 2
  fi

  local transcript_file="$1"
  local commands_dir="${2:-${WOS_COMMANDS_DIR:-$DEFAULT_COMMANDS_DIR}}"
  commands_dir="$(cd "$commands_dir" 2>/dev/null && pwd || printf '%s' "$commands_dir")"

  local output rc
  output="$(validate_transcript "$transcript_file" "$commands_dir")" && rc=0 || rc=$?

  if [[ "$rc" -ne 0 ]]; then
    printf '%s\n' "$output"
    exit 1
  fi

  exit 0
}

main "$@"
