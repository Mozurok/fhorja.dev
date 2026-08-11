#!/usr/bin/env python3
"""Freeze the compound proper nouns currently in the public-facing tree.

WHY. `check-mirror-codenames.sh` knows a LIST. It is excellent at the names on it and blind to
every other one, so a new private name is invisible until somebody remembers to register it,
and "somebody remembers" is exactly what failed the four times this recurred. On 2026-08-10 a
private engagement name sat in two `wos/` topics while the guard reported the tree clean.

Detecting "is this name private?" was measured and rejected as unworkable: the tree holds 2087
distinct capitalised names, 941 of them appearing once. Even the narrow signal (a two-word or
hyphenated capitalised name) yields 207 rare hits, nearly all legitimate vocabulary like
"Access Control" and "Apollo Federation". Any classifier here drowns in false positives.

So this does not classify. It detects NOVELTY. Every compound name already in the tree has
been through review by virtue of being here; a name that was not here yesterday is the one
worth a glance. Measured: the 20 commits of 2026-08-10, which added three ADRs, a generator,
and a ranker, introduced ZERO new compound names. The guard is quiet by construction and
speaks exactly when something new arrives.

Usage:
  build-proper-noun-baseline.py            # write the baseline
  build-proper-noun-baseline.py --check    # exit 1 on names absent from it
"""

import glob
import json
import re
import sys

BASELINE = "evals/proper-noun-baseline.json"
SCAN = ("wos/**/*.md", "commands/*.md", "commands/*/SKILL.md")
COMPOUND = re.compile(r"\b[A-Z][a-z]{2,}[- ][A-Z][a-z]{2,}\b")


def strip_code(text):
    """Code spans and fences are exempt: identifiers are not prose."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`]*`", "", text)


def scan():
    found = {}
    for pattern in SCAN:
        for path in glob.glob(pattern, recursive=True):
            body = strip_code(open(path, encoding="utf-8", errors="ignore").read())
            for name in COMPOUND.findall(body):
                found.setdefault(name, set()).add(path)
    return found


def main():
    check = "--check" in sys.argv
    found = scan()

    if not check:
        payload = {"names": sorted(found), "count": len(found)}
        with open(BASELINE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")
        print(f"[OK] wrote {BASELINE}: {len(found)} compound proper noun(s)")
        return 0

    try:
        known = set(json.load(open(BASELINE, encoding="utf-8"))["names"])
    except (OSError, KeyError, ValueError):
        print(f"proper-noun-baseline: {BASELINE} missing or unreadable; run without --check",
              file=sys.stderr)
        return 1

    new = sorted(set(found) - known)
    if not new:
        print(f"proper-noun-baseline: clean ({len(found)} known)")
        return 0

    print(f"proper-noun-baseline: {len(new)} compound name(s) not in the baseline", file=sys.stderr)
    for name in new:
        where = ", ".join(sorted(found[name])[:3])
        print(f"  {name!r} in {where}", file=sys.stderr)
    print("", file=sys.stderr)
    print("  This is a NOVELTY signal, not an accusation. Two honest outcomes:", file=sys.stderr)
    print("  1. ordinary vocabulary -> re-run without --check to accept it", file=sys.stderr)
    print("  2. a private name -> sanitize it AND add it to scripts/.mirror-codenames,",
          file=sys.stderr)
    print("     because this guard never sees it again once accepted", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
