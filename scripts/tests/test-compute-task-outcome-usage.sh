#!/usr/bin/env bash
# test-compute-task-outcome-usage.sh: the output_tokens_by_model field (E0, ADR-0236).
#
# Experiment E1 asks whether routing mechanical work to a cheaper model lowers
# the strong model's output per task. Without a per-task, per-model token count
# on the outcome line there is nothing to compare, so E0 adds one. The contract
# is tool-agnostic: the helper reads a usage source through a named adapter, and
# absent, unattributable or uncountable data is recorded as null with a reason,
# never estimated.
#
# The cases worth staring at:
#   3 and 4. One API response is written to a Claude Code transcript as several
#      lines sharing a message id. In a main session they repeat the final usage
#      (measured 2026-09-28: 2 lines, 1 id, 1965 on both), so summing lines
#      double-counts. In a sub-agent transcript they are streaming snapshots and
#      only the line with a stop_reason carries the full count, so the reader
#      takes the largest count per message id and needs that final line.
#   6. The window. A session outlives a task, so only lines between the task's
#      init and close count.
#   13 to 17. Attribution. Two tasks that ran at the same time as sub-agents of
#      one session each got the other's tokens from a reader that filtered by
#      time alone (measured 2026-09-28 on two archived tasks: 71 and 72 percent
#      of each count was the dispatching session's own output, and the rest mixed
#      both tasks' agents). A transcript now counts for a task only when its own
#      tool calls, or those of the agent that dispatched it, name the task and no
#      concurrent task; a transcript naming both counts for neither.
#   18. A sub-agent transcript written by Claude Code 2.1.280 or later keeps
#      only a streaming snapshot for most messages (measured: 1,150 final of
#      10,679 messages). A snapshot is not a count, so the field is null and the
#      reason says so.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER="${HELPER:-${SCRIPT_DIR}/../compute-task-outcome.py}"
SCHEMA="${SCRIPT_DIR}/../../templates/OUTCOMES.schema.md"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

state() {  # state <folder> <init-ts> [<last-ts>]; a TASK_STATE.md with write headers
  mkdir -p "$1"
  {
    echo "# TASK_STATE"
    echo ""
    echo "<!-- wos:write owner=task-init section='## Task summary' run_id=01J1 ts=$2 reason=task-init-fixture mode=applied -->"
    echo "## Task summary"
    echo "A fixture."
    echo ""
    echo "<!-- wos:write owner=task-init section='## Resume notes' run_id=01J1 ts=$2 reason=task-init-fixture mode=applied -->"
    echo "## Resume notes"
    echo "- Task branch: task/$(basename "$1")"
    echo "- Base branch: main"
    if [ -n "${3:-}" ]; then
      echo ""
      echo "<!-- wos:write owner=task-close section='## Current phase' run_id=01J2 ts=$3 reason=task-closed mode=applied -->"
      echo "## Current phase"
      echo "closed"
    fi
  } > "$1/TASK_STATE.md"
}

# The task under test: init at 2026-09-20T10:00:00Z, closed at 18:00.
TASK="$TMP/projects/acme__demo/active/2026-09-20_usage"
state "$TASK" 2026-09-20T10:00:00.000Z
CLOSE="2026-09-20T18:00:00.000Z"

run() {  # run [extra args...]; prints the outcome line
  python3 "$HELPER" "$TASK" --merge-status merged --close-ts "$CLOSE" "$@" 2>/dev/null
}
field() {  # field <json-line> <key>; prints the field as JSON, or MISSING
  printf '%s' "$1" | python3 -c 'import json,sys; r=json.load(sys.stdin); k=sys.argv[1]; print(json.dumps(r[k], sort_keys=True) if k in r else "MISSING")' "$2" 2>/dev/null || echo ERROR
}
expect() {  # expect <got> <want> <label>
  [ "$1" = "$2" ] && pass "$3" || fail "$3 (got '$1', expected '$2')"
}
contains() {  # contains <got> <substring> <label>
  [[ "$1" == *"$2"* ]] && pass "$3" || fail "$3 (got '$1', expected it to contain '$2')"
}

