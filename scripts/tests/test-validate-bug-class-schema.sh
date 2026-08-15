#!/usr/bin/env bash
# test-validate-bug-class-schema.sh -- mutation pins for the bug-class shape
# checker. Run from anywhere:
#   bash scripts/tests/test-validate-bug-class-schema.sh
#
# validate-bug-class-schema.sh is advisory by contract: it always exits 0 and
# its only product is a count line. That is the easy kind of script to break
# silently, because a reverted check does not fail a build, it just reports a
# nicer number. So every check below is a mutation: take a tree that scores X,
# introduce exactly one defect, and assert the score moved the way that defect
# should move it.
#
# Three rules the checks follow.
#
# Deltas, not absolutes. Each mutation is measured against a reference run of
# the SAME validator over the SAME tree plus one synthetic fixture, so a check
# does not break the day someone adds a bug class. The single absolute pin is
# check 1, kept on purpose so a change in the real catalog's shape health shows
# up here instead of drifting quietly.
#
# Fences are load-bearing. A `## ` line inside a fenced code block is sample
# text, not a heading, and checks 17 to 24 pin that for all three of the
# validator's checks (required-section presence, the hollow body scan and its
# section boundary, and the out-of-schema advisory). Check 24 pins the other
# direction: a fence has to close, or the filter would swallow every heading
# after the first code block in the file.
#
# The real tree is read-only. Every mutation runs against a copy under a temp
# path, passed as the validator's optional <dir> argument.
#
# Harness note, learned the hard way: `printf '%s\n' "$out" | grep -q X` is not
# usable under `set -o pipefail`. grep -q exits at the first match, printf takes
# SIGPIPE, and the pipeline reports 141 even though the pattern matched. That
# produced four false failures while this suite was being written. Validator
# output is captured into a variable and tested with the pipe-free `contains`.
#
# WOS_BUG_CLASS_VALIDATOR overrides the script under test. It exists for the
# falsifiability run: point the suite at a copy with a check reverted and it has
# to go red, or the suite is not evidence of anything.
#
# bash 3.2 compatible: no associative arrays, no mapfile, no readarray.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VALIDATOR="${WOS_BUG_CLASS_VALIDATOR:-$SCRIPT_DIR/../validate-bug-class-schema.sh}"
REAL_DIR="$REPO_ROOT/wos/bug-classes"

# The recorded shape health of wos/bug-classes as measured on 2026-08-13, after
# the last twelve templates were converted to the canonical schema (909d352).
# Check 1 pins these so a catalog-wide shape change (or a reverted validator
# check) is visible. Update them deliberately, never to make a red suite green.
BASE_CONF=81
BASE_NON=0
BASE_SCAN=81
# 12 before the conversion, 13 before the fence filter landed. Zero is a
# stronger assertion than either: any template regressing to a legacy section
# schema, or any new one added with an out-of-schema heading, turns this red.
BASE_EXTRA=0

FIXTURE_NAME='zz-schema-fixture.md'

fails=0
checks=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); echo "  FAIL $1"; fails=$((fails+1)); }

if [ ! -d "$REAL_DIR" ]; then
  echo "test-validate-bug-class-schema: no such directory: $REAL_DIR" >&2
  exit 2
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# ---------------------------------------------------------------- helpers ---

# Substring test with no pipeline. See the harness note above for why grep is
# not used here.
contains() {
  case "$1" in
    *"$2"*) return 0 ;;
    *)      return 1 ;;
  esac
}

# run_validator <dir>: sets V_OUT plus the five counts. --verbose is always on
# because several checks read the per-file reason lines, and the summary line
# is identical either way.
V_OUT=''; V_CONF=0; V_NON=0; V_SCAN=0; V_EXTRA=0; V_FM=0
run_validator() {
  local dir="$1" nums
  V_OUT="$(bash "$VALIDATOR" --verbose "$dir" 2>&1)"
  nums="$(printf '%s\n' "$V_OUT" | sed -n 's/^BUG-CLASS-SCHEMA: \([0-9][0-9]*\) conforming \/ \([0-9][0-9]*\) non-conforming \/ \([0-9][0-9]*\) scanned (advisory; \([0-9][0-9]*\) with out-of-schema sections, \([0-9][0-9]*\) with non-canonical frontmatter keys)$/\1 \2 \3 \4 \5/p')"
  if [ -z "$nums" ]; then
    # An unparseable summary is a harness failure, not a check failure: every
    # delta below would silently compare zeroes.
    echo "test-validate-bug-class-schema: summary line unparseable for $dir" >&2
    printf '%s\n' "$V_OUT" >&2
    exit 2
  fi
  set -- $nums
  V_CONF=$1; V_NON=$2; V_SCAN=$3; V_EXTRA=$4; V_FM=$5
}

