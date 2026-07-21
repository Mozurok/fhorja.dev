#!/usr/bin/env bash
# check-claim-grounding.sh -- Fhorja active-epistemic-humility advisory (warn-only)
#
# The D-11 script-checkable surface of ADR-0109. ADVISORY ONLY: never fails a
# build, never exits non-zero on hits (mirrors check-natural-voice.sh).
#
# What it CAN check (and does): the D-2 regression guard. D-2 locked that the
# doctrine SHALL NOT gate on self-reported confidence -- no confidence field, no
# numeric confidence threshold, no self-assessment prompt. That is the single
# most counterintuitive decision in the doctrine, and the one a future
# well-meaning edit is most likely to quietly reverse. This scans the doctrine's
# own source surfaces for a confidence-field pattern and flags it. Shared-block
# drift (lint-commands.sh) only checks the block matches its canonical copy
# across commands; it does NOT check the canonical block, the spec H3, or the
# wos topic stay free of a confidence field, so this guard is not redundant.
#
# What it CANNOT check (and does not pretend to): whether a real command OUTPUT
# carried a provenance referent on its claims, or whether an abstention was
# genuine. Lint sees command FILES, not model OUTPUTS, and this script does not
# run a model. That deeper enforcement is manual-tier by construction, covered
# by the paired abstention eval scenarios (run-evals.sh), and recorded as a
# permanent gap in the task's TEST_STRATEGY.md. Do not extend this script to
# claim otherwise.
#
# Surfaces scanned (the doctrine's source-of-truth, not the 85 propagated copies):
#   commands/_shared/claim-grounding.md
#   wos/active-epistemic-humility.md
#   the '### Claim status and abstention' H3 in WORKFLOW_OPERATING_SYSTEM.md
#
# Usage:  scripts/check-claim-grounding.sh [--verbose]
# Summary line (parsed by lint-commands.sh):
#   claim-grounding: N advisory hit(s) across M file(s)
#   claim-grounding: clean

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERBOSE=0
[ "${1:-}" = "--verbose" ] && VERBOSE=1

# A confidence-field pattern that would violate D-2. Deliberately narrow to
# avoid false positives on prose that merely mentions the word "confidence"
# while forbidding it (the doctrine itself says "no confidence field"): match
# only an ASSIGNMENT-shaped or scored form, not a bare mention.
#   confidence: high        confidence: 0.8        confidence: 80%
#   confidence level: ...    confidence score ...   confidence threshold of <n>
# The doctrine's own forbidding sentences ("SHALL NOT ... a confidence degree",
# "no confidence field") do not match, because they are not assignment-shaped.
PATTERN='confidence[ _-]?(field|score|level|threshold)?[ ]*[:=][ ]*("?(high|medium|low)"?|[0-9]|0\.[0-9]|[0-9]+%)'

hits=0
files_with_hits=0

scan_file() {
  local f="$1" label="$2"
  [ -f "$f" ] || return 0
  local body="$3"   # optional: pre-extracted body; empty means whole file
  local content
  if [ -n "$body" ]; then content="$body"; else content="$(cat "$f")"; fi
  local n
  n="$(printf '%s\n' "$content" | grep -icE "$PATTERN" || true)"
  if [ "$n" -gt 0 ]; then
    hits=$((hits + n))
    files_with_hits=$((files_with_hits + 1))
    if [ "$VERBOSE" -eq 1 ]; then
      printf '%s\n' "$content" | grep -inE "$PATTERN" | while IFS= read -r line; do
        echo "  ${label}: ${line}" >&2
      done
    fi
  fi
}

scan_file "${REPO}/commands/_shared/claim-grounding.md" "claim-grounding.md" ""
scan_file "${REPO}/wos/active-epistemic-humility.md" "active-epistemic-humility.md" ""

# The spec H3 only, not the whole 1600-line spec.
spec="${REPO}/WORKFLOW_OPERATING_SYSTEM.md"
if [ -f "$spec" ]; then
  h3="$(awk '/^### Claim status and abstention/{f=1; print; next} f&&/^### /{f=0} f{print}' "$spec")"
  scan_file "$spec" "spec ### Claim status and abstention" "$h3"
fi

if [ "$hits" -eq 0 ]; then
  echo "claim-grounding: clean"
else
  echo "claim-grounding: ${hits} advisory hit(s) across ${files_with_hits} file(s)"
fi
exit 0
