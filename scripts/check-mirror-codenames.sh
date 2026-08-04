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
# fill it in. Format: one `PRIVATE_CODENAME|public-alias|mode` per line (alias and
# mode both optional; `#` comments and blank lines ignored). `mode` is `compound`
# to also catch the token inside a dotted or underscored machine identifier;
# anything else, including empty, keeps the default boundary match.
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
# Note: git grep's regex engine has no `\b`. Whole-word `-w` was the original
# choice and it LEAKED: `-w` treats `_` as a word character, so a codename
# embedded in a project slug (`client__client-be`) never matched and passed this
# gate. The scan now bounds on any NON-ALPHANUMERIC character instead, which
# catches the embedded form while still rejecting a longer word that merely
# starts with the token (`clientele` stays a non-match, `client__client-be`
# does not). Verified against every token in the sidecar: identical counts to
# `-w` on all of them, plus the one file `-w` missed (2026-07-29, D-1). The match
# is also CASE-INSENSITIVE (D-7): a codename lowercased inside a slug leaked past a
# case-sensitive scan. Measured at +1 file and zero false positives across every
# other token, because the alnum boundary still rejects ordinary words.
# The boundary form above cannot see a codename embedded in a machine identifier
# (`com.<tok>eng.<tok>launcherstaging`), because the neighbouring character is
# alphanumeric on the trailing side. Per-entry `compound` mode widens the scan to
# that form. The separator class is deliberately `.` and `_` ONLY: a hyphen is
# shape-identical to ordinary hyphenated English prose, and including it flagged
# 278 files on a single token with zero real leaks. Measured over the tracked
# tree at the same commit, all sidecar tokens: with `.`/`_` only, 12 of 14 tokens
# add zero files while still detecting the bundle-id, dotted-host, and
# double-underscore-slug forms; the 2 that add files are short strings occurring
# inside ordinary words, and they stay on the default mode (mobile monorepo
# dogfood 2026-07-31). An unrecognised mode falls back to the default, so an
# older checkout reading a newer sidecar keeps working.
# A token is DATA, not a pattern: it is escaped before it reaches the ERE. Without
# this, a token carrying a regex metacharacter silently breaks its own check. A `.`
# acts as a wildcard (token `a.c` flagged a file holding only `aXc`), and a `[`
# makes the pattern invalid, at which point grep exits >1 and the old `|| true`
# swallowed it: the guard printed `clean` on a file that literally contained the
# codename. A leak guard that fails open is worse than none, so a scan error is now
# a hit, and the error message never echoes the token.
ere_escape() { printf '%s' "$1" | sed -e 's/[^a-zA-Z0-9_]/\\&/g'; }
# The compound gap is BOUNDED. An unbounded run between the token and the separator
# is the mechanism that flagged 278 files when the hyphen was still a separator;
# restricting the class to `.` and `_` removed the trigger, not the mechanism.
COMPOUND_GAP_MAX=12
scan_word() {  # identifier-boundary match of a codename token; mode widens it
  local tok_raw="$1" mode="${2:-}" tok out rc
  tok="$(ere_escape "$tok_raw")"
  local pat="(^|[^A-Za-z0-9])${tok}([^A-Za-z0-9]|\$)"
  if [ "$mode" = "compound" ]; then
    local g="[A-Za-z0-9]{0,${COMPOUND_GAP_MAX}}"
    pat="${pat}|[A-Za-z0-9][._]${g}${tok}|${tok}${g}[._][A-Za-z0-9]"
  fi
  if git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    out="$( cd "$TARGET" && git grep -iInE "$pat" -- . 2>/dev/null )"; rc=$?
  else
    out="$(grep -riInE "$pat" "$TARGET" --exclude-dir=.git 2>/dev/null)"; rc=$?
  fi
  # 0 = matched, 1 = no match, >1 = real error (bad pattern, unreadable tree).
  if [ "$rc" -gt 1 ]; then
    printf 'scan failed (exit %s): the pattern for this entry did not compile, or the tree could not be read\n' "$rc"
    return 2
  fi
  printf '%s' "$out"
  return 0
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
  rest="${line#*|}"
  [ "$rest" = "$line" ] && rest=""
  alias="${rest%%|*}"
  mode="${rest#*|}"
  [ "$mode" = "$rest" ] && mode=""
  # trim surrounding whitespace
  raw="$(printf '%s' "$raw" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  alias="$(printf '%s' "$alias" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  mode="$(printf '%s' "$mode" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  [ -n "$raw" ] || continue
  found="$(scan_word "$raw" "$mode")"; scan_rc=$?
  if [ "$scan_rc" -gt 1 ]; then
    hits=$((hits + 1))
    echo "SCAN ERROR on one entry (token not echoed):"
    printf '%s\n' "$found" | sed 's/^/  /'
    continue
  fi
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
