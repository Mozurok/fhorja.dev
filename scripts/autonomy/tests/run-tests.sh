#!/usr/bin/env bash
# run-tests.sh -- tests for the Fhorja autonomy helpers (ADR-0044, Slice 2).
# Governor checks use $AUTONOMY_NOW_EPOCH; background tests use bounded mock processes.
# Run: bash scripts/autonomy/tests/run-tests.sh

set -uo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLASSIFY="$DIR/classify-slice.sh"
GOV="$DIR/governor.sh"
STOP="$DIR/stop-check.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0; fail=0
expect_code() { # <desc> <expected-code> ; reads actual from $?
  local desc="$1" want="$2" got="$3"
  if [[ "$got" == "$want" ]]; then pass=$((pass+1)); else fail=$((fail+1)); echo "FAIL: $desc (want exit $want, got $got)"; fi
}
expect_contains() { # <desc> <needle> <output>
  local desc="$1" needle="$2" hay="$3"
  case "$hay" in
    *"$needle"*) pass=$((pass+1)) ;;
    *) fail=$((fail+1)); echo "FAIL: $desc (output is missing: $needle)" ;;
  esac
}
expect_absent() { # <desc> <needle> <output>
  local desc="$1" needle="$2" hay="$3"
  case "$hay" in
    *"$needle"*) fail=$((fail+1)); echo "FAIL: $desc (output unexpectedly contains: $needle)" ;;
    *) pass=$((pass+1)) ;;
  esac
}

# --- classify-slice ---
bash "$CLASSIFY" src/app/button.tsx src/lib/util.ts >/dev/null 2>&1; expect_code "plain source -> auto" 0 $?
bash "$CLASSIFY" db/migrations/0007_add_col.sql >/dev/null 2>&1; expect_code "migration -> escalate" 10 $?
bash "$CLASSIFY" src/app/button.test.tsx >/dev/null 2>&1; expect_code "test file -> escalate (D12)" 10 $?
bash "$CLASSIFY" evals/scenarios/56-foo.md >/dev/null 2>&1; expect_code "eval scenario -> escalate (D12)" 10 $?
bash "$CLASSIFY" src/auth/session.ts >/dev/null 2>&1; expect_code "auth path -> escalate (D6)" 10 $?
bash "$CLASSIFY" >/dev/null 2>&1; expect_code "empty set -> escalate (default-deny)" 10 $?
# mixed set with one boundary file must escalate (false-negative direction)
bash "$CLASSIFY" src/ok.ts api/orders.ts >/dev/null 2>&1; expect_code "mixed w/ boundary -> escalate" 10 $?
# malformed: several paths joined into ONE argument must escalate (POC finding 2026-06-16)
bash "$CLASSIFY" "db/schema.sql src/db.js" >/dev/null 2>&1; expect_code "joined-arg hiding boundary -> escalate" 10 $?
bash "$CLASSIFY" "src/a.ts src/b.ts" >/dev/null 2>&1; expect_code "joined-arg (whitespace) -> escalate (malformed)" 10 $?

# empty ARGUMENT must escalate, not just an empty argument LIST (found 2026-08-17 by
# running the helper for real). The stdin path filtered empty lines; the argv path did
# not, so `classify-slice.sh "$FILES"` with FILES unset counted "" as one safe file and
# returned auto. That is the false-auto this script's header calls the dangerous failure,
# reached by exactly the caller it warns about: an LLM expanding an empty variable.
bash "$CLASSIFY" "" >/dev/null 2>&1; expect_code "empty argument -> escalate" 10 $?
bash "$CLASSIFY" "src/a.ts" "" >/dev/null 2>&1; expect_code "empty argument among valid ones -> escalate" 10 $?

# --- runs-feed: run_id is a FILENAME, so it must be validated (found 2026-08-17) ---
# Before the guard, `end "../../x"` resolved outside .wos/runs/ and DELETED the file
# there, and `start` wrote outside the same way. The documented caller is an LLM, and
# under D-11 a run_id can come from third-party text, so this is an injection surface.
FEED="$DIR/runs-feed.sh"
VICTIM="$TMP/victim.json"; echo x > "$VICTIM"
# RUNS_DIR is derived the same way runs-feed.sh derives it ($DIR/../..), NOT from the
# caller's cwd: computing it from os.getcwd() made this test pass for the wrong reason
# when the suite ran from anywhere but the repo root, which is the fail-open probe this
# suite exists to prevent.
FEED_RUNS_DIR="$(cd "$DIR/../.." && pwd)/.wos/runs"
REL="$(python3 -c "import os,sys;print(os.path.relpath(sys.argv[1][:-5], sys.argv[2]))" "$VICTIM" "$FEED_RUNS_DIR")"
bash "$FEED" end "$REL" >/dev/null 2>&1; expect_code "end with traversal run_id -> usage error" 2 $?
if [[ -f "$VICTIM" ]]; then victim_status=0; else victim_status=1; fi
expect_code "end with traversal run_id did NOT delete the target" 0 "$victim_status"
bash "$FEED" start "../escape" t s >/dev/null 2>&1; expect_code "start with traversal run_id -> usage error" 2 $?
bash "$FEED" start "--run-id" t s >/dev/null 2>&1; expect_code "start with flag-shaped run_id -> usage error" 2 $?
bash "$FEED" start "ok-123" t s >/dev/null 2>&1; expect_code "start with a safe run_id still works" 0 $?
bash "$FEED" end "ok-123" >/dev/null 2>&1; expect_code "end with a safe run_id still works" 0 $?

