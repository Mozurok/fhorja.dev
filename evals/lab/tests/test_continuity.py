import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from continuity import FIXTURE, grade, prepare


REFERENCE = Path(__file__).resolve().parents[1] / 'fixtures/reference_continuity.py'


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'candidate'
        prepare(self.repo, 'continuity')
        self.handoff()

    def handoff(self, **changes):
        value = dict(requirement_version=2, previous_verification='unknown', remaining=[])
        value.update(changes)
        (self.repo / 'handoff.json').write_text(json.dumps(value))

    def reference(self, variant='reference', fault=None):
        source = REFERENCE.read_text()
        (self.repo / 'candidate.py').write_text(source + '\n')
        return grade(self.repo, command=[sys.executable, str(self.repo / 'candidate.py'), *[x for x in (variant, fault) if x]])

    def test_two_legitimate_algorithms_pass_real_processes(self):
        for variant in ('reference', 'alternative'):
            result = self.reference(variant)
            self.assertTrue(result['accepted'], result)
            self.assertTrue(all(row['executed'] for row in result['cases']))

    def test_obsolete_order_and_duplicate_loss_are_rejected(self):
        for fault in ('sorted', 'deduplicate'):
            result = self.reference(fault=fault)
            self.assertFalse(result['accepted'])
            self.assertTrue(any(row.get('passed') is False for row in result['cases']))

    def test_signed_large_values_and_zero_totals_protect_exactness(self):
        for fault in ('float', 'absolute', 'drop-zero'):
            result = self.reference(fault=fault)
            self.assertFalse(result['accepted'])
            failed = [row['case_id'] for row in result['cases'] if row.get('passed') is False]
            self.assertTrue(failed, fault)

    def test_bool_and_malformed_contract_defects_are_rejected(self):
        for fault, target in [('allow-bool', 'boolean-delta'), ('bad-error', 'invalid-rows')]:
            result = self.reference(fault=fault)
            row = next(row for row in result['cases'] if row['case_id'] == target)
            self.assertFalse(row['passed'])
            self.assertFalse(result['accepted'])

    def test_existing_valid_work_and_dirty_user_file_are_preserved(self):
        self.assertTrue(self.reference()['accepted'])
        for name in ('helpers.py', 'notes.txt'):
            original = (self.repo / name).read_bytes()
            (self.repo / name).write_text('discarded')
            result = self.reference()
            self.assertFalse(result['accepted'])
            self.assertIn(name, [c['path'] for c in result['preservation'] if not c['passed']])
            (self.repo / name).write_bytes(original)

    def test_probe_time_file_mutation_is_rejected(self):
        source = REFERENCE.read_text()
        source += '\nfrom pathlib import Path\nPath("notes.txt").write_text("discarded")\n'
        (self.repo / 'candidate.py').write_text(source)
        result = grade(self.repo)
        self.assertFalse(result['accepted'])
        self.assertFalse(next(c for c in result['preservation'] if c['path'] == 'notes.txt')['passed'])

    def test_unknown_prior_verification_is_not_a_pass_claim(self):
        self.handoff(previous_verification='passed')
        result = self.reference()
        self.assertFalse(result['accepted'])
        self.assertFalse(result['handoff']['passed'])

    def test_missing_and_wrong_requirement_handoff_are_rejected(self):
        (self.repo / 'handoff.json').unlink()
        self.assertFalse(self.reference()['accepted'])
        self.handoff(requirement_version=1)
        self.assertFalse(self.reference()['accepted'])

    def test_initial_partial_patch_fails_new_acceptance(self):
        result = grade(self.repo)
        self.assertFalse(result['accepted'])
        row = next(r for r in result['cases'] if r['case_id'] == 'first-seen-order')
        self.assertFalse(row['passed'])

    def test_expected_answers_and_grader_are_not_in_candidate_workspace(self):
        self.assertNotIn('continuity_cases.json', [p.name for p in self.repo.rglob('*')])
        self.assertNotIn('reference_continuity.py', [p.name for p in self.repo.rglob('*')])
        with self.assertRaises(FileExistsError):
            prepare(self.repo, 'integration')

    def test_exit_protocol_and_wrong_result_are_classified(self):
        for code, error in [('raise SystemExit(1)', 'candidate exit failure'),
                            ('print("not JSON")', 'candidate protocol failure: JSONDecodeError')]:
            (self.repo / 'candidate.py').write_text(code)
            result = grade(self.repo)
            self.assertFalse(result['accepted'])
            self.assertTrue(all(r['error'] == error and not r['executed'] for r in result['cases']))
        (self.repo / 'candidate.py').write_text('import json; print(json.dumps({"result": []}))')
        row = grade(self.repo)['cases'][0]
        self.assertTrue(row['executed'])
        self.assertEqual(row['observed'], [])
        self.assertFalse(row['passed'])
        self.assertNotIn('error', row)

    def test_timeout_is_classified_separately(self):
        (self.repo / 'candidate.py').write_text('import time; time.sleep(2)')
        fixture = Path(self.temp.name) / 'timeout.json'
        fixture.write_text(json.dumps({'schema_version': 1, 'cases': [json.loads(FIXTURE.read_text())['cases'][0]]}))
        row = grade(self.repo, fixture, timeout=.05)['cases'][0]
        self.assertEqual(row['error'], 'candidate timeout')
        self.assertFalse(row['executed'])
        self.assertFalse(row['passed'])

    def test_invalid_fixture_rejected_before_execution(self):
        invalid = json.loads(FIXTURE.read_text())
        invalid['cases'].append(invalid['cases'][0])
        fixture = Path(self.temp.name) / 'invalid.json'
        fixture.write_text(json.dumps(invalid))
        with self.assertRaises(ValueError):
            grade(self.repo, fixture)
        with self.assertRaisesRegex(ValueError, 'candidate command required'):
            grade(self.repo, command=[])
        fixture.write_text('[]')
        with self.assertRaises(ValueError):
            grade(self.repo, fixture)

    def test_duplicate_keys_are_rejected(self):
        (self.repo / 'candidate.py').write_text('print(' + repr('{"result": [], "result": []}') + ')')
        result = grade(self.repo)
        self.assertFalse(result['accepted'])
        self.assertTrue(all(r['error'] == 'candidate protocol failure: ValueError' for r in result['cases']))

    def test_boolean_and_float_cannot_replace_integer_units(self):
        fixture = Path(self.temp.name) / 'integer.json'
        case = json.loads(FIXTURE.read_text())['cases'][0]
        fixture.write_text(json.dumps({'schema_version': 1, 'cases': [case]}))
        for substitute in (True, 1.0):
            observed = [dict(row) for row in case['expected']]
            observed[0]['units'] = substitute
            encoded = json.dumps({'result': observed})
            (self.repo / 'candidate.py').write_text('print(' + repr(encoded) + ')')
            row = grade(self.repo, fixture)['cases'][0]
            self.assertTrue(row['executed'])
            self.assertEqual(type(row['observed'][0]['units']), type(substitute))
            self.assertFalse(row['passed'])

    def test_protected_symlink_is_rejected(self):
        original = self.repo / 'notes.txt'
        original.unlink()
        outside = Path(self.temp.name) / 'outside'
        outside.write_text('unrelated local draft\n')
        original.symlink_to(outside)
        self.assertFalse(self.reference()['accepted'])

    def test_self_modified_candidate_is_not_accepted(self):
        source = REFERENCE.read_text() + '\nfrom pathlib import Path\np=Path(__file__)\np.write_text(p.read_text()+"\\n# changed")\n'
        (self.repo / 'candidate.py').write_text(source)
        result = grade(self.repo)
        self.assertEqual(result['passed'], result['total'])
        self.assertFalse(result['binding']['bound'])
        self.assertFalse(result['accepted'])

    def test_declared_dependency_mutation_is_not_accepted(self):
        dependency = self.repo / 'dependency.txt'
        dependency.write_text('original')
        source = REFERENCE.read_text() + '\nfrom pathlib import Path\nPath("dependency.txt").write_text("changed")\n'
        (self.repo / 'candidate.py').write_text(source)
        result = grade(self.repo, source_files=[self.repo / 'candidate.py', self.repo / 'helpers.py', dependency])
        self.assertEqual(result['passed'], result['total'])
        self.assertFalse(result['accepted'])

    def test_external_reference_cannot_certify_unexecuted_obsolete_candidate(self):
        result = grade(self.repo, command=[sys.executable, str(REFERENCE)])
        self.assertEqual(result['passed'], result['total'])
        self.assertFalse(result['binding']['bound'])
        self.assertFalse(result['accepted'])


if __name__ == '__main__':
    unittest.main()