# fixture_base <path>: a synthetic template that conforms on every axis, so any
# single mutation below is the only thing moving the counts. Deliberately built
# rather than copied from a real bug class, which could gain a stray heading or
# key later and turn one of these checks into a false failure.
fixture_base() {
  cat > "$1" <<'EOF'
---
name: zz-schema-fixture
category: correctness
default-severity: MEDIUM
cwe: CWE-000
languages: any
file-patterns: any
perspectives: none
reversibility-check: none
---

# zz-schema-fixture

## Trigger

Synthetic trigger body.

## Detection

Synthetic detection body.

## Retrieval

Synthetic retrieval body.

## Analysis prompt

Synthetic analysis body.

## Severity rubric

Synthetic rubric body.

## Confidence factors

Synthetic confidence body.

## Examples

Synthetic example body.
EOF
}

# drop_heading <file> <heading>: remove the heading line and leave its body
# attached to the section above. This is what a lost required heading looks
# like in practice, and it keeps the file's word count roughly intact so the
# only signal that moved is the section count.
drop_heading() {
  grep -v "^## ${2}\$" "$1" > "$1.tmp" && mv "$1.tmp" "$1"
}

# drop_section <file> <heading>: remove the heading and its body.
drop_section() {
  awk -v sec="## $2" '
    $0 == sec       { skip = 1; next }
    skip && /^## /  { skip = 0 }
    skip            { next }
                    { print }
  ' "$1" > "$1.tmp" && mv "$1.tmp" "$1"
}

# hollow_section <file> <heading>: keep the heading, drop the body. The
# dispatchable-but-empty template the validator's body check exists for.
hollow_section() {
  awk -v sec="## $2" '
    $0 == sec       { print; print ""; skip = 1; next }
    skip && /^## /  { skip = 0 }
    skip            { next }
                    { print }
  ' "$1" > "$1.tmp" && mv "$1.tmp" "$1"
}

# blank_section <file> <heading>: body of spaces, tabs and blank lines. Visually
# non-empty in an editor, semantically nothing for the sweep to dispatch.
blank_section() {
  awk -v sec="## $2" '
    $0 == sec       { print; printf "   \n\n\t\n"; skip = 1; next }
    skip && /^## /  { skip = 0 }
    skip            { next }
                    { print }
  ' "$1" > "$1.tmp" && mv "$1.tmp" "$1"
}

# add_fm_key <file> <literal line>: insert a line directly under the opening
# frontmatter delimiter.
add_fm_key() {
  awk -v line="$2" 'NR == 1 { print; print line; next } { print }' "$1" > "$1.tmp" \
    && mv "$1.tmp" "$1"
}

# fence_block <file> <open> <close> <heading>: append a fenced code block whose
# only heading-shaped line is <heading>, plus a non-empty line after it so the
# body scan has something to latch onto if the fence is ignored. The open and
# close markers are passed literally, which is what lets one helper cover the
# backtick, tilde and indented forms.
fence_block() {
  printf '\n%s\n%s\n\nFenced sample body.\n%s\n' "$2" "$4" "$3" >> "$1"
}

# ------------------------------------------------------- 1. control + pin ---

run_validator "$REAL_DIR"
REAL_CONF=$V_CONF; REAL_NON=$V_NON; REAL_SCAN=$V_SCAN; REAL_EXTRA=$V_EXTRA; REAL_FM=$V_FM

cp -R "$REAL_DIR" "$WORK/pristine"
run_validator "$WORK/pristine"

