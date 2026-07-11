#!/usr/bin/env python3
"""plan-adherence.py -- dry-run plan-adherence / flow-conformance check for a task.

Read-only. Compares what a task actually executed (from the append-only
.wos/VERIFICATION_LOG.jsonl trace and the TASK_STATE completed list) against the
approved IMPLEMENTATION_PLAN, and reports drift. This is the trace-based /
plan-adherence eval the 2026 agent-eval literature calls for (see REFERENCES.md
2026-07-11 scan, the confident-ai entry): does the agent stay on the intended
workflow, not just reach an answer.

Two checks:
  1. Slice-set conformance: the executed slices/waves match the approved plan's
     slice set. Flags planned-but-skipped and executed-but-unplanned units.
  2. Command-sequence conformance: the command owners in the trace ran in a valid
     workflow order (no implement before an approval gate, nothing written after
     task-close, a plan before its approval).

Writes nothing. Prints a report to stdout; exit 0 by default (informational),
exit 1 on FAIL under --strict.

Usage:
  python3 scripts/plan-adherence.py <task-folder>
  python3 scripts/plan-adherence.py <task-folder> --strict   # exit 1 on FAIL
"""

import sys
import os
import re
import json

UNIT_RE = re.compile(r"\b(slice|wave)\s+(\d+)\b", re.IGNORECASE)
HEADING_UNIT_RE = re.compile(r"^###\s+(Slice|Wave)\s+(\d+)\b", re.IGNORECASE)


def read(path):
    return open(path, encoding="utf-8").read() if os.path.isfile(path) else ""


def planned_units(plan_text):
    """Units declared as `### Slice N` / `### Wave N` headings in the plan."""
    out = set()
    for line in plan_text.splitlines():
        m = HEADING_UNIT_RE.match(line.strip())
        if m:
            out.add((m.group(1).lower(), int(m.group(2))))
    return out


def completed_section(task_text):
    """The lines under `## Current status` -> `### Completed`."""
    lines = task_text.splitlines()
    in_status = in_completed = False
    body = []
    for l in lines:
        if l.startswith("## "):
            in_status = (l.strip() == "## Current status")
            in_completed = False
            continue
        if in_status and l.startswith("### "):
            in_completed = (l.strip() == "### Completed")
            continue
        if in_completed:
            body.append(l)
    return "\n".join(body)


