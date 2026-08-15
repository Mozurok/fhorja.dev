#!/usr/bin/env python3
"""build-task-triage.py -- one Markdown sheet for triaging every active task.

Read-only over projects/. Writes exactly one file: the triage sheet.

Grouped by project, projects ordered by how dead they look (the most recently
touched task in the project is the sort key, oldest first), so a project that
stopped months ago can be swept in one pass instead of task by task.

Classification is NOT reimplemented here. It comes from
`scripts/portfolio-review.sh --json`, so this sheet and the board can never
disagree. Everything else is read straight from each task's TASK_STATE.md.

The sheet lands under projects/ on purpose: it carries client codenames, and
projects/ is gitignored (ADR-0007). It must not go anywhere the public tree
can reach.

Usage:
  python3 scripts/audit/build-task-triage.py
  python3 scripts/audit/build-task-triage.py --out projects/TASK_TRIAGE_<date>.md
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

CLASS_SHORT = {
    "done-unclosed": "done?",
    "blocked": "blocked",
    "my-move": "my-move",
    "stale": "stale",
    "in-flight": "live",
}

WOS_COMMENT = re.compile(r"<!--.*?-->", re.S)


def section(text, heading):
    """Body of one '## Heading' section, comments stripped, whitespace collapsed."""
    m = re.search(r"^#{2,3}\s+" + re.escape(heading) + r"\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^#{2,3}\s+\S", rest, re.M)
    body = rest[:nxt.start()] if nxt else rest
    body = WOS_COMMENT.sub(" ", body)
    body = re.sub(r"^[-*]\s+", "", body.strip(), flags=re.M)
    return re.sub(r"\s+", " ", body).strip()


def clip(s, n):
    # Quoted task text is data, not prose this script authored. Pipes would break
    # a table and dashes would trip the guard in render(), so both are normalized
    # here rather than by relaxing the guard.
    s = (s or "").replace("|", "/")
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"[*_`]+", "", s).strip()
    if len(s) <= n:
        return s
    return s[:n - 3].rstrip() + "..."


def board_rows():
    script = os.path.join(REPO, "scripts", "portfolio-review.sh")
    if not os.path.isfile(script):
        sys.stderr.write("build-task-triage: scripts/portfolio-review.sh is absent\n")
        return None
    proc = subprocess.run(["bash", script, "--json"], cwd=REPO,
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        sys.stderr.write("build-task-triage: portfolio-review.sh --json failed\n")
        return None
    try:
        return json.loads(proc.stdout)
    except ValueError:
        sys.stderr.write("build-task-triage: portfolio-review.sh --json is not JSON\n")
        return None


def enrich(row):
    folder = os.path.join(REPO, "projects", row["project"], "active", row["task"])
    state = os.path.join(folder, "TASK_STATE.md")
    text = ""
    if os.path.isfile(state):
        try:
            with open(state, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""
    slices_dir = os.path.join(folder, "SLICES")
    n_slices = len([f for f in os.listdir(slices_dir) if f.endswith(".md")]) \
        if os.path.isdir(slices_dir) else 0
    try:
        touched = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(state)))
    except OSError:
        touched = "?"
    phase = clip(section(text, "Current phase"), 40)
    return {
        "class": row["class"],
        "idle": int(row.get("idle_days") or 0),
        "project": row["project"],
        "task": row["task"],
        "touched": touched,
        "phase": phase.split(" ")[0].rstrip(":,.") if phase else "-",
        "next": clip(row.get("next_command") or "", 24) or "-",
        "summary": clip(section(text, "Task summary"), 165),
        "last": clip(section(text, "Last completed step"), 120),
        "slices": n_slices,
        "pr": os.path.isfile(os.path.join(folder, "PR_PACKAGE.md")),
    }


def guess(r):
    """Best guess at done versus abandoned, shown so the operator can override.

    Never applied automatically: this only pre-labels the row.
    """
    phase = r["phase"].lower()
    early = phase in ("discovery", "planning")
    # Evidence of finishing beats age. A task that reached delivery and then went
    # quiet is a task you forgot to archive, not one you abandoned.
    if r["pr"]:
        return "done"
    if r["class"] == "done-unclosed" and not early:
        return "done"
    if phase in ("delivery", "delivered", "review", "closure", "closed", "done"):
        return "done"
    # No sign of finishing. Age then decides.
    if early and r["idle"] > 30:
        return "drop"
    if r["idle"] > 60:
        return "drop"
    return "?"


def render(rows, out_path):
    projects = {}
    for r in rows:
        projects.setdefault(r["project"], []).append(r)
    for p in projects:
        projects[p].sort(key=lambda r: (-r["idle"], r["task"]))

    # A project whose MOST recently touched task is old is a dead project.
    order = sorted(projects, key=lambda p: (-min(r["idle"] for r in projects[p]), p))

    total = len(rows)
    L = []
    L.append("# Task triage, %s" % time.strftime("%Y-%m-%d"))
    L.append("")
    L.append("%d active tasks in %d projects, grouped by project. Projects are ordered "
             "by how stopped they look: the sort key is the most recently touched task "
             "in the project, oldest first. The dead ones are at the top."
             % (total, len(projects)))
    L.append("")
    L.append("## How to use")
    L.append("")
    L.append("- Tick `[x]` on every task that should leave `active/`. Leave unticked "
             "anything you are still working on.")
    L.append("- To sweep a whole project, tick its **all** line. Individual ticks in "
             "that project are then redundant.")
    L.append("- Each row carries a guess: `done` (finished, archive it) or `drop` "
             "(abandoned). Override by writing the other word at the end of the line. "
             "A `?` means the guess had nothing to go on.")
    L.append("- Nothing is executed from this file until you hand it back and confirm "
             "the plan I read out of it.")
    L.append("")
    L.append("Back up first. `projects/` is gitignored, so there is no undo:")
    L.append("")
    L.append("```sh")
    L.append("cp -R projects ~/projects-backup-%s" % time.strftime("%Y-%m-%d"))
    L.append("```")
    L.append("")
    L.append("## Projects at a glance")
    L.append("")
    L.append("| project | tasks | quietest | oldest | with PR | guess done / drop / ? |")
    L.append("|---|---:|---:|---:|---:|---|")
    for p in order:
        g = projects[p]
        gd = sum(1 for r in g if guess(r) == "done")
        gr = sum(1 for r in g if guess(r) == "drop")
        gq = len(g) - gd - gr
        L.append("| `%s` | %d | %dd | %dd | %d | %d / %d / %d |" % (
            p, len(g), min(r["idle"] for r in g), max(r["idle"] for r in g),
            sum(1 for r in g if r["pr"]), gd, gr, gq))
    L.append("")
    L.append("---")
    L.append("")

    n = 0
    for p in order:
        g = projects[p]
        quietest = min(r["idle"] for r in g)
        L.append("## `%s`" % p)
        L.append("")
        L.append("%d task(s). Nothing touched for %d days. Oldest sits at %d days."
                 % (len(g), quietest, max(r["idle"] for r in g)))
        L.append("")
        L.append("- [ ] **all %d tasks in this project**" % len(g))
        L.append("")
        for r in g:
            n += 1
            bits = [
                "%dd" % r["idle"],
                CLASS_SHORT.get(r["class"], r["class"]),
                r["phase"],
                "next %s" % r["next"],
            ]
            if r["pr"]:
                bits.append("PR ready")
            if r["slices"]:
                bits.append("%d slices" % r["slices"])
            bits.append("guess %s" % guess(r))
            L.append("- [ ] `%s`" % r["task"])
            L.append("  <sub>%s</sub>" % " · ".join(bits))
            if r["summary"]:
                L.append("  <sub>%s</sub>" % r["summary"])
            if r["last"]:
                L.append("  <sub>last: %s</sub>" % r["last"])
            L.append("")
        L.append("")

    page = "\n".join(L) + "\n"
    for ch, label in (("—", "em-dash"), ("–", "en-dash")):
        if ch in page:
            sys.stderr.write("build-task-triage: refusing to write: a %s reached the sheet\n" % label)
            return 3
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(page)
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="Build the active-task triage sheet")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    rows = board_rows()
    if rows is None:
        return 2
    enriched = [enrich(r) for r in rows]
    out = args.out or os.path.join(
        REPO, "projects", "TASK_TRIAGE_%s.md" % time.strftime("%Y-%m-%d"))
    if not os.path.isabs(out):
        out = os.path.join(REPO, out)
    rc = render(enriched, out)
    if rc == 0:
        sys.stderr.write("build-task-triage: wrote %s (%d tasks, %d projects)\n"
                         % (os.path.relpath(out, REPO), len(enriched),
                            len({r["project"] for r in enriched})))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
