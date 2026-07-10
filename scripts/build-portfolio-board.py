#!/usr/bin/env python3
"""Render the cross-project portfolio board as a single offline HTML file.

Data sources (all optional inputs degrade visibly, never fail; D-1..D-4 of task
2026-07-03_html-dashboard):
1. Active tasks: `scripts/portfolio-review.sh --json` (the SAME classifier as the
   text board, per D-2; a failed call renders an error section, not a crash).
2. Initiative rows: `scripts/portfolio-review.sh --initiative --json` (the SAME
   parse as the text view, per D-2; unexpected rows and emitter failures become
   visible warnings, never a crash).
3. Outcome summaries: every `projects/*/OUTCOMES.jsonl` per
   `templates/OUTCOMES.schema.md` (latest event wins; a later revert overrides
   an earlier outcome; absent ledger renders "no outcome records yet").
4. Running background runs: `.wos/runs/*.json` per the runs-feed v1 contract
   (D-4: {schema_version, run_id, task, state, started_ts, last_update_ts,
   current_step}); an absent or empty directory renders an explicit
   no-running-runs state. Unknown fields are ignored (additive extension).

It RENDERS, never mutates (the ADR-0049 invariant): the only write is the
gitignored `projects/BOARD.html` (D-3), fully regenerated per invoke. The board
is measurement and visibility only; nothing here gates a workflow step.

Usage:
  python3 scripts/build-portfolio-board.py            # write projects/BOARD.html
  python3 scripts/build-portfolio-board.py --stdout   # print HTML, do not write
  python3 scripts/build-portfolio-board.py --verbose

Output lives under projects/ (gitignored per ADR-0007): local memory, no drift
guard. Stdlib only; no third-party dependencies. Modeled on
scripts/build-activity-timeline.py and scripts/build-knowledge-view.py.
"""
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

REPO = Path(__file__).resolve().parent.parent
PROJECTS = REPO / "projects"
RUNS_DIR = REPO / ".wos" / "runs"
OUTPUT_PATH = PROJECTS / "BOARD.html"
PORTFOLIO_SH = REPO / "scripts" / "portfolio-review.sh"

CLASS_ORDER = {"done-unclosed": 0, "blocked": 1, "my-move": 2, "stale": 3, "in-flight": 4}
KNOWN_STATUSES = ("merged", "waived", "not-merged", "reverted")

VERBOSE = False


def log(msg):
    if VERBOSE:
        sys.stderr.write(f"build-portfolio-board: {msg}\n")


def esc(value):
    """html.escape on everything interpolated into the page (precedent rule)."""
    return html.escape(str(value), quote=True)


# ---------------------------------------------------------------- section 1
def load_active_tasks():
    """Rows from portfolio-review.sh --json, or an error string (never raises)."""
    try:
        proc = subprocess.run(
            ["bash", str(PORTFOLIO_SH), "--json"],
            capture_output=True, text=True, timeout=120, cwd=str(REPO),
        )
        if proc.returncode != 0:
            return None, f"portfolio-review.sh --json exited {proc.returncode}: {proc.stderr.strip()[:300]}"
        rows = json.loads(proc.stdout)
        rows.sort(key=lambda r: (CLASS_ORDER.get(r.get("class"), 9), -(r.get("idle_days") or 0)))
        return rows, None
    except Exception as exc:  # degradation rule: render the failure, never crash
        return None, f"portfolio-review.sh --json unavailable: {exc}"


# ---------------------------------------------------------------- section 2
def load_initiatives():
    """(per-project rows, warnings) from portfolio-review.sh --initiative --json.

    Single parse point (the D-2 pattern the Active-tasks section already uses):
    the emitter carries the corrected column-scoped status parse, so this
    section can never drift from the text view. Emitter failure degrades to a
    visible warning, never a crash.
    """
    try:
        proc = subprocess.run(
            ["bash", str(PORTFOLIO_SH), "--initiative", "--json"],
            capture_output=True, text=True, timeout=120, cwd=str(REPO),
        )
        if proc.returncode != 0:
            return [], [f"portfolio-review.sh --initiative --json exited {proc.returncode}: {proc.stderr.strip()[:300]}"]
        flat = json.loads(proc.stdout)
    except Exception as exc:  # degradation rule: render the failure, never crash
        return [], [f"portfolio-review.sh --initiative --json unavailable: {exc}"]

    initiatives = []
    warnings = []
    by_project = {}
    for r in flat:
        if not isinstance(r, dict) or not r.get("task"):
            warnings.append(f"emitter row skipped (unexpected shape): {str(r)[:100]}")
            continue
        by_project.setdefault(r.get("project", "?"), []).append({
            "slug": r["task"],
            "status": r.get("status", "unknown"),
            "objective": r.get("objective", ""),
            "next": r.get("next_command", ""),
        })
    for project in sorted(by_project):
        initiatives.append({"project": project, "rows": by_project[project]})
    return initiatives, warnings


