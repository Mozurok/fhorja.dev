#!/usr/bin/env python3
"""flow-audit.py -- dry-run WOS command-flow health auditor.

Read-only. Reports how the command set is actually used and how well the commands
interconnect, so command-usage concentration and orphaned commands stop being a
matter of intuition. Writes nothing except its own report to stdout (and an
explicit --out path).

Two signals:
  1. Declared graph (complete): reference in-degree per command across commands/*.md,
     i.e. how many other command files mention each command. A command with 0 or 1
     inbound references is only reachable if you already know it exists.
  2. Realized usage (from telemetry): the `owner` and `invoked_by` fields in every
     projects/*/**/.wos/VERIFICATION_LOG.jsonl. Only command-name fields are read
     and emitted, never task content or project identities.

Never-invoked commands are classified so the report does not cry wolf on
read-only-by-design commands (what-next, review-hard, ...) that legitimately write
little or no substrate.

Usage:
  python3 scripts/flow-audit.py              full report to stdout
  python3 scripts/flow-audit.py --out FILE   also write the report as markdown
  python3 scripts/flow-audit.py --orphans-brief   fast static pass only (for lint)

Provenance of the curated sets below: the 2026-07-11 flow audit
(projects/bmazurok__my-work-tasks/.../2026-07-10_wos-flow-audit-dryrun-process).
Keep them in sync when commands are added; anything never-invoked and not listed
here surfaces as "cold (review)" so a genuinely new cold command is never hidden.
"""

import sys
import os
import re
import json
import glob
import collections

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Commands used but that write little/no substrate, so the write-log undercounts
# them. Listing them here keeps them out of the actionable "cold" bucket.
READ_ONLY_BY_DESIGN = {
    "api-contract-review", "atom-audit", "atom-audit-fleet", "autonomous-board",
    "code-locate", "design-spec-review", "feature-library-scout-fleet",
    "foundation-audit", "frontend-architecture-review", "graphql-contract-review",
    "harvest-session-learnings", "im-stuck", "inventory-snapshot", "mcp-server-vet",
    "portfolio-review", "prompt-shape", "resume-from-state", "skill-vet",
    "state-reconcile", "verify-against-rubric", "verify-against-rubric-fleet",
    "workflow-guide",
}

# Commands that run before or around a task folder, so they never write to a task
# .wos/ log even when used (their writes land at project level or in child tasks).
PRE_TASK_UNDERCOUNTED = {
    "problem-framing", "project-bootstrap", "task-init-fleet",
}


def command_paths():
    """Canonical command name -> source file.

    Commands are flat `commands/<name>.md` OR folder-shaped
    `commands/<name>/SKILL.md` (the persona-style commands). Enumerate both, or
    the folder-shaped commands are silently missed (they were 9 of 94 in the
    2026-07-11 audit). Mirrors lint-commands.sh, which scans both forms.
    """
    paths = {}
    for p in glob.glob(os.path.join(REPO, "commands", "*.md")):
        paths[os.path.basename(p)[:-3]] = p
    for p in glob.glob(os.path.join(REPO, "commands", "*", "SKILL.md")):
        paths[os.path.basename(os.path.dirname(p))] = p
    return paths


def command_names(paths=None):
    return sorted((paths or command_paths()).keys())


def reference_indegree(names, paths):
    """How many OTHER command files mention each command as a whole token."""
    nameset = set(names)
    indeg = collections.Counter({n: 0 for n in names})
    for src in names:
        txt = open(paths[src], encoding="utf-8").read()
        for n in nameset:
            if n == src:
                continue
            if re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", txt):
                indeg[n] += 1
    return indeg


