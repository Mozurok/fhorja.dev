#!/usr/bin/env bash
# run-baseline.sh -- produce the repository baseline audit, JSON first, then HTML.
#
# Read-only with respect to the repository: the only writes are the two report
# files under docs/audit/. Re-runnable; an unchanged tree produces an identical
# JSON payload apart from meta.run_timestamp (pin it with SOURCE_DATE_EPOCH).
#
# The JSON is the artifact of record. The HTML is a view generated from it; no
# markup is hand-written.
#
# Usage:
#   scripts/audit/run-baseline.sh                      # date defaults to today
#   scripts/audit/run-baseline.sh 2026-08-13           # explicit report date
#   scripts/audit/run-baseline.sh 2026-08-13 <launch-ref>
#
# Exit codes:
#   0  the pass completed (mismatches, if any, are reported, not fatal)
#   2  invocation or tooling error
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || exit 2

if ! command -v python3 >/dev/null 2>&1; then
  echo "run-baseline: python3 is required" >&2
  exit 2
fi

DATE="${1:-$(date +%Y-%m-%d)}"
LAUNCH_REF="${2:-}"

OUT_DIR="docs/audit"
JSON="${OUT_DIR}/${DATE}-baseline.json"
HTML="${OUT_DIR}/${DATE}-baseline.html"

mkdir -p "$OUT_DIR"

AUDIT_ARGS=(--out "$JSON")
if [ -n "$LAUNCH_REF" ]; then
  AUDIT_ARGS+=(--launch-ref "$LAUNCH_REF")
fi

python3 scripts/audit/baseline_audit.py "${AUDIT_ARGS[@]}"
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "run-baseline: baseline_audit.py exited ${rc}" >&2
  exit 2
fi

python3 scripts/audit/render_baseline_html.py --json "$JSON" --out "$HTML"
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "run-baseline: render_baseline_html.py exited ${rc}" >&2
  exit 2
fi

echo ""
echo "Wrote ${JSON}"
echo "Wrote ${HTML}"
