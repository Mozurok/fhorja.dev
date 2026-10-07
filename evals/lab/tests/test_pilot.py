"""Prospective oracle calibration; all execution is local and stdlib-only."""
import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from attempt import strict_json
import pilot_oracle as oracle
import pilot
from pilot_fixtures import prepare, advance_continuity

loader = importlib.util.spec_from_file_location("reference_pilot", LAB / "fixtures/reference_pilot.py")
reference = importlib.util.module_from_spec(loader)
loader.loader.exec_module(reference)


class PilotOracleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.counter = 0

    def product(self, task_class):
        self.counter += 1
        return prepare(self.home / str(self.counter), task_class)

    def assert_calibrated(self, root, task_class, **kwargs):
        result = oracle.evaluate(root, task_class, **kwargs)
        self.assertTrue(result["accepted"], [(r["case_id"], r.get("observed"), r.get("checks")) for r in result["cases"] if not r["passed"]])
        self.assertTrue(oracle.validate_report(result, root), result)
        return result

    def assert_defect(self, result, target):
        self.assertFalse(result["accepted"], "declared defect was accepted at " + target)
        row = next(r for r in result["cases"] if r["case_id"] == target)
        self.assertFalse(row["passed"], row)

    def test_multimodule_calibration(self):
        for algorithm in ("recursive", "flat"):
            with self.subTest(control=algorithm):
                root = self.product("multimodule")
                reference.install_config(root, algorithm)
                self.assert_calibrated(root, "multimodule")
        for fault, target in reference.CONFIG_FAULTS.items():
            with self.subTest(fault=fault):
                root = self.product("multimodule")
                reference.install_config(root, fault=fault)
                self.assert_defect(oracle.evaluate(root, "multimodule"), target)

    def test_batch_calibration(self):
        for algorithm in ("journal", "staged"):
            with self.subTest(control=algorithm):
                root = self.product("batch")
                reference.install_batch(root, algorithm)
                result = self.assert_calibrated(root, "batch")
                partial = next(r for r in result["cases"] if r["case_id"] == "partial-recovery")
                first, last = partial["calls"]
                self.assertTrue(first["actual_partial"])
                self.assertTrue(first["terminated"])
                self.assertNotEqual(first["pid"], last["pid"])
                self.assertEqual(first["files_before_kill"]["a.txt"], b"new-a\n".hex())
                self.assertNotIn("dir/b.txt", first["files_before_kill"])
        for fault, target in reference.BATCH_FAULTS.items():
            with self.subTest(fault=fault):
                root = self.product("batch")
                reference.install_batch(root, fault=fault)
                self.assert_defect(oracle.evaluate(root, "batch"), target)

    def test_batch_accepts_valid_order_and_same_process_recovery(self):
        for mode in ("reverse", "recover"):
            with self.subTest(mode=mode):
                root = self.product("batch")
                reference.install_batch(root)
                path = root / "batch_tool.py"
                text = path.read_text()
                if mode == "reverse":
                    text = text.replace('outputs=r["outputs"]; names=list(outputs)', 'outputs=dict(reversed(list(r["outputs"].items()))); names=list(outputs)')
                else:
                    text = text.replace('else: io.replace(path,body)', 'else:\n            try: io.replace(path,body)\n            except OSError:\n                if read(path)!=body: raise')
                path.write_text(text)
                self.assert_calibrated(root, "batch")

    def test_batch_interruption_drains_large_diagnostics(self):
        for stream in ("stdout", "stderr"):
            with self.subTest(stream=stream):
                root = self.product("batch")
                reference.install_batch(root)
                path = root / "batch_tool.py"
                prefix = ('import os,sys\nif os.environ.get("PILOT_PAUSE_DESTINATIONS"):\n'
                          '    sys.' + stream + '.write("d"*275000)\n'
                          '    sys.' + stream + '.flush()\n')
                path.write_text(prefix + path.read_text())
                report = self.assert_calibrated(root, "batch")
                for name in ("partial-recovery", "external-edit"):
                    row = next(r for r in report["cases"] if r["case_id"] == name)
                    self.assertTrue(row["calls"][0]["actual_partial"])
                    self.assertEqual(row["calls"][0][stream], "d"*275000)
                altered = copy.deepcopy(report)
                row = next(r for r in altered["cases"] if r["case_id"] == "partial-recovery")
                row["calls"][0][stream + "_hex"] = "00"
                self.assertFalse(oracle.validate_report(altered, root))

    def test_batch_metadata_io_bypass_is_rejected(self):
        root = self.product("batch")
        reference.install_batch(root)
        path = root / "batch_tool.py"
        text = path.read_text().replace('else: io.replace(path,body)', 'else:\n            if path.startswith(".batch/") or path=="receipts.json":\n                target=root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(body)\n            else: io.replace(path,body)')
        path.write_text(text)
        result = oracle.evaluate(root, "batch")
        self.assertFalse(result["accepted"])
        self.assertFalse(result["cases"][0]["checks"]["all_writes_via_public_io"])

    def test_initial_direct_journal_cannot_be_hidden_by_later_io(self):
        root = self.product("batch")
        reference.install_batch(root)
        path = root / "batch_tool.py"
        code = path.read_text()
        initial = '        write(state,encoded(journal))'
        self.assertEqual(code.count(initial), 1)
        replacement = ('        target=root/state; target.parent.mkdir(parents=True,exist_ok=True)\n'
                       '        target.write_text(encoded(journal))\n'
                       '        journal["phase"]="ready"\n'
                       '        write(state,encoded(journal))')
        path.write_text(code.replace(initial, replacement))
        report = oracle.evaluate(root, "batch")
        self.assertFalse(report["accepted"])
        self.assertFalse(report["cases"][0]["checks"]["all_writes_via_public_io"])

    def test_malformed_receipt_retains_raw_calls(self):
        root = self.product("batch")
        reference.install_batch(root, fault="duplicate-receipt")
        report = oracle.evaluate(root, "batch")
        self.assertFalse(report["accepted"])
        for name in ("completed-replay", "crlf-replay"):
            row = next(r for r in report["cases"] if r["case_id"] == name)
            self.assertFalse(row["passed"])
            self.assertEqual(len(row["calls"]), 2)
            self.assertTrue(row["receipt_errors"])
            self.assertIn("receipts.json", row["filesystem"])
            for call in row["calls"]:
                self.assertIsInstance(call["stdout"], str)
                self.assertIsInstance(call["stderr"], str)
                self.assertIsInstance(call["pid"], int)
                self.assertIsInstance(call["exit_code"], int)

    def test_batch_rejects_extra_status_fields(self):
        root = self.product("batch")
        reference.install_batch(root)
        path = root / "batch_tool.py"
        path.write_text(path.read_text().replace(
            'print(json.dumps({"result":{"status":status}}))',
            'print(json.dumps({"result":dict(status=status, extra=True) if status=="invalid" else {"status":status}}))'))
        report = oracle.evaluate(root, "batch")
        self.assert_defect(report, "invalid-id")
        row = next(r for r in report["cases"] if r["case_id"] == "invalid-id")
        self.assertFalse(row["checks"]["last_protocol"])

    def test_bad_filesystem_retains_raw_calls(self):
        root = self.product("batch")
        (root / "batch_tool.py").write_text(
            'import sys,json\nfrom pathlib import Path\nr=json.load(sys.stdin)\n'
            'p=Path(r["root"])/"a.txt"\np.write_bytes(bytes([255]))\n'
            'print(json.dumps({"result":{"status":"applied"}}))\n')
        report = oracle.evaluate(root, "batch")
        self.assert_defect(report, "normal")
        row = next(r for r in report["cases"] if r["case_id"] == "normal")
        self.assertEqual(len(row["calls"]), 1)
        self.assertEqual(row["calls"][0]["exit_code"], 0)
        self.assertIn('"applied"', row["calls"][0]["stdout"])
        self.assertEqual(row["filesystem"]["a.txt"], "ff")
        self.assertIn("UnicodeDecodeError", row["error"])
        self.assertTrue(oracle.validate_report(report, root))
        for call_change in ({"exit_code": {}}, {"stdout": "contradictory"}):
            altered = copy.deepcopy(report)
            altered["cases"][0]["calls"][0].update(call_change)
            self.assertFalse(oracle.validate_report(altered, root))
        for row_change in ({"filesystem":dict(row["filesystem"], **{"a.txt":"6e65772d610a"})},
                           {"error":"batch protocol failure: ValueError"},
                           {"io_audit":[]}, {"calls":[]}):
            altered = copy.deepcopy(report)
            altered["cases"][0].update(row_change)
            self.assertFalse(oracle.validate_report(altered, root))

    def test_batch_failure_annotations_require_raw_failure(self):
        root = self.product("batch")
        reference.install_batch(root)
        report = self.assert_calibrated(root, "batch")
        failure_fields = {"case_id", "expected", "observed", "checks", "calls",
                          "executed", "passed", "error", "filesystem"}
        for index, row in enumerate(report["cases"]):
            for error in ("ValueError", "UnicodeDecodeError"):
                for strip_completed_fields in (False, True):
                    with self.subTest(case=row["case_id"], error=error,
                                      failure_shape=strip_completed_fields):
                        altered = copy.deepcopy(report)
                        failed = altered["cases"][index]
                        failed.update(checks={}, observed=None, executed=False,
                                      passed=False, error="batch protocol failure: " + error)
                        if strip_completed_fields:
                            altered["cases"][index] = {k:v for k,v in failed.items()
                                                       if k in failure_fields}
                        altered["accepted"] = False
                        self.assertFalse(oracle.validate_report(altered, root))

    @unittest.skipUnless(os.name == "posix", "process-group witness uses POSIX")
    def test_interruption_observer_failure_reaps_process(self):
        root = self.product("batch")
        (root / "batch_tool.py").write_text(
            'import json,sys\nfrom pathlib import Path\nfrom public_io import IO\n'
            'r=json.load(sys.stdin)\n(Path(r["root"])/"unexpected").symlink_to("missing")\n'
            'IO(r["root"]).replace("a.txt","x")\n')
        output = self.home / "output"
        output.mkdir()
        witness = self.home / "witness.json"
        request = {"root":str(output), "operation_id":"first",
                   "outputs":{"a.txt":"x", "b.txt":"y"}}
        pid = None
        try:
            observation = oracle.interrupted(
                [str(Path(sys.executable).resolve()), str(root / "batch_tool.py")],
                request, root, output, witness, .5)
            pid = observation["pid"]
            self.assertFalse(observation["actual_partial"])
            self.assertTrue(observation["cleanup_complete"])
            self.assertNotEqual(observation["exit_code"], 0)
            self.assertIn("ValueError", observation["error"])
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)
        except ValueError as exc:
            self.fail("observer failure escaped without a cleanup receipt: " + str(exc))
        finally:
            # A failing pre-fix test must still clean its actual child.
            if pid is None and witness.exists():
                pid = strict_json(witness.read_bytes())["pid"]
            if pid is not None:
                try:
                    os.killpg(pid, 9)
                    os.waitpid(pid, 0)
                except (ProcessLookupError, ChildProcessError):
                    pass

    def continuity(self, algorithm="dict"):
        root = self.product("continuity")
        reference.install_inventory(root, algorithm, version=1, write_helper=True)
        stage1 = self.assert_calibrated(root, "continuity", version=1)
        protection = advance_continuity(root, stage1)
        reference.install_inventory(root, algorithm, version=2)
        return root, protection

    def test_continuity_calibration(self):
        protections = []
        for algorithm in ("dict", "buckets"):
            with self.subTest(control=algorithm):
                root, protection = self.continuity(algorithm)
                protections.append(protection["protected"]["helpers.py"])
                self.assert_calibrated(root, "continuity", protection=protection)
                self.assertTrue(protection["stage1"]["accepted"])
        self.assertNotEqual(*protections)  # Protection comes from actual control work.
        for fault, target in reference.INVENTORY_FAULTS.items():
            with self.subTest(fault=fault):
                root, protection = self.continuity()
                reference.install_inventory(root, fault=fault)
                self.assert_defect(oracle.evaluate(root, "continuity", protection=protection), target)

    def test_continuity_preserves_actual_failed_stage1_and_dirty_work(self):
        root = self.product("continuity")
        (root / "helpers.py").write_text('def normalize(value):\n    return "WRONG"\n')
        (root / "handoff.json").write_text('{"requirement_version":1,"previous_verification":"unknown","remaining":["implementation"]}')
        first = oracle.evaluate(root, "continuity", version=1)
        self.assertFalse(first["accepted"])
        protection = advance_continuity(root, first)
        reference.install_inventory(root)
        second = oracle.evaluate(root, "continuity", protection=protection)
        self.assertFalse(second["accepted"])
        self.assertTrue(second["global_checks"]["helpers.py"])
        self.assertFalse(protection["stage1"]["accepted"])
        for name in ("helpers.py", "notes.txt", "progress.md", "v1_checks.json"):
            with self.subTest(protected=name):
                root, protection = self.continuity()
                (root / name).write_text("discarded")
                result = oracle.evaluate(root, "continuity", protection=protection)
                self.assertFalse(result["accepted"])
                key = "progress_section" if name == "progress.md" else name
                self.assertFalse(result["global_checks"][key])
        for change in ({"requirement_version":1}, {"previous_verification":"passed"}, {"remaining":["bug"]}):
            root, protection = self.continuity()
            handoff = strict_json((root / "handoff.json").read_bytes())
            handoff.update(change)
            (root / "handoff.json").write_text(json.dumps(handoff))
            self.assertFalse(oracle.evaluate(root, "continuity", protection=protection)["accepted"])

    def test_protection_report_drift_is_rejected(self):
        for name in ("notes.txt", "progress.md", "handoff.json", "v1_checks.json"):
            root, protection = self.continuity()
            report = self.assert_calibrated(root, "continuity", protection=protection)
            (root / name).write_text("erased")
            self.assertFalse(oracle.validate_report(report, root), name)

    def test_command_and_failure_evidence_forgery_is_rejected(self):
        root = self.product("multimodule")
        reference.install_config(root)
        report = self.assert_calibrated(root, "multimodule")
        for alteration in (lambda r:r.update(task_class="batch"),
                           lambda r:r["cases"][0]["calls"][1].update(command=["fake-api-command"]),
                           lambda r:r["cases"][0]["calls"][0].update(exit_code=False)):
            altered = copy.deepcopy(report)
            alteration(altered)
            self.assertFalse(oracle.validate_report(altered, root))
        altered = copy.deepcopy(report)
        row = altered["cases"][0]
        call = row["calls"][0]
        call.update(exit_code=None, error="candidate protocol failure: ValueError")
        del call["envelope"]
        row.update(executed=False, passed=False, observed=None)
        row["checks"].update(cli_envelope=False, api_cli_agree=False)
        altered["accepted"] = False
        self.assertFalse(oracle.validate_report(altered, root))

    def test_truthful_failed_calls_remain_valid_negative_evidence(self):
        for code in ('print("not-json")\n', 'raise SystemExit(3)\n',
                     'import time\ntime.sleep(5)\n'):
            with self.subTest(code=code):
                root = self.product("multimodule")
                reference.install_config(root)
                (root / "config_tool/cli.py").write_text(code)
                report = oracle.evaluate(root, "multimodule", timeout=.15)
                self.assertFalse(report["accepted"])
                self.assertTrue(oracle.validate_report(report, root))
                altered = copy.deepcopy(report)
                altered["cases"][0]["calls"][1]["stdout"] = "contradictory"
                self.assertFalse(oracle.validate_report(altered, root))

    def test_completed_invalid_utf8_retains_diagnostics(self):
        root = self.product("multimodule")
        entry = root / "diagnostic.py"
        for stream in (1, 2):
            with self.subTest(stream=stream):
                entry.write_text('import os\nos.write(' + str(stream) + ',bytes([255]))\n')
                call = oracle.run([str(Path(sys.executable).resolve()), str(entry)], {}, root, 2)
                name = "stdout" if stream == 1 else "stderr"
                self.assertEqual(call.get(name + "_hex"), "ff")
                self.assertEqual(call[name], "\ufffd")
                self.assertEqual(call["exit_code"], 0)
                self.assertEqual(call["error"], "candidate protocol failure: UnicodeDecodeError")
                oracle.retained_envelope(call, call["command"])
                altered = copy.deepcopy(call)
                altered[name + "_hex"] = "61"
                with self.assertRaises(ValueError):
                    oracle.retained_envelope(altered, call["command"])

    def test_invalid_path_escape_is_coherent_negative_evidence(self):
        root = self.product("batch")
        reference.install_batch(root)
        path = root / "batch_tool.py"
        code = path.read_text().replace('try: status=execute(json.load(sys.stdin))',
                                       'request=json.load(sys.stdin)\n    try: status=execute(request)')
        path.write_text(code.replace(
            '    print(json.dumps({"result":{"status":status}}))',
            '    if status == "invalid" and "../escaped.txt" in request.get("outputs", {}):\n'
            '        (Path(request["root"]).parent / "escaped.txt").write_bytes(b"escaped")\n'
            '    print(json.dumps({"result":{"status":status}}))'))
        report = oracle.evaluate(root, "batch")
        row = next(r for r in report["cases"] if r["case_id"] == "invalid-path")
        self.assertIsNone(row["calls"][0]["error"])
        self.assertFalse(row["checks"]["invalid_preserves_all_bytes"])
        self.assertFalse(report["accepted"])
        self.assertTrue(oracle.validate_report(report, root))
        self.assertIs(row["escaped_path_exists"], True)

    @unittest.skipUnless(os.name == "posix", "process-group cleanup uses POSIX")
    def test_timeout_with_invalid_utf8_retains_evidence_and_reaps_child(self):
        root = self.product("multimodule")
        entry = root / "diagnostic.py"
        entry.write_text('import os,sys,time\nfrom pathlib import Path\n'
                         'Path("pid.txt").write_text(str(os.getpid()))\n'
                         'sys.stdout.buffer.write(bytes([255]));sys.stdout.flush()\n'
                         'sys.stderr.buffer.write(bytes([254]));sys.stderr.flush()\n'
                         'time.sleep(5)\n')
        pid = None
        try:
            call = oracle.run([str(Path(sys.executable).resolve()), str(entry)], {}, root, .2)
            pid = call["pid"]
            self.assertEqual(call["error"], "candidate timeout")
            self.assertTrue(call["cleanup_complete"])
            self.assertEqual(call["stdout_hex"], "ff")
            self.assertEqual(call["stderr_hex"], "fe")
            self.assertEqual(call["stdout"], "\ufffd")
            self.assertEqual(call["stderr"], "\ufffd")
            oracle.retained_envelope(call, call["command"])
            altered = copy.deepcopy(call)
            altered["stdout_hex"] = "61"
            with self.assertRaises(ValueError):
                oracle.retained_envelope(altered, call["command"])
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)
        finally:
            if pid is None and (root / "pid.txt").is_file():
                pid = int((root / "pid.txt").read_text())
            if pid is not None:
                try:
                    os.killpg(pid, 9)
                    os.waitpid(pid, 0)
                except (ProcessLookupError, ChildProcessError):
                    pass

    def test_truthful_batch_failure_and_status_types(self):
        for fault in ("malformed-io-output", "malformed-receipt", "boolean-status"):
            with self.subTest(fault=fault):
                root = self.product("batch")
                reference.install_batch(root)
                path = root / "batch_tool.py"
                code = path.read_text()
                if fault == "malformed-io-output":
                    code = ('import os\nif os.environ.get("PILOT_FAIL_DESTINATIONS"):\n'
                            '    print("not-json")\n    raise SystemExit(0)\n') + code
                elif fault == "malformed-receipt":
                    code = code.replace('write("receipts.json",encoded(receipt))',
                                        'write("receipts.json","not-json")')
                    self.assertIn('write("receipts.json","not-json")', code)
                else:
                    code = 'import json\nprint(json.dumps({"result":{"status":True}}))\n'
                path.write_text(code)
                report = oracle.evaluate(root, "batch")
                self.assertFalse(report["accepted"])
                self.assertTrue(oracle.validate_report(report, root))
                if fault == "boolean-status":
                    for forged in (1, 1.0):
                        altered = copy.deepcopy(report)
                        altered["cases"][0]["observed"]["status"] = forged
                        self.assertFalse(oracle.validate_report(altered, root))

    def test_batch_initial_and_global_evidence_contradictions(self):
        root = self.product("batch")
        reference.install_batch(root)
        report = self.assert_calibrated(root, "batch")
        for alteration in (lambda c:c.update(stdout='{"result":{"status":"invalid"}}'),
                           lambda c:c.update(exit_code=12)):
            altered = copy.deepcopy(report)
            row = next(r for r in altered["cases"] if r["case_id"] == "completed-replay")
            alteration(row["calls"][0])
            self.assertFalse(oracle.validate_report(altered, root))
        io = root / "public_io.py"
        io.write_bytes(io.read_bytes() + b"\n# modified protected file\n")
        altered = oracle.evaluate(root, "batch")
        self.assertTrue(all(r["passed"] for r in altered["cases"]))
        self.assertFalse(altered["global_checks"]["immutable_public_io"])
        altered["global_checks"]["immutable_public_io"] = True
        altered["accepted"] = True
        self.assertFalse(oracle.validate_report(altered, root))
        root = self.product("batch")
        reference.install_batch(root)
        report = self.assert_calibrated(root, "batch")
        for alteration in (lambda c:c.update(command=["wrong"]),
                           lambda c:c.update(pid=None),
                           lambda c:c.update(stdout="fabricated",exit_code=0),
                           lambda c:c.update(filesystem_after_failure={})):
            altered = copy.deepcopy(report)
            row = next(r for r in altered["cases"] if r["case_id"]=="io-failure")
            alteration(row["calls"][0])
            self.assertFalse(oracle.validate_report(altered, root))

    def test_oracle_binding_and_coverage(self):
        root = self.product("multimodule")
        reference.install_config(root)
        report = self.assert_calibrated(root, "multimodule")
        for change in (lambda r:r.update(accepted=1),
                       lambda r:r.update(cases=[]),
                       lambda r:r["cases"].append(copy.deepcopy(r["cases"][0])),
                       lambda r:r["cases"][0].update(passed=1.0),
                       lambda r:r["cases"][0].update(observed={"error":"invalid"}),
                       lambda r:r["cases"][0]["calls"][0].update(stdout='{"result":true}'),
                       lambda r:r["cases"][0]["calls"][0].update(stdout='{"result":NaN}'),
                       lambda r:r["cases"][0]["calls"][0].update(stdout='{"result":{},"result":{}}')):
            altered = copy.deepcopy(report)
            change(altered)
            self.assertFalse(oracle.validate_report(altered, root))
        config = root / "config_tool/merge.py"
        original = config.read_bytes()
        config.write_bytes(original + b"\n# source drift\n")
        self.assertFalse(oracle.validate_report(report, root))
        config.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "dependencies"):
            oracle.evaluate(root, "multimodule", source_files=[root / "config_tool/cli.py"])
        for alteration in (lambda s:s["cases"].pop(),
                           lambda s:s["cases"].append(s["cases"][0]),
                           lambda s:s.update(schema_version=True),
                           lambda s:s.update(schema_version=1.0)):
            spec = strict_json(oracle.CASES.read_bytes())
            alteration(spec)
            bad = self.home / "bad-cases.json"
            bad.write_text(json.dumps(spec))
            with self.assertRaises(ValueError):
                oracle.evaluate(root, "multimodule", cases=bad)
        declared = root / "extra_dependency.py"
        declared.write_text("VALUE=1\n")
        self.assertFalse(oracle.validate_report(report, root))

    def test_false_success_and_typed_protocol(self):
        root = self.product("multimodule")
        reference.install_config(root)
        cli = root / "config_tool/cli.py"
        for output in ('{"result":true}', '{"result":1.0}', '{"result":1e999}',
                       '{"result":{},"result":{}}', '{"result":{},"success":true}'):
            with self.subTest(output=output):
                cli.write_text("print(" + repr(output) + ")\n")
                self.assertFalse(oracle.evaluate(root, "multimodule")["accepted"])

    def test_fixture_and_evaluator_drift(self):
        root = self.product("multimodule")
        reference.install_config(root)
        cases = self.home / "cases.json"
        cases.write_bytes(oracle.CASES.read_bytes())
        evaluator = self.home / "declared_evaluator_dependency.py"
        evaluator.write_text("VALUE=1\n")
        with patch.object(oracle, "EVALUATORS", [*oracle.EVALUATORS, evaluator]):
            report = oracle.evaluate(root, "multimodule", cases=cases)
            self.assertTrue(report["accepted"])
            self.assertTrue(oracle.validate_report(report, root, cases=cases))
            original = cases.read_bytes()
            cases.write_bytes(original + b"\n")
            self.assertFalse(oracle.validate_report(report, root, cases=cases))
            cases.write_bytes(original)
            evaluator.write_text("VALUE=2\n")
            self.assertFalse(oracle.validate_report(report, root, cases=cases))

    def test_probe_time_source_mutation_refuses_acceptance(self):
        root = self.product("multimodule")
        reference.install_config(root)
        path = root / "config_tool/cli.py"
        path.write_text(path.read_text() + '\nwith open(__file__,"a") as stream:\n    stream.write("# probe mutation\\n")\n')
        report = oracle.evaluate(root, "multimodule")
        self.assertTrue(all(row["passed"] for row in report["cases"]))
        self.assertFalse(report["binding"]["bound"])
        self.assertFalse(report["accepted"])

    def test_cleanup_and_failure_witness(self):
        root = self.product("multimodule")
        reference.install_config(root)
        cli = root / "config_tool/cli.py"
        cli.write_text("import time\ntime.sleep(30)\n")
        started = time.monotonic()
        result = oracle.evaluate(root, "multimodule", timeout=.08)
        self.assertLess(time.monotonic() - started, 8)
        self.assertFalse(result["accepted"])
        for row in result["cases"]:
            call = row["calls"][0]
            self.assertEqual(call["error"], "candidate timeout")
            self.assertTrue(call["cleanup_complete"])
            self.assertIsNotNone(call["exit_code"])

    def test_public_workspace_contains_no_held_oracle_or_cases(self):
        for task_class in ("multimodule", "batch", "continuity"):
            root = self.product(task_class)
            names = {p.name for p in root.rglob("*")}
            self.assertFalse(names & {"reference_pilot.py", "pilot_cases.json", "pilot_oracle.py"})
            with self.assertRaises(FileExistsError):
                prepare(root, task_class)
        with self.assertRaises(ValueError):
            prepare(self.home / "bad", "unknown")


class PilotProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calibration_temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.calibration_temp.cleanup)
        cls.calibration_root = Path(cls.calibration_temp.name) / "calibration"
        oracle.calibrate(cls.calibration_root)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.calls = []
        self.inputs = self.home / "inputs"
        self.inputs.mkdir()
        for name in ("native.txt", "fhorja.txt", "kernel.md", "audit.json", "canonical.md",
                     "facts.txt", "checks.txt", "seed.txt", "host.json", "settings.json"):
            (self.inputs / name).write_text(name + "\n")
        names = sorted(pilot.KERNEL_GUARDS)
        canonical = self.inputs / "canonical.md"
        canonical.write_text("".join(name + " public guard\n" for name in names))
        self.audit = {"schema_version":1,
                      "public_obligations":{cls:names for cls in pilot.CLASSES},
                      "guards":[{
                          "name":name,
                          "source":{"path":str(canonical),"start_line":i+1,"end_line":i+1,
                                    "sha256":pilot.attempt.digest((name+" public guard\n").encode())},
                          "obligations":[cls+":"+name for cls in pilot.CLASSES],
                          "rationale":"Local source binding control"}
                          for i,name in enumerate(names)]}
        (self.inputs / "audit.json").write_text(json.dumps(self.audit))
        (self.inputs / "kernel.md").write_text(pilot.render_kernel(self.audit))
        self.fake = self.inputs / "fake.py"
        self.fake.write_text('import json,sys\n'
            'sys.stdin.read()\n'
            'print(json.dumps({"type":"thread.started","thread_id":sys.argv[1]}))\n'
            'print(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"First delivery"}}))\n'
            'print(json.dumps({"type":"turn.completed","usage":'
            '{"input_tokens":100,"cached_input_tokens":20,"output_tokens":10}}))\n')
        values = {"provider":"codex", "model":"test-model", "effort":"high",
                  "timeout_seconds":2, "max_calls":16, "max_actual_usd":64,
                  "max_equivalent_usd":None, "limit_mode":"monitored",
                  "accept_last_response_overrun":True}
        receipt = self.calibration_root / "calibration.json"
        self.spec = {
            "schema_version":1, "comparison":"native-vs-selected-bundle",
            "policy":{"values":values,"sources":{k:"local test policy" for k in values}},
            "common":{"service_tier":"default", "tools":["shell"],
                      "permissions":"workspace-write", "network":"disabled",
                      "approval":"never", "collaboration":{"threads":2,"depth":1},
                      "instruction_policy":"same observed inventory, delivery unknown",
                      "adapter":{"kind":"local-callback"},
                      "admission_policy":{"quota_override_authorized":True,
                                          "unknown_admission_authorized":False,
                                          "receipt_max_age_seconds":300}},
            "inputs":{k:[str(self.inputs / name)] for k,name in
                      (("facts","facts.txt"),("checks","checks.txt"),
                       ("seeds","seed.txt"),("host_inventory","host.json"))},
            "treatments":{
                "native":{"prompt":str(self.inputs / "native.txt"),"record_mode":"optional"},
                "fhorja":{"prompt":str(self.inputs / "fhorja.txt"),"record_mode":"manual",
                          "kernel":str(self.inputs / "kernel.md"),
                          "canonical":[str(self.inputs / "canonical.md")],
                          "guard_audit":str(self.inputs / "audit.json")}},
            "artifacts":{"driver":[pilot.__file__,str(LAB / "attempt.py"),
                                     str(LAB / "usage.py"),str(self.fake)],
                         "prompt":[str(self.inputs / "native.txt"),str(self.inputs / "fhorja.txt")],
                         "settings":[str(self.inputs / "settings.json")],
                         "scorer":list(map(str,oracle.EVALUATORS)),
                         "cases":[str(oracle.CASES)], "source":[str(self.inputs / "seed.txt")]},
            "calibration":{"path":str(receipt),"sha256":pilot.attempt.digest(receipt.read_bytes())},
            "schedule":pilot.schedule()}
        self.observation = {"captured_utc":datetime.now(timezone.utc).isoformat(),
                            "ordinary_usage_allowed":True,"spend_control_reached":False,
                            "credits_available":True,"provider_refusal":False,
                            "observed_actual_usd":None}

    def freeze(self):
        return pilot.freeze_protocol(self.home / "protocol", self.spec)

    def callback(self, destination, workspace, prompt, timeout):
        self.calls.append(str(destination))
        return pilot.capture_process([sys.executable,str(self.fake),str(uuid.uuid4())],
                                     workspace,prompt,destination,timeout)

    def codex_spec(self):
        skill = self.inputs / "disabled-skill.md"
        skill.write_text("Local disabled skill control\n")
        binary = self.inputs / "fake-codex"
        binary.write_text("#!" + sys.executable + "\n" +
            'import json,sys,os,uuid,pathlib\n'
            'prompt=sys.stdin.read()\n'
            'pathlib.Path("received.json").write_text(json.dumps({"argv":sys.argv[1:],'
            '"environment":sorted(os.environ),"prompt":prompt}))\n'
            'pathlib.Path(sys.argv[sys.argv.index("-o")+1]).write_text("First delivery\\n")\n'
            'print(json.dumps({"type":"thread.started","thread_id":str(uuid.uuid4())}))\n'
            'print(json.dumps({"type":"turn.completed","usage":'
            '{"input_tokens":100,"cached_input_tokens":20,"output_tokens":10}}))\n')
        binary.chmod(0o700)
        spec = copy.deepcopy(self.spec)
        spec["artifacts"]["driver"].append(str(binary))
        spec["inputs"]["host_inventory"].append(str(skill))
        common = spec["common"]
        common["approval"] = "auto-review"
        common["collaboration"] = {"max_concurrent_threads_per_session":2,
                                   "max_depth":1,"enforcement":"unknown"}
        common["adapter"] = {
            "kind":"codex-exec","binary":str(binary),
            "binary_sha256":pilot.attempt.digest(binary.read_bytes()),
            "version":"codex-cli 0.160.0",
            "config":{"model_reasoning_effort":"high","service_tier":"default",
                      "features.hooks":False,"features.apps":False,"features.multi_agent":True,
                      "web_search":"disabled","sandbox_workspace_write.network_access":False,
                      "agents.max_concurrent_threads_per_session":2,"agents.max_depth":1,
                      "skills.config":[{"path":str(skill),"enabled":False}],
                      "mcp_servers.test.enabled":False,"plugins.test.enabled":False},
            "environment":{k:os.environ[k] for k in pilot.ENVIRONMENT if k in os.environ}}
        return spec

    def host_receipt(self,spec,cwd):
        config = {}
        for key,value in spec["common"]["adapter"]["config"].items():
            current = config
            parts = key.split(".")
            for part in parts[:-1]: current = current.setdefault(part,{})
            current[parts[-1]] = value
        responses = {"config":{"result":{"config":config}},
                     "inventory":{"result":{"data":[{"cwd":str(Path(cwd).resolve()),"errors":[],
                        "skills":[{"path":str(self.inputs/"disabled-skill.md"),
                                   "scope":"user","enabled":False}]}]}},
                     "limits":{"result":{"ordinaryUsageAllowed":True,
                        "rateLimits":{"spendControlReached":False,"credits":{"hasCredits":True}}}}}
        path = self.home/"host-receipt.json"
        captures = self.home/"host-raw.jsonl"
        captures.write_text("".join(json.dumps(value)+"\n" for value in responses.values()))
        value = {"captured_utc":datetime.now(timezone.utc).isoformat(),"responses":responses,
                 "error":None,"captures":pilot.attempt.snapshot([str(captures)]),
                 "limits":["Local fixture observation, no runtime delivery attestation."]}
        path.write_text(json.dumps(value))
        return {"path":str(path),"sha256":pilot.attempt.digest(path.read_bytes())}

    def test_kernel_requires_exact_sources_and_all_public_obligations(self):
        self.assertIn("authorization public guard",pilot.render_kernel(self.audit))
        for mutation in ("hash","typed-line","missing-guard","uncovered"):
            with self.subTest(mutation=mutation):
                audit = copy.deepcopy(self.audit)
                if mutation == "hash": audit["guards"][0]["source"]["sha256"] = "0"*64
                if mutation == "typed-line": audit["guards"][0]["source"]["start_line"] = True
                if mutation == "missing-guard": audit["guards"].pop()
                if mutation == "uncovered": audit["guards"][0]["obligations"].pop()
                with self.assertRaises(ValueError): pilot.render_kernel(audit)
        (self.inputs / "kernel.md").write_text("invented shorter kernel")
        with self.assertRaisesRegex(ValueError,"audited source passages"): self.freeze()
        (self.inputs / "kernel.md").write_text(pilot.render_kernel(self.audit))
        self.spec["treatments"]["fhorja"]["canonical"] = [str(self.inputs / "facts.txt")]
        with self.assertRaisesRegex(ValueError,"full guard sources"): self.freeze()

    def test_codex_adapter_retains_session_and_frozen_environment(self):
        spec = self.codex_spec()
        binding = pilot.freeze_protocol(self.home / "protocol",spec)
        root = prepare(self.home / "product","multimodule")
        host = self.host_receipt(spec,root)
        with patch.dict(os.environ,{"OPENAI_API_KEY":"local-fake-secret"}), \
                patch.object(pilot,"_committed_driver",return_value="local fake attestation") as guard:
            result = pilot.dispatch(binding,spec["schedule"][0]["slots"][0],root,
                                    pilot.host_admission(host),pilot.codex_callback(binding),host_binding=host)
        guard.assert_called_once()
        self.assertEqual(result["terminal"]["status"],"capture-incomplete")
        self.assertIn("unique rollout unavailable", " ".join(result["terminal"]["capture_errors"]))
        received = strict_json((root / "received.json").read_bytes())
        argv = received["argv"]
        self.assertEqual(argv[0],"exec")
        self.assertEqual(argv[-1],"-")
        for flag in ("--json","--approve-for-me","--ignore-user-config","--strict-config"):
            self.assertIn(flag,argv)
        for flag in ("--ephemeral","resume","fork","--ignore-rules","--sandbox",
                     "--dangerously-bypass-approvals-and-sandbox"):
            self.assertNotIn(flag,argv)
        self.assertNotIn("OPENAI_API_KEY",received["environment"])
        self.assertEqual(received["prompt"],Path(result["terminal"]["attempt"]["path"]).parent.joinpath("prompt.txt").read_text())
        reply = next(Path(p) for p in result["terminal"]["first_delivery"]["artifacts"]["terminal"]
                     if Path(p).name == "last-message.txt")
        self.assertEqual(reply.read_text(),"First delivery\n")
        first = result["terminal"]["first_delivery"]
        pilot.attempt.verify_evidence(first["receipt"],result["terminal"]["attempt"],
                                     first["artifacts"],first["source_files"])

    def test_codex_adapter_rejects_unreviewed_overrides_and_identity_drift(self):
        spec = self.codex_spec()
        for mutation in ("binary","api-key","identity","limit","model","skill","sandbox"):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(spec)
                adapter = changed["common"]["adapter"]
                if mutation == "binary": adapter["binary_sha256"] = "0"*64
                if mutation == "api-key": adapter["environment"]["OPENAI_API_KEY"] = "fake"
                if mutation == "identity": adapter["environment"]["HOME"] += "/other"
                if mutation == "limit": adapter["config"]["agents.max_depth"] = True
                if mutation == "model": adapter["config"]["model"] = "other-model"
                if mutation == "skill": adapter["config"]["skills.config"][0]["enabled"] = True
                if mutation == "sandbox": changed["common"]["approval"] = "never"
                with self.assertRaises(ValueError):
                    pilot.freeze_protocol(self.home / mutation,changed)

    def test_codex_exec_cold_config_requires_complete_mcp_transports(self):
        spec = self.codex_spec()
        binary = Path(spec["common"]["adapter"]["binary"])
        validation = ('import tomllib\n'
            'values=[sys.argv[i+1] for i,arg in enumerate(sys.argv[:-1]) if arg=="-c"]\n'
            'cold={}\n'
            'for value in values:\n'
            ' key,raw=value.split("=",1);parts=key.split(".");target=cold\n'
            ' for part in parts[:-1]:target=target.setdefault(part,{})\n'
            ' target[parts[-1]]=tomllib.loads("v="+raw)["v"]\n'
            'for server in cold.get("mcp_servers",{}).values():\n'
            ' if not (isinstance(server.get("command"),str) or isinstance(server.get("url"),str)):\n'
            '  sys.stderr.write("invalid transport in cold MCP override\\n");sys.exit(1)\n'
            'prompt=sys.stdin.read()')
        binary.write_text(binary.read_text().replace('prompt=sys.stdin.read()',validation))
        adapter = spec["common"]["adapter"]
        adapter["binary_sha256"] = pilot.attempt.digest(binary.read_bytes())
        adapter["config"]["mcp_servers.legacy.enabled"] = False
        adapter["config"]["plugins.local-test@fixture.enabled"] = False
        binding = pilot.freeze_protocol(self.home/"protocol",spec)
        root = prepare(self.home/"product","multimodule")
        host = self.host_receipt(spec,root)
        with patch.object(pilot,"_committed_driver",return_value="local fake attestation"):
            result = pilot.dispatch(binding,spec["schedule"][0]["slots"][0],root,
                pilot.host_admission(host),pilot.codex_callback(binding),host_binding=host)
        stderr = Path(binding["path"]).parent/spec["schedule"][0]["slots"][0]/"capture/stderr.txt"
        self.assertEqual(result["terminal"]["process"]["exit_code"],0,stderr.read_text())
        self.assertIsNotNone(result["terminal"]["root_session"])
        self.assertTrue((root/"received.json").is_file())

    def test_codex_config_uses_toml_values_without_shell_interpolation(self):
        import tomllib
        value = [{"path":"spaces \"quotes\" $HOME `literal`\nnext","enabled":False}]
        encoded = pilot._toml(value)
        self.assertEqual(tomllib.loads("skills="+encoded)["skills"],value)

    def test_host_observation_boundaries_prevent_paid_callback(self):
        spec = self.codex_spec()
        binding = pilot.freeze_protocol(self.home/"protocol",spec)
        root = prepare(self.home/"product","multimodule")
        host = self.host_receipt(spec,root)
        self.assertEqual(pilot.verify_host(spec,host,root)["observed_skill_count"],1)
        with self.assertRaisesRegex(ValueError,"bound current host"):
            pilot.dispatch(binding,spec["schedule"][0]["slots"][0],root,
                           self.observation,self.callback)
        for mutation in ("skill","config","cwd","not-frozen","stale","external-tool"):
            raw = strict_json(Path(host["path"]).read_bytes())
            if mutation == "skill": raw["responses"]["inventory"]["result"]["data"][0]["skills"][0]["enabled"] = True
            if mutation == "config": raw["responses"]["config"]["result"]["config"]["agents"]["max_depth"] = True
            if mutation == "cwd": raw["responses"]["inventory"]["result"]["data"][0]["cwd"] = str(self.home)
            if mutation == "not-frozen": raw["responses"]["inventory"]["result"]["data"][0]["skills"][0]["scope"] = "system";raw["responses"]["inventory"]["result"]["data"][0]["skills"][0]["path"] = str(self.inputs/"unknown-skill.md")
            if mutation == "stale": raw["captured_utc"] = "2026-01-01T00:00:00+00:00"
            if mutation == "external-tool": raw["responses"]["config"]["result"]["config"]["mcp_servers"]["test"]["enabled"] = True
            path = self.home/(mutation+"-host.json");path.write_text(json.dumps(raw))
            changed = {"path":str(path),"sha256":pilot.attempt.digest(path.read_bytes())}
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                pilot.dispatch(binding,spec["schedule"][0]["slots"][0],root,
                               pilot.host_admission(changed),self.callback,host_binding=changed)
        self.assertEqual(self.calls,[])
        self.assertEqual(list((self.home/"protocol").glob("*-reservation.json")),[])

    def test_readonly_host_observer_preserves_typed_admission_and_no_turns(self):
        spec = self.codex_spec()
        binary = Path(spec["common"]["adapter"]["binary"])
        binary.write_text("#!"+sys.executable+"\n"+
            'import json,sys\n'
            'for line in sys.stdin:\n'
            ' r=json.loads(line);m=r["method"]\n'
            ' if "id" not in r: continue\n'
            ' if m=="account/rateLimits/read": v={"ordinaryUsageAllowed":True,'
            '"rateLimits":{"spendControlReached":False,"credits":{"hasCredits":True}}}\n'
            ' elif m in ("initialize","skills/list","config/read"): v={}\n'
            ' else: raise RuntimeError("mutation or turn request")\n'
            ' print(json.dumps({"id":r["id"],"result":v}),flush=True)\n')
        spec["common"]["adapter"]["binary_sha256"] = pilot.attempt.digest(binary.read_bytes())
        receipt = pilot.observe_host(spec,self.home,self.home/"observation",timeout=1)
        observation = pilot.host_admission(receipt)
        self.assertEqual(pilot.admit(spec,observation)["state"],"ordinary")
        raw = strict_json(Path(receipt["path"]).read_bytes())
        self.assertIsNone(raw["error"])
        self.assertTrue(raw["cleanup_complete"])
        self.assertEqual(set(raw["responses"]),{"initialize","limits","inventory","config"})
        raw["responses"]["limits"]["result"]["ordinaryUsageAllowed"] = 1
        changed = self.home/"typed-host.json"
        changed.write_text(json.dumps(raw))
        observed = pilot.host_admission({"path":str(changed),"sha256":pilot.attempt.digest(changed.read_bytes())})
        self.assertIsNone(observed["ordinary_usage_allowed"])
        self.assertIsNone(observed["observed_actual_usd"])
        (self.home/"observation"/"stdout.jsonl").write_text("changed raw observation")
        with self.assertRaisesRegex(ValueError,"capture changed"): pilot.host_admission(receipt)

    def test_rollout_retention_follows_only_observed_links_and_detects_changes(self):
        root_id, child_id = str(uuid.uuid4()), str(uuid.uuid4())
        folder = self.home / "codex" / "sessions" / "2026" / "10" / "03"
        folder.mkdir(parents=True)
        root = folder/("rollout-date-"+root_id+".jsonl")
        child = folder/("rollout-date-"+child_id+".jsonl")
        root.write_text(json.dumps({"type":"session_meta","payload":{"id":root_id}})+"\n")
        child.write_text(json.dumps({"type":"session_meta","payload":{"id":child_id,"parent_thread_id":root_id}})+"\n")
        unrelated = folder/"unrelated.jsonl";unrelated.write_bytes(b'not readable JSON')
        exec_path = self.home/"exec.jsonl"
        exec_path.write_text(json.dumps({"type":"thread.started","thread_id":root_id})+"\n"+
            json.dumps({"type":"item.completed","item":{"tool":"spawn_agent","receiver_thread_ids":[child_id]}})+"\n")
        result = pilot.retain_rollouts(root_id,exec_path,self.home/"codex",self.home/"retained")
        self.assertEqual(result["issues"],[])
        self.assertEqual({Path(p).name for p in result["paths"]},{root_id+".jsonl",child_id+".jsonl"})
        original = Path.read_bytes
        count = {"reads":0}
        def append_during_copy(path):
            if path == root:
                count["reads"] += 1
                if count["reads"] == 2: path.write_text(path.read_text()+" ")
            return original(path)
        with patch.object(Path,"read_bytes",append_during_copy):
            changed = pilot.retain_rollouts(root_id,exec_path,self.home/"codex",self.home/"changed")
        self.assertIn("rollout changed during retention: "+root_id,changed["issues"])
        missing = pilot.retain_rollouts(str(uuid.uuid4()),exec_path,self.home/"codex",self.home/"missing")
        self.assertTrue(any("unique rollout unavailable" in issue for issue in missing["issues"]))

    def test_first_snapshot_detects_concurrent_product_change(self):
        binding = self.freeze()
        root = prepare(self.home/"product","multimodule")
        original = pilot.shutil.copyfile
        def copy_then_change(source,target):
            result = original(source,target)
            if Path(source).name == "README.md": Path(source).write_text("background change")
            return result
        with patch.object(pilot.shutil,"copyfile",side_effect=copy_then_change):
            result = pilot.dispatch(binding,self.spec["schedule"][0]["slots"][0],root,
                                    self.observation,self.callback)
        self.assertEqual(result["terminal"]["status"],"capture-incomplete")
        self.assertIn("product changed during first-delivery copy",result["terminal"]["capture_errors"])

    def test_protocol_freeze_controls(self):
        binding = self.freeze()
        self.assertEqual(len(pilot.verify_protocol(binding)["spec"]["schedule"]),12)
        with self.assertRaises(FileExistsError):
            pilot.freeze_protocol(self.home / "protocol", self.spec)
        (self.inputs / "facts.txt").write_text("changed factual input")
        root = prepare(self.home / "product", "multimodule")
        with self.assertRaisesRegex(ValueError,"protocol inputs changed"):
            pilot.dispatch(binding,self.spec["schedule"][0]["slots"][0],root,
                           self.observation,self.callback)
        self.assertEqual(self.calls,[])

    def test_protocol_rejects_typed_policy_and_schedule_changes(self):
        for change in ("schedule", "calls", "strict", "common"):
            with self.subTest(change=change):
                spec = copy.deepcopy(self.spec)
                if change == "schedule": spec["schedule"][-1]["repetition"] = True
                if change == "calls": spec["policy"]["values"]["max_calls"] = True
                if change == "strict": spec["policy"]["values"]["limit_mode"] = "strict"
                if change == "common": spec["common"]["network"] = None
                with self.assertRaises(ValueError):
                    pilot.freeze_protocol(self.home / change, spec)
                self.assertFalse((self.home / change).exists())

    def test_protocol_rejects_changed_bound_record(self):
        binding = self.freeze()
        path = Path(binding["path"])
        path.write_text(path.read_text() + " ")
        with self.assertRaisesRegex(ValueError,"bound bytes changed"):
            pilot.verify_protocol(binding)

    def test_calibration_rejects_missing_and_changed_receipts(self):
        receipt = self.calibration_root / "calibration.json"
        record = strict_json(receipt.read_bytes())
        record["results"] = record["results"][:-1]
        path = self.home / "short-calibration.json"
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,"coverage"):
            pilot.calibration({"path":str(path),"sha256":pilot.attempt.digest(path.read_bytes())})
        with self.assertRaises(ValueError):
            pilot.calibration({"path":str(receipt),"sha256":"0"*64})

    def test_calibration_validates_negative_raw_evidence(self):
        receipt = self.calibration_root / "calibration.json"
        record = strict_json(receipt.read_bytes())
        for item in record["results"]:
            with self.subTest(report=item["name"]):
                raw = strict_json((self.calibration_root / (item["name"] + ".json")).read_bytes())
                self.assertTrue(oracle.validate_report(raw, self.calibration_root / item["name"]))
        copied = self.home / "copied-calibration"
        copied.mkdir()
        for item in record["results"]:
            name = item["name"]
            (copied / (name + ".json")).write_bytes((self.calibration_root / (name + ".json")).read_bytes())
            (copied / name).symlink_to(self.calibration_root / name, target_is_directory=True)
        changed = copied / "multimodule-bool-version.json"
        report = strict_json(changed.read_bytes())
        report["cases"][0]["calls"][0]["stdout"] = '{"result":{"error":"invalid"}}\n'
        changed.write_text(json.dumps(report))
        self.assertFalse(oracle.validate_report(report, self.calibration_root / "multimodule-bool-version"))
        row = next(r for r in record["results"] if r["name"] == "multimodule-bool-version")
        row["report_sha256"] = pilot.attempt.digest(changed.read_bytes())
        copied_receipt = copied / "calibration.json"
        copied_receipt.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "contradictory"):
            pilot.calibration({"path": str(copied_receipt),
                               "sha256": pilot.attempt.digest(copied_receipt.read_bytes())})
        for call_change in ({}, {"stdout": "contradictory"}, {"exit_code": {}}):
            with self.subTest(call_change=call_change):
                report = strict_json((self.calibration_root / changed.name).read_bytes())
                failed = next(r for r in report["cases"] if r["case_id"] == "bool-version")
                self.assertFalse(failed["passed"])
                failed["executed"] = False
                failed["calls"][0].update(call_change)
                self.assertFalse(oracle.validate_report(report, self.calibration_root / "multimodule-bool-version"))
                changed.write_text(json.dumps(report))
                row["report_sha256"] = pilot.attempt.digest(changed.read_bytes())
                copied_receipt.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError, "contradictory"):
                    pilot.calibration({"path": str(copied_receipt),
                                       "sha256": pilot.attempt.digest(copied_receipt.read_bytes())})

    def test_first_delivery_and_allocation(self):
        binding = self.freeze()
        self.assertEqual(len(pilot.planned_outcomes(binding)),12)
        for index, episode in enumerate(self.spec["schedule"]):
            root = prepare(self.home / ("product-%d"%index),episode["task_class"])
            for slot in episode["slots"]:
                result = pilot.dispatch(binding,slot,root,self.observation,self.callback)
                self.assertEqual(result["terminal"]["status"],"completed")
                first = result["terminal"]["first_delivery"]
                before = (Path(first["product"]) / "README.md").read_bytes()
                (root / "README.md").write_text("later work")
                self.assertEqual((Path(first["product"]) / "README.md").read_bytes(),before)
                pilot.attempt.verify_evidence(first["receipt"],result["terminal"]["attempt"],
                                             first["artifacts"],first["source_files"])
        self.assertEqual(len(self.calls),16)
        self.assertEqual(len({r["root_session"] for row in pilot.planned_outcomes(binding)
                              for r in row["stages"]}),16)
        with self.assertRaises(ValueError):
            pilot.dispatch(binding,"extra-unallocated",root,self.observation,self.callback)
        with self.assertRaises(ValueError):
            pilot.dispatch(binding,self.spec["schedule"][0]["slots"][0],root,
                           self.observation,self.callback)
        self.assertEqual(len(self.calls),16)

    def test_continuity_requires_actual_first_terminal(self):
        binding = self.freeze()
        episode = next(e for e in self.spec["schedule"] if e["task_class"] == "continuity")
        with self.assertRaisesRegex(ValueError,"actual stage1"):
            pilot.reserve(binding,episode["slots"][1],self.observation)
        self.assertEqual(len(pilot.planned_outcomes(binding)),12)

    def test_reservation_without_terminal_is_not_retried(self):
        binding = self.freeze()
        slot = self.spec["schedule"][0]["slots"][0]
        pilot.reserve(binding,slot,self.observation)
        with self.assertRaisesRegex(ValueError,"already reserved"):
            pilot.reserve(binding,slot,self.observation)
        row = next(r for r in pilot.planned_outcomes(binding) if slot in r["slots"])
        self.assertEqual(row["first_delivery"]["status"],"reserved-without-terminal")

    def test_new_file_between_freeze_and_launch_never_invokes_callback(self):
        binding = self.freeze()
        root = prepare(self.home / "product","multimodule")
        original = pilot.attempt.freeze
        def freeze_then_add(*args, **kwargs):
            result = original(*args, **kwargs)
            (root / "extra_helper.py").write_text("changed input membership")
            return result
        with patch.object(pilot.attempt,"freeze",side_effect=freeze_then_add):
            result = pilot.dispatch(binding,self.spec["schedule"][0]["slots"][0],root,
                                    self.observation,self.callback)
        self.assertEqual(self.calls,[])
        self.assertEqual(result["terminal"]["status"],"launch-failure")
        self.assertIn("membership changed",result["terminal"]["process"]["error"])

    def test_changed_bytes_during_reservation_do_not_replace_initial_baseline(self):
        binding = self.freeze()
        root = prepare(self.home / "product","multimodule")
        original = pilot.reserve
        def reserve_then_edit(*args, **kwargs):
            result = original(*args, **kwargs)
            (root / "README.md").write_text("changed during reservation")
            return result
        with patch.object(pilot,"reserve",side_effect=reserve_then_edit):
            result = pilot.dispatch(binding,self.spec["schedule"][0]["slots"][0],root,
                                    self.observation,self.callback)
        self.assertEqual(self.calls,[])
        self.assertEqual(result["terminal"]["status"],"launch-failure")

    def test_admission_separates_real_charges_and_unknowns(self):
        obs = copy.deepcopy(self.observation)
        self.assertIsNone(pilot.admit(self.spec,obs)["actual_usd_observed"])
        obs["observed_actual_usd"] = 63
        self.assertEqual(pilot.admit(self.spec,obs)["actual_usd_observed"],63)
        obs["observed_actual_usd"] = 65
        with self.assertRaisesRegex(ValueError,"monetary"):
            pilot.admit(self.spec,obs)
        for key in ("spend_control_reached", "provider_refusal"):
            obs = copy.deepcopy(self.observation); obs[key] = True
            with self.assertRaises(ValueError): pilot.admit(self.spec,obs)
        obs = copy.deepcopy(self.observation);obs["ordinary_usage_allowed"] = False
        self.assertEqual(pilot.admit(self.spec,obs)["state"],"quota-override")
        obs["captured_utc"] = None
        with self.assertRaisesRegex(ValueError,"unavailable"): pilot.admit(self.spec,obs)
        spec = copy.deepcopy(self.spec)
        spec["common"]["admission_policy"]["unknown_admission_authorized"] = True
        self.assertEqual(pilot.admit(spec,obs)["state"],"unknown")
        obs["spend_control_reached"] = 1
        with self.assertRaisesRegex(ValueError,"typed"): pilot.admit(spec,obs)

    def test_refusal_remains_in_denominator_and_stops_new_calls(self):
        self.fake.write_text('import json,sys\nsys.stdin.read()\n'
            'print(json.dumps({"type":"error","message":"usage limit reached"}))\n')
        binding = self.freeze()
        root = prepare(self.home / "product","multimodule")
        slot = self.spec["schedule"][0]["slots"][0]
        result = pilot.dispatch(binding,slot,root,self.observation,self.callback)
        self.assertEqual(result["terminal"]["status"],"provider-refusal")
        self.assertEqual(len(pilot.planned_outcomes(binding)),12)
        with self.assertRaisesRegex(ValueError,"prior provider refusal"):
            pilot.dispatch(binding,self.spec["schedule"][1]["slots"][0],root,
                           self.observation,self.callback)
        self.assertEqual(len(self.calls),1)

    def test_model_access_refusal_stops_dispatch_but_local_error_does_not(self):
        for provider in (True, False):
            with self.subTest(provider=provider):
                events = [{"type":"thread.started", "thread_id":str(uuid.uuid4())},
                          {"type":"turn.failed", "error":{"message":"The requested model is not supported for this account"}}] if provider else []
                self.fake.write_text('import json,sys\nsys.stdin.read()\n'
                    'events=' + repr(events) + '\n'
                    'for event in events: print(json.dumps(event))\n'
                    'print("The requested model is not supported for this account",file=sys.stderr)\n'
                    'raise SystemExit(1)\n')
                binding = pilot.freeze_protocol(self.home / ("refusal-"+str(provider)), self.spec)
                root = prepare(self.home / ("refusal-product-"+str(provider)), "multimodule")
                first, second = [e["slots"][0] for e in self.spec["schedule"][:2]]
                result = pilot.dispatch(binding, first, root, self.observation, self.callback)
                self.assertIs(result["terminal"]["provider_refusal"], provider)
                self.assertEqual(len(pilot.planned_outcomes(binding)), 12)
                if provider:
                    with self.assertRaisesRegex(ValueError, "prior provider refusal"):
                        pilot.reserve(binding, second, self.observation)
                else:
                    pilot.reserve(binding, second, self.observation)

    def test_refusal_with_incomplete_first_capture_still_stops_dispatch(self):
        self.fake.write_text('import json,sys\nsys.stdin.read()\n'
            'print(json.dumps({"type":"error","message":"usage limit reached"}))\n')
        for mode in ("symlink","copy-failure"):
            with self.subTest(mode=mode):
                binding = pilot.freeze_protocol(self.home/mode,self.spec)
                root = prepare(self.home/(mode+"-product"),"multimodule")
                def capture_then_link(destination,workspace,prompt,timeout):
                    process = self.callback(destination,workspace,prompt,timeout)
                    if mode == "symlink": (root/"linked-notes").symlink_to(root/"README.md")
                    return process
                def fail_copy(*args,**kwargs): raise OSError("first copy unavailable")
                with patch.object(pilot.shutil,"copyfile",side_effect=fail_copy) if mode == "copy-failure" else patch.object(pilot.shutil,"copyfile",wraps=pilot.shutil.copyfile):
                    result = pilot.dispatch(binding,self.spec["schedule"][0]["slots"][0],root,
                                            self.observation,capture_then_link)
                self.assertTrue(result["terminal"]["provider_refusal"])
                self.assertEqual(result["terminal"]["status"],"capture-incomplete")
                with self.assertRaisesRegex(ValueError,"prior provider refusal"):
                    pilot.reserve(binding,self.spec["schedule"][1]["slots"][0],self.observation)
        self.assertEqual(len(self.calls),2)

    def test_malformed_first_delivery_remains_captured(self):
        self.fake.write_text('import sys\nsys.stdin.read()\nprint("not JSON")\n')
        binding = self.freeze()
        root = prepare(self.home / "product","multimodule")
        result = pilot.dispatch(binding,self.spec["schedule"][0]["slots"][0],root,
                                self.observation,self.callback)
        self.assertEqual(result["terminal"]["status"],"malformed")
        first = result["terminal"]["first_delivery"]
        pilot.attempt.verify_evidence(first["receipt"],result["terminal"]["attempt"],
                                     first["artifacts"],first["source_files"])

    def test_reused_root_cannot_claim_fresh_continuity(self):
        binding = self.freeze()
        root = prepare(self.home / "product","continuity")
        episode = next(e for e in self.spec["schedule"] if e["task_class"] == "continuity")
        def repeat(destination, workspace, prompt, timeout):
            return pilot.capture_process([sys.executable,str(self.fake),"same-root"],
                                         workspace,prompt,destination,timeout)
        first = pilot.dispatch(binding,episode["slots"][0],root,self.observation,repeat)
        second = pilot.dispatch(binding,episode["slots"][1],root,self.observation,repeat)
        self.assertEqual(first["terminal"]["status"],"completed")
        self.assertEqual(second["terminal"]["status"],"capture-incomplete")
        self.assertIn("fresh session identity reused",second["terminal"]["capture_errors"])

    def test_changed_first_snapshot_is_rejected(self):
        binding = self.freeze()
        root = prepare(self.home / "product","multimodule")
        result = pilot.dispatch(binding,self.spec["schedule"][0]["slots"][0],root,
                                self.observation,self.callback)
        first = result["terminal"]["first_delivery"]
        (Path(first["product"])/"README.md").write_text("overwritten first outcome")
        with self.assertRaises(ValueError):
            pilot.attempt.verify_evidence(first["receipt"],result["terminal"]["attempt"],
                                         first["artifacts"],first["source_files"])

    def test_sealed_membership_rejects_added_dependencies(self):
        for mode in ("file", "symlink", "directory-link", "missing", "changed"):
            with self.subTest(mode=mode):
                binding = pilot.freeze_protocol(self.home / (mode+"-protocol"),self.spec)
                root = prepare(self.home / (mode+"-product"),"multimodule")
                reference.install_config(root)
                slot = self.spec["schedule"][0]["slots"][0]
                terminal = pilot.dispatch(binding,slot,root,self.observation,self.callback)
                first = terminal["terminal"]["first_delivery"]
                product = Path(first["product"])
                if mode == "file":
                    (product/"late_helper.py").write_text("VALUE=1\n")
                elif mode == "symlink":
                    (product/"late_helper.py").symlink_to(product/"config_tool/merge.py")
                elif mode == "directory-link":
                    (product/"late-package").symlink_to(product/"config_tool",target_is_directory=True)
                elif mode == "missing":
                    (product/"README.md").unlink()
                else:
                    (product/"README.md").write_text("changed")
                grade = pilot._read(pilot.grade_slot(binding,slot))
                self.assertFalse(grade["coherent"],grade)
                self.assertIsNotNone(grade["error"])
                self.assertIsNone(grade["report"])

    def test_sealed_inventory_guards_transition_and_report(self):
        binding = pilot.prepare_run(self.home/"controller",self.home/"products",self.spec)
        episode = next(e for e in self.spec["schedule"] if e["task_class"]=="continuity")
        def implement(destination,workspace,prompt,timeout):
            reference.install_inventory(workspace,version=1)
            return self.callback(destination,workspace,prompt,timeout)
        previous = pilot._read(pilot.execute_slot(binding,episode["slots"][0],implement,self.observation))
        self.assertTrue(pilot.report_run(binding)["episodes"])
        terminal = pilot._read(previous["terminal"])
        product = Path(terminal["first_delivery"]["product"])
        (product/"late-notes.txt").write_text("late content")
        run,_,_ = pilot.verify_run(binding)
        workspace = Path(run["workspaces"][episode["episode_id"]]["path"])
        with self.assertRaises(ValueError):
            pilot.prepare_transition(binding,episode,previous,workspace)
        with self.assertRaises(ValueError):
            pilot.report_run(binding)

    def test_sealed_inventory_is_rechecked_after_probes(self):
        binding = self.freeze()
        root = prepare(self.home/"product","multimodule")
        reference.install_config(root)
        slot = self.spec["schedule"][0]["slots"][0]
        terminal = pilot.dispatch(binding,slot,root,self.observation,self.callback)
        first = terminal["terminal"]["first_delivery"]
        evaluate = oracle.evaluate
        def add_after_probe(*args,**kwargs):
            report = evaluate(*args,**kwargs)
            (Path(first["product"])/"late.txt").write_text("post-probe addition")
            return report
        with patch.object(oracle,"evaluate",side_effect=add_after_probe):
            grade = pilot._read(pilot.grade_slot(binding,slot))
        self.assertTrue(grade["report"]["accepted"])
        self.assertFalse(grade["coherent"])
        self.assertIn("inventory changed",grade["error"])

    def test_grading_copy_matches_the_frozen_inventory(self):
        binding = self.freeze()
        root = prepare(self.home/"product","multimodule")
        reference.install_config(root)
        slot = self.spec["schedule"][0]["slots"][0]
        pilot.dispatch(binding,slot,root,self.observation,self.callback)
        copytree = pilot.shutil.copytree
        def add_to_copy(source,destination,*args,**kwargs):
            result = copytree(source,destination,*args,**kwargs)
            (Path(destination)/"late.txt").write_text("copy-only addition")
            return result
        with patch.object(pilot.shutil,"copytree",side_effect=add_to_copy):
            grade = pilot._read(pilot.grade_slot(binding,slot))
        self.assertFalse(grade["coherent"])
        self.assertIsNone(grade["report"])
        self.assertIn("grading copy differs",grade["error"])

    def test_unreserved_observation_retry_preserves_failure(self):
        spec = self.codex_spec()
        binding = pilot.prepare_run(self.home/"controller",self.home/"products",spec)
        run,_,_ = pilot.verify_run(binding)
        slot = spec["schedule"][0]["slots"][0]
        controller = Path(run["protocol"]["path"]).parent
        observations = []
        def observe(spec,workspace,destination):
            destination = Path(destination)
            destination.mkdir(exist_ok=False)
            observations.append(destination)
            if len(observations)==1:
                (destination/"failure.txt").write_text("read-only RPC failed")
                raise ValueError("read-only RPC failed")
            host = self.host_receipt(spec,workspace)
            raw = pilot._read(host)
            capture = destination/"raw.jsonl"
            capture.write_bytes((self.home/"host-raw.jsonl").read_bytes())
            raw["captures"] = pilot.attempt.snapshot([capture])
            return pilot._write(destination/"observation.json",raw)
        with patch.object(pilot,"_committed_driver",return_value="local fake attestation"), \
                patch.object(pilot,"observe_host",side_effect=observe), \
                patch.object(pilot,"codex_callback",return_value=self.callback):
            with self.assertRaisesRegex(ValueError,"read-only RPC failed"):
                pilot.execute_slot(binding,slot)
            self.assertFalse((controller/(slot+"-reservation.json")).exists())
            failure = observations[0]/"failure.txt"
            before = failure.read_bytes()
            result = pilot._read(pilot.execute_slot(binding,slot))
            self.assertEqual(result["slot_id"],slot)
            self.assertEqual(len(self.calls),1)
            self.assertEqual(failure.read_bytes(),before)
            self.assertNotEqual(observations[0],observations[1])
            self.assertEqual(len({str(p) for p in observations}),len(observations))
            with self.assertRaisesRegex(ValueError,"no retry"):
                pilot.execute_slot(binding,slot)
            self.assertEqual(len(self.calls),1)

    def test_cleanup_and_failure_witness(self):
        self.fake.write_text('import os,sys,time,subprocess\n'
            'sys.stdin.read()\nprint("partial capture",flush=True)\n'
            'subprocess.Popen([sys.executable,"-c","import time;time.sleep(20)"])\n'
            'time.sleep(20)\n')
        capture = self.home / "capture"
        started = time.monotonic()
        result = pilot.capture_process([sys.executable,str(self.fake)],self.home,"",capture,.15)
        self.assertEqual(result["status"],"timeout")
        self.assertTrue(result["cleanup_complete"])
        self.assertLess(time.monotonic()-started,2)
        self.assertIn(b"partial capture",(capture/"stdout.jsonl").read_bytes())
        self.assertIsInstance(result["exit_code"],int)

    def trace(self, missing_child=False, mismatch=False):
        fields = lambda n: {"input_tokens":n,"cached_input_tokens":0,"output_tokens":n//10}
        def write(name, events):
            p = self.home / name
            p.write_text("".join(json.dumps(e)+"\n" for e in events))
            return p
        root_events = [{"type":"session_meta","payload":{"id":"root","model":"test-model"}}]
        root_events += [{"type":"event_msg","payload":{"type":"token_count",
                        "info":{"total_token_usage":fields(n)}}} for n in (100,150,150)]
        root = write("root.jsonl",root_events)
        child = write("child.jsonl",[
            {"type":"session_meta","payload":{"id":"child","model":"test-model",
             "source":{"subAgent":{"thread_spawn":{"parent_thread_id":"root","depth":1}}}}},
            {"type":"event_msg","payload":{"type":"token_count",
             "info":{"total_token_usage":fields(20)}}}])
        exec_path = write("exec.jsonl",[
            {"type":"thread.started","thread_id":"root"},
            {"type":"item.completed","item":{"tool":"spawn_agent","receiver_thread_ids":["child"]}},
            {"type":"turn.completed","usage":fields(160 if mismatch else 150)}])
        return pilot.linked_usage("root",exec_path,[root] if missing_child else [root,child],
                                  {"test-model":{"input":2,"cached_input":.1,"output":10}},"2026-10-03")

    def test_capture_and_linked_usage(self):
        result = self.trace()
        self.assertTrue(result["complete"],result["issues"])
        self.assertEqual(result["observed_tokens"]["input_tokens"],170)
        self.assertEqual(result["session_graph"],{"root":None,"child":"root"})
        self.assertIsNone(result["actual_invoice_usd"])
        self.assertEqual(result["provider_model_delivery"],"unknown")

    def test_missing_declared_child_is_not_free(self):
        result = self.trace(missing_child=True)
        self.assertFalse(result["complete"])
        self.assertIsNone(result["cost_usd"])
        self.assertIn("missing declared child session: child",result["issues"])

    def test_cumulative_disagreement_is_not_complete(self):
        result = self.trace(mismatch=True)
        self.assertFalse(result["complete"])
        self.assertIsNone(result["cost_usd"])
        self.assertIn("exec and rollout cumulative totals do not reconcile",result["issues"])

    def test_unlinked_retained_child_is_incomplete(self):
        self.trace()
        path = self.home / "child.jsonl"
        path.write_text(path.read_text().replace('"parent_thread_id": "root"','"parent_thread_id": "missing-parent"'))
        path = self.home / "exec.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        path.write_text("".join(json.dumps(row)+"\n" for row in rows if row["type"] != "item.completed"))
        result = pilot.linked_usage("root",path,[self.home/"root.jsonl",self.home/"child.jsonl"],
                                   {"test-model":{"input":2,"cached_input":.1,"output":10}},"2026-10-03")
        self.assertFalse(result["complete"])
        self.assertIsNone(result["cost_usd"])
        self.assertIn("unlinked retained session: child",result["issues"])

    def test_refusal_after_usage_does_not_price_complete_capture(self):
        self.trace()
        path = self.home / "exec.jsonl"
        with path.open("a") as stream:
            stream.write(json.dumps({"type":"error","message":"usage limit reached"})+"\n")
            stream.write(json.dumps({"type":"turn.failed","error":"quota"})+"\n")
        result = pilot.linked_usage("root",path,[self.home/"root.jsonl",self.home/"child.jsonl"],
                                   {"test-model":{"input":2,"cached_input":.1,"output":10}},"2026-10-03")
        self.assertFalse(result["complete"])
        self.assertEqual(result["observed_tokens"]["input_tokens"],170)
        self.assertGreater(result["observed_priced_cost_usd"],0)
        self.assertIsNone(result["cost_usd"])
        self.assertIsNone(result["actual_invoice_usd"])

    def test_strict_raw_events_keep_malformed_bytes_unknown(self):
        for raw in (b'{"type":"turn.completed","type":"error"}',
                    b'{"type":"turn.completed","usage":NaN}',b'\xff'):
            with self.subTest(raw=raw):
                path = self.home / "bad.jsonl";path.write_bytes(raw)
                events, errors = pilot._events(path)
                self.assertEqual(events,[])
                self.assertTrue(errors)

    def test_documented_report_entry_prepares_without_provider_calls(self):
        request = self.home / "prepare-request.json"
        request.write_text(json.dumps({"destination":str(self.home/"controller"),
            "workspace_root":str(self.home/"public products"),"spec":self.spec}))
        command = [sys.executable,"-B",str(LAB/"pilot.py")]
        prepared = subprocess.run(command+["--prepare",str(request)],capture_output=True,text=True)
        self.assertEqual(prepared.returncode,0,prepared.stderr)
        binding = self.home / "run-binding.json"
        binding.write_text(prepared.stdout)
        verified = subprocess.run(command+["--verify",str(binding)],capture_output=True,text=True)
        self.assertEqual(verified.returncode,0,verified.stderr)
        reported = subprocess.run(command+["--report",str(binding)],capture_output=True,text=True)
        self.assertEqual(reported.returncode,0,reported.stderr)
        report = strict_json(reported.stdout)
        self.assertEqual(len(report["episodes"]),12)
        self.assertEqual(report["reserved_roots"],0)
        self.assertEqual({e["first_delivery"]["status"] for e in report["episodes"]},{"not-launched"})
        self.assertTrue(all(e["first_delivery"]["accepted"] is None for e in report["episodes"]))
        duplicate = subprocess.run(command+["--prepare",str(request)],capture_output=True,text=True)
        self.assertNotEqual(duplicate.returncode,0)
        self.assertEqual(self.calls,[])

    def test_run_scores_all_actual_first_deliveries_and_retains_denominator(self):
        binding = pilot.prepare_run(self.home/"controller",self.home/"products",self.spec)
        def implement(destination,workspace,prompt,timeout):
            name = Path(workspace).name
            if name.startswith("multimodule"):
                reference.install_config(workspace)
            elif name.startswith("batch"):
                reference.install_batch(workspace)
            else:
                version = 2 if (Path(workspace)/"v1_checks.json").exists() else 1
                reference.install_inventory(workspace,version=version)
            return self.callback(destination,workspace,prompt,timeout)
        for episode in self.spec["schedule"]:
            for slot in episode["slots"]:
                pilot.execute_slot(binding,slot,implement,self.observation)
        report = pilot.report_run(binding)
        self.assertEqual(report["reserved_roots"],16)
        self.assertEqual(len(self.calls),16)
        self.assertEqual(len(report["episodes"]),12)
        self.assertEqual({v["accepted"] for v in report["arms"].values()},{6})
        for episode in report["episodes"]:
            self.assertTrue(episode["first_delivery"]["accepted"],episode)
            self.assertEqual(episode["correction_invocations"],0)
            self.assertIsNone(episode["first_delivery"]["actual_invoice_usd"])
            self.assertIsNone(episode["first_delivery"]["equivalent_credits"])
            if episode["stage1_milestone"]:
                self.assertTrue(episode["stage1_milestone"]["accepted"])
                self.assertNotEqual(episode["stage1_milestone"]["root_session"],episode["first_delivery"]["root_session"])
        with self.assertRaisesRegex(ValueError,"no retry"):
            pilot.execute_slot(binding,self.spec["schedule"][0]["slots"][0],implement,self.observation)
        raw = Path(self.calls[0])/"stdout.jsonl"
        raw.write_text(raw.read_text()+" ")
        with self.assertRaises(ValueError): pilot.report_run(binding)

    def test_failed_stage1_is_preserved_and_transition_is_not_reapplied(self):
        binding = pilot.prepare_run(self.home/"controller",self.home/"products",self.spec)
        episode = next(e for e in self.spec["schedule"] if e["task_class"]=="continuity")
        pilot.execute_slot(binding,episode["slots"][0],self.callback,self.observation)
        before = pilot.report_run(binding)
        self.assertFalse(next(e for e in before["episodes"] if e["episode_id"]==episode["episode_id"])["stage1_milestone"]["accepted"])
        def implement(destination,workspace,prompt,timeout):
            self.assertFalse(strict_json((Path(workspace)/"v1_checks.json").read_bytes())["accepted"])
            self.assertEqual((Path(workspace)/"notes.txt").read_text().count("Uncommitted user draft"),1)
            reference.install_inventory(workspace,version=2)
            return self.callback(destination,workspace,prompt,timeout)
        stale = dict(self.observation,captured_utc=None)
        with self.assertRaisesRegex(ValueError,"unavailable"):
            pilot.execute_slot(binding,episode["slots"][1],implement,stale)
        pilot.execute_slot(binding,episode["slots"][1],implement,self.observation)
        report = pilot.report_run(binding)
        row = next(e for e in report["episodes"] if e["episode_id"]==episode["episode_id"])
        self.assertFalse(row["stage1_milestone"]["accepted"])
        self.assertTrue(row["first_delivery"]["accepted"],row)
        self.assertEqual(len(self.calls),2)

    def test_run_seed_and_pricing_drift_refuse_before_callback(self):
        binding = pilot.prepare_run(self.home/"controller",self.home/"products",self.spec)
        run,spec,prices = pilot.verify_run(binding)
        episode = self.spec["schedule"][0]
        workspace = Path(run["workspaces"][episode["episode_id"]]["path"])
        (workspace/"README.md").write_text("changed seed")
        with self.assertRaisesRegex(ValueError,"public seed"):
            pilot.execute_slot(binding,episode["slots"][0],self.callback,self.observation)
        Path(run["pricing"]["path"]).write_text("changed nominal rates")
        with self.assertRaises(ValueError): pilot.report_run(binding)
        self.assertEqual(self.calls,[])

    def test_codex_callback_commit_guard_precedes_capture(self):
        spec = self.codex_spec()
        binding = pilot.freeze_protocol(self.home / "protocol",spec)
        root = prepare(self.home / "product","multimodule")
        with patch.object(pilot,"_committed_driver",side_effect=ValueError("uncommitted driver")) as guard, \
                patch.object(pilot,"capture_process") as capture:
            with self.assertRaisesRegex(ValueError,"uncommitted driver"):
                pilot.codex_callback(binding)(self.home/"capture",root,"prompt",2)
        guard.assert_called_once()
        capture.assert_not_called()

    def test_recover_retained_delivery_without_another_provider_call(self):
        binding = pilot.prepare_run(self.home/"controller",self.home/"products",self.spec)
        episode = next(e for e in self.spec["schedule"] if e["task_class"]=="continuity")
        slot = episode["slots"][0]
        def implement(destination,workspace,prompt,timeout):
            reference.install_inventory(workspace,version=1)
            return self.callback(destination,workspace,prompt,timeout)
        # Interruption inside evaluation leaves a retained but unfinished copy.
        with patch.object(oracle,"evaluate",side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                pilot.execute_slot(binding,slot,implement,self.observation)
        controller = Path(pilot.verify_run(binding)[0]["protocol"]["path"]).parent
        partial = list((controller/slot).glob("grading-*"))
        self.assertEqual(len(partial),1)
        self.assertTrue((partial[0]/"product").is_dir())
        before = next(e for e in pilot.report_run(binding)["episodes"]
                      if e["episode_id"]==episode["episode_id"])["stage1_milestone"]
        self.assertIsNone(before["accepted"])
        self.assertIsNotNone(before["usage"])
        with patch.object(pilot,"capture_process") as capture, \
                patch.object(pilot,"observe_host") as host:
            recovered = pilot.recover_slot(binding,slot)
            self.assertEqual(pilot.recover_slot(binding,slot),recovered)
            capture.assert_not_called()
            host.assert_not_called()
        self.assertEqual(len(list((controller/slot).glob("grading-*"))),2)
        def second(destination,workspace,prompt,timeout):
            reference.install_inventory(workspace,version=2)
            return self.callback(destination,workspace,prompt,timeout)
        pilot.execute_slot(binding,episode["slots"][1],second,self.observation)
        row = next(e for e in pilot.report_run(binding)["episodes"]
                   if e["episode_id"]==episode["episode_id"])
        self.assertTrue(row["stage1_milestone"]["accepted"])
        self.assertTrue(row["first_delivery"]["accepted"])
        self.assertEqual(len(self.calls),2)
        with self.assertRaisesRegex(ValueError,"no retry"):
            pilot.execute_slot(binding,slot,implement,self.observation)
        with self.assertRaisesRegex(ValueError,"no retained terminal"):
            pilot.recover_slot(binding,self.spec["schedule"][0]["slots"][0])

    def test_transition_resumes_each_atomic_publication_boundary(self):
        binding = pilot.prepare_run(self.home/"controller",self.home/"products",self.spec)
        run,_,_ = pilot.verify_run(binding)
        episode = next(e for e in self.spec["schedule"] if e["task_class"]=="continuity")
        pilot.execute_slot(binding,episode["slots"][0],self.callback,self.observation)
        controller = Path(run["protocol"]["path"]).parent
        previous = strict_json((controller/(episode["slots"][0]+"-result.json")).read_bytes())
        terminal = pilot._read(previous["terminal"])
        workspace = Path(run["workspaces"][episode["episode_id"]]["path"])
        before = pilot._relative_manifest(workspace)
        write = pilot._write
        def interrupted_intent(path,value):
            if str(path).endswith("-transition.json"):
                raise OSError("interrupted intent publication")
            return write(path,value)
        with patch.object(pilot,"_publish",side_effect=interrupted_intent):
            with self.assertRaisesRegex(OSError,"interrupted intent"):
                pilot.prepare_transition(binding,episode,previous,workspace)
        self.assertEqual(pilot._relative_manifest(workspace),before)
        journal,protection = pilot.prepare_transition(binding,episode,previous,workspace)
        prepared = pilot._read(journal)
        replace = os.replace
        for boundary in range(len(prepared["writes"])):
            for when in ("before","after"):
                with self.subTest(boundary=boundary,when=when):
                    shutil.rmtree(workspace)
                    shutil.copytree(terminal["first_delivery"]["product"],workspace)
                    count = 0
                    def interrupted(source,target):
                        nonlocal count
                        index = count
                        count += 1
                        if index == boundary and when == "before":
                            raise KeyboardInterrupt
                        replace(source,target)
                        if index == boundary and when == "after":
                            raise KeyboardInterrupt
                    with patch.object(pilot.os,"replace",side_effect=interrupted):
                        with self.assertRaises(KeyboardInterrupt):
                            pilot.prepare_transition(binding,episode,previous,workspace)
                    resumed,actual = pilot.prepare_transition(binding,episode,previous,workspace)
                    self.assertEqual(resumed,journal)
                    self.assertEqual(actual,protection)
                    self.assertEqual(pilot._relative_manifest(workspace),prepared["after"])
                    self.assertEqual((workspace/"notes.txt").read_text().count("Uncommitted user draft"),1)
        (workspace/"notes.txt").write_text("new user edit\n")
        with self.assertRaisesRegex(ValueError,"unexpected user edit"):
            pilot.prepare_transition(binding,episode,previous,workspace)
        self.assertEqual((workspace/"notes.txt").read_text(),"new user edit\n")
        self.assertEqual(len(self.calls),1)

    def test_recovery_records_publish_atomically_without_clobber(self):
        binding = pilot.prepare_run(self.home/"controller",self.home/"products",self.spec)
        run,_,_ = pilot.verify_run(binding)
        controller = Path(run["protocol"]["path"]).parent
        episode = next(e for e in self.spec["schedule"] if e["task_class"]=="continuity")
        first,second = episode["slots"]
        write = pilot._write
        def partial_record(path,value):
            if "-result.json" in Path(path).name or "-transition.json" in Path(path).name:
                Path(path).write_bytes(json.dumps(value).encode()[:20])
                raise KeyboardInterrupt
            return write(path,value)
        with patch.object(pilot,"_write",side_effect=partial_record):
            with self.assertRaises(KeyboardInterrupt):
                pilot.execute_slot(binding,first,self.callback,self.observation)
        result_path = controller/(first+"-result.json")
        self.assertFalse(result_path.exists())
        row = next(e for e in pilot.report_run(binding)["episodes"] if e["episode_id"]==episode["episode_id"])
        self.assertIsNotNone(row["stage1_milestone"]["usage"])
        link = os.link
        def after_publication(source,target):
            link(source,target)
            raise KeyboardInterrupt
        with patch.object(pilot.os,"link",side_effect=after_publication):
            with self.assertRaises(KeyboardInterrupt):
                pilot.recover_slot(binding,first)
        self.assertTrue(result_path.is_file())
        result = pilot.recover_slot(binding,first)
        self.assertEqual(len(self.calls),1)
        before_bytes = result_path.read_bytes()
        with self.assertRaises(FileExistsError):
            pilot._publish(result_path,{"replacement":True})
        self.assertEqual(result_path.read_bytes(),before_bytes)
        workspace = Path(run["workspaces"][episode["episode_id"]]["path"])
        before = pilot._relative_manifest(workspace)
        with patch.object(pilot,"_write",side_effect=partial_record):
            with self.assertRaises(KeyboardInterrupt):
                pilot.execute_slot(binding,second,self.callback,self.observation)
        self.assertFalse((controller/(second+"-transition.json")).exists())
        self.assertFalse((controller/(second+"-reservation.json")).exists())
        self.assertEqual(pilot._relative_manifest(workspace),before)
        def implement(destination,workspace,prompt,timeout):
            reference.install_inventory(workspace,version=2)
            return self.callback(destination,workspace,prompt,timeout)
        pilot.execute_slot(binding,second,implement,self.observation)
        row = next(e for e in pilot.report_run(binding)["episodes"] if e["episode_id"]==episode["episode_id"])
        self.assertFalse(row["stage1_milestone"]["accepted"])
        self.assertTrue(row["first_delivery"]["accepted"])
        self.assertEqual(len(self.calls),2)


if __name__ == "__main__":
    unittest.main()
