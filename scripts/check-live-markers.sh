#!/usr/bin/env bash
# check-live-markers.sh: does a task's plan carry a LIVE unresolved-clarification
# marker, as opposed to prose about one.
#
# WHY. `approve-plan` refuses a plan containing the marker. The rule was prose read
# by a model, so a plan whose own text said "no such markers remain" spelled the
# marker and was refused. Third recorded occurrence of that shape; two LEARNINGS
# entries saying never to do it were surfaced by the ranker, read, and it happened
# again in the same session. Prose did not hold, so this is the rule as code.
#
# THE DISCRIMINATION IS MECHANICAL, and it was read off the corpus rather than
# invented. Every live marker in 79 active task folders is UNBACKTICKED and opens a
# bullet:   - [NEEDS CLARIFICATION: the environments require ...]
# Every mention that is prose about the marker sits inside a backtick code span:
#   No `[NEEDS CLARIFICATION:]` markers remain in the plan.
#   Zero `[NEEDS CLARIFICATION:` markers. Two backticked mentions below.
# So: strip code spans first, then look. That is the whole rule.
#
# USAGE
#   check-live-markers.sh <task-folder>
# Exit 0: no live marker. Exit 1: at least one, each printed as file:line.
# Exit 2: the folder does not exist, or holds none of the three files, so nothing
# was read (never a verdict). A folder with none of them printed "none" with exit 0
# until 2026-09-23, a clean verdict on files nobody read (ADR-0224).
set -uo pipefail

TASK="${1:-}"
[ -n "$TASK" ] || { echo "usage: check-live-markers.sh <task-folder>" >&2; exit 2; }
[ -d "$TASK" ] || { echo "check-live-markers: no such folder: $TASK" >&2; exit 2; }

MARKER='[NEEDS CLARIFICATION'
found=0
read_n=0

for f in IMPLEMENTATION_PLAN.md TASK_STATE.md DECISIONS.md; do
  p="${TASK}/${f}"
  [ -f "$p" ] || continue
  read_n=$((read_n + 1))
  # index() and not a regex. The first version of this used a dynamic awk regex on
  # a marker that opens with `[`, awk read it as an unterminated character class,
  # and BOTH directions of the control returned exit 0. A broken check that prints
  # a clean result is the defect this whole file exists to stop, so it is recorded
  # here rather than quietly corrected.
  while IFS= read -r hit; do
    [ -n "$hit" ] || continue
    echo "  live-marker: ${f}:${hit}"
    found=1
  done < <(awk -v m="$MARKER" '
    /^[ \t]*```/ { fence = !fence; next }
    fence { next }
    {
      line = $0
      gsub(/`[^`]*`/, "", line)        # paired code spans are prose ABOUT the marker
      if (index(line, m) > 0) print FNR ": " $0
    }
  ' "$p")
done

if [ "$read_n" -eq 0 ]; then
  echo "Live-markers: not scanned (no IMPLEMENTATION_PLAN.md, TASK_STATE.md or DECISIONS.md in $(basename "$TASK"))"
  exit 2
fi

if [ "$found" -eq 0 ]; then
  echo "Live-markers: none in $(basename "$TASK")"
  exit 0
fi
echo "Live-markers: at least one unresolved marker in $(basename "$TASK"); route to decision-interview"
exit 1
