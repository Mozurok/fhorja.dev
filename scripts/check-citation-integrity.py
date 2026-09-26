#!/usr/bin/env python3
"""check-citation-integrity.py -- the attribution half of citation checking.

`check-doc-sync.sh` already answers "does the cited artifact exist" and reports
zero broken across ~6600 refs. This answers the different question that three
audit waves found dominating the defect set: does the cited artifact SAY what
the citing text claims. Every finding fixed on 2026-09-03 in that class pointed
at something that existed and said something else.

Four checks, each decidable by reading. Anything needing judgment is out of
scope on purpose: this reports what a script can prove, and the audit waves keep
the rest.

  A  script-flag       `scripts/x.sh --flag` where that script rejects --flag
  B  numbered-rule     `rule N of <file>` where <file> has fewer than N rules
  C  claimed-count     `N-field` / `N-bullet` against the list actually cited
  D  attribution       `defined in `## X`` where `## X` does not contain the
                       token being attributed to it

Usage: python3 scripts/check-citation-integrity.py [--verbose] [--strict]
Exit:  0 clean (or findings without --strict), 1 with --strict and findings.
"""
import os, re, sys, io, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERBOSE = "--verbose" in sys.argv
STRICT = "--strict" in sys.argv
findings = []
checked = 0


def read(p):
    try:
        return io.open(os.path.join(ROOT, p), encoding="utf-8").read()
    except Exception:
        return None


def scan_files():
    out = []
    for sub in ("commands", "wos"):
        for root, _, fs in os.walk(os.path.join(ROOT, sub)):
            for f in fs:
                if f.endswith(".md"):
                    out.append(os.path.relpath(os.path.join(root, f), ROOT))
    for f in ("WORKFLOW_OPERATING_SYSTEM.md", "AGENTS.md", "README.md", "CONTRIBUTING.md",
              "WORKFLOW_DEMO.md", "COMMAND_PROMPT_STUBS.md",
              "docs/FAQ.md", "docs/MIGRATION.md", "docs/adr/README.md", "evals/README.md"):
        # CHANGELOG.md is deliberately out. It narrates past defects in their own
        # words ("it cited rule 7 of a file with two rules"), so scanning it reports
        # the description as the defect. Same shape as the ADR-0133 qualification
        # that names a route in order to exclude it.
        if os.path.isfile(os.path.join(ROOT, f)):
            out.append(f)
    return sorted(out)


def finding(path, line_no, check, msg):
    findings.append((path, line_no, check, msg))


# ---------------------------------------------------------------- A: script flags
FLAG_RE = re.compile(r"`?(scripts/[\w.-]+\.(?:sh|py))([^`\n]{0,80}?)(--[a-z][a-z0-9-]*)")


def check_flags(path, text):
    global checked
    for m in FLAG_RE.finditer(text):
        script, _, flag = m.group(1), m.group(2), m.group(3)
        body = read(script)
        if body is None:
            continue  # existence is doc-sync's job
        checked += 1
        if flag not in body:
            ln = text[: m.start()].count("\n") + 1
            finding(path, ln, "script-flag",
                    f"`{script} {flag}` but that script never mentions `{flag}`")


# ------------------------------------------------------------ B: numbered rules
RULE_RE = re.compile(r"rule (\d+) of `([\w./-]+\.md)`")


def rule_numbers(body):
    """The set of rule numbers present, never the count. A file numbered 2..7 has
    six rules and rule 7 exists; counting flags it as missing. First version of
    this script did exactly that and reported a false positive."""
    return {int(n) for n in re.findall(r"^\s*(\d+)\.\s", body, re.M)}


def check_rules(path, text):
    global checked
    for m in RULE_RE.finditer(text):
        n, target = int(m.group(1)), m.group(2)
        body = read(target)
        if body is None:
            continue
        checked += 1
        have = rule_numbers(body)
        if have and n not in have:
            ln = text[: m.start()].count("\n") + 1
            rng = f"{min(have)} to {max(have)}"
            finding(path, ln, "numbered-rule",
                    f"cites rule {n} of `{target}`, whose rules are numbered {rng}")


