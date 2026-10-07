#!/usr/bin/env python3
"""Explicit source binding and immutable metadata for trusted local attempts."""
import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def strict_json(raw):
    def reject(value):
        raise ValueError("nonfinite JSON value")
    value = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject)
    canonical(value)  # Also rejects overflowed exponent literals such as 1e999.
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def same(left, right):
    """Object order is immaterial; array order and JSON numeric types are not."""
    try:
        return canonical(left) == canonical(right)
    except (ValueError, TypeError):
        return False


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def snapshot(files):
    result = {}
    for value in files:
        path = Path(value)
        if path.is_symlink() or not path.is_file():
            raise ValueError("source must be an existing regular file")
        key = str(path.resolve())
        if key in result:
            raise ValueError("duplicate source path")
        result[key] = digest(path.read_bytes())
    return dict(sorted(result.items()))


def fixture(path, features=None):
    raw = Path(path).read_bytes()
    spec = strict_json(raw)
    cases = spec.get("cases") if isinstance(spec, dict) else None
    if (not isinstance(spec, dict) or type(spec.get("schema_version")) is not int
            or spec["schema_version"] != 1 or not isinstance(cases, list) or not cases
            or any(not isinstance(c, dict) or not isinstance(c.get("case_id"), str)
                   or not c["case_id"].strip() or "input" not in c or "expected" not in c
                   or (features is not None and c.get("feature") not in features) for c in cases)
            or len({c["case_id"] for c in cases}) != len(cases)):
        raise ValueError("invalid acceptance fixture")
    return spec, digest(raw)


def evaluation_snapshot(cases_path, source_files, evaluator_files):
    return {"fixture": snapshot([cases_path]), "source": snapshot(source_files),
            "evaluator": snapshot(evaluator_files)}


def adapter_declared(command, source_files):
    """Bind a trusted script entry, without guessing module or inline-code imports."""
    declared = {str(Path(p).resolve()) for p in source_files}
    if not isinstance(command, list) or not command or not all(isinstance(c, str) and c for c in command):
        return False
    entry = Path(command[0])
    interpreter = re.fullmatch(r"python(?:\d+(?:\.\d+)*)?|node|bash|sh|zsh|dash", entry.name)
    if interpreter:
        if not entry.is_absolute() or len(command) < 2 or command[1].startswith("-"):
            return False  # Reject inline and module execution even if the interpreter was declared.
        script = Path(command[1])
        return script.is_absolute() and script.is_file() and str(script.resolve()) in declared
    return entry.is_absolute() and entry.is_file() and str(entry.resolve()) in declared


def evaluation_binding(before, cases_path, source_files, evaluator_files, command):
    try:
        after = evaluation_snapshot(cases_path, source_files, evaluator_files)
    except (OSError, ValueError):
        after = None
    return {"before": before, "after": after, "candidate_command": command,
            "bound": bool(before["source"]) and same(before, after) and adapter_declared(command, source_files)}


def validate_binding(binding, cases_path, source_files, evaluator_files, command=None):
    try:
        current = evaluation_snapshot(cases_path, source_files, evaluator_files)
        return (isinstance(binding, dict) and binding.get("bound") is True
                and isinstance(binding.get("candidate_command"), list) and bool(binding["candidate_command"])
                and all(isinstance(c, str) and bool(c) for c in binding["candidate_command"])
                and adapter_declared(binding["candidate_command"], source_files)
                and bool(current["source"]) and same(binding.get("before"), current)
                and same(binding.get("after"), current)
                and (command is None or same(binding.get("candidate_command"), command)))
    except (OSError, ValueError, TypeError):
        return False


POLICY_FIELDS = {"provider", "model", "effort", "timeout_seconds", "max_calls",
                 "max_actual_usd", "max_equivalent_usd", "limit_mode",
                 "accept_last_response_overrun"}
ROLES = {"driver", "prompt", "settings", "scorer", "cases", "source"}


def validate_policy(policy):
    if (not isinstance(policy, dict) or set(policy) != {"values", "sources"}
            or not isinstance(policy["values"], dict) or not isinstance(policy["sources"], dict)
            or not POLICY_FIELDS <= set(policy["values"])
            or set(policy["values"]) != set(policy["sources"])):
        raise ValueError("fully resolved policy and per-field provenance required")
    values = policy["values"]
    if any(not isinstance(v, str) or not v.strip() for v in policy["sources"].values()):
        raise ValueError("policy provenance must be explicit")
    for key in ("provider", "model", "effort"):
        if not isinstance(values[key], str) or not values[key].strip():
            raise ValueError("effective model settings required")
    if (type(values["max_calls"]) is not int or values["max_calls"] <= 0
            or type(values["accept_last_response_overrun"]) is not bool
            or values["limit_mode"] not in ("strict", "monitored", "subscription-only")):
        raise ValueError("invalid effective limits")
    for key in ("timeout_seconds", "max_actual_usd", "max_equivalent_usd"):
        value = values[key]
        if value is None and key != "timeout_seconds":
            continue  # Unknown or inapplicable limit remains explicit, with its source.
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("finite positive effective limit required")
    canonical(policy)
    return policy


