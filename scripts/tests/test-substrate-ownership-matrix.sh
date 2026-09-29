#!/usr/bin/env bash
# test-substrate-ownership-matrix.sh -- the matrix parser keys rows by section, not by whatever
# survives trimming the cell.
#
# Why this exists. Measured 2026-08-30: the H2 table reader did `cells[0].strip("`")`, which only
# removes backticks at the two ENDS. A cell reading `## Locked decisions` (D-N) therefore keyed the
# row as "## Locked decisions` (D-N)", a string no writer ever names, so the row granted nothing
# while looking like coverage. 13 of 61 table rows were keyed that way, and the visible symptom was
# decision-interview heading the unauthorized list with 740 writes to a section it owns.
#
# The numbered-prose reader in the same file already used the correct idiom, `(## [^`]+)`, which is
# what makes this a slip rather than a design question. Nothing tested either reader; this covers
# the table half. It exercises parse_matrix directly against fixture matrices, never the real
# projects/ tree, so it runs anywhere the repo is checked out.
#
# Checks 6 onward cover ADR-0232, which made the matrix descriptive. The checker applies each
# grant the prose makes (approve-proposed promotions, the rule 2c whole-file operators on
# TASK_STATE.md only, the `### Slice N` row credited to `## Slices`), skips lines that are not
# writes to judge (a file with no matrix table, mode=proposed, event=refuse), and headlines the
# no-row count. Each grant and skip has a positive case and a mutation: the checker source is
# edited in a temp copy to drop that one rule, and the same case must then fail. A mutation whose
# target text is missing is itself a failure, so a refactor cannot turn a mutation into a no-op.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT" || exit 2

python3 - <<'PY'
import importlib.util, sys, tempfile, os, re