# ------------------------------------------------------------- C: claimed counts
# Only the referents that are countable without judgment.
COUNT_SPECS = [
    (re.compile(r"(\d+)-field schema"), "wos/substrate-peers.md", "## Audit trail",
     lambda b: len(re.findall(r"^- `\w+`", b, re.M)), "required field"),
    (re.compile(r"(\d+)-bullet entry to `LEARNINGS\.md`"), "templates/LEARNINGS.md", "## Entry shape",
     lambda b: (int(re.search(r"(\d+) required bullets", b).group(1))
                if re.search(r"(\d+) required bullets", b) else None), "required bullet"),
]


def section_body(body, heading):
    # Prefix match, because the citing convention drops a heading's parenthetical:
    # commands cite `## Audit trail` for a heading that reads
    # `## Audit trail (VERIFICATION_LOG.jsonl)`. Exact match silently found
    # nothing and the check reported clean, which is the worst failure a guard has.
    m = re.search(r"^" + re.escape(heading) + r"(?: \(|\s*$)", body, re.M)
    if not m:
        return None
    rest = body[m.end():]
    nxt = re.search(r"^#{1,2} ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def check_counts(path, text):
    global checked
    for rx, target, heading, counter, label in COUNT_SPECS:
        body = read(target)
        if body is None:
            continue
        sec = section_body(body, heading)
        if sec is None:
            continue
        truth = counter(sec)
        if truth is None:
            continue
        for m in rx.finditer(text):
            checked += 1
            claimed = int(m.group(1))
            if claimed != truth:
                ln = text[: m.start()].count("\n") + 1
                finding(path, ln, "claimed-count",
                        f"claims {claimed} {label}s; `{target} {heading}` defines {truth}")


# --------------------------------------------------------------- D: attribution
# "<quoted token> ... defined in|under `## X`" -- the named section must contain
# the token. This is the check that catches a citation pointing at a real
# section that does not hold the rule.
ATTR_RE = re.compile(r"defined (?:in|under) `(#{2,3} [^`]+)`")
TOKEN_RE = re.compile(r"`([^`\n]{3,60})`")


def check_attribution(path, text, spec):
    global checked
    for m in ATTR_RE.finditer(text):
        heading = m.group(1)
        sec = section_body(spec, heading)
        if sec is None:
            continue  # doc-sync owns "heading does not exist"
        # Every backticked token in the sentence before the attribution, not just
        # the nearest one: the nearest is often an unrelated example. At least one
        # must appear in the named section, or nothing in the sentence is defined
        # where the sentence says it is.
        start = text.rfind(".", 0, m.start()) + 1
        tokens = [t for t in TOKEN_RE.findall(text[start:m.start()]) if len(t.strip()) > 2]
        if not tokens:
            continue
        checked += 1
        if not any(t in sec for t in tokens):
            ln = text[: m.start()].count("\n") + 1
            finding(path, ln, "attribution",
                    f"attributes {', '.join('`'+t+'`' for t in tokens[:3])} to `{heading}`, "
                    f"whose body contains none of them")


def main():
    spec = read("WORKFLOW_OPERATING_SYSTEM.md") or ""
    files = scan_files()
    for p in files:
        t = read(p)
        if t is None:
            continue
        check_flags(p, t)
        check_rules(p, t)
        check_counts(p, t)
        check_attribution(p, t, spec)

    by = {}
    for f in findings:
        by.setdefault(f[2], []).append(f)
    if findings:
        for check in sorted(by):
            print(f"\n{check} ({len(by[check])}):")
            for path, ln, _, msg in sorted(by[check]):
                print(f"  {path}:{ln}: {msg}")
    print(f"\nCitation-integrity: {checked} attribution(s) checked across {len(files)} file(s), "
          f"{len(findings)} unresolved")
    if VERBOSE and not findings:
        print("  (existence of the cited artifact is check-doc-sync.sh's job; this checks what it says)")
    return 1 if (findings and STRICT) else 0


if __name__ == "__main__":
    sys.exit(main())
