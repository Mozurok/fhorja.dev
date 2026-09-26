#!/usr/bin/env bash
# test-run-spine-evals.sh: the runner refuses loudly and never fabricates a verdict.
#
# Every check here is about a refusal, because that is where an eval runner does
# damage. A runner that emits PASS when the model failed, or scores a rubric it
# could not read, produces a green board that means nothing, and nobody looks
# behind a green board.
#
# Check 6 is the one that keeps this honest across the whole suite: no run, in any
# mode, may leave a byte in evals/scenarios/. The scenarios are the input; a
# runner that edits them is grading its own homework.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RUNNER="${REPO_ROOT}/evals/scripts/run-spine-evals.py"

# The run directories that already existed when this suite started. Every cleanup below
# removes only what this suite created, never these. A blunt `rm -rf evals/runs` used to
# sit further down and it deleted an operator's real artifacts on 2026-09-01: the suite ran
# after an eight-run battery and the prompts, responses and verdicts were gone before they
# could be read a second time. The directory is gitignored, so nothing noticed.
# A stand-in for an operator artifact, planted BEFORE the snapshot so it is part of the
# pre-existing set. Check 21 at the end asserts it survived. It has to be created here and
# not next to that check: every cleanup in this suite runs earlier in the file, so a sentinel
# planted late is never exposed to the thing it exists to catch. The first version of this
# check made exactly that mistake and passed against the blunt cleanup it was written for.
SENTINEL="${REPO_ROOT}/evals/runs/00000000T000000Z-suitesentinel"
mkdir -p "$SENTINEL" && printf 'operator artifact\n' > "$SENTINEL/keep.txt"
RUNS_BEFORE_ALL="$(ls "${REPO_ROOT}/evals/runs" 2>/dev/null | sort || true)"

# Since 2026-08-30 the runner refuses --model-cmd on a dirty working tree, so that a graded
# run is reproducible from a commit. This suite exercises the plumbing with a fake model
# while someone may be editing the runner itself, which is exactly the dirty case, so it
# declares the escape. The refusal itself is exercised in checks 17 to 20, which drive the
# module with a stubbed tree state and therefore hold whether or not this repo is clean.
export FHORJA_EVAL_ALLOW_DIRTY_TREE=1
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

SCENARIOS_BEFORE="$(cd "$REPO_ROOT" && git status --porcelain evals/scenarios/)"

# 1. --dry-run exits 0 and prints one block per manifest entry.
out="$(cd "$REPO_ROOT" && python3 "$RUNNER" --dry-run 2>&1)"; rc=$?
blocks="$(printf '%s\n' "$out" | grep -c '^=== ')"
entries="$(python3 -c "
import json
print(len(json.load(open('${REPO_ROOT}/evals/spine-evals.json'))['scenarios']))
")"
if [ "$rc" = "0" ] && [ "$blocks" = "$entries" ]; then
  pass "1. --dry-run exits 0 with one block per manifest entry ($blocks)"
else
  fail "1. --dry-run exits 0 with one block per entry (exit $rc, $blocks blocks, $entries entries)"
fi

# 2. --dry-run reports no unparseable section across the elected scenarios.
if printf '%s\n' "$out" | grep -q 'ERROR: unparseable'; then
  fail "2. --dry-run reports no unparseable section"
else
  pass "2. --dry-run reports no unparseable section"
fi

# 3. No --model-cmd and no --dry-run is a refusal, exit 2.
(cd "$REPO_ROOT" && env -u FHORJA_EVAL_MODEL_CMD python3 "$RUNNER" >/dev/null 2>&1)
rc=$?
[ "$rc" = "2" ] && pass "3. no --model-cmd and no --dry-run exits 2" \
                || fail "3. no --model-cmd and no --dry-run exits 2 (got $rc)"

# 4. A rubric under three criteria is a refusal, exit 3, naming the scenario.
mkdir -p "$TMP/evals/scenarios"
cat > "$TMP/evals/scenarios/99-thin-rubric.md" <<'FIXTURE'
# Scenario 99: thin rubric fixture

## Setup

None.

## Input prompt

```
do the thing
```

## Pass criteria

1. one
2. two

## Failure modes to watch

