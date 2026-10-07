#!/usr/bin/env bash
# Verify the explicit Bash and Python suite list and its actual execution block.
# Disposable stubs exercise interpreter selection and aggregate failure handling.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKFLOW="${REPO}/.github/workflows/lint.yml"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

# Scope membership to the named step and the for-list, excluding comments and
# unrelated steps. This is deliberately a checker for this repository's format.
suite_block() {
  awk '
    /^      - name: Run script test suites$/ { step=1; next }
    step && /^        run: \|$/ { p=1; next }
    p && /^          / { sub(/^          /, ""); print; body=1; next }
    p && /^$/ { print; next }
    p { exit }
    END { if (!body) exit 1 }
  ' "$1"
}
declared() {
  suite_block "$1" | awk '
    /^[[:space:]]*for t in/ { p=1 }
    p && /^[[:space:]]*do([[:space:]]|$)/ { exit }
    p && !/^[[:space:]]*#/ { print }
  ' | grep -oE '\./scripts/tests/test-[A-Za-z0-9._-]+\.(sh|py)' | sed 's#.*/##' | sort -u
}
present() {
  find "$1" -maxdepth 1 -type f \( -name 'test-*.sh' -o -name 'test-*.py' \) -exec basename {} \; | sort -u
}
unlisted() { comm -23 <(present "$2") <(declared "$1"); }
dangling() { comm -13 <(present "$2") <(declared "$1"); }
loop_parses() {
  local block
  block="$(suite_block "$1")" || return 1
  printf '%s\n' "$block" | grep -qE '^[[:space:]]*for t in' || return 1
  printf '%s\n' "$block" | bash -n 2>/dev/null
}
write_workflow() {
  printf 'jobs:\n  script-tests:\n    steps:\n      - name: Run script test suites\n        run: |\n' > "$1"
  sed 's/^/          /' >> "$1"
}

# Run the real step, replacing only its allowlist with two disposable stubs.
# Retain the aggregate gate after done; syntax-only or body-only checks miss it.
runner_works() {
  local probe block sh_rc py_rc rc expected trace
  loop_parses "$1" || return 1
  probe="$(mktemp -d "$TMP/runner.XXXXXX")" || return 1
  block="$(suite_block "$1")" || return 1
  printf '%s\n' "$block" | awk '
    /^[[:space:]]*for t in/ { print "for t in \"$CI_PROBE_SH\" \"$CI_PROBE_PY\""; skip=1; next }
    skip && /^[[:space:]]*do([[:space:]]|$)/ { skip=0 }
    !skip { print }
  ' > "$probe/run.sh"
  cat > "$probe/test-alpha.sh" <<'STUB'
#!/usr/bin/env bash
printf 'shell\n' >> "$CI_PROBE_TRACE"
exit "$CI_PROBE_SH_RC"
STUB
  cat > "$probe/test-beta.py" <<'STUB'
import os, pathlib, sys
with pathlib.Path(os.environ['CI_PROBE_TRACE']).open('a') as stream:
    stream.write('python\n')
sys.exit(int(os.environ['CI_PROBE_PY_RC']))
STUB
  for sh_rc in 0 7; do
    for py_rc in 0 9; do
      trace="$probe/trace"; rm -f "$trace"
      expected=0; [[ "$sh_rc" == 0 && "$py_rc" == 0 ]] || expected=1
      CI_PROBE_SH="$probe/test-alpha.sh" CI_PROBE_PY="$probe/test-beta.py" \
        CI_PROBE_TRACE="$trace" CI_PROBE_SH_RC="$sh_rc" CI_PROBE_PY_RC="$py_rc" \
        bash "$probe/run.sh" > "$probe/output" 2>&1
      rc=$?
      [[ "$rc" == "$expected" && -f "$trace" ]] || return 1
      [[ "$(cat "$trace")" == $'shell\npython' ]] || return 1
    done
  done
}

[[ -f "$WORKFLOW" ]] || { echo "FAIL: workflow missing"; exit 1; }
u="$(unlisted "$WORKFLOW" "$REPO/scripts/tests")"
if [[ -z "$u" ]]; then pass "all Bash and Python suites appear in the executable for-list"; else
  fail "suite(s) CI never runs: $u"
fi
d="$(dangling "$WORKFLOW" "$REPO/scripts/tests")"
[[ -z "$d" ]] && pass "all listed suites exist" || fail "listed suite(s) absent: $d"
n_present="$(present "$REPO/scripts/tests" | wc -l | tr -d ' ')"
n_declared="$(declared "$WORKFLOW" | wc -l | tr -d ' ')"
[[ "$n_present" == "$n_declared" ]] && pass "counts agree ($n_present)" || fail "counts disagree ($n_present versus $n_declared)"
loop_parses "$WORKFLOW" && pass "actual suite block parses" || fail "actual suite block missing or malformed"
runner_works "$WORKFLOW" && pass "actual block dispatches both languages and propagates each failure combination" || fail "actual interpreter or aggregate failure handling is broken"

