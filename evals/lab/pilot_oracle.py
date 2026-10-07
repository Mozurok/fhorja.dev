"""Independent actual-process graders for three prospective public contracts."""
import argparse
import copy
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from attempt import (canonical, digest, fixture, same, strict_json, snapshot,
                     evaluation_snapshot, evaluation_binding, validate_binding)
from behavior import stop_candidate
from pilot_fixtures import PUBLIC_IO

CASES = Path(__file__).with_name("fixtures") / "pilot_cases.json"
EVALUATORS = [Path(__file__).resolve(), Path(__file__).with_name("attempt.py"),
              Path(__file__).with_name("behavior.py"),
              Path(__file__).with_name("quality.py"),
              Path(__file__).with_name("pilot_fixtures.py")]
REQUIRED = {
    "multimodule": {"recursive-delete", "arrays", "owner", "empty-object",
                    "escaped-pointer", "delete-subtree", "replace-types",
                    "empty-layers", "bool-version", "float-version",
                    "duplicate-name", "invalid-layer", "blank-name", "invalid-values",
                    "invalid-request", "invalid-layers"},
    "inventory-v1": {"v1-order", "v1-invalid", "v1-blocked"},
    "inventory-v2": {"encounter-order", "aggregate-filter", "blocked-invalid",
                     "boolean-delta", "boolean-threshold", "exact-total",
                     "zero-total", "invalid-blocked"},
    "batch": {"normal", "completed-replay", "payload-conflict", "partial-recovery",
              "external-edit", "io-failure", "two-operations", "invalid-path",
              "crlf-replay", "invalid-id", "invalid-body", "reserved-path", "ancestor-path"},
}

# Installed only in each trusted batch subprocess. Observes attempted writes,
# including overwritten intermediate journals, before candidate imports run.
BATCH_STARTUP = '''import json
import os
import sys
from pathlib import Path
root = Path(os.environ["PILOT_OUTPUT_ROOT"]).resolve()
public_io = Path(os.environ["PILOT_PUBLIC_IO"]).resolve()
log = os.environ["PILOT_WRITE_TRACE"]
def observe(event, args):
    if event == "open":
        path, mode, flags = args
        if not ((isinstance(mode,str) and any(c in mode for c in "wax+")) or
                (isinstance(flags,int) and flags & (os.O_WRONLY | os.O_RDWR))): return
    elif event == "os.rename": path = args[1]
    elif event == "os.remove": path = args[0]
    else: return
    if not isinstance(path,(str,bytes,os.PathLike)): return
    target = Path(os.fsdecode(path)).resolve()
    try: relative = str(target.relative_to(root))
    except ValueError: return
    frame = sys._getframe()
    via_io = False
    while frame:
        if frame.f_code.co_name == "replace" and Path(frame.f_code.co_filename).resolve() == public_io:
            via_io = True; break
        frame = frame.f_back
    with open(log,"a",encoding="utf-8") as stream:
        stream.write(json.dumps({"event":event,"path":relative,"via_public_io":via_io})+"\\n")
sys.addaudithook(observe)
'''


def load_cases(path):
    spec, sha = fixture(path, REQUIRED)
    for feature, required in REQUIRED.items():
        present = {r["case_id"] for r in spec["cases"] if r["feature"] == feature}
        if present != required:
            raise ValueError("complete declared meaningful case coverage required")
    return spec, sha


def sources(root):
    root = Path(root)
    files = sorted(root.rglob("*.py"))
    if not files:
        raise ValueError("candidate source dependencies required")
    # This is a trusted stdlib task. All local Python files, including added
    # helpers, are bound; arbitrary external import secrecy is not claimed.
    return files


def run(command, request, cwd, timeout, extra_env=None):
    env = {k: v for k, v in os.environ.items()
           if k in ("PATH", "SYSTEMROOT", "LANG", "LC_ALL", "TMPDIR")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra_env or {})
    started = time.monotonic()
    p = None
    observation = {"command":command, "stdout":"", "stderr":"", "exit_code":None,
                   "pid":None, "error":None}
    try:
        p = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=os.name == "posix")
        observation["pid"] = p.pid
        out_raw, err_raw = p.communicate(canonical(request).encode(), timeout=timeout)
        observation.update(stdout=out_raw.decode("utf-8", errors="replace"),
                           stderr=err_raw.decode("utf-8", errors="replace"),
                           stdout_hex=out_raw.hex(), stderr_hex=err_raw.hex(), exit_code=p.returncode)
        out, err = out_raw.decode(), err_raw.decode()
        observation.update(stdout=out, stderr=err, exit_code=p.returncode)
        if p.returncode:
            observation["error"] = "candidate exit failure"
        elif len(out) > 1_000_000:
            observation["error"] = "candidate output limit"
        else:
            parsed = strict_json(out)
            if not isinstance(parsed, dict) or set(parsed) not in ({"result"}, {"result", "input_unchanged"}):
                raise ValueError("one result envelope required")
            observation["envelope"] = parsed
    except subprocess.TimeoutExpired as exc:
        # Reap the child before interpreting diagnostics. Binary pipes also let
        # cleanup drain malformed or incomplete UTF-8 without a decoding error.
        observation["cleanup_complete"] = stop_candidate(p)
        observation["exit_code"] = p.returncode
        for name, raw in (("stdout", exc.output or b""), ("stderr", exc.stderr or b"")):
            observation[name + "_hex"] = raw.hex()
            observation[name] = raw.decode("utf-8", errors="replace")
        observation["error"] = "candidate timeout"
    except (OSError, ValueError) as exc:
        observation["error"] = f"candidate protocol failure: {type(exc).__name__}"
        if p is not None and p.poll() is None:
            observation["cleanup_complete"] = stop_candidate(p)
    observation["wall_seconds"] = time.monotonic() - started
    return observation


