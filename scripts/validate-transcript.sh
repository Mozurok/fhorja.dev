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
#   - the "Run now: /<name>" basename resolves to a real command, in either
#     shape: commands/<name>.md or commands/<name>/SKILL.md
#   - the terminal form "Run now: none" (ADR-0126) names no command and is
#     paired with "Mode: N/A", checked in both directions
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
      run_now_value="$(printf '%s' "$run_now_line" | sed -E 's/^Run now:[[:space:]]*//; s/[[:space:]]+$//' | tr -d '\r')"
      # A handoff may carry flags, and exactly one in the catalog does:
      # `Run now: branch-commit --apply` (commands/implement-approved-slice.md, the ADR-0159
      # Express lock). Cut the argument list BEFORE resolving. The previous form ran
      # `tr -d '[:space:]'` over the whole value, which glued the flag to the name and asked
      # the filesystem for `branch-commit--apply.md`: the one handoff the spine tells a run to
      # emit was the one this validator rejected, measured 2026-08-30 at exit 1.
      run_now_value="${run_now_value%% *}"
      case "$run_now_value" in
        /*) command_basename="${run_now_value#/}" ;;
        *)  command_basename="$run_now_value" ;;
      esac

      # ADR-0126. `none` is the one value that names no command: it declares the
      # chain ended. The pairing with `Mode: N/A` is checked in both directions,
      # because this script does not otherwise validate the mode value, so the
      # pairing is the only thing keeping `N/A` from becoming a general escape.
      local mode_value=""
      if [[ -n "$mode_line" ]]; then
        mode_value="$(printf '%s' "$mode_line" | sed -E 's/^Mode:[[:space:]]*//')"
      fi

      if [[ "$command_basename" == "none" ]]; then
        if [[ "$mode_value" != "N/A" ]]; then
          printf '%s\n' "terminal Handoff (Run now: none) requires Mode: N/A, got: '${mode_value}'"
          has_failure=1
        fi
      elif [[ -z "$command_basename" ]]; then
        printf '%s\n' "Handoff Run now field names no command: '${run_now_value}'"
        has_failure=1
      elif [[ ! -f "${commands_dir}/${command_basename}.md" \
           && ! -f "${commands_dir}/${command_basename}/SKILL.md" ]]; then
        # Nine commands ship folder-shaped as <name>/SKILL.md. Checking only the
        # flat form rejected every one of them; the driver's own parser has
        # always accepted both, so this script was the stricter of the two.
        printf '%s\n' "Run now basename does not resolve to a real command: ${command_basename} (expected ${commands_dir}/${command_basename}.md or ${commands_dir}/${command_basename}/SKILL.md)"
        has_failure=1
      elif [[ "$mode_value" == "N/A" ]]; then
        printf '%s\n' "Mode: N/A is valid only with 'Run now: none'; this Handoff routes to ${command_basename}"
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

  cat >"${self_test_dir}/handoff_with_flag.md" <<'EOF'
### Artifact changes
- TASK_STATE.md: APPLIED

### Command transcript
Last slice implemented; routing to the apply commit.

### Handoff
Run now: branch-commit --apply
Mode: Agent
Work complexity: LOW
Reason: The last slice is done; create the local commit.
EOF

  cat >"${self_test_dir}/mutation_invented_command_with_flag.md" <<'EOF'
### Artifact changes
None

### Command transcript
Routing to a command that does not exist, with an argument attached.

### Handoff
Run now: not-a-real-command --apply
Mode: Agent
Work complexity: LOW
Reason: Cutting the argument list must not turn an invented name into a pass.
EOF

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

  cat >"${self_test_dir}/terminal.md" <<'EOF'
### Artifact changes
None

### Command transcript
Nothing left that a following command could honestly do.

### Handoff
Run now: none
Mode: N/A
Work complexity: N/A
Reason: three decisions need a maintainer and the rest needs an environment this session lacks.
EOF

  cat >"${self_test_dir}/mutation_terminal_routing_mode.md" <<'EOF'
### Artifact changes
None

### Command transcript
Some transcript text.

### Handoff
Run now: none
Mode: Ask, when a maintainer is present
Work complexity: N/A
Reason: test.
EOF

  cat >"${self_test_dir}/mutation_na_mode_while_routing.md" <<'EOF'
### Artifact changes
None

### Command transcript
Some transcript text.

### Handoff
Run now: /task-init
Mode: N/A
Work complexity: LOW
Reason: test.
EOF

  cat >"${self_test_dir}/folder_shaped_command.md" <<'EOF'
### Artifact changes
None

### Command transcript
Routing to a command that ships as <name>/SKILL.md rather than <name>.md.

### Handoff
Run now: /a11y-audit
Mode: Ask
Work complexity: LOW
Reason: nine commands are folder-shaped and the Run now line must resolve for them too.
EOF

  check_fixture "conforming (Mode A)" "${self_test_dir}/conforming.md" 0 "" "$self_test_commands_dir" || overall_rc=1
  check_fixture "terminal form (ADR-0126)" "${self_test_dir}/terminal.md" 0 "" "$self_test_commands_dir" || overall_rc=1
  check_fixture "folder-shaped command basename" "${self_test_dir}/folder_shaped_command.md" 0 "" "$self_test_commands_dir" || overall_rc=1
  check_fixture "NO_OP with NO_OP_TRACE" "${self_test_dir}/no_op.md" 0 "" "$self_test_commands_dir" || overall_rc=1
  check_fixture "Mode B with Resume context" "${self_test_dir}/mode_b.md" 0 "" "$self_test_commands_dir" || overall_rc=1
  check_fixture "mutation: missing Handoff" "${self_test_dir}/mutation_missing_handoff.md" 1 "### Handoff" "$self_test_commands_dir" || overall_rc=1
  check_fixture "mutation: swapped section order" "${self_test_dir}/mutation_swapped_order.md" 1 "out of order" "$self_test_commands_dir" || overall_rc=1
  check_fixture "mutation: invalid Work complexity value" "${self_test_dir}/mutation_invalid_complexity.md" 1 "invalid Work complexity value" "$self_test_commands_dir" || overall_rc=1
  check_fixture "mutation: invented command basename" "${self_test_dir}/mutation_invented_command.md" 1 "does not resolve to a real command" "$self_test_commands_dir" || overall_rc=1
  check_fixture "mutation: terminal form with a routing mode" "${self_test_dir}/mutation_terminal_routing_mode.md" 1 "requires Mode: N/A" "$self_test_commands_dir" || overall_rc=1
  check_fixture "mutation: Mode N/A on a routing handoff" "${self_test_dir}/mutation_na_mode_while_routing.md" 1 "valid only with" "$self_test_commands_dir" || overall_rc=1
  # ADR-0159 emits `Run now: branch-commit --apply`, the one handoff in the catalog that carries a
  # flag. Both halves are asserted: the flag form must resolve, AND cutting the argument list must
  # not turn an invented name into a pass, which is the way this fix could have loosened the check.
  check_fixture "handoff carrying a flag (ADR-0159)" "${self_test_dir}/handoff_with_flag.md" 0 "" "$self_test_commands_dir" || overall_rc=1
  check_fixture "mutation: invented command with a flag" "${self_test_dir}/mutation_invented_command_with_flag.md" 1 "does not resolve to a real command" "$self_test_commands_dir" || overall_rc=1

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
