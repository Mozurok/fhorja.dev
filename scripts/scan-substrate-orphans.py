#!/usr/bin/env python3
"""Scan substrate files for orphan bullets between H2 sections.

Detects the substrate-bullet-orphan failure mode (wos/bug-classes/substrate-bullet-orphan.md):
a bullet line that sits BETWEEN two H2 section headers without being inside either section's
content area. K.5 + K.4 audits pass (per-line shape + header drift) but substrate's section
structure is structurally broken.

Usage (two forms):
  Directory mode (repo-consistency-sweep Pre-flight): scan the canonical substrate files in a
  task folder.
    python3 scripts/scan-substrate-orphans.py <task-folder>

  File mode (ADR-0038 Rule 3 fleet apply-step gate): scan exactly the named output files the
  apply step just wrote.
    python3 scripts/scan-substrate-orphans.py <file-1> [<file-2> ...]

A single argument that is an existing directory selects directory mode; anything else is treated
as one or more file paths (file mode). This dual signature lets the fleet commands gate on the
specific files they touched (EXTERNAL_RESEARCH.md, FEATURE_LIBRARIES.md, SCREEN_MAP.md, etc.)
while the sweep keeps scanning a whole task folder.

Exit code: 0 if zero orphans; 1 if any orphans found; 2 on usage error.

Per bug-class spec: detection pattern is bullet line (- or *) appearing AFTER an H2's content
closes OR after a K.2 transaction header BEFORE the next H2 line.
"""
import sys
from pathlib import Path

SUBSTRATE_FILES = [
    "TASK_STATE.md",
    "IMPLEMENTATION_PLAN.md",
    "DECISIONS.md",
    "SOURCE_OF_TRUTH.md",
]


def scan_file(path: Path):
    """Return list of (line_num, line_text) for orphan bullets.

    State machine: walk lines; toggle in_section=True at H2 lines; orphan = bullet
    encountered when in_section=False.
    """
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    orphans = []
    in_section = False
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if stripped.startswith("## "):
            in_section = True
            continue
        if stripped.startswith("# "):
            in_section = False
            continue
        if line.startswith("<!-- wos:write owner="):
            in_section = False
            continue
        if not in_section and (stripped.startswith("- ") or stripped.startswith("* ")):
            orphans.append((i, line))
    return orphans


def scan_targets(paths, warn_missing):
    """Scan each path, print per-file orphan reports, return total orphan count.

    warn_missing: in file mode a named file that is absent is surfaced as a stderr warning
    (the caller explicitly asked for it); in directory mode a missing canonical substrate file
    is skipped silently (not every task has every substrate file yet).
    """
    total = 0
    for path in paths:
        if not path.exists():
            if warn_missing:
                print(f"WARNING: file not found, skipped: {path}", file=sys.stderr)
            continue
        orphans = scan_file(path)
        if orphans:
            print(f"\n=== {path.name} ({len(orphans)} orphan bullet(s)) ===")
            for line_num, text in orphans:
                preview = text[:120] + ("..." if len(text) > 120 else "")
                print(f"  line {line_num}: {preview}")
            total += len(orphans)
    return total


def main():
    if len(sys.argv) < 2:
        print("Usage: scan-substrate-orphans.py <task-folder> | <file> [<file> ...]", file=sys.stderr)
        sys.exit(2)

    args = sys.argv[1:]
    if len(args) == 1 and Path(args[0]).is_dir():
        # Directory mode: scan the canonical substrate files inside the task folder.
        task_dir = Path(args[0])
        targets = [task_dir / fname for fname in SUBSTRATE_FILES]
        label = str(task_dir)
        warn_missing = False
    else:
        # File mode: scan exactly the named files (the fleet apply-step gate form).
        targets = [Path(a) for a in args]
        label = ", ".join(args)
        warn_missing = True

    total_orphans = scan_targets(targets, warn_missing)

    print()
    print(f"target: {label}")
    print(f"substrate_bullet_orphan_count: {total_orphans}")
    if total_orphans == 0:
        print("OK")
        sys.exit(0)
    print(f"\nDetected {total_orphans} orphan bullet(s). See wos/bug-classes/substrate-bullet-orphan.md for the fix protocol.")
    sys.exit(1)


if __name__ == "__main__":
    main()