def api_probe(root, module, request):
    """Internal evaluator subprocess: candidate API plus input nonmutation."""
    import importlib
    sys.path.insert(0, str(Path(root).resolve()))
    candidate = importlib.import_module(module)
    before = copy.deepcopy(request)
    result = candidate.resolve(request)
    return {"result":result, "input_unchanged":same(request, before)}


def retained_envelope(call, command, interrupted_capture=False):
    """Reconstruct run() evidence before consulting a row's execution flag."""
    if (not isinstance(call, dict)
            or not {"command", "stdout", "stderr", "exit_code", "pid", "error"} <= set(call)
            or not same(call.get("command"), command)
            or not isinstance(call.get("stdout"), str) or not isinstance(call.get("stderr"), str)
            or (call.get("exit_code") is not None and type(call["exit_code"]) is not int)
            or (call.get("pid") is not None and (type(call["pid"]) is not int or call["pid"] <= 0))
            or (call.get("error") is not None and not isinstance(call["error"], str))):
        raise ValueError("invalid retained call fields")
    error = call.get("error")
    for name in ("stdout", "stderr"):
        if name + "_hex" in call and bytes.fromhex(call[name + "_hex"]).decode("utf-8", errors="replace") != call[name]:
            raise ValueError("contradictory retained stream bytes")
    if interrupted_capture:
        if (type(call.get("pid")) is not int or type(call.get("exit_code")) is not int
                or type(call.get("actual_partial")) is not bool
                or type(call.get("terminated")) is not bool
                or call.get("cleanup_complete") is not True
                or call["terminated"] is not (call["exit_code"] != 0)
                or (error is not None and not error.startswith("interruption observation failure: "))):
            raise ValueError("invalid interruption evidence")
        if "envelope" in call and not same(strict_json(call["stdout"]), call["envelope"]):
            raise ValueError("contradictory interruption envelope")
        return {}
    if error is None:
        raw = strict_json(call["stdout"])
        if (type(call.get("pid")) is not int or call.get("exit_code") != 0
                or len(call["stdout"]) > 1_000_000 or not isinstance(raw, dict)
                or set(raw) not in ({"result"}, {"result", "input_unchanged"})
                or not same(raw, call.get("envelope"))):
            raise ValueError("contradictory successful call")
        return raw
    if "envelope" in call:
        raise ValueError("failed run cannot publish an envelope")
    if error == "candidate exit failure":
        valid = type(call.get("pid")) is int and type(call.get("exit_code")) is int and call["exit_code"] != 0
    elif error == "candidate timeout":
        valid = (type(call.get("pid")) is int and type(call.get("exit_code")) is int
                 and call.get("cleanup_complete") is True)
    elif error == "candidate output limit":
        valid = type(call.get("pid")) is int and call.get("exit_code") == 0 and len(call["stdout"]) > 1_000_000
    elif error.startswith("candidate protocol failure: "):
        valid = (call.get("exit_code") is None and call["stdout"] == "" and call["stderr"] == "")
        if call.get("pid") is None:
            valid = valid and call["stdout"] == "" and call["stderr"] == ""
        elif error == "candidate protocol failure: UnicodeDecodeError" and type(call.get("exit_code")) is int:
            valid = False
            for name in ("stdout", "stderr"):
                try:
                    bytes.fromhex(call[name + "_hex"]).decode("utf-8")
                except UnicodeDecodeError:
                    valid = True
        elif call.get("exit_code") == 0:
            try:
                raw = strict_json(call["stdout"])
                valid = not isinstance(raw, dict) or set(raw) not in ({"result"}, {"result", "input_unchanged"})
            except ValueError:
                valid = True
    else:
        valid = False
    if not valid:
        raise ValueError("contradictory failed call")
    return {}


def file_bytes(root):
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            raise ValueError("symlink is outside trusted fixture contract")
        if path.is_file():
            result[str(path.relative_to(root))] = path.read_bytes().hex()
    return result


def receipt_ids(value):
    if (not isinstance(value, dict) or set(value) != {"completed"}
            or not isinstance(value["completed"], list)
            or any(not isinstance(x, str) or not x.strip() for x in value["completed"])
            or len(set(value["completed"])) != len(value["completed"])):
        raise ValueError("invalid once-only completion receipt")
    return value["completed"]


def receipt(root):
    path = Path(root) / "receipts.json"
    return receipt_ids(strict_json(path.read_bytes())) if path.exists() else []


