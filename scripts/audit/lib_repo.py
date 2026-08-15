#!/usr/bin/env python3
"""lib_repo.py -- shared read-only readers for the baseline audit.

Python stdlib only. No writes. Every helper here answers a question about the
tree as it is on disk; none of them interpret, rank, or recommend.

Consumed by scripts/audit/baseline_audit.py.
"""

import os
import re
import subprocess

LIB_VERSION = "1.0.0"

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


def repo_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", ".."))


ROOT = repo_root()


def rel(path):
    return os.path.relpath(path, ROOT)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def read_lines(path):
    text = read_text(path)
    if text is None:
        return []
    return text.splitlines()


# --------------------------------------------------------------------------
# Command inventory (K.3 dual layout: flat commands/<name>.md and
# folder-shaped commands/<name>/SKILL.md; commands/_shared is not a command)
# --------------------------------------------------------------------------


def command_files():
    """Return sorted [(name, abs_path, shape)] for every canonical command."""
    cmd_dir = os.path.join(ROOT, "commands")
    out = []
    for entry in sorted(os.listdir(cmd_dir)):
        full = os.path.join(cmd_dir, entry)
        if os.path.isfile(full) and entry.endswith(".md"):
            out.append((entry[:-3], full, "flat"))
        elif os.path.isdir(full) and entry != "_shared":
            skill = os.path.join(full, "SKILL.md")
            if os.path.isfile(skill):
                out.append((entry, skill, "folder"))
    return sorted(out, key=lambda r: r[0])


def shared_block_files():
    """Canonical shared blocks: commands/_shared/<name>.md, README excluded."""
    shared_dir = os.path.join(ROOT, "commands", "_shared")
    out = {}
    if not os.path.isdir(shared_dir):
        return out
    for entry in sorted(os.listdir(shared_dir)):
        if not entry.endswith(".md"):
            continue
        name = entry[:-3]
        if name == "README":
            continue
        if not re.fullmatch(r"[a-z-]+", name):
            continue
        out[name] = os.path.join(shared_dir, entry)
    return out


def built_skills():
    """Return sorted [(name, abs_path)] for .claude/skills/<name>/SKILL.md."""
    skills_dir = os.path.join(ROOT, ".claude", "skills")
    out = []
    if not os.path.isdir(skills_dir):
        return out
    for entry in sorted(os.listdir(skills_dir)):
        skill = os.path.join(skills_dir, entry, "SKILL.md")
        if os.path.isfile(skill):
            out.append((entry, skill))
    return out


# --------------------------------------------------------------------------
# Frontmatter (a deliberately small YAML subset: scalars, block scalars,
# inline flow lists, nested one-level mappings, and dash lists)
# --------------------------------------------------------------------------