- nothing
FIXTURE
cat > "$TMP/manifest.json" <<FIXTURE
{"version":1,"scenarios":[{"file":"${TMP}/evals/scenarios/99-thin-rubric.md",
"reason":"fixture","setup":"none","verdict_required":false,"timeout_seconds":5}]}
FIXTURE
err="$(cd "$REPO_ROOT" && python3 - "$RUNNER" "$TMP/manifest.json" 2>&1 >/dev/null <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("r", sys.argv[1])
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
r.MANIFEST = sys.argv[2]
sys.exit(r.main(["--model-cmd", "cat"]))
PYEOF
)"; rc=$?
if [ "$rc" = "3" ] && printf '%s\n' "$err" | grep -q '99-thin-rubric.md'; then
  pass "4. a 2-criterion rubric exits 3, naming the scenario"
else
  fail "4. a 2-criterion rubric exits 3, naming the scenario (exit $rc: $err)"
fi

# 5. A fake model command produces a parseable verdict.json with the required keys.
out="$(cd "$REPO_ROOT" && python3 "$RUNNER" --scenario 137 --model-cmd cat --model-label fake 2>&1)"
rc=$?
run_dir="$(printf '%s\n' "$out" | sed -n 's|^artifacts: \(evals/runs/[^ ]*\)/$|\1|p')"
if [ "$rc" = "0" ] && [ -n "$run_dir" ] && \
   python3 -c "
import json, sys
d = json.load(open('${REPO_ROOT}/' + '$run_dir' + '/137/verdict.json'))
sys.exit(0 if all(k in d for k in ('scenario', 'overall', 'criteria')) else 1)
" 2>/dev/null; then
  pass "5. a fake model command writes a verdict.json with scenario, overall, criteria"
else
  fail "5. a fake model command writes a valid verdict.json (exit $rc, dir '$run_dir')"
fi
[ -n "$run_dir" ] && rm -rf "${REPO_ROOT:?}/${run_dir}"

# 6. A setup-shell scenario is skipped without --grade-without-setup, and skipping
#    one does not take the others down. The flag was called --allow-setup-shell until
#    2026-08-30, a name that promised to run the setup script; the runner has never run
#    one, and the flag only removes the skip. Driven by a fixture manifest since
#    2026-09-22, when scenario 125 moved to a checked-in fixture script and stopped being
#    the repository's example of a shell setup.
mkdir -p "$TMP/sh/evals/scenarios"
cat > "$TMP/sh/evals/scenarios/91-shell.md" <<'FIX'
# Scenario 91: shell setup fixture

## Setup

```bash
touch /should/never/run
```

## Input prompt

```
x
```

## Pass criteria

1. one
2. two
3. three
FIX
cat > "$TMP/sh/manifest.json" <<FIX
{"version":1,"scenarios":[{"file":"$TMP/sh/evals/scenarios/91-shell.md",
"reason":"fixture","setup":"shell","verdict_required":false,"timeout_seconds":10}]}
FIX
out="$(cd "$REPO_ROOT" && python3 - "$RUNNER" "$TMP/sh/manifest.json" 2>&1 <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("r", sys.argv[1])
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
r.MANIFEST = sys.argv[2]
sys.exit(r.main(["--dry-run"]))
PYEOF
)"; rc=$?
if [ "$rc" = "0" ] && printf '%s\n' "$out" | grep -q 'SKIPPED (setup is a shell script and this runner never runs one)'; then
  pass "6. setup shell is skipped without --grade-without-setup"
else
  fail "6. setup shell is skipped without --grade-without-setup (exit $rc)"
fi

# 7. Nothing above wrote a byte into evals/scenarios/.
SCENARIOS_AFTER="$(cd "$REPO_ROOT" && git status --porcelain evals/scenarios/)"
if [ "$SCENARIOS_BEFORE" = "$SCENARIOS_AFTER" ]; then
  pass "7. no run touched evals/scenarios/"
else
  fail "7. no run touched evals/scenarios/ (before '$SCENARIOS_BEFORE' after '$SCENARIOS_AFTER')"
fi

# 8. The overall verdict is computed, not read: one FAIL beats every PASS.
if python3 - "$RUNNER" <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("r", sys.argv[1])
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
raw = ("- Criterion 1: PASS -- fine\n- Criterion 2: FAIL -- broken\n"
       "- Overall: PASS -- the grader claims everything is fine\n")
