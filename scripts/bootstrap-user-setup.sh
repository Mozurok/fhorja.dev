#!/usr/bin/env bash
# bootstrap-user-setup.sh
#
# First-time setup helper for the my_work_tasks workflow operating system.
# Idempotent: safe to re-run; existing artifacts are left alone.
#
# What it does (default):
#   1. Bootstrap /USER_MEMORY.md at repo root from templates/USER_MEMORY.template.md
#      (only if absent; existing file is preserved).
#   2. Sanity-check the workflow surface (lint + skills drift); fail-fast if the
#      repo is in an unexpected state.
#   3. Print "next steps" hints (optional slash command install, first project,
#      first task).
#
# What it does NOT do:
#   - Install slash commands globally (use scripts/sync-workflow-slash-commands.sh
#     explicitly when you want them).
#   - Mirror skills to user-level dirs (--with-skills on the sync script).
#   - Run project-bootstrap or task-init (those need your input).
#
# Usage:
#   ./scripts/bootstrap-user-setup.sh             # bootstrap + sanity check + hints
#   ./scripts/bootstrap-user-setup.sh --dry-run   # show what would happen
#   ./scripts/bootstrap-user-setup.sh --help      # this message
#
# Exit codes:
#   0 = success (or "nothing to do" idempotent state)
#   1 = lint failed or skills drift detected (repo is in unexpected state)
#   2 = invocation error or missing template

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATE_PATH="${REPO_ROOT}/templates/USER_MEMORY.template.md"
TARGET_PATH="${REPO_ROOT}/USER_MEMORY.md"

DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap-user-setup.sh [options]

First-time setup helper. Idempotent.

What it does:
  1. Bootstrap /USER_MEMORY.md from templates/USER_MEMORY.template.md (only if absent).
  2. Sanity-check the workflow (lint + skills drift; fail-fast on unexpected state).
  3. Print next-steps hints (optional helpers; first project; first task).

Options:
  --dry-run     Show what would happen; do not modify files.
  --help, -h    Show this message.

Exit codes:
  0 = success (or idempotent no-op)
  1 = lint or skills drift detected
  2 = invocation error or missing template
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

echo "my_work_tasks: first-time setup"
echo "================================"
echo ""

# ---- Step 1: USER_MEMORY.md bootstrap --------------------------------------
echo "[1/3] USER_MEMORY.md"

if [[ ! -f "$TEMPLATE_PATH" ]]; then
  echo "  ERROR: template not found at $TEMPLATE_PATH" >&2
  echo "  The repo may be incomplete; verify the clone or fetch the latest changes." >&2
  exit 2
fi

if [[ -f "$TARGET_PATH" ]]; then
  echo "  USER_MEMORY.md already exists at $TARGET_PATH"
  echo "  Edit it directly to update preferences (no command needed)."
elif [[ $DRY_RUN -eq 1 ]]; then
  echo "  Would create $TARGET_PATH from $TEMPLATE_PATH (dry-run; no change made)."
else
  cp "$TEMPLATE_PATH" "$TARGET_PATH"
  echo "  Created USER_MEMORY.md from template."
  echo "  Open it and fill in your preferences (response length, language, emoji policy,"
  echo "  tool quirks, recurring gotchas, per-project pointers, cross-project learnings)."
fi
echo ""

# ---- Step 2: workflow sanity check -----------------------------------------
echo "[2/3] Workflow sanity check"

if [[ $DRY_RUN -eq 1 ]]; then
  echo "  Would run ./scripts/lint-commands.sh (dry-run; skipping)."
else
  if "${SCRIPT_DIR}/lint-commands.sh" >/dev/null 2>&1; then
    echo "  Lint: clean (commands, frontmatter, shared blocks, token budgets, skills)."
  else
    echo "  ERROR: lint failed. Re-run with: ./scripts/lint-commands.sh --verbose" >&2
    echo "  Common causes: clone is incomplete; local edits broke a contract; skills drifted." >&2
    exit 1
  fi
fi
echo ""

# ---- Step 3: next-steps hints ----------------------------------------------
echo "[3/3] Next steps"
echo ""
echo "  Required for daily use:"
echo "    1. Edit USER_MEMORY.md with your preferences (if just created)."
echo "    2. Open this repo in your AI tool (Cursor, Claude Code, Codex, etc.);"
echo "       commands are available as Agent Skills via .claude/skills/."
echo ""
echo "  Optional helpers (run when relevant):"
echo "    - Install slash commands globally for any project:"
echo "        ./scripts/sync-workflow-slash-commands.sh"
echo "    - Mirror skills to user-level dirs (~/.claude/skills/, ~/.cursor/skills/, etc.):"
echo "        ./scripts/sync-workflow-slash-commands.sh --with-skills"
echo ""
echo "  Start your first project (interactive; in your AI tool):"
echo "    /project-bootstrap   # new project context (creates projects/<client>__<project>/)"
echo "    /task-init           # first task on that project (or any existing project)"
echo ""
echo "Setup complete. See README.md and docs/FAQ.md if you want a deeper tour."
