#!/usr/bin/env python3
"""fix-legacy-substrate-headers.py -- Retroactively fix legacy VERIFICATION_LOG.jsonl
lines that violate the K.5 validator (event=write|overwrite + mode=applied +
sha_after=null is logically impossible: an applied write produced bytes, so a
SHA exists).

Background: K.8 first-lived-test (2026-06-04, pilot-repo session) and
follow-on sweeps surfaced legacy lines emitted by writers (implement-
approved-slice, slice-closure, repo-consistency-sweep, etc.) with null sha_after.
Commit 7879f3b tightened the K.5 validator (`scripts/verify-log-validator.py`)
to reject this pattern. This script repairs existing logs by computing the
SHA-256 of the CURRENT section bytes and writing it back into `sha_after`.

`sha_before` is left as-is (cannot be recovered from current file state).

Algorithm mirrors `scripts/scan-substrate-headers.sh` SHA computation and
`commands/_shared/substrate-write-protocol.md ## Concrete computation`
canonical helper: SHA-256 of bytes between `## <section>` and next `## ` line
or EOF, joined by '\n' (matches awk-style section extraction).

Usage:
  python3 scripts/fix-legacy-substrate-headers.py <path-to-VERIFICATION_LOG.jsonl> [--dry-run]
  python3 scripts/fix-legacy-substrate-headers.py --task <task-folder> [--dry-run]
  # When --task is given, log path is resolved as
  # <repo-root>/active/<task-folder>/.wos/VERIFICATION_LOG.jsonl
  # (mirrors verify-log-validator.py's resolve_target).

Exit codes:
  0  success (whether or not any lines were fixed)
  1  partial fix (some fixable lines could not be recovered -- file or
                  section missing, or post-fix line failed schema check)
  2  invocation error (missing args, log file not found, etc.)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# -- Mirror K.5 validator constants so post-fix self-check stays in sync. --
SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
ISO_8601_MS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
SECTION_PREFIX_RE = re.compile(r"^## ")

WOS_ROOT_DEFAULT = Path(__file__).resolve().parent.parent


def sha_of_section(file_path: Path, section_header: str) -> str | None:
    """Compute SHA-256 of section body bytes per the canonical helper in
    `commands/_shared/substrate-write-protocol.md ## Concrete computation`.

    Body = lines AFTER the `## <section>` header up to (but not including)
    the next `## ` line or EOF, joined by '\n'. Returns None on missing file,
    missing section, or empty body (matches bash helper's `null` sentinel).
    """
    if not file_path.exists():
        return None
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    lines = text.splitlines()
    try:
        # Exact match on `## <section>` line (header includes the `## ` prefix).
        start = lines.index(section_header) + 1
    except ValueError:
        return None
    end = start
    while end < len(lines) and not lines[end].startswith("## "):
        end += 1
    body = "\n".join(lines[start:end])
    if not body:
        return None
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def is_fixable_line(obj: dict) -> bool:
    """A line is fixable if it's the exact pattern the K.5 validator now
    rejects: event in {write, overwrite} AND mode=applied AND sha_after is null.
    """
    return (
        obj.get("event") in ("write", "overwrite")
        and obj.get("mode") == "applied"
        and obj.get("sha_after") is None
    )


def post_fix_check(obj: dict) -> list[str]:
    """Lightweight schema sanity check on a fixed line BEFORE we commit it to
    disk -- catches logic bugs in this script. Subset of K.5 validator rules
    sufficient to ensure the fix didn't introduce a new violation.
    """
    errors: list[str] = []
    sa = obj.get("sha_after")
    if sa is None or not isinstance(sa, str) or not SHA256_HEX_RE.match(sa):
        errors.append(f"sha_after not SHA-256 hex after fix (got {sa!r})")
    ts = obj.get("ts")
    if isinstance(ts, str) and not ISO_8601_MS_RE.match(ts):
        errors.append(f"ts no longer ISO 8601 with ms precision (got {ts!r})")
    section = obj.get("section")
    if not isinstance(section, str) or not SECTION_PREFIX_RE.match(section):
        errors.append(f"section no longer starts with '## ' (got {section!r})")
    return errors


def resolve_log_path(args: argparse.Namespace) -> Path:
    if args.path:
        return Path(args.path)
    if args.task:
        return WOS_ROOT_DEFAULT / "active" / args.task / ".wos" / "VERIFICATION_LOG.jsonl"
    print("ERROR: provide a path or --task <task-folder>", file=sys.stderr)
    sys.exit(2)


def resolve_task_folder(log_path: Path, override: str | None) -> Path:
    """Task folder = parent of .wos/. File paths in JSONL lines are relative
    to this folder. `--task <abs-path>` overrides for non-standard layouts.
    """
    if override:
        p = Path(override)
        return p if p.is_absolute() else (WOS_ROOT_DEFAULT / "active" / override)
    # log_path = <task>/.wos/VERIFICATION_LOG.jsonl  ->  <task>
    return log_path.parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Retroactively fix legacy VERIFICATION_LOG.jsonl lines "
                    "with null sha_after on applied writes."
    )
    ap.add_argument("path", nargs="?", help="path to VERIFICATION_LOG.jsonl")
    ap.add_argument("--task", help="task folder name under active/ "
                                    "(or absolute path); resolves log path")
    ap.add_argument("--task-folder", dest="task_folder_override",
                    help="override task folder for resolving 'file' field "
                         "(default: parent of .wos/)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change; do not rewrite the file")
    args = ap.parse_args()

    log_path = resolve_log_path(args)
    if not log_path.exists():
        print(f"ERROR: log not found: {log_path}", file=sys.stderr)
        return 2

    task_folder = resolve_task_folder(log_path, args.task_folder_override)
    if not task_folder.exists():
        print(f"ERROR: task folder not found: {task_folder}", file=sys.stderr)
        return 2

    print(f"log:         {log_path}")
    print(f"task folder: {task_folder}")
    print(f"dry-run:     {args.dry_run}")
    print()

    # Read all lines preserving original ordering and any non-JSON / blank
    # content. We output the same shape; only fixable JSON lines are mutated.
    raw_lines = log_path.read_text(encoding="utf-8").splitlines(keepends=True)

    out_lines: list[str] = []
    total = 0          # JSON lines seen
    fixable = 0        # matched the legacy pattern
    fixed = 0          # successfully recovered + passed post-fix check
    unfixable = 0      # matched pattern but file/section missing or check failed
    unchanged = 0      # JSON lines that were not the legacy pattern

    for i, raw in enumerate(raw_lines, start=1):
        stripped = raw.strip()
        if not stripped:
            out_lines.append(raw)
            continue

        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            # Preserve non-JSON content verbatim; not our job to validate it.
            out_lines.append(raw)
            continue

        total += 1

        if not isinstance(obj, dict) or not is_fixable_line(obj):
            unchanged += 1
            out_lines.append(raw)
            continue

        fixable += 1
        file_rel = obj.get("file")
        section = obj.get("section")

        if not isinstance(file_rel, str) or not isinstance(section, str):
            unfixable += 1
            print(f"LINE {i}: UNFIXABLE (bad file/section types) "
                  f"{file_rel!r}:{section!r}")
            out_lines.append(raw)
            continue

        target_file = (task_folder / file_rel).resolve()
        new_sha = sha_of_section(target_file, section)

        if new_sha is None:
            unfixable += 1
            reason = ("file missing" if not target_file.exists()
                      else "section missing or empty body")
            print(f"LINE {i}: UNFIXABLE ({reason}) {file_rel}:{section}")
            out_lines.append(raw)
            continue

        # Apply fix, then self-validate before committing to the output buffer.
        obj["sha_after"] = new_sha
        check_errors = post_fix_check(obj)
        if check_errors:
            unfixable += 1
            print(f"LINE {i}: UNFIXABLE (post-fix check failed: "
                  f"{'; '.join(check_errors)}) {file_rel}:{section}")
            out_lines.append(raw)
            continue

        fixed += 1
        # Re-serialize compactly (matches jq -nc style used by emit_audit).
        # Preserve key order from the original line so diffs stay readable:
        # json.loads → dict (insertion-ordered in 3.7+) → json.dumps.
        new_line = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        # Preserve trailing newline shape from the input line.
        out_lines.append(new_line + ("\n" if raw.endswith("\n") else ""))
        print(f"LINE {i}: FIXED ({new_sha[:12]}...) {file_rel}:{section}")

    print()
    print("=== summary ===")
    print(f"total JSON lines: {total}")
    print(f"fixable matches:  {fixable}")
    print(f"fixed:            {fixed}")
    print(f"unfixable:        {unfixable}")
    print(f"unchanged:        {unchanged}")

    if args.dry_run:
        print()
        print("DRY RUN -- file not modified.")
        return 1 if unfixable > 0 else 0

    if fixed == 0 and unfixable == 0:
        print()
        print("No changes to write.")
        return 0

    # Atomic write: .tmp in same directory, then os.replace.
    # Same directory keeps rename atomic on POSIX (same filesystem guarantee).
    tmp_path = log_path.with_suffix(log_path.suffix + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            f.writelines(out_lines)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, log_path)
    except OSError as e:
        # Best-effort cleanup; do not mask the original error.
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        print(f"ERROR: atomic write failed: {e}", file=sys.stderr)
        return 2

    print()
    print(f"Wrote {log_path} (atomic via {tmp_path.name}).")
    return 1 if unfixable > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