def retained_receipt(files, errors):
    """Reconstruct read_receipt(), including its recorded parsing failure."""
    if not isinstance(errors, list) or any(not isinstance(error, str) for error in errors):
        raise ValueError("typed receipt errors required")
    try:
        raw = strict_json(bytes.fromhex(files["receipts.json"])) if "receipts.json" in files else {"completed":[]}
        return {"completed":receipt_ids(raw)}
    except ValueError as exc:
        if type(exc).__name__ not in errors:
            raise ValueError("receipt failure was not captured") from exc
        return None


def interrupted(command, request, cwd, output_root, witness, timeout, extra_env=None):
    """Observe actual first target publication before killing this process group."""
    env = {k: v for k, v in os.environ.items()
           if k in ("PATH", "SYSTEMROOT", "LANG", "LC_ALL", "TMPDIR")}
    env.update(PYTHONDONTWRITEBYTECODE="1", PILOT_PAUSE_DESTINATIONS=canonical(list(request["outputs"])), PILOT_WITNESS=str(witness))
    env.update(extra_env or {})
    # File-backed capture lets diagnostics flow before the publication witness.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        p = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                             stdout=stdout, stderr=stderr,
                             text=True, start_new_session=os.name == "posix")
        seen = None
        raw_before_kill = {}
        valid = False
        error = None
        try:
            p.stdin.write(canonical(request))
            p.stdin.close()
            p.stdin = None
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline and p.poll() is None:
                if witness.is_file():
                    try:
                        seen = strict_json(witness.read_bytes())
                        break
                    except (ValueError, OSError):
                        pass  # The public witness write may still be in progress.
                time.sleep(.005)
            raw_before_kill = file_bytes(output_root)
            published = seen.get("path") if isinstance(seen, dict) else None
            valid = (isinstance(seen, dict) and type(seen.get("pid")) is int and seen["pid"] == p.pid
                     and published in request["outputs"] and seen.get("body") == request["outputs"][published]
                     and raw_before_kill.get(published) == request["outputs"][published].encode().hex()
                     and all(name not in raw_before_kill for name in request["outputs"] if name != published)
                     and p.poll() is None)
        except (OSError, ValueError, TypeError) as exc:
            error = f"interruption observation failure: {type(exc).__name__}"
        finally:
            # Observation errors are candidate failures, not permission to leak a
            # paused process. Also close stdin if writing or closing it failed.
            if p.stdin is not None:
                try:
                    p.stdin.close()
                except OSError:
                    pass
                p.stdin = None
            cleanup = stop_candidate(p)
        try:
            p.communicate(timeout=.1)
        except (subprocess.TimeoutExpired, OSError, ValueError):
            error = error or "interruption observation failure: cleanup capture"
        stdout.seek(0)
        stderr.seek(0)
        out_raw, err_raw = stdout.read(), stderr.read()
    return {"command":command, "pid":p.pid, "exit_code":p.returncode,
            "stdout":out_raw.decode("utf-8", errors="replace"),
            "stderr":err_raw.decode("utf-8", errors="replace"),
            "stdout_hex":out_raw.hex(), "stderr_hex":err_raw.hex(), "error":error,
            "witness":seen, "files_before_kill":raw_before_kill,
            "actual_partial":valid, "cleanup_complete":cleanup,
            "terminated":p.poll() is not None and p.returncode != 0}


def batch_case(root, command, case, temp, timeout):
    """Keep already observed calls even if candidate file decoding fails."""
    evidence = {"case_id":case["case_id"], "expected":case["expected"],
                "observed":None, "checks":{}, "calls":[],
                "executed":False, "passed":False}
    try:
        return _batch_case(root, command, case, temp, timeout, evidence)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        evidence["error"] = f"batch protocol failure: {type(exc).__name__}"
        try:
            evidence["filesystem"] = file_bytes(temp / case["case_id"])
        except (OSError, ValueError) as snapshot_error:
            evidence["filesystem_error"] = type(snapshot_error).__name__
        return evidence


