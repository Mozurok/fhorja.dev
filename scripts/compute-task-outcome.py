#!/usr/bin/env python3
"""compute-task-outcome.py

Compute one schema-valid OUTCOMES.jsonl line (see templates/OUTCOMES.schema.md,
schema_version 1) and print it to stdout. This script never writes files;
appending the printed line to a project's OUTCOMES.jsonl is the caller's job
(normally task-close).

Two modes:

1. Outcome mode (default): derive a task's cycle-time phases, merge status,
   sweep counts, and deliverable counts from its task-folder artifacts.

       compute-task-outcome.py <task-folder> --merge-status merged|waived|not-merged \
           [--evidence "..."] [--close-ts ISO]

2. Revert mode: record a human-observed revert of previously merged work.

       compute-task-outcome.py --revert <task-slug> --project <client__project> \
           --reason "..." [--evidence "..."]

Degradation rule: missing or unparseable data becomes a null field. This
script never raises a traceback and always exits 0 (stdlib only, no network).
"""

import argparse
import json
import os
import re
import secrets
import sys
import time
from datetime import datetime, timezone

SCHEMA_VERSION = 1
SOURCE_NAME = "compute-task-outcome.py"

# Boundary-owner groups per DECISIONS.md D-3 / the slice contract.
INIT_OWNERS = {"task-init"}
PLANNING_OWNERS = {
    "impact-analysis",
    "targeted-questions",
    "decision-interview",
    "invariants-and-non-goals",
    "implementation-plan",
    "self-critique-and-revise",
    "approve-plan",
}
IMPLEMENTATION_OWNERS = {
    "implement-approved-slice",
    "implement-fleet",
    "implement-slice-complement",
}
DELIVERY_PREP_OWNERS = {
    "review-hard",
    "repo-consistency-sweep",
    "security-review",
    "pr-package",
    "branch-commit",
    "team-update",
    "delivery-asset",
}

HEADER_RE = re.compile(r"<!--\s*wos:write\b(.*?)-->", re.DOTALL)
OWNER_ATTR_RE = re.compile(r"(?:^|\s)owner=(\S+)")
TS_ATTR_RE = re.compile(r"(?:^|\s)ts=(\S+)")


def parse_iso8601(value):
    """Parse an ISO 8601 timestamp (Z or +00:00 suffix) to an aware datetime.
    Returns None on any failure (degradation rule: never raise)."""
    if not value:
        return None
    try:
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def format_iso_ms(dt):
    """Format an aware datetime as ISO 8601 with millisecond precision and a
    Z suffix, matching the wos:write ts= convention."""
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def now_iso_ms():
    return format_iso_ms(datetime.now(timezone.utc))


def generate_run_id():
    """A ULID-shaped id: a time component plus random hex. Not a strict
    ULID, only shaped like one (timestamp prefix + random suffix) for
    correlation with the task's audit log, per the slice contract."""
    ts_ms = int(time.time() * 1000)
    return f"01J{ts_ms:x}{secrets.token_hex(8)}"