# asst <ts> <model> <msg-id> <output-tokens> <final:1|0> [<tool-call text>]
# One assistant transcript line. With a tool-call text, the line carries one
# tool_use block whose input is {"command": text}; final lines carry a stop_reason.
asst() {
  local stop='null' content='[{"type":"text","text":"-"}]'
  [ "$5" = 1 ] && stop='"tool_use"'
  [ -n "${6:-}" ] && content="[{\"type\":\"tool_use\",\"name\":\"Bash\",\"input\":{\"command\":\"$6\"}}]"
  printf '{"type":"assistant","timestamp":"%s","gitBranch":"main","message":{"id":"%s","model":"%s","stop_reason":%s,"content":%s,"usage":{"output_tokens":%s}}}\n' \
    "$1" "$3" "$2" "$stop" "$content" "$4"
}
meta() {  # meta <file> [<parent agent id>]
  if [ -n "${2:-}" ]; then printf '{"agentType":"general-purpose","parentAgentId":"%s"}\n' "$2" > "$1"
  else printf '{"agentType":"general-purpose"}\n' > "$1"; fi
}

# 1. No usage source: the field is present and null, never guessed, and says why.
LINE="$(run)"
expect "$(field "$LINE" output_tokens_by_model)" null "1. no usage source records output_tokens_by_model as null"
expect "$(field "$LINE" output_tokens_source)" null "1b. and output_tokens_source as null"
expect "$(field "$LINE" output_tokens_null_reason)" '"no usage source passed"' "1c. and output_tokens_null_reason says no source was passed"

# 2. The neutral json adapter: any harness can write {model: tokens}.
printf '{"model-a": 1200, "model-b": 300}\n' > "$TMP/usage.json"
LINE="$(run --usage-source "json:$TMP/usage.json")"
expect "$(field "$LINE" output_tokens_by_model)" '{"model-a": 1200, "model-b": 300}' "2. the json adapter records the object as given"
expect "$(field "$LINE" output_tokens_source)" '"json"' "2b. and names its adapter"
expect "$(field "$LINE" output_tokens_null_reason)" null "2c. and a filled count carries no null reason"

# A Claude Code session for one task: the session file, one sub-agent it
# dispatched, and one reviewer that sub-agent dispatched, laid out as the harness
# lays them out (<session>.jsonl beside <session>/subagents/agent-<id>.jsonl plus
# agent-<id>.meta.json).
NAME_T="projects/acme__demo/active/2026-09-20_usage/TASK_STATE.md"
SESS="$TMP/transcripts/sess-1.jsonl"
SUB="$TMP/transcripts/sess-1/subagents"
mkdir -p "$SUB"
{
  asst 2026-09-20T09:00:00.000Z model-big m0 5000 1 "cat $NAME_T"   # before init: out
  asst 2026-09-20T11:00:00.000Z model-big m1 100 1 "cat $NAME_T"
  asst 2026-09-20T11:00:00.500Z model-big m1 100 1                  # same message, second block
  asst 2026-09-20T12:00:00.000Z model-small m2 40 1
  asst 2026-09-20T12:30:00.000Z model-big m3 7000 1                 # launch branch main: in
  printf '{"type":"user","timestamp":"2026-09-20T12:00:00.000Z"}\n'
  printf 'not json\n'
  asst 2026-09-20T19:00:00.000Z model-big m4 9000 1                 # after close: out
} > "$SESS"
{
  asst 2026-09-20T12:10:00.000Z model-small m5 7 0 "git -C . switch task/2026-09-20_usage"   # streaming snapshot
  asst 2026-09-20T12:10:01.000Z model-small m5 210 1                                           # final line, same message
  asst 2026-09-20T13:00:00.000Z model-small s1 60 1
} > "$SUB/agent-a1.jsonl"
meta "$SUB/agent-a1.meta.json"
asst 2026-09-20T13:30:00.000Z model-small r1 30 1 "grep -n x README.md" > "$SUB/agent-a2.jsonl"   # names no task
meta "$SUB/agent-a2.meta.json" a1

LINE="$(run --usage-source "claude-code:$SESS")"
GOT="$(field "$LINE" output_tokens_by_model)"
expect "$GOT" '{"model-big": 7100, "model-small": 340}' \
  "3. the claude-code adapter sums in-window messages per model over the session and its sub-agents"
[[ "$GOT" == *'"model-big": 7100'* && "$GOT" == *'"model-small": 340'* ]] \
  && pass "4. a message split across lines counts once, at its final count (100 not 200, 210 not 7 or 217)" \
  || fail "4. a message split across lines counts once, at its final count (got $GOT)"
