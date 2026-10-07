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

# ---------- 10. status: one call edits one slice Status line and logs it (P-9) ----------
# A fresh task folder: implementation-plan writes ## Slices through apply, the approval
# is appended, then closing commands write Status lines through `status`. The checks are
# the ones a closure batch runs, the slice-order gate, and the approval lock's query.
TF="$WORK/status-task"; mkdir -p "$TF"; printf '# TASK_STATE\n' > "$TF/TASK_STATE.md"
printf '# Implementation plan\n\n## Slices\n\n## Approval log\n' > "$TF/IMPLEMENTATION_PLAN.md"
cat > "$WORK/slices.txt" <<'SLICES_EOF'

### S1: first slice
- Depends-on: none
- Status: planned

### S2: second slice
- Depends-on: S1
- **Status:** planned
SLICES_EOF
plan_hash() { shasum -a 256 "$TF/IMPLEMENTATION_PLAN.md" | awk '{print $1}'; }
tf_log_lines() { wc -l < "$TF/.wos/VERIFICATION_LOG.jsonl" | tr -d ' '; }
bash "$EMIT" apply --owner implementation-plan --file IMPLEMENTATION_PLAN.md --section '## Slices' --reason plan --body-file "$WORK/slices.txt" --task-root "$TF" >/dev/null 2>&1
check "status fixture: implementation-plan wrote ## Slices" $?
sleep 1
APPROVAL_TS=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
printf -- '- %s: APPROVED -- baseline locked for execution.\n' "$APPROVAL_TS" >> "$TF/IMPLEMENTATION_PLAN.md"
# The lock in commands/implement-approved-slice.md: the plan revision is the newest
# `## Slices` log line whose owner is implementation-plan or self-critique-and-revise.
lock_rev() { jq -r 'select(.section=="## Slices" and (.owner=="implementation-plan" or .owner=="self-critique-and-revise")) | .ts' "$TF/.wos/VERIFICATION_LOG.jsonl" | tail -1; }
REV_BEFORE=$(lock_rev)
sleep 1

BEFORE_LOG=$(tf_log_lines)
bash "$EMIT" status --owner slice-closure --file IMPLEMENTATION_PLAN.md --slice S1 --value closed --task-root "$TF" >/dev/null 2>&1
check "status: good write exits 0" $?
check "status: S1 Status line now reads closed" $(awk '/^### S1/{f=1;next} /^### /{f=0} f' "$TF/IMPLEMENTATION_PLAN.md" | grep -qxF -- '- Status: closed'; echo $?)
check "status: S2 Status line untouched" $(grep -qxF -- '- **Status:** planned' "$TF/IMPLEMENTATION_PLAN.md"; echo $?)
check "status: exactly one JSONL line appended" $([[ "$(tf_log_lines)" -eq $((BEFORE_LOG+1)) ]]; echo $?)
check "status: logged at ## Slices by the closing owner as an applied overwrite" $(tail -1 "$TF/.wos/VERIFICATION_LOG.jsonl" | jq -e '.section=="## Slices" and .owner=="slice-closure" and .event=="overwrite" and .mode=="applied"' >/dev/null; echo $?)
check "status: one ## Slices header, naming the closing owner" $([[ "$(grep -c "section='## Slices'" "$TF/IMPLEMENTATION_PLAN.md")" -eq 1 ]] && grep -B1 -xF '## Slices' "$TF/IMPLEMENTATION_PLAN.md" | grep -q 'owner=slice-closure'; echo $?)
check "status: slice-order gate reads S1 as closed before S2 starts" $(bash "$SCRIPT_DIR/../check-slice-order.sh" "$TF" S2 >/dev/null 2>&1; echo $?)

# A value already in place writes nothing and logs nothing.
H=$(plan_hash); L=$(tf_log_lines)
bash "$EMIT" status --owner slice-closure --file IMPLEMENTATION_PLAN.md --slice S1 --value closed --task-root "$TF" >/dev/null 2>&1
rc=$?
check "status: an unchanged value exits 0 and leaves file and log as they were" $([[ $rc -eq 0 && "$(plan_hash)" == "$H" && "$(tf_log_lines)" -eq $L ]]; echo $?)

