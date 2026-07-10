#!/usr/bin/env python3
"""S3: Remove boilerplate sections from all 49 command files.

Sections removed:
  - "Use when:" block
  - "Do not use when:" block
  - "Primary editor mode:" block
  - "Why this mode:" block
  - "Evidence priority:" block
  - "Task repository files to read:" block

Usage:
  python3 scripts/s3-thin-skills.py --dry-run   # report only
  python3 scripts/s3-thin-skills.py --apply      # modify files
"""

import os, sys, re

CMD_DIR = "commands"
SECTIONS_TO_REMOVE = [
    "Use when:",
    "Do not use when:",
    "Primary editor mode:",
    "Why this mode:",
    "Evidence priority:",
    "Task repository files to read:",
]

KNOWN_SECTION_LABELS = [
    "Use when:",
    "Do not use when:",
    "Primary editor mode:",
    "Why this mode:",
    "Required inputs:",
    "Task repository files to read:",
    "Task repository files to update:",
    "Task repository files to create or update",
    "Task repository files to create:",
    "Evidence priority:",
    "Operating rules:",
    "Required output:",
    "Files to generate:",
    "Task naming rules:",
    "Project naming rules:",
    "Mandatory files to create:",
    "Optional files must NOT",
    "Task repository structure to use:",
    "Mandatory context bootstrap",
]

def is_section_start(line):
    stripped = line.strip()
    if stripped.startswith("#"):
        return True
    for label in KNOWN_SECTION_LABELS:
        if stripped.startswith(label):
            return True
    if stripped.startswith("<!-- "):
        return True
    return False

def find_section_range(lines, start_idx):
    """Given the start of a section (the label line), find the end (exclusive).
    A section ends at the next section label or markdown header."""
    end = start_idx + 1
    while end < len(lines):
        line = lines[end]
        stripped = line.strip()
        if stripped == "":
            # blank line - check if next non-blank is a new section
            peek = end + 1
            while peek < len(lines) and lines[peek].strip() == "":
                peek += 1
            if peek >= len(lines):
                end = peek
                break
            if is_section_start(lines[peek]):
                # include trailing blank lines in the removed range
                end = peek
                break
            else:
                end += 1
        elif is_section_start(line) and end > start_idx:
            break
        else:
            end += 1
    return end

def process_file(filepath, apply=False):
    with open(filepath) as f:
        content = f.read()

    lines = content.split("\n")
    ranges_to_remove = []
    sections_found = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        for section in SECTIONS_TO_REMOVE:
            if stripped.startswith(section) or stripped == section.rstrip(":"):
                end = find_section_range(lines, i)
                ranges_to_remove.append((i, end, section))
                sections_found.append(section)
                break

    if not ranges_to_remove:
        return None, 0

    # Sort ranges and check for overlaps
    ranges_to_remove.sort(key=lambda x: x[0])

    # Build new lines excluding removed ranges
    remove_set = set()
    for start, end, _ in ranges_to_remove:
        for j in range(start, end):
            remove_set.add(j)

    new_lines = [line for i, line in enumerate(lines) if i not in remove_set]

    # Clean up multiple consecutive blank lines (max 1)
    cleaned = []
    prev_blank = False
    for line in new_lines:
        is_blank = line.strip() == ""
        if is_blank and prev_blank:
            continue
        cleaned.append(line)
        prev_blank = is_blank

    new_content = "\n".join(cleaned)

    # Ensure file ends with single newline
    new_content = new_content.rstrip("\n") + "\n"

    old_lines = len(lines)
    new_line_count = len(cleaned)
    removed = old_lines - new_line_count

    if apply:
        with open(filepath, "w") as f:
            f.write(new_content)

    return sections_found, removed

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
    apply = mode == "--apply"

    files = sorted([f for f in os.listdir(CMD_DIR) if f.endswith(".md") and not f.startswith("_")])

    total_removed = 0
    total_sections = 0

    for f in files:
        path = os.path.join(CMD_DIR, f)
        sections, removed = process_file(path, apply=apply)
        if sections:
            total_sections += len(sections)
            total_removed += removed
            action = "APPLIED" if apply else "DRY-RUN"
            print(f"  [{action}] {f}: removed {len(sections)} sections ({removed} lines)")
            for s in sections:
                print(f"    - {s}")

    print(f"\n{'APPLIED' if apply else 'DRY-RUN'} Summary:")
    print(f"  Files processed: {len(files)}")
    print(f"  Sections removed: {total_sections}")
    print(f"  Lines removed: {total_removed}")
    print(f"  Avg lines removed per file: {total_removed/len(files):.1f}")

if __name__ == "__main__":
    main()