SRC="$(field "$LINE" output_tokens_source)"
[[ "$SRC" == *"claude-code"* && "$SRC" == *"time window"* && "$SRC" == *"attributed by task name"* && "$SRC" == *"3 transcripts counted"* ]] \
  && pass "5. the source names the adapter, the window, and the attribution" \
  || fail "5. the source names the adapter, the window, and the attribution (got $SRC)"

# 6. A directory of transcripts reads every file in it.
LINE="$(run --usage-source "claude-code:$TMP/transcripts")"
expect "$(field "$LINE" output_tokens_by_model)" '{"model-big": 7100, "model-small": 340}' \
  "6. a transcript directory is read whole, with the same window"

# 7. The reader keys on the task folder's name, not on the Task branch line in
# TASK_STATE.md: a folder of the same name with no branch line gets the same
# count. (This also documents that a same-named folder in another project is
# credited with those tokens; no two task folders share a name today.)
NOBRANCH="$TMP/projects/acme__elsewhere/active/2026-09-20_usage"
mkdir -p "$NOBRANCH"
sed '/Task branch:/d' "$TASK/TASK_STATE.md" > "$NOBRANCH/TASK_STATE.md"
LINE="$(python3 "$HELPER" "$NOBRANCH" --merge-status merged --close-ts "$CLOSE" --usage-source "claude-code:$SESS" 2>/dev/null)"
expect "$(field "$LINE" output_tokens_by_model)" '{"model-big": 7100, "model-small": 340}' \
  "7. a task with no branch recorded gets the same count"

# 8. Nothing readable is null with a reason, and the helper still exits 0.
LINE="$(run --usage-source "claude-code:$TMP/does-not-exist")"; RC=$?
expect "$(field "$LINE" output_tokens_by_model)" null "8. an unreadable source records null"
contains "$(field "$LINE" output_tokens_null_reason)" "no transcript" "8b. with a reason naming the missing transcript"
[ "$RC" -eq 0 ] && pass "8c. and the helper exits 0" || fail "8c. and the helper exits 0 (rc=$RC)"

# 9. A source with no line in the window is null, not zero.
EMPTYWIN="$TMP/late.jsonl"
asst 2026-09-21T10:00:00.000Z model-big z1 50 1 "cat $NAME_T" > "$EMPTYWIN"
LINE="$(run --usage-source "claude-code:$EMPTYWIN")"
expect "$(field "$LINE" output_tokens_by_model)" null "9. no line inside the window records null, not an empty count"
contains "$(field "$LINE" output_tokens_null_reason)" "no assistant line inside the task window" "9b. with that reason"

# 10. An unknown adapter and a malformed json source are null with a reason.
LINE="$(run --usage-source "cursor:$TMP/usage.json")"
expect "$(field "$LINE" output_tokens_by_model)" null "10. an unknown adapter records null"
contains "$(field "$LINE" output_tokens_null_reason)" "unknown adapter" "10b. with a reason naming the adapter"
printf '{"model-a": "lots"}\n' > "$TMP/bad.json"
LINE="$(run --usage-source "json:$TMP/bad.json")"
expect "$(field "$LINE" output_tokens_by_model)" null "10c. a json source with a non-integer count records null"
contains "$(field "$LINE" output_tokens_null_reason)" "json:" "10d. with a reason naming the json adapter"

# 11. The except-path fallback carries all three fields, so a reader never hits a KeyError.
N="$(sed -n '/degradation rule: never traceback/,/print(json.dumps(record))/p' "$HELPER" | grep -c '"output_tokens_null_reason"')"
[ "$N" -ge 1 ] && pass "11. the except-path fallback record carries output_tokens_null_reason" \
               || fail "11. the except-path fallback record carries output_tokens_null_reason"

# 12. The schema documents the fields, so readers and producers share one contract.
grep -q 'output_tokens_by_model' "$SCHEMA" && grep -q 'output_tokens_source' "$SCHEMA" && grep -q 'output_tokens_null_reason' "$SCHEMA" \
  && pass "12. templates/OUTCOMES.schema.md documents all three fields" \
  || fail "12. templates/OUTCOMES.schema.md documents all three fields"