# --- launch-background-run: refusal paths and the run_id it derives ---
# The refusal paths run the real launcher. An unset CLI prints guidance before
# workspace provisioning, so these cases leave no background execution.
LAUNCH="$DIR/launch-background-run.sh"
mkdir -p "$TMP/2026-08-18_a-normal-name" "$TMP/hostile name (v2)"
( unset WOS_AGENT_CMD; bash "$LAUNCH" >/dev/null 2>&1 ); expect_code "launcher with no argument -> usage error" 2 $?
( unset WOS_AGENT_CMD; bash "$LAUNCH" "$TMP/does-not-exist" >/dev/null 2>&1 ); expect_code "launcher with a missing task folder -> usage error" 2 $?
( unset WOS_AGENT_CMD; bash "$LAUNCH" "$TMP/2026-08-18_a-normal-name" >/dev/null 2>&1 ); expect_code "launcher without WOS_AGENT_CMD -> manual instructions, exit 0" 0 $?

# Feed acceptance of sanitized identifiers. The process suite below additionally
# exercises the launcher's actual identifier generation with an unusual task name.
HOSTILE_SLUG="$(printf '%s' "hostile name (v2)" | tr -c 'A-Za-z0-9._-' '-')"
bash "$FEED" start "bg-$HOSTILE_SLUG-1" t s >/dev/null 2>&1; expect_code "derived run_id from a hostile folder name is accepted" 0 $?
bash "$FEED" end "bg-$HOSTILE_SLUG-1" >/dev/null 2>&1

# --- classify-slice: decision annotation (D-4) ---
# The annotation is REPORTING ONLY. Every case below asserts the exit code is
# still 10 (or still 0 for the auto path), so a downgrade would fail the suite.
DEC="$TMP/DECISIONS.md"
cat > "$DEC" <<'EOF'
# DECISIONS (test fixture)

## Locked decisions

### D-4: The classifier annotates, it does not downgrade
The boundary this covers is src/auth/session.ts, decided before the run started.
Locked: 2026-07-27, user LOCK signal "aprovado".

### D-9: A proposed decision, deliberately not locked
Covers db/migrations/0007_add_col.sql and carries no lock line on purpose.
EOF

out="$(bash "$CLASSIFY" --decisions "$DEC" src/auth/session.ts 2>&1)"; expect_code "covered boundary -> STILL escalate" 10 $?
expect_contains "covered boundary names the locked decision" "covered by D-4 (locked)" "$out"
expect_contains "covered boundary keeps the escalate verdict" "VERDICT: escalate" "$out"

out="$(bash "$CLASSIFY" --decisions "$DEC" prisma/schema.prisma 2>&1)"; expect_code "uncovered boundary -> STILL escalate" 10 $?
expect_absent "uncovered boundary carries no annotation" "covered by" "$out"

out="$(bash "$CLASSIFY" --decisions "$DEC" db/migrations/0007_add_col.sql 2>&1)"; expect_code "boundary covered by an UNLOCKED decision -> STILL escalate" 10 $?
expect_absent "an unlocked decision is not an annotation" "covered by" "$out"

out="$(bash "$CLASSIFY" src/auth/session.ts 2>&1)"; expect_code "no --decisions -> unchanged escalate" 10 $?
expect_absent "no --decisions means no annotation" "covered by" "$out"

out="$(bash "$CLASSIFY" --decisions "$TMP/no-such-file.md" src/auth/session.ts 2>&1)"; expect_code "absent decisions file -> STILL escalate" 10 $?
expect_absent "absent decisions file emits no annotation" "covered by" "$out"

