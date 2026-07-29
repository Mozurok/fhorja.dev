#!/usr/bin/env bash
# test-emit-substrate-derive.sh -- derive-by-default behaviors of the `emit`
# subcommand (v3 wave3 Slice 01, item S2). Run from anywhere:
#   bash scripts/tests/test-emit-substrate-derive.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EMIT="$SCRIPT_DIR/../emit-substrate-write.sh"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "ok   - $1"; }
fail() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }
check() { if [[ "$2" -eq 0 ]]; then ok "$1"; else fail "$1"; fi }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"
mkdir -p .wos

cat > DOC.md <<'FIX_EOF'
# DOC

<!-- wos:write owner=seed section='## Logged' run_id=01Jseed ts=2026-01-01T00:00:00.000Z reason=seed mode=applied -->
## Logged
logged body v1

## LegacySection
legacy body never logged

## FreshEmpty
FIX_EOF

last_field() { jq -r --arg s "$1" --arg f "$2" 'select(.section==$s) | .[$f]' .wos/VERIFICATION_LOG.jsonl | tail -1; }

# Seed one log record for ## Logged (explicit null on first write, legacy-compatible path).
bash "$EMIT" emit --owner seed --file DOC.md --section '## Logged' --event write --mode applied --reason seed --sha-before null --task-root . >/dev/null 2>&1
SA1=$(last_field '## Logged' sha_after)
check "seed record created with real sha_after" $([[ -n "$SA1" && "$SA1" != "null" ]]; echo $?)

# ---------- 1. default derive: no flags, chain matches ----------
printf '%s\n' 'logged body v2' > body.txt
python3 - <<'PY'
s=open('DOC.md').read()
open('DOC.md','w').write(s.replace('logged body v1','logged body v2'))
PY
bash "$EMIT" emit --owner tester --file DOC.md --section '## Logged' --event overwrite --mode applied --reason t1 --task-root . >/dev/null 2>&1
rc=$?
SB_LOGGED=$(last_field '## Logged' sha_before)
check "default emit succeeds with derived sha_before" $([[ $rc -eq 0 ]]; echo $?)
check "derived sha_before equals the prior record sha_after" $([[ "$SB_LOGGED" == "$SA1" ]]; echo $?)

# ---------- 2. caller explicit mismatch dies ----------
BEFORE_LOG=$(wc -l < .wos/VERIFICATION_LOG.jsonl)
bash "$EMIT" emit --owner tester --file DOC.md --section '## Logged' --event overwrite --mode applied --reason t2 --sha-before deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef --task-root . > /tmp/derive_t2.txt 2>&1
rc=$?
check "explicit sha_before mismatching the derived value dies" $([[ $rc -ne 0 ]]; echo $?)
check "mismatch die appends no JSONL" $([[ "$(wc -l < .wos/VERIFICATION_LOG.jsonl)" -eq "$BEFORE_LOG" ]]; echo $?)
check "mismatch message names the override flag" $(grep -q "allow-sha-before-mismatch" /tmp/derive_t2.txt; echo $?)

# ---------- 3. no record + non-null caller sha dies with guidance ----------
MEASURED=$(bash "$EMIT" sha --file DOC.md --section '## LegacySection')
bash "$EMIT" emit --owner tester --file DOC.md --section '## LegacySection' --event write --mode applied --reason t3 --sha-before "$MEASURED" --task-root . > /tmp/derive_t3.txt 2>&1
rc=$?
check "no-record plus non-null sha dies" $([[ $rc -ne 0 ]]; echo $?)
check "die message points at --first-logged-write" $(grep -q "first-logged-write" /tmp/derive_t3.txt; echo $?)

# ---------- 4. --first-logged-write with a prior record dies ----------
bash "$EMIT" emit --owner tester --file DOC.md --section '## Logged' --event overwrite --mode applied --reason t4 --first-logged-write --task-root . >/dev/null 2>&1
rc=$?
check "first-logged-write against a recorded section dies" $([[ $rc -ne 0 ]]; echo $?)

# ---------- 5. --first-logged-write on a recordless existing section succeeds ----------
bash "$EMIT" emit --owner tester --file DOC.md --section '## LegacySection' --mode applied --reason t5 --first-logged-write --task-root . >/dev/null 2>&1
rc=$?
SB_LEG=$(last_field '## LegacySection' sha_before)
EV_LEG=$(last_field '## LegacySection' event)
check "first-logged-write on recordless existing section succeeds" $([[ $rc -eq 0 ]]; echo $?)
check "legacy-promote event recorded" $([[ "$EV_LEG" == "legacy-promote" ]]; echo $?)
check "measured sha_before recorded (not null)" $([[ "$SB_LEG" == "$MEASURED" && "$SB_LEG" != "null" ]]; echo $?)

# ---------- 6. opt-out flag restores legacy trust-the-caller ----------
bash "$EMIT" emit --owner tester --file DOC.md --section '## Logged' --event overwrite --mode applied --reason t6 --sha-before deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef --no-derive-sha-before --task-root . >/dev/null 2>&1
rc=$?
check "opt-out flag accepts the caller sha verbatim" $([[ $rc -eq 0 ]]; echo $?)

# ---------- 7. env opt-out (no explicit flag) ----------
WOS_DERIVE_SHA_BEFORE=0 bash "$EMIT" emit --owner tester --file DOC.md --section '## Logged' --event overwrite --mode applied --reason t7 --sha-before cafecafecafecafecafecafecafecafecafecafecafecafecafecafecafecafe --task-root . >/dev/null 2>&1
rc=$?
check "env WOS_DERIVE_SHA_BEFORE=0 opts out" $([[ $rc -eq 0 ]]; echo $?)

# ---------- 8. null-first-write on a genuinely new section still works ----------
printf 'fresh body\n' > /dev/null
python3 - <<'PY'
s=open('DOC.md').read()
open('DOC.md','w').write(s.replace('## FreshEmpty\n','## FreshEmpty\nfresh body now\n'))
PY
bash "$EMIT" emit --owner tester --file DOC.md --section '## FreshEmpty' --event write --mode applied --reason t8 --sha-before null --task-root . >/dev/null 2>&1
rc=$?
check "explicit null on a recordless section still succeeds" $([[ $rc -eq 0 ]]; echo $?)

# ---------- 9. apply path unaffected (smoke) ----------
printf 'applied body\n' > body.txt
bash "$EMIT" apply --owner tester --file DOC.md --section '## Logged' --reason t9 --body-file body.txt --task-root . >/dev/null 2>&1
rc=$?
check "apply path still works under the new default" $([[ $rc -eq 0 ]]; echo $?)

echo
echo "pass=$PASS fail=$FAIL"
[[ "$FAIL" -eq 0 ]] || exit 1