def resolve_policy(base, overrides=None):
    """Resolve supplied value/source entries; never infer provider defaults."""
    entries = dict(base)
    entries.update(overrides or {})
    if any(not isinstance(v, dict) or set(v) != {"value", "source"} for v in entries.values()):
        raise ValueError("policy entries require value and source")
    return validate_policy({"values": {k: v["value"] for k, v in entries.items()},
                            "sources": {k: v["source"] for k, v in entries.items()}})


def artifact_snapshot(artifacts):
    if not isinstance(artifacts, dict) or set(artifacts) != ROLES:
        raise ValueError("driver, prompt, settings, scorer, cases and source roles required")
    result = {}
    for role, files in artifacts.items():
        if not isinstance(files, list) or not files:
            raise ValueError("each artifact role requires an explicit nonempty source set")
        result[role] = snapshot(files)
    return result


def write_new(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    with Path(path).open("xb") as stream:
        stream.write(raw)
    return digest(raw)


def freeze(path, attempt_id, policy, artifacts):
    if not isinstance(attempt_id, str) or not attempt_id.strip():
        raise ValueError("attempt identity required")
    record = {"schema_version": 1, "attempt_id": attempt_id,
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "effective_policy": validate_policy(policy),
              "artifacts": artifact_snapshot(artifacts)}
    sha = write_new(path, record)
    return {"path": str(Path(path).resolve()), "sha256": sha, "attempt_id": attempt_id}


def verify(binding, check_artifacts=True):
    if (not isinstance(binding, dict) or set(binding) != {"path", "sha256", "attempt_id"}
            or not all(isinstance(v, str) and v.strip() for v in binding.values())):
        raise ValueError("independent attempt path, digest and identity required")
    path = Path(binding["path"])
    if path.is_symlink():
        raise ValueError("attempt symlink refused")
    raw = path.read_bytes()
    if digest(raw) != binding["sha256"]:
        raise ValueError("attempt metadata changed")
    record = strict_json(raw)
    if (not isinstance(record, dict) or type(record.get("schema_version")) is not int
            or record["schema_version"] != 1 or record.get("attempt_id") != binding["attempt_id"]
            or not isinstance(record.get("artifacts"), dict) or set(record["artifacts"]) != ROLES):
        raise ValueError("invalid attempt record")
    validate_policy(record.get("effective_policy"))
    for files in record["artifacts"].values():
        if (not isinstance(files, dict) or not files
                or any(not isinstance(p, str) or not isinstance(sha, str) or len(sha) != 64
                       for p, sha in files.items())):
            raise ValueError("invalid artifact manifest")
    if check_artifacts:
        artifacts = {role: list(files) for role, files in record["artifacts"].items()}
        if not same(record["artifacts"], artifact_snapshot(artifacts)):
            raise ValueError("attempt artifacts changed")
    return record


def verify_evaluation_inputs(binding):
    """Verify frozen non-source inputs after legitimate implementation changes."""
    record = verify(binding, check_artifacts=False)
    for role in ROLES - {"source"}:
        if not same(record["artifacts"][role], snapshot(list(record["artifacts"][role]))):
            raise ValueError("attempt evaluation inputs changed")
    return record


def guarded_launch(binding, callback):
    verify(binding)
    return callback()


def seal_evidence(path, binding, artifacts, source_files):
    """Capture evaluation output separately from the immutable pre-launch record."""
    record = verify_evaluation_inputs(binding)
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError("captured evidence required")
    receipt = {"schema_version": 1, "attempt_id": binding["attempt_id"],
               "attempt_sha256": binding["sha256"], "source": snapshot(source_files),
               "artifacts": {name: snapshot(files) for name, files in artifacts.items()}}
    if not receipt["source"] or any(not v for v in receipt["artifacts"].values()):
        raise ValueError("nonempty source and evidence sets required")
    return {"path": str(Path(path).resolve()), "sha256": write_new(path, receipt)}


def verify_evidence(receipt_binding, binding, artifacts, source_files):
    record = verify_evaluation_inputs(binding)
    path = Path(receipt_binding["path"])
    raw = path.read_bytes()
    if path.is_symlink() or digest(raw) != receipt_binding["sha256"]:
        raise ValueError("evidence receipt changed")
    receipt = strict_json(raw)
    expected = {"schema_version": 1, "attempt_id": binding["attempt_id"],
                "attempt_sha256": binding["sha256"], "source": snapshot(source_files),
                "artifacts": {name: snapshot(files) for name, files in artifacts.items()}}
    if not expected["source"] or not same(receipt, expected):
        raise ValueError("evidence identity, source or artifacts changed")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("freeze", "verify", "seal"))
    parser.add_argument("request", type=Path, help="explicit local JSON request")
    args = parser.parse_args()
    request = strict_json(args.request.read_bytes())
    if args.operation == "freeze":
        result = freeze(**request)
    elif args.operation == "seal":
        result = seal_evidence(**request)
    else:
        result = verify(request)
    print(canonical(result))


if __name__ == "__main__":
    main()
