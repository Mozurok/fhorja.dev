#!/usr/bin/env python3
"""Render a task's activity timeline as a single offline HTML file.

Data source: the Fhorja audit log `.wos/VERIFICATION_LOG.jsonl` (append-only, one JSON
object per substrate write). This script READS that log and renders a human-facing,
chronological `ACTIVITY.html` inside the task folder: one entry per command run
(grouped by `run_id`), each showing the command, a short "what it did and why", the
files it touched, and a timestamp. It is an activity / change log, not a status board.

Scope (per the task design, ADR-0049):
- DL1 (grouping): group log lines by `run_id` into one entry per command run; lines
  with no `run_id` (legacy / free-form) each become their own entry. Never drop a line.
- DL2 (location): read the task's own `<task>/.wos/VERIFICATION_LOG.jsonl` when present;
  otherwise read the repository-root `.wos/VERIFICATION_LOG.jsonl` filtered by the `task`
  field (the task folder's basename).
- D-A (why): prefer a per-run `summary` field; fall back to aggregated `reason` values;
  fall back again to other free-form descriptive keys so messy legacy lines still say
  something. Each entry is capped at 3 lines.
- D-B (coverage): only state-changing (audit-logged) commands appear. Read-only and
  navigation commands do not write the log and are not shown; the page says so.
- A1 (trace nesting): an entry whose `invoked_by` names another entry's owner in this same
  log renders nested under that owning entry, one indentation level per generation (the
  Langfuse trace/span parent-child model, rendered on a flat audit log instead of a live
  span tree). See `link_trace_children()` for the mis-parenting tie rule. Entries with no
  `invoked_by`, or whose named owner has no run in this log, stay flat (DL1: never dropped,
  just unnested); a log with no `invoked_by` links renders the same entries in the same
  order as before this nesting was added.

This is an additive HUMAN VIEW of the same data as the machine-readable log. It does not
replace or modify the log, and it touches no command contract.

Usage:
  python3 scripts/build-activity-timeline.py <task-folder-path>          # write <task>/ACTIVITY.html
  python3 scripts/build-activity-timeline.py <task-folder-path> --stdout # print HTML, do not write
  python3 scripts/build-activity-timeline.py <task-folder-path> --verbose
  python3 scripts/build-activity-timeline.py <project-folder-path> --project  # write <project>/ACTIVITY.html

Project mode (--project, ADR-0054 D-6): the positional arg is a project folder
(`projects/<client>__<project>/`). The script aggregates every task's audit log under
`active/`, `archive/`, and the legacy `done/` into one project-scoped `ACTIVITY.html`,
each entry tagged with its task. The per-task mode (no flag) is unchanged.

Output lives under projects/ (gitignored per ADR-0007): local task memory, no drift guard.
Stdlib only; no third-party dependencies. Modeled on scripts/build-command-catalog.py.
"""
import sys
import json
import html
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT_LOG = REPO / ".wos" / "VERIFICATION_LOG.jsonl"
OUTPUT_NAME = "ACTIVITY.html"
MAX_WHY_LINES = 3          # D-A / D2: cap each entry to 3 lines
MAX_FILE_CHIPS = 10        # keep an entry scannable; overflow folds into "+N more"

# Ordered fallback chain for the "why" text (D-A). `summary` first; `reason` next;
# then other free-form descriptive keys the legacy log uses, so no entry is blank.
WHY_PRIMARY = ["summary"]
WHY_SECONDARY = ["reason"]
WHY_FALLBACK = ["note", "plan", "validation", "result", "action", "status",
                "decision", "decisions", "finding", "findings"]
# Keys that may carry touched-file paths, in priority order.
FILE_LIST_KEYS = ["writes", "files", "moved", "merged"]
FILE_STR_KEYS = ["file", "commit"]


def resolve_log(task_dir):
    """DL2: per-task log if present, else root log filtered by task basename."""
    per_task = task_dir / ".wos" / "VERIFICATION_LOG.jsonl"
    slug = task_dir.name
    if per_task.is_file():
        return per_task, None  # read every line; the file is already task-scoped
    return ROOT_LOG, slug      # read root, filter by `task` == slug


