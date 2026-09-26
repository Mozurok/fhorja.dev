#!/usr/bin/env bash
# Runs-feed v1 producer (ADR-0080) with managed lifecycle arbitration (ADR-0196).
# start <run_id> <task> <step>; update <run_id> [--state S] [--step S]; end <run_id>; check
# Supervised runs retain lifecycle authority in background-runs metadata: start/end
# cannot reset it, and late updates cannot erase escalation. Standalone use remains.
# WOS_MAIN_REPO routes a worktree caller to the main repository's feed.
# check reports heartbeat freshness only (STALE_MINUTES defaults to 15); the
# launcher uses independent ownership admission, never this display check.
# Exit: 0 success/no fresh run; 1 unknown update/fresh run; 2 invalid input or I/O.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$DIR/supervise-background-run.py" feed "$@"
