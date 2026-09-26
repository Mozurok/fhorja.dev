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

Digest scope. A line carrying "sha_scope":"file" holds whole-file SHA-256 digests,
the fallback commands/_shared/substrate-digest-fallback.md prescribes when the
per-section helper is unreachable. Those lines chain per FILE and are compared
against the whole file's bytes; every other line is a section digest, as before.
Until 2026-09-23 the validator had no notion of scope and reported every such
line as content-vs-log drift, so an install using the fallback failed its
closure integrity floor on every close (ADR-0224).

An empty log is not a clean log: it prints NOT CHECKED and exits 2.

Usage:
  python3 scripts/verify-log-validator.py <path-to-VERIFICATION_LOG.jsonl>
  python3 scripts/verify-log-validator.py --task <task-folder>
  python3 scripts/verify-log-validator.py --task <task-folder> --check-deletes
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
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

#: Fields a line MAY carry and the validator reads when present. Absence is valid, so a
#: writer that omits them is not wrong; check_substrate_emit_teaches_full_schema reads this
#: set so it does not demand them of the hand-rolled emit.
OPTIONAL_FIELDS = {"sha_scope"}

#: Values of the optional sha_scope field. Absent means section scope.
SHA_SCOPES = {"section", "file"}

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

    sha_scope = obj.get("sha_scope")
    if sha_scope is not None and sha_scope not in SHA_SCOPES:
        errors.append(f"line {idx}: sha_scope {sha_scope!r} not in {sorted(SHA_SCOPES)}")

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


#: A chain position whose current bytes cannot be known from the log alone.
#: Not an error: comparing against it is skipped rather than reported.
INDETERMINATE = object()


def _is_owning_write(obj: dict) -> bool:
    """True for an APPLIED write/overwrite, the only event class that asserts
    'these are now the section's bytes' and can therefore be held to the chain.
    Mode matters as much as event: the real logs carry two mode=proposed entries
    whose event is `overwrite`, and checking those as if they owned the section
    invents a break out of a proposal."""
    return obj.get("mode") == "applied" and obj.get("event") in ("write", "overwrite")


def _is_file_scope(obj: dict) -> bool:
    """True when the line's digests cover the whole file (the digest fallback in
    commands/_shared/substrate-digest-fallback.md), not one section."""
    return obj.get("sha_scope") == "file"


def _advance_chain(last_sec: dict, last_file: dict, key: tuple, obj: dict) -> None:
    """Advance the chain positions after visiting an entry.

    Two tables. `last_sec` is keyed by (file, section) and holds the section digest
    a section-scope write left behind. `last_file` is keyed by file and holds
    (run_id, sha_before, sha_after) from the last file-scope write. Each kind of
    write makes the OTHER table's position for that file unknowable: a section
    write moves the file's bytes by an amount no file digest records, and a file
    digest says nothing about the section's own digest.

    A mode=proposed entry can change a section's bytes WITHOUT owning it: both
    `impact-analysis` and `decision-interview` are told to insert a PROPOSED
    block INSIDE an existing section and to emit no transaction header, because
    ownership stays with the section's owner. Those entries carry event=propose
    and are not required to record a sha_after, so the section's bytes moved by
    an amount the log does not state: the position becomes INDETERMINATE and the
    next applied write is not accused of breaking a chain it did not break.

    The event is the discriminator, not the mode. A mode=proposed entry with any
    OTHER event is a Plan-mode proposal that wrote nothing to disk, so it stays
    fully outside the chain exactly as before and the applied chain continues
    across it. Measured over all 357 real logs: 281 entries are propose, and 7
    are proposed-but-not-propose.

    Chaining THROUGH a proposal (trusting its recorded sha_after as the next
    expected sha_before) was measured and flagged 23 line positions the blind
    walk had not. Whether each is a real inconsistency or an artifact of how
    promotion rewrites the block is a question this function cannot answer, and
    this gate is BLOCKING per `wos/closure-floors.md`, so fixing a
    false-positive class must not introduce a new failing class."""
    file_ = key[0]
    if obj.get("mode") == "proposed":
        if obj.get("event") == "propose":
            last_sec[key] = INDETERMINATE
            last_file[file_] = INDETERMINATE
        return
    if _is_file_scope(obj):
        if _is_owning_write(obj):
            last_file[file_] = (obj.get("run_id"), obj.get("sha_before"), obj.get("sha_after"))
        else:
            last_file[file_] = INDETERMINATE
        last_sec[key] = INDETERMINATE
        return
    last_sec[key] = obj.get("sha_after")
    last_file[file_] = INDETERMINATE


