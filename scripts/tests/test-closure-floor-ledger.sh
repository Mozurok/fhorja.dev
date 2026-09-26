#!/usr/bin/env bash
# test-closure-floor-ledger.sh: every floor declares what it does with nothing.
#
# A closure floor used to have one answer to missing evidence: refuse, and wait
# for a person. Most of them now record `unverified: <reason>` and let closure
# proceed, which is only safe because the final report lists every floor left in
# that state. Three things have to hold together for that to be true, and they
# live in three different files, hand-maintained:
#
#   - each floor declares exactly one behavior, from a closed set of three;
#   - the per-consumer views carry the SAME behavior as the source of truth;
#   - task-close item 7a collects the records, and reads `none` rather than
#     being omitted when there are none.
#
# Check 6 is the regression guard for a defect this suite was written after. The
# floor said `record` while commands/task-close.md still said the task was
# **blocked**, in prose, three lines that a scope narrowing did not reach. The
# view and the command disagreed and nothing noticed; the floor then blocked the
# closure of the very task that had changed it.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC="${REPO}/wos/closure-floors.md"
PLATFORM="${REPO}/wos/platform-runtime-floors.md"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

# floors <file>: one "<floor heading>\t<behavior>" line per H2 floor, or
# "<heading>\tNONE" when the floor declares nothing. Section-scoped, so a
# preamble that merely defines the three words is not mistaken for a floor.
floors() {
  awk '
    /^## / {
      if (name != "" && name !~ /When to load/) printf "%s\t%s\n", name, (b == "" ? "NONE" : b)
      name = substr($0, 4); b = ""; next
    }
    /On missing evidence:/ {
      if (name !~ /When to load/ && b == "") {
        if (match($0, /On missing evidence: [a-z]+/))
          b = substr($0, RSTART + 21, RLENGTH - 21)
      }
      next
    }
    END { if (name != "" && name !~ /When to load/) printf "%s\t%s\n", name, (b == "" ? "NONE" : b) }
  ' "$1"
}

[ -f "$SRC" ] || { echo "  FAIL $SRC not found"; exit 1; }

# --- 1. every floor declares one behavior from the closed set ---------------
bad=""
while IFS=$'\t' read -r name b; do
  case "$b" in record|refuse|reconcile) ;; *) bad="${bad}\n    ${name} -> ${b}" ;; esac
done < <(floors "$SRC")
[ -z "$bad" ] && pass "1. every closure floor declares record, refuse or reconcile" \
              || { fail "1. floor(s) with no valid behavior:"; printf "$bad\n"; }

bad=""
while IFS=$'\t' read -r name b; do
  case "$b" in record|refuse|reconcile) ;; *) bad="${bad}\n    ${name} -> ${b}" ;; esac
done < <(floors "$PLATFORM")
[ -z "$bad" ] && pass "2. every platform runtime floor declares one too" \
              || { fail "2. platform floor(s) with no valid behavior:"; printf "$bad\n"; }

# --- 3. the preamble defines exactly three, and no more ---------------------
defined="$(grep -oE '^- `On missing evidence: [a-z]+`' "$SRC" | grep -oE '[a-z]+`$' | tr -d '`' | sort -u | tr '\n' ' ')"
[ "$defined" = "reconcile record refuse " ] \
  && pass "3. the preamble defines exactly the three behaviors" \
  || fail "3. preamble defines '$defined', expected 'reconcile record refuse '"

# --- 4. the per-consumer views agree with the source ------------------------
mismatch=""
for v in "${REPO}"/wos/closure-floors.*.md; do
  [ -f "$v" ] || continue
  while IFS=$'\t' read -r name b; do
    src_b="$(floors "$SRC" | awk -F'\t' -v n="$name" '$1 == n {print $2; exit}')"
    [ -z "$src_b" ] && continue
    [ "$b" = "$src_b" ] || mismatch="${mismatch}\n    $(basename "$v"): ${name} says ${b}, source says ${src_b}"
  done < <(floors "$v")
done
[ -z "$mismatch" ] && pass "4. every per-consumer view agrees with wos/closure-floors.md" \
                   || { fail "4. view disagrees with the source:"; printf "$mismatch\n"; }

# --- 5. task-close collects the records ------------------------------------
TC="${REPO}/commands/task-close.md"
if grep -q '### Unverified floors' "$TC" && grep -q 'reads `none` rather than being omitted' "$TC"; then
  pass "5. task-close item 7a collects the records and never omits the block"
