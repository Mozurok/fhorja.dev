"""Post-freeze batch boundary checks, separate from primary pilot grades."""
import argparse
import builtins
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from attempt import (canonical, digest, fixture, same, strict_json,
                     evaluation_snapshot, evaluation_binding, validate_binding, snapshot)
from behavior import stop_candidate
from pilot_fixtures import PUBLIC_IO
from pilot_oracle import BATCH_STARTUP, EVALUATORS as PRIMARY_EVALUATORS, file_bytes, retained_envelope, run, sources

CASES = Path(__file__).with_name("fixtures") / "pilot_supplementary_cases.json"
EVALUATORS = [Path(__file__).resolve(), *PRIMARY_EVALUATORS,
              Path(__file__).with_name("fixtures") / "reference_pilot.py"]
REQUIRED = {"receipt-boundary", "binary-preimage", "binary-external-edit"}
SELECTION = "post-freeze-supplementary"
UNRELATED = b"user-owned\x00draft"


def load_cases(path):
    spec, sha = fixture(path, {"batch"})
    if spec.get("selection") != SELECTION or {c["case_id"] for c in spec["cases"]} != REQUIRED:
        raise ValueError("complete post-freeze supplementary cases required")
    for case in spec["cases"]:
        payload = case["input"]
        if (not isinstance(payload, dict) or set(payload) != {"operation_id", "outputs"}
                or not isinstance(payload["operation_id"], str) or not payload["operation_id"].strip()
                or not isinstance(payload["outputs"], dict) or "first.txt" not in payload["outputs"]
                or len(payload["outputs"]) < 2 or any(not isinstance(v, str) for v in payload["outputs"].values())):
            raise ValueError("valid supplementary operation required")
        expected = "replayed" if case["case_id"] == "receipt-boundary" else "applied" if case["case_id"] == "binary-preimage" else "conflict"
        if not same(case["expected"], {"status": expected}):
            raise ValueError("supplementary status contract changed")
        if case["case_id"] != "receipt-boundary":
            before = bytes.fromhex(case["preimage_hex"])
            try:
                before.decode("utf-8")
            except UnicodeDecodeError:
                pass
            else:
                raise ValueError("non-UTF8 preimage required")
        if case["case_id"] == "binary-external-edit":
            if case["edit_hex"] in (case["preimage_hex"], payload["outputs"]["first.txt"].encode().hex()):
                raise ValueError("distinct external edit required")
            bytes.fromhex(case["edit_hex"])
    return spec, sha


def paused(command, request, cwd, output, witness, target, timeout, env):
    """Kill only after witnessing this exact public replacement in a live child."""
    child_env = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "LANG", "LC_ALL", "TMPDIR")}
    child_env.update(env, PYTHONDONTWRITEBYTECODE="1", PILOT_PAUSE_PATH=target,
                     PILOT_WITNESS=str(witness))
    # File-backed streams cannot stop a legal diagnostic writer at pipe capacity.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        p = subprocess.Popen(command, cwd=cwd, env=child_env, stdin=subprocess.PIPE,
                             stdout=stdout, stderr=stderr, text=True,
                             start_new_session=os.name == "posix")
        seen, before, alive, error = None, {}, False, None
        try:
            p.stdin.write(canonical(request))
            p.stdin.close()
            p.stdin = None
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline and p.poll() is None:
                try:
                    seen = strict_json(witness.read_bytes())
                    break
                except (OSError, ValueError):
                    time.sleep(.005)
            before = file_bytes(output)
            alive = p.poll() is None
        except (OSError, ValueError, TypeError) as exc:
            error = type(exc).__name__
        finally:
            if p.stdin is not None:
                try:
                    p.stdin.close()
                except OSError:
                    pass
                p.stdin = None
            cleanup = stop_candidate(p)
            try:
                p.communicate(timeout=.5)
            except (subprocess.TimeoutExpired, OSError, ValueError):
                error = error or "cleanup capture failure"
        stdout.seek(0)
        stderr.seek(0)
        out_raw, err_raw = stdout.read(), stderr.read()
    return {"command": command, "request": request, "pid": p.pid,
            "stdout": out_raw.decode("utf-8", errors="replace"),
            "stderr": err_raw.decode("utf-8", errors="replace"),
            "stdout_hex": out_raw.hex(), "stderr_hex": err_raw.hex(),
            "exit_code": p.returncode, "error": error,
            "witness": seen, "files_before_kill": before, "alive_at_snapshot": alive,
            "cleanup_complete": cleanup}