scored = r.parse_grader(raw, 3)
ok = (r.overall_of(scored) == "FAIL"
      and scored[2]["result"] == "UNCERTAIN")
sys.exit(0 if ok else 1)
PYEOF
then
  pass "8. overall is computed here: a FAIL wins and an unanswered criterion is UNCERTAIN"
else
  fail "8. overall is computed here, not read from the grader"
fi

# --- --record: the durable line in the scenario's ## History ---

# 9. --record without --model-label is a refusal, exit 2. The runner cannot tell
#    which model sits behind a shell command.
(cd "$REPO_ROOT" && python3 "$RUNNER" --record --model-cmd cat >/dev/null 2>&1)
rc=$?
[ "$rc" = "2" ] && pass "9. --record without --model-label exits 2" \
                || fail "9. --record without --model-label exits 2 (got $rc)"

# Fixture without a History section, plus a manifest pointing at it.
mkdir -p "$TMP/rec/evals/scenarios"
FIXTURE="$TMP/rec/evals/scenarios/90-fixture-no-history.md"
cat > "$FIXTURE" <<'FIX'
# Scenario 90: fixture without a History section

## Setup

None.

## Input prompt

```
do the thing
```

## Pass criteria

1. one
2. two
3. three

## Failure modes to watch

- nothing
FIX
cat > "$TMP/rec/manifest.json" <<FIX
{"version":1,"scenarios":[{"file":"${FIXTURE}",
"reason":"fixture","setup":"none","verdict_required":false,"timeout_seconds":10}]}
FIX

record_run() {  # record_run <model-cmd>; runs the fixture manifest with --record
  (cd "$REPO_ROOT" && python3 - "$RUNNER" "$TMP/rec/manifest.json" "$1" >/dev/null 2>&1 <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("r", sys.argv[1])
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
r.MANIFEST = sys.argv[2]
sys.exit(r.main(["--record", "--model-cmd", sys.argv[3],
                 "--model-label", "fake", "--grader-label", "fake"]))
PYEOF
  )
}

BEFORE_BODY="$(cat "$FIXTURE")"
record_run cat; rc=$?

# 10. The line matches the fixed shape a later check reads back.
FORMAT='^- [0-9]{4}-[0-9]{2}-[0-9]{2}: run [^ ]+ \| model=[^ ]+ grader=[^ ]+ \| (PASS|FAIL|UNCERTAIN) [0-9]+/[0-9]+ \| failed: .+ \| artifacts: evals/runs/[^ ]+/$'
lines="$(grep -cE "$FORMAT" "$FIXTURE")"
if [ "$rc" = "0" ] && [ "$lines" = "1" ]; then
  pass "10. --record appends one line in the fixed shape"
else
  fail "10. --record appends one line in the fixed shape (exit $rc, $lines matching)"
fi

# 11. A scenario with no ## History gains the section exactly once.
sections="$(grep -c '^## History$' "$FIXTURE")"
[ "$sections" = "1" ] && pass "11. a scenario without ## History gains it exactly once" \
                      || fail "11. a scenario without ## History gains it exactly once (got $sections)"

# 12. Appending is append-only: everything that was there before is byte-identical
#     and still the prefix of the file. A writer that reorders history rewrites
#     evidence.
if [ "$(head -c ${#BEFORE_BODY} "$FIXTURE")" = "$BEFORE_BODY" ]; then
  pass "12. the pre-existing body is untouched and still the file prefix"
else
  fail "12. the pre-existing body is untouched and still the file prefix"
fi

# 13. Two runs leave two lines, and the first one survives verbatim.
first_line="$(grep -E "$FORMAT" "$FIXTURE" | head -1)"
record_run cat
lines="$(grep -cE "$FORMAT" "$FIXTURE")"
# The line starts with "- ", so -- is load-bearing: grep would read it as a flag.
if [ "$lines" = "2" ] && grep -qF -- "$first_line" "$FIXTURE"; then
  pass "13. a second --record adds a second line and keeps the first verbatim"
else
  fail "13. a second --record adds a second line and keeps the first (got $lines)"
fi

# 14. A run that ERRORed writes nothing. `false` exits 1 with empty stdout, which
#     is exactly the infrastructure failure that must not poison the history.
before="$(grep -cE "$FORMAT" "$FIXTURE")"
record_run false
after="$(grep -cE "$FORMAT" "$FIXTURE")"
[ "$before" = "$after" ] && pass "14. an ERROR run records no history line" \
                         || fail "14. an ERROR run records no history line ($before -> $after)"

