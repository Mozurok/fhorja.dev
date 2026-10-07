#!/usr/bin/env bash
# check-slice-order.sh -- refuse a slice whose Depends-on slices are not closed in the plan.
#
# WHY THIS EXISTS (ADR-0244, provisional decisions P-7 and P-11). Next-slice routing lived only
# in the Handoff of implement-approved-slice, so an agent that stopped printing Handoffs left
# the chain silently: on 2026-09-29 two headless runs executed 9 or 10 slices inside one
# skill load with no slice-closure between them. implement-approved-slice runs this script
# before it starts a slice and refuses on exit 1.
#
# WHAT IT CHECKS. For the slice given as the second argument, every slice named in that
# slice's `Depends-on:` line in `IMPLEMENTATION_PLAN.md ## Slices` is closed. Only
# `Depends-on:` is read, never "every earlier slice": a wave-parallel slice under
# implement-fleet is not refused because a sibling of its wave is still open (ADR-0243).
#
# THE CLOSURE RECORD (P-11). A dependency is closed when its `### <id>` block in
# `IMPLEMENTATION_PLAN.md ## Slices` carries a first `Status:` value starting with `closed`
# (`closed`, `closed-with-followups` and `closed (inline; commit abc123)` all count), a bare
# `done`, or `done` followed by a space or `(`, in any case: plans written before P-11 carry a
# hand-written `done` on slices closed and merged then (`DONE 2026-07-06 (wave 2)`), and
# refusing those would send merged work back through slice-closure (final review SF-1).
# `done` followed by any other character (`done-ish`, `done,`) does not count. Every
# command that closes a slice writes that value: implement-approved-slice on an inline close,
# slice-closure always, implement-fleet for each merged slice. A follow-up classified material
# reopens the slice, so slice-closure writes `not-ready` for it, which refuses. Nothing else
# counts: a slice note, a TASK_STATE.md line, a commit, or prose saying a slice is done is not
# a closure record.
# A plan whose slices carry no `Status:` field at all predates the field; it is not measured.
#
# ID MATCHING. `S1`, `S01`, `Slice 1`, `Slice S1`, `slice-1`, `1` and `01` name the same slice; other
# prefixes keep their letters (`H1`, `P01` = `P1`, `M1.1`, `S4b`). A heading's id is read from
# the start of its text; every other id before its first colon is an alias, so
# `### Slice 3 - P14.5: ...` answers to `3` and to `P14.5`. A slice's own id wins over an
# alias another heading carries. A `Depends-on:` value drops parentheticals, then splits on
# commas, semicolons, spaces, `and` (any case), `/`, `+`, `&` and `-`. A hyphen or en dash
# with no space around it and the same prefix on both sides is a range: `S1-S3`, `1-3` and
# `Slices 1-3` each name S1, S2 and S3, so no middle id is skipped. An empty value is read
# from the lines under it (`Depends-on:` then `- S1` then `- S2`) until the next field or
# blank line. `none`, `nenhum`, `n/a`, a lone `-` or dash character, and a value empty with no
# list under it mean no dependency. A value that also carries words that are not slice ids is
# not measured, because a number inside prose is not safely a slice.
#
# EXIT CODES.
#   0  every Depends-on slice is closed, or the slice depends on none.
#   1  the FIRST Depends-on slice, in the order the line lists them, whose plan Status is not
#      closed is named on the summary line. Route: slice-closure for that slice.
#   2  not measured: no task folder or slice id given, no IMPLEMENTATION_PLAN.md, no
#      `## Slices`, the slice is not in it, it declares no `Depends-on:`, the value carries
#      prose, or no slice in the plan carries a `Status:` field. The chain continues and
#      records the reason; a caller that reads only the exit code cannot take it for clean.
#   3  a Depends-on id names no slice in `## Slices`. Route: implementation-plan, to fix the
#      Depends-on line; no closure can satisfy it. Checked after the no-Status test, so a
#      legacy plan with no Status: fields is not measured rather than refused.
#
# Usage:
#   scripts/check-slice-order.sh <task-folder> <slice-id>
#
# Summary line (the last line):
#   Slice-order: clean (<slice> depends on <ids>; each is closed in the plan)
#   Slice-order: <dep> is not closed (<slice> depends on it; plan Status: <value>). ...
#   Slice-order: <dep> is not a slice in IMPLEMENTATION_PLAN.md ## Slices (...). ...
#   Slice-order: not measured (<reason>)
#
# Deterministic: it reads one file and writes nothing. It derives no path from its own
# location, so an installed copy runs the same way. Portable to macOS bash 3.2 and BWK awk.

