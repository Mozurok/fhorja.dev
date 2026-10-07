import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
from attempt import freeze, resolve_policy, guarded_launch, verify_evidence, strict_json


class HarnessTests(unittest.TestCase):
    def test_real_aggregate_adapter_uses_child_and_preserves_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); harness = root/'harness'; harness.mkdir()
            shutil.copy2(LAB/'harness/aggregate.py', harness/'aggregate.py')
            shutil.copy2(LAB/'usage.py', harness/'usage_ledger.py')
            (harness/'prices.json').write_text(json.dumps({'model': {'input': 2, 'cached_input': .1, 'output': 10}}))
            run = root/'runs/run';run.mkdir(parents=True)
            meta = {'cli': 'codex', 'model': 'model', 'arm': 'base', 'wall_secs': 1, 'timed_out': False, 'exit_code': 0}
            (run/'meta.json').write_text(json.dumps(meta))
            (run/'events.jsonl').write_text(json.dumps({'type': 'thread.started', 'thread_id': 'root'})+'\n')
            sess = root/'envs/codex-base/home/.codex/sessions'; sess.mkdir(parents=True)
            for sid, parent in [('root', None), ('child', 'root')]:
                es = [{'type': 'session_meta', 'payload': {'id': sid, 'parent_thread_id': parent}},
                      {'type': 'turn_context', 'payload': {'model': 'model'}},
                      {'type': 'token_usage_record', 'payload': {'response_id': 'r-'+sid, 'usage': {
                          'input_tokens': 100, 'cached_input_tokens': 20, 'output_tokens': 10}}}]
                (sess/(sid+'.jsonl')).write_text('\n'.join(json.dumps(e) for e in es)+'\n')
            results = root/'results';results.mkdir();old=results/'summary.json';old.write_text('historical')
            env = {k: v for k, v in os.environ.items() if k not in ['RESULTS_DIR', 'FHORJA_SKILLS_DIR']}
            r = subprocess.run([sys.executable, str(harness/'aggregate.py')], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            result = json.loads((results/'summary-v2.json').read_text())[0]
            self.assertEqual(result['tokens']['input'], 160)
            self.assertEqual(result['tokens']['output'], 20)
            self.assertEqual(result['usage_ledger']['sessions'], ['child', 'root'])
            self.assertEqual(old.read_text(), 'historical')

    def test_real_quality_entry_preserves_history_and_missing_rc_is_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            q=Path(tmp);(q/'logs').mkdir();old=q/'auto.json';old.write_text('historical')
            (q/'logs/build.rc').write_text('')
            r=subprocess.run([sys.executable,str(LAB/'quality.py'),str(q),str(q),'npm','0'],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            result=json.loads((q/'auto-v3.json').read_text())
            self.assertIsNone(result['exit_codes']['build'])
            self.assertEqual(result['total_a'],0)
            self.assertEqual(old.read_text(),'historical')
            rerun=subprocess.run([sys.executable,str(LAB/'quality.py'),str(q),str(q),'npm','0'],capture_output=True,text=True)
            self.assertNotEqual(rerun.returncode,0)
            self.assertEqual(json.loads((q/'auto-v3.json').read_text()),result)

    def test_shell_gate_refuses_missing_metadata_before_sourcing_legacy_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); harness=root/'harness';harness.mkdir()
            shutil.copy2(LAB/'harness/quality.sh',harness/'quality.sh')
            sentinel=root/'callback'
            (harness/'lib.sh').write_text('touch '+str(sentinel)+'\n')
            result=subprocess.run(['bash',str(harness/'quality.sh'),'run'],capture_output=True,text=True)
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertFalse(sentinel.exists())

    def test_actual_quality_shell_records_same_attempt_and_preserves_prior_directory(self):
        # Package manager is a local fake; this proves adapter wiring, not npm or browser behavior.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); lab=root/'lab';harness=lab/'harness';harness.mkdir(parents=True)
            for name in ('attempt.py','quality.py','behavior.py'):
                shutil.copy2(LAB/name,lab/name)
            shutil.copy2(LAB/'harness/quality.sh',harness/'quality.sh')
            work=root/'runs/run/work';work.mkdir(parents=True)
            (work/'package.json').write_text(json.dumps({'scripts':dict.fromkeys(('build','typecheck','lint','test'),'local')}))
            (work/'package-lock.json').write_text('{}')
            (work/'candidate.py').write_text('print("local")')
            for args in (['init','-q'],['config','user.email','fixture@example.invalid'],
                         ['config','user.name','Fixture'],['add','.'],['commit','-qm','fixture']):
                subprocess.run(['git','-C',str(work),*args],check=True,capture_output=True)
            tools=root/'tools';tools.mkdir(); npm=tools/'npm';npm.write_text('#!/bin/sh\nexit 0\n');npm.chmod(0o755)
            (harness/'lib.sh').write_text('ROOT='+str(root)+'\nRUNS="$ROOT/runs"\nHARNESS='+str(harness)+
                '\nREAL_HOME="$ROOT/home"\nagent_env() { AENV=("PATH='+str(tools)+':$PATH"); }\n'
                'run_capped() { shift; "$@"; }\nfree_port() { :; }\n')
            prompt=root/'prompt.txt';prompt.write_text('synthetic local quality')
            settings=root/'settings.json';settings.write_text('{}')
            cases=root/'cases.json';shutil.copy2(LAB/'fixtures/behavior_cases.json',cases)
            values=dict(provider='local',model='synthetic',effort='test',timeout_seconds=10,max_calls=1,
                        max_actual_usd=None,max_equivalent_usd=100,limit_mode='monitored',accept_last_response_overrun=True)
            policy=resolve_policy({k:{'value':v,'source':'synthetic fixture'} for k,v in values.items()})
            artifacts=dict(driver=[harness/'quality.sh',harness/'lib.sh'],prompt=[prompt],settings=[settings],
                           scorer=[lab/'quality.py',lab/'attempt.py',lab/'behavior.py'],cases=[cases],
                           source=[work/'candidate.py',work/'package.json',work/'package-lock.json'])
            binding=freeze(root/'attempt.json','local-1',policy,artifacts)
            request=root/'binding.json';request.write_text(json.dumps(binding))
            old=root/'quality/run';old.mkdir(parents=True);(old/'auto-v2.json').write_text('historical-v2')
            command=['bash',str(harness/'quality.sh'),'run','3301','full',str(request)]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            q=root/'quality/run-local-1'
            scored=json.loads((q/'auto-v3.json').read_text())
            self.assertEqual(scored['provenance_status'],'bound')
            self.assertEqual(scored['attempt_id'],'local-1')
            self.assertEqual(scored['total_a'],11.5)
            self.assertEqual((old/'auto-v2.json').read_text(),'historical-v2')
            raw=(q/'auto-v3.json').read_bytes()
            again=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(again.returncode,0)
            self.assertEqual((q/'auto-v3.json').read_bytes(),raw)
            for role in ('driver', 'scorer', 'source'):
                wrong=dict(artifacts, **{role:[prompt]})
                wrong_binding=freeze(root/(role+'-attempt.json'),'wrong-'+role,policy,wrong)
                wrong_request=root/(role+'-binding.json');wrong_request.write_text(json.dumps(wrong_binding))
                rejected=subprocess.run(command[:-1]+[str(wrong_request)],capture_output=True,text=True)
                self.assertNotEqual(rejected.returncode,0,rejected.stderr)
                self.assertFalse((root/('quality/run-wrong-'+role)).exists())
                self.assertIn('absent from frozen attempt',rejected.stderr)
            settings.write_text('changed frozen settings')
            bad=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0)
            self.assertIn('attempt evaluation inputs changed',bad.stderr)


class QualityLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='zz-probe-quality-lifecycle-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lab = self.root / 'lab'
        self.harness = self.lab / 'harness'
        self.harness.mkdir(parents=True)
        for name in ('attempt.py', 'quality.py', 'behavior.py'):
            shutil.copy2(LAB / name, self.lab / name)
        shutil.copy2(LAB / 'harness/quality.sh', self.harness / 'quality.sh')
        self.work = self.root / 'runs/run/work'
        self.work.mkdir(parents=True)
        self.candidate = self.work / 'candidate.py'
        self.candidate.write_text('print("starting")\n')
        self.obsolete = self.work / 'obsolete.py'
        self.obsolete.write_text('obsolete = True\n')
        for args in (('init', '-q'), ('config', 'user.email', 'fixture@example.invalid'),
                     ('config', 'user.name', 'Fixture'), ('add', '.'), ('commit', '-qm', 'starting fixture')):
            self.git(*args)
        self.sentinel = self.root / 'legacy-sourced'
        self.lib = self.harness / 'lib.sh'
        self.lib.write_text('touch ' + str(self.sentinel) + '\nROOT=' + str(self.root) +
                            '\nRUNS="$ROOT/runs"\nHARNESS=' + str(self.harness) +
                            '\nREAL_HOME="$ROOT/home"\nagent_env() { AENV=("PATH=$PATH"); }\n'
                            'run_capped() { shift; "$@"; }\nfree_port() { :; }\n')
        self.prompt = self.root / 'prompt.txt'; self.prompt.write_text('synthetic local fixture')
        self.settings = self.root / 'settings.json'; self.settings.write_text('{}')
        self.cases = self.root / 'cases.json'
        self.cases.write_text(json.dumps({'schema_version': 1, 'cases': [
            {'case_id': f + '-1', 'feature': f, 'input': [], 'expected': []}
            for f in ('csv', 'budget')]}))
        values = dict(provider='local', model='synthetic', effort='test', timeout_seconds=10,
                      max_calls=1, max_actual_usd=None, max_equivalent_usd=100,
                      limit_mode='monitored', accept_last_response_overrun=True)
        self.policy = resolve_policy({k: {'value': v, 'source': 'synthetic local fixture'}
                                      for k, v in values.items()})
        self.roles = dict(driver=[self.harness / 'quality.sh', self.lib], prompt=[self.prompt],
                          settings=[self.settings], scorer=[self.lab / n for n in ('quality.py', 'attempt.py', 'behavior.py')],
                          cases=[self.cases], source=[self.candidate, self.obsolete])
        self.sidecar = self.root / 'attempt.json'
        self.binding = freeze(self.sidecar, 'same-attempt', self.policy, self.roles)
        self.original_sidecar = self.sidecar.read_bytes()
        self.request = self.root / 'binding.json'; self.request.write_text(json.dumps(self.binding))
        self.command = ['bash', str(self.harness / 'quality.sh'), 'run', '3301', 'full', str(self.request)]
        self.q = self.root / 'quality/run-same-attempt'

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.work), *args], stderr=subprocess.STDOUT, text=True).strip()

    def implement(self):
        self.calls = []
        def callback():
            self.calls.append('entered')
            self.candidate.write_text('from new_module import result\nprint(result)\n')
            (self.work / 'new_module.py').write_text('result = "implemented"\n')
            self.obsolete.unlink()
            self.git('add', '-A')
            self.git('commit', '-qm', 'implemented fixture')
            return self.git('rev-parse', 'HEAD')
        return guarded_launch(self.binding, callback)

    def run_quality(self):
        return subprocess.run(self.command, capture_output=True, text=True)

    def test_original_attempt_survives_guarded_commit_with_added_and_deleted_sources(self):
        # No package.json: actual shell clones and seals, with no npm or browser dispatch.
        implemented_commit = self.implement()
        old = self.root / 'quality/run/auto-v2.json'
        old.parent.mkdir(parents=True); old.write_bytes(b'historical bytes')
        result = self.run_quality()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls, ['entered'])
        self.assertEqual(self.sidecar.read_bytes(), self.original_sidecar)
        scored = strict_json((self.q / 'auto-v3.json').read_bytes())
        self.assertEqual(scored['provenance_status'], 'bound')
        self.assertEqual(scored['attempt_id'], self.binding['attempt_id'])
        prospective = strict_json((self.q / 'prospective.json').read_bytes())
        self.assertEqual(prospective['attempt'], self.binding)
        receipt = strict_json((self.q / 'evidence-receipt.json').read_bytes())
        self.assertEqual(receipt['attempt_sha256'], self.binding['sha256'])
        app = self.q / 'app'
        self.assertEqual(set(receipt['source']), {str((app / 'candidate.py').resolve()), str((app / 'new_module.py').resolve())})
        self.assertEqual(subprocess.check_output(['git', '-C', str(app), 'rev-parse', 'HEAD'], text=True).strip(), implemented_commit)
        self.assertEqual((app / 'new_module.py').read_bytes(), (self.work / 'new_module.py').read_bytes())
        self.assertFalse((app / 'obsolete.py').exists())
        verify_evidence(prospective['receipt'], self.binding, prospective['artifacts'], list(receipt['source']))
        self.assertEqual(old.read_bytes(), b'historical bytes')
        raw = (self.q / 'auto-v3.json').read_bytes()
        repeated = self.run_quality()
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual((self.q / 'auto-v3.json').read_bytes(), raw)

    def test_every_non_source_role_refuses_before_sourcing_legacy_adapter(self):
        self.implement()
        for role in ('driver', 'prompt', 'settings', 'scorer', 'cases'):
            path = self.lib if role == 'driver' else self.roles[role][0]
            raw = path.read_bytes()
            try:
                path.write_bytes(raw + b'\n# changed\n')
                with self.subTest(role=role):
                    result = self.run_quality()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(self.sentinel.exists())
                    self.assertFalse(self.q.exists())
            finally:
                path.write_bytes(raw)

    def test_external_source_workspace_is_refused_instead_of_omitted(self):
        unrelated = self.root / 'unrelated.py'; unrelated.write_text('unrelated = True\n')
        roles = dict(self.roles, source=[unrelated])
        binding = freeze(self.root / 'unrelated-attempt.json', 'unrelated', self.policy, roles)
        self.request.write_text(json.dumps(binding))
        result = self.run_quality()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'quality/run-unrelated').exists())


    def clone_fault(self, fault):
        tools = self.root / 'tools'; tools.mkdir()
        wrapper = tools / 'git'
        real_git = shutil.which('git')
        if fault == 'bytes':
            mutation = 'printf "# changed after clone\\n" >> "$4/candidate.py"'
        elif fault in ('extra', 'ignored'):
            mutation = 'printf "unexpected = True\\n" > "$4/uncommitted.py"'
            if fault == 'ignored':
                mutation += '\nprintf "uncommitted.py\\n" >> "$4/.git/info/exclude"'
        else:
            mutation = '"' + real_git + '" -C "$4" checkout -q HEAD^'
        wrapper.write_text('#!/bin/sh\nif [ "$1" = clone ]; then\n"' + real_git +
                          '" "$@" || exit $?\n' + mutation +
                          '\nelse\nexec "' + real_git + '" "$@"\nfi\n')
        wrapper.chmod(0o755)
        roles = dict(self.roles, driver=self.roles['driver'] + [wrapper])
        self.binding = freeze(self.root / 'fault-attempt.json', 'same-attempt', self.policy, roles)
        self.request.write_text(json.dumps(self.binding))
        self.implement()
        env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'])
        return subprocess.run(self.command, env=env, capture_output=True, text=True)

    def test_clone_bytes_must_match_selected_committed_source(self):
        result = self.clone_fault('bytes')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('evaluation clone source differs from selected committed source', result.stderr)
        self.assertFalse((self.q / 'auto-v3.json').exists())

    def test_clone_head_must_match_selected_implementation_commit(self):
        result = self.clone_fault('head')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('evaluation clone differs from selected implementation commit', result.stderr)
        self.assertFalse((self.q / 'auto-v3.json').exists())

    def test_extra_clone_file_is_rejected_before_probes(self):
        result = self.clone_fault('extra')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('evaluation clone file inventory differs from selected committed source', result.stderr)
        self.assertFalse((self.q / 'evaluation-source.json').exists())

    def test_git_ignored_extra_clone_file_is_also_rejected(self):
        result = self.clone_fault('ignored')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('evaluation clone file inventory differs from selected committed source', result.stderr)
        self.assertFalse((self.q / 'auto-v3.json').exists())


if __name__ == '__main__': unittest.main()