def scan_telemetry():
    """Aggregate owner / invoked_by across all task audit logs. Names only."""
    owner_tasks = collections.defaultdict(set)
    owner_writes = collections.Counter()
    edge = collections.Counter()          # (invoked_by -> owner)
    logs = glob.glob(
        os.path.join(REPO, "projects", "*", "**", ".wos", "VERIFICATION_LOG.jsonl"),
        recursive=True,
    )
    invoked_parents = collections.Counter()
    tasks, total, bad = set(), 0, 0
    for lf in logs:
        task = lf.split(os.sep + ".wos" + os.sep)[0]
        tasks.add(task)
        for line in open(lf, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                bad += 1
                continue
            total += 1
            ow, ib = o.get("owner"), o.get("invoked_by")
            if ow:
                owner_writes[ow] += 1
                owner_tasks[ow].add(task)
            if ib:
                invoked_parents[ib] += 1
                if ow:
                    edge[(ib, ow)] += 1
    return {
        "owner_tasks": {k: len(v) for k, v in owner_tasks.items()},
        "owner_writes": owner_writes,
        "invoked_parents": invoked_parents,
        "edge": edge,
        "n_logs": len(logs),
        "n_tasks": len(tasks),
        "total": total,
        "bad": bad,
    }


def classify(names, used_set):
    used = [n for n in names if n in used_set]
    never = [n for n in names if n not in used_set]
    read_only = sorted(n for n in never if n in READ_ONLY_BY_DESIGN)
    pre_task = sorted(n for n in never if n in PRE_TASK_UNDERCOUNTED)
    cold = sorted(
        n for n in never
        if n not in READ_ONLY_BY_DESIGN and n not in PRE_TASK_UNDERCOUNTED
    )
    return used, read_only, pre_task, cold


def orphans(indeg, names):
    zero = sorted(n for n in names if indeg[n] == 0)
    low = sorted(n for n in names if indeg[n] == 1)
    return zero, low


def brief_report(names, indeg):
    """One-line-ish advisory for lint: zero-inbound orphan count + list."""
    zero, low = orphans(indeg, names)
    print(f"orphan-edge advisory: {len(zero)} command(s) with 0 inbound "
          f"references, {len(low)} with exactly 1 (warn-only)")
    if zero:
        print("  0 inbound: " + ", ".join(zero))
    return 0


def full_report(names, indeg, tel, out_lines):
    def w(s=""):
        out_lines.append(s)

    used_set = set(tel["owner_writes"]) | set(tel["invoked_parents"])
    used, read_only, pre_task, cold = classify(names, used_set)
    zero, low = orphans(indeg, names)
    ot = tel["owner_tasks"]

    w("# WOS flow audit (dry-run)")
    w("")
    w(f"Commands: {len(names)}   Used (owner or router): {len(used)}   "
      f"Never invoked: {len(names) - len(used)}")
    w(f"Telemetry: {tel['n_logs']} logs across {tel['n_tasks']} tasks, "
      f"{tel['total']} write-lines ({tel['bad']} malformed line(s) skipped)")
    w("Command names only; no task content or project identity is read or emitted.")
    w("")

    w("## Realized usage (top by distinct tasks)")
    top = sorted(ot.items(), key=lambda kv: (-kv[1], -tel["owner_writes"][kv[0]]))
    for cmd, ntasks in top[:12]:
        w(f"  {ntasks:3d} tasks | {tel['owner_writes'][cmd]:5d} writes | {cmd}")
    w("")

    w("## Command graph: orphan edges (fixable interconnection gap)")
    w(f"Zero inbound references ({len(zero)}): "
      f"only reachable if you already know they exist")
    for n in zero:
        w(f"  indeg=0  {n}")
    w(f"Exactly one inbound reference ({len(low)}):")
    w("  " + (", ".join(low) if low else "(none)"))
    w("")

    w("## Never-invoked, classified")
    w(f"Read-only by design ({len(read_only)}): used but write little/no substrate, "
      f"so the write-log undercounts them. Not a gap.")
    w("  " + (", ".join(read_only) if read_only else "(none)"))
    w(f"Pre-task, undercounted ({len(pre_task)}): run before/around a task folder, "
      f"so no task .wos log. Not a gap.")
    w("  " + (", ".join(pre_task) if pre_task else "(none)"))
    w(f"Cold, review ({len(cold)}): declared commands with no recorded invocation. "
      f"Some are work-pattern-cold (fine); some fit the pattern but are never reached.")
    w("  " + (", ".join(cold) if cold else "(none)"))
    w("")

    w("## Declared vs realized edges (low confidence)")
    w("invoked_by is sparse and user-driven, so treat this as a hint, not a verdict.")
    realized = {ib for (ib, _ow) in tel["edge"]}
    w(f"  commands that ever appear as a routing parent (invoked_by): {len(realized)}")
    top_edges = sorted(tel["edge"].items(), key=lambda kv: -kv[1])[:8]
    for (ib, ow), c in top_edges:
        w(f"    {c:3d}  {ib} -> {ow}")
    w("")
    w("Spine note: a small set of commands dominating realized usage is intended "
      "design (the happy path), not a defect. The fixable gap is the orphan edges "
      "above plus the cold-review commands that fit the work pattern.")


def main(argv):
    paths = command_paths()
    names = command_names(paths)
    if not names:
        print("flow-audit: no commands found; run from the WOS repo.",
              file=sys.stderr)
        return 2

    if "--orphans-brief" in argv:
        return brief_report(names, reference_indegree(names, paths))

    out_path = None
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 >= len(argv):
            print("flow-audit: --out needs a path", file=sys.stderr)
            return 2
        out_path = argv[i + 1]

    indeg = reference_indegree(names, paths)
    tel = scan_telemetry()
    lines = []
    full_report(names, indeg, tel, lines)
    print("\n".join(lines))
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\n(report also written to {out_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