# 15. A SKIPPED scenario records nothing either.
sed -i.bak 's/"setup":"none"/"setup":"shell"/' "$TMP/rec/manifest.json"
before="$(grep -cE "$FORMAT" "$FIXTURE")"
record_run cat
after="$(grep -cE "$FORMAT" "$FIXTURE")"
[ "$before" = "$after" ] && pass "15. a SKIPPED scenario records no history line" \
                         || fail "15. a SKIPPED scenario records no history line ($before -> $after)"

# 16. Still nothing written into the repository's own scenarios.
SCENARIOS_AFTER="$(cd "$REPO_ROOT" && git status --porcelain evals/scenarios/)"
if [ "$SCENARIOS_BEFORE" = "$SCENARIOS_AFTER" ]; then
  pass "16. no --record run touched evals/scenarios/ in this repository"
else
  fail "16. no --record run touched evals/scenarios/ (after '$SCENARIOS_AFTER')"
fi

# Remove only what this suite made, in the same shape check 17..20 already uses below.
RUNS_AFTER_ALL="$(ls "${REPO_ROOT}/evals/runs" 2>/dev/null | sort || true)"
for d in ${RUNS_AFTER_ALL}; do
  printf '%s\n' "${RUNS_BEFORE_ALL}" | grep -qxF "$d" || rm -rf "${REPO_ROOT:?}/evals/runs/${d:?}"
done

# 17..20: the clean-tree refusal and the per-scenario write check. Both are driven with a
# stubbed working_tree_state so the assertions hold whether or not this repository happens
# to be clean when the suite runs, and so nothing here ever dirties the real tree.
tree_case() {  # tree_case <states-python-list> <argv-python-list> <env-clean:0|1>
  python3 - "$REPO_ROOT" "$1" "$2" "$3" <<'PYEOF'
import importlib.util, io, contextlib, sys, os, shutil, ast
root, states_src, argv_src, drop_env = sys.argv[1:5]
os.chdir(root)
if drop_env == "1":
    os.environ.pop("FHORJA_EVAL_ALLOW_DIRTY_TREE", None)
spec = importlib.util.spec_from_file_location("r", "evals/scripts/run-spine-evals.py")
m = importlib.util.module_from_spec(spec); sys.modules["r"] = m; spec.loader.exec_module(m)
states = ast.literal_eval(states_src)
before = set(os.listdir("evals/runs")) if os.path.isdir("evals/runs") else set()
it = iter(states)
m.working_tree_state = lambda: next(it, states[-1])
out, err = io.StringIO(), io.StringIO()
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
    rc = m.main(ast.literal_eval(argv_src))
after = set(os.listdir("evals/runs")) if os.path.isdir("evals/runs") else set()
for d in after - before:
    shutil.rmtree(os.path.join("evals/runs", d))
print(f"rc={rc}")
print(out.getvalue())
print(err.getvalue())
PYEOF
}

RES="$(tree_case "[{' M some/file'}]" "['--scenario','01','--model-cmd','cat']" 1)"
if printf '%s' "$RES" | grep -q '^rc=5' && printf '%s' "$RES" | grep -q 'would grade a model'; then
  pass "17. a dirty tree refuses --model-cmd with exit 5"
else
  fail "17. a dirty tree refuses --model-cmd with exit 5 ($(printf '%s' "$RES" | head -1))"
fi

RES="$(tree_case "[{' M some/file'}, {' M some/file'}]" "['--scenario','01','--model-cmd','cat']" 0)"
if ! printf '%s' "$RES" | grep -q '^rc=5' && printf '%s' "$RES" | grep -q 'This run is not reproducible'; then
  pass "18. the escape starts anyway and says so on stdout"
else
  fail "18. the escape starts anyway and says so on stdout ($(printf '%s' "$RES" | head -1))"
fi

RES="$(tree_case "[set(), {' M evals/scenarios/01-bootstrap-and-init.md'}]" "['--scenario','01','--model-cmd','cat']" 0)"
if printf '%s' "$RES" | grep -q '^rc=4' && printf '%s' "$RES" | grep -q 'wrote into the working tree'; then
  pass "19. a scenario that writes into the tree is an ERROR, not a verdict"
