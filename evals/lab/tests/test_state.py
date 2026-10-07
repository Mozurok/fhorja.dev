import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from attempt import canonical, digest, snapshot, strict_json
from state import apply_event, capture_check, initialize, project, recover_event, section_sha, writer

REPO = Path(__file__).resolve().parents[3]


class StateProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name in ('README.md', 'DECISIONS.md', 'IMPLEMENTATION_PLAN.md'):
            (self.root / name).write_text('# Authority\nkeep model semantics\n')
        self.source = self.root / 'candidate.py'
        self.source.write_text('print("candidate")\n')
        self.event = {
            'schema_version': 1, 'event_id': 'event-1', 'task_id': 'task-a',
            'task_root': str(self.root.resolve()), 'owner': 'sync-task-state',
            'run_id': '01Jstate_test', 'ts': '2026-10-03T05:30:00.000Z',
            'target': 'TASK_STATE.md', 'expected_section_sha': 'a' * 64,
            'authority_snapshot': self.authority(),
            'candidate_snapshot': snapshot([self.source]),
            'kind': 'step_recorded',
            'payload': {'command': 'implement-approved-slice', 'mode': 'Agent',
                        'required_checks': ['test'], 'check_refs': []},
        }

    def authority(self):
        return snapshot([self.root / n for n in
                         ('README.md', 'DECISIONS.md', 'IMPLEMENTATION_PLAN.md')])

    def record(self, rc=0):
        return capture_check(self.root, 'task-a', 'test',
                             [sys.executable, '-c', f'raise SystemExit({rc})'],
                             [self.source], timeout=2)

    def bind(self, record, check_id='test'):
        path = self.root / (check_id + '.json')
        raw = (canonical(record) + '\n').encode()
        path.write_bytes(raw)
        self.event['payload']['check_refs'] = [
            {'check_id': check_id, 'path': str(path), 'sha256': digest(raw)}]

    def test_actual_success_and_nonzero_are_distinct_facts(self):
        for rc, expected in [(0, 'passed'), (7, 'failed')]:
            with self.subTest(rc=rc):
                record = self.record(rc)
                self.assertIs(type(record['exit_code']), int)
                self.assertEqual(record['exit_code'], rc)
                self.bind(record)
                result = project(self.root, self.event)
                self.assertEqual(result['verification'], expected)
                self.assertEqual(result['section'], '## Last completed step')
                self.assertIn('Command: implement-approved-slice', result['body'])

    def test_empty_missing_and_unexecuted_never_pass(self):
        self.assertEqual(project(self.root, self.event)['verification'], 'unknown')
        self.event['payload']['required_checks'] = []
        self.assertEqual(project(self.root, self.event)['verification'], 'unknown')
        self.event['payload']['required_checks'] = ['test']
        record = self.record()
        record.update(executed=False, finished=False, exit_code=None)
        self.bind(record)
        self.assertEqual(project(self.root, self.event)['verification'], 'not_run')
        self.event['payload']['required_checks'].append('missing')
        self.assertEqual(project(self.root, self.event)['verification'], 'unknown')

    def test_malformed_or_contradictory_records_never_pass(self):
        original = self.record()
        mutations = [dict(exit_code=False), dict(exit_code=0.0), dict(exit_code=None),
                     dict(executed=False), dict(finished=False), dict(task_id='other'),
                     dict(check_id='invented'), dict(before={}), dict(after={}),
                     dict(producer='model-assertion')]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                record = copy.deepcopy(original)
                record.update(mutation)
                self.bind(record)
                self.assertEqual(project(self.root, self.event)['verification'], 'unknown')
        record = copy.deepcopy(original)
        del record['executed']
        self.bind(record)
        self.assertEqual(project(self.root, self.event)['verification'], 'unknown')

    def test_digest_mismatch_and_duplicate_json_are_unknown(self):
        self.bind(self.record())
        path = Path(self.event['payload']['check_refs'][0]['path'])
        path.write_text('{"exit_code":0,"exit_code":7}\n')
        self.assertEqual(project(self.root, self.event)['verification'], 'unknown')
        self.event['payload']['check_refs'][0]['sha256'] = digest(path.read_bytes())
        self.assertEqual(project(self.root, self.event)['verification'], 'unknown')

    def test_stale_authority_and_candidate_refuse_projection(self):
        self.bind(self.record())
        for path in (self.root / 'DECISIONS.md', self.source):
            with self.subTest(path=path.name):
                before = path.read_bytes()
                path.write_bytes(before + b'changed\n')
                with self.assertRaises(ValueError):
                    project(self.root, self.event)
                path.write_bytes(before)

    def test_changed_snapshot_inside_check_cannot_pass(self):
        command = [sys.executable, '-c',
                   'from pathlib import Path; Path("candidate.py").write_text("changed")']
        record = capture_check(self.root, 'task-a', 'test', command, [self.source], 2)
        self.event['candidate_snapshot'] = snapshot([self.source])
        self.bind(record)
        self.assertEqual(project(self.root, self.event)['verification'], 'unknown')

    def test_timeout_and_missing_executable_are_not_success(self):
        for argv, expected in [([sys.executable, '-c', 'import time; time.sleep(2)'], 'unknown'),
                               ([str(self.root / 'missing')], 'not_run')]:
            with self.subTest(expected=expected):
                self.bind(capture_check(self.root, 'task-a', 'test', argv,
                                        [self.source], .05))
                self.assertEqual(project(self.root, self.event)['verification'], expected)

    def test_unknown_fields_and_type_confusion_refuse(self):
        for extra in ('body', 'summary', 'verification', 'closed'):
            event = copy.deepcopy(self.event)
            event['payload'][extra] = 'passed'
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                project(self.root, event)
        for key, value in [('schema_version', True), ('task_root', str(self.root / 'other')),
                           ('kind', 'close_task'), ('kind', []),
                           ('authority_snapshot', None), ('candidate_snapshot', []),
                           ('ts', '2026-99-03T05:30:00.000Z'), ('target', '../TASK_STATE.md')]:
            event = copy.deepcopy(self.event)
            event[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                project(self.root, event)

    def test_failed_outcome_outranks_missing_without_hiding_it(self):
        self.bind(self.record(7))
        self.event['payload']['required_checks'].append('missing')
        self.assertEqual(project(self.root, self.event)['verification'], 'failed')
        self.bind(self.record())
        self.assertEqual(project(self.root, self.event)['verification'], 'unknown')

    def test_duplicate_and_undeclared_check_references_refuse(self):
        self.bind(self.record())
        for field in ('required_checks', 'check_refs'):
            event = copy.deepcopy(self.event)
            event['payload'][field] *= 2
            with self.subTest(field=field), self.assertRaises(ValueError):
                project(self.root, event)
        event = copy.deepcopy(self.event)
        event['payload']['check_refs'][0]['check_id'] = 'not-declared'
        with self.assertRaises(ValueError):
            project(self.root, event)

    def test_check_source_iterable_is_bound_before_and_after(self):
        record = capture_check(self.root, 'task-a', 'test',
                               [sys.executable, '-c', 'pass'], iter([self.source]), 2)
        self.assertEqual(record['before'], record['after'])
        self.bind(record)
        self.assertEqual(project(self.root, self.event)['verification'], 'passed')

    def test_phase_and_activity_choices_remain_model_owned(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        event = copy.deepcopy(self.event)
        event.update(kind='phase_selected', payload={'phase': 'implementation'})
        self.assertEqual(project(self.root, event)['body'], 'implementation\n')
        event.update(kind='status_reported', payload={'items': [
            {'id': 'activity-a', 'label': 'Implementation ~~done~~ [done]',
             'action_status': 'completed', 'required_checks': ['missing'], 'check_refs': []}]})
        result = project(self.root, event)
        self.assertIn('### Completed', result['body'])
        self.assertIn(r'\~\~done\~\~', result['body'])
        self.assertIn('verification: unknown', result['body'])
        self.assertNotIn('verification: passed', result['body'])
        self.assertEqual(result, project(self.root, event))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})


