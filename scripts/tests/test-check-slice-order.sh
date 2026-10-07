#!/usr/bin/env bash
# test-check-slice-order.sh: does check-slice-order.sh refuse what it should, and only that?
#
# The gate runs before every slice (ADR-0244, P-7, P-11), so both failure directions cost:
# a parse that drops an id passes an open dependency, and a parse that misreads a legitimate
# plan refuses a slice for nothing. The 2026-09-30 review found both (SF-1: `S1 S2`, `S1/S2`,
# `S1-S2` passed with S2 open; SF-2: `nenhum` and `slice-1` were refused). Each separator form
# below therefore runs with its SECOND id open, so a parser that keeps only the first id fails
# the check instead of passing it.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${SCRIPT_DIR}/../check-slice-order.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

[ -f "$CHECKER" ] || { echo "  FAIL checker not found at $CHECKER"; exit 1; }

# make_plan <slug> <slices>; echoes the task folder.
make_plan() {
  local d="$TMP/$1"
  mkdir -p "$d"
  printf '# Implementation plan\n\n## Slices\n\n%s\n\n## Approval log\n- none\n' "$2" > "$d/IMPLEMENTATION_PLAN.md"
  echo "$d"
}

# sl <heading id> <depends-on value> <status value>; an empty status omits the field.
sl() {
  printf '### %s: demo slice\n- Scope: one file\n- Depends-on: %s\n' "$1" "$2"
  [ -n "$3" ] && printf -- '- Status: %s\n' "$3"
  printf -- '- Exit criterion: WHEN it lands the gate SHALL pass\n\n'
}

OUT=""; CODE=0
run() { OUT="$(bash "$CHECKER" "$1" "$2" 2>&1)"; CODE=$?; }

expect() {  # expect <folder> <slice> <code> <grep pattern or empty> <label>
  run "$1" "$2"
  if [ "$CODE" = "$3" ] && { [ -z "$4" ] || printf '%s\n' "$OUT" | tail -1 | grep -q -- "$4"; }; then
    pass "$5"
  else
    fail "$5 (exit $CODE, expected $3): $(printf '%s' "$OUT" | tail -1)"
  fi
}

S1_CLOSED="$(sl S1 none 'closed (inline; commit abc1234)')"
S2_OPEN="$(sl S2 none planned)"
S2_CLOSED="$(sl S2 none closed)"

# --- every separator form, second id open ------------------------------------------
n=1
for dep in 'S1, S2' 'S1 S2' 'S1 and S2' 'S1 AND S2' 'S1/S2' 'S1 + S2' 'S1 & S2' 'S1; S2' 'S1-S2'; do
  d="$(make_plan "sep$n" "$S1_CLOSED
$S2_OPEN
$(sl S3 "$dep" planned)")"
  expect "$d" S3 1 "S2 is not closed" "sep $n. Depends-on: $dep with S2 open exits 1 naming S2"
  n=$((n + 1))
done

d="$(make_plan sepclean "$S1_CLOSED
$S2_CLOSED
$(sl S3 'S1 AND S2' planned)")"
expect "$d" S3 0 "clean (S3 depends on S1, S2" "sep control. both ids closed exits 0 and lists both"

# A bulleted multi-line value joins into one line.
d="$(make_plan bullets "$S1_CLOSED
$S2_OPEN
### S3: demo slice
- Scope: one file
- Depends-on:
  - S1
  - S2
- Status: planned
")"
expect "$d" S3 1 "S2 is not closed" "sep bullets. a bulleted multi-line Depends-on reads both ids"

# --- ranges and lists under the label (review S4b SF-B): the middle or listed id is open --
S3_CLOSED="$(sl S3 none closed)"
ENDASH="$(printf '\342\200\223')"
n=1
for dep in 'S1-S3' '1-3' 'Slices 1-3' 'S1-3' "S1${ENDASH}S3" 'S01-S03'; do
  d="$(make_plan "range$n" "$S1_CLOSED
$S2_OPEN
$S3_CLOSED
$(sl S4 "$dep" planned)")"
  expect "$d" S4 1 "S2 is not closed" "range $n. Depends-on: $dep with S2 open exits 1 naming S2"
  n=$((n + 1))
done

d="$(make_plan rangeclean "$S1_CLOSED
$S2_CLOSED
$S3_CLOSED
$(sl S4 'S1-S3' planned)")"
expect "$d" S4 0 "depends on S1, S2, S3;" "range control. S1-S3 all closed exits 0 and lists S1, S2, S3"

