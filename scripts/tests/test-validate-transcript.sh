#!/usr/bin/env bash
# test-validate-transcript.sh -- runs the handoff validator's own self-test.
#
# Why this wrapper exists. `scripts/validate-transcript.sh --self-test` has carried fixtures since
# it was written, and measured 2026-08-30, NOTHING executed it: not the CI workflow, not
# lint-commands.sh, not scripts/tests/. That is the decoration ADR-0143 named, and it is how the
# validator came to reject `Run now: branch-commit --apply` (the one flag-carrying handoff in the
# catalog, emitted by the ADR-0159 Express lock) without any suite going red.
#
# The CI allowlist runs every suite bare, so the flag lives here rather than in the workflow file:
# the wrapper is the adapter between "runs with no arguments" and a script whose self-test is a
# flag. It asserts the exit code and nothing else; the fixtures and their expectations stay in the
# validator, next to the code they check.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT" || exit 2

TARGET="scripts/validate-transcript.sh"
if [[ ! -x "$TARGET" ]]; then
  echo "FAIL - $TARGET is missing or not executable"
  exit 1
fi

output="$(bash "$TARGET" --self-test 2>&1)"
rc=$?
printf '%s\n' "$output"

# An empty run is a failure, not a pass: the self-test prints one line per fixture, so zero PASS
# lines means the harness stopped reporting rather than that everything is fine.
pass_count="$(printf '%s\n' "$output" | grep -c '^PASS:' || true)"
if (( pass_count == 0 )); then
  echo "FAIL - the self-test reported no fixtures at all"
  exit 1
fi

if (( rc != 0 )); then
  echo "FAIL - validate-transcript.sh --self-test exited $rc"
  exit 1
fi

echo
echo "test-validate-transcript: self-test passed, $pass_count fixture(s) reported"