else
  fail "19. a scenario that writes into the tree is an ERROR, not a verdict ($(printf '%s' "$RES" | head -1))"
fi

RES="$(tree_case "[None]" "['--scenario','01','--model-cmd','cat']" 0)"
if printf '%s' "$RES" | grep -q '^rc=5' && printf '%s' "$RES" | grep -q 'cannot read the working tree state'; then
  pass "20. git that cannot answer refuses rather than assuming clean"
else
  fail "20. git that cannot answer refuses rather than assuming clean ($(printf '%s' "$RES" | head -1))"
fi

# 20b. --record on a clean tree is not blamed on the scenario. The history line is the
# runner's own write into the tree; checked after it, every recorded run on a clean tree
# became an ERROR (2026-09-23, scenario 141). record_history is stubbed to flip the tree
# state, so nothing here touches a real scenario file.
RES="$(python3 - "$REPO_ROOT" <<'PYEOF'
import importlib.util, io, contextlib, sys, os, shutil
os.chdir(sys.argv[1])
spec = importlib.util.spec_from_file_location("r", "evals/scripts/run-spine-evals.py")
m = importlib.util.module_from_spec(spec); sys.modules["r"] = m; spec.loader.exec_module(m)
state = {"tree": set(), "records": 0}
m.working_tree_state = lambda: set(state["tree"])
def fake_record(path, line):
    state["records"] += 1
    state["tree"] = {" M " + os.path.relpath(path)}
m.record_history = fake_record
before = set(os.listdir("evals/runs")) if os.path.isdir("evals/runs") else set()
out, err = io.StringIO(), io.StringIO()
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
    rc = m.main(["--scenario", "01", "--model-cmd", "cat", "--record", "--model-label", "fake"])
after = set(os.listdir("evals/runs")) if os.path.isdir("evals/runs") else set()
for d in after - before:
    shutil.rmtree(os.path.join("evals/runs", d))
print(f"rc={rc} records={state['records']}")
print(err.getvalue())
PYEOF
)"
if printf '%s' "$RES" | grep -q 'records=1' && ! printf '%s' "$RES" | grep -q 'wrote into the working tree'; then
  pass "20b. --record on a clean tree records once and is not reported as a scenario write"
else
  fail "20b. --record on a clean tree records once and is not reported as a scenario write ($(printf '%s' "$RES" | head -1))"
fi

# 21. The operator artifact planted at the top is still here. Every cleanup in this suite
# ran between then and now.
if [ -f "$SENTINEL/keep.txt" ]; then
  pass "21. a pre-existing run directory survives the suite"
else
  fail "21. a pre-existing run directory survives the suite (the sentinel was deleted)"
fi
rm -rf "$SENTINEL"

# 22. A non-PASS verdict points at the response, not just at the artifacts directory. The verdict's
# notes are the grader's reading; two wrong conclusions on 2026-09-01 came from treating them as the
# model's words while the response sat unread on disk.
RES="$(python3 - "$REPO_ROOT" <<'PYEOF'
import importlib.util, io, contextlib, sys, os
root = sys.argv[1]
os.chdir(root)
spec = importlib.util.spec_from_file_location("r", "evals/scripts/run-spine-evals.py")
m = importlib.util.module_from_spec(spec); sys.modules["r"] = m; spec.loader.exec_module(m)
src = open("evals/scripts/run-spine-evals.py", encoding="utf-8").read()
ok = ("criteria not PASS" in src
      and "response-turn-*.txt" in src
      and "grader's reading" in src
      and "if unresolved:" in src)
print("PASS" if ok else "the non-PASS pointer is gone from the runner")
PYEOF
)"
if printf '%s' "$RES" | grep -q '^PASS'; then
  pass "22. a non-PASS verdict points the reader at the response file"
else
  fail "22. a non-PASS verdict points the reader at the response file ($RES)"
fi