bash "$CLASSIFY" --decisions "$TMP" src/auth/session.ts >/dev/null 2>&1; expect_code "unreadable decisions path (a directory) -> STILL escalate" 10 $?
bash "$CLASSIFY" --decisions >/dev/null 2>&1; expect_code "--decisions with no value and no files -> escalate" 10 $?

out="$(bash "$CLASSIFY" --decisions "$DEC" src/app/button.tsx src/lib/util.ts 2>&1)"; expect_code "--decisions does not disturb the auto path" 0 $?
expect_absent "the auto path carries no annotation" "covered by" "$out"

out="$(bash "$CLASSIFY" --decisions "$DEC" src/app/button.test.tsx 2>&1)"; expect_code "test path with decisions -> STILL escalate (D12)" 10 $?
expect_absent "a test path is never annotated" "covered by" "$out"

# --- classify-slice: the reference must sit at a PATH BOUNDARY (wave-1 gate fix) ---
# A decision whose only "auth" lives inside "agent-authored" must NOT annotate a
# path under auth/, and "oauth/" must not match the "auth" directory. These are
# annotation-only defects (the verdict never moved), which is exactly why they
# need their own assertions: a verdict test cannot catch a wrong label.
BND="$TMP/DECISIONS-boundary.md"
cat > "$BND" <<'EOF'
# DECISIONS (boundary fixture)

## Locked decisions

### D-20: Nothing to do with auth paths
The run SHALL never record an agent-authored decision as user input.
Locked: 2026-07-27, user LOCK signal "aprovado".

### D-21: An unrelated provider directory
Covers oauth/schema.sql only.
Locked: 2026-07-27, user LOCK signal "aprovado".

### D-22: A real directory-level coverage
Everything under auth/ is decided.
Locked: 2026-07-27, user LOCK signal "aprovado".
EOF

out="$(bash "$CLASSIFY" --decisions "$BND" auth/session.ts 2>&1)"; expect_code "boundary-fixture path -> STILL escalate" 10 $?
expect_absent "'agent-authored' does not annotate a path under auth/" "covered by D-20" "$out"
expect_absent "'oauth/' does not annotate the auth directory" "covered by D-21" "$out"
expect_contains "a real 'auth/' reference still annotates" "covered by D-22 (locked)" "$out"

# oauth/schema.sql is a boundary path via the .sql extension, NOT via the auth
# directory rule (BOUNDARY_RE requires auth at a path boundary, and in "oauth/"
# it is preceded by "o"). That is what makes it the right probe here.
out="$(bash "$CLASSIFY" --decisions "$BND" oauth/schema.sql 2>&1)"; expect_code "oauth boundary path -> STILL escalate" 10 $?
expect_contains "an exact path reference annotates its own decision" "covered by D-21 (locked)" "$out"
expect_absent "the auth/ decision does not reach an oauth/ path" "covered by D-22" "$out"

# --- stop-check ---
bash "$STOP" "$TMP/nope.stop" >/dev/null 2>&1; expect_code "absent STOP -> continue" 0 $?
touch "$TMP/run.stop"
bash "$STOP" "$TMP/run.stop" >/dev/null 2>&1; expect_code "present STOP -> halt" 30 $?

# --- governor: max-iter ---
st="$TMP/gov1"; rm -f "$st"
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 2 --timeout-sec 0 --command a >/dev/null 2>&1; expect_code "gov iter1 continue" 0 $?
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 2 --timeout-sec 0 --command b >/dev/null 2>&1; expect_code "gov iter2 continue" 0 $?
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 2 --timeout-sec 0 --command c >/dev/null 2>&1; expect_code "gov iter3 halt (max-iter)" 20 $?

# --- governor: timeout ---
st="$TMP/gov2"; rm -f "$st"
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 99 --timeout-sec 60 --command x >/dev/null 2>&1; expect_code "gov within timeout" 0 $?
AUTONOMY_NOW_EPOCH=1100 bash "$GOV" "$st" --max-iter 99 --timeout-sec 60 --command y >/dev/null 2>&1; expect_code "gov over timeout halt" 20 $?

# --- governor: identical-command loop ---
st="$TMP/gov3"; rm -f "$st"
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 99 --timeout-sec 0 --command "same" >/dev/null 2>&1; expect_code "loop 1 continue" 0 $?
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 99 --timeout-sec 0 --command "same" >/dev/null 2>&1; expect_code "loop 2 continue" 0 $?
AUTONOMY_NOW_EPOCH=1000 bash "$GOV" "$st" --max-iter 99 --timeout-sec 0 --command "same" >/dev/null 2>&1; expect_code "loop 3 halt (identical-command)" 20 $?

echo "----"
echo "autonomy helper tests: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]] || exit 1
python3 "$DIR/tests/test-background-run.py"