if [ "$V_CONF" = "$REAL_CONF" ] && [ "$V_NON" = "$REAL_NON" ] && \
   [ "$V_SCAN" = "$REAL_SCAN" ] && [ "$V_EXTRA" = "$REAL_EXTRA" ] && \
   [ "$V_FM" = "$REAL_FM" ] && \
   [ "$REAL_CONF" = "$BASE_CONF" ] && [ "$REAL_NON" = "$BASE_NON" ] && \
   [ "$REAL_SCAN" = "$BASE_SCAN" ] && [ "$REAL_EXTRA" = "$BASE_EXTRA" ]; then
  pass "1  control: copy scores as the real tree, and both hold the recorded baseline"
else
  fail "1  control: copy=${V_CONF}/${V_NON}/${V_SCAN}/${V_EXTRA}/${V_FM} real=${REAL_CONF}/${REAL_NON}/${REAL_SCAN}/${REAL_EXTRA}/${REAL_FM} baseline=${BASE_CONF}/${BASE_NON}/${BASE_SCAN}/${BASE_EXTRA}"
fi

PRISTINE_SCAN=$V_SCAN

# --------------------------------------------------------- reference tree ---
# Pristine catalog plus one conforming synthetic fixture. Every mutation below
# rewrites that one file and is scored against this run, so a delta of exactly
# one is attributable to the mutation and nothing else.

cp -R "$WORK/pristine" "$WORK/case"
CASE_DIR="$WORK/case"
FIXTURE="$CASE_DIR/$FIXTURE_NAME"

fixture_base "$FIXTURE"
run_validator "$CASE_DIR"
# Only the three the delta checks below actually read. The non-conforming count
# is pinned absolutely by check 1, and conforming plus non-conforming equals
# scanned by construction, so a per-run reference for it would assert nothing.
REF_CONF=$V_CONF; REF_EXTRA=$V_EXTRA; REF_FM=$V_FM

if [ "$REF_CONF" -ne $((REAL_CONF + 1)) ]; then
  echo "test-validate-bug-class-schema: the synthetic fixture is not conforming" >&2
  printf '%s\n' "$V_OUT" >&2
  exit 2
fi

# ------------------------------------- 2, 3. a required heading goes missing --

fixture_base "$FIXTURE"
drop_heading "$FIXTURE" 'Detection'
run_validator "$CASE_DIR"

[ "$V_CONF" -eq $((REF_CONF - 1)) ] \
  && pass "2  missing '## Detection' drops conforming by 1 (${REF_CONF} -> ${V_CONF})" \
  || fail "2  missing '## Detection' did not drop conforming (${REF_CONF} -> ${V_CONF})"

if contains "$V_OUT" "${FIXTURE_NAME}: 6/7 sections present, Detection"; then
  pass "3  --verbose names the missing section"
else
  fail "3  --verbose did not name the missing section"
fi

# ------------------------------- 4, 5. '## Analysis prompt' loses its body ---
# Presence alone would let this pass, and the sweep would then dispatch a
# prompt with nothing in it and report clean.

fixture_base "$FIXTURE"
hollow_section "$FIXTURE" 'Analysis prompt'
run_validator "$CASE_DIR"

[ "$V_CONF" -eq $((REF_CONF - 1)) ] \
  && pass "4  hollow '## Analysis prompt' drops conforming by 1 (${REF_CONF} -> ${V_CONF})" \
  || fail "4  hollow '## Analysis prompt' did not drop conforming (${REF_CONF} -> ${V_CONF})"

# 7/7 plus the "empty:" prefix is what separates a hollow body from a missing
# heading. A bare section list here would mean the two failures got conflated.
if contains "$V_OUT" "${FIXTURE_NAME}: 7/7 sections present, empty: Analysis prompt"; then
  pass "5  hollow reason reads 'empty:', not a missing-section list"
else
  fail "5  hollow reason did not read as 'empty:' with all 7 sections present"
fi

# ------------------------------------- 6, 7. '## Retrieval' loses its body ---

fixture_base "$FIXTURE"
hollow_section "$FIXTURE" 'Retrieval'
run_validator "$CASE_DIR"