d="$(make_plan flat1 "$S1_CLOSED
$S2_OPEN
### S3: demo slice
- Depends-on:
- S1
- S2
- Status: planned
")"
expect "$d" S3 1 "S2 is not closed" "flat 1. '- Depends-on:' then '- S1' and '- S2', not indented, reads both ids"

d="$(make_plan flat2 "$S1_CLOSED
$S2_OPEN
### S3: demo slice
Depends-on:
S1
S2

Status: planned
")"
expect "$d" S3 1 "S2 is not closed" "flat 2. a bare 'Depends-on:' then 'S1' and 'S2' lines reads both ids"

d="$(make_plan flat3 "$(sl 'Slice 1' none planned)
### Slice 2: demo slice
- Depends-on:
- Slice 1
- Status: planned
")"
expect "$d" 'Slice 2' 1 "Slice 1 is not closed" "flat 3. '- Depends-on:' then '- Slice 1' (archived plan form) reads Slice 1"

d="$(make_plan flatnone "$S2_OPEN
### S3: demo slice
- Depends-on:
- Status: planned
")"
expect "$d" S3 0 "depends on none" "flat control. an empty Depends-on followed by a field means none"

# --- no dependency forms ---------------------------------------------------------------
EMDASH="$(printf '\342\200\224')"
n=1
for dep in none 'none (first slice)' nenhum 'nenhum.' 'n/a' 'N/A' '-' "$EMDASH" ''; do
  d="$(make_plan "none$n" "$S2_OPEN
$(sl S3 "$dep" planned)")"
  expect "$d" S3 0 "depends on none" "none $n. Depends-on: '$dep' means no dependency"
  n=$((n + 1))
done

# --- id forms --------------------------------------------------------------------------
SLICE1_CLOSED="$(sl 'Slice 1' none closed)"
SLICE1_OPEN="$(sl 'Slice 1' none planned)"
n=1
for dep in 'slice-1 (the schema)' 'Slice 1' 'S1' 'S01' '1' '01' 'Slice 01.'; do
  d="$(make_plan "id$n" "$SLICE1_CLOSED
$(sl 'Slice 2' "$dep" planned)")"
  expect "$d" 'Slice 2' 0 "clean" "id $n. '$dep' matches heading ### Slice 1 (closed)"
  d="$(make_plan "idopen$n" "$SLICE1_OPEN
$(sl 'Slice 2' "$dep" planned)")"
  expect "$d" 'Slice 2' 1 "Slice 1 is not closed" "id $n. '$dep' matches heading ### Slice 1 (open)"
  n=$((n + 1))
done

d="$(make_plan idheadS "$(sl S1 none planned)
$(sl S2 'Slice 1' planned)")"
expect "$d" 2 1 "S1 is not closed" "id S. 'Slice 1' matches heading ### S1, and target '2' matches S2"

# `### Slice S1` headings (review S4b SF-C): `Depends-on: S1` and target `S2` resolve.
d="$(make_plan idsliceS "$(sl 'Slice S1' none planned)
$(sl 'Slice S2' 'S1' planned)")"
expect "$d" S2 1 "Slice S1 is not closed" "id Slice S 1. heading ### Slice S1 answers to S1 (open), target S2 resolves"
d="$(make_plan idsliceS2 "$(sl 'Slice S1' none closed)
$(sl 'Slice S2' 'Slice S1' planned)")"
expect "$d" 'Slice S2' 0 "clean" "id Slice S 2. heading ### Slice S1 answers to 'Slice S1' (closed)"

d="$(make_plan idletter "$(sl H1 none closed)
$(sl P01 none planned)
$(sl M1.1 none closed)
$(sl S4b none closed)
$(sl S5 'H1, M1.1, S4b, P1' planned)")"
expect "$d" S5 1 "P01 is not closed" "id letters. H1, M1.1 and S4b resolve, P1 matches heading P01"

# A heading `### Slice 3 - P14.5: ...` answers to both ids; its own id still wins.
d="$(make_plan idalias "$(sl 'Slice 1 - A1' none closed)
$(sl 'Slice 2 - A2' none planned)
$(sl 'Slice 3 - A3' 'A1, A2' planned)")"
expect "$d" 'Slice 3' 1 "Slice 2 is not closed" "id alias 1. A2 resolves through the heading ### Slice 2 - A2"
expect "$d" A3 1 "is not closed" "id alias 2. the target A3 resolves through its heading alias"
d="$(make_plan idalias2 "$(sl 'Slice 1 - S2' none closed)
$(sl S2 none planned)
$(sl S3 S2 planned)")"
expect "$d" S3 1 "S2 is not closed" "id alias 3. a slice's own id wins over another heading's alias"

