"""Real-process regression tests for post-freeze batch boundaries."""
import json
import copy
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "fixtures"))
from behavior import stop_candidate
from pilot_fixtures import prepare
from pilot_oracle import file_bytes, receipt, run
from reference_pilot import install_batch
import pilot_supplementary as supplementary


class BatchBoundaryTests(unittest.TestCase):
    def test_receipt_publication_replays_without_rewriting(self):
        for algorithm in ("journal", "staged"):
            with self.subTest(algorithm=algorithm), tempfile.TemporaryDirectory() as td:
                root = Path(td) / "candidate"
                prepare(root, "batch")
                install_batch(root, algorithm)
                output = Path(td) / "product"
                output.mkdir()
                witness = Path(td) / "witness.json"
                request = {"root": str(output), "operation_id": "finish-boundary",
                           "outputs": {"a.txt": "first\n", "nested/b.txt": "second\r\n"}}
                command = [str(Path(sys.executable).resolve()), str(root / "batch_tool.py")]
                env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                           PILOT_PAUSE_PATH="receipts.json", PILOT_WITNESS=str(witness))
                p = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, start_new_session=os.name == "posix")
                try:
                    p.stdin.write(json.dumps(request))
                    p.stdin.close()
                    p.stdin = None
                    deadline = time.monotonic() + 3
                    seen = None
                    while time.monotonic() < deadline and p.poll() is None:
                        try:
                            seen = json.loads(witness.read_text())
                            break
                        except (OSError, ValueError):
                            time.sleep(.005)
                    self.assertIsNotNone(seen)
                    self.assertEqual(seen["pid"], p.pid)
                    self.assertEqual(seen["path"], "receipts.json")
                    self.assertIsNone(p.poll())
                    self.assertEqual(receipt(output), [request["operation_id"]])
                    for path, body in request["outputs"].items():
                        self.assertEqual((output / path).read_bytes(), body.encode())
                    before = file_bytes(output)
                finally:
                    cleanup = stop_candidate(p)
                    p.communicate(timeout=.5)
                self.assertTrue(cleanup)
                self.assertNotEqual(p.returncode, 0)
                replay = run(command, request, root, 3)
                self.assertIsNone(replay["error"], replay)
                self.assertNotEqual(replay["pid"], p.pid)
                self.assertEqual(replay["envelope"]["result"]["status"], "replayed")
                self.assertEqual(file_bytes(output), before)
                # The receipt is already completion even while done remains false.
                (output / "a.txt").unlink()
                protected = file_bytes(output)
                conflict = run(command, request, root, 3)
                self.assertEqual(conflict.get("envelope", {}).get("result"), {"status": "conflict"})
                self.assertEqual(file_bytes(output), protected)

    def test_binary_target_preimage_applies(self):
        for algorithm in ("journal", "staged"):
            with self.subTest(algorithm=algorithm), tempfile.TemporaryDirectory() as td:
                root = Path(td) / "candidate"
                prepare(root, "batch")
                install_batch(root, algorithm)
                output = Path(td) / "product"
                output.mkdir()
                (output / "a.txt").write_bytes(b"\xff\x00\xfe\r\n")
                request = {"root": str(output), "operation_id": "binary-preimage",
                           "outputs": {"a.txt": "replacement\r\n", "b.txt": "other"}}
                command = [str(Path(sys.executable).resolve()), str(root / "batch_tool.py")]
                applied = run(command, request, root, 3)
                self.assertIsNone(applied["error"], applied)
                self.assertEqual(applied["envelope"]["result"]["status"], "applied")
                self.assertEqual((output / "a.txt").read_bytes(), b"replacement\r\n")
                self.assertEqual(receipt(output), [request["operation_id"]])

    def test_supplementary_controls_and_intended_mutants(self):
        for algorithm in ("journal", "staged"):
            for fault, rejected in ((None, None), ("completion-boundary", "receipt-boundary"),
                                    ("utf8-preimage", "binary-preimage")):
                with self.subTest(algorithm=algorithm, fault=fault), tempfile.TemporaryDirectory() as td:
                    root = Path(td) / "candidate"
                    prepare(root, "batch")
                    install_batch(root, algorithm, fault)
                    report = supplementary.evaluate(root)
                    self.assertTrue(supplementary.validate_report(report, root), report)
                    self.assertEqual(report["selection"], "post-freeze-supplementary")
                    self.assertIs(report["accepted"], fault is None)
                    if rejected:
                        row = next(r for r in report["cases"] if r["case_id"] == rejected)
                        self.assertIs(row["passed"], False)
                    else:
                        self.assertTrue(all(r["passed"] for r in report["cases"]))

    def test_binding_and_contradiction_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "candidate"
            prepare(root, "batch")
            install_batch(root)
            cases = Path(td) / "cases.json"
            cases.write_bytes(supplementary.CASES.read_bytes())
            evaluator = Path(td) / "bound-evaluator.py"
            evaluator.write_text("# declared evaluator dependency\n")
            with patch.object(supplementary, "EVALUATORS", [*supplementary.EVALUATORS, evaluator]):
                report = supplementary.evaluate(root, cases)
                self.assertTrue(supplementary.validate_report(report, root, cases))
                for name, target in (("candidate", root / "batch_tool.py"),
                                     ("cases", cases), ("evaluator", evaluator)):
                    with self.subTest(drift=name):
                        before = target.read_bytes()
                        target.write_bytes(before + b"\n")
                        self.assertFalse(supplementary.validate_report(report, root, cases))
                        target.write_bytes(before)
                (root / "added_dependency.py").write_text("# unbound dependency\n")
                self.assertFalse(supplementary.validate_report(report, root, cases))
                (root / "added_dependency.py").unlink()
                self.assertTrue(supplementary.validate_report(report, root, cases))
                changes = [
                    lambda r: r.update(accepted=False),
                    lambda r: r.update(accepted=1),
                    lambda r: r.update(selection="primary"),
                    lambda r: r["cases"][0].update(passed=False),
                    lambda r: r["cases"][0]["checks"].update(no_replay_writes=False),
                    lambda r: r["cases"][0]["calls"][1].update(stdout='{"result":{"status":"applied"}}'),
                    lambda r: r["cases"][0]["calls"][0].update(stderr_hex="00"),
                    lambda r: r["cases"][0]["filesystem"].update(**{"first.txt": "00"}),
                    lambda r: r["cases"][0].update(expected={"status": "applied"}),
                ]
                for index, mutate in enumerate(changes):
                    with self.subTest(contradiction=index):
                        broken = copy.deepcopy(report)
                        mutate(broken)
                        self.assertFalse(supplementary.validate_report(broken, root, cases))
                        broken["raw_capture_sha256"] = supplementary._raw_hash(broken)
                        self.assertFalse(supplementary.validate_report(broken, root, cases))

    def test_incomplete_fixture_and_invalid_timeout_are_refused(self):
        with tempfile.TemporaryDirectory() as td:
            cases = Path(td) / "cases.json"
            spec = json.loads(supplementary.CASES.read_text())
            spec["cases"].pop()
            cases.write_text(json.dumps(spec))
            with self.assertRaises(ValueError):
                supplementary.load_cases(cases)
            for timeout in (True, 0, float("inf")):
                with self.assertRaises(ValueError):
                    supplementary.evaluate(td, timeout=timeout)

    def test_raw_envelope_contradiction_cannot_validate_recomputed_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "candidate"
            prepare(root, "batch")
            install_batch(root)
            report = supplementary.evaluate(root)
            self.assertTrue(supplementary.validate_report(report, root))
            for envelope in ({"result": {"status": "applied"}}, None):
                with self.subTest(envelope=envelope):
                    broken = copy.deepcopy(report)
                    row = broken["cases"][0]
                    row["calls"][1]["envelope"] = envelope
                    row.update(observed=None, passed=False)
                    broken["accepted"] = False
                    broken["raw_capture_sha256"] = supplementary._raw_hash(broken)
                    self.assertFalse(supplementary.validate_report(broken, root))

    def test_calibration_retains_bound_positive_and_negative_reports(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "calibration"
            result = supplementary.calibrate(output)
            self.assertTrue(result["calibrated"], result)
            self.assertEqual(sum(r["control"] for r in result["results"]), 2)
            self.assertEqual(sum(not r["control"] for r in result["results"]), 4)
            self.assertEqual(result["frozen_dependencies"], result["current_dependencies"])
            for row in result["results"]:
                path = Path(row["report"]["path"])
                self.assertEqual(supplementary.digest(path.read_bytes()), row["report"]["sha256"])
                report = json.loads(path.read_text())
                self.assertTrue(supplementary.validate_report(report, path.parent))
            with self.assertRaises(FileExistsError):
                supplementary.calibrate(output)

    def test_early_child_exit_is_retained_as_coherent_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "candidate"
            prepare(root, "batch")
            (root / "batch_tool.py").write_text("raise SystemExit(9)\n")
            report = supplementary.evaluate(root)
            self.assertIs(report["accepted"], False)
            self.assertTrue(supplementary.validate_report(report, root), report)
            for row in report["cases"]:
                self.assertEqual(len(row["calls"]), 2)
                self.assertTrue(all(c["exit_code"] == 9 for c in row["calls"]))

    def test_failed_call_metadata_cannot_hide_negative_contradictions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "candidate"
            prepare(root, "batch")
            install_batch(root, fault="utf8-preimage")
            report = supplementary.evaluate(root)
            self.assertFalse(report["accepted"])
            self.assertTrue(supplementary.validate_report(report, root))
            index = next(i for i,r in enumerate(report["cases"]) if r["case_id"] == "binary-preimage")
            self.assertNotEqual(report["cases"][index]["calls"][0]["exit_code"], 0)
            for change in ({"error": "unsupported error"},
                           {"envelope": {"result": {"status": "applied"}}}):
                with self.subTest(change=change):
                    altered = copy.deepcopy(report)
                    altered["cases"][index]["calls"][0].update(change)
                    altered["raw_capture_sha256"] = supplementary._raw_hash(altered)
                    self.assertFalse(supplementary.validate_report(altered, root))

    def test_paused_metadata_cannot_forge_recomputed_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "candidate"
            prepare(root, "batch")
            install_batch(root)
            report = supplementary.evaluate(root)
            self.assertTrue(report["accepted"])
            cases = supplementary.load_cases(supplementary.CASES)[0]["cases"]
            for index, change in ((index, change) for index in (0, 2) for change in (
                    {"error":"unsupported error"}, {"error":"ValueError"}, {"error":False}, {"error":1},
                    {"envelope":{"result":{"status":"applied"}}},
                    {"pid":True}, {"exit_code":False}, {"alive_at_snapshot":1},
                    {"cleanup_complete":1}, {"stdout_hex":"61"})):
                with self.subTest(case=cases[index]["case_id"], change=change):
                    altered = copy.deepcopy(report)
                    row = altered["cases"][index]
                    row["calls"][0].update(change)
                    try:
                        row["checks"], row["observed"] = supplementary.derive(
                            row, cases[index],
                            altered["binding"]["candidate_command"])
                    except ValueError:
                        altered["raw_capture_sha256"] = supplementary._raw_hash(altered)
                        self.assertFalse(supplementary.validate_report(altered, root))
                        continue
                    row["passed"] = all(row["checks"].values()) and row["observed"] == row["expected"]
                    altered["accepted"] = all(r["passed"] for r in altered["cases"])
                    altered["raw_capture_sha256"] = supplementary._raw_hash(altered)
                    self.assertFalse(supplementary.validate_report(altered, root))

    def test_legal_stderr_does_not_block_publication_capture(self):
        for algorithm in ("journal", "staged"):
            with self.subTest(algorithm=algorithm), tempfile.TemporaryDirectory() as td:
                root = Path(td) / "candidate"
                prepare(root, "batch")
                install_batch(root, algorithm)
                entry = root / "batch_tool.py"
                entry.write_text('import sys\nsys.stderr.write("d"*275000)\nsys.stderr.flush()\n' + entry.read_text())
                report = supplementary.evaluate(root, timeout=.5)
                summary = {r["case_id"]: {"checks": r["checks"], "stderr_sizes": [len(c["stderr"]) for c in r["calls"]]} for r in report["cases"]}
                self.assertTrue(report["accepted"], summary)
                self.assertTrue(supplementary.validate_report(report, root))
                for row in report["cases"]:
                    self.assertTrue(all(len(c["stderr"]) == 275000 for c in row["calls"]))
                    if "stderr_hex" in row["calls"][0]:
                        self.assertEqual(bytes.fromhex(row["calls"][0]["stderr_hex"]), b"d" * 275000)

    def test_snapshot_failure_retains_incomplete_report_and_calls(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "candidate"
            prepare(root, "batch")
            (root / "batch_tool.py").write_text(
                'import json, sys\nfrom pathlib import Path\n'
                'request = json.load(sys.stdin)\n'
                'output = Path(request["root"])\n'
                '(output / "unexpected").symlink_to(output / "missing")\n'
                'print(json.dumps({"result": {"status": "applied"}}))\n')
            try:
                report = supplementary.evaluate(root, timeout=.3)
            except ValueError as exc:
                self.fail(f"snapshot failure discarded the captured report: {exc}")
            self.assertIs(report["accepted"], False)
            self.assertFalse(supplementary.validate_report(report, root))
            for row in report["cases"]:
                self.assertEqual(row["error"], "ValueError")
                self.assertEqual(row["filesystem_error"], "ValueError")
                self.assertEqual(len(row["calls"]), 1)
                self.assertEqual(row["calls"][0]["exit_code"], 0)
                self.assertEqual(json.loads(row["calls"][0]["stdout"]),
                                 {"result": {"status": "applied"}})

    def test_bound_invocation_contradictions_cannot_validate_recomputed_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "candidate"
            prepare(root, "batch")
            install_batch(root)
            report = supplementary.evaluate(root)
            self.assertTrue(report["accepted"])
            self.assertTrue(supplementary.validate_report(report, root))
            cases = supplementary.load_cases(supplementary.CASES)[0]["cases"]
            command = report["binding"]["candidate_command"]
            mutations = [(index, call, field) for index in range(3)
                         for call in (0, 1) for field in ("command", "request")]
            mutations += [(index, None, field) for index in range(3)
                          for field in ("case_request", "missing_call")]
            for index, call, field in mutations:
                with self.subTest(case=cases[index]["case_id"], call=call, field=field):
                    broken = copy.deepcopy(report)
                    row = broken["cases"][index]
                    if field == "command":
                        row["calls"][call][field] = [command[0], str(root / "never-executed.py")]
                    elif field == "request":
                        row["calls"][call][field] = dict(row["request"], operation_id="never-requested")
                    elif field == "case_request":
                        row["request"] = dict(row["request"], operation_id="never-requested")
                        for captured in row["calls"]:
                            captured["request"] = row["request"]
                    else:
                        row["calls"].pop()
                    try:
                        row["checks"], row["observed"] = supplementary.derive(row, cases[index], command)
                    except ValueError:
                        broken["raw_capture_sha256"] = supplementary._raw_hash(broken)
                        self.assertFalse(supplementary.validate_report(broken, root))
                        continue
                    row["passed"] = all(v is True for v in row["checks"].values()) and row["observed"] == row["expected"]
                    broken["accepted"] = all(r["passed"] for r in broken["cases"])
                    broken["raw_capture_sha256"] = supplementary._raw_hash(broken)
                    self.assertFalse(supplementary.validate_report(broken, root))

    def test_unsupported_error_cannot_forge_coherent_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "candidate"
            prepare(root, "batch")
            install_batch(root)
            report = supplementary.evaluate(root)
            self.assertTrue(report["accepted"])
            for error in ("JSONDecodeError", False, 1):
                with self.subTest(error=error):
                    broken = copy.deepcopy(report)
                    broken["cases"][0].update(error=error, passed=False)
                    broken["accepted"] = False
                    broken["raw_capture_sha256"] = supplementary._raw_hash(broken)
                    self.assertFalse(supplementary.validate_report(broken, root))
                with self.subTest(call_error=error):
                    broken = copy.deepcopy(report)
                    broken["cases"][0]["calls"][1]["error"] = error
                    broken["cases"][0].update(observed=None, passed=False)
                    broken["accepted"] = False
                    broken["raw_capture_sha256"] = supplementary._raw_hash(broken)
                    self.assertFalse(supplementary.validate_report(broken, root))


if __name__ == "__main__":
    unittest.main()
