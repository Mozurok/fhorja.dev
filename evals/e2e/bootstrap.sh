#!/usr/bin/env bash
# Fhorja E2E walkthrough bootstrap -- idempotent setup of synthetic project + product repo.
#
# Creates:
#   projects/wos__e2e-test/                  -- synthetic project (gitignored per ADR-0007)
#   /tmp/wos-e2e-fake-app/                   -- copy of evals/e2e/fake-app/ (initialized as a git repo)
#
# Per evals/e2e/README.md. Safe to re-run; preserves nothing on re-run (full rebuild).
#
# Usage:
#   bash evals/e2e/bootstrap.sh           # default: rebuild both, prompt before clobber
#   bash evals/e2e/bootstrap.sh --force   # rebuild without prompting
#   bash evals/e2e/bootstrap.sh --clean   # remove both, do not rebuild
#
# Exit:
#   0 success
#   1 user declined clobber
#   2 invocation error

set -euo pipefail

FORCE=0
CLEAN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1; shift ;;
    --clean) CLEAN=1; shift ;;
    *)       echo "ERROR: unknown arg $1" >&2; exit 2 ;;
  esac
done

# Resolve Fhorja repo root from this script's location (script lives at evals/e2e/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WOS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="$WOS_ROOT/projects/wos__e2e-test"
FAKE_APP_SRC="$SCRIPT_DIR/fake-app"
FAKE_APP_DST="/tmp/wos-e2e-fake-app"

if [[ $CLEAN -eq 1 ]]; then
  echo "Cleaning up E2E artifacts..."
  rm -rf "$PROJECT_DIR" "$FAKE_APP_DST"
  echo "Done. Removed: $PROJECT_DIR + $FAKE_APP_DST"
  exit 0
fi

# Confirm clobber if either target exists and --force not set.
if [[ -d "$PROJECT_DIR" || -d "$FAKE_APP_DST" ]]; then
  if [[ $FORCE -eq 0 ]]; then
    echo "Existing E2E artifacts detected:" >&2
    [[ -d "$PROJECT_DIR" ]]  && echo "  $PROJECT_DIR" >&2
    [[ -d "$FAKE_APP_DST" ]] && echo "  $FAKE_APP_DST" >&2
    read -r -p "Rebuild (clobber existing)? [y/N] " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
      echo "Aborted by user." >&2
      exit 1
    fi
  fi
  rm -rf "$PROJECT_DIR" "$FAKE_APP_DST"
fi

# --- Synthetic project folder -------------------------------------------------
# Create ONLY the top-level project dir. The active/ and archive/ subfolders +
# PROJECT_CHARTER.md + REFERENCES.md are produced by Step 01 (project-bootstrap)
# of the walkthrough -- pre-creating them here would prevent that step from
# demonstrating its own contract.
mkdir -p "$PROJECT_DIR"
echo "Created: $PROJECT_DIR (Step 01 will populate active/, archive/, PROJECT_CHARTER.md, REFERENCES.md)"

# --- Synthetic product repo ---------------------------------------------------
mkdir -p "$FAKE_APP_DST"
# Copy ALL files + subdirs (handlers/signup.py + handlers/__init__.py + app.py + README.md + requirements.txt).
cp -R "$FAKE_APP_SRC"/. "$FAKE_APP_DST/"

# Make it a real git repo with a single committed baseline so impact-analysis +
# repo-consistency-sweep have a base branch to diff against.
# Requires git >= 2.28 for the -b flag (macOS ships compatible git since Catalina).
cd "$FAKE_APP_DST"
git init -q -b main
git add app.py handlers/ README.md requirements.txt
GIT_AUTHOR_NAME="Fhorja E2E Bootstrap" \
GIT_AUTHOR_EMAIL="e2e@example.invalid" \
GIT_COMMITTER_NAME="Fhorja E2E Bootstrap" \
GIT_COMMITTER_EMAIL="e2e@example.invalid" \
  git commit -q -m "baseline: synthetic flask signup with intentional issues"

echo "Created: $FAKE_APP_DST (initial commit $(git rev-parse --short HEAD))"
echo
echo "==> Bootstrap complete."
echo
echo "Next steps:"
echo "  1. Open evals/e2e/walkthrough.md"
echo "  2. Run Step 01 (project-bootstrap) in a fresh Claude Code or Cursor session"
echo "  3. After each step, run its assertion script: bash evals/e2e/assertions/0N-<command>.sh"
echo
echo "Re-run this script (--force) any time you want a clean slate."
