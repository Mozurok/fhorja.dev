#!/usr/bin/env bash
# test-spine-eval-extract.sh: the reading half of the spine eval runner.
#
# The case worth staring at is check 6. The first '## Input prompt' section of
# scenario 08 carries TWO fenced blocks; every other section across the five
# spine scenarios carries one. An extractor written as "take the block" refuses
# scenario 08 in silence, which is exactly the defect this suite exists to catch,
# so the check reads the real file rather than a fixture.
#
# The other half is refusing to answer quietly: a section with no fenced block
# and a rubric under three items both have to be loud, because a blank turn or a
# two-item rubric becomes a false verdict once a model is in the loop.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

py() {  # py <python-body>; runs with the extractor importable as `x`
  python3 - "$REPO_ROOT" <<PYEOF
import importlib.util, json, os, sys
root = sys.argv[1]
os.chdir(root)
spec = importlib.util.spec_from_file_location("x", "evals/scripts/spine_eval_extract.py")
x = importlib.util.module_from_spec(spec); spec.loader.exec_module(x)
$1
PYEOF
}

check() {  # check <python-body-printing-PASS-or-FAIL> <label>
  local out; out="$(py "$1" 2>&1)"
  if [ "$out" = "PASS" ]; then pass "$2"; else fail "$2 ($out)"; fi
}

# 1..5: every manifest entry exists on disk, one check per scenario.
i=0
while IFS= read -r f; do
  i=$((i + 1))
  if [ -f "${REPO_ROOT}/$f" ]; then pass "$i. manifest entry exists: $(basename "$f")"
  else fail "$i. manifest entry exists: $f"; fi
done < <(python3 -c "
import json
for s in json.load(open('${REPO_ROOT}/evals/spine-evals.json'))['scenarios']:
    print(s['file'])
")

check '
t = open("evals/scenarios/08-operating-modes-minimal-vs-strict.md").read()
head, body = x.input_prompt_sections(t)[0]
blocks = x.fenced_blocks(body)
turn = x.turn_text(body)
print("PASS" if len(blocks) == 2 and blocks[0] in turn and blocks[1] in turn
      else f"2 blocks expected, got {len(blocks)}; both in turn: "
           f"{blocks[0] in turn and blocks[-1] in turn}")
' "6. scenario 08 first section concatenates BOTH fenced blocks"

check '
d = json.load(open("evals/spine-evals.json"))
bad = []
n = 0
for s in d["scenarios"]:
    t = open(s["file"]).read()
    for head, body in x.input_prompt_sections(t):
        n += 1
        turn = x.turn_text(body)
        if turn == x.UNPARSEABLE or not turn.strip():
            bad.append(os.path.basename(s["file"]) + " " + head)
print("PASS" if not bad and n == 19 else f"{n} sections, unparseable: {bad}")
' "7. all 19 sections of the ten scenarios produce a non-empty turn"

check '
t = "## Input prompt\n\nNo fenced block here at all.\n\n## Pass criteria\n"
head, body = x.input_prompt_sections(t)[0]
print("PASS" if x.turn_text(body) == x.UNPARSEABLE else f"got {x.turn_text(body)!r}")
' "8. a section with no fenced block is reported unparseable"

check '
t = "## Pass criteria\n\n1. one\n2. two\n"
try:
    x.rubric_items(t, "fixture")
    print("no raise")
except x.RubricTooThin as e:
    print("PASS" if "fixture" in str(e) else f"raised without the name: {e}")
' "9. a 2-item rubric raises RubricTooThin, naming the scenario"

check '
t = "## Pass criteria\n\n1. one\n2. two\n3. three\n"
items = x.rubric_items(t, "fixture")
print("PASS" if len(items) == 3 else f"got {len(items)}")
' "10. a 3-item rubric returns 3 items"

check '
t = "## Expected response shape\n\n1. one\n2. two\n3. three\n4. four\n"
items = x.rubric_items(t, "fixture")
print("PASS" if len(items) == 4 else f"got {len(items)}")
' "11. Expected response shape is used when Pass criteria is absent"

check '
t = "## Expected behavior\n\n- one\n- two\n- three\n"
items = x.rubric_items(t, "fixture")
print("PASS" if len(items) == 3 else f"got {len(items)}")
' "12. bullets count when the section has no numbered lines"

check '
t = "## Setup\n\nNone.\n\n## Input prompt\n"
print("PASS" if x.read_setup(t) == "" else f"got {x.read_setup(t)!r}")
' "13. a Setup body of None. reads as empty"

check '
setup = "fixture repo state"
turns = [("first ask", "first answer"), ("second ask", None)]
p1 = x.build_prompt(setup, turns, 1)
p2 = x.build_prompt(setup, turns, 2)
ok = (setup in p1 and "first ask" in p1
      and "--- turn 1 user ---" in p2 and "first answer" in p2 and "second ask" in p2
      and setup not in p2)
print("PASS" if ok else f"turn1={p1!r} turn2={p2!r}")
' "14. turn 1 inlines the setup; turn 2 carries an explicit transcript"

check '
setup = "fixture repo state"
turns = [("only ask", None)]
p1 = x.build_prompt(setup, turns, 1, setup_mode="none")
print("PASS" if setup not in p1 and "only ask" in p1 else f"got {p1!r}")
' "15. setup mode none does not inline the setup"

check '
# 16. Fence-aware sectioning, read off the real corpus rather than a fixture. Scenario 03
# quotes an IMPLEMENTATION_PLAN inside its "## Setup", and that quote carries "## Slice 01"
# and "## Slice 02". Before 2026-08-30 the section ended at the first quoted heading and the
# extracted setup lost the slice Scope and its exit criteria, which is the material the eval
# grades against. 726 chars then, 1537 now.
t = open("evals/scenarios/03-slice-execution-and-closure.md", encoding="utf-8").read()
s = x.read_setup(t)
missing = [n for n in ("Scope:", "Exit criteria") if n not in s]
print("PASS" if not missing else f"setup is {len(s)} chars and lacks {missing}")
' "16. scenario 03 setup survives the headings quoted inside its fence"

check '
# 17. The corpus-wide form of the same claim, derived rather than hardcoded: for every
# numbered scenario the number of sections must equal the number of "## " headings that are
# NOT inside a fence. 15 of 138 scenarios failed this before the fix. Deriving it means a
# scenario added later is covered without editing this file.
import glob, re
FENCE = re.compile(r"^\`\`\`[^\n]*\n.*?^\`\`\`[^\n]*$", re.M | re.S)
bad = []
files = sorted(glob.glob("evals/scenarios/[0-9]*.md"))
for f in files:
    t = open(f, encoding="utf-8").read()
    masked = FENCE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), t)
    want = len(re.findall(r"^##\s+", masked, re.M))
    if len(x._sections(t)) != want:
        bad.append(f)
