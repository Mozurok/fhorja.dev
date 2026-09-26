#!/usr/bin/env python3
"""Every value under `metadata:` in a generated SKILL.md is a string.

The open Agent Skills spec fixes metadata as "a map from string keys to string values". The
generated skills violated that in five shapes at once (block sequence, boolean, integer, nested
map, sequence of maps), on 98 of 98 files, and CI reported green the whole time: the pinned
skills-ref validator checks the top-level fields (name, description, compatibility) and never the
TYPE of a metadata value. A client implementing the spec strictly rejects the whole install, not
one skill, which is why this is FAIL-tier and not advisory. A checker either can fail the build or
it leaves the lint.

Conforming: a double-quoted scalar, or a literal block scalar (`|`, `|-`, `>`, `>-`), which is
already a string by the spec and is what carries the worker schemas.

Exit 0 all conforming, 1 any non-conforming, 2 usage error.
"""

import glob
import os
import re
import sys


def check_file(path):
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    if not lines or lines[0] != "---":
        return [f"{path}: no frontmatter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return [f"{path}: unterminated frontmatter"]

    fails = []
    in_meta = False
    i = 1
    while i < end:
        line = lines[i]
        if re.match(r"^\S", line):
            in_meta = line.startswith("metadata:")
            i += 1
            continue
        if not in_meta:
            i += 1
            continue
        m = re.match(r"^(\s+)([A-Za-z0-9_.-]+):(.*)$", line)
        if not m:
            i += 1
            continue
        indent, key, rest = m.group(1), m.group(2), m.group(3).strip()
        if rest in ("|", "|-", ">", ">-"):
            i += 1
            while i < end and (lines[i].strip() == "" or len(lines[i]) - len(lines[i].lstrip()) > len(indent)):
                i += 1
            continue
        if rest.startswith('"') and rest.endswith('"') and len(rest) >= 2:
            i += 1
            continue
        shape = "block sequence or nested map" if rest == "" else f"unquoted scalar ({rest[:40]})"
        fails.append(f"{path}: metadata.{key} is not a string: {shape}")
        i += 1
    return fails


def main(argv):
    root = argv[0] if argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    files = sorted(glob.glob(os.path.join(root, ".claude", "skills", "*", "SKILL.md")))
    if not files:
        print("Skill-metadata-types: not measured (no generated skills found)")
        return 0
    fails = []
    for f in files:
        fails.extend(check_file(f))
    print(f"Skill-metadata-types: {len(files)} skill(s) scanned, {len(fails)} non-conforming")
    for f in fails:
        print(f"  {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
