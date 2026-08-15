#!/usr/bin/env bash
# check-gate-provenance.sh -- Fhorja gate-provenance advisory (warn-only)
#
# The D-2 script-checkable surface of ADR-0147. ADVISORY ONLY: never fails a
# build, never exits non-zero on hits (mirrors check-natural-voice.sh and
# check-claim-grounding.sh).
#
# What it checks, and why this one and not something broader.
#
# ADR-0147 records a measured pattern: when a dogfood produces a new GATE (a
# conditional that can block work or demand evidence), a rule that lands as an
# inline fold in a command body tends to carry a trigger written from the
# CIRCUMSTANCES where the failure was seen, while a rule that goes through an
# ADR tends to carry a trigger written from the MECHANISM it defeats, because
# the ADR template forces a scope rationale and an alternatives section. Four
# recurrence chains in docs/adr/ are the evidence.
#
# So the checkable proxy is provenance, not correctness: a conditional gate in a
# command body that cites no ADR is a gate whose scope boundary was never argued
# in a place that forces the argument. That is a prompt to check the trigger, not
# a defect by itself.
#
# What it CANNOT check, stated so nobody extends it wrongly:
#   - whether a trigger is actually mechanism-shaped. That is a judgment.
#   - whether a cited ADR argued the scope. It only sees that a cite exists.
#   - anything about model OUTPUTS. Lint sees command FILES. This script does
#     not run a model. Do not extend it to claim otherwise.
#
# An unconditional discipline (no WHEN, no trigger) is deliberately NOT flagged:
# a rule with no trigger has no trigger to under-scope, which is exactly the
# ADR-0147 D-1 carve-out.
#
# Usage: scripts/check-gate-provenance.sh [--verbose]
# Output (last line, machine-readable): "gate-provenance: clean"
#                                    or "gate-provenance: N uncited gate(s) across M file(s)"

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERBOSE=0
[ "${1:-}" = "--verbose" ] && VERBOSE=1

# A conditional gate: a WHEN trigger in the same line as a normative verb.
#
# Deliberately NOT `WHERE` or `IF`. Both were measured and both are dominated by
# shared-block text (`claim-grounding` rule 4 opens "WHERE you attach an
# epistemic status ... SHALL NOT", `substrate-write-protocol` opens "WHERE the
# canonical per-section digest helper is unreachable ... SHALL"), which inflated
# a first draft of this check to 129 hits across 89 files, i.e. every command in
# the repository. A check that fires everywhere reports nothing.
GATE_RE='WHEN .*(SHALL|MUST)'
# Provenance: an ADR cite anywhere on the line.
ADR_RE='ADR-[0-9]{4}'

# Lines that match GATE_RE but are not gates. Kept explicit and short; each
# entry names why it is exempt so the list cannot quietly grow into a silencer.
is_exempt() {
  local line="$1"
  # The EARS authoring template itself (decision-interview teaches the syntax).
  case "$line" in
    *'Event-driven: `WHEN <trigger>'*) return 0 ;;
    *'`WHEN <trigger> the <system> SHALL <response>`'*) return 0 ;;
  esac
  # A line that only cross-references another command's rule carries that
  # command's provenance, not its own.
  case "$line" in
    *'(cross-reference)'*) return 0 ;;
  esac
  # A wave scope boundary carrying its own decision cite (`per D-N`) is not a
  # gate learned from a dogfood; it is a scope restriction that was decided and
  # recorded. The check looks for `ADR-` specifically, so these read as uncited.
  # Deliberately NOT loosened to accept any `D-N` in general: a task-local
  # decision record does not survive its task folder's archival, while an ADR is
  # permanent, so the exemption names the shape rather than the cite (ADR-0148).
  case "$line" in
    *'out of scope for this wave per D-'*) return 0 ;;
  esac
  return 1
}

hits=0
files_with_hits=0

# Shared-block suppression, done by duplication rather than by marker parsing.
# A `<!-- shared:<name> -->` block has no end marker, so its extent cannot be
# read reliably. But a gate line that appears byte-identical in two or more
# command files IS shared text, and its provenance belongs to the canonical
# block under commands/_shared/, not to each consumer. Collect every gate line
# that occurs more than once and suppress it.
DUPES="$(grep -hE "$GATE_RE" "${REPO}"/commands/*.md 2>/dev/null \
  | grep -vE "$ADR_RE" \
  | sed 's/^[[:space:]]*//' \
  | sort | uniq -d || true)"

is_shared() {
  local needle
  needle="$(printf '%s' "$1" | sed 's/^[[:space:]]*//')"
  [ -z "$DUPES" ] && return 1
  printf '%s\n' "$DUPES" | grep -Fqx -- "$needle"
}

for f in "${REPO}"/commands/*.md; do
  [ -f "$f" ] || continue
  base="$(basename "$f")"
  file_hits=0
  while IFS= read -r entry; do
    [ -z "$entry" ] && continue
    lineno="${entry%%:*}"
    text="${entry#*:}"
    if is_exempt "$text" || is_shared "$text"; then
      continue
    fi
    file_hits=$((file_hits + 1))
    hits=$((hits + 1))
    if [ "$VERBOSE" -eq 1 ]; then
      printf '  %s:%s  %.110s\n' "$base" "$lineno" "$text"
    fi
  done < <(grep -nE "$GATE_RE" "$f" 2>/dev/null | grep -vE "$ADR_RE" || true)
  [ "$file_hits" -gt 0 ] && files_with_hits=$((files_with_hits + 1))
done

if [ "$hits" -eq 0 ]; then
  echo "gate-provenance: clean"
else
  echo "gate-provenance: ${hits} uncited gate(s) across ${files_with_hits} file(s)"
fi
exit 0