def _chain_mismatches(chain_entries: list[tuple[int, dict]]):
    """Yield (idx, obj, expected) for every applied write/overwrite whose
    sha_before does not continue the chain. `expected` is the previous sha_after.

    Section scope: sha_before must equal the previous sha_after for the same
    (file, section), as it always has.

    File scope: sha_before must equal the previous file-scope sha_after for the
    same file. Inside one run it may instead repeat the previous line's sha_before,
    because the fallback allows a run that writes several sections to digest the
    file once before and once after, so every line of that run carries the same
    pair. A later run must start from where the earlier one ended."""
    last_sec: dict[tuple[str, str], object] = {}
    last_file: dict[str, object] = {}
    for idx, obj in chain_entries:
        file_ = obj.get("file")
        section = obj.get("section")
        if not isinstance(file_, str) or not isinstance(section, str):
            continue
        key = (file_, section)
        if _is_owning_write(obj):
            sb = obj.get("sha_before")
            if _is_file_scope(obj):
                prev = last_file.get(file_, INDETERMINATE)
                if prev is not INDETERMINATE:
                    prev_run, prev_before, prev_after = prev
                    same_run = prev_run is not None and prev_run == obj.get("run_id")
                    if sb != prev_after and not (same_run and sb == prev_before):
                        yield idx, obj, prev_after
            elif key in last_sec:
                prev = last_sec[key]
                if prev is not INDETERMINATE and sb != prev:
                    yield idx, obj, prev
        _advance_chain(last_sec, last_file, key, obj)


def _scope_label(obj: dict) -> str:
    return " at file scope" if _is_file_scope(obj) else ""


def sha_chain_advisories(chain_entries: list[tuple[int, dict]]) -> list[str]:
    """Warn-only sha-chain advisory: an applied write/overwrite whose sha_before
    differs from the previous sha_after recorded for the same (file, section)
    in the log, or for the same file at file scope. Advisory text only; never
    flips the exit code. Walks applied AND proposed entries so a PROPOSED block
    inserted into a section is not invisible to the chain (see _advance_chain)."""
    advisories: list[str] = []
    for idx, obj, prev in _chain_mismatches(chain_entries):
        advisories.append(
            f"line {idx}: sha_before {obj.get('sha_before')!r} differs from previous sha_after {prev!r} for {obj.get('file')} {obj.get('section')!r}{_scope_label(obj)} (sha-chain advisory)"
        )
    return advisories


def _sha_of_section_port(path: Path, header: str) -> str:
    """Byte-exact port of emit-substrate-write.sh sha_of_section (S1, 2026-07-18).
    Operates on BYTES (not str) so Python universal-newline translation cannot
    diverge from awk's RS='\\n'. Must stay byte-identical to the emitter's awk."""
    try:
        data = path.read_bytes()
    except OSError:
        return "null"
    recs = data.split(b"\n")
    if recs and recs[-1] == b"":       # awk: a trailing '\n' yields no empty final record
        recs.pop()
    hb = header.encode("utf-8")
    body: list[bytes] = []
    cap = False
    for ln in recs:
        if not cap:
            if ln == hb:               # awk: $0 == h { f=1; next }
                cap = True
            continue
        if ln.startswith(b"## "):      # awk: f && /^## / { exit }
            break
        if ln.startswith(b"<!-- wos:write "):  # awk: f && /^<!-- wos:write / { next }
            continue
        body.append(ln)
    while body and body[-1] == b"":    # $(...) strips all trailing newlines from awk output
        body.pop()
    joined = b"\n".join(body)
    if joined == b"":                  # bash: [[ -z "$body" ]] -> 'null'
        return "null"
    return hashlib.sha256(joined).hexdigest()


