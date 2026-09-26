#!/usr/bin/env bash
# Detach one configured agent under the per-run supervisor (ADR-0196).
# Usage: launch-background-run.sh <task-folder> --timeout-sec S --grace-sec S
# WOS_AGENT_CMD is whitespace-split, never evaluated; no permission flags are added.
# Unset configuration prints the supervised manual path and exits 0.
# Exit: 0 launched/instructions; 1 refused; 2 invalid arguments or unavailable control.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$DIR/supervise-background-run.py" launch "$@"
