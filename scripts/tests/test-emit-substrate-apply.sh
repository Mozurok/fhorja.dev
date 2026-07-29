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
bash "$EMIT" apply --owner tester --file DOC.md --section '## Missing' --reason t1 --body-file body.txt --task-root . >/dev/null 2>&1
rc=$?
check "die on absent section (exit non-zero)" $([[ $rc -ne 0 ]]; echo $?)
check "die on absent section leaves file unchanged" $([[ "$(shasum -a 256 DOC.md | awk '{print $1}')" == "$BEFORE_HASH" ]]; echo $?)
check "die on absent section appends no JSONL" $([[ "$(log_lines)" -eq "$BEFORE_LOG" ]]; echo $?)

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
check "body with an H2 line dies (apply never creates sections)" $([[ $rc -ne 0 ]]; echo $?)
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

echo
echo "pass=$PASS fail=$FAIL"
[[ "$FAIL" -eq 0 ]] || exit 1