def _batch_case(root, command, case, temp, timeout, evidence):
    output = temp / case["case_id"]
    output.mkdir()
    (output / "unrelated.txt").write_bytes(b"user-owned\x00draft")
    payload = dict(case["input"], root=str(output))
    calls = evidence["calls"]
    audit = temp / (case["case_id"] + "-io-audit.jsonl")
    write_trace = temp / (case["case_id"] + "-write-trace.jsonl")
    startup = temp / (case["case_id"] + "-startup")
    startup.mkdir()
    hook = startup / "sitecustomize.py"
    hook.write_text(BATCH_STARTUP)
    io_env = {"PILOT_IO_AUDIT":str(audit), "PILOT_WRITE_TRACE":str(write_trace),
              "PILOT_OUTPUT_ROOT":str(output), "PILOT_PUBLIC_IO":str(root / "public_io.py"),
              "PYTHONPATH":str(startup)}
    checks = {"unrelated":False}
    initial_bytes = file_bytes(output)
    receipt_errors = []
    def read_receipt():
        try:
            return receipt(output)
        except (OSError, ValueError) as exc:
            receipt_errors.append(type(exc).__name__)
            return None
    kind = case["case_id"]
    if kind in ("partial-recovery", "external-edit"):
        first = interrupted(command, payload, root, output, temp / (kind + "-witness.json"), timeout, io_env)
        calls.append(first)
        checks["actual_partial"] = first["actual_partial"]
        checks["terminated"] = first["terminated"] and first["cleanup_complete"]
        checks["no_early_receipt"] = read_receipt() == []
        if kind == "external-edit":
            published = (first.get("witness") or {}).get("path")
            if published in case["input"]["outputs"]:
                (output / published).write_text("USER EDIT\n")
            protected_before = file_bytes(output)
        last = run(command, payload, root, timeout, io_env)
        calls.append(last)
        checks["fresh_process"] = type(last["pid"]) is int and last["pid"] != first["pid"]
        if kind == "external-edit":
            checks["conflict_preserves_all_bytes"] = file_bytes(output) == protected_before
    elif kind == "io-failure":
        first = run(command, payload, root, timeout,
                    dict(io_env, PILOT_FAIL_DESTINATIONS=canonical(list(payload["outputs"])), PILOT_WITNESS=str(temp / "failure-witness.json")))
        calls.append(first)
        partial = file_bytes(output)
        first["filesystem_after_failure"] = partial
        witness_path = temp / "failure-witness.json"
        first["io_witness"] = strict_json(witness_path.read_bytes()) if witness_path.exists() else None
        witness = first["io_witness"]
        published = witness.get("path") if isinstance(witness, dict) else None
        checks["io_failure_publication"] = (isinstance(witness, dict)
            and type(witness.get("pid")) is int and witness["pid"] == first["pid"]
            and published in payload["outputs"] and witness.get("body") == payload["outputs"][published]
            and partial.get(published) == payload["outputs"][published].encode().hex())
        complete_files = all(partial.get(name) == body.encode().hex() for name,body in payload["outputs"].items())
        completed = complete_files and read_receipt() == [payload["operation_id"]]
        checks["io_failure_not_false_success"] = (first["exit_code"] != 0 or
            (first.get("envelope") == {"result":{"status":"applied"}} and completed))
        checks["partial_or_recovered"] = (completed or
            (any(partial.get(name) == body.encode().hex() for name,body in payload["outputs"].items()) and not complete_files))
        checks["no_early_receipt"] = completed or read_receipt() == []
        last = run(command, payload, root, timeout, io_env)
        calls.append(last)
        checks["fresh_process"] = last["pid"] != first["pid"]
    else:
        last = run(command, payload, root, timeout, io_env)
        calls.append(last)
        if kind in ("completed-replay", "crlf-replay", "payload-conflict", "two-operations"):
            checks["initial_applied"] = last.get("envelope") == {"result":{"status":"applied"}}
            before = file_bytes(output)
            if kind == "payload-conflict":
                payload = dict(payload, outputs={"a.txt":"changed\n", "dir/b.txt":"new-b\n"})
            elif kind == "two-operations":
                payload = dict(payload, operation_id="second", outputs={"c.txt":"third\n"})
            last = run(command, payload, root, timeout, io_env)
            calls.append(last)
            if kind != "two-operations":
                checks["all_bytes_unchanged"] = file_bytes(output) == before
    expected = case_expected(case, calls)
    expected_files = expected["files"]
    files = {name:(output / name).read_bytes().decode() if (output / name).is_file() else None
             for name in expected_files}
    checks["unrelated"] = (output / "unrelated.txt").read_bytes() == b"user-owned\x00draft"
    if kind in ("invalid-path", "invalid-id", "invalid-body", "reserved-path", "ancestor-path"):
        evidence["escaped_path_exists"] = (temp / "escaped.txt").exists()
        checks["invalid_preserves_all_bytes"] = file_bytes(output) == initial_bytes and not evidence["escaped_path_exists"]
    envelope = last.get("envelope", {})
    result = envelope.get("result")
    checks["last_protocol"] = (last.get("error") is None and set(envelope) == {"result"}
                               and isinstance(result, dict) and set(result) == {"status"})
    status = result.get("status") if isinstance(result, dict) else None
    if kind == "io-failure" and status in ("applied", "replayed"):
        status = "completed"
    observed = {"status":status, "completed":read_receipt(), "files":files}
    audit_rows = [strict_json(line) for line in audit.read_text().splitlines()] if audit.exists() else []
    trace_rows = [strict_json(line) for line in write_trace.read_text().splitlines()] if write_trace.exists() else []
    final_bytes = file_bytes(output)
    checks["all_writes_via_public_io"] = audited_writes(final_bytes, initial_bytes, audit_rows,
                                                       (calls[0].get("witness") or {}).get("path") if kind == "external-edit" else None,
                                                       trace_rows)
    return {"case_id":kind, "expected":expected, "observed":observed,
            "io_audit":audit_rows,
            "receipt_errors":receipt_errors,
            "write_trace":trace_rows, "startup_hook_sha256":digest(hook.read_bytes()),
            "checks":checks, "calls":calls, "filesystem":file_bytes(output),
            "before_replay":before if kind in ("completed-replay", "crlf-replay", "payload-conflict", "two-operations") else None,
            "before_conflict":protected_before if kind == "external-edit" else None,
            "initial_filesystem":initial_bytes,
            **({"escaped_path_exists":evidence["escaped_path_exists"]} if "escaped_path_exists" in evidence else {}),
            "executed":checks["last_protocol"],
            "passed":same(observed, expected) and all(v is True for v in checks.values())}


