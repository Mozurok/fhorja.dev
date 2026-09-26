#!/usr/bin/env python3
"""Per-run process lifetime and serialized feed writes (ADR-0196). No slice loop."""

import argparse
from contextlib import contextmanager
import datetime
try:
    import fcntl
except ImportError:
    fcntl = None
import json
import math
import os
from pathlib import Path
import re
import select
import signal
import subprocess
import sys
import tempfile
import time
import uuid


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
STARTUP_SECONDS = 30
POLL_SECONDS = .02


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec='milliseconds').replace('+00:00', 'Z')


def safe_id(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', value):
        raise ValueError('unsafe run_id (letters, digits, dot, dash and underscore only)')
    return value


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as f:
            name = f.name
            json.dump(data, f)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def read_json(path):
    with path.open() as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError(f'expected an object: {path}')
    return value


def paths(root, run_id):
    safe_id(run_id)
    return (root / '.wos' / 'runs' / (run_id + '.json'),
            root / '.wos' / 'background-runs' / (run_id + '.json'))


def main_root():
    def git_main(path):
        result = subprocess.run(['git', '-C', str(path), 'worktree', 'list', '--porcelain'],
                                capture_output=True, text=True, timeout=5)
        if result.returncode:
            if (path / '.git').exists():
                raise ValueError('cannot establish main-repository ownership; inspect git metadata')
            return None  # A standalone runtime can use an explicit main-root hint.
        first = result.stdout.splitlines()[0] if result.stdout else ''
        if not first.startswith('worktree ') or not Path(first[9:]).is_absolute():
            raise ValueError('cannot resolve main repository from git worktree metadata')
        return Path(first[9:]).resolve()

    detected = git_main(ROOT)
    hint = os.environ.get('WOS_MAIN_REPO')
    if hint:
        path = Path(hint)
        if not path.is_absolute() or not path.is_dir():
            raise ValueError('WOS_MAIN_REPO must name an existing absolute repository directory')
        selected = git_main(path) or path.resolve()
        if detected and selected != detected:
            raise ValueError('WOS_MAIN_REPO disagrees with this checkout; inspect repository ownership')
        return selected
    return detected or ROOT


@contextmanager
def feed_lock(root, run_id):
    if fcntl is None:
        raise RuntimeError('feed locking unavailable; use an attended foreground session')
    _, record = paths(root, run_id)
    record.parent.mkdir(parents=True, exist_ok=True)
    with record.with_suffix('.lock').open('a') as f:
        deadline = time.monotonic() + .5
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('feed lock busy; retry after inspecting its writer')
                time.sleep(POLL_SECONDS)
        yield


def publish(root, run_id, record):
    """Called under the per-run lock; persist final authority before its projection."""
    feed, meta = paths(root, run_id)
    atomic_json(meta, record)
    if record['closed'] and not record['escalated']:
        feed.unlink(missing_ok=True)
        return
    data = read_json(feed) if feed.exists() else {}
    data.update(schema_version=1, run_id=run_id, task=record['task'],
                started_ts=record['started_ts'], last_update_ts=now(),
                state='escalated' if record['escalated'] else record['state'],
                current_step=record['reason'] if record['escalated'] else record['step'])
    atomic_json(feed, data)


def feed_command(args):
    root = main_root()
    if not args:
        raise ValueError('usage: runs-feed.sh {start|update|end|check} ...')
    action = args[0]
    if action == 'check':
        fresh = False
        minutes = float(os.environ.get('STALE_MINUTES', '15'))
        for path in sorted((root / '.wos' / 'runs').glob('*.json')):
            try:
                stamp = read_json(path)['last_update_ts']
                dt = datetime.datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%S.%fZ')
                age = (datetime.datetime.now(datetime.timezone.utc) -
                       dt.replace(tzinfo=datetime.timezone.utc)).total_seconds() / 60
                if age <= minutes:
                    print(f'check: fresh run {path.stem!r}')
                    fresh = True
                else:
                    print(f'check: warning: stale run {path.stem!r}', file=sys.stderr)
            except (OSError, ValueError, KeyError, TypeError):
                print(f'check: warning: invalid feed {path.name}', file=sys.stderr)
        if not fresh:
            print('check: no fresh run')
        return int(fresh)
    if action not in ('start', 'update', 'end') or len(args) < 2:
        raise ValueError('usage: runs-feed.sh {start|update|end|check} ...')
    run_id = safe_id(args[1])
    feed, meta = paths(root, run_id)
    if action == 'start' and len(args) != 4:
        raise ValueError('start requires run_id, task and current_step')
    if action == 'end' and len(args) != 2:
        raise ValueError('end requires run_id')
    state = step = None
    if action == 'update':
        if (len(args) - 2) % 2:
            raise ValueError('update options require values')
        for key, value in zip(args[2::2], args[3::2]):
            if key == '--state':
                state = value
            elif key == '--step':
                step = value
            else:
                raise ValueError(f'unknown update arg {key}')
    with feed_lock(root, run_id):
        if meta.exists():
            record = read_json(meta)
            # Managed start/end never grant the agent lifecycle ownership. Terminal
            # metadata also prevents a late start from resurrecting a completed run.
            if not record['closed'] and not record['escalated'] and action == 'update':
                if state:
                    record['state'] = state
                if step:
                    record['step'] = step
                if state == 'escalated':
                    record['escalated'] = True
                    record['reason'] = step or 'agent escalation (cause unspecified)'
            publish(root, run_id, record)
        elif action == 'start':
            stamp = now()
            atomic_json(feed, dict(schema_version=1, run_id=run_id, task=args[2],
                                   state='starting', started_ts=stamp,
                                   last_update_ts=stamp, current_step=args[3]))
        elif action == 'end':
            feed.unlink(missing_ok=True)
        elif feed.exists():
            data = read_json(feed)
            data['last_update_ts'] = now()
            if state:
                data['state'] = state
            if step:
                data['current_step'] = step
            atomic_json(feed, data)
        else:
            print(f'runs-feed: unknown run_id {run_id!r}', file=sys.stderr)
            return 1
    print(f'{action}: {run_id}')
    return 0


def exited(child):
    # WNOWAIT keeps the group leader's PID reserved until all group signalling
    # finishes. Popen.poll()/wait() here would reap it and permit PID reuse.
    return os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)


