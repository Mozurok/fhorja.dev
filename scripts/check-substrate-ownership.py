#!/usr/bin/env python3
"""Cross-check what commands actually wrote against the ownership matrix.

The matrix in `wos/substrate-peers.md` assigns one conventional owner and a
co-writer set to each substrate H2. Since ADR-0232 it is descriptive: a write
outside a row is recorded and counted, never refused. So the number someone acts
on is the HEADLINE: writes to a section the matrix has no row for, which are
gaps in the description. Writes outside the conventional owner are reported
after it, as the measurement ADR-0232 was decided on, not as violations.

WHAT THIS IS. The input is `.wos/VERIFICATION_LOG.jsonl`, which is what each
command REPORTED writing. It is self-reported, so a writer that names someone
else as owner is invisible here. That limit is the point rather than a flaw:
the repair target is the matrix, and a command that honestly reports writing a
section nobody granted it is exactly the row that is missing.

The static half of this check (does every command name in the matrix exist on
disk) is implemented and currently reports zero. The matrix has no stale names;
it has missing rows.

ESCAPE HATCHES are applied by name and counted, never silently. The prose grants
several, and two independent readings of them differed by about a thousand lines,
so each allowance is reported with the number of lines it absorbed. The grants
applied are the ones the prose makes: genesis (rule 2a), the pattern writers
(rule 2b), the whole-file operators on TASK_STATE.md only (rule 2c), approve-
proposed promoting a staged block (rule 3), `## Observations` (any command), and
the `### Slice N` row, whose co-writes are logged at `## Slices`.

SKIPPED LINES are not writes to judge, and each skip is counted by name: a line
with mode=proposed (a staged block, not a write), a line with event=refuse (a
fleet merge its orphan scan refused), and a line whose file carries no matrix
table (IMPACT_ANALYSIS.md, a slice note), which no row could ever cover.

Exit codes: 0 always, unless --strict, which returns 1 when any write to a
section with no matrix row survives. Advisory by default.
"""
import argparse, collections, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MATRIX = os.path.join(REPO, "wos", "substrate-peers.md")
LOGS_ROOT = REPO

# An H3 row is logged at its owning H2 (commands/_shared/substrate-write-protocol.md, the
# H3-scoped co-write rule), so its grants belong to that H2. The table reader keyed rows only on
# a backticked `## ` span, which "`### Slice N`" can never match, so the row granted nothing
# and every status write by implement-approved-slice and implement-fleet read as unauthorized
# (546 lines by those two on 2026-09-23).
H3_PARENT = {"### Slice N": "## Slices"}

# Rule 2c: the two whole-file operators co-write any TASK_STATE.md section, and only that file.
WHOLE_FILE_OPERATORS = {"state-reconcile", "compact-task-memory"}
WHOLE_FILE_TARGET = "TASK_STATE.md"

# Rule 3: approve-proposed lands a block another command staged, in whatever section it sits.
PROMOTER = "approve-proposed"


def set_matrix(path):
    """Point the parser at an alternate matrix so the check is itself testable."""
    global MATRIX
    MATRIX = path


def set_logs_root(path):
    """Point the scan at another tree's projects/ and .wos/ (tests and dry runs)."""
    global LOGS_ROOT
    LOGS_ROOT = path


def row_section(cell):
    """The H2 a table row governs: its backticked `## ` span, or the H2 that owns its H3."""
    m = re.search(r"`(## [^`]+)`", cell)
    if m:
        return m.group(1).strip()
    m = re.search(r"`(### [^`]+)`", cell)
    return H3_PARENT.get(m.group(1).strip()) if m else None


def matrix_files():
    """Basenames of the files that carry an ownership table, read from the `### FILE.md` headings.

    A log line for any other file (IMPACT_ANALYSIS.md, a SLICES/ note, README.md) was counted as a
    write to a section with no matrix row, though no row could ever cover it: 803 lines of that
    kind were in the logs on 2026-09-23. The file set is read from the matrix itself,
    so a new table widens it without an edit here.
    """
    files, current = set(), None
    for line in open(MATRIX, encoding="utf-8"):
        if line.startswith("## "):
            current = None
            continue
        if line.startswith("### "):
            m = re.match(r"### `?([A-Za-z0-9_.-]+\.md)\b", line)
            current = m.group(1) if m else None
            continue
        if current and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and row_section(cells[0]):
                files.add(current)
    return files