def load_records(log_path, task_filter):
    """Parse JSONL defensively. Returns (records, parsed, skipped)."""
    records, parsed, skipped = [], 0, 0
    if not log_path.is_file():
        return records, parsed, skipped
    with log_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (ValueError, TypeError):
                skipped += 1
                continue
            if not isinstance(obj, dict):
                skipped += 1
                continue
            parsed += 1
            if task_filter is not None and obj.get("task") != task_filter:
                continue
            records.append(obj)
    return records, parsed, skipped


def _first_str(lines, keys):
    for d in lines:
        for k in keys:
            v = d.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _collect_strs(lines, keys):
    out = []
    for d in lines:
        for k in keys:
            v = d.get(k)
            if isinstance(v, str) and v.strip() and v.strip() not in out:
                out.append(v.strip())
    return out


def _collect_files(lines):
    out = []
    for d in lines:
        for k in FILE_LIST_KEYS:
            v = d.get(k)
            if isinstance(v, list):
                for x in v:
                    if isinstance(x, str) and x and x not in out:
                        out.append(x)
        for k in FILE_STR_KEYS:
            v = d.get(k)
            if isinstance(v, str) and v and v not in out:
                out.append(v)
    return out


def _fmt_ts(ts):
    if not isinstance(ts, str) or not ts:
        return ""
    return ts.replace("T", " ").replace("Z", "")[:16]


def build_entries(records):
    """DL1: one entry per command run.

    Group key is (run_id, command). The canonical per-section lines of a single command
    invocation share both, so they collapse into one entry (DL1). Distinct commands that
    happen to reuse a run_id (a real legacy hazard: copied transaction headers) stay
    separate, honoring "one entry per command run". A run_id is unique per invocation by
    contract, so adding the command to the key never wrongly merges two real runs. Lines
    with no run_id each stand alone (no reliable key to merge them).
    """
    groups, order = {}, []
    for idx, d in enumerate(records):
        rid = d.get("run_id")
        cmd = _first_str([d], ["cmd", "owner"]) or "(unknown command)"
        bucket = rid if isinstance(rid, str) and rid else "__norid_%d" % idx
        key = (bucket, cmd)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(d)

    entries = []
    for key in order:
        bucket, command = key
        lines = groups[key]
        timestamps = [d.get("ts") for d in lines if isinstance(d.get("ts"), str)]
        ts = min(timestamps) if timestamps else ""
        mode = _first_str(lines, ["mode"])
        whys = (_collect_strs(lines, WHY_PRIMARY)
                or _collect_strs(lines, WHY_SECONDARY)
                or _collect_strs(lines, WHY_FALLBACK))
        if not whys:
            whys = ["(no summary recorded for this run)"]
        whys = whys[:MAX_WHY_LINES]
        files = _collect_files(lines)
        run_id = "" if bucket.startswith("__norid_") else bucket
        entries.append({
            "ts": ts, "command": command, "mode": mode,
            "whys": whys, "files": files, "run_id": run_id,
            "writes_n": len(lines),
            # Set only in project mode (records annotated with `_task`); empty in
            # per-task mode, so render_entry emits no task chip and the per-task
            # output stays byte-identical.
            "task": _first_str(lines, ["_task"]),
            # A1: the owner this run's lines say invoked it, e.g. a fleet orchestrator or
            # approve-plan re-triggering a command. Empty when absent (most lines carry
            # `invoked_by: null`). Resolved into actual parent/child links by
            # link_trace_children(), never here (this function stays grouping-only).
            "invoked_by": _first_str(lines, ["invoked_by"]),
            "children": [],
        })
    entries.sort(key=lambda e: (e["ts"], e["command"]))
    return entries


