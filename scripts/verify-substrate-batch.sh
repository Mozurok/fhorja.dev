#!/usr/bin/env bash
# verify-substrate-batch.sh -- run the 3 substrate validators once per batch of
# writes instead of after every individual edit (v3 wave2 Slice 02, ADR-0110).
#
# Runs, in order, each with INDEPENDENT exit-code capture (never a sequential
# `set -e` chain: scan-substrate-orphans.py exits 1 on findings and would abort
# the chain, eating the remaining validators' output):
#   1. bash    scripts/scan-substrate-headers.sh <task-folder>
#   2. python3 scripts/verify-log-validator.py   <task-folder>/.wos/VERIFICATION_LOG.jsonl [--check-deletes]
#   3. python3 scripts/scan-substrate-orphans.py <task-folder>
#
# Output: each validator's own stdout, then one summary line:
#   substrate-batch: headers=<rc> log=<rc> orphans=<rc> combined=<rc>
# Exit code: the OR of the three exit codes. Nothing here is blocking by
# itself (ADR-0110 / wave-2 D-3): the combined code is EXPOSED for consumers
# (the future S1 gate) to enforce; today's callers read it as a signal.
#
# Usage:
#   bash scripts/verify-substrate-batch.sh <task-folder> [--no-check-deletes]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="${1:-}"
[[ -n "$TASK_DIR" ]] || { echo "verify-substrate-batch: usage: $0 <task-folder> [--no-check-deletes]" >&2; exit 2; }
[[ -d "$TASK_DIR" ]] || { echo "verify-substrate-batch: not a directory: $TASK_DIR" >&2; exit 2; }
CHECK_DELETES=1
[[ "${2:-}" == "--no-check-deletes" ]] && CHECK_DELETES=0

RC_HEADERS=0; RC_LOG=0; RC_ORPHANS=0

bash "$SCRIPT_DIR/scan-substrate-headers.sh" "$TASK_DIR" || RC_HEADERS=$?

LOG="$TASK_DIR/.wos/VERIFICATION_LOG.jsonl"
# Battery default (v3 wave4 Slice 05, S1 tail): activate the validator's sha-chain
# and content-vs-log checks with the S1 cutover (they shipped 2026-07-18 as opt-in
# and all live logs measure clean under it). An explicit WOS_CUTOVER_TS still wins.
CUTOVER="${WOS_CUTOVER_TS:-2026-07-18T00:00:00.000Z}"
if [[ -f "$LOG" ]]; then
  if [[ "$CHECK_DELETES" -eq 1 ]]; then
    python3 "$SCRIPT_DIR/verify-log-validator.py" "$LOG" --check-deletes --cutover-ts "$CUTOVER" || RC_LOG=$?
  else
    python3 "$SCRIPT_DIR/verify-log-validator.py" "$LOG" --cutover-ts "$CUTOVER" || RC_LOG=$?
  fi
else
  echo "substrate-batch: no VERIFICATION_LOG.jsonl (valid for legacy tasks predating K.1)"
fi

python3 "$SCRIPT_DIR/scan-substrate-orphans.py" "$TASK_DIR" || RC_ORPHANS=$?

COMBINED=$(( RC_HEADERS | RC_LOG | RC_ORPHANS ))
echo "substrate-batch: headers=$RC_HEADERS log=$RC_LOG orphans=$RC_ORPHANS combined=$COMBINED"
exit "$COMBINED"