# Refusals leave the plan and the log untouched.
refuses() { # refuses <description> <task-folder> <args...>
  local d="$1" tf="$2"; shift 2
  local h l
  h=$(shasum -a 256 "$tf/IMPLEMENTATION_PLAN.md" | awk '{print $1}'); l=$(wc -l < "$tf/.wos/VERIFICATION_LOG.jsonl" | tr -d ' ')
  bash "$EMIT" status --file IMPLEMENTATION_PLAN.md --task-root "$tf" "$@" >/dev/null 2>&1
  local rc=$?
  check "$d" $([[ $rc -ne 0 && "$(shasum -a 256 "$tf/IMPLEMENTATION_PLAN.md" | awk '{print $1}')" == "$h" && "$(wc -l < "$tf/.wos/VERIFICATION_LOG.jsonl" | tr -d ' ')" -eq $l ]]; echo $?)
}
refuses "status: a missing slice id refuses, nothing written" "$TF" --owner slice-closure --slice S9 --value closed
refuses "status: owner implementation-plan refuses (its line would be a plan revision)" "$TF" --owner implementation-plan --slice S2 --value closed
refuses "status: owner self-critique-and-revise refuses" "$TF" --owner self-critique-and-revise --slice S2 --value closed

# `Slice 2` names `### S2` the way scripts/check-slice-order.sh reads ids; bold field kept.
bash "$EMIT" status --owner implement-approved-slice --file IMPLEMENTATION_PLAN.md --slice 'Slice 2' --value closed --task-root "$TF" >/dev/null 2>&1
check "status: a 'Slice 2' id writes '### S2', keeping the bold field label" $(grep -qxF -- '- **Status:** closed' "$TF/IMPLEMENTATION_PLAN.md"; echo $?)

VAL=$(python3 "$SCRIPT_DIR/../verify-log-validator.py" "$TF/.wos/VERIFICATION_LOG.jsonl" --check-deletes --cutover-ts 2026-07-18T00:00:00.000Z 2>&1)
vrc=$?
check "status: the validator with --check-deletes exits 0 after two status writes" $([[ $vrc -eq 0 ]]; echo $?)
check "status: no content-vs-log drift" $(grep -q 'content-vs-log drift' <<<"$VAL"; [[ $? -ne 0 ]]; echo $?)
check "status: no sha-chain break or advisory" $(grep -qi 'sha-chain' <<<"$VAL"; [[ $? -ne 0 ]]; echo $?)
REV_AFTER=$(lock_rev)
check "status: two status writes are not a ## Slices revision for the approval lock" $([[ -n "$REV_BEFORE" && "$REV_AFTER" == "$REV_BEFORE" && ! "$REV_AFTER" > "$APPROVAL_TS" ]]; echo $?)
# Control: the same query does see an authoring write, so the assertion above is not vacuous.
printf '\n### S1: first slice\n- Depends-on: none\n- Status: closed\n' > "$WORK/slices2.txt"
bash "$EMIT" apply --owner self-critique-and-revise --file IMPLEMENTATION_PLAN.md --section '## Slices' --reason revise --body-file "$WORK/slices2.txt" --task-root "$TF" >/dev/null 2>&1
check "status control: an authoring write does move the lock past the approval" $([[ "$(lock_rev)" > "$APPROVAL_TS" ]]; echo $?)

# Two Status lines under one slice refuse (a copy, so the folder above stays logged).
TF2="$WORK/status-task-2"; cp -R "$TF" "$TF2"
awk '{print} /^### S1: /{print "- Status: in progress"}' "$TF2/IMPLEMENTATION_PLAN.md" > "$WORK/p2" && cp "$WORK/p2" "$TF2/IMPLEMENTATION_PLAN.md"
refuses "status: two Status lines under the slice refuse, nothing written" "$TF2" --owner slice-closure --slice S1 --value not-ready

echo
echo "pass=$PASS fail=$FAIL"
[[ "$FAIL" -eq 0 ]] || exit 1
