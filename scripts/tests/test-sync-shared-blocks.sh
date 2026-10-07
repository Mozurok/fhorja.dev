#!/usr/bin/env bash
# test-sync-shared-blocks.sh -- pins the codename gate that runs BEFORE shared-block
# propagation.
# Run from anywhere:  bash scripts/tests/test-sync-shared-blocks.sh
#
# Why this gate exists: a shared block is copied into every command that declares
# its marker, and each command is then compiled into a tracked SKILL.md. One
# codename in one shared block therefore reaches roughly 195 tracked files before
# anything checks. The lint catches it only after the fact, on the next run.
#
# Why the checks are shaped this way. The script derives SHARED_DIR from its own
# location and offers no override, so a test cannot point it at a scratch tree.
# The SIDECAR does have an override (MIRROR_CODENAMES_FILE), so these checks plant
# a synthetic list containing a token that genuinely occurs in commands/_shared
# instead of faking the directory.
#
# Every run here passes --dry-run, so the repository is never mutated. "Propagated
# zero files" is therefore asserted by the ABSENCE of the run summary line, which
# the script prints only after the propagation loop completes. An early abort
# prints no summary; that absence is the observable proof the loop never ran.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC="$SCRIPT_DIR/../sync-shared-blocks.sh"
fails=0
checks=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); echo "  FAIL $1"; fails=$((fails+1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# A token that really occurs in commands/_shared, so the guard has something to
# find without this file inventing a fake tree. Synthetic in the sense that
# matters: it is an ordinary English word, never a real codename.
PRESENT_TOKEN="Handoff"
ABSENT_TOKEN="Zzyzxqqq"

run_sync() {  # run_sync <sidecar-path>; echoes "<exit>|<summary-seen>"
  local list="$1" out rc summary
  out="$(MIRROR_CODENAMES_FILE="$list" bash "$SYNC" --dry-run 2>&1)"; rc=$?
  if printf '%s' "$out" | grep -qE '^(Sync:|Dry run:)'; then summary=yes; else summary=no; fi
  printf '%s|%s' "$rc" "$summary"
}

# 1. A sidecar-listed token inside a shared block aborts before the loop.
printf '%s|public-alias\n' "$PRESENT_TOKEN" > "$TMP/list-hit"
r=$(run_sync "$TMP/list-hit")
[ "${r%%|*}" != "0" ] && [ "${r##*|}" = "no" ] \
  && pass "planted token aborts before propagation (exit ${r%%|*}, no summary)" \
  || fail "planted token DID NOT abort (exit ${r%%|*}, summary=${r##*|}, expected non-zero + no summary)"

# 2. An absent sidecar is a SKIP, not a failure. This is the single most likely
#    way this slice breaks things: the sidecar is gitignored, so it is missing on
#    every machine but one, and on CI.
r=$(run_sync "$TMP/does-not-exist")
[ "${r%%|*}" = "0" ] && [ "${r##*|}" = "yes" ] \
  && pass "absent sidecar skips the guard and completes (exit 0, summary printed)" \
  || fail "absent sidecar BROKE the sync (exit ${r%%|*}, summary=${r##*|}, expected 0 + summary)"

# 3. A sidecar whose tokens do not occur in the shared blocks changes nothing.
printf '%s|public-alias\n' "$ABSENT_TOKEN" > "$TMP/list-clean"
r=$(run_sync "$TMP/list-clean")
[ "${r%%|*}" = "0" ] && [ "${r##*|}" = "yes" ] \
  && pass "clean sidecar completes normally (exit 0, summary printed)" \
  || fail "clean sidecar altered the run (exit ${r%%|*}, summary=${r##*|}, expected 0 + summary)"

# 4. THE ONE THE FIRST THREE COULD NOT SEE. An UNTRACKED block is propagated (the
#    propagator uses opendir) but was invisible to a tracked-only scan, so a gate
#    delegating to `git grep` cleared a brand-new block and copied the codename out
#    of it. Checks 1 to 3 all plant tokens that live in TRACKED files, so every one
#    of them passed while this path was wide open. Found by review, not by them.
SHARED_REAL="$SCRIPT_DIR/../../commands/_shared"
UNTRACKED="$SHARED_REAL/zz-gate-probe-untracked.md"
cleanup_untracked() { rm -f "$UNTRACKED"; }
trap 'cleanup_untracked; rm -rf "$TMP"' EXIT
printf 'probe block containing %s as literal text\n' "$ABSENT_TOKEN" > "$UNTRACKED"
if git -C "$SHARED_REAL" ls-files --error-unmatch "$UNTRACKED" >/dev/null 2>&1; then
  fail "probe file is tracked, so check 4 cannot test the untracked path"
else
  printf '%s|public-alias\n' "$ABSENT_TOKEN" > "$TMP/list-untracked"
  r=$(run_sync "$TMP/list-untracked")
  [ "${r%%|*}" != "0" ] && [ "${r##*|}" = "no" ] \
    && pass "token in an UNTRACKED block aborts (exit ${r%%|*}, no summary)" \
    || fail "UNTRACKED block SLIPPED THE GATE (exit ${r%%|*}, summary=${r##*|}, expected non-zero + no summary)"
fi
cleanup_untracked

# run_sync_gate <gate-path> <sidecar>; echoes "<exit>|<summary-seen>"
# Drives the REAL script with the guard path overridden. An earlier revision of
# this file re-implemented the parse check inline and asserted its own copy; the
# mutation run caught it (removing the check from the script left the suite green),
# which is why these two checks go through SYNC_GATE_SCRIPT instead.
run_sync_gate() {
  local gate="$1" list="$2" out rc summary
  out="$(SYNC_GATE_SCRIPT="$gate" MIRROR_CODENAMES_FILE="$list" bash "$SYNC" --dry-run 2>&1)"; rc=$?
  if printf '%s' "$out" | grep -qE '^(Sync:|Dry run:)'; then summary=yes; else summary=no; fi
  printf '%s|%s' "$rc" "$summary"
}

# 5. A guard present but not parseable must refuse, not be mistaken for the
#    no-sidecar skip: `bash` exits 2 on a parse error and so does the guard's own
#    missing-sidecar path, so without a parse check the operator is told
#    "skipped (no sidecar)" while a broken guard waves the codename through.
printf 'if [ ; then\n' > "$TMP/broken-guard.sh"
r=$(run_sync_gate "$TMP/broken-guard.sh" "$TMP/list-clean")
[ "${r%%|*}" != "0" ] && [ "${r##*|}" = "no" ] \
  && pass "an unparseable guard is refused (exit ${r%%|*}, no summary)" \
  || fail "an unparseable guard was NOT refused (exit ${r%%|*}, summary=${r##*|})"

# 5b. A missing guard must refuse too. Same class, opposite branch.
r=$(run_sync_gate "$TMP/no-such-guard.sh" "$TMP/list-clean")
[ "${r%%|*}" != "0" ] && [ "${r##*|}" = "no" ] \
  && pass "a missing guard is refused (exit ${r%%|*}, no summary)" \
  || fail "a missing guard was NOT refused (exit ${r%%|*}, summary=${r##*|})"

# 5c. An exit code that is neither a verdict nor a skip must fail CLOSED. This is
#     a deliberate divergence from scripts/lint-commands.sh, which treats an
#     unexpected code as a named skip: that caller reports on a tree that already
#     exists, this one decides whether to write into ~195 files.
printf '#!/usr/bin/env bash\nexit 126\n' > "$TMP/odd-guard.sh"
r=$(run_sync_gate "$TMP/odd-guard.sh" "$TMP/list-clean")
[ "${r%%|*}" != "0" ] && [ "${r##*|}" = "no" ] \
  && pass "an unexpected guard exit fails closed (exit ${r%%|*}, no summary)" \
  || fail "an unexpected guard exit did NOT fail closed (exit ${r%%|*}, summary=${r##*|})"

# 6. The gate must reproduce none of the guard's output. The redirect is the only
#    redaction and nothing else pins it, so a routine "let me see why it fired"
#    edit would print the guard's LEAK lines, codename and all.
grep -qE 'bash "\$GATE" .* >/dev/null 2>&1' "$SYNC" \
  && pass "the guard call still discards the guard's output" \
  || fail "the guard call no longer discards output; LEAK lines would print"

# 7. The gate must run BEFORE the propagation loop, not after. Check 1's proxy
#    (absent summary) would still pass if the block moved below the loop, because
#    an exit anywhere before the final echo suppresses the summary either way.
gate_line=$(grep -n 'Codename gate: found a listed codename' "$SYNC" | head -1 | cut -d: -f1)
loop_line=$(grep -n '^for cmd_file in' "$SYNC" | head -1 | cut -d: -f1)
[ -n "$gate_line" ] && [ -n "$loop_line" ] && [ "$gate_line" -lt "$loop_line" ] \
  && pass "the gate sits above the propagation loop (gate ${gate_line} < loop ${loop_line})" \
  || fail "the gate is NOT above the propagation loop (gate ${gate_line:-?}, loop ${loop_line:-?})"

echo
if [ "$fails" -eq 0 ]; then echo "test-sync-shared-blocks: all $checks checks passed"; exit 0
else echo "test-sync-shared-blocks: $fails of $checks check(s) FAILED"; exit 1; fi