# ---------------------------------------------------------------- section 3
def load_outcomes():
    """Per-project outcome summaries per templates/OUTCOMES.schema.md."""
    summaries = []
    for ledger in sorted(PROJECTS.glob("*/OUTCOMES.jsonl")):
        project = ledger.parent.name
        outcome_latest = {}
        overall_latest = {}
        try:
            lines = ledger.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue  # tolerate a malformed line
            if not isinstance(rec, dict):
                continue  # tolerate a non-object line (valid JSON, wrong shape)
            task, ts, event = rec.get("task"), rec.get("ts"), rec.get("event")
            if not task or not ts or not event:
                continue
            prev = overall_latest.get(task)
            if prev is None or ts > prev[0]:
                overall_latest[task] = (ts, event)
            if event == "outcome":
                prev_o = outcome_latest.get(task)
                if prev_o is None or ts > prev_o[0]:
                    outcome_latest[task] = (ts, rec)
        if not outcome_latest:
            continue
        counts = {k: 0 for k in KNOWN_STATUSES}
        other = 0
        totals = []
        for task, (_ts, rec) in outcome_latest.items():
            latest = overall_latest.get(task)
            if latest and latest[1] == "revert":
                counts["reverted"] += 1
            else:
                status = rec.get("merge_status")
                if status in counts:
                    counts[status] += 1
                else:
                    other += 1
            pd = rec.get("phase_days")
            if isinstance(pd, dict) and isinstance(pd.get("total"), (int, float)):
                totals.append(pd["total"])
        summaries.append({
            "project": project,
            "closed": len(outcome_latest),
            "counts": counts,
            "other": other,
            "median_total": round(median(totals), 2) if totals else None,
        })
    return summaries


# ---------------------------------------------------------------- section 4
def load_runs():
    """(runs, warnings) from .wos/runs/*.json per the D-4 v1 contract."""
    runs = []
    warnings = []
    if not RUNS_DIR.is_dir():
        return runs, warnings
    for path in sorted(RUNS_DIR.glob("*.json")):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            warnings.append(f"{path.name}: unreadable or malformed ({exc})")
            continue
        if not isinstance(rec, dict):
            warnings.append(f"{path.name}: not a JSON object (ignored)")
            continue
        runs.append({
            "run_id": rec.get("run_id", path.stem),
            "task": rec.get("task", "?"),
            "state": rec.get("state", "unknown"),
            "started_ts": rec.get("started_ts", ""),
            "last_update_ts": rec.get("last_update_ts", ""),
            "current_step": rec.get("current_step", ""),
        })
    return runs, warnings


