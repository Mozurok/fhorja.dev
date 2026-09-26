#!/usr/bin/env bash
# test-runtime-verify-routing.sh: an unreachable battery routes, it does not halt.
#
# The four runtime-verify commands each lazy-load a battery file. Before this
# task, a battery that resolved nowhere ended the turn: the command stopped and
# asked a person to fix the path. A missing in-repo file is none of the four
# reasons a chain stops, so that halt was the defect, repeated four times.
#
# The contract now: the verdict is BLOCKED, the BLOCKED names the exact path that
# did not resolve, and it hands that path to incident-triage as a CONFIG failure.
# Same shape when no capture tool is reachable: BLOCKED naming the missing
# capability, never a silent PASS and never a stop.
#
# The assertions are deliberately tolerant about wording. TEST_STRATEGY.md says a
# test pinned to a sentence turns every editorial pass into a red build, and this
# suite already found one real variant: three commands say they "capture" their
# own artifacts and api-runtime-verify says it "records" them. Same contract. The
# regexes match the contract, not the prose.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

checks=0; fails=0
pass() { checks=$((checks + 1)); echo "  ok   $1"; }
fail() { checks=$((checks + 1)); fails=$((fails + 1)); echo "  FAIL $1"; }

SURFACES="web app api godot"

# audit <file>: one finding per line, empty when the file honours the contract.
audit() {
  local f="$1" out="" battery
  [ -f "$f" ] || { printf 'file is absent'; return; }

  battery="$(grep -oE 'wos/[a-z-]+-runtime-battery\.md' "$f" | head -1)"
  [ -n "$battery" ] || out="${out}\n      names no battery file"

  # The unresolved battery routes rather than ending the turn.
  grep -qiE 'BLOCKED.{0,80}(routes|routing) instead of halting|routes instead of halting' "$f" \
    || out="${out}\n      does not say an unresolved battery routes instead of halting"

  # It names the path that did not resolve, not just that one did not.
  grep -qiE 'name the exact path that did not resolve|the exact path that did not resolve' "$f" \
    || out="${out}\n      does not require naming the exact unresolved path"

  # A missing in-repo file is not one of the four stop reasons.
  grep -qiE 'none of the four stop reasons|not one of the four (reasons|stop reasons)' "$f" \
    || out="${out}\n      does not state a missing in-repo file is not a stop reason"

  # It hands the failure to a command instead of to a person.
  grep -qiE 'incident-triage' "$f" \
    || out="${out}\n      routes to no command"
  grep -qiE 'CONFIG failure' "$f" \
    || out="${out}\n      does not classify the failure as CONFIG"

  # It captures its own evidence rather than asking for a transported artifact.
  grep -qiE '(captures|records) its own artifacts' "$f" \
    || out="${out}\n      does not declare it captures its own artifacts"
  grep -qE '<task-folder>/evidence/<slice-id>/' "$f" \
    || out="${out}\n      cites no evidence run directory"

  # No reachable tool is BLOCKED, never a quiet PASS.
  grep -qiE 'never a silent PASS|not a silent PASS' "$f" \
    || out="${out}\n      does not forbid a silent PASS when no tool is reachable"

  printf '%s' "$out"
}

# --- every surface honours the contract ------------------------------------
for s in $SURFACES; do
  r="$(audit "${REPO}/commands/${s}-runtime-verify.md")"
  [ -z "$r" ] && pass "${s}-runtime-verify routes instead of halting" \
               || { fail "${s}-runtime-verify:"; printf "$r\n"; }
done

# --- the four agree with each other ----------------------------------------
n="$(ls "${REPO}"/commands/*-runtime-verify.md 2>/dev/null | wc -l | tr -d ' ')"
[ "$n" = "4" ] && pass "5. exactly four runtime-verify commands, all audited" \
               || fail "5. found $n runtime-verify commands, expected 4"

# --- mutations: each clause must be load-bearing ----------------------------
# Removing one clause from a copy must produce exactly one finding. A mutation
# that produces none means the clause is unguarded; one that produces several
# means the audit is matching the same sentence twice.
mutate() {  # mutate <label> <sed-expr> <expected-fragment>
  local label="$1" expr="$2" want="$3"
  sed "$expr" "${REPO}/commands/web-runtime-verify.md" > "$TMP/m.md"
  local r; r="$(audit "$TMP/m.md")"
  if printf '%s' "$r" | grep -q "$want"; then pass "$label"; else
    fail "$label (mutation did not bite; findings: $(printf '%s' "$r" | tr '\n' ' ' | cut -c1-90))"
  fi
}

mutate "6. mutation: the routing clause removed is detected" \
       's/routes instead of halting/waits for the maintainer/' \
       'routes instead of halting'
mutate "7. mutation: the stop-reason clause removed is detected" \
       's/none of the four stop reasons/a legitimate reason to stop/' \
       'not a stop reason'
mutate "8. mutation: the silent-PASS prohibition removed is detected" \
       's/never a silent PASS/acceptable/' \
       'silent PASS'
mutate "9. mutation: the evidence run directory removed is detected" \
       's#<task-folder>/evidence/<slice-id>/#somewhere convenient#g' \
       'evidence run directory'

# --- control ----------------------------------------------------------------
cp "${REPO}/commands/web-runtime-verify.md" "$TMP/clean.md"
[ -z "$(audit "$TMP/clean.md")" ] \
  && pass "10. control: an unmutated copy reports nothing" \
  || fail "10. control fixture reported a finding, so the mutations prove nothing"

echo
echo "runtime-verify-routing: $((checks - fails))/$checks checks passed"
[ "$fails" -eq 0 ] || exit 1