def audited_writes(final_bytes, initial_bytes, audit_rows, user_edit=None, trace_rows=None):
    logged = {}
    for row in audit_rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            return False
        logged[row["path"]] = row["sha256"]
    if not isinstance(trace_rows, list) or any(not isinstance(row, dict)
        or set(row) != {"event", "path", "via_public_io"} or row["via_public_io"] is not True
        for row in trace_rows):
        return False
    changed = any(initial_bytes.get(name) != body and name != user_edit for name,body in final_bytes.items())
    if changed and not trace_rows:
        return False
    return all(name == user_edit or initial_bytes.get(name) == body
               or logged.get(name) == digest(bytes.fromhex(body)) for name,body in final_bytes.items())


def case_expected(case, calls):
    expected = copy.deepcopy(case["expected"])
    if case["case_id"] == "external-edit" and calls:
        path = (calls[0].get("witness") or {}).get("path")
        if path in expected["files"]:
            expected["files"] = {name:"USER EDIT\n" if name == path else None for name in expected["files"]}
    return expected


def protection_checks(root, protection, version):
    checks = {}
    if version == 2:
        if not isinstance(protection, dict) or not isinstance(protection.get("protected"), dict):
            raise ValueError("actual first-stage protection receipt required")
        for name in ("helpers.py", "notes.txt", "v1_checks.json"):
            value = protection["protected"].get(name)
            path = root / name
            checks[name] = isinstance(value, str) and path.is_file() and not path.is_symlink() and path.read_bytes().hex() == value
        section = protection.get("progress_section")
        checks["progress_section"] = (isinstance(section, str) and bool(section)
                                       and (root / "progress.md").is_file()
                                       and section in (root / "progress.md").read_text())
        checks["prior_v2_unknown"] = protection.get("prior_v2_verification") == "unknown"
        try:
            historical = strict_json((root / "v1_checks.json").read_bytes())
            checks["v1_historical"] = (historical.get("historical") is True
                                        and type(historical.get("requirement_version")) is int
                                        and historical["requirement_version"] == 1
                                        and type(historical.get("accepted")) is bool
                                        and historical["accepted"] is protection["stage1"]["accepted"])
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            checks["v1_historical"] = False
    try:
        handoff = strict_json((root / "handoff.json").read_bytes())
        checks["handoff"] = (isinstance(handoff, dict) and type(handoff.get("requirement_version")) is int
                              and handoff["requirement_version"] == version
                              and handoff.get("previous_verification") == "unknown"
                              and same(handoff.get("remaining"), []))
    except (OSError, ValueError):
        checks["handoff"] = False
    return checks


def evaluate(root, task_class, cases=CASES, timeout=1.5, version=2, protection=None, source_files=None):
    root = Path(root).resolve()
    if (task_class not in ("multimodule", "batch", "continuity") or type(version) is not int
            or version not in (1, 2) or type(timeout) not in (float, int)
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("valid task class, version and timeout required")
    spec, fixture_hash = load_cases(cases)
    all_sources = sources(root)
    source_files = list(source_files) if source_files is not None else all_sources
    if {str(Path(p).resolve()) for p in source_files} != {str(p.resolve()) for p in all_sources}:
        raise ValueError("all local source dependencies must be declared")
    entry = root / ("config_tool/cli.py" if task_class == "multimodule" else "batch_tool.py" if task_class == "batch" else "candidate.py")
    command = [str(Path(sys.executable).resolve()), str(entry)]
    before = evaluation_snapshot(cases, source_files, EVALUATORS)
    feature = f"inventory-v{version}" if task_class == "continuity" else task_class
    rows = []
    global_checks = {}
    if task_class == "batch":
        global_checks["immutable_public_io"] = (root / "public_io.py").read_bytes() == PUBLIC_IO.encode()
    if task_class == "continuity":
        global_checks.update(protection_checks(root, protection, version))
    with tempfile.TemporaryDirectory(prefix="fhorja-pilot-oracle-") as tmp:
        temp = Path(tmp)
        for case in spec["cases"]:
            if case["feature"] != feature:
                continue
            if task_class == "batch":
                try:
                    row = batch_case(root, command, case, temp, timeout)
                except (OSError, ValueError, TypeError, AttributeError) as exc:
                    row = {"case_id":case["case_id"], "expected":case["expected"], "observed":None,
                           "checks":{}, "calls":[], "executed":False, "passed":False,
                           "error":f"batch protocol failure: {type(exc).__name__}"}
            else:
                cli = run(command, case["input"], root, timeout)
                api_command = [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()),
                               "--api-probe", str(root), "config_tool" if task_class == "multimodule" else "candidate"]
                api = run(api_command, case["input"], root, timeout)
                cli_envelope = cli.get("envelope", {})
                api_envelope = api.get("envelope", {})
                checks = {"cli_envelope":set(cli_envelope) == {"result"},
                          "api_envelope":set(api_envelope) == {"result", "input_unchanged"},
                          "input_unchanged":api_envelope.get("input_unchanged") is True,
                          "api_cli_agree":same(api_envelope.get("result"), cli_envelope.get("result"))}
                observed = cli_envelope.get("result")
                executed = cli.get("error") is None and api.get("error") is None
                row = {"case_id":case["case_id"], "expected":case["expected"], "observed":observed,
                       "checks":checks, "calls":[cli, api], "executed":executed,
                       "passed":executed and all(v is True for v in checks.values()) and same(observed, case["expected"])}
            rows.append(row)
    if task_class == "continuity":
        global_checks.update(protection_checks(root, protection, version))
    if task_class == "batch":
        global_checks["immutable_public_io"] = (root / "public_io.py").read_bytes() == PUBLIC_IO.encode()
    binding = evaluation_binding(before, cases, source_files, EVALUATORS, command)
    report = {"schema_version":1, "task_class":task_class, "feature":feature,
              "fixture_sha256":fixture_hash, "binding":binding,
              "cases":rows, "global_checks":global_checks,
              "protection":copy.deepcopy(protection) if task_class == "continuity" else None,
              "product_artifacts":snapshot([root / name for name in
                  ("handoff.json", "notes.txt", "progress.md", "v1_checks.json") if (root / name).is_file()]) if task_class == "continuity" else {},
              "accepted":False, "limits":["Trusted local execution, not adversarial isolation.",
                  "Offline continuity controls do not certify provider session boundaries.",
                  "Process death, not power-loss durability."]}
    report["accepted"] = (binding["bound"] is True and bool(rows)
                           and all(r["passed"] is True for r in rows)
                           and all(v is True for v in global_checks.values()))
    return report