if not files:
    print("no scenario files found; this check lost its subject")
else:
    print("PASS" if not bad else f"{len(bad)} of {len(files)} scenarios mis-sectioned: {bad[:3]}")
' "17. every scenario sections on real headings only, derived across the corpus"

check '
# 18. A wrapped criterion keeps its second line. Scenario 125 criterion 6 spans two lines and
# ends on the second; taking only the first dropped the half that names the commit form, which
# is the half the criterion exists to grade.
t = open("evals/scenarios/125-branch-commit-apply-authorization.md", encoding="utf-8").read()
six = [i for i in x.rubric_items(t) if i.startswith("6.")]
ok = len(six) == 1 and "bare" in six[0] and six[0].rstrip().endswith("`git commit`.")
print("PASS" if ok else f"criterion 6 came back as {six!r}")
' "18. a wrapped criterion keeps the line it wraps onto"

check '
# 19. Grouping must not change how many criteria there are. Derived per scenario rather than
# pinned: the number of items returned equals the number of lines that START an item.
import glob, re
bad = []
files = sorted(glob.glob("evals/scenarios/[0-9]*.md"))
for f in files:
    t = open(f, encoding="utf-8").read()
    try:
        items = x.rubric_items(t)
    except Exception:
        continue
    body = None
    for pat in x.RUBRIC_HEADERS:
        for h, sec in x._sections(t):
            if re.match(pat, h, re.I):
                body = sec
                break
        if body is not None:
            break
    lines = body.splitlines()
    starts = [l for l in lines if re.match(r"^\s*\d+\.\s", l)] or [
        l for l in lines if re.match(r"^\s*[-*]\s", l)]
    if len(items) != len(starts):
        bad.append((f, len(items), len(starts)))
if not files:
    print("no scenario files found; this check lost its subject")
else:
    print("PASS" if not bad else f"item count changed in {len(bad)}: {bad[:3]}")