spec = importlib.util.spec_from_file_location("cso", "scripts/check-substrate-ownership.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)   # safe: the script guards its entry point with __main__

PASS = FAIL = 0
def ok(m):
    global PASS; PASS += 1; print(f"ok   - {m}")
def bad(m):
    global FAIL; FAIL += 1; print(f"FAIL - {m}")

def parse(text, cmds):
    fd, path = tempfile.mkstemp(suffix=".md"); os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    saved = mod.MATRIX
    try:
        mod.MATRIX = path
        return mod.parse_matrix(cmds)
    finally:
        mod.MATRIX = saved
        os.unlink(path)

CMDS = {"decision-interview", "approve-plan", "task-init", "slice-closure"}

# 1. The defect itself: a trailing qualifier after the closing backtick.
rows = parse(
    "| Section | Owner | Co-writers |\n|---|---|---|\n"
    "| `## Locked decisions` (D-N) | `decision-interview` | `approve-plan` |\n",
    CMDS)
if "## Locked decisions" in rows:
    ok("a row with a trailing qualifier keys on the section alone")
else:
    bad(f"trailing qualifier corrupted the key: {list(rows)!r}")
if not any("`" in k for k in rows):
    ok("no key carries a stray backtick")
else:
    bad(f"a key still carries a backtick: {[k for k in rows if '`' in k]!r}")

# 2. Authorization actually reaches the section, which is the point of the key.
auth = rows.get("## Locked decisions", (set(), False))[0]
if {"decision-interview", "approve-plan"} <= auth:
    ok("owner and co-writer both authorize the section")
else:
    bad(f"authorization did not reach the section: {sorted(auth)!r}")

# 3. A plain row, with no qualifier, is unaffected. The fix must not narrow what parsed before.
rows = parse(
    "| Section | Owner | Co-writers |\n|---|---|---|\n"
    "| `## Plain section` | `task-init` | none |\n",
    CMDS)
if "## Plain section" in rows and "task-init" in rows["## Plain section"][0]:
    ok("a plain row still parses")
else:
    bad(f"a plain row stopped parsing: {rows!r}")

# 4. A cell that names no section is still skipped, so the fix did not turn junk into rows.
rows = parse(
    "| Section | Owner | Co-writers |\n|---|---|---|\n"
    "| not a section at all | `task-init` | none |\n",
    CMDS)
if not rows:
    ok("a cell naming no section yields no row")
else:
    bad(f"junk became a row: {rows!r}")

# 5. The live matrix has zero corrupted keys. This is the regression that matters, and an empty
#    parse is a failure rather than a vacuous pass: the file has rows today.
live = mod.parse_matrix(CMDS) if os.path.isfile(mod.MATRIX) else {}
if not live:
    bad(f"{mod.MATRIX}: parsed no rows at all; the reader broke, not the matrix")
else:
    corrupt = [k for k in live if "`" in k]
    if corrupt:
        bad(f"{mod.MATRIX}: {len(corrupt)} key(s) still carry a backtick: {corrupt[:3]!r}")
    else:
        ok(f"{mod.MATRIX}: {len(live)} row(s) parsed, none with a stray backtick")

# ---- ADR-0232: grants, skips and the headline, each with a mutation --------------------------
import json, shutil, subprocess

SRC = open("scripts/check-substrate-ownership.py", encoding="utf-8").read()
WORK = tempfile.mkdtemp()

def load(src, tag):
    path = os.path.join(WORK, f"cso_{tag}.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    sp = importlib.util.spec_from_file_location(f"cso_{tag}", path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m

def mutant(old, new, tag):
    if SRC.count(old) != 1:
        bad(f"   mutation {tag}: target text not found exactly once in the checker; the "
            f"mutation would be a no-op")
        return None
    return load(SRC.replace(old, new), tag)

MATRIX_FIXTURE = (
    "## Section ownership matrix\n\n"
    "### TASK_STATE.md\n\n"
    "| Section (H2) | Owner | Co-writers (propose) | Readers |\n|---|---|---|---|\n"
    "| `## Current phase` | slice-closure | sync-task-state | all |\n"
    "| `## Risks to watch` | rls-auth-boundary-auditor | review-hard | all |\n\n"
    "### DECISIONS.md\n\n"
    "| Section | Owner | Co-writers | Readers |\n|---|---|---|---|\n"
    "| `## Locked decisions` (D-N) | decision-interview | direction-adjust | all |\n\n"
    "### IMPLEMENTATION_PLAN.md\n\n"
    "| Section | Owner | Co-writers | Readers |\n|---|---|---|---|\n"
    "| `## Slices` | implementation-plan | implement-slice-complement | all |\n"
    "| `### Slice N` (per-slice body) | implementation-plan | implement-approved-slice (status only) | all |\n"
)
FIX_CMDS = {"slice-closure", "sync-task-state", "rls-auth-boundary-auditor", "review-hard",
            "decision-interview", "direction-adjust", "implementation-plan",
            "implement-slice-complement", "implement-approved-slice", "approve-proposed",
            "state-reconcile", "compact-task-memory", "impact-analysis", "post-deploy-verifier"}

def line(owner, file, section, event="write", mode="applied"):
    return {"ts": "2026-09-23T00:00:00.000Z", "run_id": "01TEST", "owner": owner,
            "owner_type": "command", "invoked_by": None, "file": file, "section": section,
            "event": event, "mode": mode, "sha_before": None, "sha_after": "0" * 64,
            "reason": "fixture", "partials": None, "strategy": None}

def fixture(lines):
    root = tempfile.mkdtemp(dir=WORK)
    wos = os.path.join(root, "projects", "c__p", "active", "2026-09-23_t", ".wos")
    os.makedirs(wos)
    with open(os.path.join(wos, "VERIFICATION_LOG.jsonl"), "w", encoding="utf-8") as f:
        for d in lines:
            f.write(json.dumps(d) + "\n")
    mpath = os.path.join(root, "substrate-peers.md")
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(MATRIX_FIXTURE)
    return root, mpath

def run(m, lines):
    root, mpath = fixture(lines)
    m.set_matrix(mpath)
    m.set_logs_root(root)
    return m.scan(m.parse_matrix(FIX_CMDS), mfiles=m.matrix_files())

def nbad(r): return sum(r["bad"].values())
def nrow(r): return sum(r["norow"].values())

try:
    base = load(SRC, "base")
    for need in ("set_logs_root", "matrix_files"):
        if not hasattr(base, need):
            raise AttributeError(f"the checker has no {need}()")
except Exception as e:
    base = None
    bad(f"the checker does not support the ADR-0232 checks: {e}")

CASES = []  # (label, log lines, predicate on the scan result, [(mutation old, new, tag), ...])

# 6. Grant: approve-proposed lands a block staged in a section it does not own (rule 3).
CASES.append(("6. approve-proposed promoting a staged block is granted (rule 3)",
    [line("approve-proposed", "TASK_STATE.md", "## Risks to watch", event="approve")],
    lambda r: nbad(r) == 0 and r["hatched"].get(
        "promotion (rule 3, approve-proposed lands a staged block)") == 1,
    [("            if own == PROMOTER:\n", "            if False:\n", "no-promoter")]))

# 7. Grant: rule 2c, the whole-file operators on TASK_STATE.md, and only there.
CASES.append(("7. state-reconcile and compact-task-memory are granted on TASK_STATE.md only (rule 2c)",
    [line("state-reconcile", "TASK_STATE.md", "## Current phase"),
     line("compact-task-memory", "active/x/TASK_STATE.md", "## Risks to watch"),
     line("compact-task-memory", "DECISIONS.md", "## Locked decisions")],
    lambda r: r["hatched"].get("whole-file operators (rule 2c, TASK_STATE.md only)") == 2
              and r["bad"].get(("compact-task-memory", "## Locked decisions")) == 1 and nbad(r) == 1,
    [("            if own in WHOLE_FILE_OPERATORS and fname == WHOLE_FILE_TARGET:\n",
      "            if False:\n", "no-2c"),
     ("            if own in WHOLE_FILE_OPERATORS and fname == WHOLE_FILE_TARGET:\n",
      "            if own in WHOLE_FILE_OPERATORS:\n", "2c-any-file")]))

# 8. Grant: the `### Slice N` row is credited to `## Slices`, where its co-writes are logged.
CASES.append(("8. the `### Slice N` row credits its co-writers at `## Slices`",
    [line("implement-approved-slice", "IMPLEMENTATION_PLAN.md", "## Slices")],
    lambda r: nbad(r) == 0 and nrow(r) == 0,
    [('H3_PARENT = {"### Slice N": "## Slices"}', "H3_PARENT = {}", "no-h3")]))

# 9. Skip: a file that carries no matrix table is not a no-row write; a table file still is.
CASES.append(("9. a file with no matrix table is skipped, an unlisted section of a table file is not",
    [line("impact-analysis", "IMPACT_ANALYSIS.md", "## Blast radius"),
     line("impact-analysis", "TASK_STATE.md", "## Not in the matrix")],
    lambda r: nrow(r) == 1 and r["norow"].get(("impact-analysis", "## Not in the matrix")) == 1
              and r["skipped"].get("file with no matrix table (no row could cover it)") == 1,
    [("            if mfiles and fname and fname not in mfiles:\n", "            if False:\n",
      "no-file-skip")]))

# 10. Skip: a staged block (mode=proposed) and a refused fleet merge (event=refuse) are not writes.
CASES.append(("10. mode=proposed and event=refuse lines are not counted as writes",
    [line("post-deploy-verifier", "TASK_STATE.md", "## Risks to watch", event="propose",
          mode="proposed"),
     line("post-deploy-verifier", "TASK_STATE.md", "## Current phase", event="refuse")],
    lambda r: nbad(r) == 0 and sum(r["skipped"].values()) == 2,
    [('            if d.get("mode") == "proposed":\n', "            if False:\n", "no-proposed-skip"),
     ('            if d.get("event") == "refuse":\n', "            if False:\n", "no-refuse-skip")]))

if base is not None:
    for label, lines, pred, muts in CASES:
        try:
            r = run(base, lines)
            if pred(r):
                ok(label)
            else:
                bad(f"{label}: bad={dict(r['bad'])} norow={dict(r['norow'])} "
                    f"hatched={dict(r['hatched'])} skipped={dict(r['skipped'])}")
        except Exception as e:
            bad(f"{label}: raised {e!r}")
        for old, new, tag in muts:
            m = mutant(old, new, tag)
            if m is None:
                continue
            try:
                bit = not pred(run(m, lines))
            except Exception:
                bit = True
            if bit:
                ok(f"   mutation {tag}: the case fails without the rule")
            else:
                bad(f"   mutation {tag}: the case still passes, so it proves nothing")

# 11-14. The headline is the no-row count, --logs-root points the scan, --strict follows it.
def cli(args):
    return subprocess.run([sys.executable, "scripts/check-substrate-ownership.py", *args],
                          capture_output=True, text=True)

root, mpath = fixture([line("impact-analysis", "TASK_STATE.md", "## Not in the matrix"),
                       line("review-hard", "DECISIONS.md", "## Locked decisions")])
res = cli(["--matrix", mpath, "--logs-root", root])
head = (res.stdout.splitlines() or [""])[0]
if res.returncode == 0 and re.match(
        r"^Substrate-ownership: 1 write\(s\) to a section with no matrix row across 1 of 1 ", head):
    ok("11. --logs-root scans the fixture and the headline leads with the no-row count")
else:
    bad(f"11. headline or --logs-root wrong: rc={res.returncode} head={head!r} "
        f"err={res.stderr[-200:]!r}")
if "1 write(s) outside the conventional owner" in head:
    ok("12. the outside-owner count follows the headline, labelled recorded not refused")
else:
    bad(f"12. the outside-owner count is missing from the headline: {head!r}")
rs = cli(["--matrix", mpath, "--logs-root", root, "--strict"])
root2, mpath2 = fixture([line("review-hard", "DECISIONS.md", "## Locked decisions")])
rs2 = cli(["--matrix", mpath2, "--logs-root", root2, "--strict"])
if rs.returncode == 1 and rs2.returncode == 0:
    ok("13. --strict exits 1 on a no-row write and 0 when only outside-owner writes remain")
else:
    bad(f"13. --strict exits {rs.returncode} with a no-row write and {rs2.returncode} without")
rm = cli(["--logs-root", os.path.join(WORK, "absent")])
if rm.returncode == 2:
    ok("14. --logs-root naming no directory is a usage error (exit 2)")
else:
    bad(f"14. --logs-root naming no directory exited {rm.returncode}")

# 15-16. The live matrix carries the rows ADR-0232 and the one-slice route rely on.
if base is not None:
    base.set_matrix(os.path.join(os.getcwd(), "wos", "substrate-peers.md"))
    # command_names() reads commands/ beside the module file, so it comes from the module loaded
    # in place (mod), not from the temp copy, which has no commands/ beside it.
    real = base.parse_matrix(mod.command_names())
    sl = real.get("## Slices", (set(), False))[0]
    al = real.get("## Approval log", (set(), False))[0]
    want = {"implement-approved-slice", "implement-fleet", "slice-closure", "task-init"}
    pv = real.get("## Provisional decisions", (set(), False))[0]
    if want <= sl and "task-init" in al and "task-init" in pv:
        ok("15. live matrix: `## Slices` carries the `### Slice N` co-writers and task-init; "
           "`## Approval log` and `## Provisional decisions` (ADR-0239) carry task-init")
    else:
        bad(f"15. live matrix rows missing: ## Slices lacks {sorted(want - sl)}, "
            f"## Approval log has task-init={'task-init' in al}, "
            f"## Provisional decisions has task-init={'task-init' in pv}")
    mf = base.matrix_files()
    need = {"TASK_STATE.md", "DECISIONS.md", "IMPLEMENTATION_PLAN.md", "SOURCE_OF_TRUTH.md"}
    if need <= mf:
        ok(f"16. live matrix: {len(mf)} file(s) carry a table, the four task-memory files among them")
    else:
        bad(f"16. live matrix tables missing for {sorted(need - mf)}")

# 17-18. No live text requires a refusal for an ownership conflict, and event=refuse stays valid
#        for the fleet orphan scan. Each retired phrase is the exact text that stated the rule.
RETIRED = {
    "WORKFLOW_OPERATING_SYSTEM.md": ["REFUSE + Handoff", "CO-WRITERS (propose-only via PROPOSED blocks)"],
    "wos/substrate-peers.md": ["**REFUSES** and emits a Handoff", "REFUSE conflicts emit `event=refuse`",
                               "REFUSE both. Emit Handoff"],
    "commands/_shared/substrate-write-protocol.md": ["For REFUSE conflicts (writer is not the owner"],
}
left = [f"{f}: {ph!r}" for f, phs in RETIRED.items()
        for ph in phs if ph in open(f, encoding="utf-8").read()]
if left:
    bad(f"17. an ownership refusal is still stated: {left}")
else:
    ok("17. no live spec, topic or protocol text requires a refusal for an ownership conflict")
still = ("\"refuse\"" in open("scripts/verify-log-validator.py", encoding="utf-8").read()
         and "`refuse`" in open("commands/_shared/substrate-write-protocol.md", encoding="utf-8").read())
if still:
    ok("18. event=refuse stays in the validator and the protocol taxonomy (fleet orphan scan)")
else:
    bad("18. event=refuse left the taxonomy; screen-spec-fleet and atom-audit-fleet still emit it")

shutil.rmtree(WORK, ignore_errors=True)

print()
print(f"test-substrate-ownership-matrix: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
PY
