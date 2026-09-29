#!/usr/bin/env python3
"""compute-task-outcome.py

Compute one schema-valid OUTCOMES.jsonl line (see templates/OUTCOMES.schema.md,
schema_version 1) and print it to stdout. This script never writes files;
appending the printed line to a project's OUTCOMES.jsonl is the caller's job
(normally task-close).

Two modes:

1. Outcome mode (default): derive a task's cycle-time phases, merge status,
   sweep counts, deliverable counts, and fired escalations from its
   task-folder artifacts.

       compute-task-outcome.py <task-folder> --merge-status merged|waived|not-merged \
           [--evidence "..."] [--close-ts ISO]

   Optional: --usage-source <adapter>:<path> fills output_tokens_by_model and
   output_tokens_source (E0, ADR-0236). Adapters: `json` (a {model: tokens}
   file any harness can write) and `claude-code` (a transcript file or a
   directory of them, attributed to the task by name per ADR-0238). No source,
   nothing readable, nothing attributable, or a count the transcript does not
   hold records null, and output_tokens_null_reason says which.

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


ESCALATIONS_LINE = re.compile(r"^\s*[-*]?\s*(?:\*\*)?Escalations(?:\*\*)?\s*:",
                              re.IGNORECASE | re.MULTILINE)


def read_pipeline_tier(task_state_text):
    """The ADR-0025 complexity tier from '## Recommended pipeline'. None when
    the section is absent or names no single tier. Read-only: this never asks
    for a new field in TASK_STATE.md, it reads what task-init already writes."""
    lines = task_state_text.splitlines()
    section = extract_section(lines, "## Recommended pipeline")
    if section is None:
        return None
    canonical = {"express": "Express", "standard": "Standard",
                 "disciplined": "Disciplined", "strict": "Strict"}

    def only_tier(text):
        """The single tier named in text, or None when it names none or more
        than one. The template ships the unfilled menu
        '[Express | Standard | Disciplined | Strict]', so taking the first word
        would read every untouched template as Express and bias the very
        measurement this field exists to produce."""
        found = {canonical[w.lower()] for w in re.findall(r"[A-Za-z]+", text)
                 if w.lower() in canonical}
        return found.pop() if len(found) == 1 else None

    labelled = re.compile(r"^\s*[-*]?\s*(?:\*\*)?Tier(?:\*\*)?\s*:\s*(.+)$",
                          re.IGNORECASE)
    for line in section:
        m = labelled.match(line)
        if m:
            tier = only_tier(m.group(1))
            if tier is not None:
                return tier
    body = "\n".join(section)
    # B1, 2026-09-17. The body scan reads a tier name out of prose that DENIES it.
    # Measured: the sentence "the strict-surface disqualifier does not fire" returns
    # 'Strict', and it wrote that into OUTCOMES.jsonl twice on 2026-09-16 before
    # anyone noticed. A denial naming TWO labels escapes by accident, because the
    # single-tier rule needs exactly one; a denial naming one does not.
    # The guard uses a signal that already exists rather than a new field. ADR-0207
    # retired the tier labels and replaced them with the escalation count, so a
    # section carrying an `Escalations:` line was written after the labels stopped
    # meaning anything. Any tier word in such a section is prose, not a declaration,
    # and the honest answer is that the field is absent.
    # Blast radius, measured over 422 sections carrying this heading: 6 carry an
    # `Escalations:` line and 0 of those 6 currently resolve to a tier, so no
    # existing record changes. The guard is prospective, which is the point: the
    # defect it stops was authored twice in one day.
    # A LABELLED `Tier:` line still wins above, because that IS a declaration.
    if ESCALATIONS_LINE.search(body):
        return None
    # 129 of the 380 task files carrying the section have no labelled line, so
    # fall back to the section body, under the same single-tier rule.
    return only_tier(body)


# The commands task-init may add as an escalation (commands/task-init.md,
# Escalation assessment, ADR-0184). The vocabulary is closed, so a name outside it
# is prose, not an escalation: a freeform line such as "Bounded analysis,
# single-slice plan" must not record `single-slice`. The script ships in the
# install payload, where no commands/ tree sits beside it, so the set is fixed
# here rather than read from disk (the D-3 rule test-install-payload.sh enforces);
# test-compute-task-outcome-tier.sh checks it against task-init.
ESCALATION_COMMANDS = {
    "impact-analysis",
    "decision-interview",
    "invariants-and-non-goals",
    "test-strategy",
    "review-hard",
}
# A task-init line may open with a count ("2.") or a verb ("Adding"); neither
# is a command, and skipping them keeps the name in command position.
ESCALATION_LEAD_WORDS = {"add", "adds", "adding", "added"}


def strip_parenthesized(text):
    """Drop every parenthesized span, nested or not. An unclosed '(' drops the
    rest of the text: a reason that wraps past what was read is still a reason,
    never a command list."""
    out = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth:
                depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def read_escalations(task_state_text):
    """The fired escalation commands from the `Escalations:` line of
    '## Recommended pipeline' (ADR-0184, ADR-0207), as a list in written order.

    [] for `Escalations: none`. None when the section or the line is absent,
    when the line is still the unfilled template menu, or when it names neither
    `none` nor any command (the degradation rule: unreadable is null, never a
    guess). Command names only; the parenthesized reasons are dropped.

    A wrapped line is read with its continuation lines (indented, or unbroken
    prose after a line that is not a list item), up to the next list item,
    blank line, heading, or header comment. Only the first word of each clause
    counts as a command, so prose that names a command it did NOT add (`would
    normally add impact-analysis`) does not read as a fired escalation."""
    try:
        lines = task_state_text.splitlines()
        section = extract_section(lines, "## Recommended pipeline")
        if section is None:
            return None
        start = None
        for i, line in enumerate(section):
            if ESCALATIONS_LINE.match(line):
                start = i
                break
        if start is None:
            return None
        parts = [section[start].split(":", 1)[1]]
        for line in section[start + 1:]:
            s = line.strip()
            if (not s or s.startswith("#") or s.startswith("<!--")
                    or re.match(r"^[-*]\s", s)):
                break
            parts.append(s)
        value = " ".join(p.strip() for p in parts).strip()
        plain = re.sub(r"[`*_]", "", value).strip()
        if not plain or plain.startswith("["):
            return None  # empty, or the unfilled template menu
        if re.match(r"^none\b", plain, re.IGNORECASE):
            return []
        fired = []
        for clause in re.split(r"[,;.:]|\s+(?:and|plus)\s+", strip_parenthesized(plain)):
            words = clause.split()
            while words and (words[0].isdigit() or words[0].lower() in ESCALATION_LEAD_WORDS):
                words = words[1:]
            if not words:
                continue
            name = words[0].lower()
            ok = name in ESCALATION_COMMANDS
            if ok and name not in fired:
                fired.append(name)
        return fired if fired else None
    except Exception:
        return None


def usage_from_json(path):
    """The neutral adapter: a JSON object of model id to integer output tokens,
    written by any harness. Anything else is unreadable, so None."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(obj, dict) or not obj:
        return None
    out = {}
    for model, tokens in obj.items():
        if not isinstance(model, str) or isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
            return None
        out[model] = tokens
    return out


