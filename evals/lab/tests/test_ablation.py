import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from attempt import digest, resolve_policy
from ablation import (validate_pair, prepare_pair, verify_pair, guarded_pair,
                      catalog_closure, prepare_factor, verify_factor, guarded_factor,
                      retain_observation, inspect_observation, catalog_inventory)


class PairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.inputs = {}
        entries = {'seed': {'README.md': 'Current requirement: preserve notes.\n',
                            'candidate.py': 'raise NotImplementedError\n',
                            'notes.txt': 'unrelated dirty work\n'},
                   'helper': {'lab/helper.py': '# shared helper\n'},
                   'driver': {'driver.py': '# trusted local caller\n'},
                   'scorer': {'grade.py': '# independent grader\n'},
                   'cases': {'cases.json': '{"cases": ["held-out"]}\n'}}
        for role, files in entries.items():
            self.inputs[role] = {}
            for name, text in files.items():
                path = self.root / 'sources' / role / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
                self.inputs[role][name] = path
        values = dict(provider='local', model='synthetic', effort='test',
                      timeout_seconds=10, max_calls=1, max_actual_usd=None,
                      max_equivalent_usd=10, limit_mode='monitored',
                      accept_last_response_overrun=True)
        common = {'baseline_commit': 'a' * 40,
                  'policy': resolve_policy({k: {'value': v, 'source': 'synthetic fixture'}
                                            for k, v in values.items()}),
                  'tools': ['read', 'write', 'shell'],
                  'permissions': {'sandbox': 'isolated', 'network': False},
                  'collaboration': {'allowed': True, 'max_agents': 2},
                  'required_checks': ['acceptance', 'preservation'],
                  'protected_files': ['notes.txt'],
                  'facts': ['README.md'], 'public_brief': 'README.md'}
        for role, field in [('seed', 'seed_hashes'), ('helper', 'helper_hashes'),
                            ('driver', 'driver_hashes'), ('scorer', 'scorer_hashes'),
                            ('cases', 'case_hashes')]:
            common[field] = {n: digest(p.read_bytes()) for n, p in self.inputs[role].items()}
        treatment = {'mandatory_context': 'full', 'mechanical_state': 'manual',
                     'exposed_catalog': ['approve-plan', 'implementation-plan', 'task-init']}
        self.spec = {'schema_version': 1, 'pair_id': 'local-pair',
                     'factor': 'mandatory_context',
                     'arms': [{'arm_id': 'control', 'common': common,
                               'treatment': treatment},
                              {'arm_id': 'treatment', 'common': copy.deepcopy(common),
                               'treatment': dict(treatment, mandatory_context='kernel')}]}

    def prepare(self, name='pair', spec=None):
        return prepare_pair(self.root / name, spec or self.spec, self.inputs)

    def test_each_legitimate_pair_changes_one_factor(self):
        for factor, value in [('mandatory_context', 'kernel'),
                              ('mechanical_state', 'prototype'),
                              ('exposed_catalog', ['task-init'])]:
            with self.subTest(factor=factor):
                spec = copy.deepcopy(self.spec)
                spec['factor'] = factor
                spec['arms'][1]['treatment'] = copy.deepcopy(spec['arms'][0]['treatment'])
                spec['arms'][1]['treatment'][factor] = value
                self.assertEqual(validate_pair(spec)['factor'], factor)
                binding = self.prepare(factor, spec)
                record = verify_pair(binding)
                self.assertEqual(record['spec'], spec)

    def test_every_common_condition_difference_refuses_without_writing(self):
        mutations = {
            'model': lambda c: c['policy']['values'].__setitem__('model', 'other'),
            'effort': lambda c: c['policy']['values'].__setitem__('effort', 'other'),
            'limit': lambda c: c['policy']['values'].__setitem__('max_calls', 2),
            'policy_source': lambda c: c['policy']['sources'].__setitem__('model', 'other'),
            'tools': lambda c: c['tools'].append('browser'),
            'permission': lambda c: c['permissions'].__setitem__('network', True),
            'collaboration': lambda c: c['collaboration'].__setitem__('max_agents', 3),
            'facts': lambda c: c['facts'].append('notes.txt'),
            'checks': lambda c: c['required_checks'].pop(),
            'dirty_work': lambda c: c['seed_hashes'].__setitem__('notes.txt', '0' * 64),
            'helper': lambda c: c['helper_hashes'].__setitem__('lab/helper.py', '0' * 64),
            'scorer': lambda c: c['scorer_hashes'].__setitem__('grade.py', '0' * 64),
            'fixture': lambda c: c['case_hashes'].__setitem__('cases.json', '0' * 64),
            'baseline': lambda c: c.__setitem__('baseline_commit', 'b' * 40),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                spec = copy.deepcopy(self.spec)
                mutate(spec['arms'][1]['common'])
                with self.assertRaises(ValueError):
                    self.prepare(name, spec)
                self.assertFalse((self.root / name).exists())

    def test_second_factor_or_no_factor_difference_is_rejected(self):
        for treatment in [dict(self.spec['arms'][1]['treatment'], mechanical_state='prototype'),
                          copy.deepcopy(self.spec['arms'][0]['treatment'])]:
            spec = copy.deepcopy(self.spec)
            spec['arms'][1]['treatment'] = treatment
            with self.assertRaises(ValueError):
                validate_pair(spec)

    def test_schema_and_json_types_are_not_coerced(self):
        for change in [lambda s: s.__setitem__('schema_version', True),
                       lambda s: s.__setitem__('schema_version', 1.0),
                       lambda s: s.__setitem__('unexpected', True),
                       lambda s: s['arms'][1].__setitem__('arm_id', 'control'),
                       lambda s: s['arms'][0]['common']['policy']['values'].__setitem__('max_calls', True),
                       lambda s: s['arms'][0]['treatment'].__setitem__('mandatory_context', False)]:
            spec = copy.deepcopy(self.spec)
            change(spec)
            with self.assertRaises(ValueError):
                validate_pair(spec)

    def test_closed_permission_and_policy_fields_refuse_before_writing(self):
        permissions = [{'sandbox': [], 'network': 'false'},
                       {'sandbox': 'isolated', 'network': 0},
                       {'sandbox': '', 'network': False},
                       {'sandbox': 'isolated'},
                       {'sandbox': 'isolated', 'network': False, 'extra': []}]
        for i, value in enumerate(permissions):
            with self.subTest(permissions=value):
                spec = copy.deepcopy(self.spec)
                for arm in spec['arms']:
                    arm['common']['permissions'] = value
                with self.assertRaises(ValueError):
                    self.prepare('permissions-' + str(i), spec)
                self.assertFalse((self.root / ('permissions-' + str(i))).exists())
        spec = copy.deepcopy(self.spec)
        for arm in spec['arms']:
            arm['common']['policy']['values']['extra'] = []
            arm['common']['policy']['sources']['extra'] = 'fixture'
        with self.assertRaises(ValueError):
            self.prepare('extra-policy', spec)
        self.assertFalse((self.root / 'extra-policy').exists())

    def test_distinct_workspace_roots_keep_exact_shared_bytes_and_dirty_work(self):
        binding = self.prepare()
        record = verify_pair(binding)
        control = Path(record['arms']['control']['workspace'])
        treatment = Path(record['arms']['treatment']['workspace'])
        self.assertNotEqual(control, treatment)
        for name, path in self.inputs['seed'].items():
            self.assertEqual((control / name).read_bytes(), path.read_bytes())
            self.assertEqual((treatment / name).read_bytes(), path.read_bytes())
        calls = []
        self.assertEqual(guarded_pair(binding, 'control', lambda: calls.append('entered') or 7), 7)
        self.assertEqual(calls, ['entered'])

    def test_changed_common_source_in_each_role_blocks_callback(self):
        binding = self.prepare()
        for role, paths in self.inputs.items():
            path = next(iter(paths.values()))
            before = path.read_bytes()
            with self.subTest(role=role):
                path.write_bytes(before + b'changed\n')
                calls = []
                with self.assertRaises(ValueError):
                    guarded_pair(binding, 'control', lambda: calls.append('entered'))
                self.assertEqual(calls, [])
            path.write_bytes(before)
        verify_pair(binding)

    def test_changed_arm_inputs_block_even_the_other_arm_callback(self):
        binding = self.prepare()
        record = verify_pair(binding)
        arm = Path(record['arms']['treatment']['workspace']).parent
        for path in [arm / 'prompt.txt', arm / 'settings.json',
                     arm / 'workspace/notes.txt', arm / 'workspace/candidate.py']:
            before = path.read_bytes()
            with self.subTest(path=path.name):
                path.write_bytes(before + b'changed\n')
                calls = []
                with self.assertRaises(ValueError):
                    guarded_pair(binding, 'control', lambda: calls.append('entered'))
                self.assertEqual(calls, [])
            path.write_bytes(before)
        verify_pair(binding)

    def test_unlisted_workspace_entries_block_the_other_arm_callback(self):
        binding = self.prepare()
        record = verify_pair(binding)
        workspace = Path(record['arms']['treatment']['workspace'])
        for name in ['AGENTS.md', 'nested/extra.py', 'empty-directory']:
            with self.subTest(name=name):
                path = workspace / name
                path.parent.mkdir(parents=True, exist_ok=True)
                if name == 'empty-directory':
                    path.mkdir()
                else:
                    path.write_text('unexpected input\n')
                calls = []
                with self.assertRaises(ValueError):
                    guarded_pair(binding, 'control', lambda: calls.append('entered'))
                self.assertEqual(calls, [])
                if path.is_dir():
                    path.rmdir()
                else:
                    path.unlink()
                if name.startswith('nested/'):
                    path.parent.rmdir()
        verify_pair(binding)

    def test_implicit_freezer_runtime_drift_blocks_callback(self):
        runtime = self.root / 'runtime'
        runtime.mkdir()
        lab = Path(__file__).resolve().parents[1]
        for name in ('ablation.py', 'attempt.py'):
            (runtime / name).write_bytes((lab / name).read_bytes())
        fixture = runtime / 'fixture.json'
        fixture.write_text(json.dumps({'spec': self.spec,
                                      'inputs': {role: {name: str(path) for name, path in files.items()}
                                                 for role, files in self.inputs.items()}}))
        script = '''
import json, sys
from pathlib import Path
runtime = Path(sys.argv[1])
sys.path.insert(0, str(runtime))
from ablation import prepare_pair, guarded_pair
fixture = json.loads((runtime / 'fixture.json').read_text())
binding = prepare_pair(runtime / 'pair', fixture['spec'], fixture['inputs'])
helper = runtime / 'attempt.py'
helper.write_bytes(helper.read_bytes() + b'\\n# runtime changed\\n')
calls = []
try:
    guarded_pair(binding, 'control', lambda: calls.append('entered'))
except ValueError:
    assert calls == [], calls
else:
    raise AssertionError('changed implicit freezer runtime was accepted: ' + repr(calls))
'''
        result = subprocess.run([sys.executable, '-B', '-c', script, str(runtime)],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_metadata_and_freeze_mutation_refuse_without_reconstructing(self):
        binding = self.prepare()
        record = verify_pair(binding)
        for path in [Path(binding['path']), Path(record['arms']['control']['attempt']['path'])]:
            before = path.read_bytes()
            path.write_bytes(before + b' ')
            with self.assertRaises(ValueError):
                verify_pair(binding)
            path.write_bytes(before)
        original = Path(binding['path']).read_bytes()
        Path(binding['path']).unlink()
        with self.assertRaises(OSError):
            verify_pair(binding)
        self.assertFalse(Path(binding['path']).exists())
        self.assertTrue(original)

    def test_existing_package_is_never_overwritten(self):
        binding = self.prepare()
        before = Path(binding['path']).read_bytes()
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(Path(binding['path']).read_bytes(), before)

    def test_path_escape_alias_and_symlink_inputs_refuse(self):
        for name in ['../escape', '/escape', 'nested/../escape']:
            spec = copy.deepcopy(self.spec)
            for arm in spec['arms']:
                arm['common']['seed_hashes'][name] = '0' * 64
            with self.assertRaises(ValueError):
                validate_pair(spec)
        alias = self.root / 'alias'
        alias.symlink_to(self.root / 'sources', target_is_directory=True)
        inputs = copy.deepcopy(self.inputs)
        inputs['driver']['driver.py'] = alias / 'driver/driver.py'
        with self.assertRaises(ValueError):
            prepare_pair(self.root / 'aliased', self.spec, inputs)
        self.assertFalse((self.root / 'aliased').exists())
        with self.assertRaises(ValueError):
            prepare_pair(alias / 'pair', self.spec, self.inputs)

    def test_missing_or_contradictory_input_set_is_rejected(self):
        for inputs in [dict(self.inputs, cases={}),
                       dict(self.inputs, helper={'other.py': self.inputs['driver']['driver.py']})]:
            with self.assertRaises(ValueError):
                prepare_pair(self.root / 'invalid', self.spec, inputs)
        self.assertFalse((self.root / 'invalid').exists())

    def test_live_symlink_replacement_refuses_and_preserves_protected_bytes(self):
        binding = self.prepare()
        record = verify_pair(binding)
        path = Path(record['arms']['treatment']['workspace']) / 'notes.txt'
        before = path.read_bytes()
        path.unlink()
        path.symlink_to(self.inputs['seed']['notes.txt'])
        with self.assertRaises(ValueError):
            guarded_pair(binding, 'control', lambda: self.fail('callback entered'))
        self.assertEqual(self.inputs['seed']['notes.txt'].read_bytes(), before)

    def test_unknown_arm_never_enters_callback(self):
        binding = self.prepare()
        with self.assertRaises(ValueError):
            guarded_pair(binding, 'other', lambda: self.fail('callback entered'))


class FactorTests(unittest.TestCase):
    def setUp(self):
        case = PairTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        self.root, self.inputs, self.spec = case.root, case.inputs, case.spec
        self.workflow = self.root / 'workflow'
        self.workflow.mkdir()
        lab = Path(__file__).resolve().parents[1]
        repo = lab.parents[1]
        for name in ('evals/lab/state.py', 'evals/lab/attempt.py',
                     'scripts/verify-log-validator.py', 'scripts/emit-substrate-write.sh'):
            target = self.workflow / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((repo / name).read_bytes())
        bootstrap = ['## LLM execution contract', '## Editor mode policy',
                     '## Global output contract', '## Cross-cutting workflow guardrails']
        # Synthetic source fixtures, not certification of real bootstrap semantics.
        (self.workflow / 'WORKFLOW_OPERATING_SYSTEM.md').write_bytes(
            ''.join(h + '\r\nCurrent visible-and-unchanged reuse applies.\r\n'
                    for h in bootstrap).encode())
        shared = self.workflow / 'commands/_shared/mandatory-context-bootstrap.md'
        shared.parent.mkdir(parents=True)
        shared.write_text('Reuse only visible unchanged context; never a read receipt.\n')
        entries = [{'name': 'task-init', 'next_commands': ['branch-commit --apply']},
                   {'name': 'branch-commit', 'next_commands': ['pr-package --apply']},
                   {'name': 'pr-package', 'next_commands': ['task-init']},
                   {'name': 'review-hard', 'next_commands': []}]
        self.catalog_path = self.workflow / 'docs/command-catalog.json'
        self.catalog_path.parent.mkdir()
        self.catalog_path.write_text(json.dumps({'schema_version': 1, 'command_count': 4,
                                                'commands': entries}))
        for entry in entries:
            (self.workflow / 'commands' / (entry['name'] + '.md')).write_text('# source\n')
        clauses = {'source': 'Canonical source first; missing source is unknown.',
                   'authorization': 'Only approved slice scope may be implemented.',
                   'protected_work': 'Preserve unrelated dirty notes byte-for-byte.',
                   'latest_requirement': 'Requirement version2 supersedes the old order.',
                   'unknown_verification': 'Missing or stale checks remain unknown.',
                   'verification_evidence': 'Pass needs actual current completed checks.',
                   'one_factor': 'Change exactly one mechanism per comparison.',
                   'no_default_promotion': 'No default promotion from shorter text.'}
        guard_path = self.workflow / 'guards.md'
        guard_path.write_text(''.join(text + '\n' for text in clauses.values()))
        self.guards = {name: {'path': 'guards.md', 'start_line': i, 'end_line': i,
                             'sha256': digest((text + '\n').encode())}
                       for i, (name, text) in enumerate(clauses.items(), 1)}
        self.names = sorted(entry['name'] for entry in entries)
        for arm in self.spec['arms']:
            arm['treatment']['exposed_catalog'] = self.names.copy()

    def prepare(self, factor='mandatory_context', name=None, guards=None):
        spec = copy.deepcopy(self.spec)
        spec['factor'] = factor
        spec['arms'][1]['treatment'] = copy.deepcopy(spec['arms'][0]['treatment'])
        value = {'mandatory_context': 'kernel', 'mechanical_state': 'prototype',
                 'exposed_catalog': ['branch-commit', 'pr-package', 'task-init']}[factor]
        spec['arms'][1]['treatment'][factor] = value
        return prepare_factor(self.root / (name or factor), spec, self.inputs,
                              self.workflow, self.guards if guards is None else guards, ['task-init'])

    def observation(self, factor, enabled, *, truncated=False, routes=(), origin='synthetic', name='obs'):
        source = self.root / (name + '-source.json')
        source.write_text(json.dumps({'enabled': enabled, 'truncated': truncated,
                                      'observed_routes': list(routes)}))
        provenance = {'origin': origin, 'producer': 'fixture', 'episode_id': 'local-pair',
                      'arm_id': 'treatment', 'adapter_id': None}
        return retain_observation(self.root / name, 'host_inventory', source, provenance)

    def test_actual_three_payload_pairs_differ_only_in_declared_factor(self):
        for factor in ('mandatory_context', 'mechanical_state', 'exposed_catalog'):
            with self.subTest(factor=factor):
                binding = self.prepare(factor)
                record = verify_factor(binding)
                differences = {key for key in record['payloads']['control']
                               if record['payloads']['control'][key]['sha256']
                               != record['payloads']['treatment'][key]['sha256']}
                self.assertEqual(differences, {factor})
                self.assertEqual(record['model_delivery'], 'unknown')
                pair = verify_pair(record['pair'])
                self.assertEqual(pair['spec']['arms'][0]['common'], pair['spec']['arms'][1]['common'])
                self.assertTrue(all(name in pair['spec']['arms'][0]['common']['helper_hashes']
                                    for name in ('workflow/evals/lab/state.py',
                                                 'workflow/scripts/verify-log-validator.py',
                                                 'workflow/scripts/emit-substrate-write.sh')))
                calls = []
                guarded_factor(binding, 'control', lambda: calls.append('entered'))
                self.assertEqual(calls, ['entered'])

    def test_cli_prepares_and_verifies_independently_held_binding(self):
        spec = copy.deepcopy(self.spec)
        spec['arms'][1]['treatment']['mandatory_context'] = 'kernel'
        request = {'destination': str(self.root / 'cli-pair'), 'spec': spec,
                   'inputs': {role: {n: str(p) for n, p in paths.items()}
                              for role, paths in self.inputs.items()},
                   'workflow_root': str(self.workflow), 'guards': self.guards,
                   'catalog_roots': ['task-init']}
        request_path = self.root / 'request.json'
        request_path.write_text(json.dumps(request))
        entry = Path(__file__).resolve().parents[1] / 'ablation.py'
        prepared = subprocess.run([sys.executable, '-B', str(entry), '--prepare', str(request_path)],
                                  capture_output=True, text=True)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        binding = json.loads(prepared.stdout)
        binding_path = self.root / 'independently-held-binding.json'
        binding_path.write_text(json.dumps(binding))
        verified = subprocess.run([sys.executable, '-B', str(entry), '--verify', str(binding_path)],
                                  capture_output=True, text=True)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout), {'factor': 'mandatory_context',
                         'local_integrity': 'verified', 'model_delivery': 'unknown'})
        prompt = Path(verify_factor(binding)['invocations']['treatment']['prompt']['path'])
        prompt.write_bytes(prompt.read_bytes() + b'changed\n')
        refused = subprocess.run([sys.executable, '-B', str(entry), '--verify', str(binding_path)],
                                 capture_output=True, text=True)
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual(refused.stdout, '')

    def test_full_context_retains_exact_crlf_and_reuse_with_common_task_guards(self):
        record = verify_factor(self.prepare())
        full = Path(record['payloads']['control']['mandatory_context']['path']).read_bytes()
        self.assertEqual(full, (self.workflow / 'WORKFLOW_OPERATING_SYSTEM.md').read_bytes()
                         + b'\n' + (self.workflow / 'commands/_shared/mandatory-context-bootstrap.md').read_bytes())
        self.assertIn(b'visible-and-unchanged reuse', full)
        for arm in ('control', 'treatment'):
            prompt = Path(record['invocations'][arm]['prompt']['path']).read_bytes()
            for text in ['Preserve unrelated dirty notes', 'version2 supersedes',
                         'Missing or stale checks remain unknown']:
                self.assertIn(text.encode(), prompt)

    def test_real_bootstrap_reuse_contract_is_in_full_payload_and_invocation(self):
        from context import sections
        repo = Path(__file__).resolve().parents[3]
        wos = (repo / 'WORKFLOW_OPERATING_SYSTEM.md').read_bytes()
        shared = (repo / 'commands/_shared/mandatory-context-bootstrap.md').read_bytes()
        (self.workflow / 'WORKFLOW_OPERATING_SYSTEM.md').write_bytes(wos)
        (self.workflow / 'commands/_shared/mandatory-context-bootstrap.md').write_bytes(shared)
        record = verify_factor(self.prepare())
        full = Path(record['payloads']['control']['mandatory_context']['path']).read_bytes()
        selected = b''.join(row['text'].encode() for row in sections(wos.decode())
                            if row['heading'] in ['## LLM execution contract', '## Editor mode policy',
                                                  '## Global output contract',
                                                  '## Cross-cutting workflow guardrails'])
        self.assertEqual(full, selected + b'\n' + shared)
        prompt = Path(record['invocations']['control']['prompt']['path']).read_bytes()
        self.assertIn(shared, prompt)
        self.assertIn(b'Session bootstrap reuse', full)

    def test_missing_guard_or_changed_audited_passage_refuses_before_preparation(self):
        for name in self.guards:
            guards = copy.deepcopy(self.guards)
            del guards[name]
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.prepare(name='missing-' + name, guards=guards)
            self.assertFalse((self.root / ('missing-' + name)).exists())
        guards = copy.deepcopy(self.guards)
        guards['latest_requirement']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.prepare(name='stale-guard', guards=guards)
        self.assertFalse((self.root / 'stale-guard').exists())

    def test_actual_prepared_prompt_or_shared_helper_drift_blocks_both_callbacks(self):
        binding = self.prepare('mechanical_state')
        record = verify_factor(binding)
        for path in [Path(record['invocations']['treatment']['prompt']['path']),
                     self.workflow / 'scripts/verify-log-validator.py']:
            before = path.read_bytes()
            path.write_bytes(before + b'changed\n')
            calls = []
            with self.assertRaises(ValueError):
                guarded_factor(binding, 'control', lambda: calls.append('entered'))
            self.assertEqual(calls, [])
            path.write_bytes(before)
        verify_factor(binding)

    def test_source_drift_between_payload_read_and_freeze_is_refused(self):
        import ablation
        builder = ablation._factor_payloads
        for name in ('WORKFLOW_OPERATING_SYSTEM.md', 'docs/command-catalog.json', 'guards.md',
                     'commands/_shared/mandatory-context-bootstrap.md'):
            source = self.workflow / name
            before = source.read_bytes()
            def drift(*args, **kwargs):
                assets = builder(*args, **kwargs)
                source.write_bytes(before + b'\n')
                return assets
            destination = 'drift-' + source.name
            try:
                with mock.patch.object(ablation, '_factor_payloads', side_effect=drift):
                    with self.subTest(source=name), self.assertRaises(ValueError):
                        self.prepare(name=destination)
                self.assertFalse((self.root / destination).exists())
            finally:
                source.write_bytes(before)

    def test_static_catalog_handles_cycles_cli_arguments_and_actual_source_count(self):
        graph = catalog_closure(self.workflow, ['/task-init'])
        self.assertEqual(graph['selected'], ['branch-commit', 'pr-package', 'task-init'])
        self.assertEqual(len(graph['names']), 4)
        self.assertIn({'from': 'branch-commit', 'raw': 'pr-package --apply',
                       'command': 'pr-package', 'arguments': ['--apply']}, graph['routes'])
        self.assertIn('dynamic dispatch', graph['scope'])

    def test_unknown_malformed_duplicate_routes_or_missing_sources_refuse(self):
        original = self.catalog_path.read_text()
        for route in ['missing-command --apply', '"unterminated', '']:
            data = json.loads(original)
            data['commands'][0]['next_commands'] = [route]
            self.catalog_path.write_text(json.dumps(data))
            with self.subTest(route=route), self.assertRaises(ValueError):
                catalog_closure(self.workflow, ['task-init'])
        data = json.loads(original)
        data['commands'].append(data['commands'][0])
        self.catalog_path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            catalog_closure(self.workflow, ['task-init'])
        self.catalog_path.write_text(original)
        (self.workflow / 'commands/pr-package.md').unlink()
        with self.assertRaises(OSError):
            catalog_closure(self.workflow, ['task-init'])

    def test_inventory_missing_extra_truncated_and_unsupported_dynamic_route_are_mismatches(self):
        binding = self.prepare('exposed_catalog')
        expected = ['branch-commit', 'pr-package', 'task-init']
        cases = [('missing', expected[:-1], False, []),
                 ('extra', expected + ['review-hard'], False, []),
                 ('truncated', expected, True, []),
                 ('dynamic', expected, False, ['review-hard']),
                 ('valid', expected, False, ['branch-commit --apply'])]
        for name, enabled, truncated, routes in cases:
            with self.subTest(name=name):
                obs = self.observation(binding, enabled, truncated=truncated, routes=routes, name=name)
                report = catalog_inventory(binding, 'treatment', obs)
                self.assertEqual(report['inventory_consistency'], 'match' if name == 'valid' else 'mismatch')
                self.assertEqual(report['actual_exposure'], 'unknown')
                self.assertEqual(report['model_delivery'], 'unknown')

    def test_observation_layers_preserve_raw_bytes_without_delivery_or_invoice_inference(self):
        source = self.root / 'raw-source.bin'
        source.write_bytes(b'\xff\x00\r\nobserved raw bytes\r\n')
        provenance = {'origin': 'host-recorded', 'producer': 'declared-local-caller',
                      'episode_id': 'local-pair', 'arm_id': 'control', 'adapter_id': 'unsupported'}
        for kind in ('submitted_prompt', 'tool_return', 'host_inventory',
                     'provider_model_visible', 'usage', 'invoice'):
            binding = retain_observation(self.root / kind, kind, source, provenance)
            report = inspect_observation(binding)
            self.assertEqual(report['raw'], source.read_bytes())
            self.assertEqual(report['model_delivery'], 'unknown')
            self.assertEqual(report['provenance_attestation'], 'unknown')
            self.assertEqual(report['invoice_attestation'], 'unknown')

    def test_observation_source_retained_bytes_or_record_drift_is_rejected(self):
        source = self.root / 'observation-source'
        source.write_bytes(b'original\n')
        provenance = {'origin': 'synthetic', 'producer': 'fixture', 'episode_id': 'local-pair',
                      'arm_id': 'control', 'adapter_id': None}
        binding = retain_observation(self.root / 'observation', 'tool_return', source, provenance)
        report = inspect_observation(binding)
        for path in [source, Path(report['record']['retained']['path']), Path(binding['path'])]:
            before = path.read_bytes()
            path.write_bytes(before + b' ')
            with self.assertRaises(ValueError):
                inspect_observation(binding)
            path.write_bytes(before)
        with self.assertRaises(FileExistsError):
            retain_observation(self.root / 'observation', 'tool_return', source, provenance)
        source.unlink()
        with self.assertRaises(OSError):
            inspect_observation(binding)

    def test_identical_changed_observation_copies_still_refuse_original_hash(self):
        source = self.root / 'paired-observation-source'
        source.write_bytes(b'original\n')
        provenance = {'origin': 'synthetic', 'producer': 'fixture', 'episode_id': 'local-pair',
                      'arm_id': 'control', 'adapter_id': None}
        binding = retain_observation(self.root / 'paired-observation', 'tool_return', source, provenance)
        retained = Path(inspect_observation(binding)['record']['retained']['path'])
        # Equal length and equal copies are insufficient: both lost the frozen original.
        source.write_bytes(b'modified\n')
        retained.write_bytes(b'modified\n')
        with self.assertRaisesRegex(ValueError, 'retained source bytes changed'):
            inspect_observation(binding)

    def test_observation_consumer_revalidates_typed_provenance_and_layer(self):
        source = self.root / 'typed-observation-source'
        source.write_bytes(b'raw\n')
        provenance = {'origin': 'synthetic', 'producer': 'fixture', 'episode_id': 'local-pair',
                      'arm_id': 'control', 'adapter_id': None}
        binding = retain_observation(self.root / 'typed-observation', 'tool_return', source, provenance)
        path = Path(binding['path'])
        original = json.loads(path.read_bytes())
        # Self-consistent local record hash is no substitute for consumer schema validation.
        for field, value in [('origin', []), ('producer', ''), ('episode_id', 4),
                             ('arm_id', 'other'), ('adapter_id', False)]:
            record = copy.deepcopy(original)
            record['provenance'][field] = value
            raw = json.dumps(record).encode()
            path.write_bytes(raw)
            with self.subTest(field=field), self.assertRaises(ValueError):
                inspect_observation(dict(binding, sha256=digest(raw)))
        record = copy.deepcopy(original)
        record['kind'] = []
        raw = json.dumps(record).encode()
        path.write_bytes(raw)
        with self.assertRaises(ValueError):
            inspect_observation(dict(binding, sha256=digest(raw)))


if __name__ == '__main__':
    unittest.main()
