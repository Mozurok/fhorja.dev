#!/usr/bin/env python3
"""Exercise the real background entry point with owned, disposable processes."""

import concurrent.futures
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest


SOURCE = Path(__file__).resolve().parents[1]
MOCK = r'''
import json, os, pathlib, signal, subprocess, sys, time
ready = pathlib.Path(os.environ['MOCK_READY'])
mode = os.environ.get('MOCK_MODE', 'block')
if mode == 'ignore':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
child = None
if mode == 'ignore':
    child = subprocess.Popen([sys.executable, '-c',
        'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])
pathlib.Path('partial.txt').write_text('keep this incomplete work')
ready.write_text(json.dumps({'pid': os.getpid(), 'child': child.pid if child else None,
    'run_id': os.environ['WOS_RUN_ID'], 'args': sys.argv[1:]}))
if mode == 'success': sys.exit(0)
if mode == 'failure': sys.exit(7)
while not pathlib.Path(str(ready) + '.exit').exists(): time.sleep(.02)
'''


def until(predicate, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(.02)
    return predicate()


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fhorja-background-')
        self.root = Path(self.temp.name)
        self.runtime = self.root / 'scripts' / 'autonomy'
        shutil.copytree(SOURCE, self.runtime, ignore=shutil.ignore_patterns('__pycache__'))
        (self.runtime / 'notify.sh').write_text('#!/usr/bin/env bash\nexit 0\n')
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.task = self.root / '2026-09-07_fixture'
        self.make_task(self.task)
        self.mock = self.root / 'mock.py'
        self.mock.write_text(MOCK)
        self.ready = self.root / 'ready.json'
        self.env = dict(os.environ, WOS_AGENT_CMD=f'{sys.executable} {self.mock}',
                        MOCK_READY=str(self.ready), MOCK_MODE='block')
        self.env.pop('WOS_RUN_ID', None)
        self.env.pop('WOS_MAIN_REPO', None)
        self.control = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])

    def make_task(self, task):
        task.mkdir()
        (task / 'SOURCE_OF_TRUTH.md').write_text(
            f'## Workspace\nWorktree path: `{self.workspace}`\n')

    def tearDown(self):
        # Only PIDs emitted by fixtures launched in this test's private directory.
        for ready in self.root.glob('ready*.json'):
            try:
                pid = json.loads(ready.read_text())['pid']
                if os.getpgid(pid) == pid:
                    os.killpg(pid, signal.SIGKILL)
                else:  # The old unsupervised launcher, used for the red reproduction.
                    os.kill(pid, signal.SIGKILL)
            except (OSError, ValueError, KeyError):
                pass
        for record in (self.root / '.wos' / 'background-runs').glob('*.json'):
            try:
                data = json.loads(record.read_text())
                if not data.get('closed'):
                    pid = data.get('child_pid')
                    if pid:
                        try:
                            if os.getpgid(pid) == pid:
                                os.killpg(pid, signal.SIGKILL)
                        except OSError:
                            pass
                    os.kill(data['supervisor_pid'], signal.SIGTERM)
            except (OSError, ValueError, KeyError):
                pass
        self.control.terminate()
        self.control.wait(timeout=3)
        until(lambda: all(json.loads(p.read_text()).get('closed') for p in
              (self.root / '.wos' / 'background-runs').glob('*.json')), seconds=1.5)
        self.temp.cleanup()

    def launch(self, mode='block', timeout='0.7', grace='0.2', env=None, task=None):
        selected = dict(self.env if env is None else env, MOCK_MODE=mode)
        return subprocess.run(['bash', str(self.runtime / 'launch-background-run.sh'),
                               str(task or self.task), '--timeout-sec', timeout,
                               '--grace-sec', grace], env=selected, cwd=self.root,
                              text=True, capture_output=True, timeout=8)

    def start(self, **kwargs):
        result = self.launch(**kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(until(self.ready.exists), result.stdout + result.stderr)
        self.info = json.loads(self.ready.read_text())
        self.run_id = self.info['run_id']
        return result

    def record(self):
        path = self.root / '.wos' / 'background-runs' / (self.run_id + '.json')
        return json.loads(path.read_text()) if path.exists() else {}

    def feed(self, *args):
        return subprocess.run(['bash', str(self.runtime / 'runs-feed.sh'), *args],
                              env=self.env, cwd=self.root, text=True,
                              capture_output=True, timeout=4)

    def feed_data(self):
        path = self.root / '.wos' / 'runs' / (self.run_id + '.json')
        return json.loads(path.read_text()) if path.exists() else {}

    def wait_closed(self):
        def finalized():
            if not self.record().get('closed'):
                return False
            # closed records process cleanup before the feed projection and owner
            # release. Observe the whole transaction before checking its effects.
            with (self.root / '.wos' / 'background-run.owner').open() as owner:
                try:
                    fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return False
                return not owner.read().strip()
        self.assertTrue(until(finalized),
                        (self.record(), [p.read_text() for p in
                         (self.root / '.wos' / 'runs').glob('*.log')]))
        with self.assertRaises(ProcessLookupError, msg='closed run still has a live agent'):
            os.kill(self.info['pid'], 0)
        if self.info.get('child'):
            with self.assertRaises(ProcessLookupError, msg='owned descendant survived cleanup'):
                os.kill(self.info['child'], 0)
        self.assertIsNone(self.control.poll(), 'unrelated control process was signalled')

    def test_c1_blocked_deadline_preserves_partial_work(self):
        self.start()
        self.wait_closed()
        self.assertEqual(self.feed_data()['state'], 'escalated')
        self.assertIn('timeout', self.feed_data()['current_step'])
        self.assertNotIn('permission', self.feed_data()['current_step'])
        self.assertEqual((self.workspace / 'partial.txt').read_text(), 'keep this incomplete work')
        self.assertTrue((self.root / '.wos' / 'runs' / (self.run_id + '.log')).exists())

    def test_c2_stop_during_block_and_before_launch(self):
        self.start(timeout='10')
        stop = self.root / '.wos' / ('STOP-' + self.task.name)
        stop.touch()
        self.wait_closed()
        self.assertIn('STOP', self.feed_data()['current_step'])
        self.assertTrue(stop.exists())
        self.assertNotEqual(self.launch().returncode, 0)

    def test_c3_ignored_term_and_descendant(self):
        started = time.monotonic()
        self.start(mode='ignore')
        self.wait_closed()
        self.assertLess(time.monotonic() - started, 4)
        self.assertTrue(self.record()['forced'])
        self.assertEqual(self.feed_data()['state'], 'escalated')

    def test_c3_transient_group_observation_denial(self):
        # A dying group can briefly deny signal-0 observation before disappearing.
        # Keep real TERM/KILL behavior and inject only that first observation.
        module = self.runtime / 'supervise-background-run.py'
        hook = '''
real_killpg = os.killpg
denied_groups = set()
def transient_killpg(pid, sig):
    if sig == 0 and pid not in denied_groups:
        denied_groups.add(pid)
        raise PermissionError('transient group observation denial')
    return real_killpg(pid, sig)
os.killpg = transient_killpg

'''
        source = module.read_text()
        module.write_text(source.replace('def main():', hook + 'def main():'))
        self.start(mode='ignore')
        self.wait_closed()
        self.assertTrue(self.record()['forced'])

    def test_c4_concurrent_launch_and_stale_heartbeat(self):
        task2 = self.root / '2026-09-07_other'
        self.make_task(task2)
        env2 = dict(self.env, MOCK_READY=str(self.root / 'ready2.json'))
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            a = pool.submit(self.launch, timeout='4')
            b = pool.submit(self.launch, timeout='4', task=task2, env=env2)
            results = [a.result(), b.result()]
        self.assertEqual(sorted(r.returncode for r in results), [0, 1],
                         [r.stdout + r.stderr for r in results])
        self.assertTrue(until(lambda: self.ready.exists() or (self.root / 'ready2.json').exists()))
        ready = self.ready if self.ready.exists() else self.root / 'ready2.json'
        self.run_id = json.loads(ready.read_text())['run_id']
        path = self.root / '.wos' / 'runs' / (self.run_id + '.json')
        data = json.loads(path.read_text())
        data['last_update_ts'] = '2000-01-01T00:00:00.000Z'
        path.write_text(json.dumps(data))
        self.assertNotEqual(self.launch().returncode, 0)

    def test_c5_supervisor_death_keeps_admission_closed(self):
        self.start(timeout='10')
        record = self.record()
        self.assertIn('supervisor_pid', record, 'no independent lifecycle owner was recorded')
        os.kill(record['supervisor_pid'], signal.SIGKILL)
        time.sleep(.1)
        result = self.launch()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('owner', result.stdout + result.stderr)

    def test_c4_linked_worktree_shares_main_owner_and_stop(self):
        def git(*args):
            return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                                  capture_output=True, text=True, timeout=5)
        git('init')
        git('add', 'scripts')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '-m', 'Fixture runtime')
        linked = self.root / 'linked'
        git('worktree', 'add', '-b', 'linked', str(linked))
        # Start in a linked worktree with no environment hint. It must discover main.
        self.runtime = linked / 'scripts' / 'autonomy'
        self.start(timeout='5')
        self.assertTrue(self.record().get('child_pid'))
        self.runtime = self.root / 'scripts' / 'autonomy'
        result = self.launch(env=dict(self.env, WOS_MAIN_REPO=str(linked)))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        (self.root / '.wos' / ('STOP-' + self.task.name)).touch()
        self.wait_closed()
        self.assertIn('STOP', self.feed_data()['current_step'])

    def test_c5_signal_during_spawn_never_releases_live_child(self):
        module = self.runtime / 'supervise-background-run.py'
        source = module.read_text()
        hook = '''
def interrupted_spawn(*args, **kwargs):
    spawned = subprocess.Popen(*args, **kwargs)
    Path(os.environ['MOCK_SPAWN_PID']).write_text(str(spawned.pid))
    os.kill(os.getpid(), signal.SIGTERM)
    return spawned

'''
        source = source.replace('def supervise(config, handshake):', hook + 'def supervise(config, handshake):')
        source = source.replace("child = subprocess.Popen(config['argv']", "child = interrupted_spawn(config['argv']")
        module.write_text(source)
        pid_path = self.root / 'spawned-pid'
        result = self.launch(env=dict(self.env, MOCK_SPAWN_PID=str(pid_path)))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue(pid_path.exists())
        pid = int(pid_path.read_text())
        try:
            def child_gone():
                try:
                    os.kill(pid, 0)
                    return False
                except ProcessLookupError:
                    return True
            self.assertTrue(until(child_gone), 'startup signal left a live owned child')
            self.assertFalse((self.root / '.wos' / 'background-run.owner').read_text().strip())
        finally:
            try:
                os.killpg(pid, signal.SIGKILL)
            except OSError:
                pass

    def test_c6_escalation_survives_late_writes_and_exit_zero(self):
        self.start(timeout='5')
        self.assertEqual(self.feed('update', self.run_id, '--state', 'escalated',
                                   '--step', 'operator escalation').returncode, 0)
        Path(str(self.ready) + '.exit').touch()
        with concurrent.futures.ThreadPoolExecutor(3) as pool:
            results = list(pool.map(lambda args: self.feed(*args), [
                ('start', self.run_id, 'wrong-task', 'late start'),
                ('update', self.run_id, '--state', 'executing', '--step', 'late update'),
                ('end', self.run_id)]))
        self.assertTrue(all(r.returncode == 0 for r in results))
        self.assertEqual(self.feed_data().get('state'), 'escalated')
        self.wait_closed()
        self.assertEqual(self.feed_data()['state'], 'escalated')
        self.assertIn('operator escalation', self.feed_data()['current_step'])
        self.feed('end', self.run_id)
        self.assertEqual(self.feed_data()['state'], 'escalated')

    def test_r1_success_failure_and_exec_error(self):
        # Stretch the metadata/feed publication window so early observation fails
        # deterministically instead of intermittently under CI load.
        module = self.runtime / 'supervise-background-run.py'
        source = module.read_text()
        marker = '    atomic_json(meta, record)\n'
        self.assertIn(marker, source)
        module.write_text(source.replace(marker, marker +
                          "    if record['closed']:\n        time.sleep(.2)\n"))
        self.start(mode='success')
        self.wait_closed()
        self.assertEqual(self.feed_data(), {})
        self.ready.unlink()
        self.start(mode='failure')
        self.wait_closed()
        self.assertIn('7', self.feed_data()['current_step'])
        result = self.launch(env=dict(self.env, WOS_AGENT_CMD='/no/such/agent'))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('launched:', result.stdout)

    def test_r2_invalid_bounds_and_manual_path(self):
        for value in ['0', '-1', 'nan', 'inf', 'garbage']:
            result = self.launch(timeout=value)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertEqual(self.launch(grace=value).returncode, 2)
        self.assertFalse(self.ready.exists())
        env = dict(self.env)
        env.pop('WOS_AGENT_CMD')
        result = self.launch(env=env)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--timeout-sec', result.stdout)
        self.assertNotIn('nohup', result.stdout)

    def test_r2_missing_bounds_and_unsafe_mode(self):
        result = subprocess.run(['bash', str(self.runtime / 'launch-background-run.sh'),
                                 str(self.task)], env=self.env, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        result = self.launch(env=dict(self.env, WOS_AGENT_CMD=self.env['WOS_AGENT_CMD'] +
                                      ' --dangerously-skip-permissions'))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.ready.exists())

    def test_r3_standalone_feed_and_additive_fields(self):
        self.assertEqual(self.feed('start', 'standalone', 'task', 'step').returncode, 0)
        path = self.root / '.wos' / 'runs' / 'standalone.json'
        data = json.loads(path.read_text())
        self.assertEqual(len(data), 7)
        data['extra'] = 'preserved'
        path.write_text(json.dumps(data))
        self.assertEqual(self.feed('update', 'standalone', '--step', 'next').returncode, 0)
        self.assertEqual(json.loads(path.read_text())['extra'], 'preserved')
        self.assertEqual(self.feed('check').returncode, 1)
        self.assertEqual(self.feed('end', 'standalone').returncode, 0)
        self.assertEqual(self.feed('check').returncode, 0)

    def test_e1_legacy_and_malformed_owner_refuse(self):
        self.feed('start', 'legacy', 'task', 'step')
        path = self.root / '.wos' / 'runs' / 'legacy.json'
        data = json.loads(path.read_text())
        data['last_update_ts'] = '2000-01-01T00:00:00.000Z'
        path.write_text(json.dumps(data))
        self.assertEqual(self.launch().returncode, 1)
        self.assertFalse(self.ready.exists())
        self.feed('end', 'legacy')
        (self.root / '.wos' / 'background-run.owner').write_text('malformed owner')
        self.assertEqual(self.launch().returncode, 1)

    def test_r1_workspace_failure_releases_proven_empty_owner(self):
        sot = self.task / 'SOURCE_OF_TRUTH.md'
        sot.write_text('## Workspace\nWorktree path: /no/such/workspace\n')
        result = self.launch()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('launched:', result.stdout)
        self.assertFalse(self.ready.exists())
        sot.write_text(f'## Workspace\nWorktree path: `{self.workspace}`\n')
        self.start(mode='success')
        self.wait_closed()

    def test_c5_mutating_worktree_failure_retains_actionable_owner(self):
        def git(*args):
            return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                                  capture_output=True, text=True, timeout=5)
        (self.task / 'SOURCE_OF_TRUTH.md').write_text('## Workspace\n')
        git('init')
        git('add', 'scripts')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '-m', 'Fixture runtime')
        module = self.runtime / 'supervise-background-run.py'
        marker = "    git(*(args + [branch] if exists.returncode == 0 else args + ['-b', branch]))\n"
        self.assertIn(marker, module.read_text())
        module.write_text(module.read_text().replace(
            marker,
            "    path.mkdir()\n"
            "    raise subprocess.CalledProcessError(1, ['git', 'worktree', 'add'])\n"))

        result = self.launch()
        intended = self.root / '.wos' / 'bg-worktrees' / self.task.name
        owner_path = self.root / '.wos' / 'background-run.owner'
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue(intended.is_dir(), 'fault injection did not mutate the worktree path')
        owner = json.loads(owner_path.read_text())
        self.assertEqual(owner['phase'], 'workspace-provisioning')
        self.assertEqual(Path(owner['worktree']).resolve(), intended.resolve())
        self.assertEqual(owner['branch'], 'task/' + self.task.name)
        retry = self.launch()
        self.assertEqual(retry.returncode, 1, retry.stdout + retry.stderr)
        self.assertIn('owner unresolved', retry.stdout + retry.stderr)

    def test_e1_deadline_precedes_a_clean_exit_observed_at_the_boundary(self):
        module = self.runtime / 'supervise-background-run.py'
        marker = '        started = time.monotonic()\n'
        self.assertIn(marker, module.read_text())
        module.write_text(module.read_text().replace(
            marker,
            marker +
            "        if os.environ.get('MOCK_EXIT_AT_DEADLINE'):\n"
            "            while exited(child) is None:\n"
            "                time.sleep(POLL_SECONDS)\n"
            "            started = time.monotonic() - config['timeout']\n"))
        self.start(mode='success', timeout='0.1',
                   env=dict(self.env, MOCK_EXIT_AT_DEADLINE='1'))
        self.wait_closed()
        self.assertEqual(self.feed_data()['state'], 'escalated')
        self.assertIn('timeout', self.feed_data()['current_step'])

    def test_e1_stop_racing_startup_refuses_before_agent_spawn(self):
        module = self.runtime / 'supervise-background-run.py'
        marker = '        worktree = workspace(root, task, provisioning_started)\n'
        self.assertIn(marker, module.read_text())
        module.write_text(module.read_text().replace(
            marker,
            marker + "        Path(os.environ['MOCK_STARTUP_STOP']).touch()\n"))
        stop = self.root / '.wos' / ('STOP-' + self.task.name)
        result = self.launch(env=dict(self.env, MOCK_STARTUP_STOP=str(stop)))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('STOP present before agent spawn', result.stdout + result.stderr)
        self.assertFalse(self.ready.exists())
        self.assertTrue(stop.exists())
        self.assertFalse((self.root / '.wos' / 'background-run.owner').read_text().strip())

    def test_e1_missing_notifier_does_not_delay_supervisor_exit(self):
        (self.runtime / 'notify.sh').unlink()
        self.start()
        supervisor_pid = self.record()['supervisor_pid']
        self.wait_closed()

        def supervisor_gone():
            try:
                os.kill(supervisor_pid, 0)
                return False
            except ProcessLookupError:
                return True

        self.assertTrue(until(supervisor_gone), 'missing notifier kept supervisor alive')
        self.assertIn('timeout', self.feed_data()['current_step'])

    def test_e1_launch_is_independent_of_caller_working_directory(self):
        caller = self.root / 'unrelated-caller'
        caller.mkdir()
        result = subprocess.run(
            ['bash', str(self.runtime / 'launch-background-run.sh'), str(self.task),
             '--timeout-sec', '0.7', '--grace-sec', '0.2'],
            env=self.env, cwd=caller, text=True, capture_output=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(until(self.ready.exists), result.stdout + result.stderr)
        self.info = json.loads(self.ready.read_text())
        self.run_id = self.info['run_id']
        self.wait_closed()
        self.assertEqual((self.workspace / 'partial.txt').read_text(),
                         'keep this incomplete work')

    def test_c6_feed_failure_terminates_and_preserves_owner(self):
        self.start(timeout='5')
        path = self.root / '.wos' / 'runs' / (self.run_id + '.json')
        path.unlink()
        path.mkdir()  # Deterministic write failure, including when tests run as root.
        (self.root / '.wos' / ('STOP-' + self.task.name)).touch()
        self.assertTrue(until(lambda: self.record().get('escalated')))
        self.assertEqual(self.record()['closed'], True)
        with self.assertRaises(ProcessLookupError):
            os.kill(self.info['pid'], 0)
        self.assertTrue((self.root / '.wos' / 'background-run.owner').read_text().strip())
        self.assertEqual(self.launch().returncode, 1)

    def test_c6_hanging_notifier_does_not_delay_cleanup(self):
        (self.runtime / 'notify.sh').write_text('#!/usr/bin/env bash\nsleep 30\n')
        started = time.monotonic()
        self.start()
        self.wait_closed()
        self.assertLess(time.monotonic() - started, 3)
        self.assertFalse((self.root / '.wos' / 'background-run.owner').read_text().strip())
        time.sleep(1.2)  # Let the bounded notifier reap its own process group.

    def test_r2_capability_refusal_before_agent(self):
        module = self.runtime / 'supervise-background-run.py'
        module.write_text(module.read_text().replace('if fcntl is None or os.name',
                                                     'if True or os.name'))
        result = self.launch()
        self.assertEqual(result.returncode, 2)
        self.assertIn('attended foreground', result.stderr)
        self.assertFalse(self.ready.exists())

    def test_r3_main_root_feed_and_board_reader(self):
        self.task = self.root / 'task with spaces and ação'
        self.make_task(self.task)
        self.env['WOS_AGENT_CMD'] += ' --fixture-flag literal-value'
        self.start(timeout='3')
        self.assertEqual(self.info['args'][:2], ['--fixture-flag', 'literal-value'])
        other = self.root / 'other-tree' / 'scripts' / 'autonomy'
        shutil.copytree(self.runtime, other)
        result = subprocess.run(['bash', str(other / 'runs-feed.sh'), 'update', self.run_id,
                                 '--step', 'from worktree'],
                                env=dict(self.env, WOS_MAIN_REPO=str(self.root)),
                                capture_output=True, timeout=4)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.feed_data()['current_step'], 'from worktree')
        spec = importlib.util.spec_from_file_location('board', SOURCE.parent / 'build-portfolio-board.py')
        board = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(board)
        board.RUNS_DIR = self.root / '.wos' / 'runs'
        runs, warnings = board.load_runs()
        self.assertFalse(warnings)
        self.assertEqual(runs[0]['run_id'], self.run_id)
        (self.root / '.wos' / ('STOP-' + self.task.name)).touch()
        self.wait_closed()


if __name__ == '__main__':
    unittest.main(verbosity=2)
