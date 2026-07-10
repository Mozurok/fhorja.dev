#!/usr/bin/env bash
# classify-slice.sh -- Fhorja autonomy track slice classifier (ADR-0044, D6/D12).
#
# Given the file set a slice would touch, decide whether the autonomous loop
# may auto-advance the slice or MUST escalate it to the human gate.
#
# Policy (default-deny): a slice auto-advances ONLY when every file in its set
# is provably free of boundary paths (schema, migration, contract, security)
# and free of test/eval paths. Any boundary or test/eval file, an unknown
# path, an empty input, or an argument that contains whitespace (a sign the
# caller joined several paths into one argument) forces "escalate". This is the
# conservative direction on purpose: a false "auto" is the dangerous failure,
# and the caller is an LLM, not a careful script (POC finding 2026-06-16).
#
# Usage:   classify-slice.sh <file> [<file> ...]
#   or:    printf '%s\n' file1 file2 | classify-slice.sh -
# Output:  "VERDICT: escalate" or "VERDICT: auto", plus one reason line per hit.
# Exit:    0 = auto-advance allowed, 10 = escalate. (No other nonzero is a verdict.)

set -euo pipefail

BOUNDARY_RE='(^|/)(migrations?|schema|schemas)(/|$)|\.(sql|prisma|graphql|proto)$|(^|/)(auth|security|rls|permissions?|secrets?|credentials?)(/|$)|(^|/)(openapi|swagger)|(^|/)api/|\.env(\.|$)'
TEST_RE='(^|/)(tests?|__tests__|e2e|evals?)(/|$)|\.(test|spec)\.|(^|/)[^/]*[._-](test|spec)\.|\.feature$|(^|/)evals/scenarios/'

files=()
if [[ "${1:-}" == "-" ]]; then
  while IFS= read -r line; do [[ -n "$line" ]] && files+=("$line"); done
else
  files=("$@")
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "VERDICT: escalate"
  echo "reason: empty file set (cannot prove the slice is safe)"
  exit 10
fi

reasons=()
for f in "${files[@]}"; do
  if [[ "$f" =~ [[:space:]] ]]; then
    reasons+=("malformed argument -> escalate (pass one path per argument): $f")
  elif [[ "$f" =~ $TEST_RE ]]; then
    reasons+=("test-or-eval path -> escalate (D12): $f")
  elif [[ "$f" =~ $BOUNDARY_RE ]]; then
    reasons+=("boundary path -> escalate (D6): $f")
  fi
done

if [[ ${#reasons[@]} -gt 0 ]]; then
  echo "VERDICT: escalate"
  for r in "${reasons[@]}"; do echo "reason: $r"; done
  exit 10
fi

echo "VERDICT: auto"
echo "reason: all ${#files[@]} file(s) are non-boundary and non-test"
exit 0
