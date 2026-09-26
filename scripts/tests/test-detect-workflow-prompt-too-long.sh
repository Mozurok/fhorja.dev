#!/usr/bin/env bash
# test-detect-workflow-prompt-too-long.sh: the detector scenario 39 grades
# (evals/scenarios/39-workflow-prompt-too-long-ci.md) flags an oversized prompt with
# file:line, word count and threshold, reports a missing tail reminder as its own finding,
# passes a safe prompt, never counts front matter or fenced code, refuses a missing or empty
# target by name, and fails when either of its two exclusions is broken. Added 2026-09-23
# (D-8): until then the scenario named a detector that was not in the tree.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DETECT="${REPO}/scripts/detect-workflow-prompt-too-long.sh"
FX="${REPO}/evals/fixtures/workflow-prompt"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

# The body as the test reads it, computed apart from the detector: front matter removed
# only when it closes, fenced blocks removed. Prints the stripped body; with --first, the
# 1-based line number of its first non-blank line instead.
strip_body() {
  python3 - "$@" <<'PY'
import re, sys
args = sys.argv[1:]
first = args[0] == "--first"
path = args[-1]
lines = open(path, encoding="utf-8").read().split("\n")
start = 0
if lines and re.match(r"^---\s*$", lines[0]):
    for i in range(1, len(lines)):
        if re.match(r"^(---|\.\.\.)\s*$", lines[i]):
            start = i + 1
            break
out, infence = [], False
for i in range(start, len(lines)):
    if re.match(r"^[ \t]*(```|~~~)", lines[i]):
        infence = not infence
        continue
    if infence:
        continue
    if first and lines[i].strip():
        print(i + 1)
        sys.exit(0)
    out.append(lines[i])
if not first:
    sys.stdout.write("\n".join(out) + "\n")
PY
}

[ -x "$DETECT" ] || { echo "  FAIL detector not found or not executable at $DETECT"; exit 1; }
for f in oversized/fixture-oversized.md safe/fixture-safe.md padded/fixture-padded.md buried/fixture-reminder-buried.md; do
  [ -f "$FX/$f" ] || { echo "  FAIL fixture missing: $FX/$f"; exit 1; }
done
OVER="$FX/oversized/fixture-oversized.md"

# --- Case A: the oversized template -----------------------------------------------------
out="$("$DETECT" "$FX/oversized" "$FX/safe" 2>"$TMP/errA")"; rc=$?
wc_line="$(printf '%s\n' "$out" | grep -E 'words over [0-9]+$' | grep -F 'fixture-oversized.md' || true)"
n_wc="$(printf '%s\n' "$out" | grep -cE 'fixture-oversized\.md:[0-9]+: [0-9]+ words over 600$' || true)"
first="$(strip_body --first "$OVER")"
if [ "$rc" = "1" ] && [ "$n_wc" = "1" ] && [[ "$wc_line" == "${OVER}:${first}: "* ]]; then
  pass "1. oversized: exit 1 and one word-count finding at file:line (${wc_line#"$REPO"/})"
else
  fail "1. oversized: exit 1 and one word-count finding at file:${first} (rc=$rc, got '$out')"
fi

reported="$(printf '%s\n' "$wc_line" | sed -E 's/.*: ([0-9]+) words over [0-9]+$/\1/')"
truth="$(strip_body "$OVER" | wc -w | tr -d ' ')"
if [ -n "$reported" ] && [ -n "$truth" ] && [ "$truth" -gt 0 ] \
   && [ $(( (reported - truth) * 100 )) -le $(( truth * 5 )) ] \
   && [ $(( (truth - reported) * 100 )) -le $(( truth * 5 )) ]; then
  pass "2. reported count ${reported} is within 5 percent of wc -w on the stripped body (${truth}), threshold 600 named"
else
  fail "2. reported count '${reported}' vs wc -w on the stripped body '${truth}'"
fi

n_rem="$(printf '%s\n' "$out" | grep -cE 'fixture-oversized\.md:[0-9]+: no typed-return reminder in the last 5 lines$' || true)"
n_over="$(printf '%s\n' "$out" | grep -c 'fixture-oversized.md' || true)"
if [ "$n_rem" = "1" ] && [ "$n_over" = "2" ]; then
  pass "3. the missing tail reminder is a second, separate finding (2 lines for the oversized fixture)"
else
  fail "3. reminder finding separate (reminder lines=$n_rem, oversized lines=$n_over)"
fi

# --- Case B: the safe template --------------------------------------------------------
if ! printf '%s\n' "$out" | grep -q 'fixture-safe.md'; then
  pass "4. safe: absent from the findings when scanned beside the oversized one"
else
  fail "4. safe fixture appears in the findings"
fi

out="$("$DETECT" "$FX/safe" 2>&1)"; rc=$?
[ "$rc" = "0" ] && [ -z "$out" ] \
  && pass "5. safe alone: exit 0 and no output, the oversized sibling directory is not read" \
  || fail "5. safe alone exits 0 silently (rc=$rc, got '$out')"

# --- The threshold is the one given ----------------------------------------------------
out="$("$DETECT" --threshold 800 "$FX/oversized" 2>&1)"; rc=$?
out2="$("$DETECT" --threshold 400 "$FX/safe" 2>&1)"; rc2=$?
if [ "$rc" = "1" ] && ! printf '%s\n' "$out" | grep -q 'words over' \
   && printf '%s\n' "$out" | grep -q 'no typed-return reminder' \
   && [ "$rc2" = "1" ] && printf '%s\n' "$out2" | grep -qE 'fixture-safe\.md:[0-9]+: [0-9]+ words over 400$' \
   && ! printf '%s\n' "$out2" | grep -q 'no typed-return reminder'; then
  pass "6. --threshold moves the length finding only (800 clears the oversized count, 400 flags the safe one)"
