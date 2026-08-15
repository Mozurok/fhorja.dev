#!/usr/bin/env python3
"""measure-grounding-shape.py -- the ADR-0146 forward instrument.

ADR-0146 shipped `reference-grounding` rule 7 on five documented incidents and
recorded honestly that two blinded A/B runs measured zero effect, because a
fixture small enough to author is small enough to read exhaustively. It named
the test that would discriminate, and it is not a fixture: measure, across real
sessions after the rule lands, whether the behavior it asks for actually shows
up. If it does not, the rule is ceremony and comes out under rule 1.7.

This script is that measurement. It reports two things, both deterministic.

WHAT IT MEASURES

  A. Cite shape in task artifacts (the rule's own output).
     Rule 3 has produced `Grounded in:` cites naming a REFERENCES.md entry for
     external contracts since ADR-0043. Rule 7 asks for something the corpus
     had almost none of: a `file:line` cite for a claim about IN-REPO behavior.
     So the signal is the ratio, not the total. A corpus where every cite still
     points at REFERENCES.md is a corpus where rule 7 changed nothing.

  B. Read shape in session transcripts (the condition the rule addresses).
     Window reads (a Read with offset/limit, a `sed -n 'X,Yp'`, a head/tail)
     against whole-file reads. Clause (a) of rule 7 exists because a claim over
     a whole surface cannot rest on a window. This number is context for A: if
     window share falls and internal cites rise together, that is the shape the
     rule predicts.

WHAT WAS TRIED AND DOES NOT WORK, recorded so nobody rebuilds it

  A first version tried to detect the failure directly in transcript prose:
  find a quantified claim ("every caller", "all errors"), tie it to the file it
  names, and flag it when that file was only ever read in windows. Validated
  against the session where the forensics had already established
  ground truth, it scored recall ~0 on that detector (0 of 11 quantified claims
  flagged, including the known case) and precision ~0 on its companion
  mirrored-precedent detector (53 of 55 hits, nearly all of them ordinary prose
  containing the word "precedent").

  The reason is structural, not a tuning problem. A claim in prose names the
  SYMBOL ("completeTasksByName already logs"), while a read names the PATH, and
  the join between them is exactly the work a human reviewer does. Tuning the
  regexes until the rate looked right would be fitting the instrument to the
  answer, which is the bias this whole line of work exists to catch. So the
  prose detector is gone and what remains is countable.

HONEST LIMITS

  A rate here cannot be attributed to rule 7 on its own: sessions differ in
  task, model, repository, and operator. It is a trend, and the honest use of a
  trend is to decide whether the question deserves a controlled look.

  A `file:line` cite being present says nothing about whether the cited lines
  support the claim. That check is human, and `claim-grounding` rule 4 says so.

USAGE

  scripts/measure-grounding-shape.py --artifacts projects/
  scripts/measure-grounding-shape.py --transcripts ~/.claude/projects/
  scripts/measure-grounding-shape.py --artifacts projects/ --since 2026-08-13
  scripts/measure-grounding-shape.py --artifacts projects/ --json

Stdlib only, per the repository's zero-runtime-dependency posture.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

DETECTOR_VERSION = "2.0.0"

CITE = re.compile(r"Grounded in:\s*(.+)", re.I)
# An internal cite: a path with a line or line-range. This is rule 7's shape.
INTERNAL_CITE = re.compile(r"[\w./-]+\.\w+:\d+(?:-\d+)?")
# An external cite: names a REFERENCES.md entry, which is rule 3's shape.
EXTERNAL_CITE = re.compile(r"REFERENCES\.md|reference entry|captured entry", re.I)

WINDOW_BASH = re.compile(r"\bsed -n ['\"]?\d+,\d+p|\b(head|tail) -n ?\d+")


def git_first_seen(path: str, repo: str) -> datetime | None:
    """Date a file first appeared, so --since can filter artifacts."""
    try:
        out = subprocess.run(
            ["git", "-C", repo, "log", "--diff-filter=A", "--format=%aI", "-1", "--", path],
            capture_output=True, text=True, timeout=10,
        )
        s = out.stdout.strip()
        return datetime.fromisoformat(s) if s else None
    except Exception:
        return None


def scan_artifacts(root: str, since: datetime | None, repo: str):
    total = internal = external = neither = 0
    files_with = 0
    examples: list[str] = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dirpath, fn)
            try:
                text = open(p, errors="replace").read()
            except OSError:
                continue
            if "Grounded in:" not in text:
                continue
            if since is not None:
                seen = git_first_seen(os.path.relpath(p, repo), repo)
                if seen is not None and seen < since:
                    continue
            hits = CITE.findall(text)
            if not hits:
                continue
            files_with += 1
            for h in hits:
                total += 1
                has_int = bool(INTERNAL_CITE.search(h))
                has_ext = bool(EXTERNAL_CITE.search(h))
                if has_int:
                    internal += 1
                    if len(examples) < 5:
                        examples.append(f"{os.path.relpath(p, repo)}: {h.strip()[:150]}")
                elif has_ext:
                    external += 1
                else:
                    neither += 1
    return {
        "files_with_cites": files_with,
        "cites_total": total,
        "cites_internal_fileline": internal,
        "cites_external_reference": external,
        "cites_neither": neither,
        "examples": examples,
    }


def scan_transcripts(root: str, since: datetime | None):
    window = whole = turns = 0
    sessions = 0
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".jsonl"):
                continue
            sessions += 1
            try:
                fh = open(os.path.join(dirpath, fn), errors="replace")
            except OSError:
                continue
            with fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    if o.get("type") != "assistant":
                        continue
                    if since is not None:
                        ts = str(o.get("timestamp", ""))
                        try:
                            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            if t < since:
                                continue
                        except Exception:
                            pass
                    content = (o.get("message") or {}).get("content")
                    if not isinstance(content, list):
                        continue
                    turns += 1
                    for b in content:
                        if not isinstance(b, dict) or b.get("type") != "tool_use":
                            continue
                        name, inp = b.get("name", ""), (b.get("input") or {})
                        if name == "Read":
                            if inp.get("offset") is not None or inp.get("limit") is not None:
                                window += 1
                            else:
                                whole += 1
                        elif name == "Bash" and WINDOW_BASH.search(str(inp.get("command", ""))):
                            window += 1
    return {"sessions": sessions, "assistant_turns": turns,
            "read_window": window, "read_whole": whole}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--artifacts", help="root to walk for task artifacts carrying `Grounded in:` cites")
    ap.add_argument("--transcripts", help="root to walk for harness .jsonl transcripts")
    ap.add_argument("--since", help="ISO date; artifacts by git add-date, turns by timestamp")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--examples", action="store_true")
    args = ap.parse_args()

    if not args.artifacts and not args.transcripts:
        print("error: give at least one of --artifacts or --transcripts", file=sys.stderr)
        return 2

    since = None
    if args.since:
        try:
            since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"error: --since must be an ISO date, got {args.since!r}", file=sys.stderr)
            return 2

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out: dict = {"detector_version": DETECTOR_VERSION, "since": args.since or None}

    if args.artifacts:
        out["artifacts"] = scan_artifacts(args.artifacts, since, repo)
    if args.transcripts:
        out["transcripts"] = scan_transcripts(args.transcripts, since)

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print(f"grounding-shape v{DETECTOR_VERSION}  since={out['since'] or 'all'}")
    if "artifacts" in out:
        a = out["artifacts"]
        t = a["cites_total"]
        share = (100.0 * a["cites_internal_fileline"] / t) if t else 0.0
        print(f"  A. cite shape       {t} cite(s) across {a['files_with_cites']} artifact(s)")
        print(f"       internal file:line (rule 7 shape)   {a['cites_internal_fileline']:5d}  ({share:.1f}%)")
        print(f"       external reference (rule 3 shape)   {a['cites_external_reference']:5d}")
        print(f"       neither                             {a['cites_neither']:5d}")
        if args.examples:
            for e in a["examples"]:
                print(f"       e.g. {e}")
    if "transcripts" in out:
        r = out["transcripts"]
        reads = r["read_window"] + r["read_whole"]
        wshare = (100.0 * r["read_window"] / reads) if reads else 0.0
        print(f"  B. read shape       {reads} file read(s) over {r['sessions']} session(s)")
        print(f"       window {r['read_window']}, whole {r['read_whole']}  ({wshare:.1f}% windowed)")

    print("  note: a trend, not an attribution. A present cite says nothing about whether")
    print("        the cited lines support the claim; that check stays human.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