def sha_chain_breaks(chain_entries: list[tuple[int, dict]], cutover_ts: str) -> list[str]:
    """Post-cutover sha-chain break (S1, opt-in): same chain walk as
    sha_chain_advisories, but a break is REPORTED (not just advised) when the
    current applied write/overwrite is at or after cutover_ts. The chain is
    built over ALL applied AND proposed entries so 'previous sha_after' stays
    correct: a PROPOSED block inserted into a section moves its bytes, and a
    walk blind to that reports a break where the writer obeyed its contract."""
    breaks: list[str] = []
    for idx, obj, prev in _chain_mismatches(chain_entries):
        ts = obj.get("ts")
        if isinstance(ts, str) and ts >= cutover_ts:
            breaks.append(
                f"line {idx}: sha_before {obj.get('sha_before')!r} != previous sha_after {prev!r} for {obj.get('file')} {obj.get('section')!r}{_scope_label(obj)} (post-cutover sha-chain break)"
            )
    return breaks


def delete_orphan_findings(applied_entries: list[tuple[int, dict]], task_dir: Path, cutover_ts: str | None = None) -> list[str]:
    """Delete-orphan cross-check (ADR-0101): a (file, section) whose last
    applied event is write/overwrite, whose file exists at task_dir, but whose
    '## ' heading line is gone from the file on disk. Files that do not
    resolve at task_dir are skipped."""
    last_event: dict[tuple[str, str], tuple[int, object, object]] = {}
    for idx, obj in applied_entries:
        file_ = obj.get("file")
        section = obj.get("section")
        if not isinstance(file_, str) or not isinstance(section, str):
            continue
        last_event[(file_, section)] = (idx, obj.get("event"), obj.get("ts"))

    findings: list[str] = []
    for (file_, section), (idx, event, ts) in last_event.items():
        if event not in ("write", "overwrite"):
            continue
        if cutover_ts is not None and (not isinstance(ts, str) or ts < cutover_ts):
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