def read_text(path):
    """Read a text file, returning '' when missing or unreadable (never
    raises)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def extract_section(lines, heading):
    """Return the list of lines under a '## Heading' line, up to the next
    '## ' heading or EOF. Returns None when the heading is not found."""
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return lines[start:end]


def parse_task_state_headers(text):
    """Extract (owner, ts_datetime) pairs from every wos:write header comment
    in TASK_STATE.md. Unparseable timestamps are skipped, not fatal."""
    pairs = []
    for m in HEADER_RE.finditer(text):
        attrs = m.group(1)
        owner_m = OWNER_ATTR_RE.search(attrs)
        ts_m = TS_ATTR_RE.search(attrs)
        if not owner_m or not ts_m:
            continue
        ts_dt = parse_iso8601(ts_m.group(1))
        if ts_dt is not None:
            pairs.append((owner_m.group(1), ts_dt))
    return pairs


def parse_verification_log(path):
    """Extract (owner, ts_datetime) pairs from .wos/VERIFICATION_LOG.jsonl,
    when present. Malformed lines are skipped, not fatal."""
    pairs = []
    text = read_text(path)
    if not text:
        return pairs
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (ValueError, TypeError):
            continue
        owner = obj.get("owner")
        ts = obj.get("ts")
        if not owner or not ts:
            continue
        ts_dt = parse_iso8601(ts)
        if ts_dt is not None:
            pairs.append((owner, ts_dt))
    return pairs


def earliest(pool, owners):
    candidates = [ts for owner, ts in pool if owner in owners]
    return min(candidates) if candidates else None


def delta_days(a, b):
    """Fractional-day delta between two datetimes, or None if either is
    missing."""
    if a is None or b is None:
        return None
    return round((b - a).total_seconds() / 86400.0, 2)


def derive_project_task(task_folder):
    """Derive (project, project_root, task) from a task-folder path shaped
    projects/<project>/<lifecycle>/<task>, where <lifecycle> is active,
    archive, or the legacy done alias (task-close keeps using done/ in
    projects that already do). project/project_root are None when the path
    does not match that shape; task is always the folder basename."""
    norm = os.path.normpath(os.path.abspath(task_folder))
    parts = norm.split(os.sep)
    task = parts[-1] if parts else norm
    project = None
    project_root = None
    for i, p in enumerate(parts):
        if p == "projects" and i + 2 < len(parts) and parts[i + 2] in ("active", "archive", "done"):
            project = parts[i + 1]
            project_root = os.sep.join(parts[: i + 2])
            break
    return project, project_root, task


def is_separator_row(cells):
    non_empty = [c for c in cells if c.strip() != ""]
    if not non_empty:
        return False
    return all(re.fullmatch(r":?-+:?", c.strip()) for c in non_empty)


def parse_table_rows(lines):
    """Parse markdown table data rows (skips the header row and the
    ---|---|--- separator row)."""
    rows = []
    if not lines:
        return rows
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells:
            continue
        if cells[0].lower() == "date":
            continue
        if is_separator_row(cells):
            continue
        rows.append(cells)
    return rows


def compute_sweep(project_root, task_slug):
    """{"applied": N, "declined": N} attributable to this task's slug, from
    the project's REVIEW_PREFERENCES.md. None when the file is absent, the
    project root is unknown, or the format cannot be confidently parsed."""
    if not project_root:
        return None
    path = os.path.join(project_root, "REVIEW_PREFERENCES.md")
    if not os.path.isfile(path):
        return None
    text = read_text(path)
    if not text:
        return None
    try:
        lines = text.splitlines()
        declined_lines = extract_section(lines, "## Declined findings")
        applied_lines = extract_section(lines, "## Applied findings")
        if declined_lines is None and applied_lines is None:
            # Not the expected document shape; parse uncertainty.
            return None
        declined_rows = parse_table_rows(declined_lines)
        applied_rows = parse_table_rows(applied_lines)
        declined = sum(1 for row in declined_rows if any(task_slug in c for c in row))
        applied = sum(1 for row in applied_rows if any(task_slug in c for c in row))
        return {"applied": applied, "declined": declined}
    except Exception:
        return None


def compute_deliverables(task_state_text):
    """{"done": N, "de_scoped": N} from '## Requested deliverables'. None
    when the section is absent."""
    lines = task_state_text.splitlines()
    section = extract_section(lines, "## Requested deliverables")
    if section is None:
        return None
    done = 0
    de_scoped = 0
    for line in section:
        s = line.strip()
        if not s.startswith("-"):
            continue
        if "[done]" in s:
            done += 1
        if "de-scoped" in s:
            de_scoped += 1
    return {"done": done, "de_scoped": de_scoped}


def build_outcome_record(task_folder, merge_status, evidence, close_ts_arg):
    project, project_root, task = derive_project_task(task_folder)

    task_state_path = os.path.join(task_folder, "TASK_STATE.md")
    task_state_text = read_text(task_state_path)

    verification_log_path = os.path.join(task_folder, ".wos", "VERIFICATION_LOG.jsonl")

    pool = parse_task_state_headers(task_state_text)
    pool.extend(parse_verification_log(verification_log_path))

    if close_ts_arg:
        close_dt = parse_iso8601(close_ts_arg)
        if close_dt is None:
            # Unparseable input; degrade to now() rather than losing the
            # close boundary entirely.
            close_dt = datetime.now(timezone.utc)
    else:
        close_dt = datetime.now(timezone.utc)
    close_str = format_iso_ms(close_dt)

    if not pool:
        phases = None
        phase_days = None
    else:
        init_dt = earliest(pool, INIT_OWNERS)
        planning_dt = earliest(pool, PLANNING_OWNERS)
        implementation_dt = earliest(pool, IMPLEMENTATION_OWNERS)
        delivery_prep_dt = earliest(pool, DELIVERY_PREP_OWNERS)

        phases = {
            "init": format_iso_ms(init_dt) if init_dt else None,
            "planning": format_iso_ms(planning_dt) if planning_dt else None,
            "implementation": format_iso_ms(implementation_dt) if implementation_dt else None,
            "delivery_prep": format_iso_ms(delivery_prep_dt) if delivery_prep_dt else None,
            "close": close_str,
        }
        phase_days = {
            "init_to_planning": delta_days(init_dt, planning_dt),
            "planning_to_implementation": delta_days(planning_dt, implementation_dt),
            "implementation_to_delivery_prep": delta_days(implementation_dt, delivery_prep_dt),
            "delivery_prep_to_close": delta_days(delivery_prep_dt, close_dt),
            "total": delta_days(init_dt, close_dt) if init_dt else None,
        }

    sweep = compute_sweep(project_root, task)
    deliverables = compute_deliverables(task_state_text)

    return {
        "schema_version": SCHEMA_VERSION,
        "event": "outcome",
        "ts": close_str,
        "project": project,
        "task": task,
        "phases": phases,
        "phase_days": phase_days,
        "merge_status": merge_status,
        "merge_evidence": evidence if evidence else None,
        "sweep": sweep,
        "deliverables": deliverables,
        "source": SOURCE_NAME,
        "run_id": generate_run_id(),
    }


def build_revert_record(task_slug, project, reason, evidence):
    return {
        "schema_version": SCHEMA_VERSION,
        "event": "revert",
        "ts": now_iso_ms(),
        "project": project,
        "task": task_slug,
        "reason": reason,
        "evidence": evidence if evidence else None,
    }


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Compute one OUTCOMES.jsonl line (schema_version 1) and print it to stdout.",
    )
    parser.add_argument(
        "task_folder",
        nargs="?",
        default=None,
        help="Path to the task folder (outcome mode).",
    )
    parser.add_argument(
        "--revert",
        metavar="TASK_SLUG",
        default=None,
        help="Switch to revert mode; the task slug whose merged work was reverted.",
    )
    parser.add_argument("--project", default=None, help="Project folder name (revert mode).")
    parser.add_argument(
        "--merge-status",
        dest="merge_status",
        choices=["merged", "waived", "not-merged"],
        default=None,
        help="Human verdict at task-close (outcome mode).",
    )
    parser.add_argument("--evidence", default=None, help="Citation for the verdict or the revert.")
    parser.add_argument("--reason", default=None, help="Why the revert happened (revert mode).")
    parser.add_argument(
        "--close-ts",
        dest="close_ts",
        default=None,
        help="ISO 8601 close timestamp; defaults to now (outcome mode).",
    )
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.revert is not None:
        if not args.project or not args.reason:
            parser.error("--revert mode requires --project and --reason")
        try:
            record = build_revert_record(args.revert, args.project, args.reason, args.evidence)
        except Exception as exc:  # degradation rule: never traceback
            sys.stderr.write(f"compute-task-outcome: warning: {exc}\n")
            record = {
                "schema_version": SCHEMA_VERSION,
                "event": "revert",
                "ts": now_iso_ms(),
                "project": args.project,
                "task": args.revert,
                "reason": args.reason,
                "evidence": args.evidence if args.evidence else None,
            }
        print(json.dumps(record))
        return 0

    if not args.task_folder or not args.merge_status:
        parser.error("outcome mode requires <task-folder> and --merge-status")

    try:
        record = build_outcome_record(args.task_folder, args.merge_status, args.evidence, args.close_ts)
    except Exception as exc:  # degradation rule: never traceback
        sys.stderr.write(f"compute-task-outcome: warning: {exc}\n")
        _, _, task = derive_project_task(args.task_folder)
        record = {
            "schema_version": SCHEMA_VERSION,
            "event": "outcome",
            "ts": now_iso_ms(),
            "project": None,
            "task": task,
            "phases": None,
            "phase_days": None,
            "merge_status": args.merge_status,
            "merge_evidence": args.evidence if args.evidence else None,
            "sweep": None,
            "deliverables": None,
            "source": SOURCE_NAME,
            "run_id": generate_run_id(),
        }
    print(json.dumps(record))
    return 0


if __name__ == "__main__":
    sys.exit(main())
