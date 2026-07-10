#!/usr/bin/env bash
# portfolio-review.sh -- read-only cross-task board for Fhorja.
#
# Walks every active task (projects/*/active/*/TASK_STATE.md), extracts each
# task's phase, recommended next command, blocker state, and idle time, then
# classifies and prints one ranked row per task plus per-class counts. The
# `portfolio-review` command interprets this table and recommends one action
# per row. Pure read-only: nothing is written.
#
# Usage:
#   scripts/portfolio-review.sh [--project <slug>] [--stale-days N]
#
# Classes (sort order): done-unclosed, blocked, my-move, stale, in-flight.
#
# --outcomes mode reads projects/*/OUTCOMES.jsonl per the read contract in
# templates/OUTCOMES.schema.md (schema version 1). Measurement only: it
# reports what happened, it never gates a workflow step.
#
# --json mode emits the classified active-task rows as one JSON array
# ({class, idle_days, project, task, next_command}, loop order, unsorted)
# for machine consumers like scripts/build-portfolio-board.py. It reuses the
# SAME classification loop as the board, so the taxonomy cannot drift.

# -u catches real bugs; no -e (a non-matching grep over heterogeneous task files
# is normal, not an error). pipefail kept for genuine pipe failures.
set -uo pipefail

PROJECT_FILTER=""
STALE_DAYS=7
MODE="board"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT_FILTER="${2:-}"; shift 2 ;;
    --stale-days) STALE_DAYS="${2:-7}"; shift 2 ;;
    --initiative) MODE="initiative"; shift ;;
    --outcomes) MODE="outcomes"; shift ;;
    --json) JSON_FLAG=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Flag resolution: bare --json keeps its historical meaning (the active-task
# array); combined with --initiative (either order) it selects the initiative
# JSON emitter (the ADR-0080 single-source pattern extended to initiatives).
if [[ "${JSON_FLAG:-0}" -eq 1 ]]; then
  if [[ "$MODE" == "initiative" ]]; then MODE="initiative-json"; else MODE="json"; fi
fi

# Repo root = parent of this script's dir.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# --initiative mode: best-effort dependency view over projects/*/INITIATIVE_INDEX.md.
# Parses each row's slug, status, and any "blocked-by: ..." cross-link, then reports
# per-task ready/blocked state, one start-now recommendation, and dangling-ref +
# deadlock(cycle) warnings. Best-effort grep parsing (the cross-link column is free
# text); it warns rather than fails on rows it cannot parse. Read-only.
# parse_initiative_rows <index-file> <out-file>
# The single parse point for INITIATIVE_INDEX.md tables (both the human view
# and the JSON emitter call this; the board consumes the emitter). Emits one
# TSV row per data row: slug, status, blocked-by, objective, next-command.
# Status (and, when a header exists, objective and next) come from
# header-derived column indexes; a headerless table falls back to the
# historical whole-row status match with empty objective/next.
parse_initiative_rows() {
  local idx="$1" out="$2"
  awk '
    # A non-table line ends the current table: forget the learned column
    # indexes so a later headerless table degrades to the whole-row match.
    !/^[[:space:]]*\|/ { scol=0; ocol=0; ncol=0; next }
    /^[[:space:]]*\|/ {
      line=$0; low=tolower(line)
      if (line ~ /-{3,}/) next
      # Header row: learn the Status (and Objective / Next command) column
      # indexes from cells whose trimmed lowercase matches, then skip the row.
      nc=split(low, cells, "|")
      hdr=0
      for (i=1; i<=nc; i++) {
        c=cells[i]; gsub(/^[[:space:]]+|[[:space:]]+$/, "", c)
        if (c=="status") { scol=i; hdr=1 }
        else if (c=="objective") { ocol=i }
        else if (c ~ /^next/) { ncol=i }
      }
      if (hdr) next
      if (low ~ /slug/ && low ~ /status/) next
      slug=""
      if (match(line, /`[a-z0-9][a-z0-9_-]+`/)) slug=substr(line, RSTART+1, RLENGTH-2)
      else if (match(line, /[0-9]{4}-[0-9]{2}-[0-9]{2}_[a-z0-9-]+/)) slug=substr(line, RSTART, RLENGTH)
      if (slug=="") next
      status="unknown"
      if (scol > 0 && scol <= nc) {
        if (match(cells[scol], /done|closed|delivered|archived|in-progress|in progress|blocked|review|initialized|ready/)) { status=substr(cells[scol],RSTART,RLENGTH); gsub(/ /,"-",status) }
      } else if (match(low, /done|closed|delivered|archived|in-progress|in progress|blocked|review|initialized|ready/)) { status=substr(low,RSTART,RLENGTH); gsub(/ /,"-",status) }
      bb=""
      if (match(low, /blocked-by[: ]+[a-z0-9_,. -]+/)) { bb=substr(low,RSTART,RLENGTH); sub(/blocked-by[: ]+/,"",bb) }
      # Original-case objective and next-command cells for the JSON emitter
      # (empty on headerless tables); tabs cannot survive inside table cells,
      # so TSV stays unambiguous.
      no=split(line, ocells, "|")
      objective=""; nextcmd=""
      if (ocol > 0 && ocol <= no) { objective=ocells[ocol]; gsub(/^[[:space:]]+|[[:space:]]+$/, "", objective) }
      if (ncol > 0 && ncol <= no) { nextcmd=ocells[ncol]; gsub(/^[[:space:]]+|[[:space:]]+$/, "", nextcmd); gsub(/`/, "", nextcmd) }
      printf "%s\t%s\t%s\t%s\t%s\n", slug, status, bb, objective, nextcmd
    }
  ' "$idx" > "$out"
}

initiative_summary() {
  local found=0 idx project rows slug status bb d deps unmet dang done_slugs all_slugs
  for idx in projects/*/INITIATIVE_INDEX.md; do
    [[ -e "$idx" ]] || continue
    project="$(echo "$idx" | sed -E 's#projects/([^/]+)/INITIATIVE_INDEX.md#\1#')"
    [[ -n "$PROJECT_FILTER" && "$project" != "$PROJECT_FILTER" ]] && continue
    found=1
    echo "Initiative: ${project} (${idx})"
    rows="$(mktemp)"
    # slug, status, blocked-by, objective, next (TSV) via the single parse point.
    parse_initiative_rows "$idx" "$rows"

    if [[ ! -s "$rows" ]]; then
      echo "  (no parseable sub-task rows; check the table format)"; rm -f "$rows"; echo ""; continue
    fi
    done_slugs="$(awk -F'\t' '$2 ~ /done|closed|delivered|archived/ {print $1}' "$rows")"
    all_slugs="$(cut -f1 "$rows")"
    local ready_list="" blocked_n=0 remain_n=0 dangling=""
    while IFS=$'\t' read -r slug status bb _objective _nextcmd; do
      [[ -z "$slug" ]] && continue
      if echo "$status" | grep -qE 'done|closed|delivered|archived'; then
        echo "  [done]    ${slug}"; continue
      fi
      remain_n=$(( remain_n + 1 ))
      deps="$(echo "$bb" | tr ',. ' '\n' | sed -E 's/[^a-z0-9_-]//g' | grep -E '[a-z0-9]' || true)"
      unmet=""; dang=""
      for d in $deps; do
        if ! printf '%s\n' "$all_slugs" | grep -qx "$d"; then dang="${dang} ${d}"; continue; fi
        printf '%s\n' "$done_slugs" | grep -qx "$d" || unmet="${unmet} ${d}"
      done
      [[ -n "$dang" ]] && dangling="${dangling} ${slug}:[${dang} ]"
      if [[ -z "$unmet" ]]; then
        echo "  [ready]   ${slug}  (${status})"
        [[ -z "$ready_list" ]] && ready_list="$slug"
      else
        echo "  [blocked] ${slug}  blocked-by:${unmet}"; blocked_n=$(( blocked_n + 1 ))
      fi
    done < "$rows"
    rm -f "$rows"

    if [[ -n "$ready_list" ]]; then
      echo "  -> start now: ${ready_list}"
    elif [[ "$remain_n" -gt 0 ]]; then
      echo "  -> WARN: ${remain_n} task(s) remain but none are unblocked (possible dependency cycle or incomplete deps)"
    fi
    [[ -n "$dangling" ]] && echo "  -> WARN dangling blocked-by refs:${dangling}"
    echo ""
  done
  [[ "$found" -eq 0 ]] && echo "no INITIATIVE_INDEX.md found (run task-init-fleet to create one)"
}

if [[ "$MODE" == "initiative" ]]; then
  initiative_summary
  exit 0
fi

# --initiative --json mode: the initiative rows as one JSON array, same parse
# point as the human view; the portfolio board consumes this instead of
# re-parsing INITIATIVE_INDEX.md (single-source, the ADR-0080 D-2 pattern).
if [[ "$MODE" == "initiative-json" ]]; then
  ROWS_ALL="$(mktemp)"
  for idx in projects/*/INITIATIVE_INDEX.md; do
    [[ -e "$idx" ]] || continue
    project="$(echo "$idx" | sed -E 's#projects/([^/]+)/INITIATIVE_INDEX.md#\1#')"
    [[ -n "$PROJECT_FILTER" && "$project" != "$PROJECT_FILTER" ]] && continue
    tmp_rows="$(mktemp)"
    parse_initiative_rows "$idx" "$tmp_rows"
    awk -F'\t' -v p="$project" '{ printf "%s\t%s\n", p, $0 }' "$tmp_rows" >> "$ROWS_ALL"
    rm -f "$tmp_rows"
  done
  python3 -c '
import json, sys
rows = []
for line in sys.stdin:
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 3 or not parts[1]:
        continue
    rows.append({
        "project": parts[0],
        "task": parts[1],
        "status": parts[2],
        "objective": parts[4] if len(parts) > 4 else "",
        "next_command": parts[5] if len(parts) > 5 else "",
    })
print(json.dumps(rows, indent=2))
' < "$ROWS_ALL"
  rm -f "$ROWS_ALL"
  exit 0
fi

# --outcomes mode: walk projects/*/OUTCOMES.jsonl and report closed-task counts,
# effective-status counts, and cycle-time medians, per the read contract in
# templates/OUTCOMES.schema.md. This script only globs files, filters by
# --project, and hands each ledger to python3 (stdlib json + statistics) for
# parsing and aggregation; the repo pattern is bash orchestration, python for
# structured data (do not parse JSON with awk). Read-only, measurement only.
outcomes_summary() {
  local found=0 ledger project
  for ledger in projects/*/OUTCOMES.jsonl; do
    [[ -e "$ledger" ]] || continue
    project="$(echo "$ledger" | sed -E 's#projects/([^/]+)/OUTCOMES.jsonl#\1#')"
    [[ -n "$PROJECT_FILTER" && "$project" != "$PROJECT_FILTER" ]] && continue
    found=1
    echo "Outcomes: ${project} (${ledger})"
    python3 - "$ledger" <<'PY'
import json
import sys
from statistics import median

# Chronological phase-boundary order per templates/OUTCOMES.schema.md D-3.
PHASE_ORDER = [
    "init_to_planning",
    "planning_to_implementation",
    "implementation_to_delivery_prep",
    "delivery_prep_to_close",
]
KNOWN_STATUSES = ("merged", "waived", "not-merged", "reverted")

path = sys.argv[1]

# task -> (ts, record) for the latest event=outcome line (read rule: latest
# outcome wins when a task has more than one).
outcome_latest = {}
# task -> (ts, event) for the latest line of ANY event type, used to resolve
# effective status: a later revert overrides an earlier outcome.
overall_latest = {}

with open(path) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue  # tolerate a malformed line rather than fail the report
        if not isinstance(rec, dict):
            continue  # tolerate a non-object line (valid JSON, wrong shape)
        task = rec.get("task")
        ts = rec.get("ts")
        event = rec.get("event")
        if not task or not ts or not event:
            continue  # unknown/incomplete line; ignore rather than fail
        prev = overall_latest.get(task)
        if prev is None or ts > prev[0]:
            overall_latest[task] = (ts, event)
        if event == "outcome":
            prev_o = outcome_latest.get(task)
            if prev_o is None or ts > prev_o[0]:
                outcome_latest[task] = (ts, rec)

if not outcome_latest:
    print("  no outcome records yet")
else:
    status_counts = {k: 0 for k in KNOWN_STATUSES}
    other = 0  # forward-compat: statuses this reader does not know yet
    totals = []
    phase_lists = {}
    for task, (_o_ts, rec) in outcome_latest.items():
        latest = overall_latest.get(task)
        if latest and latest[1] == "revert":
            status_counts["reverted"] += 1
        else:
            status = rec.get("merge_status")
            if status in status_counts:
                status_counts[status] += 1
            else:
                other += 1
        phase_days = rec.get("phase_days")
        if isinstance(phase_days, dict):
            total = phase_days.get("total")
            if isinstance(total, (int, float)):
                totals.append(total)
            for phase in PHASE_ORDER:
                v = phase_days.get(phase)
                if isinstance(v, (int, float)):
                    phase_lists.setdefault(phase, []).append(v)

    print(f"  closed tasks: {len(outcome_latest)}")
    line = "  status: merged={0} waived={1} not-merged={2} reverted={3}".format(
        status_counts["merged"],
        status_counts["waived"],
        status_counts["not-merged"],
        status_counts["reverted"],
    )
    if other:
        line += f" other={other}"
    print(line)
    if totals:
        print(f"  median total cycle days: {median(totals):.2f}")
    else:
        print("  median total cycle days: n/a")
    for phase in PHASE_ORDER:
        if phase in phase_lists:
            print(f"  median {phase}: {median(phase_lists[phase]):.2f}")
PY
    echo ""
  done
  [[ "$found" -eq 0 ]] && echo "no outcome records yet"
}

if [[ "$MODE" == "outcomes" ]]; then
  outcomes_summary
  exit 0
fi

NOW="$(date +%s)"

# Portable mtime: detect macOS `stat -f` vs GNU `stat -c` once.
if stat -f '%m' "$0" >/dev/null 2>&1; then STAT=(stat -f '%m'); else STAT=(stat -c '%Y'); fi

# Newest mtime across a folder's files = the task's last activity (0 if none).
folder_mtime() {
  local newest
  newest="$(find "$1" -type f -exec "${STAT[@]}" {} + 2>/dev/null | sort -rn | head -1)"
  echo "${newest:-0}"
}

# First non-empty, non-comment line of a `## <header>` section.
section_first_line() {
  awk -v h="$1" '
    $0 == h { f=1; next }
    /^## / && f { exit }
    f && /^<!--/ { next }
    f && NF { print; exit }
  ' "$2"
}

# Whole body of a section (for blocker emptiness check).
section_body() {
  awk -v h="$1" '$0 == h { f=1; next } /^## / && f { exit } f && !/^<!--/ { print }' "$2"
}

ROWS=()
RAWS=()   # raw tab-separated fields for --json (same loop, same classifier)
# Plain counters (no associative arrays: macOS ships bash 3.2).
c_done=0 c_blocked=0 c_mymove=0 c_stale=0 c_inflight=0

# Next-command signals. MYMOVE = a decision only the maintainer can make.
# TERMINAL = one step from closed (finish and archive).
MYMOVE_CMDS="decision-interview approve-plan approve-proposed targeted-questions resolve-contract-gaps contract-signoff"
TERMINAL_CMDS="task-close pr-package branch-commit where-we-at slice-closure"

for ts in projects/*/active/*/TASK_STATE.md; do
  [[ -e "$ts" ]] || continue
  dir="$(dirname "$ts")"
  project="$(echo "$dir" | sed -E 's#projects/([^/]+)/active/.*#\1#')"
  task="$(basename "$dir")"
  [[ -n "$PROJECT_FILTER" && "$project" != "$PROJECT_FILTER" ]] && continue

  phase_line="$(section_first_line '## Current phase' "$ts")"
  phase_short="$(echo "$phase_line" | cut -c1-32)"
  next_raw="$(section_body '## Recommended next step' "$ts" | grep -m1 -E '^- Command:' | sed -E 's/^- Command:[[:space:]]*//' || true)"
  # strip markdown noise (backticks, asterisks), drop a leading slash, keep the bare command token
  next_cmd="$(echo "$next_raw" | tr -d '`*' | awk '{print $1}' | sed -E 's#^/##; s/[^a-zA-Z0-9_-].*$//')"
  [[ -z "$next_cmd" ]] && next_cmd="-"

  # real blocker = an explicit "block" mention, not the "No blockers" boilerplate
  blocker_hit="$(section_body '## Open questions / blockers' "$ts" | grep -iE 'block' | grep -ivE 'no blocker|no planning blocker|without block' || true)"

  mtime="$(folder_mtime "$dir")"
  if [[ "$mtime" -gt 0 ]]; then idle=$(( (NOW - mtime) / 86400 )); else idle=999; fi

  # Classify (first match wins, in priority order).
  # done-unclosed = finished or one step from it, still sitting in active/ (close/archive it).
  class="in-flight"
  if echo "$phase_line" | grep -iqE 'closed|done|delivery' \
     || echo " $TERMINAL_CMDS " | grep -q " $next_cmd "; then
    class="done-unclosed"
  elif [[ -n "$blocker_hit" ]]; then
    class="blocked"
  elif echo " $MYMOVE_CMDS " | grep -q " $next_cmd "; then
    class="my-move"
  elif [[ "$idle" -gt "$STALE_DAYS" ]]; then
    class="stale"
  fi
  # rank + count per class
  case "$class" in
    done-unclosed) pr=0; c_done=$(( c_done + 1 )) ;;
    blocked)       pr=1; c_blocked=$(( c_blocked + 1 )) ;;
    my-move)       pr=2; c_mymove=$(( c_mymove + 1 )) ;;
    stale)         pr=3; c_stale=$(( c_stale + 1 )) ;;
    *)             pr=4; c_inflight=$(( c_inflight + 1 )) ;;
  esac
  # tab fields 1-2 are sort keys (class priority, idle); field 3 is the space-formatted display line
  disp="$(printf '%-13s %4dd  %-32s %-52s %s' "$class" "$idle" "$project" "$task" "$next_cmd")"
  ROWS+=("$(printf '%d\t%05d\t%s' "$pr" "$idle" "$disp")")
  RAWS+=("$(printf '%s\t%s\t%s\t%s\t%s' "$class" "$idle" "$project" "$task" "$next_cmd")")
