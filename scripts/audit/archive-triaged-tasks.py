#!/usr/bin/env python3
"""archive-triaged-tasks.py -- move ticked tasks from active/ to archive/.

Reads the triage sheet, moves every ticked task folder, and appends one honest
note to each moved TASK_STATE.md saying it was archived in bulk WITHOUT the
task-close done-condition check.

Dry run by default. `--apply` performs the moves.

It deliberately does NOT write projects/*/OUTCOMES.jsonl: these tasks have no
real outcome, and the outcome ledger is what measures cycle time and merge rate.

Every move is recorded in a manifest next to the sheet so the pass can be undone
with `--undo <manifest>`.

Usage:
  python3 scripts/audit/archive-triaged-tasks.py --sheet projects/TASK_TRIAGE_<date>.md
  python3 scripts/audit/archive-triaged-tasks.py --sheet ... --apply
  python3 scripts/audit/archive-triaged-tasks.py --undo projects/TASK_TRIAGE_<date>.moves.json --apply
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

TICK = re.compile(r"^\s*-\s*\[\s*[xX]\s*\]\s*(.*)$")
BLANK = re.compile(r"^\s*-\s*\[\s*\]\s*(.*)$")

NOTE_HEADING = "## Bulk archive note"


def parse_sheet(path):
    """Return [(project, task)] for every ticked task, project ticks included."""
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    proj = None
    per_project = {}
    order = []
    all_ticked = set()
    for line in lines:
        m = re.match(r"^## `([^`]+)`\s*$", line)
        if m:
            proj = m.group(1)
            per_project[proj] = []
            order.append(proj)
            continue
        if proj is None:
            continue
        t = TICK.match(line)
        b = BLANK.match(line)
        if not (t or b):
            continue
        body = (t or b).group(1)
        ticked = bool(t)
        if body.startswith("**all"):
            if ticked:
                all_ticked.add(proj)
            continue
        ms = re.match(r"`([^`]+)`", body)
        if ms:
            per_project[proj].append((ms.group(1), ticked))

    out = []
    for p in order:
        for slug, ticked in per_project[p]:
            if p in all_ticked or ticked:
                out.append((p, slug))
    return out


def board_meta():
    script = os.path.join(REPO, "scripts", "portfolio-review.sh")
    if not os.path.isfile(script):
        return {}
    proc = subprocess.run(["bash", script, "--json"], cwd=REPO,
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return {}
    try:
        return {(r["project"], r["task"]): r for r in json.loads(proc.stdout)}
    except ValueError:
        return {}


def note_for(meta, stamp):
    cls = meta.get("class", "unknown") if meta else "unknown"
    idle = meta.get("idle_days", "unknown") if meta else "unknown"
    return "\n".join([
        "",
        NOTE_HEADING,
        "",
        "Archived %s by a bulk triage pass over the active-task board." % stamp,
        "",
        "This task did NOT go through `task-close`. Its done-conditions were never",
        "checked. The operator marked it during triage as no longer relevant, and it",
        "was moved from `active/` to `archive/` on that basis alone.",
        "",
        "- Board class at archive time: `%s`" % cls,
        "- Days idle at archive time: %s" % idle,
        "- No entry was written to `OUTCOMES.jsonl`: there is no real outcome to record.",
        "",
    ])


def plan(sheet_path):
    ticks = parse_sheet(sheet_path)
    meta = board_meta()
    moves, problems = [], []
    for project, task in ticks:
        src = os.path.join(REPO, "projects", project, "active", task)
        dst = os.path.join(REPO, "projects", project, "archive", task)
        if not os.path.isdir(src):
            problems.append({"project": project, "task": task,
                             "reason": "source folder is missing"})
            continue
        if os.path.exists(dst):
            problems.append({"project": project, "task": task,
                             "reason": "destination already exists in archive/"})
            continue
        moves.append({"project": project, "task": task,
                      "src": os.path.relpath(src, REPO),
                      "dst": os.path.relpath(dst, REPO),
                      "class": (meta.get((project, task)) or {}).get("class"),
                      "idle_days": (meta.get((project, task)) or {}).get("idle_days")})
    return moves, problems, meta


def apply_moves(moves, meta, stamp):
    done = []
    for m in moves:
        src = os.path.join(REPO, m["src"])
        dst = os.path.join(REPO, m["dst"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        state = os.path.join(src, "TASK_STATE.md")
        if os.path.isfile(state):
            try:
                with open(state, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                if NOTE_HEADING not in text:
                    with open(state, "a", encoding="utf-8") as fh:
                        fh.write(note_for(meta.get((m["project"], m["task"])), stamp))
            except OSError as exc:
                sys.stderr.write("warn: could not annotate %s: %s\n" % (m["src"], exc))
        shutil.move(src, dst)
        done.append(m)
    return done


def undo(manifest_path, apply_it):
    with open(manifest_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    moves = data.get("moves", [])
    n = 0
    for m in moves:
        src = os.path.join(REPO, m["dst"])
        dst = os.path.join(REPO, m["src"])
        if not os.path.isdir(src) or os.path.exists(dst):
            continue
        if apply_it:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
        n += 1
    print("%s %d folder(s) back to active/" % ("moved" if apply_it else "would move", n))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="Archive ticked tasks in bulk")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--undo", default=None)
    args = ap.parse_args(argv)

    if args.undo:
        return undo(args.undo if os.path.isabs(args.undo)
                    else os.path.join(REPO, args.undo), args.apply)

    if not args.sheet:
        sys.stderr.write("archive-triaged-tasks: --sheet is required\n")
        return 2
    sheet = args.sheet if os.path.isabs(args.sheet) else os.path.join(REPO, args.sheet)
    if not os.path.isfile(sheet):
        sys.stderr.write("archive-triaged-tasks: no sheet at %s\n" % args.sheet)
        return 2

    moves, problems, meta = plan(sheet)
    stamp = time.strftime("%Y-%m-%d")

    print("Sheet:   %s" % os.path.relpath(sheet, REPO))
    print("Ticked:  %d task(s) resolve to a real folder" % len(moves))
    print("Skipped: %d" % len(problems))
    for p in problems:
        print("  skip %s / %s: %s" % (p["project"], p["task"], p["reason"]))

    by_project = {}
    for m in moves:
        by_project.setdefault(m["project"], 0)
        by_project[m["project"]] += 1
    print("\nPer project:")
    for p in sorted(by_project, key=lambda k: (-by_project[k], k)):
        print("  %3d  %s" % (by_project[p], p))

    if not args.apply:
        print("\nDry run. Nothing moved. Re-run with --apply.")
        return 0

    manifest = os.path.splitext(sheet)[0] + ".moves.json"
    done = apply_moves(moves, meta, stamp)
    with open(manifest, "w", encoding="utf-8") as fh:
        json.dump({"stamp": stamp, "sheet": os.path.relpath(sheet, REPO),
                   "moves": done, "skipped": problems}, fh, indent=1)
    print("\nMoved %d folder(s)." % len(done))
    print("Manifest: %s" % os.path.relpath(manifest, REPO))
    print("Undo:     python3 scripts/audit/archive-triaged-tasks.py --undo %s --apply"
          % os.path.relpath(manifest, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