def command_names():
    n = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(REPO, "commands", "*.md"))}
    n |= {os.path.basename(os.path.dirname(p))
          for p in glob.glob(os.path.join(REPO, "commands", "*", "SKILL.md"))}
    return n


def parse_matrix(cmds):
    """{section: (authorized set, cites_pattern_writers)} from the H2 tables."""
    rows = {}
    for line in open(MATRIX, encoding="utf-8"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        # Take the FIRST backticked span, the same idiom the numbered-prose reader below
        # already uses. Trimming the ends instead keeps everything after the closing
        # backtick: a cell reading `## Locked decisions` (D-N) produced the key
        # "## Locked decisions` (D-N)", which matches no section any writer ever names, so
        # the row silently granted nothing. Measured 2026-08-30: 13 of 61 table rows were
        # keyed that way, and `## Locked decisions` was one of them, which is why
        # decision-interview headed the unauthorized list with 740 writes to a section it
        # owns. A row that cannot match is worse than a missing row: it looks like coverage.
        sec = row_section(cells[0])
        if not sec:
            continue
        auth = set()
        for cell in cells[1:3]:
            for tok in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", cell):
                if tok in cmds:
                    auth.add(tok)
        prev, prev_pat = rows.get(sec, (set(), False))
        rows[sec] = (prev | auth, prev_pat or ("pattern writer" in line))

    # The matrix has TWO shapes and a first version read only one. Beside the H2
    # tables, several files' rules are numbered prose ("3. `## Repositories`:
    # `task-init` sole owner; `project-bootstrap` seeds."). Parsing tables alone
    # reported 4,646 writes to a section with no matrix row when 1,174 of them
    # were covered here, `## Locked decisions` among them, a 25 per cent inflation
    # in the alarming direction. The reading is deliberately generous: every
    # command named in a numbered rule authorizes every section named in that same
    # rule, because the prose does not associate them any more finely than that.
    body = open(MATRIX, encoding="utf-8").read()
    for m in re.finditer(r"^\d+\.\s+(.*)$", body, re.M):
        rule = m.group(1)
        secs = [x.strip() for x in re.findall(r"`(## [^`]+)`", rule)]
        if not secs:
            continue
        auth = {t for t in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)+", rule) if t in cmds}
        for sec in secs:
            prev, prev_pat = rows.get(sec, (set(), False))
            rows[sec] = (prev | auth, prev_pat)
    return rows


def scan(rows, live_only=False, mfiles=frozenset()):
    hatched = collections.Counter()
    skipped = collections.Counter()
    bad = collections.Counter()
    norow = collections.Counter()
    folders, badfolders, norowfolders = set(), set(), set()
    total = 0
    logs = glob.glob(os.path.join(LOGS_ROOT, "projects", "**", ".wos", "VERIFICATION_LOG.jsonl"),
                     recursive=True)
    # The repo's own root log is a task log too. Omitting it is the same defect
    # flow-audit.py carried: it reported task-init-fleet as never invoked while
    # 8 of its records sat at the root and none under projects/.
    root_log = os.path.join(LOGS_ROOT, ".wos", "VERIFICATION_LOG.jsonl")
    if os.path.isfile(root_log) and not live_only:
        logs.append(root_log)
    for lg in logs:
        if live_only and f"{os.sep}active{os.sep}" not in lg:
            continue
        folder = os.path.dirname(os.path.dirname(lg))
        folders.add(folder)
        for line in open(lg, errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            total += 1
            if not isinstance(d, dict):
                continue
            # A staged block is not a write, and a refused fleet merge wrote nothing. Both were
            # counted as writes until 2026-09-23: 389 proposed lines and the refuse lines.
            if d.get("mode") == "proposed":
                skipped["mode=proposed (a staged block, not a write)"] += 1
                continue
            if d.get("event") == "refuse":
                skipped["event=refuse (a refused fleet merge wrote nothing)"] += 1
                continue
            fname = os.path.basename(str(d.get("file") or "").strip())
            if mfiles and fname and fname not in mfiles:
                skipped["file with no matrix table (no row could cover it)"] += 1
                continue
            sec = (d.get("section") or "").strip()
            own = (d.get("owner") or "").strip()
            if not sec or not own:
                continue
            if sec not in rows:
                norow[(own, sec)] += 1
                norowfolders.add(folder)
                continue
            auth, is_pattern = rows[sec]
            if own in auth:
                continue
            if own == PROMOTER:
                hatched["promotion (rule 3, approve-proposed lands a staged block)"] += 1
                continue
            if own in WHOLE_FILE_OPERATORS and fname == WHOLE_FILE_TARGET:
                hatched["whole-file operators (rule 2c, TASK_STATE.md only)"] += 1
                continue
            if own == "task-init":
                hatched["genesis (rule 2a, task-init seeds the file)"] += 1
                continue
            if is_pattern:
                hatched["pattern writers (rule 2b, row cites them by class)"] += 1
                continue
            if sec == "## Observations":
                hatched["append-only (matrix grants any-command)"] += 1
                continue
            bad[(own, sec)] += 1
            badfolders.add(folder)
    return dict(total=total, folders=folders, badfolders=badfolders, norowfolders=norowfolders,
                bad=bad, norow=norow, hatched=hatched, skipped=skipped)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", help="alternate ownership matrix (for controls and dry runs)")
    ap.add_argument("--logs-root", help="tree whose projects/ and .wos/ hold the logs to scan "
                    "(default: this repository; tests point it at a fixture)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when any write to a section with no matrix row survives")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--repair-list", action="store_true",
                    help="print the (command, section) pairs to add to the matrix")
    a = ap.parse_args()

    if a.matrix:
        if not os.path.isfile(a.matrix):
            print(f"Substrate-ownership: skipped (usage error: --matrix not a file: {a.matrix})",
                  file=sys.stderr)
            return 2
        set_matrix(a.matrix)
    if a.logs_root:
        if not os.path.isdir(a.logs_root):
            print(f"Substrate-ownership: skipped (usage error: --logs-root not a directory: "
                  f"{a.logs_root})", file=sys.stderr)
            return 2
        set_logs_root(a.logs_root)

    cmds = command_names()
    rows = parse_matrix(cmds)
    if not rows:
        print("Substrate-ownership: skipped (no ownership tables parsed from wos/substrate-peers.md)",
              file=sys.stderr)
        return 2

    # static half: names in the matrix that are not commands on disk
    stale = set()
    for line in open(MATRIX, encoding="utf-8"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not row_section(cells[0]):
            continue
        for cell in cells[1:3]:
            for tok in re.findall(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`", cell):
                if tok not in cmds:
                    stale.add(tok)

    mfiles = matrix_files()
    allr = scan(rows, mfiles=mfiles)
    live = scan(rows, live_only=True, mfiles=mfiles)
    if not allr["folders"]:
        print("Substrate-ownership: not measured (no .wos/VERIFICATION_LOG.jsonl found under projects/)")
        return 0

    nbad = sum(allr["bad"].values())
    nrow = sum(allr["norow"].values())
    lrow = sum(live["norow"].values())

    # The headline is the no-row count: a section the matrix does not describe is a gap someone
    # can close by adding a row. A write outside the conventional owner is allowed (ADR-0232), so
    # heading the line with it made a measurement read like a defect queue.
    print(f"Substrate-ownership: {nrow} write(s) to a section with no matrix row across "
          f"{len(allr['norowfolders'])} of {len(allr['folders'])} task folder(s) "
          f"({len(rows)} sections have one). Live scope: {lrow} line(s) in "
          f"{len(live['norowfolders'])} of {len(live['folders'])} active folder(s). "
          f"{nbad} write(s) outside the conventional owner, recorded not refused (ADR-0232). "
          f"{'advisory' if not a.strict else 'strict'}")
    print(f"  matrix names {len(stale)} command(s) not on disk"
          + (": " + ", ".join(sorted(stale)) if stale else " (referential integrity clean)"))
    print(f"  scanned {allr['total']} log line(s); {len(mfiles)} file(s) carry a matrix table")
    for h, n in sorted(allr["skipped"].items(), key=lambda x: -x[1]):
        print(f"  skipped        {n:6d}: {h}")
    for h, n in sorted(allr["hatched"].items(), key=lambda x: -x[1]):
        print(f"  hatch absorbed {n:6d}: {h}")

    if a.verbose or a.repair_list:
        print("\n  top writes to a section with NO matrix row:")
        for (o, s), n in allr["norow"].most_common(20 if not a.repair_list else 200):
            print(f"    {n:5d}  {o} -> {s}")
        print("\n  top writes outside the conventional owner (command -> section), self-reported:")
        for (o, s), n in allr["bad"].most_common(20 if not a.repair_list else 200):
            print(f"    {n:5d}  {o} -> {s}")

    return 1 if (a.strict and nrow) else 0


if __name__ == "__main__":
    sys.exit(main())