' "19. grouping preserves the criterion count, derived across the corpus"

check '
# 20. A numbered rubric is numbered 1..N in file order. Scenario 125 read 1,2,3,4,5,6,8,9,7
# until 2026-08-30, which makes a run cite a criterion by a number that is not where it sits.
# Derived, so a scenario added later is covered without editing this file.
import glob, re
bad = []
files = sorted(glob.glob("evals/scenarios/[0-9]*.md"))
seen = 0
for f in files:
    t = open(f, encoding="utf-8").read()
    try:
        items = x.rubric_items(t)
    except Exception:
        continue
    heads = [re.match(r"^(\d+)\.", i) for i in items]
    if not all(heads):
        continue
    seen += 1
    seq = [int(h.group(1)) for h in heads]
    if seq != list(range(1, len(seq) + 1)):
        bad.append((f, seq))
if not seen:
    print("no numbered rubric found; this check lost its subject")
else:
    print("PASS" if not bad else f"{len(bad)} of {seen} numbered rubrics out of order: {bad[:2]}")
' "20. every numbered rubric runs 1..N in file order, derived across the corpus"

check '
# 21. The agent directive (ADR-0189) leads turn 1 and never a later turn. A rubric that grades the
# command chain grades a configuration that carries the directive; a prompt without it measures an
# install with its last step missing.
d = "DIRECTIVE PARAGRAPH"
turns = [("first ask", "first answer"), ("second ask", None)]
p1 = x.build_prompt("fixture state", turns, 1, directive=d)
p2 = x.build_prompt("fixture state", turns, 2, directive=d)
p1n = x.build_prompt("fixture state", turns, 1, setup_mode="none", directive=d)
ok = (p1.startswith(d) and "fixture state" in p1 and "first ask" in p1
      and d not in p2
      and p1n.startswith(d) and "fixture state" not in p1n)
print("PASS" if ok else f"p1={p1[:80]!r} p2has={d in p2} p1n={p1n[:60]!r}")
' "21. the directive leads turn 1, in both setup modes, and never a later turn"

check '
# 22. No directive is the pre-ADR-0189 behavior exactly, so the change is additive.
turns = [("only ask", None)]
a = x.build_prompt("fixture state", turns, 1)
b = x.build_prompt("fixture state", turns, 1, directive=None)
c = x.build_prompt("fixture state", turns, 1, directive="")
print("PASS" if a == b == c and a.startswith("Setup context") else f"a={a[:60]!r}")
' "22. a missing or empty directive leaves the prompt byte-identical to before"

check '
# 23. read_directive takes the fenced block out of the real template, not the prose around it.
d = x.read_directive("templates/AGENT_DIRECTIVE.template.md")
missing = x.read_directive("templates/does-not-exist.md")
ok = (d and "task-init" in d and "Paste this into" not in d and "## Adjusting it" not in d
      and missing == "")
print("PASS" if ok else f"len={len(d)} head={d[:60]!r} missing={missing!r}")
' "23. read_directive returns the fenced block, and empty for an absent file"

check '
# 24. The verdict-line regex tolerates a CLI that decorates its first stdout line. kimi prefixes
# "\u2022 ", which is not whitespace, so a bare ^\\s*- anchor dropped criterion 1 and only criterion 1
# across three 2026-09-01 runs while the grader had in fact answered it.
import re, os
src = open(os.path.join("evals", "scripts", "run-spine-evals.py"), encoding="utf-8").read()
m = re.search(r"_VERDICT_LINE = re\.compile\(\n(.*?)\n\s*re\.IGNORECASE", src, re.S)
pat = [l for l in m.group(1).split("\n") if l.strip().startswith("r\"")][0]
rx = re.compile(eval(pat.strip().rstrip(",")), re.IGNORECASE | re.MULTILINE)
raw = ("\u2022 - Criterion 1: PASS -- decorated first line\n"
       "  - Criterion 2: FAIL -- plain\n"
       "* - Criterion 3: UNCERTAIN -- asterisk\n"
       "not a verdict line at all\n"
       "- Criterion 4: PASS -- bare\n")
got = [int(x.group(1)) for x in rx.finditer(raw)]
print("PASS" if got == [1, 2, 3, 4] else f"matched {got}")
' "24. a decorated first stdout line still yields criterion 1"

echo ""
echo "test-spine-eval-extract: ${checks} check(s), ${fails} failure(s)"
[ "$fails" -eq 0 ]