# 23..27: fixture scenarios (B29, 2026-09-22). A scenario may name a checked-in fixture
# script; the runner builds it in a directory it creates, substitutes {fixture} in the
# prompts, probes the disk after each turn and hands that to the grader. The point is the
# grader: scenario 137 passed a run that reported a ledger write no file showed.
mkdir -p "$TMP/fx/evals/scenarios"
cat > "$TMP/fx/fixture.sh" <<'FIX'
#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  build) [ -z "$(ls -A "$2")" ] || exit 2; echo seed > "$2/seed.txt"; echo "$2" >> "$(dirname "$0")/built.log" ;;
  probe) echo "  PROBE-OK $(ls "$2" | tr '\n' ' ')" ;;
esac
FIX
cat > "$TMP/fx/badfixture.sh" <<'FIX'
#!/usr/bin/env bash
echo "cannot build" >&2; exit 3
FIX
cat > "$TMP/fx/evals/scenarios/92-fixture.md" <<'FIX'
# Scenario 92: fixture

## Setup

None.

## Input prompt (turn 1)

```
FIX={fixture} turn-one-marker
```

## Input prompt (turn 2)

```
FIX={fixture} turn-two
```

## Pass criteria

1. one
2. two
3. three
FIX
# A model that writes one file into the fixture it was given, then answers.
cat > "$TMP/fx/model.sh" <<'FIX'
#!/usr/bin/env bash
p="$(cat)"; d="$(printf '%s' "$p" | grep -o 'FIX=[^ ]*' | tail -1 | cut -d= -f2)"
echo made > "$d/made.txt"; echo "answer for $d"
FIX
chmod +x "$TMP/fx/"*.sh
fx_manifest() {  # fx_manifest <fixture script> <turns>
  cat > "$TMP/fx/manifest.json" <<FIX
{"version":1,"scenarios":[{"file":"$TMP/fx/evals/scenarios/92-fixture.md","reason":"fixture",
"setup":"fixture","fixture":"$1","turns":"$2","verdict_required":false,"timeout_seconds":20}]}
FIX
}
fx_run() {
  (cd "$REPO_ROOT" && python3 - "$RUNNER" "$TMP/fx/manifest.json" "$TMP/fx/model.sh" 2>&1 <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("r", sys.argv[1])
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
r.MANIFEST = sys.argv[2]
sys.exit(r.main(["--model-cmd", sys.argv[3], "--grader-cmd", "cat"]))
PYEOF
  )
}
: > "$TMP/fx/built.log"
fx_manifest "$TMP/fx/fixture.sh" chained
out="$(fx_run)"; rc=$?
dir="$(printf '%s\n' "$out" | sed -n 's|^artifacts: \(evals/runs/[^ ]*\)/$|\1|p')"
S92="$REPO_ROOT/$dir/92"
if [ -n "$dir" ] && grep -q "added    made.txt" "$S92/disk-after-turn-1.txt" 2>/dev/null \
   && grep -q "PROBE-OK" "$S92/disk-after-turn-1.txt" \
   && ! grep -q '{fixture}' "$S92/prompt-turn-1.txt"; then
  pass "23. a fixture is built, substituted into the prompt, and diffed and probed after the turn"
else
  fail "23. fixture build, substitution, diff and probe (exit $rc, dir '$dir')"
fi
if grep -q "measured by the runner" "$S92/grader-raw.txt" 2>/dev/null \
   && grep -q "added    made.txt" "$S92/grader-raw.txt"; then
  pass "24. the grader receives the disk state as ground truth"
else
  fail "24. the grader receives the disk state as ground truth"
fi
builds="$(wc -l < "$TMP/fx/built.log" | tr -d ' ')"; first="$(head -1 "$TMP/fx/built.log")"
if [ "$builds" = "1" ] && [ -n "$first" ] && [ ! -e "$first" ] \
   && grep -q "turn-one-marker" "$S92/prompt-turn-2.txt"; then
  pass "25. chained turns share one fixture, carry the history, and the fixture is removed after"
else
  fail "25. chained turns share one fixture and it is removed after (builds $builds, dir '$first')"
fi
[ -n "$dir" ] && rm -rf "${REPO_ROOT:?}/${dir}"

: > "$TMP/fx/built.log"
fx_manifest "$TMP/fx/fixture.sh" independent
out="$(fx_run)"; rc=$?
dir="$(printf '%s\n' "$out" | sed -n 's|^artifacts: \(evals/runs/[^ ]*\)/$|\1|p')"
S92="$REPO_ROOT/$dir/92"
builds="$(wc -l < "$TMP/fx/built.log" | tr -d ' ')"
if [ "$builds" = "2" ] && [ -n "$dir" ] && ! grep -q "turn-one-marker" "$S92/prompt-turn-2.txt" \
   && grep -q "added    made.txt" "$S92/disk-after-turn-2.txt"; then
  pass "26. independent turns get a fresh fixture each and no earlier transcript"