def _status(call, command):
    envelope = retained_envelope(call, command)
    if set(envelope) != {"result"}:
        return None
    result = envelope["result"]
    return result.get("status") if isinstance(result, dict) and set(result) == {"status"} else None


def _receipt(fs):
    value = strict_json(bytes.fromhex(fs["receipts.json"])) if "receipts.json" in fs else {"completed": []}
    ids = value["completed"]
    if (set(value) != {"completed"} or not isinstance(ids, list)
            or any(not isinstance(x, str) or not x.strip() for x in ids) or len(set(ids)) != len(ids)):
        raise ValueError("once-only receipt required")
    return ids


def derive(row, case, command):
    """Derive checks from raw calls and byte snapshots, never reported pass flags."""
    calls = row["calls"]
    request = row["request"]
    payload = case["input"]
    kind = case["case_id"]
    expected_initial = {"unrelated.txt": UNRELATED.hex()}
    if kind != "receipt-boundary":
        expected_initial["first.txt"] = case["preimage_hex"]
    checks = {"initial_bytes": same(row["initial_bytes"], expected_initial),
              "request": isinstance(request.get("root"), str) and Path(request["root"]).is_absolute()
              and same({k: v for k, v in request.items() if k != "root"}, payload),
              "two_real_calls": len(calls) == 2,
              "immutable_public_io": row["immutable_public_io"] is True,
              "startup_hook": row["startup_hook_sha256"] == digest(BATCH_STARTUP.encode()),
              "public_writes": bool(row["write_trace"]) and all(x.get("via_public_io") is True for x in row["write_trace"]),
              "unrelated": row["filesystem"].get("unrelated.txt") == UNRELATED.hex()}
    if not checks["request"] or not checks["two_real_calls"]:
        raise ValueError("incomplete or contradictory invocation capture")
    first, last = calls
    checks["commands_and_requests"] = all(same(c["command"], command) and same(c["request"], request) for c in calls)
    if not checks["commands_and_requests"]:
        raise ValueError("contradictory invocation capture")
    checks["fresh_process"] = all(type(c["pid"]) is int and c["pid"] > 0 for c in calls) and first["pid"] != last["pid"]
    final_status = _status(last, command)
    if kind == "binary-preimage":
        observed = _status(first, command)
        checks["completed_replay"] = final_status == "replayed"
        checks["no_replay_writes"] = same(row["before_retry"], row["filesystem"])
    else:
        target = "receipts.json" if kind == "receipt-boundary" else "first.txt"
        # paused() cannot publish a decoded envelope. An unsupported error is
        # contradictory capture metadata, not an ordinary candidate rejection.
        error = first.get("error")
        error_type = getattr(builtins, error, None) if isinstance(error, str) else None
        supported_error = (error is None or error == "cleanup capture failure"
                           or isinstance(error_type, type) and issubclass(error_type, (OSError, ValueError, TypeError)))
        if ("envelope" in first or not supported_error
                or type(first.get("pid")) is not int or first["pid"] <= 0
                or type(first.get("exit_code")) is not int
                or type(first.get("alive_at_snapshot")) is not bool
                or type(first.get("cleanup_complete")) is not bool
                or any(not isinstance(first.get(name), str) for name in ("stdout", "stderr"))):
            raise ValueError("invalid paused capture metadata")
        if error is not None and error != "cleanup capture failure" and first["alive_at_snapshot"]:
            raise ValueError("observation failure precedes the live snapshot")
        witness = first.get("witness")
        prior = first.get("files_before_kill", {})
        checks["paused_streams"] = all(bytes.fromhex(first[name + "_hex"]).decode("utf-8", errors="replace") == first[name]
                                      for name in ("stdout", "stderr"))
        if not checks["paused_streams"]:
            raise ValueError("contradictory paused stream bytes")
        checks["actual_publication"] = (isinstance(witness, dict) and witness.get("pid") == first["pid"]
            and type(witness.get("pid")) is int and witness.get("path") == target
            and isinstance(witness.get("body"), str)
            and prior.get(target) == witness["body"].encode().hex()
            and first.get("alive_at_snapshot") is True)
        checks["terminated"] = (type(first["exit_code"]) is int and first["exit_code"] != 0
                                and first.get("cleanup_complete") is True and first["error"] is None)
        observed = final_status
        if kind == "receipt-boundary":
            checks["all_outputs_before_kill"] = all(prior.get(path) == body.encode().hex() for path, body in payload["outputs"].items())
            checks["once_only_before_kill"] = _receipt(prior) == [payload["operation_id"]]
            checks["before_retry_bound"] = same(row["before_retry"], prior)
            checks["no_replay_writes"] = same(prior, row["filesystem"])
        else:
            protected = dict(prior, **{"first.txt": case["edit_hex"]})
            checks["published_target"] = prior.get("first.txt") == payload["outputs"]["first.txt"].encode().hex()
            checks["no_early_receipt"] = _receipt(prior) == []
            checks["before_retry_bound"] = same(row["before_retry"], protected)
            checks["conflict_preserves_bytes"] = same(protected, row["filesystem"])
    if kind != "binary-external-edit":
        checks["outputs"] = all(row["filesystem"].get(path) == body.encode().hex() for path, body in payload["outputs"].items())
    checks["receipt"] = _receipt(row["filesystem"]) == ([] if kind == "binary-external-edit" else [payload["operation_id"]])
    return checks, {"status": observed} if observed is not None else None


