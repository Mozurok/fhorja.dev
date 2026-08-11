#!/usr/bin/env bash
# test-branch-commit-unchanged.sh -- asserts D-4 of the ref-attested commit-evidence
# task: `commands/branch-commit.md` does not change. Run from anywhere:
#   bash scripts/tests/test-branch-commit-unchanged.sh <base-ref>
#
# <base-ref> is REQUIRED and is the commit the task STARTED from. For the task behind
# D-4 that is d45177d. See the block above the argument check for why there is no default.
#
# Why this exists. D-4 lived only in a STOP condition on a slice, which halts an
# executor and asserts nothing afterwards; `approve-plan` named that as a coverage gap
# and TEST_STRATEGY row R2 is the answer. The file is the only path in this repository
# that can create a commit, and the ref-attested migration deliberately added a second
# evidence route WITHOUT touching it. A silent edit here would widen what an unattended
# run can reach, which is the one thing that decision refused.
#
# The check is `git diff --quiet -- <file>`: exit 0 when unchanged, 1 when it differs.
# Both directions are exercised below, so a green run is evidence the check can fail
# rather than evidence that it ran.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GUARDED="commands/branch-commit.md"
PASS=0; FAIL=0

ok()   { PASS=$((PASS+1)); echo "ok   - $1"; }
fail() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }

# The base is REQUIRED and has no default. It used to default to HEAD, and that made the
# check blind to the only way a D-4 violation actually ships. `git diff HEAD` compares the
# working tree to HEAD, so a change that is IN HEAD produces no diff: measured 2026-08-08,
# a clone whose `commands/branch-commit.md` had been edited AND committed reported
# "D-4 holds" and exited 0. A working-tree edit is transient; the committed one is the
# real failure, and the check passed on it while asserting the opposite.
#
# Refusing is better than guessing. A check that picks its own meaningless baseline is
# worse than one that will not run until told what to compare against, because the first
# emits a false affirmative and the second emits nothing.
if [[ $# -lt 1 ]]; then
  echo "usage: bash scripts/tests/test-branch-commit-unchanged.sh <base-ref>" >&2
  echo "  <base-ref> is the commit the task STARTED from, not HEAD. D-4 asserts the file" >&2
  echo "  is byte-identical across the task, which HEAD cannot establish once the task's" >&2
  echo "  own work is committed." >&2
  exit 2
fi
BASE="$1"

# 1. The real assertion: the guarded file is identical between the task's starting ref and
#    the working tree, which covers both committed and uncommitted change.
if git -C "$REPO_ROOT" diff --quiet "$BASE" -- "$GUARDED"; then
  ok "$GUARDED is byte-identical between $BASE and the working tree (D-4 holds)"
else
  fail "$GUARDED differs from $BASE; D-4 says that file does not change"
  git -C "$REPO_ROOT" diff --stat "$BASE" -- "$GUARDED" | sed 's/^/       /'
fi

# 2. Falsifiability, in a throwaway clone so the real tree is never touched. Without
#    this a green result would only prove the command ran, never that it can fail.
PROBE=$(mktemp -d)
trap 'rm -rf "$PROBE"' EXIT
if git clone --quiet --no-hardlinks --depth 1 "$REPO_ROOT" "$PROBE/repo" 2>/dev/null; then
  printf '\n<!-- probe: an edit D-4 forbids -->\n' >> "$PROBE/repo/$GUARDED"
  if git -C "$PROBE/repo" diff --quiet -- "$GUARDED"; then
    fail "the check did NOT bite on a mutated copy; it cannot detect a real edit"
  else
    ok "the check bites: a mutated copy exits non-zero"
  fi
else
  fail "could not clone into a probe directory; falsifiability unverified"
fi

echo
echo "test-branch-commit-unchanged: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]]
