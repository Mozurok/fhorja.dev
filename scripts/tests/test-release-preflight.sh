#!/usr/bin/env bash
# test-release-preflight.sh: the release gate refuses a public commit that the next
# release would overwrite.
#
# WHY. The public tree is an overwrite target (ADR-0188): each release copies this tree
# over it. A pull request merged there exists nowhere else, so the next release deletes
# it unless it was ported here first. Until 2026-09-23 release-preflight.sh read only
# file contents, so nothing noticed a merged pull request and the release took it away.
#
# HOW. Everything runs in temporary git repositories. The script derives REPO_ROOT from
# its own location, so it is COPIED into a fixture staging repository next to a stub
# mirror guard that always passes; that keeps these checks about history alone. The
# real public checkout and this repository are never read or written. Git's global and
# system config are switched off so a hook or signing rule on the machine cannot change
# what a fixture commit looks like.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${SCRIPT_DIR}/../release-preflight.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=fixture GIT_AUTHOR_EMAIL=fixture@example.invalid
export GIT_COMMITTER_NAME=fixture GIT_COMMITTER_EMAIL=fixture@example.invalid

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

[ -f "$SRC" ] || { echo "  FAIL $SRC missing"; exit 1; }

g() { git -c init.defaultBranch=main -c commit.gpgsign=false "$@"; }
commit() {  # commit <repo> <file> <message>
  echo "$RANDOM $2" >> "$1/$2"
  g -C "$1" add "$2" >/dev/null
  g -C "$1" commit -q -m "$3"
  g -C "$1" rev-parse HEAD
}

# --- fixture: a staging repository carrying the script and a stub guard ------
STG="$TMP/staging"
mkdir -p "$STG/scripts"
cp "$SRC" "$STG/scripts/release-preflight.sh"
printf '#!/usr/bin/env bash\nexit 0\n' > "$STG/scripts/check-mirror-codenames.sh"
chmod +x "$STG/scripts/release-preflight.sh" "$STG/scripts/check-mirror-codenames.sh"
g init -q "$STG"
g -C "$STG" add scripts >/dev/null
g -C "$STG" commit -q -m "staging: the tree a release is cut from"
S1="$(g -C "$STG" rev-parse HEAD)"

PUB="$TMP/public"
g init -q "$PUB"
P1="$(commit "$PUB" README.md "release one

Mirror-sync: ${S1:0:12}")"

run() {  # run <public-dir> [script]: prints the exit code, output in $TMP/out
  local script="${2:-$STG/scripts/release-preflight.sh}"
  bash "$script" "$1" >"$TMP/out" 2>&1
  echo $?
}

# 1. A public history of release commits only passes.
rc="$(run "$PUB")"
if [ "$rc" = 0 ] && grep -q 'public history clean (1 commit' "$TMP/out"; then
  pass "1. a public history of mirror syncs passes (exit 0)"
else
  fail "1. mirror-sync-only history: exit $rc"; sed 's/^/       /' "$TMP/out"
fi

# 2. A merged pull request that staging never received is refused, by sha.
P2="$(commit "$PUB" fix.txt "fix: a contributor's change merged on GitHub")"
rc="$(run "$PUB")"
if [ "$rc" = 1 ] && grep -q "UNPORTED" "$TMP/out" && grep -q "$P2" "$TMP/out" \
   && ! grep -q "$P1" "$TMP/out"; then
  pass "2. an unported public commit is refused and named, the sync is not (exit 1)"
else
  fail "2. unported public commit: exit $rc"; sed 's/^/       /' "$TMP/out"
fi

# 3. A staging commit that names it in a Ported-from-public line clears it.
commit "$STG" ported.txt "Port the contributor's fix

Ported-from-public: ${P2:0:9}" >/dev/null
rc="$(run "$PUB")"
if [ "$rc" = 0 ] && grep -q 'public history clean (2 commit' "$TMP/out"; then
  pass "3. a Ported-from-public line in staging clears the commit (exit 0)"
else
  fail "3. ported commit: exit $rc"; sed 's/^/       /' "$TMP/out"
fi

# 4. A Mirror-sync line naming a commit staging does not have is not a sync.
P4="$(commit "$PUB" forged.txt "looks like a release