def log_reasons(log_path):
    """Concatenated reason fields from the audit log (a secondary executed signal)."""
    out = []
    if not os.path.isfile(log_path):
        return ""
    for line in open(log_path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        r = o.get("reason")
        if r:
            out.append(r)
    return "\n".join(out)


def executed_units(task_text, reasons_text=""):
    """Units marked done: the TASK_STATE completed section plus the log reasons.

    The reasons pass also catches range forms like `slices-1-4` (each number in
    the range is treated as executed)."""
    out = set()
    for m in UNIT_RE.finditer(completed_section(task_text)):
        out.add((m.group(1).lower(), int(m.group(2))))
    # log reasons: `slice-2`, `wave-1`, and ranges `slices-1-4` / `slices 1 4`
    for m in re.finditer(r"(slice|wave)s?[-\s](\d+)(?:[-\s](\d+))?", reasons_text, re.IGNORECASE):
        t = m.group(1).lower()
        lo = int(m.group(2))
        hi = int(m.group(3)) if m.group(3) else lo
        for n in range(min(lo, hi), max(lo, hi) + 1):
            out.add((t, n))
    return out


def owner_sequence(log_path):
    """Ordered (ts, owner) list from the audit log; user/worker rows kept out."""
    seq = []
    if not os.path.isfile(log_path):
        return seq
    for line in open(log_path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        ow = o.get("owner")
        ts = o.get("ts") or ""
        if ow:
            seq.append((ts, ow))
    return seq


def first_index(seq, owner):
    for i, (_ts, ow) in enumerate(seq):
        if ow == owner:
            return i
    return -1


def last_index(seq, owner):
    idx = -1
    for i, (_ts, ow) in enumerate(seq):
        if ow == owner:
            idx = i
    return idx


def check_sequence(seq):
    """Return (status, findings). status in PASS/WARN/FAIL."""
    findings = []
    status = "PASS"
    owners = {ow for _ts, ow in seq}
    impl = [c for c in ("implement-approved-slice", "implement-fleet",
                        "implement-slice-complement") if c in owners]

    # Gate 1: implementation must be preceded by an approval gate.
    if impl:
        ap = first_index(seq, "approve-plan")
        first_impl = min(first_index(seq, c) for c in impl)
        if ap == -1:
            status = "WARN" if status == "PASS" else status
            findings.append(
                "WARN: implementation ran but no approve-plan owner is in the "
                "trace (approval may have been inline; confirm it was approved)")
        elif ap > first_impl:
            status = "FAIL"
            findings.append(
                f"FAIL: approve-plan (index {ap}) appears AFTER the first "
                f"implementation write (index {first_impl}); implementation "
                "preceded approval")

    # Gate 2: a plan must precede its approval.
    if "approve-plan" in owners and "implementation-plan" in owners:
        if first_index(seq, "implementation-plan") > first_index(seq, "approve-plan"):
            status = "FAIL"
            findings.append(
                "FAIL: approve-plan appears before implementation-plan; a plan "
                "was approved before it was written")

    # Gate 3: task-close must be terminal (nothing written after it).
    if "task-close" in owners:
        tc = last_index(seq, "task-close")
        after = [ow for (_ts, ow) in seq[tc + 1:]]
        if after:
            status = "FAIL"
            findings.append(
                f"FAIL: {len(after)} substrate write(s) after task-close "
                f"({', '.join(sorted(set(after)))}); task-close must be terminal")

    if not findings:
        findings.append("valid workflow order (approval before implementation, "
                        "plan before approval, task-close terminal)")
    return status, findings


def fmt_units(units):
    return ", ".join(f"{t} {n}" for (t, n) in sorted(units, key=lambda x: (x[0], x[1]))) or "(none)"


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    strict = "--strict" in argv
    if not args:
        print("usage: plan-adherence.py <task-folder> [--strict]", file=sys.stderr)
        return 2
    task = args[0].rstrip("/")
    if not os.path.isdir(task):
        print(f"plan-adherence: not a directory: {task}", file=sys.stderr)
        return 2

    log_path = os.path.join(task, ".wos", "VERIFICATION_LOG.jsonl")
    plan = read(os.path.join(task, "IMPLEMENTATION_PLAN.md"))
    state = read(os.path.join(task, "TASK_STATE.md"))
    seq = owner_sequence(log_path)

    planned = planned_units(plan)
    executed = executed_units(state, log_reasons(log_path))
    skipped = planned - executed
    unplanned = executed - planned

    slice_status = "PASS"
    if not planned:
        slice_status = "N/A"
    elif skipped or unplanned:
        slice_status = "FAIL"

    seq_status, seq_findings = check_sequence(seq)

    verdict = "CONFORMANT"
    if slice_status == "FAIL" or seq_status == "FAIL":
        verdict = "DRIFT"
    elif seq_status == "WARN":
        verdict = "CONFORMANT (with warnings)"

    print(f"# Plan-adherence check (dry-run) -- {os.path.basename(task)}")
    print(f"Planned units: {len(planned)}   Executed units: {len(executed)}   "
          f"Trace writes: {len(seq)}")
    print()
    print(f"## Slice-set conformance: {slice_status}")
    if planned:
        print(f"  planned:   {fmt_units(planned)}")
        print(f"  executed:  {fmt_units(executed)}")
        print(f"  skipped (planned, not executed):   {fmt_units(skipped)}")
        print(f"  unplanned (executed, not planned): {fmt_units(unplanned)}")
        if not executed:
            print("  note: no slice-anchored completion evidence found; the work "
                  "may be incomplete, OR completion was not recorded per slice "
                  "number (record slice N done in TASK_STATE ## Current status).")
    else:
        print("  no ### Slice/Wave headings in IMPLEMENTATION_PLAN.md (nothing to compare)")
    print()
    print(f"## Command-sequence conformance: {seq_status}")
    for f in seq_findings:
        print(f"  - {f}")
    print()
    print(f"VERDICT: {verdict}")

    if strict and verdict.startswith("DRIFT"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
