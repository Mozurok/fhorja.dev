#!/usr/bin/env bash
# test-initiative-blocked-by-column.sh -- regression for the portfolio-review
# --initiative cross-link (blocked-by) parse.
#
# Sibling of test-initiative-classifier.sh, which covers the same masking
# defect class on the Status column. This one covers the Cross-links column:
# a "blocked-by: ..." string appearing in an Objective (or any other) cell
# must not be read as a real dependency when a header row identifies the
# Cross-links column, and a table WITHOUT a header row must keep the
# historical whole-row best-effort match so every already-written prose row
# keeps parsing.
#
# The script under test resolves ROOT from its own location, so the fixture
# is a minimal layout clone (scripts/ + projects/) in a mktemp dir with the
# script copied in; no environment hook is needed and the repo is untouched.
#
# Usage: test-initiative-blocked-by-column.sh [path-to-portfolio-review.sh]
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

### fixture initiative A (header table: the column-scoped path)

| Date | Task folder | Objective | Status | Cross-links | Next command |
| --- | --- | --- | --- | --- | --- |
| 2026-01-01 | 2026-01-01_alpha-task | groundwork everyone waits on | initialized | none | what-next |
| 2026-01-02 | 2026-01-02_decoy-task | document why blocked-by: 2026-01-01_alpha-task was rejected | initialized | none | what-next |
| 2026-01-03 | 2026-01-03_real-dep-task | depends on alpha for real | initialized | blocked-by: 2026-01-01_alpha-task | what-next |
| 2026-01-04 | 2026-01-04_multi-dep-task | depends on two siblings | initialized | blocked-by: 2026-01-01_alpha-task,2026-01-03_real-dep-task | what-next |
| 2026-01-05 | 2026-01-05_mixed-cell-task | blocking plus informational relations | initialized | blocked-by: 2026-01-01_alpha-task; shares-contract: 2026-01-02_decoy-task | what-next |
| 2026-01-06 | 2026-01-06_dangling-task | names a sibling that is not in the table | initialized | blocked-by: 2026-01-99_ghost-task | what-next |

### fixture initiative B (headerless table: the fallback path)

| 2026-02-01 | 2026-02-01_legacy-blocker | groundwork | initialized | none | what-next |
| 2026-02-02 | 2026-02-02_legacy-task | prose row from before the format existed | initialized | blocked-by: 2026-02-01_legacy-blocker | what-next |
EOF

OUT="$(cd "$TMPD" && bash "$TMPD/scripts/portfolio-review.sh" --initiative 2>/dev/null || true)"

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
refute() {
  local desc="$1" pattern="$2"
  if printf '%s\n' "$OUT" | grep -qE "$pattern"; then
    echo "FAIL: $desc (pattern unexpectedly found: $pattern)"
    fail=1
  else
    echo "PASS: $desc"
  fi
}

# CRITICAL 1 (the masking case, mirrors the Status-column defect of 2026-07-06):
# "blocked-by: ..." sits inside the Objective cell of the decoy row. Only a
# column-scoped parse leaves that row unblocked.
refute "decoy row is NOT blocked by a blocked-by string in its Objective cell" \
  '\[blocked\][[:space:]]+2026-01-02_decoy-task'
assert "decoy row is ready despite the Objective-cell decoy" \
  '\[ready\][[:space:]]+2026-01-02_decoy-task'

# REGRESSION: a genuine Cross-links dependency is still read.
assert "real dependency in the Cross-links column is read" \
  '\[blocked\][[:space:]]+2026-01-03_real-dep-task[[:space:]]+blocked-by:.*2026-01-01_alpha-task'

# REGRESSION: a comma-separated pair yields both slugs.
assert "multi-dependency cell yields the first slug" \
  '\[blocked\][[:space:]]+2026-01-04_multi-dep-task[[:space:]]+blocked-by:.*2026-01-01_alpha-task'
assert "multi-dependency cell yields the second slug" \
  '\[blocked\][[:space:]]+2026-01-04_multi-dep-task[[:space:]]+blocked-by:.*2026-01-03_real-dep-task'

# EDGE: a cell holding both a blocking and a non-blocking relation blocks only
# on the blocking one.
assert "mixed cell blocks on the blocked-by slug" \
  '\[blocked\][[:space:]]+2026-01-05_mixed-cell-task[[:space:]]+blocked-by:.*2026-01-01_alpha-task'
refute "mixed cell does not block on the shares-contract slug" \
  '\[blocked\][[:space:]]+2026-01-05_mixed-cell-task[[:space:]]+blocked-by:.*2026-01-02_decoy-task'

# EDGE: a blocked-by naming an absent slug still warns as dangling.
assert "dangling blocked-by ref still warns" \
  'WARN dangling blocked-by refs:.*2026-01-06_dangling-task'

# CRITICAL 2 (backward compatibility): the headerless table has no Cross-links
# column to scope to, so the historical whole-row match must still fire.
assert "headerless fallback still reads its dependency" \
  '\[blocked\][[:space:]]+2026-02-02_legacy-task[[:space:]]+blocked-by:.*2026-02-01_legacy-blocker'

if [[ "$fail" -ne 0 ]]; then
  echo "RESULT: FAIL"
  exit 1
fi
echo "RESULT: PASS"
exit 0