def transcript_files(path):
    """A transcript file plus the session directory beside it (where Claude Code
    keeps subagent and workflow transcripts), or every *.jsonl under a directory."""
    files = []
    if os.path.isfile(path):
        files.append(path)
        stem = path[:-len(".jsonl")] if path.endswith(".jsonl") else None
        roots = [stem] if stem and os.path.isdir(stem) else []
    elif os.path.isdir(path):
        roots = [path]
    else:
        return files
    for root in roots:
        for dirpath, _dirs, names in os.walk(root):
            for name in sorted(names):
                if name.endswith(".jsonl"):
                    files.append(os.path.join(dirpath, name))
    return files


TASK_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_[A-Za-z0-9][A-Za-z0-9_-]*$")
AGENT_FILE_RE = re.compile(r"^agent-([A-Za-z0-9]+)\.jsonl$")


def task_write_window(folder):
    """(first, last) wos:write ts in a task folder's TASK_STATE.md, or None.
    Another task's file is read with undecodable bytes replaced, so one damaged
    sibling can never fail this task's outcome line."""
    try:
        with open(os.path.join(folder, "TASK_STATE.md"), "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return None
    stamps = [ts for _, ts in parse_task_state_headers(text)]
    return (min(stamps), max(stamps)) if stamps else None


def concurrent_tasks(project_root, task, start_dt, end_dt):
    """The other task folders, in any project of the same projects/ tree, whose
    own wos:write window overlaps [start_dt, end_dt]. A folder under active/ is
    still running, so its window stays open at the end. A folder with no headers
    has no window and is left out: nothing says when it ran."""
    found = set()
    if not project_root or start_dt is None or end_dt is None:
        return found
    projects_dir = os.path.dirname(project_root)
    try:
        projects = sorted(os.listdir(projects_dir))
    except OSError:
        return found
    for project in projects:
        for lifecycle in ("active", "archive", "done"):
            parent = os.path.join(projects_dir, project, lifecycle)
            try:
                names = os.listdir(parent)
            except OSError:
                continue
            for name in names:
                if name == task or not TASK_DIR_RE.match(name):
                    continue
                window = task_write_window(os.path.join(parent, name))
                if window is None or window[0] > end_dt:
                    continue
                if lifecycle == "active" or window[1] >= start_dt:
                    found.add(name)
    return found


def names_in(text, names):
    """The task folder names that occur in text as whole names: a match must not
    touch a letter, digit, underscore or hyphen on either side, nor be followed by
    a dot and a letter or digit, so one task's name never matches inside a longer
    one."""
    hits = set()
    for name in names:
        i = text.find(name)
        while i != -1:
            before = text[i - 1] if i > 0 else " "
            j = i + len(name)
            after = text[j] if j < len(text) else " "
            longer = after.isalnum() or after in "_-" or (
                after == "." and j + 1 < len(text) and text[j + 1].isalnum())
            if not (before.isalnum() or before in "_-") and not longer:
                hits.add(name)
                break
            i = text.find(name, i + 1)
    return hits


def input_strings(value):
    """Every string inside a tool call's input, walked through dicts and lists,
    so a name is matched against the raw text rather than its JSON escaping (in
    `json.dumps`, a name after a newline follows the letter n)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from input_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from input_strings(item)


def session_root_of(fpath):
    """The session transcript a sub-agent file belongs to: Claude Code keeps
    <session>.jsonl beside a <session>/ directory that holds subagents/."""
    d = os.path.dirname(fpath)
    while d and d != os.path.dirname(d):
        if os.path.isfile(d + ".jsonl"):
            return d + ".jsonl"
        d = os.path.dirname(d)
    return None


def agent_node(fpath):
    """(node key, parent key or None) for one transcript file. A session file is
    a root. A sub-agent file agent-<id>.jsonl names its dispatcher in the sibling
    agent-<id>.meta.json as parentAgentId; without one its parent is the session."""
    m = AGENT_FILE_RE.match(os.path.basename(fpath))
    if not m:
        return fpath, None
    root = session_root_of(fpath)
    parent_id = None
    try:
        with open(fpath[:-len(".jsonl")] + ".meta.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        if isinstance(meta, dict) and isinstance(meta.get("parentAgentId"), str):
            parent_id = meta["parentAgentId"] or None
    except (OSError, ValueError):
        pass
    parent = ("agent", root, parent_id) if parent_id else root
    return ("agent", root, m.group(1)), parent


def scan_transcript(fpath, start_dt, end_dt, wanted):
    """One transcript file: the wanted task names its tool calls carry inside
    the window, and per message that STARTED inside the window [model, largest
    output count, final]. A message is final when one of its lines has a
    stop_reason; only that line holds the whole count. A message's later lines
    count even past the close, so a response cut by the boundary is not read as
    unfinished. Reads names, model ids and integers, never keeps text."""
    named = set()
    messages = {}
    started = {}
    try:
        fh = open(fpath, "r", encoding="utf-8", errors="replace")
    except OSError:
        return None
    with fh:
        for n, line in enumerate(fh):
            if '"assistant"' not in line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if not isinstance(obj, dict) or obj.get("type") != "assistant":
                continue
            ts = parse_iso8601(obj.get("timestamp"))
            if ts is None:
                continue
            msg = obj.get("message")
            if not isinstance(msg, dict):
                continue
            inside = start_dt <= ts <= end_dt
            content = msg.get("content")
            if inside and isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        for text in input_strings(block.get("input")):
                            named |= names_in(text, wanted)
            model = msg.get("model")
            usage = msg.get("usage")
            tokens = usage.get("output_tokens") if isinstance(usage, dict) else None
            if not isinstance(model, str) or isinstance(tokens, bool) or not isinstance(tokens, int):
                continue
            key = msg.get("id") or ("line", fpath, n)
            if key not in started or ts < started[key]:
                started[key] = ts
            entry = messages.setdefault(key, [model, 0, False])
            entry[1] = max(entry[1], tokens)
            entry[2] = entry[2] or bool(msg.get("stop_reason"))
    kept = {k: v for k, v in messages.items() if start_dt <= started[k] <= end_dt}
    return named, kept


def usage_from_claude_code(path, start_dt, end_dt, task=None, project_root=None):
    """The Claude Code adapter (ADR-0238). Returns (totals, detail): totals is
    {model: output tokens} or None, and detail is the scope of the count or,
    when totals is None, the reason.

    Attribution, per transcript file (one file is one agent: the session or one
    sub-agent). An agent belongs to the task when its tool calls inside the
    window name the task's folder anywhere in their inputs (a path, the
    task/<name> branch, a mention) and name no concurrent task, meaning another
    task folder in any project of the same projects/ directory whose write
    window overlaps this one (an active/ folder's window stays open). An agent
    whose tool calls name no task takes the attribution of the agent that
    dispatched it (agent-<id>.meta.json parentAgentId, else the session). An
    agent that names this task and a concurrent one is ambiguous and is not
    counted.

    Signals measured on 2026-09-28 against two tasks that ran at once as
    sub-agents of one session, and not used: the line's cwd (one task's agent
    wrote the main checkout path on 151 of 157 lines, the same path its parent
    wrote) and gitBranch (the launch branch, `main`, on every line).

    Counting. Each message id counts once, at the largest output count any of its
    lines carries. Every counted message must be final, meaning one of its lines
    has a stop_reason. Sub-agent transcripts written by Claude Code 2.1.280 and
    later keep only a streaming snapshot for most messages (measured: 1150 final
    of 10679 such messages, against 2203 of 2256 before 2.1.280), so an
    attributed message with no final line makes the whole count null, with the
    reason, rather than a floor that reads like a total."""
    if start_dt is None or end_dt is None:
        return None, "claude-code: no task window (no wos:write header in TASK_STATE.md)"
    if not task:
        return None, "claude-code: no task name to attribute by"
    files = transcript_files(path)
    if not files:
        return None, "claude-code: no transcript at the given path"
    concurrent = concurrent_tasks(project_root, task, start_dt, end_dt)
    wanted = set(concurrent) | {task}
    nodes = {}
    for fpath in files:
        scanned = scan_transcript(fpath, start_dt, end_dt, wanted)
        if scanned is None:
            continue
        key, parent = agent_node(fpath)
        nodes[key] = {"parent": parent, "named": scanned[0], "messages": scanned[1]}

    def verdict(key, seen):
        node = nodes.get(key)
        if node is None or key in seen:
            return "none"
        named = node["named"]
        if task in named:
            return "ambiguous" if named & concurrent else "task"
        if named & concurrent:
            return "other"
        if node["parent"] is None:
            return "none"
        return verdict(node["parent"], seen | {key})

    tally = {"task": 0, "ambiguous": 0, "other": 0, "none": 0}
    counted = {}
    for key, node in nodes.items():
        if not node["messages"]:
            continue
        v = verdict(key, frozenset())
        tally[v] += 1
        if v == "task":
            for mid, (model, tokens, final) in node["messages"].items():
                prior = counted.get(mid)
                if prior is None:
                    counted[mid] = [model, tokens, final]
                else:
                    prior[1] = max(prior[1], tokens)
                    prior[2] = prior[2] or final
    agents_in_window = sum(tally.values())
    if agents_in_window == 0:
        return None, "claude-code: no assistant line inside the task window"
    excluded = "%d excluded: %d ambiguous, %d of a concurrent task, %d unattributed" % (
        tally["ambiguous"] + tally["other"] + tally["none"], tally["ambiguous"], tally["other"], tally["none"])
    if not counted:
        return None, "claude-code: no transcript in the window is attributed to the task; " + excluded
    not_final = sum(1 for _, _, final in counted.values() if not final)
    if not_final:
        return None, ("claude-code: %d of %d attributed messages have no final count (a sub-agent "
                      "transcript kept only a streaming snapshot); %d transcripts attributed, %s"
                      % (not_final, len(counted), tally["task"], excluded))
    totals = {}
    for model, tokens, _ in counted.values():
        totals[model] = totals.get(model, 0) + tokens
    return totals, "claude-code; time window %s to %s; attributed by task name: %d transcripts counted, %s" % (
        format_iso_ms(start_dt), format_iso_ms(end_dt), tally["task"], excluded)


def read_usage(usage_source, start_dt, end_dt, task=None, project_root=None):
    """(output_tokens_by_model, output_tokens_source, output_tokens_null_reason).
    Tool-agnostic at the contract: the adapter name picks a reader. Absent,
    unreadable or unattributable data is a null count plus a reason, never an
    estimate."""
    if not usage_source:
        return None, None, "no usage source passed"
    if ":" not in usage_source:
        return None, None, "usage source is not <adapter>:<path>"
    adapter, path = usage_source.split(":", 1)
    try:
        if adapter == "json":
            got = usage_from_json(path)
            if got is None:
                return None, None, "json: the file is missing or is not a {model: non-negative integer} object"
            return got, "json", None
        if adapter == "claude-code":
            got, detail = usage_from_claude_code(path, start_dt, end_dt, task, project_root)
            if got is None:
                return None, None, detail
            return got, detail, None
    except Exception:
        return None, None, "%s: the reader failed" % adapter
    return None, None, "unknown adapter: %s" % adapter


def build_outcome_record(task_folder, merge_status, evidence, close_ts_arg, usage_source=None):
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
    usage_start = earliest(pool, INIT_OWNERS) if pool else None
    if usage_start is None and pool:
        usage_start = min(ts for _, ts in pool)
    tokens_by_model, tokens_source, tokens_reason = read_usage(
        usage_source, usage_start, close_dt, task, project_root)

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
        "tier": read_pipeline_tier(task_state_text),
        "escalations": read_escalations(task_state_text),
        "output_tokens_by_model": tokens_by_model,
        "output_tokens_source": tokens_source,
        "output_tokens_null_reason": tokens_reason,
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


VALID_EXITS = ("RESOLVED", "NO_PROGRESS", "BUDGET", "ESCALATED", "ENVIRONMENT")


def build_plan_review_record(task_slug, project, exit_label, rubric, escalated_on):
    """One `plan_review` line, appended by approve-plan at every approval (ADR-0208).

    This exists because D-1 of the 2026-09-16 plan-approval task ACCEPTED the
    measured 39-percent plan-rejection rate and replaced the control rather than
    disputing the number, which moves the burden of proof onto the replacement.
    A replacement that leaves no trail cannot discharge it. The record carries
    what was decided and on what, never how certain anything sounded: a
    confidence value here would be the exact shape ADR-0109 D-2 forbids.
    """
    if exit_label not in VALID_EXITS:
        raise ValueError(
            "exit must be one of %s (the five in commands/_shared/"
            "grounded-residue-termination.md), got %r" % (", ".join(VALID_EXITS), exit_label)
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "event": "plan_review",
        "ts": now_iso_ms(),
        "project": project,
        "task": task_slug,
        "exit": exit_label,
        "rubric": rubric,
        # Bound to the exit that produces it. The schema promises non-null only on
        # ESCALATED, and a reader sampling this trail filters on that field first: a
        # residue attached to an exit that continued the chain would read as a stop
        # that never happened. Found 2026-09-16 by test-plan-review-record.sh check 4.
        "escalated_on": escalated_on if (escalated_on and exit_label == "ESCALATED") else None,
        "source": "compute-task-outcome.py",
        "run_id": generate_run_id(),
    }


def build_review_coverage_record(task_slug, project, units_declared, units_checked,
                                 criteria, residual, findings):
    """One `review_coverage` line, appended by review-hard at every verdict (B22).

    WHY THIS EXISTS. A verdict that does not say what it looked at makes a claim
    about the COMPLEMENT of what it checked, and nothing grounds that. An unbounded
    claim is falsifiable by one more look, forever, which is how "are you sure?"
    became an unbounded number of rounds: each one found something real, so no round
    was ever trustworthy. Measured 2026-09-17 against this session and against the
    literature: re-asking is repeated sampling, and coverage from repeated sampling
    keeps rising, so the loop has no natural end. What ends it is a declared scope
    plus a named residual, because then a challenge has to NAME a unit or a criterion
    rather than just ask again.

    The rule is the one `commands/_shared/deliverable-reconcile.md` already applies
    to the deliverable ledger, moved to a second object: a de-scope is allowed,
    silence is not. So `residual` is REQUIRED and may not be empty. A pass that
    reached everything writes why that is credible; it does not write nothing.

    No confidence field, deliberately, per ADR-0109 D-2. Coverage is not certainty:
    it says what was looked at, never how sure the looking felt.
    """
    if units_declared < 0 or units_checked < 0:
        raise ValueError("unit counts must not be negative")
    if units_checked > units_declared:
        raise ValueError(
            "units_checked (%d) exceeds units_declared (%d): a pass cannot check more "
            "units than it declared, and a scope that grew mid-pass is a scope that was "
            "never declared" % (units_checked, units_declared)
        )
    if not (residual or "").strip():
        raise ValueError(
            "residual is required and may not be empty. A de-scope is allowed; silence "
            "is not. Name what was not checked and why, or state why nothing was left."
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "event": "review_coverage",
        "ts": now_iso_ms(),
        "project": project,
        "task": task_slug,
        "units_declared": units_declared,
        "units_checked": units_checked,
        "criteria": criteria,
        "residual": residual.strip(),
        "findings": findings,
        "source": SOURCE_NAME,
        "run_id": generate_run_id(),
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
        "--plan-review",
        default=None,
        metavar="TASK_SLUG",
        help="Switch to plan-review mode; the task whose plan was just reviewed (ADR-0208).",
    )
    parser.add_argument("--exit", dest="exit_label", default=None, help="The exit the review took (plan-review mode).")
    parser.add_argument("--rubric", default=None, help="The locked rubric the review ran against (plan-review mode).")
    parser.add_argument(
        "--review-coverage",
        dest="review_coverage",
        default=None,
        metavar="TASK_SLUG",
        help="Switch to review-coverage mode; the task whose verdict declared this scope (B22).",
    )
    parser.add_argument("--units-declared", type=int, default=None, help="Units in the declared scan set.")
    parser.add_argument("--units-checked", type=int, default=None, help="Units actually read.")
    parser.add_argument("--criteria", default=None, help="The criterion set applied, named.")
    parser.add_argument("--residual", default=None, help="What was NOT checked and why. Required; empty is refused.")
    parser.add_argument("--findings", type=int, default=0, help="How many findings the pass produced.")
    parser.add_argument("--escalated-on", default=None, help="What the review could not ground; only on ESCALATED.")
    parser.add_argument(
        "--usage-source",
        dest="usage_source",
        default=None,
        metavar="ADAPTER:PATH",
        help="Where to read output tokens per model (outcome mode): json:<file> or "
             "claude-code:<transcript file or directory>. Absent or unreadable records null.",
    )
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

    if args.plan_review is not None:
        if not args.project or not args.exit_label or not args.rubric:
            parser.error("--plan-review mode requires --project, --exit and --rubric")
        try:
            record = build_plan_review_record(
                args.plan_review, args.project, args.exit_label, args.rubric, args.escalated_on
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(record))
        return 0

    if args.review_coverage is not None:
        if (not args.project or args.units_declared is None
                or args.units_checked is None or not args.criteria):
            parser.error(
                "--review-coverage mode requires --project, --units-declared, "
                "--units-checked and --criteria"
            )
        try:
            record = build_review_coverage_record(
                args.review_coverage, args.project, args.units_declared,
                args.units_checked, args.criteria, args.residual, args.findings,
            )
        except ValueError as exc:
            # NOT the degradation rule. Every other mode here degrades a bad input to
            # a null field and exits 0, because a missing cycle-time is better absent
            # than absent-and-fatal. This mode refuses, because the whole point of the
            # record is that a verdict with no stated residual does not get written.
            # Degrading it to a null residual would reproduce the silence it exists to
            # forbid, in the ledger meant to prove the silence did not happen.
            parser.error(str(exc))
        print(json.dumps(record))
        return 0

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
    # A folder that does not exist is a wrong path, not missing data. Degrading it printed a
    # well-formed line with project null and exit 0 (measured 2026-09-22), which a caller
    # appends as a real outcome. The degradation rule below covers a folder that EXISTS and
    # lacks a field; this refuses the case where there is nothing to read at all.
    if not os.path.isdir(args.task_folder):
        parser.error(f"task folder not found: {args.task_folder}")

    try:
        record = build_outcome_record(args.task_folder, args.merge_status, args.evidence, args.close_ts,
                                      args.usage_source)
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
            "tier": None,
            "escalations": None,
            "output_tokens_by_model": None,
            "output_tokens_source": None,
            "output_tokens_null_reason": "the helper failed before reading usage",
            "source": SOURCE_NAME,
            "run_id": generate_run_id(),
        }
    print(json.dumps(record))
    return 0


if __name__ == "__main__":
    sys.exit(main())
