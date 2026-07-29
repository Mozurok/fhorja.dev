#!/usr/bin/env python3
"""plan-adherence.py -- dry-run plan-adherence / flow-conformance check for a task.

Read-only. Compares what a task actually executed against the approved
IMPLEMENTATION_PLAN and reports drift. This is the trace-based / plan-adherence
eval the 2026 agent-eval literature calls for (see REFERENCES.md 2026-07-11 scan,
the confident-ai entry): does the agent stay on the intended workflow, not just
reach an answer.

Two checks:
  1. Slice-set conformance: the executed slices/waves match the approved plan's
     slice set. Flags planned-but-skipped and executed-but-unplanned units.
  2. Command-sequence conformance: the command owners in the trace ran in a valid
     workflow order (no implement before an approval gate, nothing written after
     task-close, a plan before its approval).

Executed signal, in order of reliability (2026-07-29):
  a. `SLICES/NN_*.md` `Status:` lines. This is the PRIMARY source, not a fallback:
     `implement-approved-slice` closes a LOW or MEDIUM slice INLINE, and that path
     is a Regime-2 plain write with no audit line, so a normally-executed slice
     leaves nothing in the trace at all.
  b. `TASK_STATE.md ## Current status -> ### Completed`, when it enumerates units.
  c. Unit-shaped `reason` fields in the audit log.

Three planned-but-not-executed outcomes are reported separately and are NOT drift:
a unit halted or de-scoped on the record, a unit the plan itself marks PROPOSED or
not-approved, and (as verdict UNKNOWN) a task offering no executed signal of any
kind, where absence of evidence cannot be told apart from a real skip.

A 407-task sweep on 2026-07-29 measured the effect of reading those three cases
correctly: 64 of 170 DRIFT verdicts (38%) were misleading, and no CONFORMANT
verdict changed. A check that cries drift on healthy tasks trains its reader to
ignore it, which costs more than the check is worth.

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


UNAPPROVED_WORDS = ("proposed", "not approved", "unapproved", "draft")


def unapproved_units(plan_text):
    """Units the plan itself marks as not-yet-approved.

    A slice carrying `PROPOSED` in its heading or a `Status: planned (PROPOSED)`
    line was never part of the approved execution baseline, so its absence from
    the executed set is the CORRECT outcome, not drift. Without this, every plan
    that parks a proposed slice at the end reports a permanent FAIL, which
    teaches the reader to ignore the verdict."""
    out = set()
    current = None
    for raw in plan_text.splitlines():
        line = raw.strip()
        m = HEADING_UNIT_RE.match(line)
        if m:
            current = (m.group(1).lower(), int(m.group(2)))
            if any(w in line.lower() for w in UNAPPROVED_WORDS):
                out.add(current)
            continue
        if current and STATUS_LINE_RE.match(line.lstrip("- ")):
            if any(w in line.lower() for w in UNAPPROVED_WORDS):
                out.add(current)
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


SLICE_FILE_RE = re.compile(r"^(\d+)[_-]")
STATUS_LINE_RE = re.compile(r"^\**status\**\s*:", re.IGNORECASE)
# Ordered: a halted marker wins over a closed one, because "HALTED before the
# first edit" and "closed as de-scoped" both need to land in `halted`.
HALTED_WORDS = ("halted", "de-scoped", "descoped", "abandoned", "waived",
                "stopped", "cancelled", "canceled", "superseded")
CLOSED_WORDS = ("closed", "done", "complete")


def slice_file_units(task_dir):
    """Per-slice status read from SLICES/NN_*.md -> (closed, halted) unit sets.

    This is the third executed-signal, and for most tasks it is the only correct
    one. `implement-approved-slice` closes a LOW or MEDIUM slice INLINE, and the
    inline path is a Regime-2 plain write: no wos:write header, no audit line
    (see `wos/substrate-peers.md`). So a normally-executed slice leaves NOTHING
    in the trace, and a task that closed 7 of 8 slices inline reads as 7 skipped
    units unless the slice files are consulted. Reading them is not a fallback,
    it is the primary source for the common path.
    """
    closed, halted = set(), set()
    sdir = os.path.join(task_dir, "SLICES")
    if not os.path.isdir(sdir):
        return closed, halted
    for name in sorted(os.listdir(sdir)):
        if not name.endswith(".md"):
            continue
        m = SLICE_FILE_RE.match(name)
        if not m:
            continue
        n = int(m.group(1))
        status = ""
        for line in read(os.path.join(sdir, name)).splitlines():
            if STATUS_LINE_RE.match(line.strip()):
                status = line.split(":", 1)[1].replace("*", "").strip().lower()
                break
        if not status:
            continue
        if any(w in status for w in HALTED_WORDS):
            halted.add(("slice", n))
        elif any(w in status for w in CLOSED_WORDS):
            closed.add(("slice", n))
    return closed, halted


def executed_units(task_text, reasons_text="", slice_closed=frozenset()):
    """Units marked done, from three sources in order of reliability.

    1. `SLICES/NN_*.md` status lines (the only signal the inline-close path leaves)
    2. the TASK_STATE `### Completed` section
    3. the audit-log reason fields

    The reasons pass also catches range forms like `slices-1-4` (each number in
    the range is treated as executed)."""
    out = set(slice_closed)
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
    unapproved = unapproved_units(plan)
    slice_closed, slice_halted = slice_file_units(task)
    executed = executed_units(state, log_reasons(log_path), slice_closed)
    # Two classes of planned-but-not-executed are correct outcomes, not drift:
    # a unit halted or de-scoped on the record (a decision), and a unit the plan
    # never approved (never in the baseline). Both get their own report line;
    # only what is left is a silent skip.
    skipped = planned - executed - slice_halted - unapproved
    unplanned = executed - planned

    slice_status = "PASS"
    if not planned:
        slice_status = "N/A"
    elif not executed:
        # No executed signal of any kind: no SLICES/ status lines, no enumerated
        # units in TASK_STATE ### Completed, no unit-shaped log reasons. That is
        # an absence of evidence, not evidence of a skip, and the two are not
        # distinguishable from here (a task predating the Status: convention
        # looks identical to one that genuinely ran nothing). Report UNKNOWN so
        # the verdict stays readable; calling it FAIL is what teaches a reader
        # to ignore this check.
        slice_status = "UNKNOWN"
    elif skipped or unplanned:
        slice_status = "FAIL"

    seq_status, seq_findings = check_sequence(seq)

    verdict = "CONFORMANT"
    if slice_status == "FAIL" or seq_status == "FAIL":
        verdict = "DRIFT"
    elif slice_status == "UNKNOWN":
        verdict = "UNKNOWN (no executed signal to compare)"
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
        if slice_halted:
            print(f"  halted or de-scoped on the record: {fmt_units(slice_halted)} "
                  f"(a recorded decision, not counted as drift)")
        if unapproved:
            print(f"  planned but never approved:        {fmt_units(unapproved)} "
                  f"(outside the approved baseline, not counted as drift)")
        print(f"  executed-signal source: {len(slice_closed)} from SLICES/ status lines, "
              f"{len(executed) - len(slice_closed & executed)} from TASK_STATE or the audit log")
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