mkdir "$TMP/tests"
printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP/tests/test-alpha.sh"
printf 'raise SystemExit(0)\n' > "$TMP/tests/test-beta.py"
write_workflow "$TMP/control.yml" <<'BLOCK'
set -euo pipefail
fail=0
for t in \
  ./scripts/tests/test-alpha.sh \
  ./scripts/tests/test-beta.py
do
  case "$t" in
    *.sh) interpreter=bash ;;
    *.py) interpreter=python3 ;;
    *) fail=$((fail + 1)); continue ;;
  esac
  if "$interpreter" "$t"; then
    echo "PASS: $t"
  else
    echo "FAIL: $t"
    fail=$((fail + 1))
  fi
done
if [[ "$fail" -gt 0 ]]; then
  exit 1
fi
BLOCK
[[ -z "$(unlisted "$TMP/control.yml" "$TMP/tests")" && -z "$(dangling "$TMP/control.yml" "$TMP/tests")" ]] \
  && pass "valid mixed-language membership control" || fail "valid membership control rejected"
loop_parses "$TMP/control.yml" && pass "valid block syntax control" || fail "valid syntax control rejected"
runner_works "$TMP/control.yml" && pass "valid dispatch and failure control" || fail "valid dispatch control rejected"

sed '/\.\/scripts\/tests\/test-beta.py/d' "$TMP/control.yml" > "$TMP/unlisted.yml"
[[ "$(unlisted "$TMP/unlisted.yml" "$TMP/tests")" == test-beta.py ]] \
  && pass "unlisted Python suite rejected" || fail "unlisted Python mutation did not bite"
sed 's/test-beta.py/test-absent.py/' "$TMP/control.yml" > "$TMP/absent.yml"
[[ "$(dangling "$TMP/absent.yml" "$TMP/tests")" == test-absent.py ]] \
  && pass "absent Python suite rejected" || fail "absent Python mutation did not bite"
cp "$TMP/unlisted.yml" "$TMP/comment.yml"
printf '# ./scripts/tests/test-beta.py\n' >> "$TMP/comment.yml"
[[ "$(unlisted "$TMP/comment.yml" "$TMP/tests")" == test-beta.py ]] \
  && pass "comment-only suite cannot satisfy membership" || fail "comment-only mutation did not bite"
sed 's/test-alpha.sh \\/test-alpha.sh/' "$TMP/control.yml" > "$TMP/malformed.yml"
loop_parses "$TMP/malformed.yml" && fail "missing continuation mutation did not bite" || pass "missing continuation rejected"
write_workflow "$TMP/no-loop.yml" <<'BLOCK'
set -euo pipefail
true
BLOCK
loop_parses "$TMP/no-loop.yml" && fail "missing loop mutation did not bite" || pass "missing loop rejected"

sed 's/interpreter=python3/interpreter=bash/' "$TMP/control.yml" > "$TMP/wrong-interpreter.yml"
runner_works "$TMP/wrong-interpreter.yml" && fail "wrong Python interpreter mutation did not bite" || pass "wrong Python interpreter rejected"
sed 's/interpreter=python3/interpreter=true/' "$TMP/control.yml" > "$TMP/skipped.yml"
runner_works "$TMP/skipped.yml" && fail "skipped Python mutation did not bite" || pass "skipped Python execution rejected"
sed 's/fail=$((fail + 1))/:/g' "$TMP/control.yml" > "$TMP/swallowed.yml"
runner_works "$TMP/swallowed.yml" && fail "swallowed failure mutation did not bite" || pass "swallowed failures rejected"
sed '/if \[\[ "\$fail" -gt 0 \]\]; then/,$d' "$TMP/control.yml" > "$TMP/no-gate.yml"
runner_works "$TMP/no-gate.yml" && fail "missing aggregate gate mutation did not bite" || pass "missing aggregate gate rejected"
sed 's/if \[\[ "\$fail" -gt 0 \]\]; then/if true; then/' "$TMP/control.yml" > "$TMP/always-fail.yml"
runner_works "$TMP/always-fail.yml" && fail "unconditional failure mutation did not bite" || pass "unconditional failure rejected by valid control"

echo "ci-test-list-coverage: $((checks - fails))/$checks checks passed"
[[ "$fails" -eq 0 ]] || exit 1
