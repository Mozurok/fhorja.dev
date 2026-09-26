#!/usr/bin/env bash
# test-emit-substrate-apply.sh -- round-trip tests for the `apply` subcommand of
# emit-substrate-write.sh (v3 wave2 Slice 01, ADR-0110). Run from anywhere:
#   bash scripts/tests/test-emit-substrate-apply.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EMIT="$SCRIPT_DIR/../emit-substrate-write.sh"
PASS=0; FAIL=0

ok()   { PASS=$((PASS+1)); echo "ok   - $1"; }
fail() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }

check() { # check <description> <condition-exit-code(0=true)>
  if [[ "$2" -eq 0 ]]; then ok "$1"; else fail "$1"; fi
}

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"
mkdir -p .wos
# The emitter refuses a --task-root that is not a task folder (ADR-0224), so the fixture is one.
printf '# TASK_STATE\n' > TASK_STATE.md

make_fixture() {
  cat > DOC.md <<'FIXTURE_EOF'
# DOC

<!-- wos:write owner=old-owner section='## Alpha' run_id=01Jold ts=2026-01-01T00:00:00.000Z reason=seed mode=applied -->
## Alpha
alpha line one
alpha line two

<!-- wos:write owner=old-owner section='## Target' run_id=01Jold ts=2026-01-01T00:00:00.000Z reason=seed mode=applied -->
## Target
old body line

<!-- wos:write owner=old-owner section='## Empty' run_id=01Jold ts=2026-01-01T00:00:00.000Z reason=seed mode=applied -->
## Empty

<!-- wos:write owner=old-owner section='## Omega' run_id=01Jold ts=2026-01-01T00:00:00.000Z reason=seed mode=applied -->
## Omega
omega body
FIXTURE_EOF
}

log_lines() { { wc -l < .wos/VERIFICATION_LOG.jsonl; } 2>/dev/null || echo 0; }