else
  fail "6. --threshold honored (800: rc=$rc '$out'; 400: rc=$rc2 '$out2')"
fi

# --- Exclusions -----------------------------------------------------------------------
mkdir -p "$TMP/fm"
{
  echo "---"
  echo "name: front-matter-heavy"
  printf 'notes: '; for _ in $(seq 1 700); do printf 'word '; done; echo
  echo "---"
  echo "Check one file and report its size."
  echo
  echo "Return one payload matching worker_output_schema and nothing else."
} > "$TMP/fm/heavy.md"
out="$("$DETECT" "$TMP/fm" 2>&1)"; rc=$?
[ "$rc" = "0" ] && [ -z "$out" ] \
  && pass "7. front matter is not counted (700 words of it, a short body, exit 0)" \
  || fail "7. front matter excluded (rc=$rc, got '$out')"

raw="$(wc -w < "$FX/padded/fixture-padded.md" | tr -d ' ')"
out="$("$DETECT" "$FX/padded" 2>&1)"; rc=$?
[ "$rc" = "0" ] && [ -z "$out" ] && [ "$raw" -gt 600 ] \
  && pass "8. fenced code is not counted (padded control: ${raw} raw words, clean, native carrier accepted)" \
  || fail "8. fenced code excluded (rc=$rc, raw=$raw, got '$out')"

out="$("$DETECT" "$FX/buried" 2>&1)"; rc=$?
if [ "$rc" = "1" ] && [ "$(printf '%s\n' "$out" | grep -c .)" = "1" ] \
   && printf '%s\n' "$out" | grep -qE 'fixture-reminder-buried\.md:[0-9]+: no typed-return reminder in the last 5 lines$'; then
  pass "9. a reminder in the preamble does not count: one reminder finding, no length finding"
else
  fail "9. buried reminder flagged alone (rc=$rc, got '$out')"
fi

# --- Refusals -------------------------------------------------------------------------
err="$("$DETECT" "$FX/safe" "$TMP/absent-dir" 2>&1 >/dev/null)"; rc=$?
[ "$rc" = "2" ] && [[ "$err" == *"$TMP/absent-dir"* ]] \
  && pass "10. a missing directory exits 2 and is named, even beside a clean one" \
  || fail "10. missing directory refused by name (rc=$rc, err='$err')"

mkdir -p "$TMP/empty"
err="$("$DETECT" "$TMP/empty" 2>&1 >/dev/null)"; rc=$?
[ "$rc" = "2" ] && [[ "$err" == *"$TMP/empty"* ]] \
  && pass "11. a directory with no *.md exits 2 and is named, never reported clean" \
  || fail "11. empty directory refused by name (rc=$rc, err='$err')"

# --- Location independence and speed --------------------------------------------------
cp "$DETECT" "$TMP/copy.sh"
a="$("$DETECT" "$FX" 2>&1)"; b="$(cd "$TMP" && bash "$TMP/copy.sh" "$FX" 2>&1)"
[ -n "$a" ] && [ "$a" = "$b" ] \
  && pass "12. a copy run from another directory gives the same findings (no self-relative path)" \
  || fail "12. copy elsewhere differs"

TIMEFORMAT=%R
{ time "$DETECT" "$REPO/commands" "$REPO/wos" >/dev/null 2>&1; } 2>"$TMP/elapsed"; rc=$?
ms="$(awk '{ printf "%d", $1 * 1000 }' "$TMP/elapsed")"
[ "$rc" != "2" ] && [ "$ms" -lt 2000 ] \
  && pass "13. commands/ and wos/ scanned in ${ms} ms (budget 2000)" \
  || fail "13. runtime budget (rc=$rc, ${ms} ms)"

# --- Mutations: each exclusion must be load-bearing ------------------------------------
grep -v '^    if (inf) continue$' "$DETECT" > "$TMP/mut-code.sh"
if cmp -s "$DETECT" "$TMP/mut-code.sh"; then
  fail "14. mutation did not apply (code-skip line not found)"
else
  out="$(bash "$TMP/mut-code.sh" "$FX/padded" 2>&1)"; rc=$?
  [ "$rc" = "1" ] && printf '%s\n' "$out" | grep -q 'words over 600' \
    && pass "14. mutation: a detector that counts fenced code flags the padded control, so check 8 bites" \
    || fail "14. code-counting mutant was not caught (rc=$rc, got '$out')"
fi

sed 's/tail = (nb > 5) ? nb - 4 : 1/tail = 1/' "$DETECT" > "$TMP/mut-tail.sh"
if cmp -s "$DETECT" "$TMP/mut-tail.sh"; then
  fail "15. mutation did not apply (tail window line not found)"
else
  out="$(bash "$TMP/mut-tail.sh" "$FX/buried" 2>&1)"; rc=$?
  [ "$rc" = "0" ] && [ -z "$out" ] \
    && pass "15. mutation: a detector that searches the whole body passes the buried control, so check 9 bites" \
    || fail "15. whole-body mutant was not caught (rc=$rc, got '$out')"
fi

echo ""
echo "test-detect-workflow-prompt-too-long: ${checks} check(s), ${fails} failure(s)"
[ "$fails" -eq 0 ]
