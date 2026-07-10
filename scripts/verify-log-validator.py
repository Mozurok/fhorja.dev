#!/usr/bin/env python3
"""verify-log-validator.py - Validate VERIFICATION_LOG.jsonl per wos/substrate-peers.md schema.

Per K.7 (joint J.11) + J.5, Epic K v2.1 2026-06-04.

Reads:  active/<task>/.wos/VERIFICATION_LOG.jsonl  (one JSON object per line)
Checks: required fields, enum values, ISO 8601 ts, SHA-256 hex, partials shape

Usage:
  python3 scripts/verify-log-validator.py <path-to-VERIFICATION_LOG.jsonl>
  python3 scripts/verify-log-validator.py --task <task-folder>
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
    "write", "overwrite", "propose", "approve", "refuse",
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


def resolve_target(args: argparse.Namespace) -> Path:
    if args.path:
        return Path(args.path)
    if args.task:
        return Path(__file__).resolve().parent.parent / "active" / args.task / ".wos" / "VERIFICATION_LOG.jsonl"
    print("ERROR: provide a path or --task", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?")
    p.add_argument("--task", help="task folder name under active/")
    p.add_argument("--max-errors", type=int, default=50)
    args = p.parse_args()

    target = resolve_target(args)
    if not target.exists():
        print(f"ERROR: not found: {target}", file=sys.stderr)
        return 2

    total = 0
    bad = 0
    all_errors: list[str] = []

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

    print(f"file: {target}")
    print(f"lines: {total}")
    print(f"invalid: {bad}")
    if all_errors:
        print()
        print("ERRORS:")
        for e in all_errors[: args.max_errors]:
            print(f"  {e}")
        if len(all_errors) > args.max_errors:
            print(f"  ... and {len(all_errors) - args.max_errors} more")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