def batch_case(root, command, case, temp, timeout):
    output = temp / case["case_id"]
    output.mkdir()
    (output / "unrelated.txt").write_bytes(UNRELATED)
    if case["case_id"] != "receipt-boundary":
        (output / "first.txt").write_bytes(bytes.fromhex(case["preimage_hex"]))
    request = dict(case["input"], root=str(output))
    trace = temp / (case["case_id"] + "-trace.jsonl")
    startup = temp / (case["case_id"] + "-startup")
    startup.mkdir()
    (startup / "sitecustomize.py").write_text(BATCH_STARTUP)
    env = {"PYTHONPATH": str(startup), "PILOT_WRITE_TRACE": str(trace),
           "PILOT_OUTPUT_ROOT": str(output), "PILOT_PUBLIC_IO": str(root / "public_io.py")}
    row = {"case_id": case["case_id"], "expected": case["expected"], "request": request,
           "initial_bytes": file_bytes(output), "calls": [], "before_retry": {},
           "filesystem": {}, "write_trace": [], "startup_hook_sha256": digest(BATCH_STARTUP.encode()),
           "immutable_public_io": (root / "public_io.py").read_bytes() == PUBLIC_IO.encode(),
           "checks": {}, "observed": None, "passed": False, "error": None}
    try:
        if case["case_id"] == "binary-preimage":
            first = run(command, request, root, timeout, env)
            first["request"] = request
        else:
            target = "receipts.json" if case["case_id"] == "receipt-boundary" else "first.txt"
            first = paused(command, request, root, output, temp / (case["case_id"] + "-witness.json"), target, timeout, env)
        row["calls"].append(first)
        if case["case_id"] == "binary-external-edit":
            (output / "first.txt").write_bytes(bytes.fromhex(case["edit_hex"]))
        row["before_retry"] = file_bytes(output)
        last = run(command, request, root, timeout, env)
        last["request"] = request
        row["calls"].append(last)
        row["filesystem"] = file_bytes(output)
        row["write_trace"] = [strict_json(line) for line in trace.read_text().splitlines()] if trace.exists() else []
        row["checks"], row["observed"] = derive(row, case, command)
        row["passed"] = all(v is True for v in row["checks"].values()) and same(row["observed"], case["expected"])
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        row["error"] = type(exc).__name__
        try:
            row["filesystem"] = file_bytes(output)
        except (OSError, ValueError) as snapshot_error:
            row["filesystem_error"] = type(snapshot_error).__name__
    return row


def _raw_hash(report):
    return digest(canonical([{k: v for k, v in row.items() if k not in {"checks", "observed", "passed", "expected"}}
                             for row in report["cases"]]).encode())


def evaluate(root, cases=CASES, timeout=3):
    root = Path(root).resolve()
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("finite positive timeout required")
    spec, sha = load_cases(cases)
    source_files = sources(root)
    command = [str(Path(sys.executable).resolve()), str(root / "batch_tool.py")]
    before = evaluation_snapshot(cases, source_files, EVALUATORS)
    with tempfile.TemporaryDirectory(prefix="fhorja-supplementary-") as td:
        rows = [batch_case(root, command, case, Path(td), timeout) for case in spec["cases"]]
    binding = evaluation_binding(before, cases, source_files, EVALUATORS, command)
    report = {"schema_version": 1, "selection": SELECTION, "task_class": "batch",
              "fixture_sha256": sha, "binding": binding, "cases": rows,
              "immutable_public_io": (root / "public_io.py").read_bytes() == PUBLIC_IO.encode(),
              "accepted": binding["bound"] is True and all(r["passed"] is True for r in rows),
              "limits": ["Post-freeze selected cases, not primary prospective outcomes.",
                         "Trusted local capture, not hostile execution attestation.",
                         "Process death, not power-loss durability."]}
    report["accepted"] = report["accepted"] and report["immutable_public_io"]
    report["raw_capture_sha256"] = _raw_hash(report)
    return report


