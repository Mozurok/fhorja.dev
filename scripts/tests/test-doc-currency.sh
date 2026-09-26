#!/usr/bin/env bash
# test-doc-currency.sh: the SKU table's declared refresh cadence is measured,
# not merely written. The table said "every 6 weeks" and "stale SKUs degrade the
# routing more than no routing at all" while sitting 9.6 weeks past that cadence,
# because nothing read the sentence.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CHK="${REPO}/scripts/check-doc-currency.sh"
FILE="${REPO}/wos/model-routing.md"
checks=0; fails=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); fails=$((fails+1)); echo "  FAIL $1"; }
[ -x "$CHK" ] || { echo "  FAIL $CHK not executable"; exit 1; }

for d in model-routing editor-mode-mappings sub-agent-orchestration; do
  grep -qE '^Last scanned: [0-9]{4}-[0-9]{2}-[0-9]{2}$' "${REPO}/wos/${d}.md" \
    || fail "0. wos/${d}.md declares no Last scanned: date"
done
grep -qE '^Last scanned: [0-9]{4}-[0-9]{2}-[0-9]{2}$' "$FILE" \
  && pass "1. the table carries a machine-readable Last scanned: date" \
  || fail "1. no machine-readable Last scanned: line"
grep -qE '^Cadence: [0-9]+ weeks$' "$FILE" \
  && pass "2. the table carries a machine-readable Cadence:" || fail "2. no machine-readable Cadence:"

out="$("$CHK" 2>&1)"; rc=$?
[ "$rc" -eq 0 ] && pass "3. advisory: always exits 0" || fail "3. exited $rc; a date must not break the build"
printf '%s' "$out" | grep -q '^Doc-currency:' \
  && pass "4. prints exactly one Doc-currency: line" || fail "4. no Doc-currency: line"
printf '%s' "$out" | grep -q 'within their declared' \
  && pass "5. every dated doc is inside its cadence" \
  || fail "5. a dated doc is PAST its cadence: $out"

# The control. Forcing the limit below the age must flip the verdict, or check 5
# is measuring nothing. -1 and not 0: an age of 0 days is legitimately within a
# limit of 0, and the first version of this control asserted otherwise and was
# caught by scripts/verified-check.sh rather than by reading.
late="$("$CHK" --days -1 2>&1)"
printf '%s' "$late" | grep -q 'past cadence' \
  && pass "6. control: a forced limit reports the overrun" || fail "6. control: forced limit did not flip the verdict"
[ "$out" != "$late" ] \
  && pass "7. control: the two runs DIFFER, so check 5 is measuring the cadence" \
  || fail "7. control: both runs returned the same text"
# The generalized checker cannot hardcode one URL, because each dated doc names its
# own source. What it must still do is tell the reader WHICH file to reopen; a bare
# "something is stale" line is the advisory nobody acts on.
printf '%s' "$late" | grep -qE 'oldest wos/[a-z-]+\.md' \
  && pass "8. the overrun line names the specific file to reopen" \
  || fail "8. overrun line has no actionable pointer: $late"

# The stale SKUs this item existed to remove are gone from every RECOMMENDING surface.
#
# The first version of this check scanned scripts/ whole and found exactly one hit:
# its own grep pattern, on the line below. A checker matching its own trigger token,
# written in the same hour as scripts/check-live-markers.sh, which exists to solve
# that exact class. Recorded rather than quietly corrected.
#
# The distinction is the one that file already draws. A RECOMMENDATION lives in a
# `suggested-model:` frontmatter field or in the routing table's Default model
# column. A historical mention is prose, and wos/model-routing.md deliberately keeps
# one: naming the four SKUs it carried until 2026-09-17 is how it explains that the
# drift degraded the routing rather than breaking it. So: scan the recommending
# surfaces, and exclude this suite, whose job is to spell the tokens.
# claude-opus-5 joined on 2026-09-22 when the vendor moved it to its legacy list behind
# claude-opus-5-5. Anchored below because the bare token is a PREFIX of the id that
# replaced it: unanchored, this check would accuse every command now carrying 5.5.
RETIRED='claude-sonnet-4-6|claude-opus-4-7|claude-opus-4-8|claude-opus-5'
hits="$(grep -rnE "suggested-model: *(${RETIRED})([^-0-9]|$)" "${REPO}/commands" 2>/dev/null || true)"
hits="${hits}$(grep -nE "^\| .*\| *\`(${RETIRED})\`" "$FILE" 2>/dev/null || true)"
if [ -n "$hits" ]; then
  fail "9. a retired SKU is still RECOMMENDED: $(printf '%s' "$hits" | head -1 | cut -c1-90)"
else
  pass "9. no retired SKU is recommended by any frontmatter field or routing-table row"
fi
grep -q 'claude-opus-5-5' "$FILE" && grep -q 'claude-sonnet-5' "$FILE" \
  && pass "10. the table names the current SKUs" || fail "10. the table does not name the current SKUs"

# A rename sweep collapses two old SKUs onto one new one and leaves a pipe-enum
# reading `... | claude-opus-5 | claude-opus-5`. Found by eye on 2026-09-17 in
# commands/_shared/worker-contract.md, after every other check in this file passed.
dupes="$(grep -rn 'claude-opus-5[^|]*| *`\?claude-opus-5\|claude-sonnet-5[^|]*| *`\?claude-sonnet-5' \
          "${REPO}/commands" "${REPO}/wos" "${REPO}/templates" 2>/dev/null || true)"
if [ -n "$dupes" ]; then
  fail "11. a SKU enum repeats a value: $(printf '%s' "$dupes" | head -1 | cut -c1-90)"
else
  pass "11. no SKU enum repeats a value after the rename sweep"
fi

echo
echo "doc-currency: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
