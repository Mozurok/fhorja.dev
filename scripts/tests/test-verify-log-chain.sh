#!/usr/bin/env bash
# test-verify-log-chain.sh -- sha-chain and tip-check semantics of
# verify-log-validator.py plus the battery-default activation in
# verify-substrate-batch.sh (v3 wave4 Slice 05, S1 tail). Run from anywhere:
#   bash scripts/tests/test-verify-log-chain.sh
#
# The chain/tip machinery itself shipped 2026-07-18 (S1 opt-in, --cutover-ts);
# checks 1-8 are characterization pins over that shipped semantics. Check 9-10
# are the NEW behavior (TDD red-to-green): the batch wrapper activates the
# checks by default with the S1 cutover when WOS_CUTOVER_TS is unset.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATOR="$SCRIPT_DIR/../verify-log-validator.py"
WRAPPER="$SCRIPT_DIR/../verify-substrate-batch.sh"
EMIT="$SCRIPT_DIR/../emit-substrate-write.sh"
CUT="2026-07-18T00:00:00.000Z"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "ok   - $1"; }
fail() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }
check() { if [[ "$2" -eq 0 ]]; then ok "$1"; else fail "$1"; fi }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
# scan-substrate-headers.sh (stage 1 of the wrapper) requires the task folder
# to live inside a git repo; give the fixtures one with a root commit.
git -c init.defaultBranch=main init -q "$WORK"
git -C "$WORK" -c user.email=t@test -c user.name=t commit -q --allow-empty -m init

SA="a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1"
SB="b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2"
SC="c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3c3"
SD="d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4d4"

# jline TS EVENT MODE SHA_BEFORE SHA_AFTER  (file GHOST.md: absent on disk, so
# the delete-orphan and content-vs-log cross-checks skip; chain is log-internal)
jline() {
  local sb=$4 sa=$5
  [[ "$sb" == null ]] || sb="\"$sb\""
  [[ "$sa" == null ]] || sa="\"$sa\""
  printf '{"ts":"%s","run_id":"01Jtest","owner":"t","owner_type":"command","invoked_by":null,"file":"GHOST.md","section":"## S","event":"%s","mode":"%s","sha_before":%s,"sha_after":%s,"reason":"t","partials":null,"strategy":null}\n' "$1" "$2" "$3" "$sb" "$sa"
}

mklog() { mkdir -p "$WORK/$1/.wos"; cat > "$WORK/$1/.wos/VERIFICATION_LOG.jsonl"; }

# ---------- 1. valid chain passes in error mode ----------
mklog A <<EOF
$(jline 2026-07-20T10:00:00.000Z write applied null "$SA")
$(jline 2026-07-20T10:01:00.000Z overwrite applied "$SA" "$SB")
EOF
python3 "$VALIDATOR" "$WORK/A/.wos/VERIFICATION_LOG.jsonl" --check-deletes --cutover-ts "$CUT" >/dev/null 2>&1
check "valid chain: exit 0 under --check-deletes + cutover" $?

# ---------- 2. broken chain fails in error mode ----------
mklog B <<EOF
$(jline 2026-07-20T10:00:00.000Z write applied null "$SA")
$(jline 2026-07-20T10:01:00.000Z overwrite applied "$SC" "$SB")
EOF
RC=0; OUT=$(python3 "$VALIDATOR" "$WORK/B/.wos/VERIFICATION_LOG.jsonl" --check-deletes --cutover-ts "$CUT" 2>&1) || RC=$?
check "broken chain: nonzero exit under --check-deletes + cutover" $([[ "$RC" -ne 0 ]]; echo $?)
check "broken chain: break names the section" $(grep -q "sha-chain break" <<<"$OUT"; echo $?)

# ---------- 3. broken chain without --check-deletes stays advisory ----------
RC=0; python3 "$VALIDATOR" "$WORK/B/.wos/VERIFICATION_LOG.jsonl" --cutover-ts "$CUT" >/dev/null 2>&1 || RC=$?
check "broken chain without --check-deletes: exit 0 (advisory)" $([[ "$RC" -eq 0 ]]; echo $?)