else
  fail "26. independent turns get a fresh fixture each and no earlier transcript (builds $builds)"
fi
[ -n "$dir" ] && rm -rf "${REPO_ROOT:?}/${dir}"

fx_manifest "$TMP/fx/badfixture.sh" chained
out="$(fx_run)"; rc=$?
dir="$(printf '%s\n' "$out" | sed -n 's|^artifacts: \(evals/runs/[^ ]*\)/$|\1|p')"
if [ "$rc" = "4" ] && printf '%s\n' "$out" | grep -q '^ERROR' \
   && [ ! -e "$REPO_ROOT/$dir/92/verdict.json" ]; then
  pass "27. a fixture that fails to build is an ERROR with no verdict"
else
  fail "27. a fixture that fails to build is an ERROR with no verdict (exit $rc)"
fi
[ -n "$dir" ] && rm -rf "${REPO_ROOT:?}/${dir}"

# 28. Every fixture the manifest names builds from an empty directory and refuses a non-empty one.
for fxs in $(python3 -c "
import json
for e in json.load(open('${REPO_ROOT}/evals/spine-evals.json'))['scenarios']:
    if e.get('fixture'): print('${REPO_ROOT}/' + e['fixture'])
"); do
  d="$(mktemp -d)"
  if (cd "$REPO_ROOT" && bash "$fxs" build "$d" >/dev/null 2>&1) \
     && (cd "$REPO_ROOT" && bash "$fxs" probe "$d" >/dev/null 2>&1) \
     && ! (cd "$REPO_ROOT" && bash "$fxs" build "$d" >/dev/null 2>&1); then
    pass "28. $(basename "$fxs") builds, probes, and refuses a non-empty directory"
  else
    fail "28. $(basename "$fxs") builds, probes, and refuses a non-empty directory"
  fi
  rm -rf "$d"
done

# 29. A scenario with no fixture but a declared probe gets a repository probe after each turn,
# and the grader receives it. Scenario 01 writes into the repository itself.
cat > "$TMP/fx/probe.sh" <<'FIX'
#!/usr/bin/env bash
[ "$1" = "probe" ] && echo "  REPO-PROBE-OK $(basename "$2")"
FIX
cat > "$TMP/fx/evals/scenarios/93-probe.md" <<'FIX'
# Scenario 93: probe

## Setup

None.

## Input prompt

```
FIX=/nonexistent answer me
```

## Pass criteria

1. one
2. two
3. three
FIX
cat > "$TMP/fx/manifest.json" <<FIX
{"version":1,"scenarios":[{"file":"$TMP/fx/evals/scenarios/93-probe.md","reason":"fixture",
"setup":"none","probe":"$TMP/fx/probe.sh","verdict_required":false,"timeout_seconds":20}]}
FIX
out="$(cd "$REPO_ROOT" && python3 - "$RUNNER" "$TMP/fx/manifest.json" 2>&1 <<'PYEOF'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("r", sys.argv[1])
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
r.MANIFEST = sys.argv[2]
sys.exit(r.main(["--model-cmd", "echo answered", "--grader-cmd", "cat"]))
PYEOF
)"
dir="$(printf '%s\n' "$out" | sed -n 's|^artifacts: \(evals/runs/[^ ]*\)/$|\1|p')"
if [ -n "$dir" ] && grep -q "REPO-PROBE-OK" "$REPO_ROOT/$dir/93/disk-after-turn-1.txt" 2>/dev/null \
   && grep -q "REPO-PROBE-OK" "$REPO_ROOT/$dir/93/grader-raw.txt"; then
  pass "29. a declared probe reports the repository after the turn, and the grader sees it"
else
  fail "29. a declared probe reports the repository after the turn (dir '$dir')"
fi
[ -n "$dir" ] && rm -rf "${REPO_ROOT:?}/${dir}"

echo ""
echo "test-run-spine-evals: ${checks} check(s), ${fails} failure(s)"
[ "$fails" -eq 0 ]