done

# --json: same rows the board just classified, emitted as a JSON array via
# python3 (never hand-assembled in bash). Exits before the table renders.
if [[ "$MODE" == "json" ]]; then
  { [[ ${#RAWS[@]} -gt 0 ]] && printf '%s\n' "${RAWS[@]}"; } | python3 -c '
import json, sys
rows = []
for line in sys.stdin:
    parts = line.rstrip("\n").split("\t")
    if len(parts) != 5:
        continue  # tolerate a malformed row rather than fail the emitter
    cls, idle, project, task, next_cmd = parts
    rows.append({
        "class": cls,
        "idle_days": int(idle) if idle.lstrip("-").isdigit() else None,
        "project": project,
        "task": task,
        "next_command": next_cmd,
    })
print(json.dumps(rows))
'
  exit 0
fi

echo "Portfolio review -- ${#ROWS[@]} active task(s), stale threshold ${STALE_DAYS}d"
printf '%-13s %5s  %-32s %-52s %s\n' "class" "idle" "project" "task" "next"
printf '%-13s %5s  %-32s %-52s %s\n' "-------------" "-----" "--------------------------------" "----------------------------------------------------" "----"
# sort by class priority then idle desc, then strip the two sort-key columns.
# Guard the empty case: under bash 3.2 (macOS) with `set -u`, expanding an empty
# "${ROWS[@]}" errors as an unbound variable; with no active tasks there is
# nothing to print anyway.
if [[ ${#ROWS[@]} -gt 0 ]]; then
  printf '%s\n' "${ROWS[@]}" | sort -t"$(printf '\t')" -k1,1n -k2,2nr | cut -f3-
fi
echo "----"
echo "totals: done-unclosed=${c_done}  blocked=${c_blocked}  my-move=${c_mymove}  stale=${c_stale}  in-flight=${c_inflight}"
