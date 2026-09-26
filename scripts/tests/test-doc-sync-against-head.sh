#!/usr/bin/env bash
# test-doc-sync-against-head.sh: the renumber check, `check-doc-sync.sh --against HEAD`
# (ADR-0225).
#
# WHY. The default doc-sync asks whether a cited section EXISTS. An inserted numbered
# section keeps every number in existence and moves the titles under them, so on the
# defect of record (a section inserted above AGENTS.md section 6) the default form
# exited 0 with seven live citations stale. This mode compares the tree with HEAD.
#
# HOW. Each check builds a throwaway git repository in a temp directory, commits a
# base, applies one change to the working tree, and runs the mode with --repo pointed
# at it. Nothing here writes to the real repository.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC="${REPO}/scripts/check-doc-sync.sh"
LINT="${REPO}/scripts/lint-commands.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
checks=0; fails=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); fails=$((fails+1)); echo "  FAIL $1"; }
[ -f "$SRC" ] || { echo "  FAIL $SRC missing"; exit 1; }

AGENTS='# AGENTS.md

## 1. One

## 6. Changing a rule

## 7. Writing rules'

build() {  # build <name>: a committed base repository; echoes its path
  local d="$TMP/$1"; mkdir -p "$d/docs"
  printf '%s\n' "$AGENTS" > "$d/AGENTS.md"
  printf '# CLAUDE.md\n\nHow a rule changes is `AGENTS.md` section 6.\n' > "$d/CLAUDE.md"
  printf '# Guide\n\n## Install\n\nText.\n\n## Notes\n\nText.\n' > "$d/docs/guide.md"
  printf '# README\n\nRead `docs/guide.md`, or [the guide](docs/guide.md), and `docs/guide.md` `## Notes`.\n' > "$d/README.md"
  printf '# Changelog\n\n- 2026-01-01: `AGENTS.md` section 6 and `docs/guide.md` shipped.\n' > "$d/CHANGELOG.md"
  git -C "$d" init -q -b main
  git -C "$d" add AGENTS.md CLAUDE.md README.md CHANGELOG.md docs/guide.md
  git -C "$d" -c user.email=t@t -c user.name=t commit -qm base
  echo "$d"
}
run() { bash "$SRC" --against HEAD --repo "$1" >"$1/.out" 2>&1; echo $?; }
insert_six() {  # a new section 6 above "Changing a rule", everything below renumbered
  printf '# AGENTS.md\n\n## 1. One\n\n## 6. A new section\n\n## 7. Changing a rule\n\n## 8. Writing rules\n' > "$1/AGENTS.md"
}

d="$(build clean)"
[ "$(run "$d")" = "0" ] && grep -q "no heading or path the change removed" "$d/.out" \
  && pass "1. a tree identical to HEAD passes and says it read nothing to compare" \
  || fail "1. clean tree: $(cat "$d/.out")"

d="$(build inserted)"; insert_six "$d"
[ "$(run "$d")" = "1" ] && grep -q "BROKEN renumbered-section ref 'AGENTS.md section 6' in CLAUDE.md:3" "$d/.out" \
  && pass "2. an inserted numbered section refuses, naming the stale citation" \
  || fail "2. an insertion above section 6 was not refused: $(cat "$d/.out")"

# The same insertion with the citation updated in the same change: the citing line is
# now a line the diff added, so it is the change itself, and it is not read.
d="$(build inserted-fixed)"; insert_six "$d"
printf '# CLAUDE.md\n\nHow a rule changes is `AGENTS.md` section 7.\n' > "$d/CLAUDE.md"
[ "$(run "$d")" = "0" ] && pass "3. control: the insertion with its citation updated passes" \
  || fail "3. an updated citation was refused: $(cat "$d/.out")"

d="$(build historical)"; insert_six "$d"
printf '# CLAUDE.md\n\nHow a rule changes is in AGENTS.md.\n' > "$d/CLAUDE.md"
git -C "$d" -c user.email=t@t -c user.name=t commit -qam "drop the citation"
insert_six "$d"
[ "$(run "$d")" = "0" ] && pass "4. a citation that survives only in CHANGELOG.md is history, not a finding" \
  || fail "4. a historical record was read: $(cat "$d/.out")"

d="$(build heading)"
printf '# Guide\n\n## Install\n\nText.\n' > "$d/docs/guide.md"
[ "$(run "$d")" = "1" ] && grep -q "BROKEN removed-heading ref 'guide.md ## Notes' in README.md:3" "$d/.out" \
  && pass "5. a removed heading that a live line cites beside its file refuses" \
  || fail "5. a removed cited heading was not refused: $(cat "$d/.out")"

d="$(build deleted)"
git -C "$d" rm -q docs/guide.md
[ "$(run "$d")" = "1" ] && grep -q "BROKEN deleted-path ref 'docs/guide.md' in README.md:3" "$d/.out" \
  && pass "6. a deleted path still referenced outside the diff refuses" \
  || fail "6. a deleted referenced path was not refused: $(cat "$d/.out")"

d="$(build deleted-link)"
printf '# README\n\nRead [the guide](docs/guide.md).\n' > "$d/README.md"
git -C "$d" -c user.email=t@t -c user.name=t commit -qam "link only"
git -C "$d" rm -q docs/guide.md
[ "$(run "$d")" = "1" ] && grep -q "BROKEN deleted-path ref 'docs/guide.md' in README.md:3" "$d/.out" \
  && pass "7. a relative markdown link to a deleted path refuses" \
  || fail "7. a link to a deleted path was not refused: $(cat "$d/.out")"

d="$(build deleted-said)"
printf '# README\n\nThe old `docs/guide.md` was deleted in 2026.\n' > "$d/README.md"
git -C "$d" -c user.email=t@t -c user.name=t commit -qam "absence line"
git -C "$d" rm -q docs/guide.md
[ "$(run "$d")" = "0" ] && pass "8. a line naming a deleted path to say it is gone is spared" \
  || fail "8. an absence statement was refused: $(cat "$d/.out")"

mkdir -p "$TMP/not-git"
bash "$SRC" --against HEAD --repo "$TMP/not-git" >"$TMP/not-git.out" 2>&1; rc=$?
[ "$rc" = "2" ] && grep -q "not measured" "$TMP/not-git.out" \
  && pass "9. a directory with no git revision is reported not measured (exit 2), never clean" \
  || fail "9. a non-repository returned $rc: $(cat "$TMP/not-git.out")"

# The lint runs the mode and fails on its exit 1. Asserted on the lint text because the
# lint scans the real tree, which this test must not change.
grep -q 'check-doc-sync.sh.*--against HEAD\|DOC_SYNC_SCRIPT" --against HEAD' "$LINT" \
  && grep -q 'DR_EXIT' "$LINT" \
  && pass "10. lint-commands.sh runs --against HEAD and keeps its exit code" \
  || fail "10. lint-commands.sh does not run the renumber check"

echo
echo "doc-sync-against-head: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
