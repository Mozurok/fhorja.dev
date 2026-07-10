#!/usr/bin/env bash
# proposed-counter-hook.sh - Claude Code Stop hook warning about pending PROPOSED artifacts
#
# Per ADR-0024 approve-proposed-idiom, when artifact changes are proposed but not
# yet persisted (PROPOSED tag still present), the user needs to run /approve-proposed
# to commit them. This hook nudges when there are pending PROPOSED artifacts in
# recently-modified active task folders.
#
# Stateless by design: examines filesystem directly, no state file.
# Non-blocking: emits warning to stderr but exits 0 (Stop hook may block by exit 2,
# but warning is enough — we don't want to prevent turn completion).
#
# Heuristic: looks at .md files in projects/*/active/*/ modified in last N minutes
# that contain the word PROPOSED.

set -euo pipefail

# ---------------------------------------------------------------------------
# 0. Config
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WOS_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
THRESHOLD_MIN=30   # only count files modified in last 30 min (avoid stale noise)
WARN_THRESHOLD=1   # warn when at least 1 pending PROPOSED file exists

# ---------------------------------------------------------------------------
# 1. Discard stdin (Stop hook payload is just {stop_reason}; not needed here)
# ---------------------------------------------------------------------------
cat > /dev/null

# ---------------------------------------------------------------------------
# 2. Scan active task folders for recently-modified files with PROPOSED markers
# ---------------------------------------------------------------------------
# Use find with -print0 + xargs -0 to handle weird paths safely.
# Limit to .md files because PROPOSED tag convention is markdown-only (ADR-0001).

pending_files="$(
  find "$WOS_ROOT/projects/"*/active/*/ \
    -maxdepth 2 \
    -type f \
    -name "*.md" \
    -mmin -$THRESHOLD_MIN \
    -print0 2>/dev/null \
  | xargs -0 grep -l "PROPOSED" 2>/dev/null \
  || true
)"

if [[ -z "$pending_files" ]]; then
  exit 0
fi

pending_count="$(echo "$pending_files" | wc -l | tr -d ' ')"

if [[ "$pending_count" -lt "$WARN_THRESHOLD" ]]; then
  exit 0
fi

# ---------------------------------------------------------------------------
# 3. Emit warning to stderr (visible in transcript per Stop hook docs)
# ---------------------------------------------------------------------------
cat >&2 <<EOF
⚠  PROPOSED counter: $pending_count file(s) modified in last ${THRESHOLD_MIN}min contain PROPOSED markers in active tasks.
   Run /approve-proposed to persist, or revise. See ADR-0024.
   Files:
$(echo "$pending_files" | sed 's|^|     - |' | head -10)
EOF

exit 0
