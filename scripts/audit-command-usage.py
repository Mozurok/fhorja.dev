#!/usr/bin/env python3
"""audit-command-usage.py - Per-command usage audit (one-pass, optimized)

Counts mentions of each command in:
  - ~/.claude/projects/<project>/*.jsonl (last LOOKBACK_DAYS days)
  - git log of Fhorja repo (commit messages)
  - projects/*/active|archive/*/TASK_STATE.md mentions

Output: CSV at _internal/command-usage-audit-2026-06.csv
Per Epic C.1 of Fhorja improvement plan 2026-06-03.

Usage:
  python3 scripts/audit-command-usage.py                       # default 60-day lookback
  python3 scripts/audit-command-usage.py /tmp/audit.csv 90     # custom output + lookback
"""

import os
import re
import sys
import time
import subprocess
import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else str(REPO_ROOT / "_internal" / "command-usage-audit-2026-06.csv")
LOOKBACK_DAYS = int(sys.argv[2]) if len(sys.argv) > 2 else 60
PROJECTS_DIR = Path.home() / ".claude" / "projects"

NOW = time.time()
CUTOFF = NOW - (LOOKBACK_DAYS * 86400)

commands = sorted([p.stem for p in (REPO_ROOT / "commands").glob("*.md")])
print(f"Auditing {len(commands)} commands, last {LOOKBACK_DAYS} days, one-pass scan.", file=sys.stderr)

cmd_set = set(commands)
# One regex matches any command name as: /<cmd>, @commands/<cmd>.md, command-name>/<cmd><
alt = "|".join(re.escape(c) for c in commands)
pat = re.compile(
    rf"(?:^|[/\"<])((?:{alt}))(?:[/\"<>\s\.]|$)"
)

transcript_count = {c: 0 for c in commands}
git_count = {c: 0 for c in commands}
ts_count = {c: 0 for c in commands}

# Phase 1: transcripts (file-presence count, not occurrence count)
if PROJECTS_DIR.is_dir():
    print("Scanning transcripts...", file=sys.stderr)
    jsonl_files = []
    for jsonl in PROJECTS_DIR.rglob("*.jsonl"):
        try:
            if jsonl.stat().st_mtime >= CUTOFF:
                jsonl_files.append(jsonl)
        except OSError:
            continue
    print(f"  {len(jsonl_files)} JSONL files in window", file=sys.stderr)

    for jsonl in jsonl_files:
        try:
            text = jsonl.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        cmds_seen = set()
        for m in pat.finditer(text):
            name = m.group(1)
            if name in cmd_set:
                cmds_seen.add(name)
        for c in cmds_seen:
            transcript_count[c] += 1

# Phase 2: git log
print("Scanning git log...", file=sys.stderr)
try:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "log", "--oneline", "--all",
         f"--since={LOOKBACK_DAYS}.days.ago"],
        capture_output=True, text=True, timeout=30
    )
    git_text = proc.stdout
    for c in commands:
        git_count[c] = len(re.findall(rf"\b{re.escape(c)}\b", git_text))
except Exception as e:
    print(f"  git log error: {e}", file=sys.stderr)

# Phase 3: TASK_STATE.md presence count
print("Scanning TASK_STATE files...", file=sys.stderr)
projects_dir = REPO_ROOT / "projects"
if projects_dir.is_dir():
    ts_files = list(projects_dir.rglob("TASK_STATE.md"))
    print(f"  {len(ts_files)} TASK_STATE.md files", file=sys.stderr)
    for ts in ts_files:
        try:
            text = ts.read_text(errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        cmds_seen = set()
        for c in commands:
            if re.search(rf"\b{re.escape(c)}\b", text):
                cmds_seen.add(c)
        for c in cmds_seen:
            ts_count[c] += 1

# Phase 4: emit CSV
with open(OUTPUT, "w") as f:
    w = csv.writer(f)
    w.writerow(["command", "transcripts_mentions", "git_log_mentions", "task_state_mentions", "total", "classification_hint"])
    for c in commands:
        t = transcript_count[c]
        g = git_count[c]
        ts = ts_count[c]
        total = t + g + ts
        if total >= 10:
            hint = "ACTIVE"
        elif total >= 3:
            hint = "DORMANT"
        elif total == 0:
            hint = "NEVER_USED"
        else:
            hint = "LOW_USE"
        w.writerow([c, t, g, ts, total, hint])

# Summary to stderr
print("", file=sys.stderr)
print(f"Done: scanned {len(commands)} commands.", file=sys.stderr)
print(f"  output: {OUTPUT}", file=sys.stderr)
print("", file=sys.stderr)

# Re-read for summary
import collections
rows = []
with open(OUTPUT) as f:
    r = csv.reader(f)
    headers = next(r)
    for row in r:
        rows.append(row)

hints = collections.Counter(row[5] for row in rows)
print("Classification distribution:", file=sys.stderr)
for h, n in hints.most_common():
    print(f"  {h:<15} {n}", file=sys.stderr)

print("", file=sys.stderr)
print("Top 10 by total mentions:", file=sys.stderr)
sorted_rows = sorted(rows, key=lambda r: -int(r[4]))
for row in sorted_rows[:10]:
    print(f"  {row[0]:<35} total={row[4]:<4} transcripts={row[1]:<4} git={row[2]:<4} task_state={row[3]}", file=sys.stderr)

print("", file=sys.stderr)
print("NEVER_USED commands (zero mentions):", file=sys.stderr)
for row in rows:
    if int(row[4]) == 0:
        print(f"  - {row[0]}", file=sys.stderr)
