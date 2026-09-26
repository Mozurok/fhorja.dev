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
# Exempt from the never-invoked metric, each with the reason written down. A name
# on this list is invisible to the usage signal by construction, so the reason has
# to survive the person who added it: a bare set turns "we decided this is fine"
# into "nobody remembers why".
#
# Being exempt is not the same as being reachable. A name here with an indegree of
# 1 or 0 is exempt from the USAGE metric and still unreachable in the command
# graph, which is a different defect and the one the review queue surfaces.
READ_ONLY_BY_DESIGN = {
    "api-contract-review": "read-only review; writes findings into the caller's artifact, not a task log",
    "atom-audit": "read-only audit of a design surface; produces a report, not task state",
    "atom-audit-fleet": "fleet variant of atom-audit; same read-only shape",
    "autonomous-board": "read-only status view over the autonomous track",
    "code-locate": "read-only lookup; answers where something is",
    "design-spec-review": "read-only review of a spec against its surface",
    "feature-library-scout-fleet": "read-only scout; reports what exists upstream",
    "foundation-audit": "read-only audit of repository foundations",
    "frontend-architecture-review": "read-only architecture review",
    "graphql-contract-review": "read-only contract review",
    "harvest-session-learnings": "reads a session and writes to project memory, not a task log",
    "im-stuck": "conversational unblocking; writes nothing by design",
    "inventory-snapshot": "read-only inventory of a codebase",
    "mcp-server-vet": "read-only vetting of an MCP server before it is trusted",
    "portfolio-review": "read-only report across projects",
    "prompt-shape": "read-only prompt critique",
    "resume-from-state": "reads state to re-enter a task; the writes belong to what it routes to",
    "skill-vet": "read-only vetting of a skill before install",
    "state-reconcile": "repairs artifacts in place; the repair is the output, not a log line",
    "verify-against-rubric": "read-only verdict against a rubric",
    "verify-against-rubric-fleet": "fleet variant; same read-only shape",
    "workflow-guide": "read-only explainer of the workflow itself",
}

# The date this exemption list was last read end to end and each reason confirmed.
# An exemption nobody has re-read is a decision that has stopped being one.
READ_ONLY_REVIEWED = "2026-08-29"