def validate_report(report, root, cases=CASES):
    try:
        root = Path(root).resolve()
        spec, sha = load_cases(cases)
        command = [str(Path(sys.executable).resolve()), str(root / "batch_tool.py")]
        if (type(report.get("schema_version")) is not int or report["schema_version"] != 1
                or report.get("selection") != SELECTION or report.get("task_class") != "batch"
                or report.get("fixture_sha256") != sha or type(report.get("accepted")) is not bool
                or not validate_binding(report["binding"], cases, sources(root), EVALUATORS, command)
                or report.get("raw_capture_sha256") != _raw_hash(report)
                or len(report["cases"]) != len(spec["cases"])):
            return False
        immutable = (root / "public_io.py").read_bytes() == PUBLIC_IO.encode()
        if report.get("immutable_public_io") is not immutable:
            return False
        passed = []
        for row, case in zip(report["cases"], spec["cases"]):
            if row["case_id"] != case["case_id"] or not same(row["expected"], case["expected"]):
                return False
            # A complete derivation cannot carry an unsupported capture error.
            # Incomplete captures remain retained, but never validate as coherent.
            if row["error"] is not None:
                return False
            checks, observed = derive(row, case, command)
            good = all(v is True for v in checks.values()) and same(observed, case["expected"])
            if not same(checks, row["checks"]) or not same(observed, row["observed"]) or row["passed"] is not good:
                return False
            passed.append(good)
        return report["accepted"] is (immutable and all(passed))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def calibrate(output, cases=CASES):
    """Retain both correct algorithms and each targeted defect in both algorithms."""
    import importlib.util
    from pilot_fixtures import prepare
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    reference_path = Path(__file__).with_name("fixtures") / "reference_pilot.py"
    loader = importlib.util.spec_from_file_location("supplementary_references", reference_path)
    reference = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(reference)
    dependencies = [*EVALUATORS, Path(cases)]
    frozen = snapshot(dependencies)
    results = []
    for algorithm in ("journal", "staged"):
        for fault, target in ((None, None), ("completion-boundary", "receipt-boundary"),
                              ("utf8-preimage", "binary-preimage")):
            candidate = output / (algorithm + "-" + (fault or "correct"))
            prepare(candidate, "batch")
            reference.install_batch(candidate, algorithm, fault)
            report = evaluate(candidate, cases)
            coherent = validate_report(report, candidate, cases)
            path = candidate / "supplementary-report.json"
            path.write_text(json.dumps(report, indent=2) + "\n")
            targeted_failure = target is not None and any(r["case_id"] == target and r["passed"] is False for r in report["cases"])
            good = coherent and (report["accepted"] is True if fault is None else report["accepted"] is False and targeted_failure)
            results.append({"algorithm": algorithm, "fault": fault, "target_case": target,
                            "control": fault is None, "accepted": report["accepted"],
                            "coherent": coherent, "calibration_passed": good,
                            "report": {"path": str(path), "sha256": digest(path.read_bytes())}})
    result = {"schema_version": 1, "selection": SELECTION, "provider_calls": 0,
              "frozen_dependencies": frozen, "current_dependencies": snapshot(dependencies),
              "results": results, "calibrated": all(r["calibration_passed"] for r in results)}
    result["calibrated"] = result["calibrated"] and same(result["frozen_dependencies"], result["current_dependencies"])
    (output / "calibration.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path)
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--calibrate", type=Path)
    args = parser.parse_args()
    if (args.root is None) == (args.calibrate is None):
        parser.error("provide exactly one candidate root or --calibrate directory")
    if args.calibrate is not None:
        result = calibrate(args.calibrate, args.cases)
        print(canonical({"calibrated": result["calibrated"], "controls": 2, "mutants": 4,
                         "selection": SELECTION, "provider_calls": 0}))
        return
    report = evaluate(args.root, args.cases)
    report["coherent"] = validate_report(report, args.root, args.cases)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