# ---------- 4. legacy-promote resets the chain ----------
mklog C <<EOF
$(jline 2026-07-20T10:00:00.000Z write applied null "$SA")
$(jline 2026-07-20T10:01:00.000Z legacy-promote applied "$SC" "$SD")
$(jline 2026-07-20T10:02:00.000Z overwrite applied "$SD" "$SB")
EOF
python3 "$VALIDATOR" "$WORK/C/.wos/VERIFICATION_LOG.jsonl" --check-deletes --cutover-ts "$CUT" >/dev/null 2>&1
check "legacy-promote resets the chain baseline: exit 0" $?

# ---------- 5. delete then fresh write opens a new chain ----------
mklog D <<EOF
$(jline 2026-07-20T10:00:00.000Z write applied null "$SA")
$(jline 2026-07-20T10:01:00.000Z delete applied "$SA" null)
$(jline 2026-07-20T10:02:00.000Z write applied null "$SB")
EOF
python3 "$VALIDATOR" "$WORK/D/.wos/VERIFICATION_LOG.jsonl" --check-deletes --cutover-ts "$CUT" >/dev/null 2>&1
check "delete then fresh write: exit 0" $?

# ---------- 6. proposed lines are outside the chain ----------
mklog E <<EOF
$(jline 2026-07-20T10:00:00.000Z write applied null "$SA")
$(jline 2026-07-20T10:01:00.000Z overwrite proposed "$SC" "$SD")
$(jline 2026-07-20T10:02:00.000Z overwrite applied "$SA" "$SB")
EOF
python3 "$VALIDATOR" "$WORK/E/.wos/VERIFICATION_LOG.jsonl" --check-deletes --cutover-ts "$CUT" >/dev/null 2>&1
check "proposed line does not enter the chain: exit 0" $?

# ---------- 7. pre-cutover breaks are grandfathered ----------
mklog F <<EOF
$(jline 2026-07-01T10:00:00.000Z write applied null "$SA")
$(jline 2026-07-01T10:01:00.000Z overwrite applied "$SC" "$SB")
EOF
python3 "$VALIDATOR" "$WORK/F/.wos/VERIFICATION_LOG.jsonl" --check-deletes --cutover-ts "$CUT" >/dev/null 2>&1
check "pre-cutover break grandfathered: exit 0" $?

# ---------- 8. consistent real fixture built with the emitter (tip check included) ----------
mkdir -p "$WORK/G/.wos"; cd "$WORK/G"
cat > TASK_STATE.md <<'EOF'
# TASK_STATE

<!-- wos:write owner=t section='## S' run_id=01Jt ts=2026-07-20T10:00:00.000Z reason=t mode=applied -->
## S
body v1
EOF
bash "$EMIT" emit --owner t --file TASK_STATE.md --section '## S' --event write --mode applied --reason t --sha-before null --task-root . >/dev/null 2>&1
python3 "$VALIDATOR" "$WORK/G/.wos/VERIFICATION_LOG.jsonl" --check-deletes --cutover-ts "$CUT" >/dev/null 2>&1
check "emitter-built fixture: chain plus tip check clean (exit 0)" $?
cd "$WORK"

# ---------- 9-10. NEW: wrapper activates the checks by default (red-to-green) ----------
RC=0; bash "$WRAPPER" "$WORK/B" >/dev/null 2>&1 || RC=$?
check "wrapper over broken chain: nonzero WITHOUT env (battery default)" $([[ "$RC" -ne 0 ]]; echo $?)
RC=0; bash "$WRAPPER" "$WORK/G" >/dev/null 2>&1 || RC=$?
check "wrapper over consistent fixture: exit 0 (no false positive)" $([[ "$RC" -eq 0 ]]; echo $?)

# ---------- 11. explicit env still wins over the wrapper default ----------
RC=0; WOS_CUTOVER_TS=2099-01-01T00:00:00.000Z bash "$WRAPPER" "$WORK/B" >/dev/null 2>&1 || RC=$?
check "wrapper honors explicit WOS_CUTOVER_TS override (future cutover: exit 0)" $([[ "$RC" -eq 0 ]]; echo $?)

echo "----"
echo "pass=$PASS fail=$FAIL"
[[ "$FAIL" -eq 0 ]]