set -euo pipefail

FOLDER="${1:-}"
SLICE="${2:-}"

case "$FOLDER" in
  -h|--help) sed -n '2,60p' "$0"; exit 0 ;;
esac

if [ -z "$FOLDER" ] || [ -z "$SLICE" ]; then
  echo "Slice-order: not measured (usage: check-slice-order.sh <task-folder> <slice-id>)"
  exit 2
fi

PLAN="$FOLDER/IMPLEMENTATION_PLAN.md"
if [ ! -f "$PLAN" ]; then
  echo "Slice-order: not measured (no IMPLEMENTATION_PLAN.md found in $FOLDER)"
  exit 2
fi

# Dash characters built from bytes, so this file carries none of them literally.
EMDASH="$(printf '\342\200\224')"
ENDASH="$(printf '\342\200\223')"

# One awk pass over the plan. For the target slice it prints:
#   TARGET<TAB><raw id>
#   NOSTATUS                                   (no slice carries a Status: field)
#   PROSE<TAB><words that are not slice ids>
#   DEP<TAB><normalized id><TAB><display id><TAB><found 0|1><TAB><plan status>
# or one NOTMEASURED<TAB><reason> line.
read -r -d '' AWK_PROG <<'AWK_END' || true
function trim(s) { sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s }

# The slice id at the start of s, in its original case: `Slice 1`, `slice-01`, `S4b`, `H1`,
# `M1.1`, `3`. Returns s itself when it starts with no id.
function leadid(s) {
  s = trim(s)
  gsub(/[`*]/, "", s)
  if (match(s, /^([Ss][Ll][Ii][Cc][Ee][ \t_-]*)?[A-Za-z]*[0-9]+(\.[0-9]+)*[A-Za-z]?/))
    return substr(s, RSTART, RLENGTH)
  return s
}

# `Slice 01`, `slice-1`, `S01`, `01` and `1` all normalize to `1`; `P01` to `p1`.
function norm(s,   pre, rest) {
  s = tolower(s)
  gsub(/[ \t`*"']/, "", s)
  sub(/[.,;:]+$/, "", s)
  if (s ~ /^slice/) { s = substr(s, 6); sub(/^[_-]+/, "", s) }
  if (s ~ /^s[0-9]/) s = substr(s, 2)
  match(s, /^[a-z]*/)
  pre = substr(s, 1, RLENGTH); rest = substr(s, RLENGTH + 1)
  if (rest ~ /^[0-9]/) {
    sub(/^0+/, "", rest)
    if (rest !~ /^[0-9]/) rest = "0" rest
  }
  return pre rest
}

function fieldval(l,   p, v) {
  p = index(l, ":")
  if (p == 0) return ""
  v = substr(l, p + 1)
  gsub(/^[ \t*`]+/, "", v)
  return trim(v)
}

# Split s into id-shaped tokens in ids[1..n]; words that are not ids go to the global `prose`.
# `Slice 1`, `Slices 1`, `Slice S1` and `slice-1` become `S1` before `-` turns into a
# separator. With rng set, a range `S1-S3` or `1-3` (no spaces, same prefix) adds every id in it.
function idtokens(s, ids, rng,   n, i, j, k, m, tok, toks, pa, pre, pb, a, b) {
  gsub(/[Ss][Ll][Ii][Cc][Ee][Ss]?[ \t_-]*[Ss]?/, "S", s)
  gsub(endash, "-", s)
  gsub(/[,;\/+&]/, " ", s)
  gsub(emdash, " ", s)
  n = split(s, toks, /[ \t]+/)
  prose = ""; k = 0
  for (i = 1; i <= n; i++) {
    tok = toks[i]
    sub(/^[.:]+/, "", tok)
    sub(/[.:]+$/, "", tok)
    m = split(tok, pa, "-")
    if (rng && m == 2 && pa[1] ~ /^[A-Za-z]*[0-9]+$/ && pa[2] ~ /^[A-Za-z]*[0-9]+$/) {
      match(pa[1], /^[A-Za-z]*/); pre = substr(pa[1], 1, RLENGTH); a = substr(pa[1], RLENGTH + 1) + 0
      match(pa[2], /^[A-Za-z]*/); pb = tolower(substr(pa[2], 1, RLENGTH)); b = substr(pa[2], RLENGTH + 1) + 0
      # `S1-3` and `1-S3` keep one prefix; `S` and no prefix are the same slice namespace.
      if ((pb == "" || pb == tolower(pre) || (pb == "s" && pre == "")) && a < b) {
        if (b - a > 50) { prose = prose (prose == "" ? "" : " ") tok; continue }
        for (j = a; j <= b; j++) ids[++k] = pre j
        continue
      }
    }
    for (j = 1; j <= m; j++) {
      tok = pa[j]
      sub(/^[.:]+/, "", tok)
      sub(/[.:]+$/, "", tok)
      if (tok == "" || tolower(tok) == "and") continue
      if (tok ~ /^[A-Za-z]*[0-9]+(\.[0-9]+)*[A-Za-z]?$/) ids[++k] = tok
      else prose = prose (prose == "" ? "" : " ") tok
    }
  }
  return k
}

# A slice's own heading id, else an alias another heading carries, else "".
function resolve(d) {
  if (d in status) return d
  if (d in alias) return alias[d]
  return ""
}

function isfield(ll, name) {
  return (ll ~ ("^([-*][ \t]*)?[*]*" name "[*]*[ \t]*:"))
}

# A field line (`- Status: x`, `**Scope:** y`) ends a Depends-on list written under its label.
function anyfield(ll) {
  return (ll ~ /^([-*][ \t]*)?[*]*[a-z][a-z -]*[*]*[ \t]*:/)
}

function flush(   b, n, lines, i, l, ll, st, dep, hasdep, coll) {
  if (!insl) return
  insl = 0
  b = body
  gsub(/\n[ \t]+/, " ", b)
  n = split(b, lines, "\n")
  st = ""; dep = ""; hasdep = 0; coll = 0
  for (i = 1; i <= n; i++) {
    l = trim(lines[i]); ll = tolower(l)
    if (coll) {
      if (anyfield(ll) || (l == "" && dep != "")) coll = 0
      else { sub(/^[-*+][ \t]*/, "", l); if (l != "") dep = dep (dep == "" ? "" : ", ") l; continue }
    }
    if (st == "" && isfield(ll, "status")) st = fieldval(l)
    else if (!hasdep && isfield(ll, "depends-on")) { hasdep = 1; dep = fieldval(l); coll = (dep == "") }
  }
  if (st != "") nstatus++
  if (!(cid in status)) {
    status[cid] = st
    rawid[cid] = craw
    deps[cid] = dep
    hdeps[cid] = hasdep
  }
}

/^## / {
  flush()
  inslices = ($0 ~ /^## Slices/) ? 1 : 0
  if (inslices) sawslices = 1
  next
}
inslices && /^### / {
  flush()
  h = trim(substr($0, 5))
  craw = leadid(h)
  cid = norm(craw)
  p = index(h, ":")
  na = idtokens((p > 1) ? substr(h, 1, p - 1) : h, aid, 0)
  for (i = 1; i <= na; i++) { a = norm(aid[i]); if (a != cid && !(a in alias)) alias[a] = cid }
  insl = 1
  body = ""
  next
}
insl { body = body "\n" $0 }

END {
  flush()
  if (!sawslices) { print "NOTMEASURED\tno ## Slices section in IMPLEMENTATION_PLAN.md"; exit }
  t = resolve(norm(leadid(target)))
  if (t == "") { print "NOTMEASURED\tno slice " target " in IMPLEMENTATION_PLAN.md ## Slices"; exit }
  if (!hdeps[t]) { print "NOTMEASURED\t" rawid[t] " declares no Depends-on:"; exit }
  print "TARGET\t" rawid[t]
  if (nstatus == 0) print "NOSTATUS"
  v = deps[t]
  gsub(/\([^)]*\)/, "", v)
  gsub(/[`*]/, "", v)
  v = trim(v)
  lv = tolower(v)
  if (lv == "" || lv ~ /^(none|nenhum|n\/a)([^a-z]|$)/) exit
  if (lv ~ ("^(-|" emdash "|" endash ")[ \t.]*$")) exit
  n = idtokens(v, dids, 1)
  if (prose != "") { print "PROSE\t" prose; exit }
  for (i = 1; i <= n; i++) {
    d = resolve(norm(dids[i]))
    if (d != "") print "DEP\t" d "\t" rawid[d] "\t1\t" status[d]
    else         print "DEP\t" norm(dids[i]) "\t" dids[i] "\t0\t"
  }
}
AWK_END

PARSED="$(awk -v target="$SLICE" -v emdash="$EMDASH" -v endash="$ENDASH" "$AWK_PROG" "$PLAN")"

NM="$(printf '%s\n' "$PARSED" | grep '^NOTMEASURED' || true)"
if [ -n "$NM" ]; then
  echo "Slice-order: not measured ($(printf '%s' "$NM" | head -1 | cut -f2))"
  exit 2
fi

TARGET_RAW="$(printf '%s\n' "$PARSED" | grep '^TARGET' | head -1 | cut -f2)"

PROSE="$(printf '%s\n' "$PARSED" | grep '^PROSE' || true)"
if [ -n "$PROSE" ]; then
  echo "Slice-order: not measured ($TARGET_RAW Depends-on: carries words that are not slice ids: $(printf '%s' "$PROSE" | head -1 | cut -f2))"
  exit 2
fi

DEPS="$(printf '%s\n' "$PARSED" | grep '^DEP' || true)"
if [ -z "$DEPS" ]; then
  echo "Slice-order: clean ($TARGET_RAW depends on none)"
  exit 0
fi

if printf '%s\n' "$PARSED" | grep -q '^NOSTATUS'; then
  echo "Slice-order: not measured (no slice in IMPLEMENTATION_PLAN.md ## Slices carries a Status: field)"
  exit 2
fi

# A Depends-on id that names no slice is a plan defect, reported before any closure.
TAB="$(printf '\t')"
while IFS="$TAB" read -r _ id raw found pstatus; do
  [ -n "$id" ] || continue
  if [ "$found" = "0" ]; then
    echo "Slice-order: $raw is not a slice in IMPLEMENTATION_PLAN.md ## Slices ($TARGET_RAW depends on it). Fix the Depends-on line through implementation-plan."
    exit 3
  fi
done <<EOF
$DEPS
EOF

CLOSED_LIST=""
while IFS="$TAB" read -r _ id raw found pstatus; do
  [ -n "$id" ] || continue
  lower="$(printf '%s' "$pstatus" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    closed*|done|'done '*|'done('*) echo "  $raw: closed (IMPLEMENTATION_PLAN.md Status: $pstatus)"
             CLOSED_LIST="${CLOSED_LIST:+$CLOSED_LIST, }$raw"; continue ;;
  esac
  echo "Slice-order: $raw is not closed ($TARGET_RAW depends on it; plan Status: ${pstatus:-none}). Run slice-closure for $raw before starting $TARGET_RAW."
  exit 1
done <<EOF
$DEPS
EOF

echo "Slice-order: clean ($TARGET_RAW depends on $CLOSED_LIST; each is closed in the plan)"
exit 0
