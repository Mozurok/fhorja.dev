#!/usr/bin/env bash
# test-initiative-classifier.sh -- regression for the portfolio-review
# --initiative status classifier (the 2026-07-06 masking defect).
#
# Asserts that a status keyword appearing in an Objective cell can no longer
# mask the Status column (header-derived column parse), and that a table
# WITHOUT a header row keeps the historical whole-row best-effort behavior.
#
# The script under test resolves ROOT from its own location, so the fixture
# is a minimal layout clone (scripts/ + projects/) in a mktemp dir with the
# script copied in; no environment hook is needed and the repo is untouched.
#
# Usage: test-initiative-classifier.sh [path-to-portfolio-review.sh]
#        (default: the sibling scripts/portfolio-review.sh; pass an older
#         version to prove the test catches the defect, the red-proof)
# Exit:  0 = all assertions pass, 1 = any assertion fails.

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="${1:-$DIR/../portfolio-review.sh}"
[[ -f "$SCRIPT" ]] || { echo "no such script: $SCRIPT" >&2; exit 2; }

TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
mkdir -p "$TMPD/scripts" "$TMPD/projects/test__fixture"
cp "$SCRIPT" "$TMPD/scripts/portfolio-review.sh"
chmod +x "$TMPD/scripts/portfolio-review.sh"

cat > "$TMPD/projects/test__fixture/INITIATIVE_INDEX.md" <<'EOF'
# INITIATIVE_INDEX

## Initiatives

### fixture initiative A (header table: the fixed path)

| Date | Task folder | Objective | Status | Cross-links | Next command |
| --- | --- | --- | --- | --- | --- |
| 2026-01-01 | 2026-01-01_masked-task | consumed by portfolio-review early in the row | closed | none | none |
| 2026-01-02 | 2026-01-02_plain-task | does ordinary things | in-progress | none | what-next |

### fixture initiative B (headerless table: the fallback path)

| 2026-01-03 | 2026-01-03_beta-task | reviews stuff early in row | closed | none | none |
EOF

OUT="$(bash "$TMPD/scripts/portfolio-review.sh" --initiative 2>/dev/null || true)"

fail=0
assert() {
  local desc="$1" pattern="$2"
  if printf '%s\n' "$OUT" | grep -qE "$pattern"; then
    echo "PASS: $desc"
  else
    echo "FAIL: $desc (pattern not found: $pattern)"
    fail=1
  fi
}

# The masking case: "portfolio-review" in the Objective cell sits BEFORE the
# Status cell; only a column-scoped parse classifies this row done.
assert "masked row classifies by the Status column (done)" \
  '\[done\][[:space:]]+2026-01-01_masked-task'

# A plain header-table row still reads its own status.
assert "plain header-table row classifies in-progress" \
  '2026-01-02_plain-task[[:space:]]+\(in-progress\)'

# The headerless table keeps the historical whole-row behavior byte-compatible:
# "reviews" early in the row wins over the later "closed".
assert "headerless fallback preserves whole-row behavior (review wins)" \
  '\[ready\][[:space:]]+2026-01-03_beta-task[[:space:]]+\(review\)'

# JSON emitter mode (ADR-0083 single parse point): the same fixture through
# --initiative --json must carry the column-scoped status per row.
JOUT="$(bash "$TMPD/scripts/portfolio-review.sh" --initiative --json 2>/dev/null || true)"

json_assert() {
  local desc="$1" task="$2" want="$3"
  local got
  got="$(printf '%s' "$JOUT" | python3 -c '
import json, sys
task = sys.argv[1]
try:
    rows = json.load(sys.stdin)
except Exception:
    print("INVALID-JSON"); raise SystemExit
for r in rows:
    if r.get("task") == task:
        print(r.get("status", "MISSING")); break
else:
    print("ROW-NOT-FOUND")
' "$task")"
  if [[ "$got" == "$want" ]]; then
    echo "PASS: $desc"
  else
    echo "FAIL: $desc (want status=$want, got $got)"
    fail=1
  fi
}

json_assert "emitter: masked row carries Status-column status (closed)" \
  "2026-01-01_masked-task" "closed"
json_assert "emitter: plain header-table row carries in-progress" \
  "2026-01-02_plain-task" "in-progress"

if [[ "$fail" -ne 0 ]]; then
  echo "RESULT: FAIL"
  exit 1
fi
echo "RESULT: PASS"
exit 0
