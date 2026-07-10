#!/usr/bin/env bash
# stop-check.sh -- Fhorja autonomy track kill switch (ADR-0044, D11).
#
# The out-of-process kill switch is a STOP sentinel file that lives OUTSIDE the
# autonomous agent's writable scope. The controller checks it between slices;
# because the agent cannot write where the file lives, it cannot clear its own
# kill switch. A present STOP file halts the run.
#
# Usage: stop-check.sh <stop-file-path>
# Exit:  0 = no stop (continue), 30 = STOP present (halt).

set -euo pipefail

stop_file="${1:-}"
if [[ -z "$stop_file" ]]; then
  echo "stop-check: missing <stop-file-path> argument" >&2
  exit 2
fi

if [[ -e "$stop_file" ]]; then
  echo "HALT: STOP sentinel present at $stop_file"
  exit 30
fi

echo "OK: no STOP sentinel"
exit 0