# Two tasks at once. alpha and beta ran in the same window as sub-agents of one
# session; old is a sibling that finished before the window opened, and noheader
# is a sibling with no write headers, so nothing says when it ran.
P2="$TMP/projects/acme__two"
ALPHA="$P2/active/2026-09-20_alpha"
BETA="$P2/archive/2026-09-20_beta"
state "$ALPHA" 2026-09-20T10:00:00.000Z
state "$BETA" 2026-09-20T10:05:00.000Z 2026-09-20T17:55:00.000Z
state "$P2/archive/2026-09-19_old" 2026-09-19T08:00:00.000Z 2026-09-19T09:00:00.000Z
mkdir -p "$P2/archive/2026-09-20_noheader"; printf '# TASK_STATE\n' > "$P2/archive/2026-09-20_noheader/TASK_STATE.md"
S2="$TMP/two/sess-2.jsonl"; SUB2="$TMP/two/sess-2/subagents"; mkdir -p "$SUB2"
{
  asst 2026-09-20T11:00:00.000Z model-big d1 5000 1 "launch projects/acme__two/active/2026-09-20_alpha"
  asst 2026-09-20T11:01:00.000Z model-big d2 4000 1 "launch projects/acme__two/active/2026-09-20_beta"
} > "$S2"
asst 2026-09-20T11:10:00.000Z model-big x1 700 1 "cat projects/acme__two/active/2026-09-20_alpha/TASK_STATE.md" > "$SUB2/agent-x1.jsonl"; meta "$SUB2/agent-x1.meta.json"
asst 2026-09-20T11:20:00.000Z model-small x2 50 1 "git diff" > "$SUB2/agent-x2.jsonl"; meta "$SUB2/agent-x2.meta.json" x1
asst 2026-09-20T11:30:00.000Z model-small x3 5 1 "cat archive/2026-09-19_old/DECISIONS.md archive/2026-09-20_noheader/x active/2026-09-20_alpha/y" > "$SUB2/agent-x3.jsonl"; meta "$SUB2/agent-x3.meta.json" x1
asst 2026-09-20T11:15:00.000Z model-big y1 900 1 "cat projects/acme__two/archive/2026-09-20_beta/TASK_STATE.md" > "$SUB2/agent-y1.jsonl"; meta "$SUB2/agent-y1.meta.json"
asst 2026-09-20T11:25:00.000Z model-small y2 80 1 "git status" > "$SUB2/agent-y2.jsonl"; meta "$SUB2/agent-y2.meta.json" y1
{
  asst 2026-09-20T11:40:00.000Z model-small z1 11 1 "ls"
  asst 2026-09-20T11:41:00.000Z model-small z9 4 0      # a snapshot in an excluded transcript: nulls neither task
} > "$SUB2/agent-z1.jsonl"; meta "$SUB2/agent-z1.meta.json"
# A heredoc whose second line starts with beta's folder name: the agent names
# alpha and beta, so it is ambiguous even though beta's name follows a newline.
asst 2026-09-20T11:50:00.000Z model-small h1 9 1 "cat > active/2026-09-20_alpha/notes.md <<EOF\\n2026-09-20_beta/TASK_STATE.md\\nEOF" > "$SUB2/agent-h1.jsonl"; meta "$SUB2/agent-h1.meta.json"
# A task in another project that is still active counts as concurrent too: an
# agent naming alpha and acme__demo's task is ambiguous.
asst 2026-09-20T11:55:00.000Z model-small k1 6 1 "diff active/2026-09-20_alpha/a projects/acme__demo/active/2026-09-20_usage/b" > "$SUB2/agent-k1.jsonl"; meta "$SUB2/agent-k1.meta.json"
asst 2026-09-20T11:45:00.000Z model-small q1 3 1 "git switch task/2026-09-20_alpha-2" > "$SUB2/agent-q1.jsonl"; meta "$SUB2/agent-q1.meta.json"

LINE="$(python3 "$HELPER" "$ALPHA" --merge-status merged --close-ts "$CLOSE" --usage-source "claude-code:$S2" 2>/dev/null)"
expect "$(field "$LINE" output_tokens_by_model)" '{"model-big": 700, "model-small": 55}' \
  "13. of two concurrent tasks, alpha counts only its own agent and the agents it dispatched"
SRC="$(field "$LINE" output_tokens_source)"
contains "$SRC" "3 transcripts counted" "14. the source says how many transcripts were counted"
contains "$SRC" "7 excluded: 5 ambiguous, 2 of a concurrent task, 0 unattributed" \
  "15. and how many were excluded: the session naming both, what it dispatched unnamed, a heredoc naming both, an agent naming a task of another project, and beta's agents"
