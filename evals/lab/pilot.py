"""Opt-in prospective protocol and retained local captures, not a billing governor.

The controller owns the binding and callbacks. This is trusted execution, not
an adversarial isolation boundary. No provider is called by importing this file.
"""
import argparse
import ast
import copy
import fcntl
import json
import math
import os
import re
import select
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import attempt
import pilot_oracle as oracle
import pilot_fixtures as fixtures
import usage
from behavior import stop_candidate

ARMS = ("native", "fhorja")
CLASSES = ("multimodule", "batch", "continuity")
COMMON = {"service_tier", "tools", "permissions", "network", "approval",
          "collaboration", "instruction_policy", "admission_policy", "adapter"}
INPUTS = {"facts", "checks", "seeds", "host_inventory"}
KERNEL_GUARDS = {"source", "authorization", "protected_work", "latest_requirement",
                 "unknown_verification", "verification_evidence", "comparison_scope",
                 "no_default_promotion"}
ENVIRONMENT = {"PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "CODEX_HOME"}
TERMINAL = {"completed", "exit-failure", "timeout", "malformed",
            "provider-refusal", "capture-incomplete", "launch-failure"}


def _keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError("closed object fields required: " + ",".join(sorted(keys)))


def _files(paths):
    if not isinstance(paths, list) or not paths:
        raise ValueError("explicit nonempty file set required")
    return attempt.snapshot(paths)


def _read(binding):
    _keys(binding, {"path", "sha256"})
    path = Path(binding["path"])
    if path.is_symlink() or attempt.digest(path.read_bytes()) != binding["sha256"]:
        raise ValueError("bound bytes changed")
    return attempt.strict_json(path.read_bytes())


def _write(path, value):
    return {"path": str(Path(path).resolve()), "sha256": attempt.write_new(path, value)}


def _publish(path, value):
    """Publish a complete new controller record atomically, without overwriting."""
    path = Path(path).resolve()
    temporary = path.with_name("."+path.name+"-"+str(uuid.uuid4())+".prepared")
    try:
        receipt = _write(temporary,value)
        os.link(temporary,path)
        return {"path":str(path),"sha256":receipt["sha256"]}
    finally:
        temporary.unlink(missing_ok=True)


def _events(path):
    events, errors = [], []
    try:
        lines = Path(path).read_bytes().splitlines()
    except OSError as exc:
        return [], [str(exc)]
    for index, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            value = attempt.strict_json(raw)
            if not isinstance(value, dict) or not isinstance(value.get("type"), str):
                raise ValueError("typed event required")
            events.append(value)
        except (ValueError, UnicodeError):
            errors.append("%s:%d: malformed event" % (Path(path).name, index))
    return events, errors


def _product_files(workspace):
    return [str(p) for p in Path(workspace).rglob("*") if p.is_file() and
            ".git" not in p.relative_to(workspace).parts and
            "__pycache__" not in p.relative_to(workspace).parts]


def render_kernel(audit):
    """Mechanical source/coverage validation; semantic passage selection is audited separately."""
    _keys(audit, {"schema_version", "guards", "public_obligations"})
    if type(audit["schema_version"]) is not int or audit["schema_version"] != 1:
        raise ValueError("typed kernel audit version required")
    _keys(audit["public_obligations"], CLASSES)
    obligations = set()
    for cls, names in audit["public_obligations"].items():
        if (not isinstance(names, list) or not names
                or any(not isinstance(n, str) or not n.strip() for n in names)
                or len(set(names)) != len(names)):
            raise ValueError("distinct public obligations required")
        obligations.update(cls + ":" + name for name in names)
    guards = audit["guards"]
    if (not isinstance(guards, list) or len(guards) != len(KERNEL_GUARDS)
            or any(not isinstance(g, dict) for g in guards)
            or {g.get("name") for g in guards} != KERNEL_GUARDS):
        raise ValueError("all eight distinct guards required")
    covered, paragraphs = set(), []
    for guard in guards:
        _keys(guard, {"name", "source", "obligations", "rationale"})
        source = guard["source"]
        _keys(source, {"path", "start_line", "end_line", "sha256"})
        path = Path(source["path"])
        _files([str(path)])
        lines = path.read_bytes().decode("utf-8").splitlines(keepends=True)
        if (type(source["start_line"]) is not int or type(source["end_line"]) is not int
                or not 1 <= source["start_line"] <= source["end_line"] <= len(lines)):
            raise ValueError("exact bounded guard passage required")
        passage = "".join(lines[source["start_line"]-1:source["end_line"]])
        if not passage.strip() or attempt.digest(passage.encode()) != source["sha256"]:
            raise ValueError("audited guard passage changed")
        if (not isinstance(guard["rationale"], str) or not guard["rationale"].strip()
                or not isinstance(guard["obligations"], list)
                or (not guard["obligations"] and guard["name"] not in
                    ("comparison_scope", "no_default_promotion"))
                or any(not isinstance(o, str) or o not in obligations for o in guard["obligations"])):
            raise ValueError("explicit public guard coverage required")
        covered.update(guard["obligations"])
        paragraphs.append("## " + guard["name"] + "\n" + passage.rstrip() + "\n")
    if covered != obligations:
        raise ValueError("uncovered declared public obligation")
    return "# Selected Fhorja kernel\n\n" + "\n".join(paragraphs)


def _toml(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if isinstance(value, list):
        return "[" + ",".join(_toml(v) for v in value) + "]"
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        return "{" + ",".join(_toml(k) + "=" + _toml(v) for k,v in value.items()) + "}"
    raise ValueError("unsupported config value")


def codex_adapter(spec):
    """Validate the declared adapter; configuration is not runtime delivery attestation."""
    adapter = spec["common"]["adapter"]
    _keys(adapter, {"kind", "binary", "binary_sha256", "version", "config", "environment"})
    if adapter["kind"] != "codex-exec" or adapter["version"] != "codex-cli 0.160.0":
        raise ValueError("observed installed adapter version required")
    binary = Path(adapter["binary"])
    manifest = _files([str(binary)])
    if (not binary.is_absolute() or adapter["binary_sha256"] != manifest[str(binary.resolve())]
            or str(binary.resolve()) not in attempt.artifact_snapshot(spec["artifacts"])["driver"]):
        raise ValueError("installed executable must be independently frozen")
    common, values = spec["common"], spec["policy"]["values"]
    if (values["provider"] != "codex" or common["permissions"] != "workspace-write"
            or common["approval"] != "auto-review" or common["network"] != "disabled"):
        raise ValueError("matched existing-account workspace policy required")
    config = adapter["config"]
    if not isinstance(config, dict):
        raise ValueError("explicit config required")
    expected = {"model_reasoning_effort":values["effort"],
                "service_tier":common["service_tier"], "features.hooks":False,
                "features.apps":False, "features.multi_agent":True,
                "web_search":"disabled", "sandbox_workspace_write.network_access":False,
                "agents.max_concurrent_threads_per_session":2, "agents.max_depth":1}
    if any(not attempt.same(config.get(k), v) for k,v in expected.items()):
        raise ValueError("matched explicit Codex config required")
    if not attempt.same(common["collaboration"], {
            "max_concurrent_threads_per_session":2, "max_depth":1, "enforcement":"unknown"}):
        raise ValueError("collaboration request and enforcement unknown must be explicit")
    skills = config.get("skills.config")
    if (not isinstance(skills, list) or not skills
            or any(not isinstance(s, dict) or set(s) != {"path", "enabled"}
                   or not isinstance(s["path"], str) or not s["path"]
                   or s["enabled"] is not False for s in skills)
            or len({s["path"] for s in skills}) != len(skills)):
        raise ValueError("explicit distinct non-system skill disables required")
    extras = set(config) - set(expected) - {"skills.config"}
    if any(not (k.startswith(("mcp_servers.", "plugins.")) and k.endswith(".enabled")
                and config[k] is False) for k in extras):
        raise ValueError("unreviewed adapter config override")
    environment = adapter["environment"]
    if (not isinstance(environment, dict) or not {"HOME", "PATH"} <= set(environment)
            or not set(environment) <= ENVIRONMENT
            or any(not isinstance(v, str) or v != os.environ.get(k) for k,v in environment.items())
            or ("CODEX_HOME" in os.environ and environment.get("CODEX_HOME") != os.environ["CODEX_HOME"])):
        raise ValueError("existing identity and credential-free frozen environment required")
    for value in config.values():
        _toml(value)
    return adapter


def codex_command(spec, workspace, destination):
    adapter = codex_adapter(spec)
    command = [adapter["binary"], "exec", "--ignore-user-config", "--strict-config",
               "--json", "--approve-for-me", "--skip-git-repo-check",
               "--color", "never", "-m", spec["policy"]["values"]["model"],
               "-C", str(Path(workspace).resolve()), "-o",
               str(Path(destination).resolve() / "last-message.txt")]
    for key, value in sorted(adapter["config"].items()):
        # exec skips the user transports; enabled=false alone is an invalid
        # cold server definition under strict validation. Metadata RPCs still
        # disable each existing user server when observing their own layer.
        if key.startswith("mcp_servers."):
            continue
        command += ["-c", key + "=" + _toml(value)]
    command += ["-c", "mcp_servers={}"]
    return command + ["-"]


def codex_callback(binding):
    """Use only through dispatch's allocated, guarded invocation boundary."""
    def callback(destination, workspace, prompt, timeout):
        spec = verify_protocol(binding)["spec"]
        adapter = codex_adapter(spec)
        if timeout != spec["policy"]["values"]["timeout_seconds"]:
            raise ValueError("unmatched invocation deadline")
        _committed_driver(spec)
        process = capture_process(codex_command(spec, workspace, destination), workspace,
                                  prompt, destination, timeout, environment=adapter["environment"])
        events, errors = _events(Path(destination) / "stdout.jsonl")
        roots = {e.get("thread_id") for e in events if e.get("type") == "thread.started"
                 and isinstance(e.get("thread_id"), str)}
        if len(roots) == 1:
            home = Path(adapter["environment"].get("CODEX_HOME",
                        str(Path(adapter["environment"]["HOME"]) / ".codex")))
            process["rollouts"] = retain_rollouts(next(iter(roots)),
                Path(destination) / "stdout.jsonl", home, Path(destination) / "rollouts")
        return process
    return callback


def observe_host(spec, cwd, destination, timeout=40):
    """Read-only RPCs, no thread or turn creation; exec's config layer remains distinct."""
    adapter = codex_adapter(spec)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    command = [adapter["binary"], "app-server", "--strict-config"]
    for key, value in sorted(adapter["config"].items()):
        command += ["-c", key + "=" + _toml(value)]
    started = datetime.now(timezone.utc).isoformat()
    process, error, cleanup = None, None, None
    responses, pending = {}, bytearray()
    with (destination / "stdout.jsonl").open("xb") as out, (destination / "stderr.txt").open("xb") as err:
        def send(value):
            process.stdin.write((json.dumps(value)+"\n").encode())
            process.stdin.flush()
        def request(ident, method, params=None):
            value = {"id":ident,"method":method}
            if params is not None:
                value["params"] = params
            send(value)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                while b"\n" in pending:
                    raw, _, rest = pending.partition(b"\n")
                    pending[:] = rest
                    row = attempt.strict_json(raw)
                    if not isinstance(row, dict):
                        raise ValueError("typed RPC response required")
                    if type(row.get("id")) is int and row["id"] == ident:
                        if "error" in row:
                            raise ValueError("read-only RPC rejected: " + method)
                        return row
                if not select.select([process.stdout],[],[],min(1,max(0,deadline-time.monotonic())))[0]:
                    continue
                chunk = os.read(process.stdout.fileno(),65536)
                if not chunk:
                    raise ValueError("read-only RPC stream ended: " + method)
                out.write(chunk);out.flush();pending.extend(chunk)
            raise TimeoutError("read-only RPC deadline: " + method)
        try:
            process = subprocess.Popen(command,cwd=cwd,env=adapter["environment"],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,
                start_new_session=True,bufsize=0)
            responses["initialize"] = request(0,"initialize",{
                "clientInfo":{"name":"fhorja_readonly_observer","version":"1"},
                "capabilities":{"experimentalApi":True}})
            send({"method":"initialized","params":{}})
            responses["limits"] = request(1,"account/rateLimits/read")
            responses["inventory"] = request(2,"skills/list",{
                "cwds":[str(Path(cwd).resolve())],"forceReload":True})
            responses["config"] = request(3,"config/read",{"includeLayers":False})
        except (OSError, ValueError, TimeoutError, UnicodeError) as exc:
            error = type(exc).__name__ + ": " + str(exc)
        finally:
            if process is not None:
                cleanup = stop_candidate(process)
                process.stdin.close();process.stdout.close()
    return _write(destination / "observation.json",{
        "started_utc":started,"captured_utc":datetime.now(timezone.utc).isoformat(),
        "responses":responses,"error":error,"cleanup_complete":cleanup,
        "command":command,"captures":attempt.snapshot([
            destination / "stdout.jsonl",destination / "stderr.txt"]),
        "limits":["App-server config inventory is not exec input or backend delivery attestation.",
                  "Read-only observation does not enforce dollar, nested-call or child limits."]})


def host_admission(binding):
    """Parse the observed installed shape; missing/unsupported fields stay unknown."""
    receipt = _read(binding)
    if not attempt.same(receipt["captures"],attempt.snapshot(list(receipt["captures"]))):
        raise ValueError("host observation capture changed")
    limits = receipt["responses"].get("limits",{}).get("result",{})
    if not isinstance(limits,dict):
        limits = {}
    rates = limits.get("rateLimits")
    rates = rates if isinstance(rates,dict) else {}
    credits = rates.get("credits")
    credits = credits if isinstance(credits,dict) else {}
    typed = lambda v: v if type(v) is bool else None
    return {"captured_utc":receipt["captured_utc"] if receipt["error"] is None else None,
            "ordinary_usage_allowed":typed(limits.get("ordinaryUsageAllowed")),
            "spend_control_reached":typed(rates.get("spendControlReached")),
            "credits_available":typed(credits.get("hasCredits")),
            "provider_refusal":False,"observed_actual_usd":None}


def verify_host(spec, binding, cwd=None):
    """Verify observed metadata effects, without equating app-server and exec layers."""
    adapter = codex_adapter(spec)
    receipt = _read(binding)
    observation = host_admission(binding)
    responses = receipt["responses"]
    if receipt["error"] is not None:
        raise ValueError("host configuration observation unavailable")
    try:
        stamp = datetime.fromisoformat(receipt["captured_utc"].replace("Z","+00:00"))
        age = (datetime.now(timezone.utc)-stamp).total_seconds()
        if not 0 <= age <= spec["common"]["admission_policy"]["receipt_max_age_seconds"]:
            raise ValueError("stale host configuration observation")
    except (TypeError,AttributeError) as exc:
        raise ValueError("typed current host observation timestamp required") from exc
    config = responses.get("config",{}).get("result",{}).get("config",{})
    for key in ("model_reasoning_effort","service_tier","web_search",
                "features.hooks","features.apps","features.multi_agent",
                "agents.max_concurrent_threads_per_session","agents.max_depth",
                "sandbox_workspace_write.network_access"):
        actual = config
        for part in key.split("."):
            actual = actual.get(part) if isinstance(actual,dict) else None
        if not attempt.same(actual,adapter["config"][key]):
            raise ValueError("observed host setting mismatch: " + key)
    for section in ("mcp_servers","plugins"):
        entries = config.get(section,{})
        if not isinstance(entries,dict):
            raise ValueError("typed host tool configuration required")
        for name, entry in entries.items():
            key = section+"."+name+".enabled"
            if (not isinstance(entry,dict) or entry.get("enabled") is not False
                    or adapter["config"].get(key) is not False):
                raise ValueError("external host tool exposure changed")
    data = responses.get("inventory",{}).get("result",{}).get("data")
    if not isinstance(data,list) or len(data) != 1 or not isinstance(data[0],dict):
        raise ValueError("single workspace inventory required")
    entry = data[0]
    if cwd is not None and entry.get("cwd") != str(Path(cwd).resolve()):
        raise ValueError("host observation belongs to another workspace")
    skills = entry.get("skills")
    if entry.get("errors") != [] or not isinstance(skills,list) or not skills:
        raise ValueError("complete observed skill inventory required")
    disabled = {s["path"] for s in adapter["config"]["skills.config"]}
    observed, system = set(), set()
    for skill in skills:
        if (not isinstance(skill,dict) or not isinstance(skill.get("path"),str)
                or not skill["path"] or type(skill.get("enabled")) is not bool
                or skill.get("scope") not in ("system","user","repo","admin")):
            raise ValueError("typed skill metadata required")
        if skill["path"] in observed:
            raise ValueError("duplicate observed skill path")
        observed.add(skill["path"])
        if skill["scope"] != "system":
            if skill["enabled"] is not False or skill["path"] not in disabled:
                raise ValueError("non-system skill exposure changed")
        elif skill["enabled"]:
            system.add(skill["path"])
    frozen_host = attempt.snapshot(spec["inputs"]["host_inventory"])
    if not {str(Path(p).resolve()) for p in observed} <= set(frozen_host):
        raise ValueError("observed skill sources must be frozen host inputs")
    return {"admission":admit(spec,observation),"observation":observation,
            "binding":copy.deepcopy(binding),"observed_skill_count":len(observed),
            "enabled_system_skills":sorted(system),
            "limits":receipt["limits"]}


def _declared_children(events):
    children = set()
    for event in events:
        item = event.get("item") or event.get("payload")
        if isinstance(item,dict) and item.get("tool") == "spawn_agent":
            values = item.get("receiver_thread_ids",item.get("receiverThreadIds"))
            if isinstance(values,list):
                children.update(v for v in values if isinstance(v,str))
    return children


def retain_rollouts(root_id, exec_path, codex_home, destination):
    """Copy only observed UUID-linked filenames, never search unrelated history contents."""
    destination = Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    events, issues = _events(exec_path)
    queue, seen, paths, manifests = [root_id,*sorted(_declared_children(events))], set(), [], {}
    while queue:
        sid = queue.pop(0)
        if sid in seen:
            continue
        seen.add(sid)
        if len(seen) > 64:
            issues.append("observed-link collection ceiling reached")
            break
        if not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}",sid):
            issues.append("unsupported observed session identity: " + sid)
            continue
        found = list((Path(codex_home) / "sessions").glob("*/*/*/*-"+sid+".jsonl"))
        if len(found) != 1:
            issues.append("unique rollout unavailable: " + sid)
            continue
        source = found[0]
        if source.is_symlink() or not source.is_file():
            issues.append("regular rollout unavailable: " + sid)
            continue
        target = destination / (sid+".jsonl")
        try:
            data = source.read_bytes()
            with target.open("xb") as stream:
                stream.write(data)
        except OSError as exc:
            issues.append("rollout retention: " + sid + ": " + str(exc))
            continue
        manifests[str(source.resolve())] = attempt.digest(data)
        paths.append(str(target.resolve()))
        try:
            if source.read_bytes() != data:
                issues.append("rollout changed during retention: " + sid)
        except OSError:
            issues.append("rollout disappeared during retention: " + sid)
        child_events, errors = _events(target)
        issues.extend(errors)
        queue.extend(sorted(_declared_children(child_events)-seen))
    receipt = _write(destination / "receipt.json",{
        "root_id":root_id,"observed_ids":sorted(seen),"source_manifest":manifests,
        "retained_manifest":attempt.snapshot(paths) if paths else {},"issues":sorted(set(issues)),
        "limits":["Only emitted spawn links collected; unseen descendants remain unknown.",
                  "Post-terminal copy cannot attest remote child cancellation or completion."]})
    return {"receipt":receipt,"paths":paths,"issues":sorted(set(issues))}


def schedule():
    """Counterbalance order within each class; continuity stages stay paired."""
    episodes = []
    for repetition in (1, 2):
        for index, task_class in enumerate(CLASSES):
            arms = ARMS if (index + repetition) % 2 else tuple(reversed(ARMS))
            for arm in arms:
                ident = "%s-r%d-%s" % (task_class, repetition, arm)
                episodes.append({"episode_id": ident, "task_class": task_class,
                                 "repetition": repetition, "arm": arm,
                                 "slots": [ident + "-s%d" % stage for stage in
                                           ((1, 2) if task_class == "continuity" else (1,))]})
    return episodes


def calibration(binding):
    """Check all retained controls and named defects against current dependencies."""
    record = _read(binding)
    _keys(record, {"schema_version", "source_manifest", "results", "calibrated", "provider_calls"})
    reference = Path(oracle.__file__).with_name("fixtures") / "reference_pilot.py"
    dependencies = [*oracle.EVALUATORS, oracle.CASES, reference]
    if (type(record["schema_version"]) is not int or record["schema_version"] != 1
            or record["calibrated"] is not True or type(record["provider_calls"]) is not int
            or record["provider_calls"] != 0
            or not attempt.same(record["source_manifest"], attempt.snapshot(dependencies))):
        raise ValueError("current calibrated dependencies required")
    definitions = {}
    for node in ast.parse(reference.read_text()).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.endswith("_FAULTS"):
                    definitions[target.id] = ast.literal_eval(node.value)
    expected = {}
    for cls, controls, name in (("multimodule", ("recursive", "flat"), "CONFIG_FAULTS"),
                                ("batch", ("journal", "staged"), "BATCH_FAULTS"),
                                ("continuity", ("dict", "buckets"), "INVENTORY_FAULTS")):
        expected.update({cls + "-" + c: (True, None) for c in controls})
        expected.update({cls + "-" + fault: (False, case)
                         for fault, case in definitions[name].items()})
    rows = record["results"]
    if (not isinstance(rows, list) or len(rows) != len(expected)
            or any(not isinstance(r, dict) for r in rows)
            or {r.get("name") for r in rows} != set(expected)):
        raise ValueError("complete distinct calibration coverage required")
    folder = Path(binding["path"]).parent
    reports = []
    for row in rows:
        control, intended = expected[row["name"]]
        path = folder / (row["name"] + ".json")
        report = _read({"path": str(path), "sha256": row.get("report_sha256")})
        failures = [r["case_id"] for r in report["cases"] if r["passed"] is False]
        if (row.get("control") is not control or row.get("accepted") is not control
                or row.get("calibrated") is not True or row.get("intended_case") != intended
                or report.get("accepted") is not control
                or not attempt.same(row.get("failed_cases"), failures)
                or (not control and intended not in failures)
                or not attempt.validate_binding(report["binding"], oracle.CASES,
                    oracle.sources(folder / row["name"]), oracle.EVALUATORS)
                or not oracle.validate_report(report, folder / row["name"])):
            raise ValueError("contradictory or stale calibration report")
        reports.append(str(path))
    return {"receipt": attempt.snapshot([binding["path"]]),
            "reports": attempt.snapshot(reports), "dependencies": record["source_manifest"]}


def _spec(spec):
    _keys(spec, {"schema_version", "comparison", "policy", "common", "inputs",
                 "treatments", "artifacts", "calibration", "schedule"})
    if (type(spec["schema_version"]) is not int or spec["schema_version"] != 1
            or spec["comparison"] != "native-vs-selected-bundle"
            or not attempt.same(spec["schedule"], schedule())):
        raise ValueError("declared bundle comparison and fixed twelve-episode schedule required")
    policy = attempt.validate_policy(spec["policy"])["values"]
    if policy["max_calls"] != 16 or policy["limit_mode"] == "strict":
        raise ValueError("sixteen roots required; no strict monetary governor implemented")
    _keys(spec["common"], COMMON)
    for key, value in spec["common"].items():
        if value is None or value == "" or value == [] or value == {}:
            raise ValueError("explicit common setting required: " + key)
    admission = spec["common"]["admission_policy"]
    _keys(admission, {"quota_override_authorized", "unknown_admission_authorized",
                      "receipt_max_age_seconds"})
    if (type(admission["quota_override_authorized"]) is not bool
            or type(admission["unknown_admission_authorized"]) is not bool
            or type(admission["receipt_max_age_seconds"]) not in (int, float)
            or not math.isfinite(admission["receipt_max_age_seconds"])
            or admission["receipt_max_age_seconds"] <= 0):
        raise ValueError("typed admission policy required")
    adapter = spec["common"]["adapter"]
    if not isinstance(adapter, dict) or adapter.get("kind") not in ("local-callback", "codex-exec"):
        raise ValueError("declared adapter required")
    if adapter["kind"] == "codex-exec":
        codex_adapter(spec)
    else:
        _keys(adapter, {"kind"})
    _keys(spec["inputs"], INPUTS)
    inputs = {key: _files(paths) for key, paths in spec["inputs"].items()}
    _keys(spec["treatments"], ARMS)
    treatment_files = {}
    for arm in ARMS:
        treatment = spec["treatments"][arm]
        fields = {"prompt", "record_mode"} if arm == "native" else {
            "prompt", "record_mode", "kernel", "canonical", "guard_audit"}
        _keys(treatment, fields)
        if treatment["record_mode"] != ("optional" if arm == "native" else "manual"):
            raise ValueError("competitive native and manual selected bundle required")
        paths = [treatment["prompt"]]
        if arm == "fhorja":
            paths += [treatment["kernel"], treatment["guard_audit"]]
            _files(treatment["canonical"])
            paths += treatment["canonical"]
            audit = attempt.strict_json(Path(treatment["guard_audit"]).read_bytes())
            if Path(treatment["kernel"]).read_text() != render_kernel(audit):
                raise ValueError("kernel differs from audited source passages")
            if not {str(Path(g["source"]["path"]).resolve()) for g in audit["guards"]} <= set(_files(treatment["canonical"])):
                raise ValueError("full guard sources required on demand")
        treatment_files[arm] = _files(paths)
    assets = attempt.artifact_snapshot(spec["artifacts"])
    driver = [Path(__file__), Path(attempt.__file__), Path(usage.__file__)]
    if not set(attempt.snapshot(driver)) <= set(assets["driver"]):
        raise ValueError("pilot, attempt and usage drivers must be frozen")
    if not set(attempt.snapshot(oracle.EVALUATORS)) <= set(assets["scorer"]):
        raise ValueError("all evaluator dependencies must be frozen")
    if str(oracle.CASES.resolve()) not in assets["cases"]:
        raise ValueError("calibrated cases required")
    return {"inputs": inputs, "treatments": treatment_files,
            "artifacts": assets, "calibration": calibration(spec["calibration"])}


def freeze_protocol(destination, spec):
    """Exclusive protocol creation; the caller retains the independent binding."""
    manifests = _spec(spec)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    return _write(destination / "protocol.json", {"spec": copy.deepcopy(spec),
                                                 "manifests": manifests})


def verify_protocol(binding):
    record = _read(binding)
    _keys(record, {"spec", "manifests"})
    if not attempt.same(record["manifests"], _spec(record["spec"])):
        raise ValueError("protocol inputs changed")
    return record


def admit(spec, observation, now=None):
    """Read-only observation only; dollars and credits are different quantities."""
    _keys(observation, {"captured_utc", "ordinary_usage_allowed", "spend_control_reached",
                        "credits_available", "provider_refusal", "observed_actual_usd"})
    if type(observation["provider_refusal"]) is not bool:
        raise ValueError("typed provider refusal required")
    for key in ("ordinary_usage_allowed", "spend_control_reached", "credits_available"):
        if observation[key] is not None and type(observation[key]) is not bool:
            raise ValueError("typed account fields required")
    dollars = observation["observed_actual_usd"]
    if dollars is not None and (type(dollars) not in (int, float)
                               or not math.isfinite(dollars) or dollars < 0):
        raise ValueError("observed real charges must be finite and nonnegative")
    maximum = spec["policy"]["values"]["max_actual_usd"]
    if observation["provider_refusal"] or observation["spend_control_reached"] is True:
        raise ValueError("provider refusal or spend control prevents dispatch")
    if dollars is not None and maximum is not None and dollars >= maximum:
        raise ValueError("observed monetary target reached")
    policy = spec["common"]["admission_policy"]
    fresh = False
    try:
        stamp = datetime.fromisoformat(observation["captured_utc"].replace("Z", "+00:00"))
        if stamp.tzinfo is not None:
            age = ((now or datetime.now(timezone.utc)) - stamp).total_seconds()
            fresh = 0 <= age <= policy["receipt_max_age_seconds"]
    except (TypeError, ValueError, AttributeError):
        pass
    ordinary = (fresh and observation["ordinary_usage_allowed"] is True
                and observation["spend_control_reached"] is False)
    override = (fresh and policy["quota_override_authorized"]
                and observation["credits_available"] is True
                and observation["spend_control_reached"] is False)
    if not ordinary and not override and not policy["unknown_admission_authorized"]:
        raise ValueError("current admission observation unavailable")
    return {"state": "ordinary" if ordinary else "quota-override" if override else "unknown",
            "actual_usd_observed": dollars, "usd_cap_enforced": False,
            "invoice_attribution": "unknown", "observation": copy.deepcopy(observation)}


def reserve(binding, slot_id, observation):
    """Reserve before launch under one controller lock; never recycle a failed slot."""
    record = verify_protocol(binding)
    spec = record["spec"]
    episode = next((e for e in spec["schedule"] if slot_id in e["slots"]), None)
    if episode is None:
        raise ValueError("unallocated invocation")
    state = admit(spec, observation)
    root = Path(binding["path"]).parent
    with (root / "controller.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        reservations = list(root.glob("*-reservation.json"))
        allowed = {slot for e in spec["schedule"] for slot in e["slots"]}
        seen = []
        for path in reservations:
            entry = attempt.strict_json(path.read_bytes())
            if entry.get("protocol_sha256") != binding["sha256"] or entry.get("slot_id") not in allowed:
                raise ValueError("invalid prior reservation")
            seen.append(entry["slot_id"])
        if len(set(seen)) != len(seen) or len(seen) >= 16 or slot_id in seen:
            raise ValueError("root allocation exhausted or already reserved")
        for path in root.glob("*-terminal.json"):
            terminal = attempt.strict_json(path.read_bytes())
            if terminal.get("provider_refusal") is True or terminal.get("status") == "provider-refusal":
                raise ValueError("prior provider refusal prevents further dispatch")
        if slot_id == episode["slots"][-1] and len(episode["slots"]) == 2:
            if not (root / (episode["slots"][0] + "-terminal.json")).is_file():
                raise ValueError("actual stage1 terminal capture required before stage2")
        return _write(root / (slot_id + "-reservation.json"), {
            "slot_id": slot_id, "episode_id": episode["episode_id"],
            "protocol_sha256": binding["sha256"], "admission": state,
            "reserved_utc": datetime.now(timezone.utc).isoformat()})


def planned_outcomes(binding):
    """Always retain twelve denominator rows, including never launched episodes."""
    spec = verify_protocol(binding)["spec"]
    root = Path(binding["path"]).parent
    rows = []
    for episode in spec["schedule"]:
        stages = []
        for slot in episode["slots"]:
            path = root / (slot + "-terminal.json")
            stages.append(attempt.strict_json(path.read_bytes()) if path.is_file() else {
                "slot_id": slot, "status": "reserved-without-terminal" if
                (root / (slot + "-reservation.json")).exists() else "not-launched"})
        rows.append({**episode, "stages": stages, "first_delivery": stages[-1],
                     "stage1_milestone": stages[0] if len(stages) == 2 else None,
                     "corrections": "not-allocated"})
    return rows


def dispatch(binding, slot_id, workspace, observation, callback, host_binding=None, transition_binding=None):
    """One allocated root, sealed before returning to the caller for hidden grading.

    callback(destination, workspace, prompt, timeout) returns the process record
    and writes stdout.jsonl/stderr.txt/process.json in destination. A CLI adapter
    must be declared in frozen driver artifacts; this function never chooses one.
    """
    record = verify_protocol(binding)
    spec = record["spec"]
    host = None
    if spec["common"]["adapter"]["kind"] == "codex-exec":
        if host_binding is None:
            raise ValueError("bound current host observation required")
        host = verify_host(spec,host_binding,workspace)
        if not attempt.same(observation,host["observation"]):
            raise ValueError("admission differs from bound host observation")
    episode = next((e for e in spec["schedule"] if slot_id in e["slots"]), None)
    if episode is None:
        raise ValueError("unallocated invocation")
    workspace = Path(workspace).resolve()
    if any((p / "WORKFLOW_OPERATING_SYSTEM.md").exists() for p in workspace.parents):
        raise ValueError("episode must not inherit workflow repository instructions")
    sources = _product_files(workspace)
    initial_source = attempt.snapshot(sources)
    treatment = spec["treatments"][episode["arm"]]
    prompt = Path(treatment["prompt"]).read_text() + "\n" + (workspace / "README.md").read_text()
    if episode["arm"] == "fhorja":
        prompt += "\n" + Path(treatment["kernel"]).read_text()
        prompt += "\nKeep a compact manual TASK_STATE.md with requirements, observed checks, unknowns and next step.\n"
        prompt += "Canonical references available on demand:\n" + "\n".join(treatment["canonical"])
    # Source validation precedes a reservation; a reserved-but-not-launched crash
    # remains explicit and never grants a retry slot.
    reserve(binding, slot_id, observation)
    root = Path(binding["path"]).parent
    local = root / slot_id
    local.mkdir(exist_ok=False)
    prompt_path = local / "prompt.txt"
    prompt_path.write_text(prompt)
    artifacts = copy.deepcopy(spec["artifacts"])
    artifacts["prompt"] = [str(prompt_path)]
    artifacts["settings"] += [binding["path"]]
    if host is not None:
        artifacts["settings"] += [host_binding["path"],*list(_read(host_binding)["captures"])]
    if transition_binding is not None:
        _read(transition_binding)
        artifacts["settings"].append(transition_binding["path"])
    artifacts["source"] = sources
    trial = attempt.freeze(local / "attempt.json", slot_id, spec["policy"], artifacts)

    def launch():
        verify_protocol(binding)
        if (not attempt.same(initial_source, attempt.verify(trial)["artifacts"]["source"])
                or not attempt.same(attempt.snapshot(_product_files(workspace)), initial_source)):
            raise ValueError("workspace source membership changed before launch")
        return callback(local / "capture", workspace, prompt, spec["policy"]["values"]["timeout_seconds"])

    captured = local / "capture"
    try:
        process = attempt.guarded_launch(trial, launch)
    except Exception as exc:
        captured.mkdir(exist_ok=True)
        for name in ("stdout.jsonl", "stderr.txt"):
            path = captured / name
            if not path.exists():
                path.write_bytes(b"")
        process = {"status": "launch-failure", "error": type(exc).__name__ + ": " + str(exc)}
        if not (captured / "process.json").exists():
            _write(captured / "process.json", process)
    if not isinstance(process, dict) or process.get("status") not in TERMINAL:
        process = {"status": "capture-incomplete", "error": "malformed callback process record"}
    events, errors = _events(captured / "stdout.jsonl")
    root_values = [e.get("thread_id") for e in events if e.get("type") == "thread.started"]
    roots = {v for v in root_values if isinstance(v, str) and v}
    if len(roots) != 1 or len(roots) != len(set(map(repr, root_values))):
        errors.append("coherent retained root thread identity unavailable")
    session = next(iter(roots)) if len(roots) == 1 and all(isinstance(s, str) and s for s in roots) else None
    status = process["status"]
    error_events = [e for e in events if e.get("type") in ("error", "turn.failed")]
    provider_refusal = any(any(marker in str(event.get("message",event.get("error",""))).lower()
                              for marker in ("usage limit","quota","rate limit","spend limit","insufficient credit"))
                          for event in error_events) or process["status"] == "provider-refusal"
    if session is not None and not errors:
        provider_refusal = provider_refusal or any(
            any(marker in str(event.get("message", event.get("error", ""))).lower()
                for marker in ("model is not supported for this account", "model access denied",
                               "model is not available for this account"))
            for event in error_events)
    if provider_refusal:
        status = "provider-refusal"
    if status == "completed":
        if errors:
            status = "malformed"
        elif session is None or not any(e.get("type") == "turn.completed" for e in events) or error_events:
            status = "capture-incomplete"
        if not (captured / "last-message.txt").is_file():
            errors.append("final response unavailable")
            if status == "completed":
                status = "capture-incomplete"
    previous = [attempt.strict_json(p.read_bytes()) for p in root.glob("*-terminal.json")]
    if session is not None and any(p.get("root_session") == session for p in previous):
        errors.append("fresh session identity reused")
        status = "capture-incomplete"
    files = [str(captured / name) for name in ("stdout.jsonl", "stderr.txt", "process.json")]
    if (captured / "last-message.txt").is_file():
        files.append(str(captured / "last-message.txt"))
    rollouts = process.get("rollouts")
    if isinstance(rollouts,dict):
        rollout_record = _read(rollouts["receipt"])
        files += [rollouts["receipt"]["path"],*rollouts["paths"]]
        errors += rollouts["issues"]
        if not attempt.same(rollout_record["retained_manifest"],
                            attempt.snapshot(rollouts["paths"]) if rollouts["paths"] else {}):
            errors.append("retained rollout bytes changed")
        if errors and status == "completed":
            status = "capture-incomplete"
    first = None
    try:
        first = seal_first_delivery(local / "first-delivery", trial, workspace, files)
        if first["capture_complete"] is not True:
            errors.extend(first["capture_errors"])
            status = "capture-incomplete"
    except (OSError, ValueError) as exc:
        errors.append("first-delivery capture: " + str(exc))
        status = "capture-incomplete"
    terminal = {"slot_id": slot_id, "episode_id": episode["episode_id"],
                "status": status, "root_session": session, "process": process,
                "capture_errors": errors, "attempt": trial, "first_delivery": first,
                "protocol_sha256": binding["sha256"],"host_observation":host,
                "provider_refusal":provider_refusal,"continuity_transition":transition_binding}
    terminal_binding = _write(root / (slot_id + "-terminal.json"), terminal)
    return {"binding": terminal_binding, "terminal": terminal}


def capture_process(command, cwd, prompt, destination, timeout, environment=None):
    """File-backed stdout/stderr retain partial bytes without inherited pipe hangs."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    status, error, process, cleanup = "launch-failure", None, None, None
    with (destination / "stdout.jsonl").open("xb") as out, (destination / "stderr.txt").open("xb") as err:
        try:
            process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE,
                                       stdout=out, stderr=err, start_new_session=True,
                                       env=environment)
            process.communicate(prompt.encode(), timeout=timeout)
            status = "completed" if process.returncode == 0 else "exit-failure"
        except subprocess.TimeoutExpired:
            status, cleanup = "timeout", stop_candidate(process)
        except (OSError, ValueError) as exc:
            error = str(exc)
            if process is not None:
                cleanup = stop_candidate(process)
    record = {"status": status, "command": command, "pid": process.pid if process else None,
              "exit_code": process.returncode if process else None, "error": error,
              "cleanup_complete": cleanup, "started_utc": started,
              "ended_utc": datetime.now(timezone.utc).isoformat(),
              "elapsed_seconds": time.monotonic() - tick}
    # An adapter may use the CLI's output file. Otherwise retain the last
    # emitted agent-message text alongside the original unchanged JSONL bytes.
    reply = destination / "last-message.txt"
    if not reply.exists():
        events, errors = _events(destination / "stdout.jsonl")
        messages = [e["item"]["text"] for e in events
                    if isinstance(e.get("item"), dict)
                    and e["item"].get("type") == "agent_message"
                    and isinstance(e["item"].get("text"), str)]
        if messages:
            with reply.open("xb") as stream:
                stream.write(messages[-1].encode())
    _write(destination / "process.json", record)
    return record


def seal_first_delivery(path, binding, workspace, capture_files):
    """Copy and bind actual first-terminal bytes before any grader or continuation."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    product = path / "product"
    product.mkdir()
    links = {}
    root = Path(workspace)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("regular product root required")
    regular = [p for p in _product_files(root) if not Path(p).is_symlink()]
    before = attempt.snapshot(regular)
    def refuse_walk(error):
        raise error
    for folder, dirs, files in os.walk(root, followlinks=False, onerror=refuse_walk):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for name in list(dirs) + files:
            source = Path(folder) / name
            relative = source.relative_to(root)
            target = product / relative
            if source.is_symlink():
                links[str(relative)] = os.readlink(source)
                if name in dirs:
                    dirs.remove(name)
            elif source.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif source.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            else:
                raise ValueError("unsupported product file")
    files = sorted(p for p in product.rglob("*") if p.is_file())
    after = attempt.snapshot([p for p in _product_files(root) if not Path(p).is_symlink()])
    copied = {str(root / p.relative_to(product)):attempt.digest(p.read_bytes()) for p in files}
    stable = attempt.same(before,after) and attempt.same(before,copied)
    index = path / "product-index.json"
    _write(index, {"files": {str(p.relative_to(product)): attempt.digest(p.read_bytes()) for p in files},
                   "symlinks": links, "exclusions": [".git", "__pycache__"]})
    source = [str(index), *map(str, files)]
    artifacts = {"terminal": list(capture_files)}
    receipt = attempt.seal_evidence(path / "receipt.json", binding, artifacts, source)
    return {"receipt": receipt, "product": str(product.resolve()),
            "source_files": source, "artifacts": artifacts,
            "capture_complete": not links and stable,
            "capture_errors": (["product symlink target bytes unknown"] if links else []) +
                              (["product changed during first-delivery copy"] if not stable else []),
            "limits": ["Trusted capture, no adversarial read isolation."]}


def _sealed_inventory(product):
    """Observe every copied file, without following links or hiding new paths."""
    product = Path(product)
    if product.is_symlink() or not product.is_dir():
        raise ValueError("regular sealed product root required")
    files = {}
    def refuse_walk(error):
        raise error
    for folder, dirs, names in os.walk(product,followlinks=False,onerror=refuse_walk):
        for name in dirs + names:
            path = Path(folder) / name
            if path.is_symlink():
                raise ValueError("sealed inventory contains symlink")
            if path.is_file():
                files[str(path.relative_to(product))] = attempt.digest(path.read_bytes())
            elif not path.is_dir():
                raise ValueError("unsupported sealed product file")
    return files


def verify_first_delivery(first, binding):
    """A listed-file receipt also requires exact complete sealed membership."""
    attempt.verify_evidence(first["receipt"],binding,first["artifacts"],first["source_files"])
    product = Path(first["product"])
    index = product.parent / "product-index.json"
    if index.is_symlink():
        raise ValueError("regular sealed product index required")
    manifest = attempt.strict_json(index.read_bytes())
    if (not isinstance(manifest,dict) or set(manifest) != {"files","symlinks","exclusions"}
            or not isinstance(manifest["files"],dict)
            or not isinstance(manifest["symlinks"],dict)):
        raise ValueError("typed sealed product index required")
    declared = [str(Path(p).resolve()) for p in first["source_files"]]
    expected = [str(index.resolve()),*[str((product/name).resolve()) for name in manifest["files"]]]
    if len(set(declared)) != len(declared) or set(declared) != set(expected):
        raise ValueError("sealed index source membership changed")
    if first.get("capture_complete") is True and manifest["symlinks"]:
        raise ValueError("complete sealed capture contains omitted links")
    if not attempt.same(_sealed_inventory(product),manifest["files"]):
        raise ValueError("sealed product inventory changed")
    return manifest["files"]


def linked_usage(root_id, exec_path, rollout_paths, prices, pricing_date=None):
    """Only explicit copied rollouts; normalize observed parent links, never scan history."""
    exec_events, exec_errors = _events(exec_path)
    sessions, declared, problems = {}, set(), list(exec_errors)
    if any(e.get("type") in ("error", "turn.failed") for e in exec_events):
        problems.append("exec reports failure or contradictory terminal evidence")
    root_values = [e.get("thread_id") for e in exec_events if e.get("type") == "thread.started"]
    if not root_values or any(not isinstance(v, str) or v != root_id for v in root_values):
        problems.append("coherent retained root thread identity unavailable")
    for path in rollout_paths:
        events, errors = _events(path)
        metas = [e.get("payload", {}) for e in events if e.get("type") == "session_meta"]
        if (len(metas) != 1 or not isinstance(metas[0], dict)
                or not isinstance(metas[0].get("id"), str) or not metas[0]["id"]):
            problems.append("rollout session identity unavailable: " + str(path))
            continue
        meta = metas[0]
        parent_values = [meta[k] for k in ("parent_thread_id", "parentThreadId") if meta.get(k) is not None]
        source = meta.get("source")
        if isinstance(source, dict):
            for key in ("subagent", "subAgent"):
                child = source.get(key)
                if isinstance(child, dict):
                    spawn = child.get("thread_spawn")
                    if isinstance(spawn, dict) and spawn.get("parent_thread_id") is not None:
                        parent_values.append(spawn["parent_thread_id"])
        parents = {p for p in parent_values if isinstance(p, str) and p}
        if len(parents) > 1 or any(not isinstance(p, str) or not p for p in parent_values):
            errors.append("conflicting or malformed parent link")
        parent = next(iter(parents)) if len(parents) == 1 else None
        sid = meta["id"]
        if sid in sessions:
            problems.append("duplicate retained session: " + sid)
            continue
        sessions[sid] = {"parent": parent, "model": None, "events": events,
                         "errors": errors, "sha256": attempt.digest(Path(path).read_bytes())}
    # Exec's turn totals and rollout's cumulative/per-call view are alternatives.
    # Without a rollout retain the root total as a fallback, explicitly incomplete.
    totals = [e.get("usage") for e in exec_events if e.get("type") == "turn.completed"]
    if not totals or any(not usage.valid_usage(t) for t in totals):
        problems.append("exec terminal usage unavailable or malformed")
    if root_id not in sessions:
        problems.append("root rollout unavailable; exec-only capture incomplete")
        events = [{"type": "event_msg", "payload": {"type": "token_count",
                   "info": {"total_token_usage": total}}} for total in totals]
        sessions[root_id] = {"parent": None, "model": None, "events": events,
                             "sha256": attempt.digest(Path(exec_path).read_bytes()), "errors": []}
    elif sessions[root_id]["parent"] is not None:
        problems.append("fresh root has a parent")
    for event in [*exec_events, *[e for s in sessions.values() for e in s["events"]]]:
        item = event.get("item") or event.get("payload")
        if not isinstance(item, dict):
            continue
        if item.get("tool") == "spawn_agent":
            children = item.get("receiver_thread_ids", item.get("receiverThreadIds"))
            if not isinstance(children, list) or any(not isinstance(c, str) or not c for c in children):
                problems.append("spawn child identity unavailable")
            else:
                declared.update(children)
    result = usage.ledger(sessions, root_id, prices, pricing_date, declared)
    for sid in set(sessions) - set(result["sessions"]):
        problems.append("unlinked retained session: " + sid)
    root_rows = [r for r in result["records"] if r["session_id"] == root_id]
    if totals and root_rows:
        total = totals[-1]
        observed = {k: sum(r["usage"][k] for r in root_rows) for k in usage.FIELDS}
        if not usage.valid_usage(total) or any(total[k] != observed[k] for k in usage.FIELDS):
            problems.append("exec and rollout cumulative totals do not reconcile")
    result["issues"] = sorted(set(result["issues"] + problems))
    result["complete"] = not result["issues"]
    if result["issues"]:
        result["cost_usd"] = None
    result["actual_invoice_usd"] = None
    result["provider_model_delivery"] = "unknown"
    result["descendant_completeness"] = "unknown beyond observed links"
    return result


def prepare_run(destination, workspace_root, spec, pricing=None):
    """Prepare public workspaces and an independently held run binding, without calls."""
    destination, workspace_root = Path(destination).resolve(), Path(workspace_root).resolve()
    if (destination == workspace_root or destination in workspace_root.parents
            or workspace_root in destination.parents
            or any((p / "WORKFLOW_OPERATING_SYSTEM.md").exists()
                   for p in [workspace_root, *workspace_root.parents])):
        raise ValueError("separate public workspace and controller roots required")
    pricing = pricing if pricing is not None else {
        "rates":{}, "pricing_date":None, "credits_per_usd":None, "source":"unknown"}
    _keys(pricing, {"rates", "pricing_date", "credits_per_usd", "source"})
    if not isinstance(pricing["rates"], dict) or not isinstance(pricing["source"], str):
        raise ValueError("explicit pricing provenance required")
    rate = pricing["credits_per_usd"]
    if rate is not None and (type(rate) not in (int,float) or not math.isfinite(rate) or rate <= 0):
        raise ValueError("finite positive equivalent-credit conversion required")
    _spec(spec)
    if destination.exists() or workspace_root.exists():
        raise FileExistsError("new controller and workspace destinations required")
    destination.mkdir(parents=True)
    workspace_root.mkdir(parents=True)
    measurement = destination / "pricing.json"
    _write(measurement, pricing)
    frozen = copy.deepcopy(spec)
    frozen["artifacts"]["settings"].append(str(measurement))
    fixture_path = str(Path(fixtures.__file__).resolve())
    if fixture_path not in {str(Path(p).resolve()) for p in frozen["artifacts"]["driver"]}:
        frozen["artifacts"]["driver"].append(fixture_path)
    workspaces = {}
    for episode in frozen["schedule"]:
        product = fixtures.prepare(workspace_root / episode["episode_id"], episode["task_class"])
        workspaces[episode["episode_id"]] = {
            "path":str(product), "initial_manifest":attempt.snapshot(_product_files(product))}
    protocol = freeze_protocol(destination / "protocol", frozen)
    return _write(destination / "run.json", {
        "schema_version":1, "protocol":protocol, "workspace_root":str(workspace_root),
        "workspaces":workspaces, "pricing":{
            "path":str(measurement), "sha256":attempt.digest(measurement.read_bytes())}})


def verify_run(binding):
    record = _read(binding)
    _keys(record, {"schema_version", "protocol", "workspace_root", "workspaces", "pricing"})
    if type(record["schema_version"]) is not int or record["schema_version"] != 1:
        raise ValueError("typed run version required")
    spec = verify_protocol(record["protocol"])["spec"]
    _keys(record["workspaces"], {e["episode_id"] for e in spec["schedule"]})
    for episode, workspace in record["workspaces"].items():
        _keys(workspace, {"path", "initial_manifest"})
        if Path(workspace["path"]) != Path(record["workspace_root"]) / episode:
            raise ValueError("workspace identity changed")
    pricing = _read(record["pricing"])
    if str(Path(record["pricing"]["path"]).resolve()) not in {
            str(Path(p).resolve()) for p in spec["artifacts"]["settings"]}:
        raise ValueError("pricing must be frozen before results")
    return record, spec, pricing


def _committed_driver(spec):
    """Paid adapter dispatch requires current repository driver bytes committed."""
    root = Path(__file__).resolve().parents[2]
    commit = subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    paths = [p for role in ("driver","scorer","cases") for p in spec["artifacts"][role]]
    for path in sorted(set(paths)):
        path = Path(path).resolve()
        if path.is_relative_to(root):
            data = subprocess.check_output(["git","-C",str(root),"show",
                                           commit+":"+str(path.relative_to(root))])
            if attempt.digest(data) != attempt.digest(path.read_bytes()):
                raise ValueError("commit the final driver before provider dispatch")
    return commit


def grade_slot(protocol, slot_id, protection=None):
    """Run withheld checks on a copy; never execute candidates in the sealed product."""
    spec = verify_protocol(protocol)["spec"]
    episode = next((e for e in spec["schedule"] if slot_id in e["slots"]), None)
    if episode is None:
        raise ValueError("unallocated grading slot")
    root = Path(protocol["path"]).parent
    terminal = attempt.strict_json((root / (slot_id+"-terminal.json")).read_bytes())
    first = terminal.get("first_delivery")
    folder = Path(tempfile.mkdtemp(prefix="grading-",dir=root / slot_id))
    report, error, coherent = None, None, False
    try:
        if not isinstance(first,dict) or first.get("capture_complete") is not True:
            raise ValueError("complete sealed first delivery unavailable")
        originals = verify_first_delivery(first,terminal["attempt"])
        product = folder / "product"
        shutil.copytree(first["product"], product)
        copied = _sealed_inventory(product)
        if not attempt.same(originals,copied):
            raise ValueError("grading copy differs from first delivery")
        version = 1 if episode["task_class"] == "continuity" and slot_id == episode["slots"][0] else 2
        report = oracle.evaluate(product,episode["task_class"],version=version,protection=protection)
        coherent = oracle.validate_report(report,product)
        if not coherent:
            error = "independent grader report is not coherent"
        verify_first_delivery(first,terminal["attempt"])
    except (OSError,ValueError,TypeError,KeyError) as exc:
        error = type(exc).__name__+": "+str(exc)
    return _write(folder / "grade.json", {
        "slot_id":slot_id,"protocol_sha256":protocol["sha256"],
        "first_delivery_receipt":first.get("receipt") if isinstance(first,dict) else None,
        "report":report,"coherent":coherent if error is None else False,"error":error})


def _relative_manifest(workspace, excluded=()):
    return {str(Path(p).relative_to(workspace)):digest for p,digest in
            attempt.snapshot([p for p in _product_files(workspace)
                if str(Path(p).relative_to(workspace)) not in excluded]).items()}


def prepare_transition(binding, episode, previous, workspace):
    """Journal exact pre/postimages before publishing any public stage2 file."""
    run,spec,pricing = verify_run(binding)
    controller = Path(run["protocol"]["path"]).parent
    slot = episode["slots"][1]
    path = controller / (slot+"-transition.json")
    prior = _read(previous["grade"])
    terminal = _read(previous["terminal"])
    first = terminal["first_delivery"]
    sealed = verify_first_delivery(first,terminal["attempt"])
    if not path.exists():
        if not attempt.same(_relative_manifest(workspace),sealed):
            raise ValueError("stage1 workspace differs from actual first delivery")
        staging = Path(tempfile.mkdtemp(prefix=slot+"-transition-",dir=controller)) / "product"
        shutil.copytree(first["product"],staging)
        protection = fixtures.advance_continuity(staging,prior["report"])
        target = _relative_manifest(staging)
        writes = {name:(staging / name).read_bytes().hex() for name in target if target[name] != sealed.get(name)}
        temps = {name:str(Path(name).with_name(".fhorja-transition-"+str(uuid.uuid4()))) for name in writes}
        _publish(path,{"run_sha256":binding["sha256"],"terminal":previous["terminal"],
            "grade":previous["grade"],"before":sealed,"after":target,
            "writes":writes,"temporaries":temps,"protection":protection})
    journal_binding = {"path":str(path),"sha256":attempt.digest(path.read_bytes())}
    prepared = _read(journal_binding)
    if (prepared["run_sha256"] != binding["sha256"] or prepared["terminal"] != previous["terminal"]
            or prepared["grade"] != previous["grade"]):
        raise ValueError("prepared transition belongs to another first delivery")
    current = _relative_manifest(workspace,prepared["temporaries"].values())
    for name in set(current) | set(prepared["before"]) | set(prepared["after"]):
        if current.get(name) not in (prepared["before"].get(name),prepared["after"].get(name)):
            raise ValueError("unexpected user edit during continuity publication")
    for name,hex_bytes in prepared["writes"].items():
        target,temporary = workspace / name, workspace / prepared["temporaries"][name]
        if temporary.is_symlink():
            raise ValueError("transition temporary is not a regular file")
        if current.get(name) != prepared["after"][name]:
            data = bytes.fromhex(hex_bytes)
            if attempt.digest(data) != prepared["after"][name]:
                raise ValueError("transition postimage changed")
            temporary.write_bytes(data)
            os.replace(temporary,target)
        elif temporary.exists():
            temporary.unlink()
    if not attempt.same(_relative_manifest(workspace),prepared["after"]):
        raise ValueError("continuity publication incomplete")
    return journal_binding,prepared["protection"]


def recover_slot(binding, slot_id):
    """Offline-only assessment recovery; never calls an adapter or changes reservations."""
    run,spec,pricing = verify_run(binding)
    controller = Path(run["protocol"]["path"]).parent
    if slot_id not in {s for e in spec["schedule"] for s in e["slots"]}:
        raise ValueError("unallocated recovery slot")
    result_path = controller / (slot_id+"-result.json")
    if result_path.exists():
        report_run(binding)
        return {"path":str(result_path),"sha256":attempt.digest(result_path.read_bytes())}
    path = controller / (slot_id+"-terminal.json")
    if not path.is_file():
        raise ValueError("no retained terminal; reservation cannot authorize another call")
    terminal_binding = {"path":str(path),"sha256":attempt.digest(path.read_bytes())}
    terminal = _read(terminal_binding)
    if terminal["slot_id"] != slot_id or terminal["protocol_sha256"] != run["protocol"]["sha256"]:
        raise ValueError("terminal belongs to another slot")
    transition = terminal.get("continuity_transition")
    protection = _read(transition)["protection"] if transition is not None else None
    grade = grade_slot(run["protocol"],slot_id,protection)
    return _publish(result_path,{"slot_id":slot_id,"terminal":terminal_binding,"grade":grade,
        "run_sha256":binding["sha256"],"protection":protection,"account_after":None,
        "account_after_error":"offline recovery; no post-invocation account observation retained"})


def execute_slot(binding, slot_id, callback=None, observation=None):
    """One allocated invocation. Interrupted reservations are never retried."""
    run, spec, pricing = verify_run(binding)
    protocol = run["protocol"]
    controller = Path(protocol["path"]).parent
    episode = next((e for e in spec["schedule"] if slot_id in e["slots"]), None)
    if episode is None:
        raise ValueError("unallocated invocation")
    if (controller / (slot_id+"-reservation.json")).exists():
        raise ValueError("allocated invocation already reserved; no retry")
    workspace_record = run["workspaces"][episode["episode_id"]]
    workspace = Path(workspace_record["path"])
    paid = spec["common"]["adapter"]["kind"] == "codex-exec"
    if paid:
        if callback is not None or observation is not None:
            raise ValueError("paid adapter cannot substitute a callback or admission receipt")
        _committed_driver(spec)
    protection = None
    transition_binding = None
    if slot_id == episode["slots"][0]:
        if not attempt.same(workspace_record["initial_manifest"],attempt.snapshot(_product_files(workspace))):
            raise ValueError("public seed changed before its first invocation")
    else:
        previous = attempt.strict_json((controller / (episode["slots"][0]+"-result.json")).read_bytes())
        prior = _read(previous["grade"])
        if prior["coherent"] is not True or prior["report"] is None:
            raise ValueError("actual coherent stage1 assessment required for transition")
        if not oracle.validate_report(prior["report"],Path(previous["grade"]["path"]).parent / "product"):
            raise ValueError("actual stage1 graded sources changed")
        transition_binding,protection = prepare_transition(binding,episode,previous,workspace)
    host = None
    if paid:
        host = observe_host(spec,workspace,controller / (slot_id+"-host-before-"+str(uuid.uuid4())))
        observation = host_admission(host)
        callback = codex_callback(protocol)
    elif callback is None or observation is None:
        raise ValueError("local adapter requires explicit callback and observation")
    captured = dispatch(protocol,slot_id,workspace,observation,callback,host_binding=host,
                        transition_binding=transition_binding)
    grade = grade_slot(protocol,slot_id,protection)
    result = {"slot_id":slot_id,"terminal":captured["binding"],"grade":grade,
              "run_sha256":binding["sha256"],"protection":protection,
              "account_after":None,"account_after_error":None}
    if host is not None:
        try:
            result["account_after"] = observe_host(spec,workspace,controller / (slot_id+"-host-after"))
        except (OSError,ValueError) as exc:
            result["account_after_error"] = str(exc)
    return _publish(controller / (slot_id+"-result.json"),result)


def report_run(binding):
    """Twelve planned denominator rows; acceptance, process and observability stay separate."""
    run, spec, pricing = verify_run(binding)
    controller = Path(run["protocol"]["path"]).parent
    episodes = []
    for episode in planned_outcomes(run["protocol"]):
        stages = []
        for stage in episode["stages"]:
            slot = stage["slot_id"]
            result_path = controller / (slot+"-result.json")
            accepted, grading_error, ledger = None, None, None
            record = None
            if result_path.exists():
                record = attempt.strict_json(result_path.read_bytes())
                if record["run_sha256"] != binding["sha256"] or record["slot_id"] != slot:
                    raise ValueError("result belongs to another run")
                terminal = _read(record["terminal"])
                if not attempt.same(terminal,stage):
                    raise ValueError("terminal capture changed")
                first = terminal.get("first_delivery")
                if isinstance(first,dict):
                    verify_first_delivery(first,terminal["attempt"])
                grade = _read(record["grade"])
                if grade["protocol_sha256"] != run["protocol"]["sha256"] or grade["slot_id"] != slot:
                    raise ValueError("grade belongs to another slot")
                grading_error = grade["error"]
                if grade["coherent"] is True:
                    product = Path(record["grade"]["path"]).parent / "product"
                    if not oracle.validate_report(grade["report"],product):
                        raise ValueError("graded source or report changed")
                    accepted = grade["report"]["accepted"]
            # Terminal capture survives an interruption before result publication.
            # Report retained usage independently of whether grading has finished.
            first = stage.get("first_delivery")
            if isinstance(first,dict):
                verify_first_delivery(first,stage["attempt"])
            captured = controller / slot / "capture"
            if isinstance(stage.get("root_session"),str):
                ledger = linked_usage(stage["root_session"],captured / "stdout.jsonl",
                    stage["process"].get("rollouts",{}).get("paths",[]),
                    pricing["rates"],pricing["pricing_date"])
            cost = ledger["cost_usd"] if ledger else None
            credits = (cost*pricing["credits_per_usd"] if cost is not None
                       and pricing["credits_per_usd"] is not None else None)
            stages.append({"slot_id":slot,"status":stage["status"],"accepted":accepted,
                "grading_error":grading_error,"elapsed_seconds":stage.get("process",{}).get("elapsed_seconds"),
                "root_session":stage.get("root_session"),"usage":ledger,
                "equivalent_usd":cost,"equivalent_credits":credits,"actual_invoice_usd":None,
                "account_before":stage.get("host_observation",{}),
                "account_after":record["account_after"] if record else None,
                "provider_refusal":stage.get("provider_refusal",False)})
        episodes.append({k:episode[k] for k in ("episode_id","task_class","repetition","arm")})
        episodes[-1].update(stages=stages,first_delivery=stages[-1],
            stage1_milestone=stages[0] if len(stages)==2 else None,
            correction_invocations=0,corrections="not allocated",
            within_invocation_self_fixes="retained in raw trace; not independent correction calls")
    return {"schema_version":1,"run_binding":copy.deepcopy(binding),"episodes":episodes,
        "planned_episodes":12,"reserved_roots":len(list(controller.glob("*-reservation.json"))),
        "arms":{arm:{"episodes":6,"accepted":sum(e["first_delivery"]["accepted"] is True
            for e in episodes if e["arm"]==arm),"unknown_quality":sum(e["first_delivery"]["accepted"] is None
            for e in episodes if e["arm"]==arm)} for arm in ARMS},
        "pricing":pricing,"coordination_cost":"not attributed to episode ledger",
        "limits":["Descriptive two-repetition bundle pilot; no causal factor or broad ROI claim.",
                  "Observed account snapshots are account-wide, not per-episode invoice charges.",
                  "Missing usage is unknown; descendant and model delivery limits remain explicit."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--prepare",type=Path,help="JSON request: destination, workspace_root, spec, optional pricing")
    actions.add_argument("--verify",type=Path,help="independently retained run binding")
    actions.add_argument("--execute",type=Path,help="run binding; launches only the named allocated slot")
    actions.add_argument("--report",type=Path,help="run binding; emits the twelve-row report without calls")
    actions.add_argument("--recover",type=Path,help="offline-only grading/result recovery from retained terminal")
    parser.add_argument("--slot",help="allocated slot for --execute or --recover")
    args = parser.parse_args()
    if args.prepare:
        request = attempt.strict_json(args.prepare.read_bytes())
        result = prepare_run(**request)
    else:
        binding = attempt.strict_json((args.verify or args.execute or args.report or args.recover).read_bytes())
        if args.execute or args.recover:
            if not args.slot:
                parser.error("--execute and --recover require --slot")
            result = recover_slot(binding,args.slot) if args.recover else execute_slot(binding,args.slot)
        elif args.report:
            result = report_run(binding)
        else:
            record,spec,pricing = verify_run(binding)
            result = {"local_integrity":"verified","planned_episodes":12,"planned_roots":16,
                      "provider_delivery":"unknown"}
    print(json.dumps(result,sort_keys=True,allow_nan=False))


if __name__ == "__main__":
    main()
