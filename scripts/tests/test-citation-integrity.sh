#!/usr/bin/env bash
# test-citation-integrity.sh: the attribution checker finds a planted defect and
# stays quiet on a correct citation.
#
# The point of this suite is the second half. A checker that reports clean because
# its heading matcher silently found nothing is worse than no checker, and the
# first version of check-citation-integrity.py did exactly that: it matched
# `## Audit trail` exactly against a heading that reads
# `## Audit trail (VERIFICATION_LOG.jsonl)`, found no section, and reported clean
# over seven real defects. Check 4 is the regression guard for that.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CHECKER="${REPO_ROOT}/scripts/check-citation-integrity.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

# 1. The real tree is clean. Any finding here is a live defect, not a test bug.
OUT="$(python3 "$CHECKER" 2>&1)"
if grep -qE '^Citation-integrity: [0-9]+ attribution\(s\) checked .*, 0 unresolved' <<<"$OUT"; then
  pass "the repository reports zero unresolved attributions"
else
  fail "the repository has unresolved attributions (or the summary line changed)"
  echo "$OUT" | tail -6
fi

# 2. It checks a non-trivial number of them. A checker whose matchers all miss
#    reports zero findings AND zero checked, which reads identical to clean.
N="$(grep -oE '^Citation-integrity: [0-9]+' <<<"$OUT" | grep -oE '[0-9]+' || echo 0)"
if [ "${N:-0}" -ge 50 ]; then
  pass "checked ${N} attributions (a matcher that silently matches nothing cannot pass this)"
else
  fail "only ${N} attributions checked; a matcher is probably finding nothing"
fi

# 3. It finds a planted count defect.
WORK="$TMP/repo"
mkdir -p "$WORK/scripts" "$WORK/commands" "$WORK/wos" "$WORK/templates"
cp "$CHECKER" "$WORK/scripts/"
cp "${REPO_ROOT}/wos/substrate-peers.md" "$WORK/wos/"
cp "${REPO_ROOT}/templates/LEARNINGS.md" "$WORK/templates/"
printf 'Append a 4-bullet entry to `LEARNINGS.md` per the template.\n' > "$WORK/commands/planted.md"
OUT3="$(python3 "$WORK/scripts/check-citation-integrity.py" 2>&1)"
if grep -q 'claims 4 required bullets' <<<"$OUT3"; then
  pass "a planted 4-bullet claim is reported against the template's 5"
else
  fail "the planted count defect was not found"
  echo "$OUT3" | tail -4
fi

# 4. Regression guard for the silent-miss bug: the section matcher must resolve a
#    heading cited without its parenthetical.
if python3 - "$WORK" <<'PY'
import sys, os, re, io
sys.path.insert(0, os.path.join(sys.argv[1], "scripts"))
src = io.open(os.path.join(sys.argv[1], "scripts", "check-citation-integrity.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(sys.argv[1], "scripts", "check-citation-integrity.py")}
exec(compile(src.split('def main(')[0], "checker", "exec"), ns)
body = io.open(os.path.join(sys.argv[1], "wos", "substrate-peers.md"), encoding="utf-8").read()
sec = ns["section_body"](body, "## Audit trail")
sys.exit(0 if sec and len(sec) > 500 else 1)
PY
then
  pass "'## Audit trail' resolves the heading that carries a parenthetical"
else
  fail "the section matcher does not resolve a heading cited without its parenthetical"
fi

echo
if [ "$fails" -eq 0 ]; then echo "test-citation-integrity: all $checks checks passed"; exit 0
else echo "test-citation-integrity: $fails of $checks check(s) FAILED"; exit 1; fi