# ---------------------------------------------------------------- rendering
CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       margin: 2rem auto; max-width: 72rem; padding: 0 1rem; color: #1f2430; background: #fafafa; }
h1 { font-size: 1.4rem; } h2 { font-size: 1.1rem; margin-top: 2rem;
     border-bottom: 1px solid #ddd; padding-bottom: .3rem; }
table { border-collapse: collapse; width: 100%; font-size: .85rem; }
th, td { text-align: left; padding: .3rem .6rem; border-bottom: 1px solid #eee; vertical-align: top; }
th { color: #666; font-weight: 600; }
.badge { display: inline-block; padding: .05rem .5rem; border-radius: .6rem; font-size: .75rem; }
.b-done-unclosed { background: #e8f0fe; } .b-blocked { background: #fdecea; }
.b-my-move { background: #fef7e0; } .b-stale { background: #f3e8fd; }
.b-in-flight { background: #e6f4ea; } .b-unknown { background: #eee; }
.empty { color: #777; font-style: italic; }
.warn { color: #8a5a00; font-size: .8rem; }
.meta { color: #888; font-size: .8rem; }
code { background: #f0f0f0; padding: 0 .25rem; border-radius: .2rem; }
"""


def badge(cls):
    safe = re.sub(r"[^a-z-]", "", str(cls))
    return f'<span class="badge b-{safe or "unknown"}">{esc(cls)}</span>'


def render(active_rows, active_err, initiatives, init_warnings, outcomes, runs, run_warnings):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [f"<style>{CSS}</style>", "<h1>Fhorja portfolio board</h1>",
             f'<p class="meta">Generated {esc(now)} by scripts/build-portfolio-board.py. '
             f"Read-only projection; regenerate to refresh.</p>"]

    parts.append("<h2>Running background runs</h2>")
    if runs:
        parts.append("<table><tr><th>run</th><th>task</th><th>state</th><th>started</th>"
                     "<th>last update</th><th>current step</th></tr>")
        for r in runs:
            parts.append(f"<tr><td><code>{esc(r['run_id'])}</code></td><td>{esc(r['task'])}</td>"
                         f"<td>{badge(r['state'])}</td><td>{esc(r['started_ts'])}</td>"
                         f"<td>{esc(r['last_update_ts'])}</td><td>{esc(r['current_step'])}</td></tr>")
        parts.append("</table>")
    else:
        parts.append('<p class="empty">No running background runs (.wos/runs/ absent or empty).</p>')
    for w in run_warnings:
        parts.append(f'<p class="warn">warning: {esc(w)}</p>')

    parts.append("<h2>Active tasks</h2>")
    if active_err:
        parts.append(f'<p class="warn">Active-task board unavailable: {esc(active_err)}</p>')
    elif not active_rows:
        parts.append('<p class="empty">No active tasks.</p>')
    else:
        parts.append(f'<p class="meta">{len(active_rows)} active task(s), classified by '
                     f"scripts/portfolio-review.sh (one classifier, D-2).</p>")
        parts.append("<table><tr><th>class</th><th>idle</th><th>project</th><th>task</th><th>next</th></tr>")
        for r in active_rows:
            idle = r.get("idle_days")
            parts.append(f"<tr><td>{badge(r.get('class'))}</td><td>{esc(idle)}d</td>"
                         f"<td>{esc(r.get('project'))}</td><td>{esc(r.get('task'))}</td>"
                         f"<td><code>{esc(r.get('next_command'))}</code></td></tr>")
        parts.append("</table>")

    parts.append("<h2>Initiatives</h2>")
    if not initiatives:
        parts.append('<p class="empty">No INITIATIVE_INDEX.md found in any project.</p>')
    for ini in initiatives:
        parts.append(f"<h3>{esc(ini['project'])}</h3>")
        parts.append("<table><tr><th>task</th><th>status</th><th>objective</th><th>next</th></tr>")
        for row in ini["rows"]:
            parts.append(f"<tr><td>{esc(row['slug'])}</td><td>{badge(row['status'])}</td>"
                         f"<td>{esc(row['objective'][:160])}</td><td><code>{esc(row['next'])}</code></td></tr>")
        parts.append("</table>")
    for w in init_warnings:
        parts.append(f'<p class="warn">warning: {esc(w)}</p>')

    parts.append("<h2>Outcomes</h2>")
    if not outcomes:
        parts.append('<p class="empty">No outcome records yet (no projects/*/OUTCOMES.jsonl).</p>')
    else:
        parts.append("<table><tr><th>project</th><th>closed</th><th>merged</th><th>waived</th>"
                     "<th>not-merged</th><th>reverted</th><th>other</th><th>median cycle days</th></tr>")
        for s in outcomes:
            med = s["median_total"] if s["median_total"] is not None else "n/a"
            parts.append(f"<tr><td>{esc(s['project'])}</td><td>{s['closed']}</td>"
                         f"<td>{s['counts']['merged']}</td><td>{s['counts']['waived']}</td>"
                         f"<td>{s['counts']['not-merged']}</td><td>{s['counts']['reverted']}</td>"
                         f"<td>{s['other']}</td><td>{esc(med)}</td></tr>")
        parts.append("</table>")

    return "<!DOCTYPE html><html><head><meta charset='utf-8'>" \
           "<title>Fhorja portfolio board</title></head><body>" + "".join(parts) + "</body></html>"


def main(argv=None):
    global VERBOSE
    args = list(sys.argv[1:] if argv is None else argv)
    to_stdout = "--stdout" in args
    VERBOSE = "--verbose" in args

    active_rows, active_err = load_active_tasks()
    log(f"active tasks: {len(active_rows) if active_rows else 0} (err={active_err})")
    initiatives, init_warnings = load_initiatives()
    log(f"initiatives: {len(initiatives)} project(s), {len(init_warnings)} warning(s)")
    outcomes = load_outcomes()
    log(f"outcomes: {len(outcomes)} project(s)")
    runs, run_warnings = load_runs()
    log(f"runs: {len(runs)} running, {len(run_warnings)} warning(s)")

    page = render(active_rows, active_err, initiatives, init_warnings, outcomes, runs, run_warnings)
    if to_stdout:
        sys.stdout.write(page)
        return 0
    OUTPUT_PATH.write_text(page, encoding="utf-8")
    log(f"wrote {OUTPUT_PATH}")
    print(f"wrote {OUTPUT_PATH.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
