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
# Usage:   classify-slice.sh [--decisions <file>] <file> [<file> ...]
#   or:    printf '%s\n' f1 f2 | classify-slice.sh [--decisions <file>] -
# Output:  "VERDICT: escalate" or "VERDICT: auto", plus one reason line per hit.
# Exit:    0 = auto-advance allowed, 10 = escalate. (No other nonzero is a verdict.)
#
# --decisions is OPTIONAL and REPORTING ONLY (D-4). With no such file the script
# behaves exactly as it did before the flag existed. With one, a boundary hit
# that a locked decision already covers gets ONE EXTRA reason line naming that
# decision, so the morning reviewer can see which escalations were already
# decided. It cannot turn an escalate into an auto: the annotation only ever
# APPENDS to the reason list, and any non-empty reason list is an escalate.

set -euo pipefail

BOUNDARY_RE='(^|/)(migrations?|schema|schemas)(/|$)|\.(sql|prisma|graphql|proto)$|(^|/)(auth|security|rls|permissions?|secrets?|credentials?)(/|$)|(^|/)(openapi|swagger)|(^|/)api/|\.env(\.|$)'
TEST_RE='(^|/)(tests?|__tests__|e2e|evals?)(/|$)|\.(test|spec)\.|(^|/)[^/]*[._-](test|spec)\.|\.feature$|(^|/)evals/scenarios/'

DECISIONS_FILE=""
args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --decisions)
      DECISIONS_FILE="${2:-}"
      shift
      if [[ $# -gt 0 ]]; then shift; fi
      ;;
    --decisions=*)
      DECISIONS_FILE="${1#--decisions=}"
      shift
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

files=()
if [[ "${args[0]:-}" == "-" ]]; then
  while IFS= read -r line; do [[ -n "$line" ]] && files+=("$line"); done
elif [[ ${#args[@]} -gt 0 ]]; then
  files=("${args[@]}")
fi

# decisions_covering <path> -- print the id of every locked decision whose text
# references <path> or its directory, one per line. Grep-shaped on purpose: a
# block starts at "### D-<n>", counts as locked when it carries a "Locked:"
# line, and covers the path when its text contains that path or its directory
# verbatim. Deliberately not a parser, and deliberately incapable of changing a
# verdict: it only ever prints identifiers.
# ref_at_path_boundary <line> <ref> <kind> -- true when <ref> occurs in <line>
# at a path boundary rather than glued inside a longer word. kind=dir also
# requires a trailing "/". Pure string comparison on purpose: no regex, so no
# metacharacter escaping to get wrong in a script whose value is predictability.
# Fixes the substring class the wave-1 integration gate caught (2026-07-27): a
# decision whose only "auth" sat inside "agent-authored" annotated a path under
# auth/. Annotation-only either way; this never touched a verdict.
ref_at_path_boundary() {
  local line="$1" ref="$2" kind="$3"
  local needle="$ref" rest="$line" before prev after next
  [[ "$kind" == "dir" ]] && needle="$ref/"
  [[ -n "$needle" ]] || return 1
  while [[ "$rest" == *"$needle"* ]]; do
    before="${rest%%"$needle"*}"
    after="${rest#*"$needle"}"
    prev="${before: -1}"
    next="${after:0:1}"
    if [[ -z "$prev" || "$prev" != [A-Za-z0-9_] ]]; then
      if [[ "$kind" == "dir" || -z "$next" || "$next" != [A-Za-z0-9_] ]]; then
        return 0
      fi
    fi
    rest="$after"
  done
  return 1
}

decisions_covering() {
  local path="$1"
  [[ -n "$DECISIONS_FILE" && -f "$DECISIONS_FILE" && -r "$DECISIONS_FILE" ]] || return 0
  local dir=""
  case "$path" in */*) dir="${path%/*}" ;; esac
  case "$dir" in .|/) dir="" ;; esac
  local id="" hit=0 locked=0 line
  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      '### D-'*)
        if [[ $hit -eq 1 && $locked -eq 1 ]]; then echo "$id"; fi
        id="${line#\#\#\# }"
        id="${id%%:*}"
        hit=0
        locked=0
        ;;
      'Locked:'*)
        locked=1
        ;;
    esac
    if [[ -n "$id" ]]; then
      if ref_at_path_boundary "$line" "$path" path; then
        hit=1
      elif [[ -n "$dir" ]] && ref_at_path_boundary "$line" "$dir" dir; then
        hit=1
      fi
    fi
  done < "$DECISIONS_FILE"
  if [[ $hit -eq 1 && $locked -eq 1 ]]; then echo "$id"; fi
  return 0
}

if [[ ${#files[@]} -eq 0 ]]; then
  echo "VERDICT: escalate"
  echo "reason: empty file set (cannot prove the slice is safe)"
  exit 10
fi

reasons=()
for f in "${files[@]}"; do
  if [[ -z "$f" ]]; then
    reasons+=("empty argument -> escalate (pass one non-empty path per argument)")
  elif [[ "$f" =~ [[:space:]] ]]; then
    reasons+=("malformed argument -> escalate (pass one path per argument): $f")
  elif [[ "$f" =~ $TEST_RE ]]; then
    reasons+=("test-or-eval path -> escalate (D12): $f")
  elif [[ "$f" =~ $BOUNDARY_RE ]]; then
    reasons+=("boundary path -> escalate (D6): $f")
    covering="$(decisions_covering "$f")"
    if [[ -n "$covering" ]]; then
      while IFS= read -r did; do
        [[ -n "$did" ]] || continue
        reasons+=("covered by $did (locked) -> annotation only, verdict unchanged: $f")
      done <<< "$covering"
    fi
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
