#!/usr/bin/env bash
# test-agents-section-refs.sh: a citation to a NUMBERED section of AGENTS.md must
# stop resolving when that section is renumbered.
#
# WHY. The rule that changing a rule needs a superseding ADR lives in a numbered
# section of AGENTS.md, and seven other places cite it by number. Inserting a
# section renumbers everything below and every citation goes stale in silence:
# check-doc-sync.sh did not read AGENTS.md at all and resolved headings only inside
# the spec.
#
# HOW THE FIXTURE WORKS, because the first attempt at it proved nothing. The
# checker does `cd` to a ROOT derived from its OWN location, so running it from a
# temp directory scanned the real repository and returned the same 7223 refs in
# both directions. The script is therefore COPIED into the fixture's scripts/ dir,
# which is what makes ROOT the fixture.
#
# Since 2026-09-23 this is the fixture suite for check-doc-sync.sh as a whole:
# checks 8 to 15 cover the file paths, bug classes, relative links, wos topic
# sections and next-step command names it learned to resolve after the docs
# drift audit (gap 5).
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC="${REPO}/scripts/check-doc-sync.sh"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
checks=0; fails=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); fails=$((fails+1)); echo "  FAIL $1"; }
[ -f "$SRC" ] || { echo "  FAIL $SRC missing"; exit 1; }

build() {  # build <dir> <agents-body> <citing-body>
  local d="$TMP/$1"; mkdir -p "$d/scripts"
  cp "$SRC" "$d/scripts/"
  printf '%s\n' "$2" > "$d/AGENTS.md"
  printf '%s\n' "$3" > "$d/CLAUDE.md"
  printf '# WOS\n' > "$d/WORKFLOW_OPERATING_SYSTEM.md"
  echo "$d"
}
run() { ( cd "$1" && bash scripts/check-doc-sync.sh >out.txt 2>&1; echo $? ); }

AG6='# AGENTS.md

## 1. One

## 6. Changing a rule'
AG7='# AGENTS.md

## 1. One

## 7. Changing a rule'
CITE='# CLAUDE.md

How a rule changes is `AGENTS.md` section 6.'
NOCITE='# CLAUDE.md

How a rule changes is described in AGENTS.md.'

d="$(build resolves "$AG6" "$CITE")"
[ "$(run "$d")" = "0" ] && pass "1. a citation that resolves passes" || fail "1. a resolving citation was refused"
grep -q "1 refs verified" "$d/out.txt" \
  && pass "2. the citation was actually COUNTED, not skipped into a vacuous pass" \
  || fail "2. verified count does not show the citation being checked"

d="$(build renumbered "$AG7" "$CITE")"
[ "$(run "$d")" = "1" ] && pass "3. a renumbered section refuses" || fail "3. renumbering did not refuse"
grep -q "BROKEN agents-section ref 'AGENTS.md section 6'" "$d/out.txt" \
  && pass "4. the refusal names the exact stale citation" || fail "4. refusal does not name the citation"

d="$(build nocite "$AG7" "$NOCITE")"
[ "$(run "$d")" = "0" ] && pass "5. a file naming AGENTS.md with no section number is not a finding" \
  || fail "5. false positive on a file with no section citation"

# The fixture's own control: checks 1 and 3 must differ, or the fixture is inert.
a="$(run "$(build c1 "$AG6" "$CITE")")"; b="$(run "$(build c2 "$AG7" "$CITE")")"
[ "$a" != "$b" ] && pass "6. control: the two fixtures produce DIFFERENT exit codes" \
  || fail "6. control: both fixtures returned $a, so checks 1 and 3 prove nothing"

# AGENTS.md is in the surface list, so its own outbound refs are scanned too.
grep -qE '^AGENTS\.md$' <(sed -n '/^SURFACES=/,/^"$/p' "$SRC") \
  && pass "7. AGENTS.md is a scanned surface" || fail "7. AGENTS.md is not in SURFACES"

# --- 8-15. paths, bug classes, links, sections and next-step names (docs drift audit, gap 5)
# The same fixture harness, pointed at the kinds of reference check-doc-sync did not
# read until 2026-09-23. Each mutation reintroduces one shape the audit found live,
# and each must be refused by kind, not merely make the exit code non-zero.
build_refs() {  # build_refs <dir> <claude-body> [adr-body]
  local d
  d="$(build "$1" "$AG6" "$2")"
  mkdir -p "$d/commands" "$d/templates" "$d/wos/bug-classes" "$d/docs/adr"
  printf '# what-next\n' > "$d/commands/what-next.md"
  printf '# review-hard\n' > "$d/commands/review-hard.md"
  printf '# t\n' > "$d/templates/REAL.template.md"
  printf '# c\n' > "$d/wos/bug-classes/real-class.md"
  printf '%s\n' "${3:-# ADR-0001: a}" > "$d/docs/adr/0001-a.md"
  echo "$d"
}
REFS_OK='# CLAUDE.md