def link_trace_children(entries):
    """A1: nest an entry under the entry it names via `invoked_by` (the Langfuse
    trace/span parent-child model, applied to this flat audit log). Purely a rendering-time
    grouping on top of `build_entries()`'s output; it never removes an entry, so DL1 ("never
    drop a line") still holds -- every entry stays reachable, either at the top level or
    nested under a resolved parent.

    Mis-parenting tie rule: when `invoked_by` names an owner with more than one run in this
    log, resolve within the same task first (relevant only in --project mode, where entries
    from unrelated tasks can share a command name; per-task mode has one task so this is a
    no-op there), then to the run with the nearest ts at or before the child's own ts. If no
    same-task candidate run has a ts at or before the child's, fall back to the earliest-ts
    same-task run for that owner. An `invoked_by` naming an owner absent from this log (or
    absent from this task in project mode), or a resolution that would create a cycle (an
    entry nested under its own descendant), keeps the entry at the top level: never dropped,
    only left unnested.

    Returns the top-level entries (those without a resolved parent) in their original,
    already-chronological order. A log with no `invoked_by` links resolves no parents, so
    this returns `entries` filtered to itself: same entries, same order as before nesting.
    """
    by_command = {}
    for e in entries:
        by_command.setdefault(e["command"], []).append(e)

    parent_of = {}  # id(child entry) -> id(parent entry); tracked to guard against cycles
    child_ids = set()
    for e in entries:
        parent_name = e.get("invoked_by")
        if not parent_name:
            continue
        # Same-task scoping (a no-op in per-task mode, where every entry's "task" is "").
        candidates = [c for c in by_command.get(parent_name, [])
                      if c is not e and c.get("task") == e.get("task")]
        if not candidates:
            continue
        earlier = [c for c in candidates if c["ts"] and e["ts"] and c["ts"] <= e["ts"]]
        parent = max(earlier, key=lambda c: c["ts"]) if earlier else \
            min(candidates, key=lambda c: c["ts"])
        ancestor, cyclical = id(parent), False
        while ancestor in parent_of:
            ancestor = parent_of[ancestor]
            if ancestor == id(e):
                cyclical = True
                break
        if cyclical:
            continue
        parent["children"].append(e)
        parent_of[id(e)] = id(parent)
        child_ids.add(id(e))

    for e in entries:
        e["children"].sort(key=lambda c: c["ts"])
    return [e for e in entries if id(e) not in child_ids]


def _esc(s):
    return html.escape(str(s), quote=True)


def render_entry(e, depth=0):
    why_html = "<br>".join(_esc(w) for w in e["whys"])
    chips = ""
    files = e["files"]
    if files:
        shown = files[:MAX_FILE_CHIPS]
        chips = "".join('<span class="file">%s</span>' % _esc(f) for f in shown)
        if len(files) > MAX_FILE_CHIPS:
            chips += '<span class="file more">+%d more</span>' % (len(files) - MAX_FILE_CHIPS)
    else:
        chips = '<span class="file none">no files recorded</span>'
    mode = '<span class="mode">%s</span>' % _esc(e["mode"]) if e["mode"] else ""
    rid = '<span class="rid">%s</span>' % _esc(e["run_id"]) if e["run_id"] else ""
    # Project-mode only: tag each entry with its task. Styled inline so the shared
    # CSS (and therefore the per-task output) is unchanged. Empty in per-task mode.
    task = ('<span class="task" style="font:10.5px var(--mono);color:var(--accent);'
            'background:var(--accent-weak);border-radius:5px;padding:1px 7px">%s</span>'
            % _esc(e["task"])) if e.get("task") else ""
    # A1: children resolved by link_trace_children() render nested inside this entry's own
    # article, one <div class="children"> level per generation. Empty when there are none,
    # so a flat entry (no invoked_by resolved to it) renders exactly as before this field
    # existed.
    children = e.get("children") or []
    nested_html = ""
    if children:
        nested_html = '<div class="children">%s</div>' % "\n".join(
            render_entry(c, depth + 1) for c in children)
    cls = "entry nested" if depth else "entry"
    return (
        '<article class="%s">'
        '<div class="ehead"><code class="cmd">%s</code><span class="ts">%s</span></div>'
        '<div class="why">%s</div>'
        '<div class="files">%s</div>'
        '<div class="emeta">%s%s%s</div>'
        '%s'
        '</article>'
    ) % (cls, _esc(e["command"]), _esc(_fmt_ts(e["ts"])), why_html, chips, task, mode, rid,
         nested_html)


HTML_SHELL = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{
  --bg:#ffffff;--bg-soft:#f7f7f8;--fg:#18181b;--muted:#71717a;--faint:#a1a1aa;
  --line:#e4e4e7;--line-soft:#efeff1;--accent:#4f46e5;--accent-weak:#eef2ff;
  --card:#ffffff;--code-bg:#f4f4f5;--shadow:0 1px 2px rgba(24,24,27,.05),0 1px 3px rgba(24,24,27,.04);
  --radius:12px;--font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}
