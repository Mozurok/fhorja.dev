#!/usr/bin/env bash
# rank-references.sh - read-only retrieval ranker for Fhorja REFERENCES.md entries.
#
# The sibling of rank-learnings.sh, for the file that actually grew. Measured 2026-08-10:
# 73 REFERENCES.md across all projects total 2,300,541 chars (about 575k tokens), and the
# largest single one is 591,818 chars with 292 entries. LEARNINGS, which HAS a ranker, totals
# 701,243. The file with no ranker is three times the size of the file with one.
#
# REFERENCES is also the memory that survives every task: project-level by ADR-0007, appended
# by capture-references, never archived. It only grows. A consumer that reads it whole pays
# for every source ever captured to answer one question, and Chroma's context-rot work is
# specific that a single distractor already costs accuracy.
#
# Same design as rank-learnings.sh, deliberately: recency plus keyword overlap, plain grep and
# bash, no vector store and no embeddings (ADR-0027 keeps that posture). It ranks; it never
# edits, and it always exits 0 so it can never block a caller.
#
# Usage:
#   rank-references.sh "KEYWORDS OR OBJECTIVE" [PROJECT_DIR_OR_REFERENCES_FILE] [TOP_N]
#
# Scoring, per entry:
#   recency  0..40   from `Accessed: YYYY-MM-DD` (today 40, decaying to 0 at 365 days)
#   overlap  0..60   6 per distinct query token found in Title, Tags, Summary or URL
# An entry with no `Accessed:` scores recency 0 rather than being dropped: an undated capture
# is worse than a dated one, not invisible.

set -uo pipefail

QUERY="${1:-}"
TARGET="${2:-.}"
TOP_N="${3:-5}"

if [ -z "$QUERY" ]; then
  echo "usage: $0 \"KEYWORDS OR OBJECTIVE\" [PROJECT_DIR_OR_REFERENCES_FILE] [TOP_N]" >&2
  exit 0
fi

# Resolve the target: a REFERENCES.md, a project dir, or a tree to search.
FILES=()
if [ -f "$TARGET" ]; then
  FILES+=("$TARGET")
elif [ -f "$TARGET/REFERENCES.md" ]; then
  FILES+=("$TARGET/REFERENCES.md")
else
  while IFS= read -r f; do
    [ -n "$f" ] && FILES+=("$f")
  done < <(find "$TARGET" -name REFERENCES.md -not -path '*/.git/*' 2>/dev/null)
fi

if (( ${#FILES[@]} == 0 )); then
  echo "rank-references: no REFERENCES.md under ${TARGET} (nothing to rank)"
  exit 0
fi

python3 - "$QUERY" "$TOP_N" "${FILES[@]}" <<'PY'
import re
import sys
from datetime import date

query, top_n = sys.argv[1], int(sys.argv[2])
paths = sys.argv[3:]

tokens = {t for t in re.findall(r"[a-z0-9][a-z0-9._-]{2,}", query.lower())}
today = date.today()

def recency(text):
    m = re.search(r"Accessed:\s*(\d{4})-(\d{2})-(\d{2})", text)
    if not m:
        return 0.0
    try:
        age = (today - date(*(int(g) for g in m.groups()))).days
    except ValueError:
        return 0.0
    return max(0.0, 40.0 * (1.0 - min(age, 365) / 365.0))

def _has(token, hay):
    # Word-bounded, never substring. Plain `t in hay` matched "rot" inside "protocol", which
    # is a collision that produces a perfect-looking score on an unrelated entry.
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])", hay))


def overlap(title, text):
    """Weighted by WHERE the token matched, because one field lies about aboutness.

    ADR-0018 requires a `Context within project` field naming how each source relates to the
    others, so entries routinely quote their neighbours' titles. Measured on a "context rot
    chroma" query: an entry about progressive disclosure matched all three tokens, every one
    of them inside its `Context within project` line quoting the Chroma source it is NOT.
    Title and tags say what an entry IS; the body often says what it is near.
    """
    lower = text.lower()
    body_start = lower.find("\n")
    tags = " ".join(re.findall(r"(?im)^\s*-?\s*\*{0,2}Tags\*{0,2}:\s*(.+)$", text)).lower()
    head = title.lower()
    body = lower[body_start:] if body_start > 0 else lower

    score = 0.0
    for t in tokens:
        if _has(t, head):
            score += 10.0
        elif _has(t, tags):
            score += 8.0
        elif _has(t, body):
            score += 3.0
    return min(60.0, score)

rows = []
for path in paths:
    try:
        body = open(path, encoding="utf-8").read()
    except OSError:
        continue
    parts = re.split(r"(?m)^(?=### )", body)
    for part in parts:
        if not part.startswith("### "):
            continue
        title = part.split("\n", 1)[0][4:].strip()
        hit = overlap(title, part)
        # Overlap GATES, recency only orders. Scoring recency additively made an unrelated
        # query return 278 of 292 entries, because every recent capture scored on age alone:
        # a ranker that ranks almost everything has not ranked anything. Recency breaks ties
        # between entries that already matched.
        if hit <= 0:
            continue
        score = hit + recency(part)
        url = re.search(r"URL:\s*(\S+)", part)
        acc = re.search(r"Accessed:\s*(\d{4}-\d{2}-\d{2})", part)
        rows.append((score, title, url.group(1) if url else "", acc.group(1) if acc else "undated", path))

rows.sort(key=lambda r: (-r[0], r[1]))
total = sum(1 for p in paths for _ in re.finditer(r"(?m)^### ", open(p, encoding="utf-8").read()))

if not rows:
    print(f"rank-references: {total} entr(y|ies) scanned, none matched {query!r}")
    sys.exit(0)

print(f"Top {min(top_n, len(rows))} of {total} references for: {query}")
print()
for score, title, url, acc, path in rows[:top_n]:
    print(f"- **{title}** (score {score:.0f}, accessed {acc})")
    if url:
        print(f"  - {url}")
    print(f"  - from `{path}`")
print()
print(f"_{len(rows)} of {total} entries matched at least one query token. Read the full entry")
print("before citing it; this ranks, it does not summarize._")
PY

exit 0
