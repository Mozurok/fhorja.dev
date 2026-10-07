import copy
import sys
import json
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quality import score as raw_score, WIDTHS
from behavior import evaluate
from attempt import freeze, resolve_policy, seal_evidence


class QualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.fixture = cls.root / "cases.json"
        cls.candidate = cls.root / "candidate.py"
        cls.candidate.write_text("import json,sys; print(json.dumps({'result':json.load(sys.stdin)}))")
        cls.fixture.write_text(json.dumps({"schema_version": 1, "cases": [
            {"case_id": f + "-1", "feature": f, "input": [1, 2], "expected": [1, 2]}
            for f in ("csv", "budget")]}))
        cls.valid_behavior = evaluate(cls.fixture, [sys.executable, str(cls.candidate)], source_files=[cls.candidate])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.rc = dict.fromkeys(["install", "build", "typecheck", "lint", "test"], 0)
        self.browser = {"schemaVersion": 2, "expectedRoutes": ["/"],
                        "routes": [{"route": "/", "ok": True, "status": 200}],
                        "requestedWidths": WIDTHS, "widthProbes": {"/": WIDTHS},
                        "axeCompleted": ["/"], "axe": {"/": []}, "overflow": [],
                        "consoleErrors": [], "lighthouse": {"performance": 90, "accessibility": 95}}
        self.behavior = copy.deepcopy(self.valid_behavior)

    def score(self, rc, browser=None, behavior=None):
        return raw_score(rc, browser, behavior, cases_path=self.fixture, source_files=[self.candidate], candidate_command=[sys.executable, str(self.candidate)])

    def test_completed_reference(self):
        self.assertEqual(self.score(self.rc, self.browser, self.behavior)["total_a"], 20)

    def test_return_code_requires_an_actual_integer(self):
        for substitute in (False, 0.0):
            with self.subTest(substitute=repr(substitute)):
                rc = dict(self.rc, build=substitute)
                self.assertEqual(self.score(rc, self.browser, self.behavior)["score_a"]["build"], 0)

    def test_false_pass_flag_withholds_domain_credit(self):
        self.behavior["csv"]["cases"][0]["passed"] = False
        self.assertFalse(self.score(self.rc, self.browser, self.behavior)["tests_cover_csv"])

    def test_feature_level_false_pass_flag_withholds_domain_credit(self):
        self.behavior['csv']['passed'] = False
        self.assertFalse(self.score(self.rc, self.browser, self.behavior)['tests_cover_csv'])

    def test_extra_feature_group_cannot_hide_invented_cases(self):
        self.behavior['invented'] = copy.deepcopy(self.behavior['csv'])
        self.behavior['invented']['cases'][0]['case_id'] = 'invented'
        out = self.score(self.rc, self.browser, self.behavior)
        self.assertFalse(out['tests_cover_csv'])
        self.assertFalse(out['tests_cover_budget'])

    def test_original_false_green(self):
        old = {"routes": [{"route": "/", "ok": False, "error": "timeout"}],
               "axe": {}, "overflow": [], "consoleErrors": [], "lighthouse": {"performance": 99, "accessibility": 99}}
        out = self.score(self.rc, old)
        self.assertEqual(out["total_a"], 11.5)
        self.assertFalse(out["tests_cover_csv"])
        self.assertFalse(out["browser_completed"])

    def test_failed_route_and_http_error(self):
        for change in [{"ok": False}, {"status": 500}]:
            b = copy.deepcopy(self.browser); b["routes"][0].update(change)
            out = self.score(self.rc, b, self.behavior)
            self.assertEqual(sum(out["score_a"][k] for k in ["console", "overflow", "axe", "lighthouse"]), 0)

    def test_missing_route_or_probe(self):
        for key in ["routes", "widthProbes", "axeCompleted", "consoleErrors"]:
            b = copy.deepcopy(self.browser); del b[key]
            out = self.score(self.rc, b, self.behavior)
            self.assertTrue(out["missing_evidence"])

    def test_skipped_width_and_axe(self):
        b = copy.deepcopy(self.browser); b["widthProbes"]["/"] = [1280]
        b["axeCompleted"] = []
        out = self.score(self.rc, b)
        self.assertEqual(out["score_a"]["overflow"], 0)
        self.assertEqual(out["score_a"]["axe"], 0)

    def test_comment_only_and_unexecuted_cases(self):
        out = self.score(self.rc, self.browser, {"csv": "// csv budget"})
        self.assertEqual(out["score_a"]["test"], 1.5)
        self.behavior["csv"]["cases"][0]["executed"] = False
        self.assertFalse(self.score(self.rc, self.browser, self.behavior)["tests_cover_csv"])

    def test_observed_failure(self):
        self.behavior["budget"]["cases"][0]["observed"] = [99]
        self.assertFalse(self.score(self.rc, self.browser, self.behavior)["tests_cover_budget"])

    def test_empty_rc_unknown_and_demo_unverified(self):
        self.assertEqual(self.score({}, self.browser)["score_a"]["build"], 0)
        out = self.score(self.rc, self.browser)
        self.assertFalse(out["demo_loaded"])
        self.assertEqual(out["demo_verification"], "unverified")

    def test_malformed_results_are_not_clean(self):
        for key, value in [("routes", [self.browser["routes"][0], "bad"]),
                           ("expectedRoutes", ["/", {}]), ("widthProbes", []),
                           ("lighthouse", "bad"), ("axeCompleted", "/")]:
            b = copy.deepcopy(self.browser); b[key] = value
            out = self.score(self.rc, b, {"schema_version": 1, "producer": "independent-harness", "csv": "bad"})
            self.assertTrue(out["missing_evidence"])


    def test_malformed_nested_widths_withhold_credit(self):
        b = copy.deepcopy(self.browser); b["widthProbes"]["/"] = [320, "bad"]
        out = self.score(self.rc, b)
        self.assertFalse(out["viewport_completed"])
        self.assertEqual(out["score_a"]["overflow"], 0)

    def test_domain_fault_matrix_cannot_earn_bound_coverage(self):
        mutations = [
            lambda b: b["csv"]["cases"][0].pop("passed"),
            lambda b: b["csv"]["cases"][0].update(error="failure"),
            lambda b: b["csv"]["cases"][0].update(cleanup_incomplete=True),
            lambda b: b["csv"]["cases"][0].update(exit_code=1),
            lambda b: b["csv"]["cases"][0].update(exit_code=False),
            lambda b: b["csv"]["cases"][0].update(exit_code=0.0),
            lambda b: b["csv"]["cases"].clear(),
            lambda b: b["csv"]["cases"].append(copy.deepcopy(b["csv"]["cases"][0])),
            lambda b: b["csv"]["cases"][0].update(case_id="invented"),
            lambda b: b.update(fixture_sha256="0" * 64),
            lambda b: b.update(schema_version=2.0),
            lambda b: b.update(schema_version=True),
            lambda b: b.update(candidate_command=['different']),
            lambda b: b["csv"]["cases"][0].update(observed=[True, 2]),
            lambda b: b["csv"]["cases"][0].update(observed=[1.0, 2]),
            lambda b: b["csv"]["cases"][0].update(observed=[float("inf"), 2], expected=[float("inf"), 2]),
            lambda b: b["csv"]["cases"][0].update(observed=[9, 2], expected=[9, 2]),
            lambda b: b["binding"].update(bound=False),
            lambda b: b.update(error="failed"),
            lambda b: b.update(cleanup_incomplete=True),
            lambda b: b["csv"].update(error="failed"),
            lambda b: b["csv"].update(cleanup_incomplete=True),
            lambda b: b["csv"]["cases"][0].update(wall_seconds=float("inf")),
            lambda b: b["binding"]["after"]["evaluator"].update({str(Path(__file__).parents[1] / "quality.py"): "0" * 64}),
        ]
        for index, mutate in enumerate(mutations):
            b = copy.deepcopy(self.behavior)
            mutate(b)
            with self.subTest(index=index):
                self.assertFalse(self.score(self.rc, self.browser, b)["tests_cover_csv"])

    def test_exact_fixture_case_order_and_feature_grouping(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases.json"
            spec = json.loads(self.fixture.read_text())
            second = dict(spec["cases"][0], case_id="csv-2")
            spec["cases"].insert(1, second)
            cases.write_text(json.dumps(spec))
            evidence = evaluate(cases, [sys.executable, str(self.candidate)], source_files=[self.candidate])
            def check(value):
                return raw_score(self.rc, self.browser, value, cases_path=cases, source_files=[self.candidate], candidate_command=[sys.executable, str(self.candidate)])
            self.assertEqual(check(evidence)["total_a"], 20)
            evidence["csv"]["cases"].reverse()
            self.assertFalse(check(evidence)["tests_cover_csv"])
            evidence["csv"]["cases"].reverse()
            evidence["csv"]["cases"][1] = evidence["budget"]["cases"][0]
            self.assertFalse(check(evidence)["tests_cover_csv"])

    def test_missing_independent_context_is_explicitly_unbound(self):
        out = raw_score(self.rc, self.browser, self.behavior)
        self.assertFalse(out["tests_cover_csv"])
        self.assertEqual(out["provenance_status"], "unbound")
        out = raw_score(self.rc, self.browser, self.behavior, cases_path=self.fixture, source_files=[self.candidate])
        self.assertFalse(out["tests_cover_csv"])
        out = raw_score(self.rc, self.browser, self.behavior, cases_path=self.fixture,
                        source_files=[self.candidate], candidate_command=[sys.executable, str(self.candidate), 'other'])
        self.assertFalse(out["tests_cover_csv"])

    def test_changed_or_different_candidate_and_fixture_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            different = Path(tmp) / "candidate.py"
            different.write_bytes(self.candidate.read_bytes())
            out = raw_score(self.rc, self.browser, self.behavior, cases_path=self.fixture, source_files=[different])
            self.assertFalse(out["tests_cover_csv"])
            different_cases = Path(tmp) / "cases.json"
            different_cases.write_bytes(self.fixture.read_bytes())
            out = raw_score(self.rc, self.browser, self.behavior, cases_path=different_cases, source_files=[self.candidate], candidate_command=[sys.executable, str(self.candidate)])
            self.assertFalse(out["tests_cover_csv"])
        raw = self.candidate.read_bytes()
        try:
            self.candidate.write_bytes(raw + b"\n# changed\n")
            self.assertFalse(self.score(self.rc, self.browser, self.behavior)["tests_cover_csv"])
        finally:
            self.candidate.write_bytes(raw)

    def test_browser_numeric_types_and_extra_probe_identity_withhold_credit(self):
        for key, value, category in [("schemaVersion", 2.0, "console"),
                                     ("requestedWidths", [float(w) for w in WIDTHS], "overflow"),
                                     ("axeCompleted", ["/", "/extra"], "axe"),
                                     ("error", "failure", "console"),
                                     ("cleanup_incomplete", True, "console"),
                                     ("lighthouse", {"performance": 10**400}, "lighthouse")]:
            b = copy.deepcopy(self.browser)
            b[key] = value
            self.assertEqual(self.score(self.rc, b, self.behavior)["score_a"][category], 0)

    def test_lighthouse_failure_markers_withhold_only_its_credit(self):
        for marker in ({'error': 'native failure'}, {'error': None}, {'error': ''},
                       {'completed': False}, {'passed': False}, {'cleanup_incomplete': True},
                       {'completed': 1}, {'passed': 1}, {'cleanup_incomplete': 0}):
            with self.subTest(marker=marker):
                b = copy.deepcopy(self.browser)
                b['lighthouse'].update(marker)
                result = self.score(self.rc, b, self.behavior)
                self.assertEqual(result['score_a']['lighthouse'], 0)
                self.assertEqual(result['total_a'], 18)
                self.assertIn('successful Lighthouse probe', result['missing_evidence'])
        b = copy.deepcopy(self.browser)
        b['lighthouse'].update(completed=True, passed=True, cleanup_incomplete=False)
        self.assertEqual(self.score(self.rc, b, self.behavior)['total_a'], 20)

    def test_object_order_is_harmless_but_nested_numeric_type_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            cases = Path(tmp) / "cases.json"
            cases.write_text(json.dumps({"schema_version": 1, "cases": [
                {"case_id": "object-" + f, "feature": f, "input": {"b": 2, "a": {"n": -1}},
                 "expected": {"a": {"n": -1}, "b": 2}} for f in ("csv", "budget")]}))
            b = evaluate(cases, [sys.executable, str(self.candidate)], source_files=[self.candidate])
            self.assertEqual(raw_score(self.rc, self.browser, b, cases_path=cases,
                                      source_files=[self.candidate], candidate_command=[sys.executable, str(self.candidate)])["total_a"], 20)
            b["csv"]["cases"][0]["observed"]["a"]["n"] = -1.0
            self.assertFalse(raw_score(self.rc, self.browser, b, cases_path=cases,
                                       source_files=[self.candidate], candidate_command=[sys.executable, str(self.candidate)])["tests_cover_csv"])

    def test_unrelated_declared_source_and_inline_trailing_path_are_unbound(self):
        with tempfile.TemporaryDirectory() as tmp:
            unrelated = Path(tmp) / 'unrelated.py'
            unrelated.write_text('raise SystemExit(8)')
            for command in ([sys.executable, str(self.candidate)],
                            [sys.executable, '-c', "import json,sys;print(json.dumps({'result':json.load(sys.stdin)}))", str(unrelated)]):
                result = evaluate(self.fixture, command, source_files=[unrelated])
                self.assertTrue(result['csv']['completed'])
                self.assertFalse(result['binding']['bound'])
                out = raw_score(self.rc, self.browser, result, cases_path=self.fixture,
                                source_files=[unrelated], candidate_command=command)
                self.assertFalse(out['tests_cover_csv'])

    def test_real_prospective_receipt_binds_all_scored_inputs_and_actual_scorer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            values = dict(provider='local', model='synthetic', effort='test', timeout_seconds=10,
                          max_calls=1, max_actual_usd=None, max_equivalent_usd=100,
                          limit_mode='monitored', accept_last_response_overrun=True)
            policy = resolve_policy({k: {'value': v, 'source': 'synthetic fixture'} for k, v in values.items()})
            prompt = root / 'prompt'; prompt.write_text('synthetic')
            lab = Path(__file__).resolve().parents[1]
            roles = dict(driver=[lab / 'quality.py'], prompt=[prompt], settings=[prompt],
                         scorer=[lab / 'quality.py', lab / 'attempt.py', lab / 'behavior.py'],
                         cases=[self.fixture], source=[self.candidate])
            browser = root / 'browser.json'; browser.write_text(json.dumps(self.browser))
            domain = root / 'behavior.json'; domain.write_text(json.dumps(self.behavior))
            commands = []
            for name in self.rc:
                path = root / (name + '.rc'); path.write_text('0'); commands.append(path)
            artifacts = dict(browser=[str(browser)], behavior=[str(domain)], commands=[str(p) for p in commands])
            binding = freeze(root / 'attempt.json', 'local-1', policy, roles)
            receipt = seal_evidence(root / 'receipt.json', binding, artifacts, [self.candidate])
            prospective = dict(attempt=binding, receipt=receipt, artifacts=artifacts)
            def check(rc=None, b=None, behavior=None, metadata=None):
                return raw_score(self.rc if rc is None else rc, self.browser if b is None else b,
                                 self.behavior if behavior is None else behavior,
                                 cases_path=self.fixture, source_files=[self.candidate],
                                 candidate_command=[sys.executable, str(self.candidate)],
                                 prospective=prospective if metadata is None else metadata)
            valid = check()
            self.assertEqual(valid['total_a'], 20)
            self.assertEqual(valid['provenance_status'], 'bound')
            self.assertEqual(valid['attempt_id'], 'local-1')
            self.assertEqual(check(rc=dict(self.rc, build=False))['total_a'], 0)
            self.assertEqual(check(b=dict(self.browser, consoleErrors=['different']))['total_a'], 0)
            bad = copy.deepcopy(self.behavior); bad['csv']['completed'] = False
            self.assertEqual(check(behavior=bad)['total_a'], 0)
            raw = browser.read_bytes(); browser.write_bytes(raw + b' ')
            self.assertEqual(check()['total_a'], 0); browser.write_bytes(raw)
            missing = dict(prospective, receipt=dict(receipt, sha256='0'*64))
            self.assertEqual(check(metadata=missing)['total_a'], 0)
            unrelated = dict(roles, scorer=[prompt])
            wrong = freeze(root / 'wrong-attempt.json', 'wrong-scorer', policy, unrelated)
            wrong_receipt = seal_evidence(root / 'wrong-receipt.json', wrong, artifacts, [self.candidate])
            wrong_metadata = dict(attempt=wrong, receipt=wrong_receipt, artifacts=artifacts)
            self.assertEqual(check(metadata=wrong_metadata)['total_a'], 0)
            # A matching receipt establishes provenance, not success of a failed probe.
            failed_browser = copy.deepcopy(self.browser)
            failed_browser['lighthouse']['error'] = 'native lighthouse failure'
            browser.write_text(json.dumps(failed_browser))
            failed_receipt = seal_evidence(root / 'failed-lighthouse-receipt.json', binding, artifacts, [self.candidate])
            failed_metadata = dict(attempt=binding, receipt=failed_receipt, artifacts=artifacts)
            failed = check(b=failed_browser, metadata=failed_metadata)
            self.assertEqual(failed['provenance_status'], 'bound')
            self.assertEqual(failed['score_a']['lighthouse'], 0)
            self.assertEqual(failed['total_a'], 18)
            self.assertIn('successful Lighthouse probe', failed['missing_evidence'])



if __name__ == "__main__":
    unittest.main()