Start from `templates/REAL.template.md`; the sweep applies `wos/bug-classes/real-class.md`.
Run now: what-next
A routing command (`what-next`, `review-hard`) emits only a Handoff.
**Bug class:** `real-class`'

d="$(build_refs refs-ok "$REFS_OK" "See [the other](./0001-a.md).")"
[ "$(run "$d")" = "0" ] && pass "8. control: resolving paths, a bug class, a next step, a command list and a link pass" \
  || fail "8. control refused: $(cat "$d/out.txt")"

d="$(build_refs refs-path "${REFS_OK/REAL.template.md/ADR.template.md}")"
[ "$(run "$d")" = "1" ] && grep -q "BROKEN path ref 'templates/ADR.template.md'" "$d/out.txt" \
  && pass "9. mutation: a path to a template that does not exist is refused by name" \
  || fail "9. a missing template path was not refused: $(cat "$d/out.txt")"

d="$(build_refs refs-bug "${REFS_OK/\`real-class\`/\`inline-style-object\`}")"
[ "$(run "$d")" = "1" ] && grep -q "BROKEN bug-class ref 'inline-style-object'" "$d/out.txt" \
  && pass "10. mutation: a bug class that was never written is refused by name" \
  || fail "10. a missing bug class was not refused: $(cat "$d/out.txt")"

d="$(build_refs refs-next "${REFS_OK/Run now: what-next/Run now: device-verify}")"
[ "$(run "$d")" = "1" ] && grep -q "BROKEN next-step ref 'device-verify'" "$d/out.txt" \
  && pass "11. mutation: an unknown command after Run now: is a failure, not a --strict warning" \
  || fail "11. an unknown next step was not refused: $(cat "$d/out.txt")"

d="$(build_refs refs-list "${REFS_OK/\`review-hard\`/\`command-router\`}")"
[ "$(run "$d")" = "1" ] && grep -q "BROKEN command-list ref 'command-router'" "$d/out.txt" \
  && pass "12. mutation: an unknown name in a list of commands is refused by name" \
  || fail "12. an unknown name in a command list was not refused: $(cat "$d/out.txt")"

d="$(build_refs refs-link "$REFS_OK" "See [the other](./0207-a-renamed-adr.md).")"
[ "$(run "$d")" = "1" ] && grep -q "BROKEN link ref './0207-a-renamed-adr.md'" "$d/out.txt" \
  && pass "13. mutation: a relative link in an ADR to a renamed file is refused by name" \
  || fail "13. a broken ADR link was not refused: $(cat "$d/out.txt")"

d="$(build_refs refs-absent "# CLAUDE.md

The detector (\`scripts/lint/detect-x.sh\`) does not exist; the scenario awaits a decision.
Not a Fhorja command: never write \`Run now: device-verify\` or any slash command.")"
[ "$(run "$d")" = "0" ] && pass "14. control: a line naming a path or a name to say it is absent is not a finding" \
  || fail "14. a line stating an absence was refused: $(cat "$d/out.txt")"

d="$(build_refs refs-section '# CLAUDE.md

See `wos/example.md` (section "Parallel batch sizing") and `wos/example.md` `## Fan-out floor`.')"
printf '# Example\n\n## Fan-out floor\n\nBody.\n' > "$d/wos/example.md"
[ "$(run "$d")" = "1" ] && grep -q "BROKEN topic-section ref 'wos/example.md Parallel batch sizing'" "$d/out.txt" \
  && ! grep -q "Fan-out floor" "$d/out.txt" \
  && pass "15. mutation: a wos topic section that does not exist is refused, and one that does is not" \
  || fail "15. a missing topic section was not refused, or a real one was: $(cat "$d/out.txt")"

# --- 16-18. the scan set reaches the three files that carried live citations (ADR-0225)
# The renumber check found "AGENTS.md section 6" in CONTRIBUTING.md, docs/adr/README.md
# and .github/pull_request_template.md, and no loop of this script read any of them.
# Each fixture keeps CLAUDE.md clean, so the only stale citation is in the widened file.
for w in CONTRIBUTING.md docs/adr/README.md .github/pull_request_template.md; do
  n=$((checks + 1))
  d="$(build "wide-$n" "$AG7" "$NOCITE")"
  mkdir -p "$d/$(dirname "$w")"
  printf '%s\n' "$CITE" > "$d/$w"
  [ "$(run "$d")" = "1" ] && grep -q "BROKEN agents-section ref 'AGENTS.md section 6' in $w" "$d/out.txt" \
    && pass "$n. a stale section citation in $w is refused" \
    || fail "$n. $w is not scanned: $(cat "$d/out.txt")"
done

echo
echo "agents-section-refs: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