# --- plan Status is the only record (P-11) --------------------------------------------
d="$(make_plan notes "$S1_CLOSED
$S2_OPEN
$(sl S3 'S1, S2' planned)")"
mkdir -p "$d/SLICES"; printf '# S2\nStatus: closed\n' > "$d/SLICES/02_demo.md"
expect "$d" S3 1 "S2 is not closed" "record 1. a closed slice note does not close a planned plan slice"

d="$(make_plan followups "$S1_CLOSED
$(sl S2 none closed-with-followups)
$(sl S3 'S1, S2' planned)")"
expect "$d" S3 0 "clean" "record 2. closed-with-followups counts as closed"

d="$(make_plan notready "$S1_CLOSED
$(sl S2 none not-ready)
$(sl S3 'S1, S2' planned)")"
expect "$d" S3 1 "plan Status: not-ready" "record 3. not-ready is not closed"

d="$(make_plan reopened "$S1_CLOSED
$(sl S2 none 'not-ready (material follow-up reopens S2)')
$(sl S3 'S1, S2' planned)")"
expect "$d" S3 1 "S2 is not closed" "record 5. a slice a material follow-up reopened (not-ready) refuses its dependents (SF-F)"

d="$(make_plan done "$(sl S1 none done)
$(sl S2 none 'done (commits 1d19d58, 2886b6a; PR #1)')
$(sl S3 'S1, S2' planned)")"
expect "$d" S3 0 "clean" "record 6. done and done (...) count as closed, for plans written before P-11 (final review SF-1)"

d="$(make_plan donenot "$S1_CLOSED
$(sl S2 none 'done-ish, pending review')
$(sl S3 'S1, S2' planned)")"
expect "$d" S3 1 "S2 is not closed" "record 7. a value that only starts with the letters done is not closed"

d="$(make_plan donespace "$(sl S1 none 'DONE 2026-07-06 (wave 2)')
$(sl S2 none closed)
$(sl S3 'S1, S2' planned)")"
expect "$d" S3 0 "clean" "record 7b. done followed by a space, in any case, counts as closed"

d="$(make_plan bold "### S1: demo slice
- **Depends-on:** none
- **Status:** closed
$(sl S2 S1 planned)")"
expect "$d" S2 0 "clean" "record 4. a bold **Status:** closed is read"

# --- open, closed, and a non-dependency ------------------------------------------------
d="$(make_plan opendep "$(sl S1 none planned)
$(sl S2 S1 planned)")"
expect "$d" S2 1 "Run slice-closure for S1" "gate 1. an open dependency exits 1 and routes to slice-closure"

d="$(make_plan closeddep "$S1_CLOSED
$(sl S2 S1 planned)")"
expect "$d" S2 0 "each is closed in the plan" "gate 2. a closed dependency exits 0"

d="$(make_plan nondep "$S1_CLOSED
$S2_OPEN
$(sl S3 S1 planned)")"
expect "$d" S3 0 "clean" "gate 3. an open slice outside Depends-on does not refuse (wave siblings)"

# --- not measured and plan defects ------------------------------------------------------
d="$(make_plan nostatus "$(sl S1 none '')
$(sl S2 S1 '')")"
expect "$d" S2 2 "carries a Status: field" "measure 1. a plan with no Status: fields exits 2"

d="$(make_plan prose "$S1_CLOSED
$(sl S2 'S1 once the schema lands' planned)")"
expect "$d" S2 2 "not slice ids" "measure 2. a Depends-on carrying prose exits 2, never 0"

d="$(make_plan unknown "$S1_CLOSED
$(sl S2 'S1, S7' planned)")"
expect "$d" S2 3 "S7 is not a slice" "measure 3. an id naming no slice exits 3 and routes to implementation-plan"

d="$(make_plan unknownlegacy "$(sl S1 none '')
$(sl S2 'S1, S7' '')")"
expect "$d" S2 2 "carries a Status: field" "measure 3b. a legacy plan with no Status: fields and a stale id exits 2, not 3"

d="$(make_plan nodep "### S1: demo
- Status: planned
")"
expect "$d" S1 2 "declares no Depends-on" "measure 4. a slice with no Depends-on: exits 2"

d="$(make_plan missing "$S1_CLOSED")"
expect "$d" S9 2 "no slice S9" "measure 5. an unknown target slice exits 2"

expect "$TMP/nowhere" S1 2 "no IMPLEMENTATION_PLAN.md" "measure 6. a folder with no plan exits 2"

OUT="$(bash "$CHECKER" 2>&1)"; CODE=$?
[ "$CODE" = "2" ] && pass "measure 7. no arguments exits 2" || fail "measure 7. no arguments exited $CODE"

echo
echo "check-slice-order: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