LINE="$(python3 "$HELPER" "$BETA" --merge-status merged --close-ts "$CLOSE" --usage-source "claude-code:$S2" 2>/dev/null)"
expect "$(field "$LINE" output_tokens_by_model)" '{"model-big": 900, "model-small": 80}' \
  "16. beta, read from the same transcripts, gets its own agents and none of alpha's"
# 17. A name counts only whole. Case 13 already shows that x3 (naming a sibling
# that ran earlier and one with no headers) still counts for alpha, and that q1
# (naming only task/2026-09-20_alpha-2) does not. Here a session that names only
# a longer name starting with the task's name is not attributed to the task.
S5="$TMP/five.jsonl"
asst 2026-09-20T11:00:00.000Z model-big w1 800 1 "git switch task/2026-09-20_usage-2" > "$S5"
LINE="$(run --usage-source "claude-code:$S5")"
expect "$(field "$LINE" output_tokens_by_model)" null "17. a longer name that starts with the task's name is not the task's name"

# 18. An attributed message with no final line makes the count null, with the reason.
S3="$TMP/three/sess-3.jsonl"; SUB3="$TMP/three/sess-3/subagents"; mkdir -p "$SUB3"
asst 2026-09-20T11:00:00.000Z model-big n1 400 1 "cat $NAME_T" > "$S3"
asst 2026-09-20T11:05:00.000Z model-big n2 5 0 "cat $NAME_T" > "$SUB3/agent-c1.jsonl"; meta "$SUB3/agent-c1.meta.json"
LINE="$(run --usage-source "claude-code:$S3")"
expect "$(field "$LINE" output_tokens_by_model)" null "18. a sub-agent message with only a streaming snapshot makes the count null"
contains "$(field "$LINE" output_tokens_null_reason)" "1 of 2 attributed messages have no final count" "18b. and the reason counts them"

# 19. No transcript names the task: null, with the reason, not the window's total.
S4="$TMP/four.jsonl"
asst 2026-09-20T11:00:00.000Z model-big o1 800 1 "ls" > "$S4"
LINE="$(run --usage-source "claude-code:$S4")"
expect "$(field "$LINE" output_tokens_by_model)" null "19. a window whose transcripts never name the task records null"
contains "$(field "$LINE" output_tokens_null_reason)" "no transcript in the window is attributed to the task" "19b. with that reason"

# 20. A name counts only inside the window: a session that names the task
# before init and not after is not attributed to it.
S6="$TMP/six.jsonl"
{
  asst 2026-09-20T09:00:00.000Z model-big e1 300 1 "cat $NAME_T"
  asst 2026-09-20T11:00:00.000Z model-big e2 500 1 "ls"
} > "$S6"
LINE="$(run --usage-source "claude-code:$S6")"
expect "$(field "$LINE" output_tokens_by_model)" null "20. a name mentioned only before the window does not attribute the window's lines"

# 21. A response that starts inside the window and whose final line lands just
# after the close counts at its final count, not as an unfinished snapshot.
S7="$TMP/seven.jsonl"
{
  asst 2026-09-20T17:59:59.000Z model-big c1 3 0 "cat $NAME_T"
  asst 2026-09-20T18:00:02.000Z model-big c1 640 1
} > "$S7"
LINE="$(run --usage-source "claude-code:$S7")"
expect "$(field "$LINE" output_tokens_by_model)" '{"model-big": 640}' \
  "21. a message cut by the close boundary counts at the count its final line carries"

# 22. A sibling task folder whose TASK_STATE.md holds undecodable bytes never
# degrades this task's line, with or without a usage source.
printf '# TASK_STATE\n\xff\xfe broken\n' > "$P2/archive/2026-09-19_old/TASK_STATE.md"
LINE="$(python3 "$HELPER" "$ALPHA" --merge-status merged --close-ts "$CLOSE" 2>/dev/null)"
expect "$(field "$LINE" project)" '"acme__two"' "22. a damaged sibling TASK_STATE.md leaves the line intact without a usage source"
LINE="$(python3 "$HELPER" "$ALPHA" --merge-status merged --close-ts "$CLOSE" --usage-source "claude-code:$S2" 2>/dev/null)"
expect "$(field "$LINE" output_tokens_by_model)" '{"model-big": 700, "model-small": 55}' \
  "22b. and with one, the count is the same"

echo ""
echo "test-compute-task-outcome-usage: ${checks} check(s), ${fails} failure(s)"
[ "$fails" -eq 0 ]