[ "$V_CONF" -eq $((REF_CONF - 1)) ] \
  && pass "6  hollow '## Retrieval' drops conforming by 1 (${REF_CONF} -> ${V_CONF})" \
  || fail "6  hollow '## Retrieval' did not drop conforming (${REF_CONF} -> ${V_CONF})"

if contains "$V_OUT" "${FIXTURE_NAME}: 7/7 sections present, empty: Retrieval"; then
  pass "7  hollow reason names Retrieval"
else
  fail "7  hollow reason did not name Retrieval"
fi

# --------------------------------- 8. whitespace-only body counts as hollow --

fixture_base "$FIXTURE"
blank_section "$FIXTURE" 'Retrieval'
run_validator "$CASE_DIR"

if [ "$V_CONF" -eq $((REF_CONF - 1)) ] \
   && contains "$V_OUT" "${FIXTURE_NAME}: 7/7 sections present, empty: Retrieval"; then
  pass "8  spaces, tabs and blank lines count as an empty body"
else
  fail "8  whitespace-only body passed as a real body (${REF_CONF} -> ${V_CONF})"
fi

# ------------------------- 9, 10. hollow section at EOF, no following heading --
# The awk body scan closes a section on the next '## ' line. A section that runs
# to EOF never sees one, so this is the case a naive implementation misses.

fixture_base "$FIXTURE"
drop_section "$FIXTURE" 'Retrieval'
printf '\n## Retrieval\n' >> "$FIXTURE"
run_validator "$CASE_DIR"

[ "$V_CONF" -eq $((REF_CONF - 1)) ] \
  && pass "9  hollow last section with no trailing heading is still caught" \
  || fail "9  hollow last section at EOF passed (${REF_CONF} -> ${V_CONF})"

if contains "$V_OUT" "${FIXTURE_NAME}: 7/7 sections present, empty: Retrieval"; then
  pass "10 the EOF case names the empty section"
else
  fail "10 the EOF case did not name the empty section"
fi

# ------------------------------- 11, 12, 13. non-canonical frontmatter keys ---
# YAML is case-sensitive, so `Priority:` is a different key from `priority:` and
# both are outside the canonical 8. A lowercase-anchored extraction reported the
# capitalised form as clean, which is the regression check 12 exists for.

fixture_base "$FIXTURE"
add_fm_key "$FIXTURE" 'priority: high'
run_validator "$CASE_DIR"
[ "$V_FM" -eq $((REF_FM + 1)) ] \
  && pass "11 lowercase stray key counts as non-canonical (${REF_FM} -> ${V_FM})" \
  || fail "11 lowercase stray key not counted (${REF_FM} -> ${V_FM})"

fixture_base "$FIXTURE"
add_fm_key "$FIXTURE" 'Priority: high'
run_validator "$CASE_DIR"
[ "$V_FM" -eq $((REF_FM + 1)) ] \
  && pass "12 capitalised stray key counts as non-canonical (${REF_FM} -> ${V_FM})" \
  || fail "12 capitalised stray key not counted (${REF_FM} -> ${V_FM})"

fixture_base "$FIXTURE"
add_fm_key "$FIXTURE" '  priority: high'
run_validator "$CASE_DIR"
[ "$V_FM" -eq $((REF_FM + 1)) ] \
  && pass "13 indented stray key counts as non-canonical (${REF_FM} -> ${V_FM})" \
  || fail "13 indented stray key not counted (${REF_FM} -> ${V_FM})"

# ------------------------------------ 14, 15. a heading outside the schema ---
# Reported on its own advisory line. Conflating it with conformance would make
# one stray heading read like a template the sweep cannot dispatch.

fixture_base "$FIXTURE"
printf '\n## Rollback plan\n\nSynthetic body.\n' >> "$FIXTURE"
run_validator "$CASE_DIR"

[ "$V_EXTRA" -eq $((REF_EXTRA + 1)) ] \
  && pass "14 out-of-schema heading counts as out-of-schema (${REF_EXTRA} -> ${V_EXTRA})" \
  || fail "14 out-of-schema heading not counted (${REF_EXTRA} -> ${V_EXTRA})"

[ "$V_CONF" -eq "$REF_CONF" ] \
  && pass "15 out-of-schema heading leaves conformance alone (${V_CONF})" \
  || fail "15 out-of-schema heading changed conformance (${REF_CONF} -> ${V_CONF})"