Mirror-sync: 0123456789abcdef0123456789abcdef01234567")"
rc="$(run "$PUB")"
if [ "$rc" = 1 ] && grep -q "$P4" "$TMP/out"; then
  pass "4. a Mirror-sync line naming no staging commit is refused (exit 1)"
else
  fail "4. forged Mirror-sync line: exit $rc"; sed 's/^/       /' "$TMP/out"
fi
commit "$STG" ported.txt "Port it

Ported-from-public: $P4" >/dev/null

# 5. A pull request merged with a merge commit: the branch commit is what needs porting,
#    the merge commit itself carries no change and is never listed.
g -C "$PUB" checkout -q -b pr
P5="$(commit "$PUB" pr.txt "feat: a pull request branch commit")"
g -C "$PUB" checkout -q main
g -C "$PUB" merge -q --no-ff -m "Merge pull request #2 from someone/pr" pr
M5="$(g -C "$PUB" rev-parse HEAD)"
rc="$(run "$PUB")"
if [ "$rc" = 1 ] && grep -q "$P5" "$TMP/out" && ! grep -q "$M5" "$TMP/out"; then
  pass "5. a merged branch commit is refused, its merge commit is not listed (exit 1)"
else
  fail "5. merge commit case: exit $rc"; sed 's/^/       /' "$TMP/out"
fi
commit "$STG" ported.txt "Port pull request 2

Ported-from-public: $P5" >/dev/null
rc="$(run "$PUB")"
[ "$rc" = 0 ] && pass "5b. porting the branch commit clears the merge (exit 0)" \
  || { fail "5b. ported merge: exit $rc"; sed 's/^/       /' "$TMP/out"; }

# 6. The upstream branch is read along with HEAD: a pull request merged on GitHub after
#    the checkout was last pulled, but fetched, is refused.
CLONE="$TMP/clone"
g clone -q "$PUB" "$CLONE"
P6="$(commit "$PUB" late.txt "fix: merged on GitHub after the last pull")"
g -C "$CLONE" fetch -q
rc="$(run "$CLONE")"
if [ "$rc" = 1 ] && grep -q "$P6" "$TMP/out"; then
  pass "6. an unported commit on the fetched upstream branch is refused (exit 1)"
else
  fail "6. upstream commit: exit $rc"; sed 's/^/       /' "$TMP/out"
fi

# 7. Commits at or before the baseline predate the Mirror-sync line and are not read.
sed "s/^PUBLIC_BASELINE=.*/PUBLIC_BASELINE=${P6}/" "$STG/scripts/release-preflight.sh" \
  > "$STG/scripts/preflight-baseline.sh"
rc="$(run "$PUB" "$STG/scripts/preflight-baseline.sh")"
if [ "$rc" = 0 ] && grep -q 'public history clean (0 commit' "$TMP/out"; then
  pass "7. a commit at the baseline is not read (exit 0)"
else
  fail "7. baseline: exit $rc"; sed 's/^/       /' "$TMP/out"
fi
P7="$(commit "$PUB" after.txt "fix: after the baseline")"
rc="$(run "$PUB" "$STG/scripts/preflight-baseline.sh")"
if [ "$rc" = 1 ] && grep -q "$P7" "$TMP/out" && ! grep -q "$P6" "$TMP/out"; then
  pass "7b. a commit after the baseline is still read (exit 1)"
else
  fail "7b. after the baseline: exit $rc"; sed 's/^/       /' "$TMP/out"
fi

# 8. A public directory with no history of its own is not measured, and that blocks.
mkdir -p "$TMP/plain" "$STG/nested"
for d in "$TMP/plain" "$STG/nested"; do
  rc="$(run "$d")"
  if [ "$rc" = 1 ] && grep -q "public history NOT MEASURED" "$TMP/out"; then
    pass "8. ${d#"$TMP"/} without its own git history is NOT MEASURED (exit 1)"
  else
    fail "8. ${d#"$TMP"/}: exit $rc"; sed 's/^/       /' "$TMP/out"
  fi
done

echo
echo "test-release-preflight: ${checks} checks, ${fails} failed"
[ "$fails" -eq 0 ]
