#!/usr/bin/env bash
# check-mirror-codenames.sh -- guard against private codename leaks in a tree
# before (or after) mirroring the staging repo to the public one.
#
# Why: the public mirror is a manual copy, and private client codenames have
# leaked more than once because a sanitization pass only grepped the newest
# files, not the whole tree (see the maintainer memory
# feedback_public_repo_codename_sanitization). This script does the whole-tree
# grep for you and exits non-zero if anything is found, so it can gate a mirror.
#
# The codename list is read from a GITIGNORED sidecar (scripts/.mirror-codenames),
# so this script itself stays codename-free and is safe to live in the public
# repo. Copy scripts/.mirror-codenames.example to scripts/.mirror-codenames and
# fill it in. Format: one `PRIVATE_CODENAME|public-alias` per line (alias
# optional; `#` comments and blank lines ignored).
#
# Usage:  scripts/check-mirror-codenames.sh <target-dir>
#   e.g.  scripts/check-mirror-codenames.sh ../fhorja.dev
# Exit:   0 clean, 1 leak(s) found, 2 usage error.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIST="${MIRROR_CODENAMES_FILE:-${SCRIPT_DIR}/.mirror-codenames}"
TARGET="${1:-}"

if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "usage: $0 <target-dir>" >&2
  exit 2
fi

if [ ! -f "$LIST" ]; then
  echo "check-mirror-codenames: no codename list at ${LIST}." >&2
  echo "  copy scripts/.mirror-codenames.example to scripts/.mirror-codenames and fill it in." >&2
  exit 2
fi

hits=0

# Scan only what is actually PUBLISHED: git-tracked files. Untracked, local, or
# gitignored files (e.g. .claude/settings.local.json) never reach the remote, so
# a match there is not a leak. `git grep` searches tracked working-tree files
# only. Fall back to a whole-tree grep if TARGET is not a git repo.
# Note: git grep's regex engine has no `\b`, so whole-word matching uses `-w`
# (supported by both git grep and GNU grep) rather than a `\b...\b` pattern.
scan_word() {  # whole-word match of a codename token
  local tok="$1"
  if git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    ( cd "$TARGET" && git grep -wInE "$tok" -- . 2>/dev/null || true )
  else
    grep -rwInE "$tok" "$TARGET" --exclude-dir=.git 2>/dev/null || true
  fi
}
scan_ere() {  # arbitrary ERE (no word boundary), e.g. an absolute path
  local pat="$1"
  if git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    ( cd "$TARGET" && git grep -InE "$pat" -- . 2>/dev/null || true )
  else
    grep -rInE "$pat" "$TARGET" --exclude-dir=.git 2>/dev/null || true
  fi
}

while IFS= read -r line; do
  case "$line" in ''|'#'*) continue ;; esac
  raw="${line%%|*}"
  alias="${line#*|}"
  [ "$alias" = "$line" ] && alias=""
  # trim surrounding whitespace
  raw="$(printf '%s' "$raw" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  alias="$(printf '%s' "$alias" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  [ -n "$raw" ] || continue
  found="$(scan_word "$raw")"
  if [ -n "$found" ]; then
    hits=$((hits + 1))
    if [ -n "$alias" ]; then
      echo "LEAK: '${raw}' (public alias: ${alias})"
    else
      echo "LEAK: '${raw}'"
    fi
    printf '%s\n' "$found" | sed 's/^/  /'
  fi
done < "$LIST"

# A real absolute home path (an actual username), not the generic "/Users/..."
# example used in docs. Matches /Users/<lowercase-name> but not /Users/... or <.
paths="$(scan_ere '/Users/[a-z][a-z0-9_-]+' | grep -vE '/Users/(\.\.\.|<|name>)' || true)"
if [ -n "$paths" ]; then
  hits=$((hits + 1))
  echo "LEAK: absolute /Users/<name> path"
  printf '%s\n' "$paths" | sed 's/^/  /'
fi

if [ "$hits" -eq 0 ]; then
  echo "check-mirror-codenames: clean (${TARGET})"
  exit 0
fi

echo "check-mirror-codenames: ${hits} leak class(es) found in ${TARGET}" >&2
exit 1
