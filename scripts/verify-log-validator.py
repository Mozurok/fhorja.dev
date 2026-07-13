#!/usr/bin/env python3
"""verify-log-validator.py - Validate VERIFICATION_LOG.jsonl per wos/substrate-peers.md schema.

Per K.7 (joint J.11) + J.5, Epic K v2.1 2026-06-04.

Reads:  projects/<client>__<project>/active/<task>/.wos/VERIFICATION_LOG.jsonl  (one JSON object per line)
Checks: required fields, enum values, ISO 8601 ts, SHA-256 hex, partials shape

Cross-checks (after line validation, when the target is a .wos/VERIFICATION_LOG.jsonl):
  delete-orphan (ADR-0101): the last applied event for a (file, section) is
  write/overwrite but the '## ' heading line is gone from the file on disk.
  Warn-only by default; --check-deletes promotes the class to errors.
  sha-chain (advisory): an applied write/overwrite whose sha_before differs
  from the pair's previous sha_after in the log. Never flips the exit code.

Usage:
  python3 scripts/verify-log-validator.py <path-to-VERIFICATION_LOG.jsonl>
  python3 scripts/verify-log-validator.py --task <task-folder>
  python3 scripts/verify-log-validator.py --task <task-folder> --check-deletes
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_FIELDS = {
    "ts", "run_id", "owner", "owner_type", "invoked_by",
    "file", "section", "event", "mode",
    "sha_before", "sha_after", "reason", "partials", "strategy",
}

OWNER_TYPES = {"command", "persona", "fleet-merger"}

EVENTS = {
    "write", "overwrite", "propose", "approve", "refuse", "delete",
    "fleet-merge", "legacy-promote", "partial_merge",
    "merge_include", "merge_with_gap",
    "worker_failed", "worker_interrupted", "worker_missing", "worker_timeout",
    "retry_needs_revision", "max_iterations_promoted",
    "retry_failed_recoverable", "quorum_discard",
}

MODES = {"applied", "proposed"}

MERGE_STRATEGIES = {"union", "last-by-timestamp", "consensus-of-N", "manual-review"}

FLEET_EVENTS = {
    "fleet-merge", "partial_merge", "merge_include", "merge_with_gap",
    "worker_failed", "worker_interrupted", "worker_missing", "worker_timeout",
    "retry_needs_revision", "max_iterations_promoted",
    "retry_failed_recoverable", "quorum_discard",
}

ISO_8601_MS = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
)
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
SECTION_PREFIX = re.compile(r"^## ")
REASON_MAX_CHARS = 80


def validate_line(idx: int, raw: str) -> list[str]:
    errors: list[str] = []
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        return [f"line {idx}: invalid JSON: {e}"]

    if not isinstance(obj, dict):
        return [f"line {idx}: not a JSON object"]

    missing = REQUIRED_FIELDS - set(obj.keys())
    if missing:
        errors.append(f"line {idx}: missing fields: {sorted(missing)}")

    ts = obj.get("ts")
    if isinstance(ts, str) and not ISO_8601_MS.match(ts):
        errors.append(f"line {idx}: ts not ISO 8601 with ms precision (got {ts!r})")

    if not isinstance(obj.get("run_id"), str) or not obj["run_id"]:
        errors.append(f"line {idx}: run_id must be non-empty string")

    if not isinstance(obj.get("owner"), str) or not obj["owner"]:
        errors.append(f"line {idx}: owner must be non-empty string")

    owner_type = obj.get("owner_type")
    if owner_type not in OWNER_TYPES:
        errors.append(f"line {idx}: owner_type {owner_type!r} not in {sorted(OWNER_TYPES)}")

    invoked_by = obj.get("invoked_by")
    if invoked_by is not None and not isinstance(invoked_by, str):
        errors.append(f"line {idx}: invoked_by must be string or null")

    if not isinstance(obj.get("file"), str) or not obj["file"]:
        errors.append(f"line {idx}: file must be non-empty string")

    section = obj.get("section")
    if not isinstance(section, str) or not SECTION_PREFIX.match(section):
        errors.append(f"line {idx}: section must start with '## ' (got {section!r})")

    event = obj.get("event")
    if event not in EVENTS:
        errors.append(f"line {idx}: event {event!r} not in canonical taxonomy")

    mode = obj.get("mode")
    if mode not in MODES:
        errors.append(f"line {idx}: mode {mode!r} not in {sorted(MODES)}")

    for fname in ("sha_before", "sha_after"):
        v = obj.get(fname)
        if v is None:
            continue
        if not isinstance(v, str) or not SHA256_HEX.match(v):
            errors.append(f"line {idx}: {fname} not SHA-256 hex (got {v!r})")

    # sha_after MUST be non-null hex on applied writes -- an applied write
    # produced bytes, so a SHA exists. K.4 cutover fix (2026-06-04): catches
    # the half-compliant pattern where writers emit a JSONL line with null
    # SHAs (placeholder) but actually mutated the section.
    if event in ("write", "overwrite") and mode == "applied" and obj.get("sha_after") is None:
        errors.append(
            f"line {idx}: event={event!r} with mode='applied' requires non-null sha_after (the write produced bytes; compute SHA-256 of the new section bytes)"
        )

    # delete convention (ADR-0101): the section existed before (non-null
    # sha_before) and no longer exists after (sha_after null).
    if event == "delete":
        if obj.get("sha_before") is None:
            errors.append(
                f"line {idx}: event='delete' requires non-null sha_before (a delete removes a section that existed)"
            )
        if obj.get("sha_after") is not None:
            errors.append(
                f"line {idx}: event='delete' requires null sha_after (the section no longer exists)"
            )

    reason = obj.get("reason")
    if not isinstance(reason, str):
        errors.append(f"line {idx}: reason must be string")
    elif len(reason) > REASON_MAX_CHARS:
        errors.append(f"line {idx}: reason exceeds {REASON_MAX_CHARS} chars (got {len(reason)})")

    partials = obj.get("partials")
    if partials is not None:
        if not isinstance(partials, list) or not all(isinstance(p, str) for p in partials):
            errors.append(f"line {idx}: partials must be array of strings or null")

    strategy = obj.get("strategy")
    if strategy is not None:
        if strategy not in MERGE_STRATEGIES:
            errors.append(f"line {idx}: strategy {strategy!r} not in {sorted(MERGE_STRATEGIES)}")

    if event == "fleet-merge":
        if owner_type != "fleet-merger":
            errors.append(f"line {idx}: event=fleet-merge requires owner_type=fleet-merger")
        if not partials:
            errors.append(f"line {idx}: event=fleet-merge requires non-empty partials")
        if not strategy:
            errors.append(f"line {idx}: event=fleet-merge requires strategy")

    if event not in FLEET_EVENTS and partials is not None:
        errors.append(f"line {idx}: partials must be null for non-fleet event {event!r}")
    if event not in FLEET_EVENTS and strategy is not None:
        errors.append(f"line {idx}: strategy must be null for non-fleet event {event!r}")

    return errors


def sha_chain_advisories(applied_entries: list[tuple[int, dict]]) -> list[str]:
    """Warn-only sha-chain advisory: an applied write/overwrite whose sha_before
    differs from the previous sha_after recorded for the same (file, section)
    in the log. Advisory text only; never flips the exit code."""
    advisories: list[str] = []
    last_sha_after: dict[tuple[str, str], object] = {}
    for idx, obj in applied_entries:
        file_ = obj.get("file")
        section = obj.get("section")
        if not isinstance(file_, str) or not isinstance(section, str):
            continue
        key = (file_, section)
        if obj.get("event") in ("write", "overwrite") and key in last_sha_after:
            prev = last_sha_after[key]
            if obj.get("sha_before") != prev:
                advisories.append(
                    f"line {idx}: sha_before {obj.get('sha_before')!r} differs from previous sha_after {prev!r} for {file_} {section!r} (sha-chain advisory)"
                )
        last_sha_after[key] = obj.get("sha_after")
    return advisories


def delete_orphan_findings(applied_entries: list[tuple[int, dict]], task_dir: Path) -> list[str]:
    """Delete-orphan cross-check (ADR-0101): a (file, section) whose last
    applied event is write/overwrite, whose file exists at task_dir, but whose
    '## ' heading line is gone from the file on disk. Files that do not
    resolve at task_dir are skipped."""
    last_event: dict[tuple[str, str], tuple[int, object]] = {}
    for idx, obj in applied_entries:
        file_ = obj.get("file")
        section = obj.get("section")
        if not isinstance(file_, str) or not isinstance(section, str):
            continue
        last_event[(file_, section)] = (idx, obj.get("event"))

    findings: list[str] = []
    for (file_, section), (idx, event) in last_event.items():
        if event not in ("write", "overwrite"):
            continue
        path = task_dir / file_
        if not path.is_file():
            continue
        try:
            headings = {ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()}
        except OSError:
            continue
        if section.strip() not in headings:
            findings.append(
                f"{file_} {section!r} (last event: line {idx}): section removed without event=delete (delete-orphan, ADR-0101)"
            )
    return findings


def resolve_target(args: argparse.Namespace) -> Path:
    if args.path:
        return Path(args.path)
    if args.task:
        repo_root = Path(__file__).resolve().parent.parent
        pattern = f"projects/*/active/{args.task}/.wos/VERIFICATION_LOG.jsonl"
        matches = sorted(repo_root.glob(pattern))
        if len(matches) == 1:
            return matches[0]
        if not matches:
            print(f"ERROR: no match for {pattern} under {repo_root}", file=sys.stderr)
            sys.exit(2)
        print(f"ERROR: --task {args.task} matches multiple logs:", file=sys.stderr)
        for m in matches:
            print(f"  {m}", file=sys.stderr)
        sys.exit(2)
    print("ERROR: provide a path or --task", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?")
    p.add_argument("--task", help="task folder name under projects/<client>__<project>/active/")
    p.add_argument("--max-errors", type=int, default=50)
    p.add_argument(
        "--check-deletes",
        action="store_true",
        help="promote delete-orphan findings (ADR-0101) from warnings to errors",
    )
    args = p.parse_args()

    target = resolve_target(args)
    if not target.exists():
        print(f"ERROR: not found: {target}", file=sys.stderr)
        return 2

    total = 0
    bad = 0
    all_errors: list[str] = []
    applied_entries: list[tuple[int, dict]] = []

    with target.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            total += 1
            errors = validate_line(i, stripped)
            if errors:
                bad += 1
                all_errors.extend(errors)
                if len(all_errors) >= args.max_errors:
                    break
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("mode") == "applied":
                applied_entries.append((i, obj))

    advisories = sha_chain_advisories(applied_entries)

    delete_orphans: list[str] = []
    if target.name == "VERIFICATION_LOG.jsonl" and target.parent.name == ".wos":
        delete_orphans = delete_orphan_findings(applied_entries, target.parent.parent)

    print(f"file: {target}")
    print(f"lines: {total}")
    print(f"invalid: {bad}")

    if advisories:
        print()
        print("SHA-CHAIN ADVISORIES (warn-only, never affects exit code):")
        for a in advisories:
            print(f"  {a}")

    if delete_orphans:
        print()
        if args.check_deletes:
            print("DELETE-ORPHAN ERRORS (--check-deletes):")
        else:
            print("DELETE-ORPHAN WARNINGS (warn-only; --check-deletes promotes to errors):")
        for d in delete_orphans:
            print(f"  {d}")

    if all_errors:
        print()
        print("ERRORS:")
        for e in all_errors[: args.max_errors]:
            print(f"  {e}")
        if len(all_errors) > args.max_errors:
            print(f"  ... and {len(all_errors) - args.max_errors} more")
        return 1
    if args.check_deletes and delete_orphans:
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
