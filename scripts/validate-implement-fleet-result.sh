#!/usr/bin/env bash
# Read-only native pre-merge gate. All identities come from explicit arguments.
set -euo pipefail
exec python3 - "$@" <<'PY'
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def refuse(message):
    raise ValueError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            refuse("duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path):
    if not path.is_file():
        refuse("not found: input " + str(path))
    raw = path.read_bytes()
    value = json.loads(raw, object_pairs_hook=unique_object,
                       parse_constant=lambda x: refuse("nonfinite JSON value: " + x))
    if not isinstance(value, dict):
        refuse("input must be a JSON object")
    return value, hashlib.sha256(raw).hexdigest()


def string(obj, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        refuse("missing or invalid string: " + key)
    return value


def strings(obj, key):
    value = obj.get(key)
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() or "\x00" in x for x in value):
        refuse("missing or invalid string array: " + key)
    if len(set(value)) != len(value):
        refuse("duplicate array entry: " + key)
    return value


def relative(path):
    # Git names and declared scopes use canonical POSIX paths.
    if path.startswith("/") or "\\" in path or any(p in ("", ".", "..") for p in path.split("/")):
        refuse("noncanonical relative path: " + path)
    if path.split("/")[0] in (".git", ".fleet-out"):
        refuse("out-of-scope return or Git path: " + path)
    return path


def git(root, *args):
    result = subprocess.run(["git", "--no-replace-objects", "-C", str(root), *args],
                            capture_output=True, check=False)
    if result.returncode:
        refuse("Git check failed: " + " ".join(args) + ": " + result.stderr.decode(errors="replace").strip())
    return result.stdout


def git_text(root, *args):
    return git(root, *args).decode().strip()


def commit_id(value, label):
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
        refuse("expected full commit ID: " + label)
    return value


def validate(payload, expected):
    worker = string(expected, "worker_id")
    slice_id = string(expected, "slice_id")
    if string(payload, "worker_id") != worker or string(payload, "slice_id") != slice_id:
        refuse("worker or slice identity mismatch")
    status = string(payload, "status")
    allowed = ("satisfied", "needs_revision", "max_iterations_reached", "scope_violation", "failed", "interrupted", "timed_out")
    if status not in allowed:
        refuse("unknown worker status")
    touched = strings(payload, "files_touched")
    for path in touched:
        relative(path)
    if payload.get("build_status") not in ("pass", "fail", "not_run"):
        refuse("invalid build_status")
    if payload.get("test_status") not in ("pass", "fail", "not_run", "partial"):
        refuse("invalid test_status")
    for key in ("out_of_scope_writes", "residual_risks"):
        if key in payload:
            strings(payload, key)
    for key in ("slice_note_path", "worktree_path", "commit_sha", "diff_summary"):
        if key in payload:
            string(payload, key)
    if "commit_sha" in payload:
        commit_id(payload["commit_sha"], "commit_sha")
    if "error" in payload:
        error = payload["error"]
        if not isinstance(error, dict):
            refuse("invalid error object")
        if string(error, "error_class") not in ("tool-failure", "missing-input", "contract-violation", "timeout", "unknown"):
            refuse("invalid error.error_class")
        string(error, "error_message")
        string(error, "error_evidence")
        if type(error.get("recoverable")) is not bool:
            refuse("invalid error.recoverable")
    if status == "failed" and "error" not in payload:
        refuse("failed return requires error.error_class")
    if status != "satisfied":
        return {"worker_id": worker, "slice_id": slice_id, "status": status, "merge_ready": False}
    if "error" in payload or payload.get("out_of_scope_writes", []):
        refuse("satisfied return contradicts error or out_of_scope_writes")
    if payload["build_status"] == "fail" or payload["test_status"] in ("fail", "partial"):
        refuse("satisfied return contradicts check failure")

    worktree = Path(string(expected, "worktree_path")).resolve(strict=True)
    product = Path(string(expected, "product_repo_path")).resolve(strict=True)
    if worktree == product:
        refuse("worker must have a distinct worktree")
    if Path(string(payload, "worktree_path")).resolve(strict=True) != worktree:
        refuse("worktree identity mismatch")
    for root in (product, worktree):
        if Path(git_text(root, "rev-parse", "--show-toplevel")).resolve() != root:
            refuse("expected path is not a Git worktree root")
    def common(root):
        return (root / git_text(root, "rev-parse", "--git-common-dir")).resolve()
    if common(product) != common(worktree):
        refuse("worktree does not belong to product repository")
    base = commit_id(string(expected, "base_ref"), "base_ref")
    tip = commit_id(string(payload, "commit_sha"), "commit_sha")
    for value in (base, tip):
        if git_text(worktree, "rev-parse", "--verify", value + "^{commit}") != value:
            refuse("commit identity mismatch")
    if git_text(worktree, "rev-parse", "HEAD") != tip:
        refuse("returned commit is not worktree HEAD")
    git(worktree, "merge-base", "--is-ancestor", base, tip)
    commits = git_text(worktree, "rev-list", "--reverse", base + ".." + tip).splitlines()
    if not commits:
        refuse("worker produced no commit after base")
    parent = base
    changed = set()
    for commit in commits:
        parents = git_text(worktree, "rev-list", "--parents", "-n", "1", commit).split()
        if parents != [commit, parent]:
            refuse("worker commit sequence is not linear from base")
        names = git(worktree, "diff", "--name-only", "--no-renames", "-z", parent, commit).split(b"\0")
        changed.update(relative(name.decode()) for name in names if name)
        parent = commit
    if changed != set(touched):
        refuse("files_touched does not equal actual committed paths")
    scope = strings(expected, "scope_files")
    if not scope:
        refuse("empty expected scope_files")
    for pattern in scope:
        relative(pattern)
    for path in changed:
        if not any(fnmatch.fnmatchcase(path, pattern) for pattern in scope):
            refuse("committed path outside scope: " + path)
    # No unstaged or staged tracked edits may differ from the returned commit.
    for entry in git(worktree, "ls-files", "-v", "-z").split(b"\0"):
        if not entry:
            continue
        if entry[:1].islower() or entry[:1] == b"S":
            refuse("index hides tracked paths (assume-unchanged or skip-worktree)")
        if entry[2:].startswith(b".fleet-out/"):
            refuse("committed return folder must not be present")
    if git(worktree, "diff", "--name-only", "HEAD", "--"):
        refuse("worktree has uncommitted tracked edits")
    for name in git(worktree, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
        if name and not name.decode().startswith(".fleet-out/"):
            refuse("worktree has uncommitted non-return files")
    note_name = string(payload, "slice_note_path")
    note = Path(note_name)
    if not note.is_absolute():
        note = worktree / note
    resolved = note.resolve(strict=True)
    return_root = worktree / ".fleet-out"
    if return_root.is_symlink() or return_root not in resolved.parents or note.is_symlink():
        refuse("slice note escapes worker return folder")
    assigned_note = Path(string(expected, "slice_note_path"))
    if not assigned_note.is_absolute():
        assigned_note = worktree / assigned_note
    if resolved != assigned_note.resolve(strict=True):
        refuse("slice note identity mismatch")
    if resolved.suffix != ".md" or not resolved.is_file() or not resolved.read_bytes().strip():
        refuse("missing or empty slice note")
    return {"worker_id": worker, "slice_id": slice_id, "status": status, "merge_ready": True,
            "worktree_path": str(worktree), "base_ref": base, "commit_sha": tip,
            "commit_sequence": commits, "files_touched": sorted(changed),
            "slice_note_path": str(resolved),
            "slice_note_sha256": hashlib.sha256(resolved.read_bytes()).hexdigest()}


try:
    if len(sys.argv) != 3:
        refuse("not checked: usage validate-implement-fleet-result.sh <payload.json> <expected.json>")
    if Path(sys.argv[1]).is_symlink():
        refuse("payload carrier must not be a symlink")
    payload, payload_hash = read_json(Path(sys.argv[1]))
    expected, expected_hash = read_json(Path(sys.argv[2]))
    if Path(sys.argv[1]).resolve() != Path(string(expected, "payload_path")).resolve():
        refuse("payload carrier identity mismatch")
    result = validate(payload, expected)
    result.update(payload_sha256=payload_hash, expected_sha256=expected_hash)
    print(json.dumps(result, sort_keys=True))
    sys.exit(0 if result["merge_ready"] else 3)
except (ValueError, OSError, UnicodeError) as exc:
    print("Fleet result: " + str(exc), file=sys.stderr)
    sys.exit(2)
PY
