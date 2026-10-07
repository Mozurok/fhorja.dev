import json
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from behavior import evaluate
from quality import score as raw_score


class BehaviorTests(unittest.TestCase):
    cases = LAB / "fixtures/behavior_cases.json"
    reference = [sys.executable, str(LAB / "fixtures/reference_behavior.py")]

    def score(self, rc, behavior, command=None):
        return raw_score(rc, behavior=behavior, cases_path=self.cases,
                         source_files=[self.reference[1]], candidate_command=command or self.reference)

    def test_real_reference_execution_earns_domain_credit(self):
        result = evaluate(self.cases, self.reference, source_files=[self.reference[1]])
        scored = self.score({"test": 0}, behavior=result)
        self.assertTrue(scored["tests_cover_csv"])
        self.assertTrue(scored["tests_cover_budget"])
        self.assertTrue(all(r["executed"] for f in ("csv", "budget") for r in result[f]["cases"]))

    def test_reference_preserves_large_signed_cents_and_historical_keys(self):
        whole = 1234567890123456789012345678901234567890
        cents = whole * 100 + 12
        request = {
            "operation": "csv_import",
            "csv": ("date;description;amount\n"
                    f"01/10/2026;positive; +{whole},12 \n"
                    f"01/10/2026;negative;-{whole},12\n"
                    f"01/10/2026;whole;{whole}\n"
                    f"01/10/2026;fraction;{whole},1\n"
                    f"01/10/2026;history;{whole},12\n"),
            "existing_keys": [f"2026-10-01|history|{cents}"],
        }
        expected = {
            "transactions": [
                {"date": "2026-10-01", "description": description, "amount_cents": amount}
                for description, amount in [("positive", cents), ("negative", -cents),
                                            ("whole", whole * 100), ("fraction", whole * 100 + 10)]
            ],
            "invalid_rows": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "cases.json"
            fixture.write_text(json.dumps({"schema_version": 1, "cases": [
                {"case_id": "large-cents", "feature": "csv", "input": request,
                 "expected": expected}]}))
            result = evaluate(fixture, self.reference)
            row = result["csv"]["cases"][0]
            self.assertTrue(row["executed"])
            self.assertEqual(row["observed"], expected)
            self.assertTrue(row["passed"])

    def test_real_seeded_faults_withhold_credit(self):
        for fault, feature in [("deduplicate", "csv"), ("float", "csv"),
                               ("refund-income", "budget"), ("all-income", "budget")]:
            with self.subTest(fault=fault):
                result = evaluate(self.cases, self.reference + [fault], source_files=[self.reference[1]])
                self.assertFalse(self.score({"test": 0}, behavior=result, command=self.reference + [fault])["tests_cover_" + feature])
                self.assertTrue(any(r.get("passed") is False for r in result[feature]["cases"]))

    def test_answers_and_case_metadata_never_sent_to_candidate(self):
        command = [sys.executable, "-c", "import sys,json; print(json.dumps({'result':json.load(sys.stdin)}))"]
        result = evaluate(self.cases, command)
        for feature in ("csv", "budget"):
            for row in result[feature]["cases"]:
                self.assertTrue(row["executed"])
                self.assertNotIn("expected", row["observed"])
                self.assertNotIn("case_id", row["observed"])
                self.assertNotIn("passed", row["observed"])

    def test_failed_malformed_and_nonfinite_processes(self):
        for script in ["raise SystemExit(2)", "print('bad')",
                       "print('{\"result\":NaN}')", "print('{\"passed\":true}')",
                       "print('{\"result\":9,\"result\":1}')",
                       "print('{\"result\":{\"x\":9,\"x\":1}}')"]:
            result = evaluate(self.cases, [sys.executable, "-c", script])
            self.assertFalse(result["csv"]["completed"])
            self.assertTrue(all(not r["executed"] for r in result["csv"]["cases"]))

    def test_timeout_is_not_execution_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "cases.json"
            fixture.write_text(json.dumps({"schema_version": 1, "cases": [
                {"case_id": "timeout", "feature": "csv", "input": {}, "expected": {}}]}))
            result = evaluate(fixture, [sys.executable, "-c", "import time;time.sleep(60)"], .05)
            self.assertEqual(result["csv"]["cases"][0]["error"], "candidate timeout")
            self.assertFalse(result["csv"]["completed"])

    def test_boolean_cannot_substitute_integer_expected_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "cases.json"
            fixture.write_text(json.dumps({"schema_version": 1, "cases": [
                {"case_id": "integer", "feature": "csv", "input": {}, "expected": 1}]}))
            result = evaluate(fixture, [sys.executable, "-c", "print('{\"result\":true}')"])
            self.assertFalse(self.score({"test": 0}, behavior=result)["tests_cover_csv"])

    def test_invalid_timeout_is_rejected_before_launch(self):
        for timeout in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                evaluate(self.cases, self.reference, timeout)

    def test_detached_pipe_holders_have_bounded_timeout_cleanup(self):
        import time
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "cases.json"
            fixture.write_text(json.dumps({"schema_version": 1, "cases": [
                {"case_id": "detached", "feature": "csv", "input": {}, "expected": 1}]}))
            for stay_alive in (False, True):
                script = ("import subprocess,sys,time; "
                          "subprocess.Popen([sys.executable,'-c','import time;time.sleep(2)'], "
                          "start_new_session=True); print('{\"result\":1}', flush=True); "
                          + ("time.sleep(2)" if stay_alive else ""))
                started = time.monotonic()
                result = evaluate(fixture, [sys.executable, "-c", script], .05)
                self.assertLess(time.monotonic() - started, 1.5)
                self.assertEqual(result["csv"]["cases"][0]["error"], "candidate timeout")
                self.assertFalse(result["csv"]["completed"])

    def test_fixture_versions_duplicate_keys_and_overflow_reject_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / 'cases.json'
            for version in (True, 1.0):
                spec = json.loads(self.cases.read_text())
                spec['schema_version'] = version
                fixture.write_text(json.dumps(spec))
                with self.subTest(version=version), self.assertRaises(ValueError):
                    evaluate(fixture, self.reference)
            for raw in ('{"schema_version":1,"schema_version":1,"cases":[]}',
                        '{"schema_version":1,"cases":[{"case_id":"x","feature":"csv","input":{},"expected":1e999}]}'):
                fixture.write_text(raw)
                with self.assertRaises(ValueError):
                    evaluate(fixture, self.reference)

    def test_self_modification_and_declared_dependency_mutation_withhold_credit(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / 'candidate.py'
            dependency = Path(tmp) / 'dependency.txt'
            dependency.write_text('original')
            reference = Path(self.reference[1]).read_text()
            for target in (candidate, dependency):
                candidate.write_text(reference + '\nfrom pathlib import Path\np=Path('+repr(str(target))+')\np.write_text(p.read_text()+"\\n# changed")\n')
                evidence = evaluate(self.cases, [sys.executable, str(candidate)], source_files=[candidate, dependency])
                self.assertTrue(all(evidence[f]['completed'] for f in ('csv', 'budget')))
                self.assertFalse(evidence['binding']['bound'])
                out = raw_score({'test':0}, behavior=evidence, cases_path=self.cases, source_files=[candidate, dependency])
                self.assertFalse(out['tests_cover_csv'])

    def test_immutable_output_refuses_overwrite(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'behavior.json'
            command = [sys.executable, str(LAB / 'behavior.py'), '--cases', str(self.cases),
                       '--output', str(output), '--source', self.reference[1], '--', *self.reference]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            raw = output.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(output.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