# ------------------------------------- 16. underscore-prefixed files skipped --
# _index.md and any future _-prefixed file are library plumbing, not templates.

md_total=0
for f in "$WORK/pristine"/*.md; do
  [ -e "$f" ] || continue
  md_total=$((md_total + 1))
done
md_under=0
for f in "$WORK/pristine"/_*.md; do
  [ -e "$f" ] || continue
  md_under=$((md_under + 1))
done

# The underscore count guards against a vacuous check: with none present the
# subtraction proves nothing.
if [ "$md_under" -ge 1 ] && [ "$PRISTINE_SCAN" -eq $((md_total - md_under)) ]; then
  pass "16 scanned (${PRISTINE_SCAN}) equals ${md_total} md files minus ${md_under} underscore-prefixed"
else
  fail "16 underscore skip wrong: scanned=${PRISTINE_SCAN} total=${md_total} underscore=${md_under}"
fi

# ------------------- 17, 18. a fenced heading does not satisfy presence ------
# The required heading is gone and only a sample copy of it survives inside a
# code block. Counting that copy would report a template as dispatchable when
# the section it needs is not there.

fixture_base "$FIXTURE"
drop_heading "$FIXTURE" 'Detection'
fence_block "$FIXTURE" '```markdown' '```' '## Detection'
run_validator "$CASE_DIR"

[ "$V_CONF" -eq $((REF_CONF - 1)) ] \
  && pass "17 fenced '## Detection' does not satisfy the presence check (${REF_CONF} -> ${V_CONF})" \
  || fail "17 fenced '## Detection' passed as the real heading (${REF_CONF} -> ${V_CONF})"

if contains "$V_OUT" "${FIXTURE_NAME}: 6/7 sections present, Detection"; then
  pass "18 the fenced-presence case still names Detection as missing"
else
  fail "18 the fenced-presence case did not name Detection as missing"
fi

# ------------ 19, 20. a fenced heading does not close or open a section ------
# The real '## Retrieval' is hollow. A sample copy of that exact line inside a
# later code block, with text under it, is enough to make a body scan that reads
# every '## ' line as a boundary believe the section has a body after all. This
# is the masking direction: the defect hides a real one, so it reports cleaner.

fixture_base "$FIXTURE"
hollow_section "$FIXTURE" 'Retrieval'
fence_block "$FIXTURE" '```markdown' '```' '## Retrieval'
run_validator "$CASE_DIR"

[ "$V_CONF" -eq $((REF_CONF - 1)) ] \
  && pass "19 a fenced '## Retrieval' does not mask the hollow real one (${REF_CONF} -> ${V_CONF})" \
  || fail "19 a fenced '## Retrieval' masked the hollow real one (${REF_CONF} -> ${V_CONF})"

if contains "$V_OUT" "${FIXTURE_NAME}: 7/7 sections present, empty: Retrieval"; then
  pass "20 the masking case still reports the real section as empty"
else
  fail "20 the masking case did not report the real section as empty"
fi

# ------------------- 21, 22, 23. fenced headings are not out-of-schema -------
# Same line, three fence forms. Tildes and up-to-three-space indentation are
# both CommonMark openers, so a filter that only knows bare backticks would pass
# 21 and fail the other two.

fixture_base "$FIXTURE"
fence_block "$FIXTURE" '```markdown' '```' '## Rollback plan'
run_validator "$CASE_DIR"
[ "$V_EXTRA" -eq "$REF_EXTRA" ] \
  && pass "21 backtick-fenced heading is not counted as out-of-schema (${REF_EXTRA} -> ${V_EXTRA})" \
  || fail "21 backtick-fenced heading counted as out-of-schema (${REF_EXTRA} -> ${V_EXTRA})"

fixture_base "$FIXTURE"
fence_block "$FIXTURE" '~~~markdown' '~~~' '## Rollback plan'
run_validator "$CASE_DIR"
[ "$V_EXTRA" -eq "$REF_EXTRA" ] \
  && pass "22 tilde-fenced heading is not counted as out-of-schema (${REF_EXTRA} -> ${V_EXTRA})" \
  || fail "22 tilde-fenced heading counted as out-of-schema (${REF_EXTRA} -> ${V_EXTRA})"

fixture_base "$FIXTURE"
fence_block "$FIXTURE" '   ```markdown' '   ```' '## Rollback plan'
run_validator "$CASE_DIR"
[ "$V_EXTRA" -eq "$REF_EXTRA" ] \
  && pass "23 indented fence is still a fence (${REF_EXTRA} -> ${V_EXTRA})" \
  || fail "23 indented fence was not read as a fence (${REF_EXTRA} -> ${V_EXTRA})"

# ---------------------------------------- 24. a fence closes ----------------
# The opposite failure to 21: a filter that never leaves fence state would drop
# every heading after the first code block, and the counts would look great.
# Both headings below are out-of-schema, and the advisory counts files, so the
# file count moves either way; the per-file list is what separates them.

fixture_base "$FIXTURE"
fence_block "$FIXTURE" '```markdown' '```' '## Fenced sample heading'
printf '\n## Rollback plan\n\nReal body after the fence.\n' >> "$FIXTURE"
run_validator "$CASE_DIR"

if [ "$V_EXTRA" -eq $((REF_EXTRA + 1)) ] \
   && contains "$V_OUT" "${FIXTURE_NAME}: Rollback plan"; then
  pass "24 a heading after a closed fence is still a heading, and only it is listed"
else
  fail "24 the post-fence heading was lost or the fenced one leaked into the list"
fi

# ------------------------------- 25. an unclosed fence names itself ----------
# Per CommonMark an unclosed fence runs to end of document, so every heading
# after it really is sample text and the template really is non-conforming.
# What review-hard caught is that saying only "5 sections missing" sends the
# author looking for headings that are sitting right there in the file. The
# cause has to lead the reason.

fixture_base "$FIXTURE"
# Cut the file at Retrieval, open a fence there and never close it, then put the
# five remaining sections back BELOW it. They are all really present in the file
# and all invisible in the filtered view, which is exactly the shape that used to
# report as five missing sections and nothing else.
awk '/^## Retrieval$/ { exit } { print }' "$FIXTURE" > "$FIXTURE.tmp"
{
  printf '```bash\ngrep foo bar\n\n'
  printf '## Retrieval\n\nSynthetic retrieval body.\n\n'
  printf '## Analysis prompt\n\nSynthetic analysis body.\n\n'
  printf '## Severity rubric\n\nSynthetic rubric body.\n\n'
  printf '## Confidence factors\n\nSynthetic confidence body.\n\n'
  printf '## Examples\n\nSynthetic example body.\n'
} >> "$FIXTURE.tmp"
mv "$FIXTURE.tmp" "$FIXTURE"
run_validator "$CASE_DIR"

if contains "$V_OUT" "${FIXTURE_NAME}: " \
   && contains "$V_OUT" "unclosed code fence swallows the rest of the file"; then
  pass "25 an unclosed fence is named as the cause, not just its symptoms"
else
  fail "25 an unclosed fence was reported only as missing sections"
fi

# ------------------------- 26. a broken filter is not a clean scan -----------
# The failure mode this guards is silent: with no exit-status check, a filter
# that dies leaves an empty view and every template reads as missing every
# section, which prints as a confident 0 conforming rather than as an error.
# That exact shape was produced once by a corrupted copy of the validator.

BROKEN="${WORK}/broken-validator.sh"
sed 's|END { if (fence) exit 3 }|END { if (fence) exit 3 }\n    BEGIN { exit 9 }|' \
  "$VALIDATOR" > "$BROKEN"
B_OUT="$(bash "$BROKEN" "$REAL_DIR" 2>&1)"
if contains "$B_OUT" "fence filter failed on" && contains "$B_OUT" "exit 9"; then
  pass "26 a failing fence filter reports the failure instead of an empty scan"
else
  fail "26 a failing fence filter degraded into a silent scan: ${B_OUT}"
fi

echo
if [ "$fails" -eq 0 ]; then
  echo "test-validate-bug-class-schema: all $checks checks passed"
  exit 0
else
  echo "test-validate-bug-class-schema: $fails of $checks check(s) FAILED"
  exit 1
fi
