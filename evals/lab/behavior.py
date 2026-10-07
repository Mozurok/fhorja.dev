#!/usr/bin/env python3
"""Run trusted local candidate adapters against externally held acceptance cases."""
import argparse
import json
import math
import os
import signal
import subprocess
import time
from pathlib import Path
from attempt import (canonical, unique_object, strict_json, fixture, evaluation_snapshot,
                     evaluation_binding, write_new)


EVALUATORS = [Path(__file__).resolve(), Path(__file__).with_name("attempt.py").resolve(),
              Path(__file__).with_name("quality.py").resolve()]


def stop_candidate(process, grace=.1):
    """Bound pipe cleanup even when a detached helper retains an output handle."""
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except OSError:
        pass
    try:
        process.communicate(timeout=grace)
        return True
    except (subprocess.TimeoutExpired, OSError, ValueError):
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        try:
            process.wait(timeout=grace)
        except (subprocess.TimeoutExpired, OSError):
            pass
        return False


def evaluate(cases_path, command, timeout=5, source_files=None):
    if (not isinstance(command, list) or not command
            or any(not isinstance(c, str) or not c for c in command)
            or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("candidate command and positive timeout required")
    spec, fixture_hash = fixture(cases_path, ("csv", "budget"))
    cases = spec["cases"]
    source_files = list(source_files or [])
    before = evaluation_snapshot(cases_path, source_files, EVALUATORS)
    evidence = {"schema_version": 2, "producer": "independent-harness",
                "fixture_sha256": fixture_hash,
                "candidate_command": command, "timeout_seconds": timeout,
                "limits": ["Trusted local execution, not an adversarial sandbox.",
                           "Fixture calibration does not prove agent ROI.",
                           "The output size check runs after capture, not as a memory cap."]}
    for feature in ("csv", "budget"):
        evidence[feature] = {"completed": False, "cases": []}
    env = {k: v for k, v in os.environ.items()
           if k in ("PATH", "SYSTEMROOT", "LANG", "LC_ALL", "TMPDIR")}
    for case in cases:
        row = {"case_id": case["case_id"], "executed": False, "passed": False,
               "expected": case["expected"], "observed": None}
        started = time.monotonic()
        process = None
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, env=env,
                                       start_new_session=os.name == "posix")
            output, _ = process.communicate(canonical(case["input"]), timeout=timeout)
            row["exit_code"] = process.returncode
            if process.returncode:
                row["error"] = "candidate exit failure"
            elif len(output) > 1_000_000:
                row["error"] = "candidate result exceeds protocol limit"
            else:
                observed = strict_json(output)
                if not isinstance(observed, dict) or set(observed) != {"result"}:
                    raise ValueError("expected one result object")
                row["observed"] = observed["result"]
                row["executed"] = True
                row["passed"] = canonical(row["observed"]) == canonical(row["expected"])
        except subprocess.TimeoutExpired:
            row["cleanup_incomplete"] = not stop_candidate(process)
            row["error"] = "candidate timeout"
        except (OSError, ValueError) as exc:
            row["error"] = f"candidate protocol failure: {type(exc).__name__}"
            if process is not None and process.poll() is None:
                row["cleanup_incomplete"] = not stop_candidate(process)
        row["wall_seconds"] = time.monotonic() - started
        evidence[case["feature"]]["cases"].append(row)
    evidence["binding"] = evaluation_binding(before, cases_path, source_files, EVALUATORS, command)
    if list(before["fixture"].values()) != [fixture_hash]:
        evidence["binding"]["bound"] = False
    for feature in ("csv", "budget"):
        rows = evidence[feature]["cases"]
        evidence[feature]["completed"] = bool(rows) and all(
            r["executed"] and r.get("passed") is True for r in rows)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument("--source", type=Path, action="append", default=[],
                        help="explicit candidate or dependency file; repeat for the whole source set")
    parser.add_argument("candidate", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.candidate[1:] if args.candidate[:1] == ["--"] else args.candidate
    evidence = evaluate(args.cases, command, args.timeout, args.source)
    write_new(args.output, evidence)
    print(json.dumps({k: evidence[k]["completed"] for k in ("csv", "budget")}))
    return 0 if all(evidence[k]["completed"] for k in ("csv", "budget")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