class StatePublicationTests(unittest.TestCase):
    def setUp(self):
        fixture = StateProjectionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root, self.event = fixture.root, fixture.event
        self.state = self.root / 'TASK_STATE.md'
        self.state.write_bytes(b'# TASK_STATE\n\n## Current phase\nplanning\n\n'
                               b'## Last completed step\nunknown\n\n'
                               b'## Current status\nunknown\n\n'
                               b'## Unknowns\nkeep model-owned bytes\n')
        self.log = self.root / '.wos/VERIFICATION_LOG.jsonl'
        raw = subprocess.check_output(['bash', str(REPO / 'scripts/emit-substrate-write.sh'),
                                       'sha', '--file', str(self.state),
                                       '--section', '## Current phase'], text=True).strip()
        self.event.update(kind='phase_selected', payload={'phase': 'implementation'},
                          expected_section_sha=raw)

    def init(self):
        return initialize(self.root, 'task-a', genesis=True)

    def validator(self):
        r = subprocess.run(['python3', str(REPO / 'scripts/verify-log-validator.py'),
                            str(self.log), '--check-deletes', '--cutover-ts',
                            '2026-07-18T00:00:00.000Z'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def interrupt(self, phase):
        event_file = self.root / 'event.json'
        event_file.write_text(canonical(self.event))
        script = ('import sys,json,os,signal; from pathlib import Path; '
                  f'sys.path.insert(0,{str(REPO / "evals/lab")!r}); '
                  'from state import apply_event; '
                  'stop=lambda phase: os.kill(os.getpid(),signal.SIGTERM) '
                  'if phase==sys.argv[3] else None; '
                  'apply_event(sys.argv[1],json.loads(Path(sys.argv[2]).read_text()),stop)')
        r = subprocess.run([sys.executable, '-c', script, str(self.root),
                            str(event_file), phase], capture_output=True, text=True, timeout=5)
        self.assertEqual(r.returncode, -15, r.stdout + r.stderr)

    def test_apply_exact_replay_and_conflicting_event_identity(self):
        self.init()
        before = self.state.read_bytes()
        result = apply_event(self.root, self.event)
        self.assertEqual(result['outcome'], 'applied')
        self.assertIn(b'implementation', self.state.read_bytes())
        self.assertNotEqual(before, self.state.read_bytes())
        after = (self.state.read_bytes(), self.log.read_bytes())
        self.assertEqual(apply_event(self.root, self.event)['outcome'], 'already_applied')
        self.assertEqual(after, (self.state.read_bytes(), self.log.read_bytes()))
        self.assertEqual(len(self.log.read_text().splitlines()), 1)
        conflict = copy.deepcopy(self.event)
        conflict['payload']['phase'] = 'review'
        with self.assertRaises(ValueError):
            apply_event(self.root, conflict)
        self.assertEqual(after, (self.state.read_bytes(), self.log.read_bytes()))
        self.validator()

    def test_no_change_has_no_owning_header_or_log_churn(self):
        self.init()
        self.event['payload']['phase'] = 'planning'
        before = (self.state.read_bytes(), self.log.read_bytes())
        self.assertEqual(apply_event(self.root, self.event)['outcome'], 'unchanged')
        self.assertEqual(before, (self.state.read_bytes(), self.log.read_bytes()))
        self.assertEqual(apply_event(self.root, self.event)['outcome'], 'unchanged')

    def test_completed_historical_replay_never_restores_old_state(self):
        self.init()
        apply_event(self.root, self.event)
        old = copy.deepcopy(self.event)
        self.event['event_id'] = 'event-2'
        self.event['payload']['phase'] = 'review'
        self.event['expected_section_sha'] = digest(b'implementation')
        apply_event(self.root, self.event)
        before = (self.state.read_bytes(), self.log.read_bytes())
        self.assertEqual(apply_event(self.root, old)['outcome'], 'already_applied')
        self.assertEqual(before, (self.state.read_bytes(), self.log.read_bytes()))
        self.assertEqual(len(self.log.read_text().splitlines()), 2)
        self.validator()

    def test_real_interruption_at_each_publication_boundary_recovers_once(self):
        for phase in ('prepared', 'target', 'log'):
            with self.subTest(phase=phase):
                fixture = StatePublicationTests()
                fixture.setUp()
                try:
                    fixture.init()
                    fixture.interrupt(phase)
                    result = recover_event(fixture.root, fixture.event['event_id'])
                    self.assertIn(result['outcome'], ('applied', 'already_applied'))
                    fixture.validator()
                    row = strict_json(fixture.log.read_bytes())
                    self.assertEqual(row['ts'], fixture.event['ts'])
                    self.assertEqual(row['run_id'], fixture.event['run_id'])
                    self.assertEqual(row['sha_before'], fixture.event['expected_section_sha'])
                    before = (fixture.state.read_bytes(), fixture.log.read_bytes())
                    recover_event(fixture.root, fixture.event['event_id'])
                    self.assertEqual(before, (fixture.state.read_bytes(), fixture.log.read_bytes()))
                finally:
                    fixture.doCleanups()

    def test_wrong_task_refuses_before_either_canonical_file_changes(self):
        self.init()
        before = (self.state.read_bytes(), self.log.read_bytes())
        for key, value in [('task_id', 'task-b'), ('task_root', str(self.root.parent)),
                           ('target', '../TASK_STATE.md')]:
            event = copy.deepcopy(self.event)
            event[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                apply_event(self.root, event)
            self.assertEqual(before, (self.state.read_bytes(), self.log.read_bytes()))

    def test_dirty_target_refuses_and_preexisting_dirty_neighbors_survive(self):
        self.init()
        self.state.write_bytes(self.state.read_bytes().replace(b'planning', b'manual dirty'))
        before = (self.state.read_bytes(), self.log.read_bytes())
        with self.assertRaises(ValueError):
            apply_event(self.root, self.event)
        self.assertEqual(before, (self.state.read_bytes(), self.log.read_bytes()))
        self.state.write_bytes(self.state.read_bytes().replace(b'manual dirty', b'planning'))
        self.state.write_bytes(self.state.read_bytes().replace(b'keep model-owned bytes',
                                                              b'preexisting dirty unknowns\r'))
        patch = self.root / 'partial.patch'
        patch.write_bytes(b'preserve unfinished implementation\n')
        apply_event(self.root, self.event)
        self.assertIn(b'preexisting dirty unknowns\r', self.state.read_bytes())
        self.assertEqual(patch.read_bytes(), b'preserve unfinished implementation\n')
        self.validator()

    def test_changed_target_or_log_during_recovery_is_preserved(self):
        self.init()
        self.interrupt('prepared')
        self.state.write_bytes(self.state.read_bytes() + b'neighbor changed\n')
        before = (self.state.read_bytes(), self.log.read_bytes())
        with self.assertRaises(ValueError):
            recover_event(self.root, self.event['event_id'])
        self.assertEqual(before, (self.state.read_bytes(), self.log.read_bytes()))

    def test_superseded_authority_before_target_refuses_after_target_repairs_only_log(self):
        for phase in ('prepared', 'target'):
            with self.subTest(phase=phase):
                fixture = StatePublicationTests()
                fixture.setUp()
                try:
                    fixture.init()
                    fixture.interrupt(phase)
                    authority = fixture.root / 'DECISIONS.md'
                    authority.write_text(authority.read_text() + 'Supersedes old requirement\n')
                    before = fixture.state.read_bytes()
                    if phase == 'prepared':
                        with self.assertRaises(ValueError):
                            recover_event(fixture.root, fixture.event['event_id'])
                        self.assertEqual(fixture.log.read_bytes(), b'')
                    else:
                        result = recover_event(fixture.root, fixture.event['event_id'])
                        self.assertTrue(result['authority_stale'])
                        self.assertEqual(result['verification'], 'unknown')
                        fixture.validator()
                    self.assertEqual(before, fixture.state.read_bytes())
                    self.assertIn('Supersedes old requirement', authority.read_text())
                finally:
                    fixture.doCleanups()

    def test_nonregular_log_and_symlink_target_refuse_without_target_loss(self):
        self.log.mkdir(parents=True)
        before = self.state.read_bytes()
        with self.assertRaises(ValueError):
            self.init()
        self.assertEqual(before, self.state.read_bytes())
        self.log.rmdir()
        self.init()
        real = self.root / 'real-state.md'
        self.state.rename(real)
        self.state.symlink_to(real)
        with self.assertRaises(ValueError):
            apply_event(self.root, self.event)
        self.assertEqual(before, real.read_bytes())

    def test_moved_affiliation_and_missing_receipt_refuse_without_guessing(self):
        self.init()
        self.interrupt('prepared')
        moved = self.root / 'archive'
        # A root declaration mismatch represents the move; no sibling scan is allowed.
        event = copy.deepcopy(self.event)
        event['task_root'] = str(moved)
        with self.assertRaises(ValueError):
            apply_event(self.root, event)
        with self.assertRaises(ValueError):
            recover_event(self.root, 'missing-event')

    def test_existing_owning_headers_need_existing_log_not_genesis_guess(self):
        self.state.write_bytes(b'<!-- wos:write owner=sync-task-state -->\n' + self.state.read_bytes())
        with self.assertRaises(ValueError):
            self.init()

    def test_real_folder_move_and_archive_refuse_pending_recovery(self):
        self.init()
        self.interrupt('prepared')
        moved = self.root.parent / (self.root.name + '-moved')
        self.root.rename(moved)
        try:
            before = {str(p.relative_to(moved)): p.read_bytes()
                      for p in moved.rglob('*') if p.is_file()}
            with self.assertRaises(ValueError):
                recover_event(moved, self.event['event_id'])
            archive = moved / 'archive' / 'task'
            archive.parent.mkdir()
            archive.mkdir()
            # Copy the pending task into a real archive path, not a changed event field.
            import shutil
            for p in list(moved.iterdir()):
                if p.name != 'archive':
                    shutil.move(str(p), str(archive / p.name))
            with self.assertRaises(ValueError):
                recover_event(archive, self.event['event_id'])
            after = {str(p.relative_to(archive)): p.read_bytes()
                     for p in archive.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
        finally:
            import shutil
            shutil.rmtree(moved)

    def test_log_edits_reversed_publication_and_duplicate_records_refuse(self):
        for fault in ('append', 'reverse', 'duplicate', 'malformed'):
            with self.subTest(fault=fault):
                fixture = StatePublicationTests()
                fixture.setUp()
                try:
                    fixture.init()
                    fixture.interrupt('prepared')
                    path = fixture.root / '.wos/state-replay/events/event-1.prepared.json'
                    receipt = strict_json(path.read_bytes())
                    import base64
                    post_log = base64.b64decode(receipt['bytes']['log_after'])
                    if fault == 'append':
                        fixture.log.write_bytes(b'concurrent appended bytes\n')
                    elif fault == 'reverse':
                        fixture.log.write_bytes(post_log)
                    elif fault == 'duplicate':
                        fixture.state.write_bytes(base64.b64decode(receipt['bytes']['target_after']))
                        fixture.log.write_bytes(post_log + post_log)
                    else:
                        path.write_bytes(b'{"event":')
                    before = (fixture.state.read_bytes(), fixture.log.read_bytes(), path.read_bytes())
                    with self.assertRaises(ValueError):
                        recover_event(fixture.root, fixture.event['event_id'])
                    self.assertEqual(before, (fixture.state.read_bytes(), fixture.log.read_bytes(),
                                              path.read_bytes()))
                finally:
                    fixture.doCleanups()

    def test_preimages_are_rechecked_after_projection_before_target_replace(self):
        self.init()
        calls = 0
        dirty = None
        def mutate_on_resume(root, event):
            nonlocal calls, dirty
            result = project(root, event)
            calls += 1
            if calls == 2:
                dirty = self.state.read_bytes() + b'ordinary neighbor edit\n'
                self.state.write_bytes(dirty)
            return result
        with patch('state.project', side_effect=mutate_on_resume):
            with self.assertRaises(ValueError):
                apply_event(self.root, self.event)
        self.assertEqual(self.state.read_bytes(), dirty)
        self.assertEqual(self.log.read_bytes(), b'')

    def test_prepared_target_and_record_must_agree_with_captured_event(self):
        for fault in ('neighbor', 'section', 'record', 'record-type'):
            with self.subTest(fault=fault):
                fixture = StatePublicationTests()
                fixture.setUp()
                try:
                    fixture.init()
                    fixture.interrupt('prepared')
                    path = fixture.root / '.wos/state-replay/events/event-1.prepared.json'
                    receipt = strict_json(path.read_bytes())
                    import base64
                    if fault in ('neighbor', 'section'):
                        raw = base64.b64decode(receipt['bytes']['target_after'])
                        raw = raw.replace(b'keep model-owned bytes', b'rewritten neighbor') if fault == 'neighbor' else raw.replace(b'implementation', b'delivery')
                        receipt['bytes']['target_after'] = base64.b64encode(raw).decode()
                        receipt['hashes']['target_after'] = digest(raw)
                    elif fault == 'record':
                        row = strict_json(base64.b64decode(receipt['record']))
                        row['run_id'] = 'other-run'
                        raw = (canonical(row) + '\n').encode()
                        receipt['record'] = base64.b64encode(raw).decode()
                        receipt['bytes']['log_after'] = receipt['record']
                        receipt['hashes']['log_after'] = digest(raw)
                    else:
                        receipt['record'] = []
                    path.write_text(canonical(receipt) + '\n')
                    before = (fixture.state.read_bytes(), fixture.log.read_bytes(), path.read_bytes())
                    with self.assertRaises(ValueError):
                        recover_event(fixture.root, fixture.event['event_id'])
                    self.assertEqual(before, (fixture.state.read_bytes(), fixture.log.read_bytes(),
                                              path.read_bytes()))
                finally:
                    fixture.doCleanups()

    def test_shell_sha_parity_and_next_owning_header_preservation(self):
        next_header = b'<!-- wos:write owner=sync-task-state section=next -->\n'
        for body in (b'planning\n', b'planning\r\n', b'planning\n\n\n'):
            with self.subTest(body=body):
                fixture = StatePublicationTests()
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                fixture.init()
                raw = b'# TASK_STATE\n\n## Current phase\n' + body + next_header + b'## Unknowns\nneighbor\r\n'
                fixture.state.write_bytes(raw)
                shell = subprocess.check_output(['bash', str(REPO / 'scripts/emit-substrate-write.sh'),
                    'sha', '--file', str(fixture.state), '--section', '## Current phase'], text=True).strip()
                self.assertEqual(section_sha(fixture.state, '## Current phase'), shell)
                event = copy.deepcopy(fixture.event)
                event['expected_section_sha'] = shell
                apply_event(fixture.root, event)
                self.assertTrue(fixture.state.read_bytes().endswith(next_header + b'## Unknowns\nneighbor\r\n'))
                fixture.validator()
        self.state.write_bytes(b'## Current phase\r\nplanning\r\n')
        shell = subprocess.check_output(['bash', str(REPO / 'scripts/emit-substrate-write.sh'),
            'sha', '--file', str(self.state), '--section', '## Current phase'], text=True).strip()
        self.assertEqual(shell, 'null')
        self.assertIsNone(section_sha(self.state, '## Current phase'))

    def test_duplicate_h2_including_fenced_decoy_refuses_without_writes(self):
        self.init()
        self.state.write_bytes(self.state.read_bytes() + b'```text\n## Current phase\ndecoy\n```\n')
        before = (self.state.read_bytes(), self.log.read_bytes())
        with self.assertRaises(ValueError):
            apply_event(self.root, self.event)
        self.assertEqual(before, (self.state.read_bytes(), self.log.read_bytes()))

    def test_task_log_identity_and_parent_symlink_refusal(self):
        self.init()
        fixture = StatePublicationTests()
        fixture.setUp()
        try:
            fixture.init()
            before = (self.state.read_bytes(), self.log.read_bytes(),
                      fixture.state.read_bytes(), fixture.log.read_bytes())
            with self.assertRaises(ValueError):
                apply_event(fixture.root, self.event)
            self.assertEqual(before, (self.state.read_bytes(), self.log.read_bytes(),
                                      fixture.state.read_bytes(), fixture.log.read_bytes()))
            folder = self.root / '.wos/state-replay'
            real = self.root / 'real-replay'
            folder.rename(real)
            folder.symlink_to(real, target_is_directory=True)
            with self.assertRaises(ValueError):
                apply_event(self.root, self.event)
            self.assertEqual(before[:2], (self.state.read_bytes(), self.log.read_bytes()))
        finally:
            fixture.doCleanups()

    def test_missing_log_and_overlapping_writer_refuse(self):
        with self.assertRaises(ValueError):
            initialize(self.root, 'task-a')
        self.init()
        before = self.state.read_bytes()
        with writer(self.root):
            with self.assertRaises(ValueError):
                apply_event(self.root, self.event)
        self.assertEqual(before, self.state.read_bytes())
        self.log.unlink()
        with self.assertRaises(ValueError):
            self.init()
        with self.assertRaises(ValueError):
            apply_event(self.root, self.event)
        self.assertEqual(before, self.state.read_bytes())

    def test_production_project_reference_write_remains_task_affiliated(self):
        project_root = self.root / 'project'
        task = project_root / 'active/task'
        task.mkdir(parents=True)
        (task / 'TASK_STATE.md').write_text('# Task\n')
        references = project_root / 'REFERENCES.md'
        references.write_text('# References\n\n## Sources\nold\n')
        body = self.root / 'reference-body.txt'
        body.write_text('captured official source\n')
        r = subprocess.run(['bash', str(REPO / 'scripts/emit-substrate-write.sh'), 'apply',
            '--owner', 'capture-references', '--file', str(references), '--section', '## Sources',
            '--body-file', str(body), '--reason', 'project-reference-control', '--task-root', str(task)],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        log = task / '.wos/VERIFICATION_LOG.jsonl'
        row = strict_json(log.read_bytes())
        self.assertEqual(row['file'], 'REFERENCES.md')
        shell = subprocess.check_output(['bash', str(REPO / 'scripts/emit-substrate-write.sh'),
            'sha', '--file', str(references), '--section', '## Sources'], text=True).strip()
        self.assertEqual(row['sha_after'], shell)
        self.assertFalse((project_root / '.wos/VERIFICATION_LOG.jsonl').exists())
        self.assertIn('captured official source', references.read_text())
        r = subprocess.run(['python3', str(REPO / 'scripts/verify-log-validator.py'),
            str(log), '--check-deletes', '--cutover-ts', '2026-07-18T00:00:00.000Z'],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_new_event_cannot_bypass_pending_historical_publication(self):
        self.init()
        self.interrupt('target')
        event = copy.deepcopy(self.event)
        event.update(event_id='event-2', expected_section_sha=digest(b'implementation'),
                     payload={'phase': 'review'})
        before = (self.state.read_bytes(), self.log.read_bytes())
        with self.assertRaises(ValueError):
            apply_event(self.root, event)
        self.assertEqual(before, (self.state.read_bytes(), self.log.read_bytes()))
        recover_event(self.root, self.event['event_id'])
        apply_event(self.root, event)
        self.assertEqual(len(self.log.read_text().splitlines()), 2)
        self.validator()

    def test_truncated_registered_log_history_refuses_without_new_write(self):
        self.init()
        apply_event(self.root, self.event)
        self.log.write_bytes(b'')
        event = copy.deepcopy(self.event)
        event.update(event_id='event-2', expected_section_sha=digest(b'implementation'),
                     payload={'phase': 'review'})
        before = (self.state.read_bytes(), self.log.read_bytes())
        with self.assertRaises(ValueError):
            apply_event(self.root, event)
        self.assertEqual(before, (self.state.read_bytes(), self.log.read_bytes()))

    def test_symlink_ancestor_task_alias_refuses_before_publication(self):
        self.init()
        alias = self.root.parent / (self.root.name + '-alias')
        alias.symlink_to(self.root.parent, target_is_directory=True)
        try:
            before = (self.state.read_bytes(), self.log.read_bytes())
            with self.assertRaises(ValueError):
                apply_event(alias / self.root.name, self.event)
            self.assertEqual(before, (self.state.read_bytes(), self.log.read_bytes()))
        finally:
            alias.unlink()

    def test_registered_preexisting_history_cannot_be_truncated(self):
        r = subprocess.run(['bash', str(REPO / 'scripts/emit-substrate-write.sh'), 'emit',
            '--owner', 'sync-task-state', '--file', str(self.state), '--section', '## Current phase',
            '--event', 'write', '--mode', 'applied', '--reason', 'initial-history-control',
            '--sha-before', 'null', '--no-derive-sha-before', '--task-root', str(self.root)],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        initialize(self.root, 'task-a')
        self.log.write_bytes(b'')
        before = self.state.read_bytes()
        with self.assertRaises(ValueError):
            apply_event(self.root, self.event)
        self.assertEqual(before, self.state.read_bytes())
        self.assertEqual(self.log.read_bytes(), b'')

    def test_stale_verified_step_repairs_provenance_without_recertifying(self):
        self.init()
        source = self.root / 'candidate.py'
        record = capture_check(self.root, 'task-a', 'test',
                               [sys.executable, '-c', 'pass'], [source], 2)
        evidence = self.root / 'check.json'
        raw = (canonical(record) + '\n').encode()
        evidence.write_bytes(raw)
        self.event.update(kind='step_recorded', expected_section_sha=digest(b'unknown'),
            payload={'command': 'implement-approved-slice', 'mode': 'Agent',
                     'required_checks': ['test'], 'check_refs': [
                         {'check_id': 'test', 'path': str(evidence), 'sha256': digest(raw)}]})
        self.interrupt('target')
        before = self.state.read_bytes()
        self.assertIn(b'verification: passed', before)
        source.write_bytes(source.read_bytes() + b'# partial implementation changed\n')
        changed = source.read_bytes()
        result = recover_event(self.root, self.event['event_id'])
        self.assertTrue(result['candidate_stale'])
        self.assertEqual(result['verification'], 'unknown')
        self.assertEqual(before, self.state.read_bytes())
        self.assertEqual(changed, source.read_bytes())
        self.validator()

    def test_late_log_write_failure_retains_exact_recoverable_evidence(self):
        self.init()
        from state import publish
        def fail_log(path, raw):
            if path == self.log and raw:
                raise OSError('injected late log publication failure')
            return publish(path, raw)
        with patch('state.publish', side_effect=fail_log):
            with self.assertRaises(OSError):
                apply_event(self.root, self.event)
        self.assertIn(b'implementation', self.state.read_bytes())
        self.assertEqual(self.log.read_bytes(), b'')
        self.assertTrue((self.root / '.wos/state-replay/events/event-1.prepared.json').is_file())
        result = recover_event(self.root, self.event['event_id'])
        self.assertEqual(result['outcome'], 'applied')
        self.assertEqual(len(self.log.read_text().splitlines()), 1)
        self.validator()

    def test_renamed_completed_receipt_cannot_claim_another_event(self):
        import shutil
        for outcome in ('unchanged', 'applied'):
            with self.subTest(outcome=outcome):
                fixture = StatePublicationTests()
                fixture.setUp()
                try:
                    fixture.init()
                    if outcome == 'unchanged':
                        fixture.event['payload']['phase'] = 'planning'
                    apply_event(fixture.root, fixture.event)
                    folder = fixture.root / '.wos/state-replay/events'
                    shutil.copy2(folder / 'event-1.done.json', folder / 'event-2.done.json')
                    if outcome == 'applied':
                        shutil.copy2(folder / 'event-1.prepared.json', folder / 'event-2.prepared.json')
                    before = (fixture.state.read_bytes(), fixture.log.read_bytes())
                    with self.assertRaises(ValueError):
                        recover_event(fixture.root, 'event-2')
                    self.assertEqual(before, (fixture.state.read_bytes(), fixture.log.read_bytes()))
                finally:
                    fixture.doCleanups()

    def test_dangling_identity_symlink_is_not_replaced_by_initialization(self):
        folder = self.root / '.wos/state-replay'
        folder.mkdir(parents=True)
        identity_path = folder / 'identity.json'
        identity_path.symlink_to(self.root / 'missing-identity.json')
        before = self.state.read_bytes()
        with self.assertRaises(ValueError):
            self.init()
        self.assertTrue(identity_path.is_symlink())
        self.assertEqual(before, self.state.read_bytes())
        self.assertFalse(self.log.exists())

    def test_completed_replay_refuses_missing_history_and_symlink_target(self):
        for outcome in ('unchanged', 'applied'):
            for fault in ('missing-log', 'empty-log', 'symlink-target'):
                with self.subTest(outcome=outcome, fault=fault):
                    fixture = StatePublicationTests()
                    fixture.setUp()
                    try:
                        fixture.init()
                        apply_event(fixture.root, fixture.event)
                        if outcome == 'unchanged':
                            fixture.event.update(event_id='event-2',
                                                 expected_section_sha=digest(b'implementation'))
                            self.assertEqual(apply_event(fixture.root, fixture.event)['outcome'],
                                             'unchanged')
                        if fault == 'missing-log':
                            fixture.log.unlink()
                        elif fault == 'empty-log':
                            fixture.log.write_bytes(b'')
                        else:
                            real = fixture.root / 'real-state.md'
                            fixture.state.rename(real)
                            fixture.state.symlink_to(real)
                        before = (fixture.state.read_bytes(),
                                  fixture.log.read_bytes() if fixture.log.exists() else None,
                                  fixture.state.is_symlink())
                        for replay in (lambda: apply_event(fixture.root, fixture.event),
                                       lambda: recover_event(fixture.root, fixture.event['event_id'])):
                            with self.assertRaises(ValueError):
                                replay()
                            self.assertEqual(before, (fixture.state.read_bytes(),
                                fixture.log.read_bytes() if fixture.log.exists() else None,
                                fixture.state.is_symlink()))
                    finally:
                        fixture.doCleanups()


if __name__ == '__main__':
    unittest.main()
