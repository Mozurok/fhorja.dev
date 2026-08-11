#!/usr/bin/env python3
"""Emit the compact output-contract summary that goes at the top of a large skill body.

WHY. Skill bodies are re-injected after compaction capped at 5,000 tokens, and the
documentation is explicit that "truncation keeps the start of the file". Every command puts its
output contract at the END, so measured 2026-08-10: 55 of 98 skills exceed the cap and 46 lose
`### Definition of done` outright, along with Handoff and the output layout, exactly when the
session has run longest.

The first mitigation shipped today was a notice telling the agent its tail was gone and to
re-read the file. That is honest but weak: it depends on the agent acting on it.

This is the pattern the vendor documentation actually recommends for partial reads: "For
reference files longer than 100 lines, include a table of contents at the top. This ensures
Claude can see the full scope of available information even when previewing with partial
reads." So the summary carries the contract in compressed form rather than announcing its
absence.

Reordering the whole file was measured as the alternative and rejected: it does not remove the
cut, it only changes what falls off, and the position effect on instruction ADHERENCE is
model-specific and unpredictable in direction (arXiv 2607.19257 measured up to 8.7pp in BOTH
directions across 5 models). Trading a known loss for an unpredictable one is a bad deal.

Usage: emit-skill-contract-summary.py <command-file>   # prints the block, or nothing
"""

import os
import re
import sys

# Sections whose absence changes what the command EMITS, in the order they are summarized.
CONTRACT_SECTIONS = (
    "### Standard output layout",
    "### Artifact changes",
    "### Command transcript",
    "### Handoff",
    "### Definition of done",
)
CAP_CHARS = 20000
MAX_CLAUSE = 130


def first_rule(body):
    """The first substantive line of a section: the rule, not the heading or a blank."""
    for line in body.split("\n")[1:]:
        line = line.strip()
        if not line or line.startswith("<!--"):
            continue
        line = re.sub(r"^[-*]\s+", "", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        return line[:MAX_CLAUSE].rstrip() + ("..." if len(line) > MAX_CLAUSE else "")
    return ""


def main():
    if len(sys.argv) < 2 or not os.path.isfile(sys.argv[1]):
        return 0
    text = open(sys.argv[1], encoding="utf-8").read()
    if len(text) <= CAP_CHARS:
        return 0

    sections = re.split(r"(?m)^(?=### )", text)
    found = []
    for head in CONTRACT_SECTIONS:
        for sec in sections:
            if sec.startswith(head):
                rule = first_rule(sec)
                if rule:
                    found.append((sec.split("\n", 1)[0].strip(), rule))
                break
    if not found:
        return 0

    print("> **Output contract, in brief.** This body is over the per-skill re-injection cap, so")
    print("> after a compaction the sections below are truncated away while this summary survives.")
    print("> They remain authoritative in full; re-read this file before emitting if you need them.")
    print(">")
    for head, rule in found:
        print(f"> - `{head[4:]}`: {rule}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