def finish_child(child, grace):
    def waitable_after_denied_signal():
        # A dying child can reject a signal just before its exit becomes waitable.
        # Allow that transition, but never interpret EPERM alone as proof of death.
        deadline = time.monotonic() + .2
        while exited(child) is None:
            if time.monotonic() >= deadline:
                return False
            time.sleep(POLL_SECONDS)
        return True

    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass  # Some systems remove an empty group before its leader is reaped.
    except PermissionError:
        if not waitable_after_denied_signal():
            raise
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        time.sleep(min(POLL_SECONDS, max(0, deadline - time.monotonic())))
    forced = exited(child) is None
    # Signal before reaping even if the leader exited: descendants can still run.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        # An all-zombie group can reject signals. A waitable leader is necessary
        # but not sufficient: confirm group absence below before releasing ownership.
        if not waitable_after_denied_signal():
            raise
    code = child.wait(timeout=2)
    deadline = time.monotonic() + 1
    while True:
        try:
            os.killpg(child.pid, 0)  # Observation only after reap; never signal again.
        except ProcessLookupError:
            return code, forced, True
        except PermissionError:
            # Dying groups can briefly deny observation before disappearing. Keep
            # observing within the same bound; denial alone never proves cleanup.
            pass
        if time.monotonic() >= deadline:
            return code, forced, False
        time.sleep(POLL_SECONDS)


def workspace(root, task, provisioning_started):
    sot = task / 'SOURCE_OF_TRUTH.md'
    if sot.exists():
        section = re.search(r'^## Workspace[^\n]*\n(.*?)(?=^## |\Z)',
                            sot.read_text(), re.M | re.S)
        if section:
            match = re.search(r'^.*worktree path\s*:\s*(.+)$', section[1], re.M | re.I)
            if match:
                path = Path(match[1].replace('`', '').strip())
                if not path.is_absolute():
                    raise ValueError('recorded Worktree path must be absolute')
                if not path.is_dir():
                    raise ValueError('recorded Worktree path is not a directory')
                return path
    path = root / '.wos' / 'bg-worktrees' / task.name
    branch = 'task/' + task.name
    def git(*args, check=True):
        return subprocess.run(['git', '-C', str(root), *args], check=check,
                              capture_output=True, text=True, timeout=10)
    if f'worktree {path}\n' in git('worktree', 'list', '--porcelain').stdout:
        return path
    provisioning_started(path, branch)
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = git('show-ref', '--verify', '--quiet', 'refs/heads/' + branch, check=False)
    args = ['worktree', 'add', str(path)]
    git(*(args + [branch] if exists.returncode == 0 else args + ['-b', branch]))
    return path


class Halt(Exception):
    pass