else
  fail "5. task-close has no Unverified-floors block, or dropped the 'none' rule"
fi

# --- 6. no command contradicts a record or reconcile floor ------------------
# Matching a floor's HEADING against command prose was tried first and was
# decoration: the line that actually shipped the defect said "Experience gates",
# and the heading reads "Experience-verdict floor". Check 9 caught that, which is
# why the direction is inverted here. Enumerate every place a command asserts a
# closure is blocked, then require each one to name a floor that declares
# `refuse`. The allowlist is DERIVED from the floor files, so a floor that stops
# refusing narrows this check without anyone remembering to.
refuse_tokens() {  # refuse_tokens <floor-file>...
  local f n
  for f in "$@"; do floors "$f"; done \
    | awk -F'\t' '$2 == "refuse" { n = $1; sub(/ \(.*/, "", n); sub(/ floor$/, "", n); print n }'
}

contradictions() {  # contradictions <commands-dir> <floor-file>...
  local dir="$1"; shift
  local allow line out="" t ok
  allow="$(refuse_tokens "$@")"
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    ok=0
    while IFS= read -r t; do
      [ -n "$t" ] || continue
      printf '%s' "$line" | grep -qiE "$(printf '%s' "$t" | sed 's/[^A-Za-z]/./g')" && { ok=1; break; }
      # The Godot floor is cited by its short name as often as its full one.
      printf '%s' "$t" | grep -qi 'feel' && printf '%s' "$line" | grep -qi 'feel.verdict' && { ok=1; break; }
    done <<EOF
$allow
EOF
    [ "$ok" -eq 0 ] && out="${out}\n    $(printf '%s' "$line" | cut -c1-130)"
  done <<EOF
$(grep -rniE '\*\*blocked\*\*[ ]*\(not archived\)|is blocked \(not archived\)' "$dir"/*.md 2>/dev/null | sed "s#^${dir}/##")
EOF
  printf '%s' "$out"
}

contradiction="$(contradictions "${REPO}/commands" "$SRC" "$PLATFORM")"
[ -z "$contradiction" ] && pass "6. every blocked assertion names a floor that declares refuse" \
                        || { fail "6. a command asserts blocked for a floor that does not refuse:"; printf "$contradiction\n"; }

# --- 6b. a command line that restates a floor carries that floor's verdict ---
# Check 6 reads one phrasing, "**blocked** (not archived)". The 2026-09-22 audit
# found the same contradiction written as "does NOT close inline" and "is not
# ready-to-close" in the Definition of done of implement-approved-slice and
# slice-closure, where a DoD bullet repeats a floor, and check 6 saw none of it.
# So every command line that carries a blocking idiom and names a floor must name
# a floor whose `On missing evidence:` line is `refuse`. A line that speaks of
# floors in general ("a slice failing a floor") must defer to the declared
# verdict instead of stating one, because most of those floors record.
# BLOCKING_IDIOMS and HISTORY_LINES are defined with check 11 below; the function
# reads them when it runs, after both are set.
floor_line_contradictions() {  # floor_line_contradictions <commands-dir> <floor-file>...
  local dir="$1"; shift
  python3 - "$dir" "$BLOCKING_IDIOMS" "$HISTORY_LINES" "$@" <<'PY'
import glob, os, re, sys
cdir, idioms, history, floor_files = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
block = re.compile(idioms, re.I)
hist = re.compile(history, re.I)
floors = {}
for f in floor_files:
    name = None
    for line in open(f, encoding="utf-8"):
        if line.startswith("## "):
            name = line[3:].strip()
            if name.startswith("When to load"):
                name = None
            continue
        m = re.match(r"On missing evidence: ([a-z]+)", line)
        if name and m and name not in floors:
            floors[name] = m.group(1)
def token(name):
    t = re.sub(r" \(.*", "", name)
    t = re.sub(r" floor$", "", t)
    return re.compile(re.sub(r"[^A-Za-z0-9]", ".", t), re.I)
tokens = [(token(n), b) for n, b in floors.items()]
# A floor is often cited by a shorter name than its heading.
experience = [b for n, b in floors.items() if n.startswith("Experience-verdict floor")]
tokens += [(re.compile(r"Experience gates?", re.I), experience[0] if experience else "record"),
           (re.compile(r"feel.verdict", re.I), "refuse")]
generic = re.compile(r"\b(?:failing|fails|failed) (?:a|the|any) floor\b", re.I)
defers = re.compile(r"On missing evidence|declared verdict", re.I)
files = sorted(glob.glob(os.path.join(cdir, "*.md")) + glob.glob(os.path.join(cdir, "*", "SKILL.md")))
for path in files:
    rel = os.path.relpath(path, cdir)
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        if not block.search(line) or hist.search(line):
            continue
        named = [b for t, b in tokens if t.search(line)]
        if generic.search(line) and not defers.search(line):
            print(f"    {rel}:{n}: states one verdict for every floor instead of each floor's own: {line.strip()[:90]}")
        elif named and "refuse" not in named:
            print(f"    {rel}:{n}: blocks on a floor that declares {'/'.join(sorted(set(named)))}: {line.strip()[:90]}")
PY
}

# --- 7. mutation: a floor that declares nothing must be caught --------------
cp "$SRC" "$TMP/mutated.md"
python3 - "$TMP/mutated.md" <<'PY'
import sys,io,re
p=sys.argv[1]; s=io.open(p,encoding='utf-8').read()
i=s.index('## Experience-verdict floor')
head,tail=s[:i],s[i:]
tail=re.sub(r'\nOn missing evidence: [a-z]+[^\n]*\n', '\n', tail, count=1)
io.open(p,'w',encoding='utf-8').write(head+tail)
PY
if floors "$TMP/mutated.md" | grep -q 'NONE'; then
  pass "7. mutation: a floor stripped of its behavior line is detected"
else
  fail "7. mutation did not bite; an undeclared floor would pass check 1"
fi

# --- 8. mutation: a view drifting from the source must be caught ------------
mkdir -p "$TMP/wos"
cp "$SRC" "$TMP/wos/closure-floors.md"
sed 's/^On missing evidence: refuse -- uncommitted/On missing evidence: record -- uncommitted/' \
  "$SRC" > "$TMP/wos/closure-floors.fake-consumer.md"
drift=""
while IFS=$'\t' read -r name b; do
  src_b="$(floors "$TMP/wos/closure-floors.md" | awk -F'\t' -v n="$name" '$1 == n {print $2; exit}')"
  [ -n "$src_b" ] && [ "$b" != "$src_b" ] && drift="yes"
done < <(floors "$TMP/wos/closure-floors.fake-consumer.md")
[ "$drift" = "yes" ] && pass "8. mutation: a view drifting from the source is detected" \
                     || fail "8. drift mutation did not bite; check 4 is blind"

# --- 9. mutation: check 6 must bite on the defect it was written for --------
# The exact line commands/task-close.md carried until 2026-09-16, against a
# floor that declares `record`. If this fixture comes back clean, check 6 is
# decoration and the drift it exists to catch would ship again.
mkdir -p "$TMP/commands"
cat > "$TMP/commands/task-close.md" <<'EOF'
# task-close

- Experience gates (generalized, ADR-0091): a task with a deliverable tagged `user-facing-content` is **blocked** (not archived) without a cited `## Experience verdict` PASS.
EOF
mut="$(contradictions "$TMP/commands" "$SRC" "$PLATFORM")"
[ -n "$mut" ] && pass "9. mutation: the 2026-09-16 prose drift is detected" \
              || fail "9. mutation did not bite; check 6 would miss the defect it was written for"

# A fixture with the corrected prose must come back clean, or check 9 proves
# only that the grep matches something.
cat > "$TMP/commands/task-close.md" <<'EOF'
# task-close

- Experience gates (generalized, ADR-0091; `On missing evidence: record`): WHEN the verdict is absent, the floor writes `unverified: <reason>` and closure proceeds.
EOF
[ -z "$(contradictions "$TMP/commands" "$SRC" "$PLATFORM")" ] \
  && pass "10. control: the corrected prose reports nothing" \
  || fail "10. control fixture reported a contradiction"


# The blocking idioms this corpus actually uses, enumerated from it rather than
# guessed. A narrower list is how this session reported a floor clean four
# separate times: `SHALL NOT be archived` is not `do NOT archive`, and
# ``not `ready to close` `` is not `not ready to close`. Every form below was
# found in the files, not invented for the check.
#
# Matched without regard to case since 2026-09-23 (docs drift audit, gap 3). The
# list was case-sensitive, so `do not inline-close`, `not-ready-to-close` with
# hyphens, `leave the slice open`, `stays open pending` and `fail-closed` all
# passed: the platform floors file used four of them.
BLOCKING_IDIOMS='SHALL NOT close|SHALL NOT be archived|do NOT inline-close|do NOT archive|not `ready to close`|not[- ]ready[- ]to[- ]close|SHALL BLOCK|is a BLOCK|FAILS CLOSED|fail-closed|does not close|gate-blocked|closure is blocked|leave the slice open|stays open pending'

# A sentence that names a blocking rule in order to say it was replaced is
# history, not a mandate. The tier-declaration floor carries one on purpose.
HISTORY_LINES='replaces|replaced|used to|until 20[0-9][0-9]|superseded'

# body_blocks <floor-file> <floor-name>: 0 when that floor's body mandates blocking.
body_blocks() {
  awk -v n="## $2" '$0 == n {p=1; next} /^## / {p=0} p' "$1" \
    | grep -viE "$HISTORY_LINES" | grep -qiE "$BLOCKING_IDIOMS"
}

# body_contradictions <floor-file>...: every record or reconcile floor whose body
# mandates blocking anyway.
body_contradictions() {
  local f out=""
  for f in "$@"; do
    while IFS=$'\t' read -r name b; do
      case "$b" in record|reconcile) ;; *) continue ;; esac
      body_blocks "$f" "$name" \
        && out="${out}\n    $(basename "$f"): ${name} declares ${b} and mandates blocking"
    done < <(floors "$f")
  done
  printf '%s' "$out"
}

# --- 11. the declaration and the body it governs ---------------------------
# ADR-0203 gave each floor an `On missing evidence:` line and did not rewrite the
# normative variant bodies underneath. For a day, eleven floors declared record
# or reconcile and then instructed a consumer to hold the slice: "SHALL NOT close
# inline", "classify the slice `not ready to close`", "do NOT archive". A reader
# following the sentence blocked; a reader following the declaration recorded.
#
# This check pinned that count while the rewrite was pending and now asserts its
# absence. It names the offending floor rather than returning a bare count,
# because the count alone sends the next person looking through fifteen floors
# for the one that moved.
contradicting="$(body_contradictions "$SRC" "$PLATFORM")"
if [ -z "$contradicting" ]; then
  pass "11. every floor's body carries the behavior its declaration line names"
else
  fail "11. a floor declares one behavior and mandates another:"
  printf "$contradicting\n"
fi

# --- 12. the control: a refuse floor MUST still block ----------------------
# The inverse of check 11, and the reason it is not vacuous. A rewrite that
# turned every floor into a recorder would pass check 11 and would have removed
# the three gates that prevent losing work rather than adding friction.
n_refuse_blocking=0
for f in "$SRC" "$PLATFORM"; do
  while IFS=$'\t' read -r name b; do
    [ "$b" = "refuse" ] || continue
    body_blocks "$f" "$name" && n_refuse_blocking=$((n_refuse_blocking + 1))
  done < <(floors "$f")
done
[ "$n_refuse_blocking" -eq 4 ] \
  && pass "12. all 4 refuse floors still block, which is what check 11 must not have removed" \
  || fail "12. $n_refuse_blocking of 4 refuse floors still block; a record rewrite reached a floor that prevents losing work"

# --- 6b, run here because it reads BLOCKING_IDIOMS, set above check 11 -------
restated="$(floor_line_contradictions "${REPO}/commands" "$SRC" "$PLATFORM")"
[ -z "$restated" ] && pass "6b. every command line restating a floor carries that floor's own verdict" \
                   || { fail "6b. a command line restates a floor with the wrong verdict:"; printf '%s\n' "$restated"; }

# --- 13-16. mutations for the 2026-09-23 widening (docs drift audit, gap 3) ---
# Each reintroduces a form the case-sensitive list or the single-phrase check 6
# let through, and the control proves the corrected text reports nothing.
mkdir -p "$TMP/cmd6b"
cat > "$TMP/cmd6b/slice-closure.md" <<'EOF'
# slice-closure

- Experience gates (generalized, ADR-0091): a slice tagged `user-facing-content` or `new-user-facing-surface` is not ready-to-close without a cited `## Experience verdict` PASS.
EOF
[ -n "$(floor_line_contradictions "$TMP/cmd6b" "$SRC" "$PLATFORM")" ] \
  && pass "13. mutation: a DoD line blocking on the record-floor experience verdict is detected" \
  || fail "13. mutation did not bite; the hyphenated not-ready-to-close form passes 6b"

cat > "$TMP/cmd6b/slice-closure.md" <<'EOF'
# slice-closure

- Platform runtime floors: on a Godot-signature task a slice failing a floor does NOT close inline and routes per that file.
EOF
[ -n "$(floor_line_contradictions "$TMP/cmd6b" "$SRC" "$PLATFORM")" ] \
  && pass "14. mutation: one blanket verdict for every platform floor is detected" \
  || fail "14. mutation did not bite; a blanket block over record floors passes 6b"

cat > "$TMP/cmd6b/slice-closure.md" <<'EOF'
# slice-closure

- Platform runtime floors: a slice failing a floor takes that floor's declared verdict from its `On missing evidence:` line; the Godot feel-verdict floor refuses and does not close.
- Commit-evidence floor: a slice does NOT close inline without a cited commit.
EOF
[ -z "$(floor_line_contradictions "$TMP/cmd6b" "$SRC" "$PLATFORM")" ] \
  && pass "15. control: deferring to the declared verdict, and blocking on a refuse floor, report nothing" \
  || fail "15. control fixture reported a contradiction"

cp "$PLATFORM" "$TMP/platform-mutated.md"
python3 - "$TMP/platform-mutated.md" <<'PY'
import sys, io
p = sys.argv[1]; s = io.open(p, encoding="utf-8").read()
i = s.index("## Web-runtime-gate floor")
j = s.index("\n", s.index("On missing evidence:", i))
s = s[:j] + "\n\nWhen the verdict is missing, do not inline-close; leave the slice open.\n" + s[j:]
io.open(p, "w", encoding="utf-8").write(s)
PY
[ -n "$(body_contradictions "$TMP/platform-mutated.md")" ] \
  && pass "16. mutation: a lower-case blocking idiom in a record floor's body is detected" \
  || fail "16. mutation did not bite; check 11 is still case-sensitive"

# --- 17-19. the views builder compares each command with its own view -------
# The C26 defect (docs drift audit, gap 4): implement-approved-slice's Definition
# of done required an "Integrity floor (inline-close)" that the canonical file
# gave no inline-close variant, so the generated view never applied it, and
# `build-closure-floor-views.py --check` stayed clean because it compared views
# with the canonical file and never read the commands. The builder runs from the
# fixture root, where every path it opens is relative.
VROOT="$TMP/views-root"
mkdir -p "$VROOT/wos" "$VROOT/commands"
cp "$SRC" "$PLATFORM" "$VROOT/wos/"
for c in task-close slice-closure implement-approved-slice; do
  cp "${REPO}/commands/${c}.md" "$VROOT/commands/"
done
views_check() { ( cd "$VROOT" && python3 "${REPO}/scripts/build-closure-floor-views.py" --check 2>&1 ); }
( cd "$VROOT" && python3 "${REPO}/scripts/build-closure-floor-views.py" >/dev/null )
out="$(views_check)"; rc=$?
[ "$rc" -eq 0 ] && pass "17. control: the real commands agree with their views" \
                || fail "17. control: the builder reports a disagreement on the real tree: $out"

python3 - "$VROOT/wos/closure-floors.md" <<'PY'
import io, sys
p = sys.argv[1]; s = io.open(p, encoding="utf-8").read()
i = s.index("## Integrity floor")
j = s.index("### implement-approved-slice variant", i)
k = s.index("\n### ", j + 4)
io.open(p, "w", encoding="utf-8").write(s[:j] + s[k + 1:])
PY
( cd "$VROOT" && python3 "${REPO}/scripts/build-closure-floor-views.py" >/dev/null )
out="$(views_check)"; rc=$?
if [ "$rc" -ne 0 ] && grep -q 'requires the `integrity` floor' <<<"$out"; then
  pass "18. mutation: a DoD floor with no variant in the command's view is refused by name"
else
  fail "18. mutation did not bite for the right reason (rc=$rc): $out"
fi

cp "$SRC" "$VROOT/wos/closure-floors.md"
( cd "$VROOT" && python3 "${REPO}/scripts/build-closure-floor-views.py" >/dev/null )
python3 - "$VROOT/commands/slice-closure.md" <<'PY'
import io, sys
p = sys.argv[1]; s = io.open(p, encoding="utf-8").read()
needle = "integrity (v3 wave3 S1), "
assert needle in s, "fixture lost its mutation target"
io.open(p, "w", encoding="utf-8").write(s.replace(needle, "", 1))
PY
out="$(views_check)"; rc=$?
if [ "$rc" -ne 0 ] && grep -q 'leaves out `integrity`' <<<"$out"; then
  pass "19. mutation: a 'The floors are:' list that drops a floor its view applies is refused by name"
else
  fail "19. mutation did not bite for the right reason (rc=$rc): $out"
fi

echo
echo "closure-floor-ledger: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