def _sha_of_file(path: Path) -> str:
    """Whole-file SHA-256, the same bytes `shasum -a 256 <file>` digests."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "null"


def content_sha_findings(chain_entries: list[tuple[int, dict]], task_dir: Path, cutover_ts: str | None = None) -> list[str]:
    """Content-vs-log SHA drift (S1, opt-in): for the last applied write/overwrite
    per (file, section) whose recorded sha_after is a real hash, recompute the
    section's current bytes on disk and flag when they disagree. Catches a stub
    that keeps a header but gutted the body. Post-cutover only when cutover_ts set.

    Walks applied AND proposed entries. When the LAST entry for a section is a
    PROPOSED block (event=propose), the section's bytes on disk legitimately
    include content the owner never applied, so the event filter below skips the
    key: disk cannot be compared against an applied sha while a proposal sits on
    top of it. That is a deliberate loss of coverage for pending proposals, and
    it is preferable to reporting drift against a writer that did as it was told.

    File scope ("sha_scope":"file"): the digest covers the whole file, so it is
    compared against the whole file, and only when that line is the last entry
    to touch the file. Any later write to the file, to any section and at any
    scope, moves the file's bytes past what the line recorded, so an earlier
    file-scope line has nothing left to be compared with. A section-scope line
    whose section was last written at file scope is skipped at section scope for
    the same reason."""
    last_write: dict[tuple[str, str], tuple[int, object, dict]] = {}
    last_touch: dict[str, tuple[int, dict]] = {}
    for idx, obj in chain_entries:
        file_ = obj.get("file")
        section = obj.get("section")
        if not isinstance(file_, str) or not isinstance(section, str):
            continue
        last_write[(file_, section)] = (idx, obj.get("event"), obj)
        # A proposed entry that is not event=propose wrote nothing to disk.
        if obj.get("mode") == "proposed" and obj.get("event") != "propose":
            continue
        last_touch[file_] = (idx, obj)

    def in_window(obj: dict) -> bool:
        ts = obj.get("ts")
        return cutover_ts is None or (isinstance(ts, str) and ts >= cutover_ts)

    findings: list[str] = []
    for (file_, section), (idx, event, obj) in last_write.items():
        if not _is_owning_write(obj) or _is_file_scope(obj):
            continue
        recorded = obj.get("sha_after")
        if not isinstance(recorded, str):
            continue
        if not in_window(obj):
            continue
        path = task_dir / file_
        if not path.is_file():
            continue
        actual = _sha_of_section_port(path, section)
        if actual != recorded:
            findings.append(
                f"{file_} {section!r} (last applied: line {idx}): recorded sha_after {recorded} != recomputed {actual} (content-vs-log drift)"
            )

    for file_, (idx, obj) in last_touch.items():
        if not _is_owning_write(obj) or not _is_file_scope(obj):
            continue
        recorded = obj.get("sha_after")
        if not isinstance(recorded, str) or not in_window(obj):
            continue
        path = task_dir / file_
        if not path.is_file():
            continue
        actual = _sha_of_file(path)
        if actual != recorded:
            findings.append(
                f"{file_} (last applied at file scope: line {idx}): recorded sha_after {recorded} != recomputed {actual} (content-vs-log drift)"
            )
    return findings


def resolve_target(args: argparse.Namespace) -> Path:
    if args.path:
        return Path(args.path)
    if args.task:
        # The task repository is where the caller stands, not where this file sits.
        # Resolving from the script's own location read this clone's projects/ on
        # every install, which holds none of the user's tasks (ADR-0224).
        repo_root = Path.cwd()
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
    p.add_argument("--task", help="task folder name under projects/<client>__<project>/active/, resolved from the current directory")
    p.add_argument("--max-errors", type=int, default=50)
    p.add_argument(
        "--check-deletes",
        action="store_true",
        help="promote delete-orphan findings (ADR-0101) from warnings to errors",
    )
    p.add_argument(
        "--cutover-ts",
        default=os.environ.get("WOS_CUTOVER_TS"),
        help="ISO-8601 cutover ts (S1, opt-in): grandfathers pre-cutover delete-orphans and activates the post-cutover sha-chain + content-vs-log checks. --check-deletes promotes all three to errors.",
    )
    args = p.parse_args()
    cutover = args.cutover_ts

    target = resolve_target(args)
    if not target.exists():
        print(f"ERROR: not found: {target}", file=sys.stderr)
        return 2

    total = 0
    bad = 0
    all_errors: list[str] = []
    applied_entries: list[tuple[int, dict]] = []
    # Applied AND proposed, in line order: the chain and content checks need
    # every entry that can move a section's bytes, not only the owning writes.
    chain_entries: list[tuple[int, dict]] = []

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
            if isinstance(obj, dict) and obj.get("mode") in ("applied", "proposed"):
                chain_entries.append((i, obj))

    if total == 0:
        # A log with no lines records no write, so nothing was checked. It used to
        # print `lines: 0` and OK with exit 0, a pass on a log nobody wrote to.
        print(f"file: {target}")
        print("NOT CHECKED: log has no lines")
        return 2

    advisories = sha_chain_advisories(chain_entries)

    delete_orphans: list[str] = []
    content_findings: list[str] = []
    chain_breaks: list[str] = []
    if target.name == "VERIFICATION_LOG.jsonl" and target.parent.name == ".wos":
        task_dir = target.parent.parent
        delete_orphans = delete_orphan_findings(applied_entries, task_dir, cutover)
        if cutover:
            content_findings = content_sha_findings(chain_entries, task_dir, cutover)
    if cutover:
        chain_breaks = sha_chain_breaks(chain_entries, cutover)

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

    if chain_breaks:
        print()
        print("POST-CUTOVER SHA-CHAIN BREAKS (--check-deletes promotes to errors):")
        for b in chain_breaks:
            print(f"  {b}")

    if content_findings:
        print()
        print("CONTENT-VS-LOG SHA DRIFT (--check-deletes promotes to errors):")
        for c in content_findings:
            print(f"  {c}")

    if all_errors:
        print()
        print("ERRORS:")
        for e in all_errors[: args.max_errors]:
            print(f"  {e}")
        if len(all_errors) > args.max_errors:
            print(f"  ... and {len(all_errors) - args.max_errors} more")
        return 1
    if args.check_deletes and (delete_orphans or content_findings or chain_breaks):
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