def supervise(config, handshake):
    root = Path(config['root'])
    task = Path(config['task'])
    run_id = config['run_id']
    stop = root / '.wos' / ('STOP-' + task.name)
    owner_path = root / '.wos' / 'background-run.owner'
    owner = owner_path.open('a+')
    acquired = False
    child = None
    record = None
    reason = None
    cleaned = True
    announced = False
    interruption = None

    def persist_owner(data):
        owner.seek(0)
        owner.truncate()
        json.dump(data, owner)
        owner.flush()
        os.fsync(owner.fileno())

    def provisioning_started(path, branch):
        nonlocal cleaned
        # From this point a directory, branch or worktree may exist even if the
        # provisioning command raises. Keep admission closed with recovery facts.
        cleaned = False
        persist_owner(dict(run_id=run_id, supervisor_pid=os.getpid(),
                           phase='workspace-provisioning', worktree=str(path),
                           branch=branch))

    def interrupted(sig, frame):
        # Do not unwind Popen between child creation and assignment. The main path
        # consumes this request only after ownership registration is complete.
        nonlocal interruption
        interruption = f'supervisor interrupted by signal {sig}'

    def check_interruption():
        if interruption:
            raise Halt(interruption)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        try:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Halt('owner active; only one background run is allowed')
        owner.seek(0)
        if owner.read().strip():
            raise Halt(f'owner unresolved; inspect {owner_path} and its log before retrying')
        for feed in (root / '.wos' / 'runs').glob('*.json'):
            _, meta = paths(root, feed.stem)
            if not meta.exists() or read_json(meta).get('closed') is not True:
                raise Halt(f'legacy or unresolved owner for {feed.name}; inspect it before retrying')
        if stop.exists():
            raise Halt(f'STOP already present: {stop}')
        acquired = True
        persist_owner(dict(run_id=run_id, supervisor_pid=os.getpid(), phase='admitted'))
        check_interruption()
        worktree = workspace(root, task, provisioning_started)
        # A returned worktree proves provisioning completed. Until a child is
        # created, there is no unresolved process resource owned by this run.
        cleaned = True
        check_interruption()
        if stop.exists():
            raise Halt(f'STOP present before agent spawn: {stop}')
        record = dict(run_id=run_id, task=task.name, started_ts=now(), state='starting',
                      step='launching', escalated=False, reason='', closed=False,
                      supervisor_pid=os.getpid(), child_pid=None, forced=False)
        with feed_lock(root, run_id):
            publish(root, run_id, record)
        prompt = (f'Run autonomous-run for task {task.name}. STOP file: {stop}. '
                  f'Run id: {run_id}. Main repository: {root}. '
                  f'Supervised timeout: {config["timeout"]} seconds; '
                  f'termination grace: {config["grace"]} seconds.')
        env = dict(os.environ, WOS_STOP_PATH=str(stop), WOS_RUN_ID=run_id,
                   WOS_TASK_DIR=task.name, WOS_MAIN_REPO=str(root))
        child = subprocess.Popen(config['argv'] + [prompt], cwd=worktree, env=env,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
        cleaned = False
        record['child_pid'] = child.pid
        started = time.monotonic()
        with feed_lock(root, run_id):
            record = read_json(paths(root, run_id)[1])
            record['child_pid'] = child.pid
            publish(root, run_id, record)
        check_interruption()
        os.write(handshake, (f'launched: run_id={run_id} pid={child.pid} '
                            f'supervisor_pid={os.getpid()} worktree={worktree} '
                            f'log={config["log"]}\n').encode())
        os.close(handshake)
        announced = True
        while True:
            check_interruption()
            if stop.exists():
                reason = 'STOP requested; interrupted slice remains incomplete'
                break
            if time.monotonic() - started >= config['timeout']:
                reason = 'wall-clock timeout; cause unknown; interrupted slice remains incomplete'
                break
            record = read_json(paths(root, run_id)[1])
            if record['escalated']:
                reason = record['reason']
                break
            status = exited(child)
            if status is not None:
                if status.si_code != os.CLD_EXITED or status.si_status != 0:
                    reason = f'agent exited with status {status.si_status} (code {status.si_code})'
                break
            time.sleep(POLL_SECONDS)
    except (Exception, KeyboardInterrupt) as exc:
        reason = str(exc) or type(exc).__name__
        print(f'REFUSED: {reason}', file=sys.stderr, flush=True)
        if not announced:
            try:
                os.write(handshake, f'REFUSED: {reason}\n'.encode())
            except OSError:
                pass
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if not announced:
            try:
                os.close(handshake)
            except OSError:
                pass
        try:
            forced = False
            if child is not None:
                try:
                    _, forced, cleaned = finish_child(child, config['grace'])
                except (OSError, subprocess.SubprocessError) as exc:
                    cleaned = False
                    reason = f'process-group cleanup unresolved: {exc}; human inspection required'
                if not cleaned:
                    reason = reason or 'process-group cleanup unresolved; human inspection required'
            if record is not None:
                with feed_lock(root, run_id):
                    record = read_json(paths(root, run_id)[1])
                    record['closed'] = cleaned
                    record['forced'] = forced
                    if reason and not record['escalated']:
                        record['escalated'] = True
                        record['reason'] = reason
                    publish(root, run_id, record)
            if acquired and cleaned:
                owner.seek(0)
                owner.truncate()
                owner.flush()
                os.fsync(owner.fileno())
        except Exception as exc:
            # The owner record remains. Never infer safe reentry from failed cleanup.
            print(f'escalated: finalization unresolved: {exc}; inspect {owner_path}',
                  file=sys.stderr, flush=True)
        finally:
            owner.close()
    if reason and announced:
        notify = None
        try:
            notify = subprocess.Popen(['bash', str(HERE / 'notify.sh'), reason],
                                      stdin=subprocess.DEVNULL, start_new_session=True)
            deadline = time.monotonic() + 1
            while exited(notify) is None and time.monotonic() < deadline:
                time.sleep(POLL_SECONDS)
            finish_child(notify, 0)
        except (OSError, subprocess.SubprocessError):
            pass
    return 0 if announced else 1


def positive(value):
    try:
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            raise ValueError
        return number
    except ValueError:
        raise argparse.ArgumentTypeError('must be a finite positive number')


def control_probe():
    """Exercise control of a disposable owned group before any agent/workspace start."""
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        _, _, cleaned = finish_child(child, 0)
        if not cleaned:
            raise RuntimeError('probe process-group cleanup unresolved')
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        raise RuntimeError(f'process control unavailable: {exc}; '
                           'use an attended foreground session') from exc


def launch(args):
    parser = argparse.ArgumentParser(prog='launch-background-run.sh')
    parser.add_argument('task', type=Path)
    parser.add_argument('--timeout-sec', type=positive)
    parser.add_argument('--grace-sec', type=positive)
    parsed = parser.parse_args(args)
    if not parsed.task.is_dir():
        parser.error('task folder does not exist')
    command = os.environ.get('WOS_AGENT_CMD', '').strip()
    if not command:
        print('No WOS_AGENT_CMD configured: configure the pre-approved agent invocation, then run\n'
              '  scripts/autonomy/launch-background-run.sh <task-folder> '
              '--timeout-sec <seconds> --grace-sec <seconds>\n'
              'Both bounds must be positive. This same supervised entry point is the manual\n'
              'fallback. If process ownership/control is unavailable, use an attended foreground\n'
              'session. Inspect any unresolved owner and preserve its workspace before retrying.')
        return 0
    if parsed.timeout_sec is None or parsed.grace_sec is None:
        parser.error('--timeout-sec and --grace-sec are required for detachment')
    # Preserve whitespace-split configuration; never evaluate a shell command string.
    argv = command.split()
    if any(word in command.lower() for word in
           ('acceptedits', 'bypasspermissions', 'skip-permissions', 'yolo')):
        parser.error('configured invocation violates the autonomous permission skip list')
    if fcntl is None or os.name != 'posix' or not all(hasattr(os, key) for key in
                                   ('waitid', 'WNOWAIT', 'killpg', 'CLD_EXITED')):
        parser.error('process lifetime control unavailable; use an attended foreground session')
    control_probe()
    root = main_root()
    runs = root / '.wos' / 'runs'
    runs.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^A-Za-z0-9._-]', '-', parsed.task.resolve().name)
    run_id = f'bg-{slug}-{uuid.uuid4().hex[:12]}'
    log = runs / (run_id + '.log')
    config = dict(root=str(root), task=str(parsed.task.resolve()), run_id=run_id,
                  timeout=parsed.timeout_sec, grace=parsed.grace_sec, argv=argv, log=str(log))
    reader, writer = os.pipe()
    try:
        with log.open('a') as out:
            supervisor = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                                           'run', json.dumps(config), str(writer)],
                                          stdin=subprocess.DEVNULL, stdout=out, stderr=out,
                                          pass_fds=(writer,), start_new_session=True)
        os.close(writer)
        writer = None
        if not select.select([reader], [], [], STARTUP_SECONDS)[0]:
            print(f'REFUSED: startup unresolved; inspect {log} and background-run.owner',
                  file=sys.stderr)
            return 1
        message = os.read(reader, 65536).decode().strip()
        if message.startswith('launched:'):
            print(message)
            return 0
        print(message or f'REFUSED: supervisor failed before startup; inspect {log}',
              file=sys.stderr)
        supervisor.wait(timeout=3)
        return 1
    finally:
        os.close(reader)
        if writer is not None:
            os.close(writer)


def main():
    try:
        if len(sys.argv) < 2:
            raise ValueError('expected launch, run or feed')
        if sys.argv[1] == 'feed':
            return feed_command(sys.argv[2:])
        if sys.argv[1] == 'launch':
            return launch(sys.argv[2:])
        if sys.argv[1] == 'run':
            return supervise(json.loads(sys.argv[2]), int(sys.argv[3]))
        raise ValueError('unknown operation')
    except (ValueError, OSError, RuntimeError) as exc:
        print(f'autonomy: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