html[data-theme="dark"]{
  --bg:#0b0d12;--bg-soft:#0f1218;--fg:#e8e8ea;--muted:#9aa0ac;--faint:#6b7280;
  --line:#242833;--line-soft:#1b1e26;--accent:#818cf8;--accent-weak:#1a1d2b;
  --card:#12151c;--code-bg:#1a1e27;--shadow:0 1px 2px rgba(0,0,0,.4);
}
*{box-sizing:border-box}
body{margin:0;font:15px/1.6 var(--font);background:var(--bg);color:var(--fg);-webkit-font-smoothing:antialiased}
code{font:13px/1.5 var(--mono)}
.topbar{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:16px;padding:12px 22px;
  background:color-mix(in srgb,var(--bg) 86%,transparent);backdrop-filter:saturate(160%) blur(10px);
  border-bottom:1px solid var(--line)}
.brand{font-weight:650;letter-spacing:-.01em;white-space:nowrap}
.brand .dot{color:var(--accent)}
.search{position:relative;flex:1;max-width:520px;margin:0 auto}
#q{width:100%;padding:9px 12px 9px 34px;font:14px var(--font);color:var(--fg);background:var(--bg-soft);
  border:1px solid var(--line);border-radius:9px;outline:none}
#q:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-weak)}
.search .mag{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--faint);font-size:14px}
.tog{cursor:pointer;border:1px solid var(--line);background:var(--bg-soft);color:var(--fg);border-radius:9px;
  padding:7px 10px;font-size:14px;line-height:1}
.tog:hover{border-color:var(--accent)}
.wrap{max-width:880px;margin:0 auto;padding:26px 22px 80px}
h1{font-size:20px;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:13px;margin:0 0 6px}
.note{color:var(--faint);font-size:12.5px;margin:0 0 22px;max-width:72ch}
.timeline{position:relative;margin:0;padding:0 0 0 22px;border-left:2px solid var(--line)}
.entry{position:relative;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  padding:14px 16px;margin:0 0 14px;box-shadow:var(--shadow)}
.entry::before{content:"";position:absolute;left:-29px;top:18px;width:10px;height:10px;border-radius:50%;
  background:var(--accent);border:2px solid var(--bg)}
.ehead{display:flex;align-items:baseline;justify-content:space-between;gap:10px}
.ehead .cmd{font-size:15px;font-weight:650;color:var(--fg)}
.ehead .ts{font:11.5px var(--mono);color:var(--faint);white-space:nowrap}
.why{margin:8px 0 10px;color:var(--fg);font-size:13.5px;display:-webkit-box;-webkit-line-clamp:3;
  -webkit-box-orient:vertical;overflow:hidden}
.files{display:flex;flex-wrap:wrap;gap:6px}
.file{font:11px/1.5 var(--mono);background:var(--bg-soft);border:1px solid var(--line-soft);border-radius:6px;
  padding:1px 7px;color:var(--muted)}
.file.more{color:var(--faint);background:transparent}
.file.none{color:var(--faint);background:transparent;border-style:dashed}
.emeta{display:flex;flex-wrap:wrap;gap:8px;margin-top:9px}
.emeta .mode{font:10px var(--mono);text-transform:uppercase;letter-spacing:.05em;color:var(--accent);
  background:var(--accent-weak);border-radius:5px;padding:1px 7px}
.emeta .rid{font:10.5px var(--mono);color:var(--faint)}
.children{position:relative;margin:12px 0 0;padding-left:20px;border-left:2px dashed var(--line);
  display:flex;flex-direction:column;gap:12px}
.entry.nested{box-shadow:none;margin-bottom:0}
.entry.nested::before{display:none}
.empty{display:none;color:var(--muted);padding:40px 0;text-align:center}
footer{color:var(--faint);font-size:12px;border-top:1px solid var(--line-soft);margin-top:26px;padding-top:18px}
@media(max-width:640px){.topbar .brand .full{display:none}}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand"><span class="dot">/</span> Fhorja <span class="full">activity timeline</span></div>
  <div class="search"><span class="mag">&#x2315;</span>
    <input id="q" type="search" placeholder="Filter by command, file, or text..." autocomplete="off" spellcheck="false"></div>
  <button class="tog" id="theme" type="button" aria-label="Toggle theme">&#x25D1;</button>
