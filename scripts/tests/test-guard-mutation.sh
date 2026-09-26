#!/usr/bin/env bash
# test-guard-mutation.sh -- the mutation harness runs, and it catches a sleeping guard.
#
# Two assertions, and the second is the load-bearing one. Asserting only that the
# harness exits 0 would pass just as happily if every mutation silently stopped
# biting, which is the exact failure the harness exists to catch. So this also
# feeds it a guard that never fails and requires the harness to report ASLEEP and
# exit non-zero. A harness that cannot fail is the thing it was built to prevent.
#
# Exit codes: 0 all assertions hold, 1 otherwise.

set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || exit 1
fail=0

pass() { echo "  ok: $1"; }
bad()  { echo "  FAIL: $1"; fail=1; }

echo "test-guard-mutation: harness runs, and it catches a sleeping guard"

# 1. The harness runs green over the real check set.
OUT="$(python3 evals/scripts/guard-mutation.py 2>&1)"; rc=$?
if [ "$rc" -eq 0 ]; then pass "harness exits 0"; else bad "harness exits $rc: $OUT"; fi

if grep -q "Every control passed and every mutation bit." <<<"$OUT"; then
  pass "every control passed and every mutation bit"
else
  bad "harness did not report both directions clean"
fi

if grep -qE "^\[ASLEEP\]" <<<"$OUT"; then
  bad "a guard is asleep: $(grep -E '^\[ASLEEP\]' <<<"$OUT" | tr '\n' ' ')"
else
  pass "no guard reported ASLEEP"
fi

# The coverage line is reported, never claimed. Its absence would mean the harness
# stopped saying how much of the check set it does NOT cover.
#
# The wording changed on 2026-09-18 and so did the claim under it. It used to read
# "N of M check(s) mutation-tested" alongside "the remaining K read the real tree
# directly and cannot be mutation-tested until they take one". That second half
# stopped being true when structural-evals.py routed path resolution through _ROOT:
# a check with no `root=` parameter can now be pointed at a fixture through
# `fixture_root`. The gap moved from unreachable to unwritten, and the line says so.
# This assertion pins the INVARIANT, which is that both numbers keep being printed,
# rather than the sentence they sit in.
if grep -qE "^Coverage: [0-9]+ of [0-9]+ check\(s\) have a fixture and a mutation\." <<<"$OUT"; then
  pass "coverage is reported with both numbers"
else
  bad "no coverage line; the uncovered checks would go unmentioned"
fi

# The reachability half, added with the same change. A harness that stopped naming
# how each check is reached would hide whether the queue is shrinking.
if grep -qE "reachable: [0-9]+ by an explicit root= parameter and [0-9]+ through fixture_root" <<<"$OUT"; then
  pass "both reach routes are named with their counts"
else
  bad "the reachability split is missing; the queue's shape would be invisible"
fi

# And the honest limit stays printed: unwritten is not unreachable.
if grep -qE "unwritten, not unreachable" <<<"$OUT"; then
  pass "the report distinguishes unwritten from unreachable"
else
  bad "the report no longer distinguishes an unwritten fixture from an unreachable check"
fi

# 2. A guard that never fails MUST be caught. This is the meta-assertion.
META="$(python3 - <<'PY' 2>&1
import importlib.util, sys, io, contextlib
sp = importlib.util.spec_from_file_location("gm", "evals/scripts/guard-mutation.py")
gm = importlib.util.module_from_spec(sp)
sys.modules["gm"] = gm
sp.loader.exec_module(gm)
gm.se.check_never_fails = lambda root=None: (True, [])
gm.MUTATIONS = [("check_never_fails", gm.build_spec_root, gm.mutate_spec_over_ceiling)]
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = gm.main([])
print(f"rc={rc}")
print("asleep" if "[ASLEEP]" in buf.getvalue() else "missed")
PY
)"
if grep -q "rc=1" <<<"$META" && grep -q "asleep" <<<"$META"; then
  pass "a guard that never fails is reported ASLEEP and exits 1"
else
  bad "the harness did not catch a sleeping guard: $META"
fi

# 3. A guard that fails for the WRONG reason MUST be caught too. Added 2026-09-18
# with the `expect` field. Asserting only that the mutated check FAILS passes just
# as happily when the mutation broke the fixture instead of the rule: a check with
# a fail-closed branch fails on an empty subject, reports BITES, and looks proven
# while nothing about the branch under test was measured. Two mutations written
# that day destroyed their own fixture through `open(f, "w").write(open(f).read())`,
# where the write handle truncates before the read runs.
WRONG="$(python3 - <<'PY' 2>&1
import importlib.util, sys, io, contextlib
sp = importlib.util.spec_from_file_location("gm", "evals/scripts/guard-mutation.py")
gm = importlib.util.module_from_spec(sp)
sys.modules["gm"] = gm
sp.loader.exec_module(gm)
state = {"n": 0}
def fails_for_another_reason(root=None):
    state["n"] += 1
    if state["n"] == 1:
        return (True, [])
    return (False, ["the subject is missing; this check lost it rather than it becoming clean"])