def split_frontmatter(text):
    """Return (frontmatter_lines, body_lines, body_start_lineno_1based)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], lines, 1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], lines[i + 1:], i + 2
    return [], lines, 1


def _parse_scalar(raw):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [p.strip().strip("'\"") for p in inner.split(",") if p.strip()]
    if raw in ("true", "false"):
        return raw == "true"
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        return raw[1:-1]
    return raw


def parse_frontmatter(fm_lines):
    """Parse the frontmatter subset used by this repository."""
    result = {}
    i = 0
    n = len(fm_lines)
    while i < n:
        line = fm_lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if indent != 0:
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2)
        if rest.strip() in ("|", "|-", ">", ">-"):
            chunk = []
            i += 1
            while i < n and (not fm_lines[i].strip() or fm_lines[i].startswith("  ")):
                chunk.append(fm_lines[i][2:] if fm_lines[i].startswith("  ") else "")
                i += 1
            result[key] = "\n".join(chunk).strip()
            continue
        if rest.strip() == "":
            block = []
            i += 1
            while i < n and (not fm_lines[i].strip() or fm_lines[i].startswith("  ")):
                block.append(fm_lines[i])
                i += 1
            result[key] = _parse_block(block)
            continue
        result[key] = _parse_scalar(rest)
        i += 1
    return result


def _parse_block(block):
    """A nested block is either a dash list or a one-level mapping."""
    stripped = [b for b in block if b.strip()]
    if not stripped:
        return None
    if all(b.lstrip().startswith("- ") for b in stripped):
        return [b.lstrip()[2:].strip().strip("'\"") for b in stripped]
    out = {}
    i = 0
    n = len(block)
    base = min((len(b) - len(b.lstrip())) for b in stripped)
    while i < n:
        line = block[i]
        if not line.strip():
            i += 1
            continue
        indent = len(line) - len(line.lstrip())
        if indent != base:
            i += 1
            continue
        m = re.match(r"^\s*([A-Za-z0-9_.-]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2)
        if rest.strip() == "":
            sub = []
            i += 1
            while i < n and (not block[i].strip() or
                             (len(block[i]) - len(block[i].lstrip())) > base):
                sub.append(block[i])
                i += 1
            out[key] = _parse_block(sub)
            continue
        out[key] = _parse_scalar(rest)
        i += 1
    return out


def command_meta(path):
    """Return a flat dict of the fields the audit needs from one command file."""
    text = read_text(path) or ""
    fm_lines, body_lines, body_start = split_frontmatter(text)
    fm = parse_frontmatter(fm_lines)
    meta = fm.get("metadata") or {}
    if not isinstance(meta, dict):
        meta = {}
    profiles = meta.get("x-wos-profiles") or []
    if isinstance(profiles, str):
        profiles = [profiles]
    return {
        "name": fm.get("name"),
        "description": fm.get("description") or "",
        "has_frontmatter": bool(fm_lines),
        "frontmatter_keys": sorted(fm.keys()),
        "category": meta.get("category"),
        "profiles": list(profiles),
        "tools": meta.get("tools") or [],
        "body_lines": body_lines,
        "body_start_lineno": body_start,
        "raw_text": text,
    }


# --------------------------------------------------------------------------
# Count markers
# --------------------------------------------------------------------------

COUNT_MARKER_RE = re.compile(r"<!-- count:([a-z-]+) -->(\d+)<!-- /count -->")

# Mirrors scripts/lint-commands.sh COUNT_SCAN_FILES and
# scripts/reconcile-counts.sh FILES. Deliberately narrow: frozen snapshots under
# _internal/ and scripts/baseline-*.md carry markers pinned to a past count.
COUNT_SCAN_ROOT_DOCS = [
    "README.md", "WORKFLOW_OPERATING_SYSTEM.md", "WORKFLOW_DEMO.md",
    "CONTRIBUTING.md", "CLAUDE.md", "CHANGELOG.md", "ROADMAP.md",
    "CODE_OF_CONDUCT.md", "SECURITY.md", "COMMAND_PROMPT_STUBS.md",
]
COUNT_SCAN_EXTRA = [
    "docs/FAQ.md", "docs/MIGRATION.md", "docs/adr/README.md", "evals/README.md",
]


def count_scan_files():
    files = [os.path.join(ROOT, f) for f in COUNT_SCAN_ROOT_DOCS]
    wos_dir = os.path.join(ROOT, "wos")
    if os.path.isdir(wos_dir):
        for entry in sorted(os.listdir(wos_dir)):
            if entry.endswith(".md"):
                files.append(os.path.join(wos_dir, entry))
    files += [os.path.join(ROOT, f) for f in COUNT_SCAN_EXTRA]
    return [f for f in files if os.path.isfile(f)]


def disk_count(kind):
    """On-disk value for a count KIND. Mirrors lint-commands.sh disk_count()."""
    cmds = command_files()
    if kind == "commands":
        return len(cmds)
    if kind in ("commands-minimal", "commands-core"):
        want = kind.split("-", 1)[1]
        return sum(1 for _, p, _ in cmds if want in (command_meta(p)["profiles"] or []))
    if kind == "skills":
        return len(built_skills())
    if kind == "command-categories":
        cats = {command_meta(p)["category"] for _, p, _ in cmds}
        cats.discard(None)
        return len(cats)
    if kind == "adrs":
        return len(_glob_numbered(os.path.join(ROOT, "docs", "adr")))
    if kind == "scenarios":
        return len(_glob_numbered(os.path.join(ROOT, "evals", "scenarios")))
    if kind == "wos-topics":
        d = os.path.join(ROOT, "wos")
        return len([f for f in os.listdir(d) if f.endswith(".md")])
    if kind == "bug-templates":
        d = os.path.join(ROOT, "wos", "bug-classes")
        return len([f for f in os.listdir(d)
                    if f.endswith(".md") and "_index" not in f])
    if kind == "bug-categories":
        d = os.path.join(ROOT, "wos", "bug-classes")
        cats = set()
        for f in sorted(os.listdir(d)):
            if not f.endswith(".md"):
                continue
            for line in read_lines(os.path.join(d, f)):
                if line.startswith("category:"):
                    cats.add(line.split(":", 1)[1].strip())
        return len(cats)
    if kind == "anti-patterns":
        return sum(1 for line in read_lines(os.path.join(ROOT, "wos", "anti-patterns.md"))
                   if line.startswith("- "))
    if kind == "entry-points":
        return sum(1 for line in read_lines(os.path.join(ROOT, "wos", "entry-points.md"))
                   if line.startswith("## "))
    if kind == "fleet-commands":
        return len([n for n, _, shape in cmds if n.endswith("-fleet") and shape == "flat"])
    if kind == "personas":
        return len([n for n, _, shape in cmds if shape == "folder"])
    return None


def _glob_numbered(directory):
    if not os.path.isdir(directory):
        return []
    return sorted(f for f in os.listdir(directory)
                  if f.endswith(".md") and f[:1].isdigit())


# --------------------------------------------------------------------------
# Git
# --------------------------------------------------------------------------


def git(*args):
    try:
        proc = subprocess.run(
            ["git"] + list(args), cwd=ROOT, capture_output=True, text=True, check=False)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def git_available():
    return git("rev-parse", "--git-dir") is not None