# ---------- 1. die on missing section, nothing written ----------
make_fixture
printf 'new body\n' > body.txt
BEFORE_HASH=$(shasum -a 256 DOC.md | awk '{print $1}')
BEFORE_LOG=$(log_lines)
# An absent section is CREATED, not refused (2026-08-31). The old contract died
# here and sent every caller back to hand-inserting the heading and its header,
# which is the manual step apply exists to remove. These assertions replace the
# three that asserted the die; they are stricter, not looser: the section has to
# appear, carry the body, log exactly one line, and log it as a genesis write.
OUT=$(bash "$EMIT" apply --owner tester --file DOC.md --section '## Missing' --reason t1 --body-file body.txt --task-root . 2>&1)
rc=$?
check "absent section: exits 0" $([[ $rc -eq 0 ]]; echo $?)
check "absent section: says created, not applied" $(grep -q "^created '## Missing'" <<<"$OUT"; echo $?)
check "absent section: the heading now exists exactly once" $([[ "$(grep -cxF '## Missing' DOC.md)" -eq 1 ]]; echo $?)
check "absent section: the body landed" $(grep -q "$(head -1 body.txt)" DOC.md; echo $?)
check "absent section: a transaction header sits above it" $(grep -B1 -xF '## Missing' DOC.md | grep -q '<!-- wos:write '; echo $?)
check "absent section: exactly one JSONL line appended" $([[ "$(log_lines)" -eq "$((BEFORE_LOG + 1))" ]]; echo $?)
check "absent section: logged as a genesis write (sha_before null, event write)" $(tail -1 .wos/VERIFICATION_LOG.jsonl | python3 -c "
import json,sys
d=json.loads(sys.stdin.read())
sys.exit(0 if d.get('sha_before') in (None,'null') and d.get('event')=='write' else 1)"; echo $?)

# ---------- 2. die on code-fence decoy (non-unique exact line) ----------
make_fixture
cat >> DOC.md <<'DECOY_EOF'

<!-- wos:write owner=old-owner section='## Snippets' run_id=01Jold ts=2026-01-01T00:00:00.000Z reason=seed mode=applied -->
## Snippets
```markdown
## Target
```
DECOY_EOF
BEFORE_HASH=$(shasum -a 256 DOC.md | awk '{print $1}')
BEFORE_LOG=$(log_lines)
bash "$EMIT" apply --owner tester --file DOC.md --section '## Target' --reason t2 --body-file body.txt --task-root . >/dev/null 2>&1
rc=$?
check "die on code-fence decoy (non-unique target line)" $([[ $rc -ne 0 ]]; echo $?)
check "decoy die leaves file unchanged" $([[ "$(shasum -a 256 DOC.md | awk '{print $1}')" == "$BEFORE_HASH" ]]; echo $?)
check "decoy die appends no JSONL" $([[ "$(log_lines)" -eq "$BEFORE_LOG" ]]; echo $?)

# ---------- 3. happy path: splice, header replace, hashes, one JSONL ----------
make_fixture
rm -f .wos/VERIFICATION_LOG.jsonl
printf 'replacement one\nreplacement two\n' > body.txt
SB_PRE=$(bash "$EMIT" sha --file DOC.md --section '## Target')
bash "$EMIT" apply --owner tester --file DOC.md --section '## Target' --reason t3 --body-file body.txt --task-root . --run-id 01Jtest >/dev/null 2>&1
rc=$?
check "happy-path apply exits 0" $([[ $rc -eq 0 ]]; echo $?)
SA_POST=$(bash "$EMIT" sha --file DOC.md --section '## Target')
LOG_SB=$(jq -r 'select(.section=="## Target") | .sha_before' .wos/VERIFICATION_LOG.jsonl | tail -1)
LOG_SA=$(jq -r 'select(.section=="## Target") | .sha_after'  .wos/VERIFICATION_LOG.jsonl | tail -1)
check "JSONL sha_before equals pre-write sha subcommand value" $([[ "$LOG_SB" == "$SB_PRE" ]]; echo $?)
check "JSONL sha_after equals post-write sha subcommand value" $([[ "$LOG_SA" == "$SA_POST" ]]; echo $?)
check "exactly one JSONL line appended" $([[ "$(log_lines)" -eq 1 ]]; echo $?)
check "section body replaced" $(grep -q 'replacement two' DOC.md; echo $?)
check "old body gone" $([[ "$(grep -c 'old body line' DOC.md)" -eq 0 ]]; echo $?)
HDRS=$(awk '/^<!-- wos:write /{h=$0} /^## Target$/{print h}' DOC.md)
check "header above target replaced with new owner" $(printf '%s' "$HDRS" | grep -q 'owner=tester'; echo $?)
check "exactly one header line above target" $([[ "$(grep -c "section='## Target'" DOC.md)" -eq 1 ]]; echo $?)
check "neighbor sections intact (Alpha)" $(grep -q 'alpha line two' DOC.md; echo $?)
check "neighbor sections intact (Omega)" $(grep -q 'omega body' DOC.md; echo $?)
NEXT_HDR_OK=$(awk '/^## Empty$/{print prev} {prev=$0}' DOC.md | grep -c 'owner=old-owner')
check "next section keeps its own header (not consumed by splice)" $([[ "$NEXT_HDR_OK" -eq 1 ]]; echo $?)

# ---------- 4. existing-but-empty section proceeds, sha_before null ----------
printf 'empty no more\n' > body.txt
bash "$EMIT" apply --owner tester --file DOC.md --section '## Empty' --reason t4 --body-file body.txt --task-root . >/dev/null 2>&1
rc=$?
check "apply proceeds on existing-but-empty section" $([[ $rc -eq 0 ]]; echo $?)
LOG_SB=$(jq -r 'select(.section=="## Empty") | .sha_before' .wos/VERIFICATION_LOG.jsonl | tail -1)
check "empty-section sha_before recorded as null" $([[ "$LOG_SB" == "null" ]]; echo $?)
check "empty section gained the body" $(grep -q 'empty no more' DOC.md; echo $?)

# ---------- 5. expected-sha guard: caller mismatch dies ----------
bash "$EMIT" apply --owner tester --file DOC.md --section '## Omega' --reason t5 --body-file body.txt --task-root . --sha-before deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef >/dev/null 2>&1
rc=$?
check "caller sha_before mismatch dies (measured is authoritative)" $([[ $rc -ne 0 ]]; echo $?)

# ---------- 6. body containing a new H2 or header line dies ----------
printf '## Sneaky new section\n' > body.txt
bash "$EMIT" apply --owner tester --file DOC.md --section '## Omega' --reason t6 --body-file body.txt --task-root . >/dev/null 2>&1
rc=$?
check "body with an H2 line dies (an H2 would move the hashed boundary)" $([[ $rc -ne 0 ]]; echo $?)
printf '<!-- wos:write owner=x section=y -->\n' > body.txt
bash "$EMIT" apply --owner tester --file DOC.md --section '## Omega' --reason t7 --body-file body.txt --task-root . >/dev/null 2>&1
rc=$?
check "body with a wos:write line dies (excluded from hash, would break self-check)" $([[ $rc -ne 0 ]]; echo $?)

# ---------- 7. last section of file (EOF boundary) ----------
printf 'omega rewritten\n' > body.txt
bash "$EMIT" apply --owner tester --file DOC.md --section '## Omega' --reason t8 --body-file body.txt --task-root . >/dev/null 2>&1
rc=$?
check "apply works on the last section (EOF boundary)" $([[ $rc -eq 0 ]]; echo $?)
check "last-section body replaced" $(grep -q 'omega rewritten' DOC.md; echo $?)

# ---------- 8. legacy subcommands behavior smoke (byte-identical constraint) ----------
SB=$(bash "$EMIT" sha --file DOC.md --section '## Alpha')
check "legacy sha still works" $([[ -n "$SB" && "$SB" != "null" ]]; echo $?)
BEFORE_LOG=$(log_lines)
bash "$EMIT" emit --owner tester --file DOC.md --section '## Alpha' --mode applied --reason legacy --sha-before "$SB" --first-logged-write --task-root . >/dev/null 2>&1
rc=$?
check "legacy emit still works (first-logged-write path since the v3 wave3 derive default)" $([[ $rc -eq 0 && "$(log_lines)" -eq $((BEFORE_LOG+1)) ]]; echo $?)

# ---------- 9. a --task-root that is not a task folder refuses (ADR-0224) ----------
# Before this, the emitter ran `mkdir -p <root>/.wos` on whatever root it was given, so a
# wrong root grew a stray log no validator reads and the write looked logged. On the old
# emitter every assertion below fails: exit 0, a new stray log, and a changed DOC.md.
STRAY="$WORK/not-a-task"; mkdir -p "$STRAY"
printf 'refused body\n' > body.txt
DOC_BEFORE=$(shasum -a 256 DOC.md | awk '{print $1}')
OUT=$(bash "$EMIT" apply --owner tester --file DOC.md --section '## Omega' --reason t9 --body-file body.txt --task-root "$STRAY" 2>&1)
rc=$?
check "apply with a --task-root holding no TASK_STATE.md refuses" $([[ $rc -ne 0 ]]; echo $?)
check "the refusal names the missing TASK_STATE.md" $(grep -q 'no TASK_STATE.md found' <<<"$OUT"; echo $?)
check "the refusal writes no stray log" $([[ ! -e "$STRAY/.wos" ]]; echo $?)
check "the refusal leaves the target file untouched" $([[ "$(shasum -a 256 DOC.md | awk '{print $1}')" == "$DOC_BEFORE" ]]; echo $?)
OUT=$(bash "$EMIT" emit --owner tester --file DOC.md --section '## Alpha' --mode applied --reason t9 --task-root "$STRAY" 2>&1)
rc=$?
check "emit with the same root refuses too, with no stray log" $([[ $rc -ne 0 && ! -e "$STRAY/.wos" ]]; echo $?)

echo
echo "pass=$PASS fail=$FAIL"
[[ "$FAIL" -eq 0 ]] || exit 1
