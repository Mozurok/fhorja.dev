#!/usr/bin/env bash
# test-build-agent-skills-markers.sh: the generated skills carry no maintenance markers.
#
# A `<!-- shared:<name> -->` line and a `<!-- count:<kind> -->N<!-- /count -->` wrapper are
# read by sync-shared-blocks.sh, reconcile-counts.sh and the lint in commands/*.md. Nothing
# reads them in .claude/skills/, where they only cost the Load stage characters. ADR-0227 has
# build-agent-skills.sh drop them from the generated copy. This pins three things: the real
# corpus is clean, the builder strips only the exact marker forms (a quoted example in prose
# and anything inside a fenced block stay as written), and the command source keeps its
# markers so the checks that read them still work.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
checks=0; fails=0
pass() { checks=$((checks+1)); echo "  ok   $1"; }
fail() { checks=$((checks+1)); fails=$((fails+1)); echo "  FAIL $1"; }

# 1. The real corpus.
n="$(ls "${REPO}"/.claude/skills/*/SKILL.md 2>/dev/null | wc -l | tr -d ' ')"
if [ "$n" -eq 0 ]; then
  fail "1. no generated skills at .claude/skills; this test lost its subject"
else
  hits="$(grep -lE '^<!-- shared:[a-z-]+ -->[[:space:]]*$|<!-- count:[a-z0-9-]+ -->[0-9]+<!-- /count -->' \
    "${REPO}"/.claude/skills/*/SKILL.md 2>/dev/null || true)"
  [ -z "$hits" ] \
    && pass "1. none of the $n generated skills carries a shared or count marker" \
    || fail "1. markers survive in: $(printf '%s' "$hits" | head -3 | tr '\n' ' ')"
fi

# 2-6. A fixture root: the builder resolves every path from its own location.
ROOT="$TMP/root"
mkdir -p "$ROOT/scripts" "$ROOT/commands"
for f in build-agent-skills.sh emit-skill-frontmatter.py emit-skill-contract-summary.py; do
  cp "${REPO}/scripts/$f" "$ROOT/scripts/"
done
awk 'NR==1 || c<2 { print } /^---$/ { c++ }' "${REPO}/commands/capture-observation.md" \
  | sed 's/^name: capture-observation$/name: marker-fixture/' > "$ROOT/commands/marker-fixture.md"
cat >> "$ROOT/commands/marker-fixture.md" <<'EOF'
# marker-fixture

### Handoff
<!-- shared:handoff-body -->
Body line.
There are <!-- count:skills -->98<!-- /count --> skills.
Prose may quote the form `<!-- count:KIND -->N<!-- /count -->` without losing it.
```text
<!-- shared:inside-a-fence -->
<!-- count:skills -->98<!-- /count -->
```
EOF
cp "$ROOT/commands/marker-fixture.md" "$TMP/source-before.md"
out="$(bash "$ROOT/scripts/build-agent-skills.sh" 2>&1)"; rc=$?
SKILL="$ROOT/.claude/skills/marker-fixture/SKILL.md"
if [ "$rc" -ne 0 ] || [ ! -f "$SKILL" ]; then
  fail "2. the builder did not produce the fixture skill (rc=$rc): $(printf '%s' "$out" | tail -2)"
else
  body="$(awk 'c>=2 { print } /^---$/ { c++ }' "$SKILL")"
  grep -qx '<!-- shared:handoff-body -->' <<<"$(printf '%s' "$body" | sed -n '1,/^```text$/p')" \
    && fail "2. the shared marker line survived outside the fence" \
    || pass "2. the shared marker line is dropped"
  grep -qF 'There are 98 skills.' <<<"$body" \
    && pass "3. a count wrapper becomes its bare number" \
    || fail "3. the count wrapper was not reduced to its number"
  grep -qF '`<!-- count:KIND -->N<!-- /count -->`' <<<"$body" \
    && pass "4. a quoted marker example in prose stays as written" \
    || fail "4. the quoted example was altered"
  fence="$(printf '%s\n' "$body" | sed -n '/^```text$/,/^```$/p')"
  if grep -qx '<!-- shared:inside-a-fence -->' <<<"$fence" && grep -qF '<!-- count:skills -->98<!-- /count -->' <<<"$fence"; then
    pass "5. markers inside a fenced block are left alone"
  else
    fail "5. the fenced block was rewritten"
  fi
  cmp -s "$TMP/source-before.md" "$ROOT/commands/marker-fixture.md" \
    && pass "6. the command source keeps its markers for the checks that read them" \
    || fail "6. the builder changed the command source"
  chk="$(bash "$ROOT/scripts/build-agent-skills.sh" --check 2>&1)"; crc=$?
  [ "$crc" -eq 0 ] \
    && pass "7. --check is clean right after a build (the strip is deterministic)" \
    || fail "7. --check reports drift after a build: $(printf '%s' "$chk" | tail -3 | tr '\n' ' ')"
fi

echo
echo "build-agent-skills-markers: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
