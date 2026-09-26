#!/usr/bin/env bash
# test-live-markers.sh: a live unresolved-clarification marker must be caught and
# prose ABOUT the marker must not. Fixtures are built here rather than pointed at
# real task folders, whose paths carry client names that never enter a tracked file.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CHK="${REPO}/scripts/check-live-markers.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
checks=0; fails=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); fails=$((fails+1)); echo "  FAIL $1"; }
[ -x "$CHK" ] || { echo "  FAIL $CHK not executable"; exit 1; }

mk() { local d="$TMP/$1"; mkdir -p "$d"; printf '%s\n' "$2" > "$d/IMPLEMENTATION_PLAN.md"; echo "$d"; }
rc() { "$CHK" "$1" >/dev/null 2>&1; echo $?; }

# Shapes copied from the corpus, not invented.
LIVE='## Open questions or approvals still needed

- [NEEDS CLARIFICATION: the environments in scope are unknown | confirm each one | user supplies access]'
PROSE='## Open questions or approvals still needed

No `[NEEDS CLARIFICATION:]` markers remain in the plan.'
PROSE2='## Validation expectations

Zero `[NEEDS CLARIFICATION:` markers. Two backticked mentions appear above.'
FENCED='## Notes

```
- [NEEDS CLARIFICATION: this is inside a fence and is an example, not a marker]
```'
BOTH='## Open questions or approvals still needed

No `[NEEDS CLARIFICATION:]` markers remain, except:
- [NEEDS CLARIFICATION: one actually does remain]'

[ "$(rc "$(mk live "$LIVE")")" = "1" ]  && pass "1. a live marker is caught" || fail "1. live marker missed"
[ "$(rc "$(mk prose "$PROSE")")" = "0" ] && pass "2. prose denying the marker is not caught" || fail "2. false positive on prose"
[ "$(rc "$(mk prose2 "$PROSE2")")" = "0" ] && pass "3. a second real prose form is not caught" || fail "3. false positive on second prose form"
[ "$(rc "$(mk fenced "$FENCED")")" = "0" ] && pass "4. a marker inside a fenced block is an example, not a marker" || fail "4. fenced example counted"
[ "$(rc "$(mk both "$BOTH")")" = "1" ] && pass "5. prose AND a live marker still refuses" || fail "5. a live marker hidden beside prose was missed"

# A folder with no plan at all is not a verdict of clean. Until 2026-09-23 this check asserted
# exit 0 here, so it pinned the defect: "Live-markers: none" on three files nobody read, which
# approve-plan read as permission to continue (ADR-0224).
empty="$TMP/empty"; mkdir -p "$empty"
out="$("$CHK" "$empty" 2>&1)"; code=$?
[ "$code" = "2" ] && printf '%s' "$out" | grep -q 'Live-markers: not scanned' \
  && pass "6. a folder with none of the three files exits 2 and says not scanned" \
  || fail "6. empty folder gave exit $code: $out"
"$CHK" "$TMP/no-such-folder" >/dev/null 2>&1
[ $? -eq 2 ] && pass "7. a missing folder exits 2, distinct from a clean verdict" || fail "7. missing folder not distinguished from clean"

# The defect that produced this file: an awk dynamic regex on a marker opening with
# `[` read as an unterminated character class, and BOTH directions returned 0.
# This check fails if the checker ever stops discriminating at all.
[ "$(rc "$(mk live2 "$LIVE")")" != "$(rc "$(mk prose3 "$PROSE")")" ] \
  && pass "8. control: the checker discriminates, it does not return one answer for everything" \
  || fail "8. control: live and prose returned the SAME code, so checks 1 and 2 prove nothing"

# The command consumes it rather than eyeballing the file.
grep -q 'bash scripts/check-live-markers.sh <task-folder>' "${REPO}/commands/approve-plan.md" \
  && pass "9. approve-plan runs the checker" || fail "9. approve-plan does not run the checker"

echo
echo "live-markers: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