# Commands that run before or around a task folder, so they never write to a task
# .wos/ log even when used (their writes land at project level or in child tasks).
PRE_TASK_UNDERCOUNTED = {
    "problem-framing": "runs before a task folder exists; writes at project level",
    "project-bootstrap": "creates the project; there is no task log yet",
    "task-init-fleet": "creates child tasks; the writes land in them, not in a parent log",
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
    # The repo's OWN root log counts. Globbing projects/ alone reported
    # task-init-fleet as never invoked while it held 8 records at the root and
    # none anywhere under projects/.
    logs = glob.glob(
        os.path.join(REPO, "projects", "*", "**", ".wos", "VERIFICATION_LOG.jsonl"),
        recursive=True,
    )
    root_log = os.path.join(REPO, ".wos", "VERIFICATION_LOG.jsonl")
    if os.path.isfile(root_log):
        logs.append(root_log)
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


def classify(names, used_set, indeg=None):
    """Six buckets, not four.

    An exempt name used to vanish into one `read_only` list, which hid two
    different things: a command that is genuinely reachable and simply does not
    write a log, and a command nobody can reach at all. Splitting on indegree
    separates them. `missing` catches an exemption whose command no longer exists,
    which is how a stale entry would otherwise outlive its command in silence.
    """
    indeg = indeg or {}
    used = [n for n in names if n in used_set]
    never = [n for n in names if n not in used_set]
    exempt = [n for n in never if n in READ_ONLY_BY_DESIGN]
    read_only_reachable = sorted(n for n in exempt if indeg.get(n, 0) >= 2)
    read_only_unreachable = sorted(n for n in exempt if indeg.get(n, 0) <= 1)
    pre_task = sorted(n for n in never if n in PRE_TASK_UNDERCOUNTED)
    cold = sorted(
        n for n in never
        if n not in READ_ONLY_BY_DESIGN and n not in PRE_TASK_UNDERCOUNTED
    )
    on_disk = set(names)
    missing = sorted(n for n in list(READ_ONLY_BY_DESIGN) + list(PRE_TASK_UNDERCOUNTED)
                     if n not in on_disk)
    return used, read_only_reachable, read_only_unreachable, pre_task, cold, missing


def exemption_audit(names, indeg):
    """(unreachable, missing) over the exemption lists, from static signal only.

    Deliberately reads indegree rather than telemetry: this has to give the same
    answer in a clone with no projects/ directory.
    """
    on_disk = set(names)
    unreachable = sorted(n for n in READ_ONLY_BY_DESIGN
                         if n in on_disk and indeg.get(n, 0) <= 1)
    missing = sorted(n for n in list(READ_ONLY_BY_DESIGN) + list(PRE_TASK_UNDERCOUNTED)
                     if n not in on_disk)
    return unreachable, missing


def orphans(indeg, names):
    zero = sorted(n for n in names if indeg[n] == 0)
    low = sorted(n for n in names if indeg[n] == 1)
    return zero, low


def brief_report(names, indeg):
    """Two static advisory lines for lint: orphan edges, then the exemption queue."""
    zero, low = orphans(indeg, names)
    print(f"orphan-edge advisory: {len(zero)} command(s) with 0 inbound "
          f"references, {len(low)} with exactly 1 (warn-only)")
    if zero:
        print("  0 inbound: " + ", ".join(zero))
    unreachable, missing = exemption_audit(names, indeg)
    print(f"exemption audit: {len(unreachable)} name(s) with indegree <= 1 (review), "
          f"{len(missing)} name(s) not on disk")
    if unreachable:
        print("  review: " + ", ".join(unreachable))
    if missing:
        print("  not on disk: " + ", ".join(missing))
    return 0


def full_report(names, indeg, tel, out_lines):
    def w(s=""):
        out_lines.append(s)

    used_set = set(tel["owner_writes"]) | set(tel["invoked_parents"])
    used, read_only_reachable, read_only_unreachable, pre_task, cold, missing = classify(
        names, used_set, indeg)
    read_only = sorted(read_only_reachable + read_only_unreachable)
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

    w("## Exempt but unreachable (review)")
    w("Exempt from the usage metric AND hard to reach in the command graph. Being on")
    w("the exemption list answers why the write-log does not see them; it does not")
    w(f"answer how a user finds them. Exemption list last read end to end: {READ_ONLY_REVIEWED}.")
    # Fed by exemption_audit, not by the classify bucket. The bucket is intersected
    # with "never invoked", so a name that telemetry has seen drops out of it even
    # though it is still unreachable in the graph. The section title promises the
    # static predicate, so it has to answer the same question the brief line does,
    # or the two outputs of one script disagree about the same word.
    queue, _missing_dup = exemption_audit(names, indeg)
    if queue:
        for n in queue:
            reason = READ_ONLY_BY_DESIGN.get(n, "(no reason recorded)")
            w(f"  indeg={indeg.get(n, 0)}  {n}: {reason}")
    else:
        w("  (none)")
    w("")
    w(f"Referential integrity: {len(missing)} exemption name(s) with no command on disk.")
    w("  " + (", ".join(missing) if missing else "(none)"))
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


def persona_maturity_level(path):
    """Read `maturity_level` from a persona SKILL.md frontmatter.

    The field is nested under `metadata:`, so it is indented and a column-zero
    match finds nothing. That is the first way this was written and it reported
    every persona as unknown while all nine carried a level.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"\s*maturity_level:\s*(L[1-5])\b", line)
                if m:
                    return m.group(1)
    except OSError:
        return None
    return None


def demand_report(paths):
    """One line per folder-shaped persona: owner tasks, owner writes, maturity level.

    The instrument the ladder's demand-based demotion rule would read. It reports
    and decides nothing: no window, no verdict, no demotion.

    Counting is by `owner`, which is what the ladder's ownership model means by a
    persona doing its job, and NOT by `invoked_by`. Measured 2026-08-30 the two
    differ enough to invert the answer: rls-auth-boundary-auditor and
    jtbd-switch-interviewer have 0 owner writes and 4 and 5 invoked_by writes.

    Telemetry lives under `projects/`, which is gitignored. On a clone that has
    none, every line says `not measured` rather than `0`, because a zero read as
    absence of demand would demote every persona in CI. Same rule and same words
    as check-substrate-ownership.py.

    Exactly one line per `commands/*/SKILL.md` on stdout, nothing else, so the
    line count is the persona count. Anything explanatory goes to stderr.
    """
    personas = sorted(
        (name, p) for name, p in paths.items()
        if os.path.basename(p) == "SKILL.md"
    )
    tel = scan_telemetry()
    measured = tel["n_logs"] > 0
    if not measured:
        print("flow-audit --demand: no .wos/VERIFICATION_LOG.jsonl found under "
              "projects/, so demand is not measured here.", file=sys.stderr)
    for name, path in personas:
        level = persona_maturity_level(path) or "unknown"
        if measured:
            tasks = tel["owner_tasks"].get(name, 0)
            writes = tel["owner_writes"].get(name, 0)
            print(f"{name}\ttasks={tasks}\towner_writes={writes}\tmaturity_level={level}")
        else:
            print(f"{name}\ttasks=not measured\towner_writes=not measured\t"
                  f"maturity_level={level}")
    return 0


def main(argv):
    paths = command_paths()
    names = command_names(paths)
    if not names:
        print("flow-audit: no commands found; run from the WOS repo.",
              file=sys.stderr)
        return 2

    if "--orphans-brief" in argv:
        return brief_report(names, reference_indegree(names, paths))

    if "--demand" in argv:
        return demand_report(paths)

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