def validate_report(report, root, cases=CASES):
    """Reject incomplete or internally contradictory typed calibration evidence."""
    try:
        spec, sha = load_cases(cases)
        feature = report["feature"]
        task_class = "continuity" if feature in ("inventory-v1", "inventory-v2") else feature
        root = Path(root).resolve()
        entry = root / ("config_tool/cli.py" if task_class == "multimodule" else "batch_tool.py" if task_class == "batch" else "candidate.py")
        command = [str(Path(sys.executable).resolve()), str(entry)]
        api_command = [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()),
                       "--api-probe", str(root), "config_tool" if task_class == "multimodule" else "candidate"]
        expected = {c["case_id"]:c for c in spec["cases"] if c["feature"] == feature}
        rows = report["cases"]
        required_global = ({"immutable_public_io"} if feature == "batch" else
                           {"helpers.py", "notes.txt", "v1_checks.json", "progress_section",
                            "prior_v2_unknown", "v1_historical", "handoff"} if feature == "inventory-v2" else
                           {"handoff"} if feature == "inventory-v1" else set())
        if (type(report.get("schema_version")) is not int or report["schema_version"] != 1
                or feature not in REQUIRED or report.get("fixture_sha256") != sha
                or report.get("task_class") != task_class
                or not same(report["binding"].get("candidate_command"), command)
                or not isinstance(rows, list) or len(rows) != len(expected)
                or {r["case_id"] for r in rows} != set(expected)
                or type(report.get("accepted")) is not bool
                or not isinstance(report.get("global_checks"), dict)
                or set(report["global_checks"]) != required_global
                or any(type(v) is not bool for v in report["global_checks"].values())):
            return False
        for row in rows:
            if (type(row.get("passed")) is not bool or type(row.get("executed")) is not bool
                    or not same(row.get("expected"), case_expected(expected[row["case_id"]], row.get("calls", [])))
                    or not isinstance(row.get("checks"), dict)
                    or any(type(v) is not bool for v in row["checks"].values())):
                return False
            calculated = (row["executed"] is True and bool(row["checks"])
                          and all(v is True for v in row["checks"].values())
                          and same(row.get("observed"), row["expected"]))
            if calculated is not row["passed"]:
                return False
            if feature != "batch":
                if len(row.get("calls", [])) != 2:
                    return False
                cli, api = row["calls"]
                raw_cli = retained_envelope(cli, command)
                raw_api = retained_envelope(api, api_command)
                if row["executed"] is not (cli.get("error") is None and api.get("error") is None):
                    return False
                derived_checks = {"cli_envelope":set(raw_cli) == {"result"},
                                  "api_envelope":set(raw_api) == {"result", "input_unchanged"},
                                  "input_unchanged":raw_api.get("input_unchanged") is True,
                                  "api_cli_agree":same(raw_api.get("result"), raw_cli.get("result"))}
                if (not same(derived_checks, row["checks"])
                        or not same(raw_cli.get("result"), row.get("observed"))):
                    return False
            else:
                calls = row.get("calls")
                if not isinstance(calls, list):
                    return False
                for index, call in enumerate(calls):
                    retained_envelope(call, command, index == 0 and row["case_id"] in ("partial-recovery", "external-edit"))
                if not row["checks"]:
                    # Only expected-file decoding failures are reproducible from
                    # a complete retained snapshot. Other capture failures stay
                    # diagnostic, rather than becoming coherent by annotation.
                    fields = {"case_id", "expected", "observed", "checks", "calls",
                              "executed", "passed", "error", "filesystem"}
                    two_calls = {"completed-replay", "crlf-replay", "payload-conflict",
                                 "two-operations", "partial-recovery", "external-edit", "io-failure"}
                    if (set(row) != fields or row["executed"] or row.get("observed") is not None
                            or row.get("error") != "batch protocol failure: UnicodeDecodeError"
                            or len(calls) != (2 if row["case_id"] in two_calls else 1)
                            or not isinstance(row["filesystem"], dict)):
                        return False
                    fs = row["filesystem"]
                    for name, body in fs.items():
                        if (not isinstance(name, str) or not isinstance(body, str)
                                or bytes.fromhex(body).hex() != body):
                            return False
                    decode_failure = False
                    for name in expected[row["case_id"]]["expected"]["files"]:
                        if name in fs:
                            try:
                                bytes.fromhex(fs[name]).decode()
                            except UnicodeDecodeError:
                                decode_failure = True
                    if not decode_failure:
                        return False
                    continue
                if not calls:
                    return False
                last = calls[-1]
                raw = retained_envelope(last, command)
                last_protocol = (last.get("error") is None and set(raw) == {"result"}
                    and isinstance(raw.get("result"), dict) and set(raw["result"]) == {"status"})
                if row["executed"] is not last_protocol or row["checks"].get("last_protocol") is not last_protocol:
                    return False
                status = raw.get("result", {}).get("status") if isinstance(raw.get("result"), dict) else None
                if row["case_id"] == "io-failure" and status in ("applied", "replayed"):
                    status = "completed"
                if not isinstance(row.get("observed"), dict) or not same(status, row["observed"]["status"]):
                    return False
                fs = row["filesystem"]
                if row.get("startup_hook_sha256") != digest(BATCH_STARTUP.encode()):
                    return False
                final_receipt = retained_receipt(fs, row.get("receipt_errors"))
                completed_ids = final_receipt["completed"] if final_receipt is not None else None
                files = {name:bytes.fromhex(fs[name]).decode() if name in fs else None
                         for name in expected[row["case_id"]]["expected"]["files"]}
                if (not same(completed_ids, row["observed"]["completed"])
                        or not same(files, row["observed"]["files"])):
                    return False
                kind = row["case_id"]
                derived = {"unrelated":fs.get("unrelated.txt") == b"user-owned\x00draft".hex(), "last_protocol":last_protocol,
                           "all_writes_via_public_io":audited_writes(fs, row["initial_filesystem"], row["io_audit"],
                               (calls[0].get("witness") or {}).get("path") if kind == "external-edit" else None,
                               row.get("write_trace"))}
                if kind in ("completed-replay", "crlf-replay", "payload-conflict", "two-operations"):
                    if len(calls) != 2: return False
                    derived["initial_applied"] = (calls[0]["exit_code"] == 0
                        and calls[0].get("envelope") == {"result":{"status":"applied"}})
                    if kind != "two-operations": derived["all_bytes_unchanged"] = same(fs, row.get("before_replay"))
                elif kind in ("partial-recovery", "external-edit"):
                    if len(calls) != 2: return False
                    first = calls[0]; witness = first.get("witness")
                    prior = first.get("files_before_kill", {})
                    published = witness.get("path") if isinstance(witness, dict) else None
                    outputs = expected[kind]["input"]["outputs"]
                    derived["actual_partial"] = (isinstance(witness, dict)
                        and type(witness.get("pid")) is int and witness["pid"] == first.get("pid")
                        and published in outputs and witness.get("body") == outputs[published]
                        and prior.get(published) == outputs[published].encode().hex()
                        and all(name not in prior for name in outputs if name != published)
                        and first.get("actual_partial") is True)
                    derived["terminated"] = (type(first.get("exit_code")) is int and first["exit_code"] != 0
                                              and first.get("terminated") is True and first.get("cleanup_complete") is True)
                    prior_receipt = retained_receipt(prior, row.get("receipt_errors"))
                    derived["no_early_receipt"] = same(prior_receipt, {"completed":[]})
                    derived["fresh_process"] = type(last.get("pid")) is int and last["pid"] != first.get("pid")
                    if kind == "external-edit": derived["conflict_preserves_all_bytes"] = same(fs, row.get("before_conflict"))
                elif kind == "io-failure":
                    if len(calls) != 2: return False
                    first = calls[0]; prior = first["filesystem_after_failure"]
                    outputs = expected[kind]["input"]["outputs"]
                    witness = first.get("io_witness")
                    published = witness.get("path") if isinstance(witness, dict) else None
                    derived["io_failure_publication"] = (isinstance(witness, dict)
                        and type(witness.get("pid")) is int and witness["pid"] == first["pid"]
                        and published in outputs and witness.get("body") == outputs[published]
                        and prior.get(published) == outputs[published].encode().hex())
                    first_receipt = retained_receipt(prior, row.get("receipt_errors"))
                    complete_files = all(prior.get(name) == body.encode().hex() for name,body in outputs.items())
                    completed = complete_files and same(first_receipt, {"completed":[expected[kind]["input"]["operation_id"]]})
                    derived["io_failure_not_false_success"] = first["exit_code"] != 0 or (first.get("envelope") == {"result":{"status":"applied"}} and completed)
                    derived["partial_or_recovered"] = completed or (any(prior.get(name) == body.encode().hex() for name,body in outputs.items()) and not complete_files)
                    derived["no_early_receipt"] = completed or same(first_receipt, {"completed":[]})
                    derived["fresh_process"] = last["pid"] != first["pid"]
                elif kind in ("invalid-path", "invalid-id", "invalid-body", "reserved-path", "ancestor-path"):
                    if type(row.get("escaped_path_exists")) is not bool:
                        return False
                    derived["invalid_preserves_all_bytes"] = same(fs, row.get("initial_filesystem")) and not row["escaped_path_exists"]
                if not same(derived, row["checks"]):
                    return False
        current_binding = validate_binding(report["binding"], cases, sources(root), EVALUATORS)
        if task_class == "batch" and report["global_checks"]["immutable_public_io"] is not (
                (root / "public_io.py").read_bytes() == PUBLIC_IO.encode()):
            return False
        if task_class == "continuity":
            artifacts = snapshot([root / name for name in ("handoff.json", "notes.txt", "progress.md", "v1_checks.json") if (root / name).is_file()])
            if not same(artifacts, report.get("product_artifacts")):
                return False
            if not same(protection_checks(root, report.get("protection"), 1 if feature == "inventory-v1" else 2), report["global_checks"]):
                return False
        accepted = (current_binding and bool(rows) and all(r["passed"] is True for r in rows)
                    and all(v is True for v in report["global_checks"].values()))
        return current_binding and accepted is report["accepted"]
    except (KeyError, ValueError, TypeError, OSError, AttributeError):
        return False


