#!/usr/bin/env bash
# release-preflight.sh <public-tree-dir>
#
# The gate before any push to the public mirror. Runs the mirror guard twice: against this
# tree, and against the public checkout. Both scans cover the ENTIRE tracked tree, not the
# diff that is about to go out, because a leak that an earlier release missed sits in the
# public tree already and no diff-scoped scan will ever see it. That accumulation is the
# whole reason this script exists.
#
# The second run exports MIRROR_CODENAMES_FILE so the codename loop reads the STAGING
# sidecar. Without it the loop is skipped against the public tree, which has no sidecar of
# its own and cannot have one: the file is gitignored by design. Exporting a private
# sidecar into a scan of the public tree is correct HERE and wrong in anything that ships,
# which is why this script is deliberately not wired into lint-commands.sh. It also takes a
# path that does not exist in CI.
#
# It also reads the public checkout's history. A pull request merged in the public tree exists
# nowhere else, and the next release overwrites that tree (ADR-0188), so the change is lost unless
# it was ported into this tree first. The gate refuses while the public history carries a commit
# that is neither of these:
#   - a mirror sync: its message has a line `Mirror-sync: <sha>` naming a commit in this tree's
#     history, the staging commit the release was cut from. Every release commit carries one.
#   - ported: a commit in this tree's history has a line `Ported-from-public: <sha>` naming it,
#     7 to 40 hex characters, matched as a prefix of the public sha.
# Merge commits are skipped because they carry no change of their own; the commits a merge
# brings in are read one by one. Commits at or before PUBLIC_BASELINE predate the Mirror-sync
# line and were read on 2026-09-23: every one is a release commit except pull request #1
# (merge d06c180 of 9b8b3a2), whose change is staging commit 39fbcbe7. The read is local, so
# fetch the public checkout first; its upstream branch, when one is set, is read with HEAD.
#
# Exit: 0 both trees clean and every public commit a sync or ported; 1 a leak class found, an
# unported public commit, or a history that could not be read; 2 usage error.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GUARD="${SCRIPT_DIR}/check-mirror-codenames.sh"
SIDECAR="${MIRROR_CODENAMES_FILE:-${SCRIPT_DIR}/.mirror-codenames}"
PUBLIC_BASELINE=1150bbc706fc7744429ea6ec77fe7ccf0db0579d

usage() {
  echo "usage: release-preflight.sh <public-tree-dir>" >&2
  echo "  runs the mirror guard over this tree and over the public checkout, both in full," >&2
  echo "  and refuses a public commit that is neither a mirror sync nor ported into this tree" >&2
  exit 2
}

[ "$#" -eq 1 ] || usage
PUBLIC="$1"
[ -d "$PUBLIC" ] || { echo "release-preflight: not a directory: ${PUBLIC}" >&2; usage; }
[ -x "$GUARD" ] || { echo "release-preflight: guard not executable: ${GUARD}" >&2; exit 2; }

rc=0

scan() {  # scan <label> <dir> [sidecar]
  local label="$1" dir="$2" sidecar="${3:-}" out status
  if [ -n "$sidecar" ]; then
    out="$(MIRROR_CODENAMES_FILE="$sidecar" "$GUARD" "$dir" 2>&1)"; status=$?
  else
    out="$("$GUARD" "$dir" 2>&1)"; status=$?
  fi
  if [ "$status" -eq 0 ]; then
    echo "release-preflight: clean (${label})"
  elif [ "$status" -eq 3 ]; then
    # Guard exit 3: the structural scans ran clean, the codename scan did not run at all.
    # Still blocks, and deliberately so. This script exists to export the staging sidecar into
    # the public checkout precisely so that loop runs, so a 3 here means the export did not take
    # and the push would go out with the codename class unmeasured. What changes is the label:
    # calling an unmeasured scan a LEAK was as wrong in the other direction as calling it clean.
    echo "release-preflight: codename scan NOT MEASURED in ${label} (no sidecar); this gate requires it"
    printf '%s\n' "$out" | sed 's/^/  /'
    rc=1
  else
    echo "release-preflight: LEAK in ${label}"
    printf '%s\n' "$out" | sed 's/^/  /'
    rc=1
  fi
}

is_sync() {  # is_sync <public-dir> <sha>: its Mirror-sync line names a commit in this history
  local ref
  ref="$(git -C "$1" log -1 --format=%B "$2" \
    | sed -nE 's/^Mirror-sync:[[:space:]]*([0-9a-fA-F]{7,40})[[:space:]]*$/\1/p' | head -1)"
  [ -n "$ref" ] && git -C "$REPO_ROOT" merge-base --is-ancestor "$ref" HEAD 2>/dev/null
}

is_ported() {  # is_ported <sha> <ported-list>: a Ported-from-public line names it by prefix
  local p
  for p in $2; do
    case "$1" in "$p"*) return 0 ;; esac
  done
  return 1
}

history_check() {  # history_check <public-dir>
  local dir="$1" revs="HEAD" base="" ported sha unported="" n=0 top
  # The directory must be the top of its own checkout: a plain folder nested inside another
  # repository would otherwise read that repository's history and report on the wrong tree.
  top="$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null || true)"
  if [ -z "$top" ] || [ "$(cd "$top" && pwd -P)" != "$(cd "$dir" && pwd -P)" ] \
     || ! git -C "$dir" rev-parse --verify --quiet HEAD >/dev/null 2>&1 \
     || ! git -C "$REPO_ROOT" rev-parse --verify --quiet HEAD >/dev/null 2>&1; then
    echo "release-preflight: public history NOT MEASURED in ${dir} (no git history to read); this gate requires it"
    rc=1
    return
  fi
  if git -C "$dir" rev-parse --verify --quiet '@{upstream}' >/dev/null 2>&1; then
    revs="HEAD @{upstream}"
  fi
  if git -C "$dir" cat-file -e "${PUBLIC_BASELINE}^{commit}" 2>/dev/null; then
    base="^${PUBLIC_BASELINE}"
  fi
  ported="$(git -C "$REPO_ROOT" log --format=%B HEAD \
    | sed -nE 's/^Ported-from-public:[[:space:]]*([0-9a-fA-F]{7,40})[[:space:]]*$/\1/p' \
    | tr 'A-F' 'a-f' | sort -u)"
  # shellcheck disable=SC2086  # revs and base are word lists on purpose
  for sha in $(git -C "$dir" rev-list --no-merges $revs $base); do
    n=$((n + 1))
    is_sync "$dir" "$sha" && continue
    is_ported "$sha" "$ported" && continue
    unported="${unported}${sha} $(git -C "$dir" log -1 --format=%s "$sha")
"
  done
  if [ -z "$unported" ]; then
    echo "release-preflight: public history clean (${n} commit(s) after the baseline, each a mirror sync or ported)"
  else
    echo "release-preflight: UNPORTED public commit(s) in ${dir}; the next release would overwrite them"
    printf '%s' "$unported" | sed 's/^/  /'
    echo "  port each into this tree in a commit whose message has the line 'Ported-from-public: <sha>'"
    rc=1
  fi
}

scan "." "$REPO_ROOT"
scan "$PUBLIC" "$PUBLIC" "$SIDECAR"
history_check "$PUBLIC"

exit "$rc"