gm.se.check_wrong_reason = fails_for_another_reason
gm.MUTATIONS = [("check_wrong_reason", gm.build_spec_root, gm.mutate_spec_over_ceiling,
                 "non-regression ceiling")]
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = gm.main([])
print(f"rc={rc}")
print("caught" if "WRONG REASON" in buf.getvalue() else "missed")
PY
)"
if grep -q "rc=1" <<<"$WRONG" && grep -q "caught" <<<"$WRONG"; then
  pass "a mutation that bites for the wrong reason is caught"
else
  bad "the harness accepted a failure for the wrong reason: $WRONG"
fi

# 4. Every entry names the branch it aimed at. Without this the field is optional in
# practice and a new entry silently opts out of assertion 3.
MISSING="$(python3 - <<'PY' 2>&1
import importlib.util, sys
sp = importlib.util.spec_from_file_location("gm", "evals/scripts/guard-mutation.py")
gm = importlib.util.module_from_spec(sp)
sys.modules["gm"] = gm
sp.loader.exec_module(gm)
bare = [e[0] for e in gm.MUTATIONS if len(e) < 4 or not e[3]]
print(len(bare), " ".join(sorted(set(bare))))
PY
)"
if [ "${MISSING%% *}" = "0" ]; then
  pass "every mutation entry states the finding it expects"
else
  bad "mutation entr(ies) with no expected finding: $MISSING"
fi

# 5. The exemption list stays honest. A name here is a claim that no failing input
# exists for that check, which is why it is a list of two things: the name and the
# reason. A stale name (a check that was deleted, or one that later grew a failing
# branch and got a fixture) would quietly shrink the number of checks the harness
# admits it has not covered.
EXEMPT="$(python3 - <<'PY' 2>&1
import importlib.util, sys
sp = importlib.util.spec_from_file_location("gm", "evals/scripts/guard-mutation.py")
gm = importlib.util.module_from_spec(sp)
sys.modules["gm"] = gm
sp.loader.exec_module(gm)
live = {c[3].__name__ for c in gm.se.CHECKS}
covered = {e[0] for e in gm.MUTATIONS}
problems = []
for name, why in gm.UNMUTABLE.items():
    if name not in live:
        problems.append(f"{name}: exempted but not in the live check set")
    if name in covered:
        problems.append(f"{name}: exempted AND carries a mutation; it is one or the other")
    if len(why) < 40:
        problems.append(f"{name}: exempted with no reason worth reading")
print(len(problems), "; ".join(problems))
PY
)"
if [ "${EXEMPT%% *}" = "0" ]; then
  pass "every exempted check is live, uncovered, and carries a reason"
else
  bad "the unmutable exemption list is stale: $EXEMPT"
fi

# The advisory line itself must keep being printed. Dropping it would leave the
# coverage number reading as though every check were mutation-testable.
if grep -q "Advisory by construction, no failing input exists:" <<<"$OUT"; then
  pass "a check that cannot fail is named, not silently counted as uncovered"
else
  bad "the report no longer names the checks that cannot be mutation-tested"
fi

# 6. The `warns:` direction has to be asserted too, and asserted the other way. An entry
# that expects a report must fail when the check HARDENS, or a tier change would slip by
# as silently as the softening the plain contract catches. Added 2026-09-21 with the
# advisory half of check_cwe_mapping_allowed.
WARNS="$(python3 - <<'PY' 2>&1
import importlib.util, sys, io, contextlib
sp = importlib.util.spec_from_file_location("gm", "evals/scripts/guard-mutation.py")
gm = importlib.util.module_from_spec(sp)
sys.modules["gm"] = gm
sp.loader.exec_module(gm)
state = {"n": 0}
def hardened(root=None):
    state["n"] += 1
    return (True, []) if state["n"] == 1 else (False, ["the extract is past its cadence"])
gm.se.check_hardened = hardened
gm.MUTATIONS = [("check_hardened", gm.build_spec_root, gm.mutate_spec_over_ceiling,
                 "warns:past its cadence")]
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = gm.main([])
print(f"rc={rc}")
print("caught" if "MUTATION FAILED THE BUILD" in buf.getvalue() else "missed")
PY
)"
if grep -q "rc=1" <<<"$WARNS" && grep -q "caught" <<<"$WARNS"; then
  pass "a warns: entry is caught when the check hardens instead"
else
  bad "the harness accepted a failure where it expected a report: $WARNS"
fi

if [ "$fail" -eq 0 ]; then
  echo "test-guard-mutation: PASS"
else
  echo "test-guard-mutation: FAIL"
fi
exit "$fail"