def calibrate(output):
    """Retain six controls and every declared mutant with source-bound receipts."""
    import importlib.util
    from pilot_fixtures import prepare, advance_continuity
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    reference_path = Path(__file__).with_name("fixtures") / "reference_pilot.py"
    loader = importlib.util.spec_from_file_location("pilot_calibration_references", reference_path)
    reference = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(reference)
    dependencies = [*EVALUATORS, CASES, reference_path]
    frozen = snapshot(dependencies)
    results = []
    definitions = (
        ("multimodule", ("recursive", "flat"), reference.CONFIG_FAULTS, reference.install_config),
        ("batch", ("journal", "staged"), reference.BATCH_FAULTS, reference.install_batch),
        ("continuity", ("dict", "buckets"), reference.INVENTORY_FAULTS, reference.install_inventory),
    )
    for task_class, algorithms, faults, install in definitions:
        treatments = [(algorithm, None, None) for algorithm in algorithms]
        treatments += [(algorithms[0], fault, target) for fault,target in faults.items()]
        for algorithm, fault, target in treatments:
            name = task_class + "-" + (fault or algorithm)
            root = prepare(output / name, task_class)
            protection = None
            if task_class == "continuity":
                install(root, algorithm, version=1, write_helper=True)
                stage1 = evaluate(root, task_class, version=1)
                if not stage1["accepted"] or not validate_report(stage1, root):
                    raise ValueError("correct stage1 control failed calibration")
                (output / (name + "-stage1.json")).write_text(canonical(stage1))
                protection = advance_continuity(root, stage1)
                install(root, algorithm, version=2, fault=fault)
            else:
                install(root, algorithm, fault=fault)
            report = evaluate(root, task_class, protection=protection)
            (output / (name + ".json")).write_text(canonical(report))
            failed_ids = [r["case_id"] for r in report["cases"] if r["passed"] is False]
            met = validate_report(report, root) and (report["accepted"] is True if fault is None
                   else report["accepted"] is False and target in failed_ids)
            results.append({"name":name,"control":fault is None,"accepted":report["accepted"],
                            "intended_case":target,"failed_cases":failed_ids,"calibrated":met,
                            "report_sha256":digest((output / (name + ".json")).read_bytes())})
    if not same(snapshot(dependencies), frozen):
        raise ValueError("calibration source changed")
    result = {"schema_version":1,"source_manifest":frozen,"results":results,
              "calibrated":bool(results) and all(r["calibrated"] is True for r in results),
              "provider_calls":0}
    (output / "calibration.json").write_text(canonical(result))
    if not result["calibrated"]:
        raise ValueError("calibration controls or intended mutants failed")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-probe", nargs=2, metavar=("ROOT", "MODULE"))
    parser.add_argument("--calibrate", type=Path)
    args = parser.parse_args()
    if args.api_probe:
        print(canonical(api_probe(*args.api_probe, strict_json(sys.stdin.read()))))
    elif args.calibrate:
        result = calibrate(args.calibrate)
        print(canonical({"calibrated":result["calibrated"],"controls":sum(r["control"] for r in result["results"]),
                         "mutants":sum(not r["control"] for r in result["results"]),"provider_calls":0}))
    else:
        parser.error("controller evaluate() API or internal --api-probe required")


if __name__ == "__main__":
    main()