</div>
<div class="wrap">
  <h1>__TITLE__</h1>
  <p class="sub">__SUB__</p>
  <p class="note">__NOTE__</p>
  <div class="timeline" id="tl">
__ENTRIES__
  </div>
  <div class="empty" id="empty">No entries match the filter.</div>
  <footer>__FOOTER__</footer>
</div>
<script>
(function(){
  var t=document.getElementById('theme'),r=document.documentElement;
  t.addEventListener('click',function(){r.setAttribute('data-theme',r.getAttribute('data-theme')==='dark'?'light':'dark')});
  var q=document.getElementById('q'),items=[].slice.call(document.querySelectorAll('.entry')),e=document.getElementById('empty');
  q.addEventListener('input',function(){
    var v=q.value.toLowerCase(),n=0;
    items.forEach(function(el){var hit=el.textContent.toLowerCase().indexOf(v)>=0;el.style.display=hit?'':'none';if(hit)n++;});
    e.style.display=n?'none':'block';
  });
})();
</script>
</body>
</html>
"""


def render_html(task_dir, entries, top_entries, log_path):
    title = "Activity timeline: %s" % task_dir.name
    sub = "%d command run%s, in order. A human-readable view of the Fhorja audit log." % (
        len(entries), "" if len(entries) == 1 else "s")
    note = ("Activity / change log: this shows state-changing (audit-logged) commands only. "
            "Read-only and navigation commands do not write the log and are not listed. "
            "Each entry is one command run (grouped by run_id), capped at 3 lines. A run "
            "another entry's invoked_by names as its owner renders nested under it.")
    body = "\n".join(render_entry(e) for e in top_entries) if entries else \
        '<p class="sub">No audit-logged activity found for this task yet.</p>'
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    try:
        rel_log = log_path.relative_to(REPO)
    except ValueError:
        rel_log = log_path
    footer = ("Generated %s by scripts/build-activity-timeline.py from %s. "
              "Regenerate on demand; this file is local task memory (gitignored).") % (
        _esc(generated), _esc(str(rel_log)))
    return (HTML_SHELL
            .replace("__TITLE__", _esc(title))
            .replace("__SUB__", _esc(sub))
            .replace("__NOTE__", _esc(note))
            .replace("__ENTRIES__", body)
            .replace("__FOOTER__", footer))


# --- Project mode (--project, ADR-0054 D-6) -------------------------------------

PROJECT_TASK_DIRS = ["active", "archive", "done"]  # `done/` is the legacy alias


def resolve_project_task_dirs(project_dir):
    """List task folders under active/, archive/, and legacy done/ that carry an
    audit log (per-task or root-filtered). Sorted by name for a stable read order;
    the final entries are re-sorted chronologically by build_entries."""
    out = []
    for sub in PROJECT_TASK_DIRS:
        container = project_dir / sub
        if not container.is_dir():
            continue
        for task_dir in sorted(container.iterdir(), key=lambda p: p.name):
            if not task_dir.is_dir():
                continue
            log_path, task_filter = resolve_log(task_dir)
            if log_path.is_file():
                out.append((task_dir, log_path, task_filter))
    return out


def load_project_records(project_dir):
    """Aggregate records across every task under the project, annotating each with
    `_task` (the task folder name) so build_entries can tag the entry. Returns
    (records, n_tasks, parsed, skipped)."""
    records, parsed, skipped, n_tasks = [], 0, 0, 0
    for task_dir, log_path, task_filter in resolve_project_task_dirs(project_dir):
        recs, p, s = load_records(log_path, task_filter)
        if not recs:
            continue
        n_tasks += 1
        parsed += p
        skipped += s
        for r in recs:
            r["_task"] = task_dir.name  # annotate; build_entries reads this
            records.append(r)
    return records, n_tasks, parsed, skipped


def render_project_html(project_dir, entries, top_entries, n_tasks):
    title = "Activity timeline: %s" % project_dir.name
    sub = "%d command run%s across %d task%s. A human-readable view of the Fhorja audit log." % (
        len(entries), "" if len(entries) == 1 else "s",
        n_tasks, "" if n_tasks == 1 else "s")
    note = ("Project activity / change log: state-changing (audit-logged) commands only, "
            "across every task under active/, archive/, and done/. Each entry is one command "
            "run (grouped by run_id), tagged with its task, capped at 3 lines. Read-only and "
            "navigation commands do not write the log and are not listed. A run another "
            "entry's invoked_by names as its owner (within the same task) renders nested "
            "under it.")
    body = "\n".join(render_entry(e) for e in top_entries) if entries else \
        '<p class="sub">No audit-logged activity found for this project yet.</p>'
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    try:
        rel_proj = project_dir.relative_to(REPO)
    except ValueError:
        rel_proj = project_dir
    footer = ("Generated %s by scripts/build-activity-timeline.py --project from "
              "%d task log(s) under %s. Regenerate on demand; this file is local "
              "project memory (gitignored).") % (_esc(generated), n_tasks, _esc(str(rel_proj)))
    return (HTML_SHELL
            .replace("__TITLE__", _esc(title))
            .replace("__SUB__", _esc(sub))
            .replace("__NOTE__", _esc(note))
            .replace("__ENTRIES__", body)
            .replace("__FOOTER__", footer))


def run_project(project_dir, to_stdout, verbose):
    records, n_tasks, parsed, skipped = load_project_records(project_dir)
    entries = build_entries(records)
    top_entries = link_trace_children(entries)
    if verbose:
        sys.stderr.write("project: %s (%d task log(s))\n" % (project_dir, n_tasks))
        sys.stderr.write("parsed %d line(s), skipped %d unparseable, %d entr(y/ies), "
                         "%d nested\n" % (parsed, skipped, len(entries),
                                          len(entries) - len(top_entries)))
    document = render_project_html(project_dir, entries, top_entries, n_tasks)
    if to_stdout:
        sys.stdout.write(document)
        return 0
    out_path = project_dir / OUTPUT_NAME
    out_path.write_text(document, encoding="utf-8")
    sys.stderr.write("wrote %s (%d entr%s across %d task%s)\n" % (
        out_path, len(entries), "y" if len(entries) == 1 else "ies",
        n_tasks, "" if n_tasks == 1 else "s"))
    return 0


# --------------------------------------------------------------------------------


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    verbose = "--verbose" in flags
    to_stdout = "--stdout" in flags
    project_mode = "--project" in flags

    if not args:
        sys.stderr.write("usage: build-activity-timeline.py <task-folder-path> [--stdout] [--verbose]\n"
                         "       build-activity-timeline.py <project-folder-path> --project [--stdout] [--verbose]\n")
        return 2

    if project_mode:
        project_dir = Path(args[0]).resolve()
        if not project_dir.is_dir():
            sys.stderr.write("error: project folder not found: %s\n" % project_dir)
            return 2
        return run_project(project_dir, to_stdout, verbose)

    task_dir = Path(args[0]).resolve()
    if not task_dir.is_dir():
        sys.stderr.write("error: task folder not found: %s\n" % task_dir)
        return 2

    log_path, task_filter = resolve_log(task_dir)
    records, parsed, skipped = load_records(log_path, task_filter)
    entries = build_entries(records)
    top_entries = link_trace_children(entries)

    if verbose:
        scope = "per-task log" if task_filter is None else ("root log filtered by task=%s" % task_filter)
        sys.stderr.write("source: %s (%s)\n" % (log_path, scope))
        sys.stderr.write("parsed %d line(s), skipped %d unparseable, matched %d, %d entr(y/ies), "
                         "%d nested\n" % (parsed, skipped, len(records), len(entries),
                                          len(entries) - len(top_entries)))

    document = render_html(task_dir, entries, top_entries, log_path)
    if to_stdout:
        sys.stdout.write(document)
        return 0
    out_path = task_dir / OUTPUT_NAME
    out_path.write_text(document, encoding="utf-8")
    sys.stderr.write("wrote %s (%d entr%s)\n" % (out_path, len(entries), "y" if len(entries) == 1 else "ies"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
