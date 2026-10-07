"""Opt-in mechanical facts from trusted local check execution, not model flags."""
import math
import base64
import contextlib
import fcntl
import importlib.util
import os
import re
import subprocess
import tempfile
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from attempt import canonical, digest, same, snapshot, strict_json


AUTHORITY_FILES = ('README.md', 'DECISIONS.md', 'IMPLEMENTATION_PLAN.md')
PHASES = {'discovery', 'planning', 'contract refinement', 'contract signoff',
          'test design', 'implementation', 'review', 'debug', 'delivery'}
MODES = {'Ask', 'Plan', 'Agent', 'Debug'}
SECTIONS = {'phase_selected': '## Current phase',
            'step_recorded': '## Last completed step',
            'status_reported': '## Current status'}
ENVELOPE = {'schema_version', 'event_id', 'task_id', 'task_root', 'owner',
            'run_id', 'ts', 'target', 'expected_section_sha', 'authority_snapshot',
            'candidate_snapshot', 'kind', 'payload'}
RECORD_FIELDS = {'schema_version', 'producer', 'task_id', 'check_id',
                 'execution_id', 'argv', 'executed', 'finished', 'exit_code',
                 'before', 'after'}
REASONS = {'passed': 'all declared checks completed with exit 0',
           'failed': 'recorded nonzero exit',
           'unknown': 'no checks declared or evidence missing, invalid or stale',
           'not_run': 'declared check not executed'}


def fields(value, expected):
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError('exact structured fields required')


def token(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value):
        raise ValueError('invalid identity token')
    return value


def hash_value(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
        raise ValueError('invalid SHA256')


def current_snapshot(expected):
    if not isinstance(expected, dict):
        raise ValueError('snapshot object required')
    for path, value in expected.items():
        if not isinstance(path, str) or not Path(path).is_absolute():
            raise ValueError('absolute snapshot paths required')
        hash_value(value)
    if not same(snapshot(expected), expected):
        raise ValueError('stale snapshot')
    return expected


def command(value):
    token(value)
    root = Path(__file__).resolve().parents[2]
    if not (root / 'commands' / (value + '.md')).is_file() and not (
            root / 'commands' / value / 'SKILL.md').is_file():
        raise ValueError('unknown canonical command')


def capture_check(task_root, task_id, check_id, argv, candidate_files=(), timeout=5):
    """The caller keeps this record outside candidate/model-authored evidence."""
    root = Path(task_root).resolve(strict=True)
    candidate_files = tuple(candidate_files)
    token(task_id)
    token(check_id)
    if (not isinstance(argv, list) or not argv
            or any(not isinstance(a, str) or not a for a in argv)
            or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('explicit argv and finite positive timeout required')
    def capture():
        return {'authority': snapshot(root / n for n in AUTHORITY_FILES),
                'candidate': snapshot(candidate_files)}
    before = capture()
    executed, finished, exit_code = True, False, None
    try:
        result = subprocess.run(argv, cwd=root, timeout=timeout,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        finished, exit_code = True, result.returncode
    except subprocess.TimeoutExpired:
        pass
    except OSError:
        executed = False
    try:
        after = capture()
    except (OSError, ValueError):
        after = None
    return {'schema_version': 1, 'producer': 'local-state-check-harness',
            'task_id': task_id, 'check_id': check_id, 'execution_id': uuid.uuid4().hex,
            'argv': list(argv), 'executed': executed, 'finished': finished,
            'exit_code': exit_code, 'before': before, 'after': after}


def checks_shape(required, references):
    if not isinstance(required, list) or not isinstance(references, list):
        raise ValueError('check arrays required')
    for check in required:
        token(check)
    if len(set(required)) != len(required):
        raise ValueError('duplicate required check')
    seen = set()
    for ref in references:
        fields(ref, {'check_id', 'path', 'sha256'})
        token(ref['check_id'])
        hash_value(ref['sha256'])
        if (not isinstance(ref['path'], str) or not Path(ref['path']).is_absolute()
                or ref['check_id'] not in required or ref['check_id'] in seen):
            raise ValueError('invalid or duplicate check reference')
        seen.add(ref['check_id'])


def record_status(ref, event):
    try:
        path = Path(ref['path'])
        if path.is_symlink() or not path.is_file():
            return 'unknown'
        raw = path.read_bytes()
        if digest(raw) != ref['sha256']:
            return 'unknown'
        record = strict_json(raw)
        fields(record, RECORD_FIELDS)
        expected = {'authority': event['authority_snapshot'],
                    'candidate': event['candidate_snapshot']}
        token(record['execution_id'])
        if (type(record['schema_version']) is not int or record['schema_version'] != 1
                or record['producer'] != 'local-state-check-harness'
                or record['task_id'] != event['task_id'] or record['check_id'] != ref['check_id']
                or type(record['executed']) is not bool or type(record['finished']) is not bool
                or not isinstance(record['argv'], list) or not record['argv']
                or any(not isinstance(a, str) or not a for a in record['argv'])
                or not same(record['before'], expected) or not same(record['after'], expected)):
            return 'unknown'
        if not record['executed']:
            return 'not_run' if not record['finished'] and record['exit_code'] is None else 'unknown'
        if not record['finished'] or type(record['exit_code']) is not int:
            return 'unknown'
        return 'passed' if record['exit_code'] == 0 else 'failed'
    except (OSError, ValueError, TypeError, UnicodeError):
        return 'unknown'


def verification(required, references, event):
    checks_shape(required, references)
    refs = {ref['check_id']: ref for ref in references}
    statuses = [record_status(refs[c], event) if c in refs else 'unknown' for c in required]
    for status in ('failed', 'unknown', 'not_run'):
        if status in statuses:
            return status
    return 'passed' if statuses else 'unknown'


def literal_label(value):
    if (not isinstance(value, str) or not value.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('single-line literal label required')
    return re.sub(r'([\\`*_{}\[\]()<>#!|~])', r'\\\1', value)


def project(task_root, event):
    """Only execution facts are derived; semantic choices stay in the event."""
    fields(event, ENVELOPE)
    canonical(event)
    root = Path(task_root).resolve(strict=True)
    for key in ('event_id', 'task_id', 'owner', 'run_id'):
        token(event[key])
    command(event['owner'])
    if (type(event['schema_version']) is not int or event['schema_version'] != 1
            or event['task_root'] != str(root) or event['target'] != 'TASK_STATE.md'
            or not isinstance(event['kind'], str) or event['kind'] not in SECTIONS
            or not isinstance(event['ts'], str)
            or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z', event['ts'])):
        raise ValueError('invalid task-affiliated event')
    try:
        datetime.fromisoformat(event['ts'].replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('invalid captured timestamp') from error
    if event['expected_section_sha'] is not None:
        hash_value(event['expected_section_sha'])
    if (not isinstance(event['authority_snapshot'], dict)
            or set(event['authority_snapshot']) != {str(root / n) for n in AUTHORITY_FILES}):
        raise ValueError('complete task authority required')
    current_snapshot(event['authority_snapshot'])
    current_snapshot(event['candidate_snapshot'])
    payload, kind = event['payload'], event['kind']
    if kind == 'phase_selected':
        fields(payload, {'phase'})
        if not isinstance(payload['phase'], str) or payload['phase'] not in PHASES:
            raise ValueError('invalid model-selected phase')
        return {'section': SECTIONS[kind], 'body': payload['phase'] + '\n', 'verification': 'unknown'}
    if kind == 'step_recorded':
        fields(payload, {'command', 'mode', 'required_checks', 'check_refs'})
        command(payload['command'])
        if not isinstance(payload['mode'], str) or payload['mode'] not in MODES:
            raise ValueError('invalid model-selected mode')
        status = verification(payload['required_checks'], payload['check_refs'], event)
        body = (f"- Command: {payload['command']}\n- Mode: {payload['mode']}\n"
                f"- Summary: Recorded {payload['command']}; verification: {status} ({REASONS[status]})\n")
        return {'section': SECTIONS[kind], 'body': body, 'verification': status}
    fields(payload, {'items'})
    if not isinstance(payload['items'], list):
        raise ValueError('ordered status items required')
    groups = {'completed': [], 'in_progress': [], 'pending': []}
    seen, statuses = set(), []
    for item in payload['items']:
        fields(item, {'id', 'label', 'action_status', 'required_checks', 'check_refs'})
        token(item['id'])
        label = literal_label(item['label'])
        if (item['id'] in seen or not isinstance(item['action_status'], str)
                or item['action_status'] not in groups):
            raise ValueError('duplicate or invalid status item')
        seen.add(item['id'])
        status = verification(item['required_checks'], item['check_refs'], event)
        statuses.append(status)
        groups[item['action_status']].append(
            f"- {label} [{item['action_status']}]; verification: {status} ({REASONS[status]})")
    body = ''
    for key, title in [('completed', 'Completed'), ('in_progress', 'In progress'), ('pending', 'Not started')]:
        body += '### ' + title + '\n' + '\n'.join(groups[key] or ['- (none)']) + '\n'
    overall = next((s for s in ('failed', 'unknown', 'not_run') if s in statuses),
                   'passed' if statuses else 'unknown')
    return {'section': SECTIONS[kind], 'body': body, 'verification': overall}


@lru_cache(maxsize=1)
def validator():
    path = Path(__file__).resolve().parents[2] / 'scripts/verify-log-validator.py'
    spec = importlib.util.spec_from_file_location('state_log_validator', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def local_path(root, relative, directory=False):
    path = root / relative
    for part in [path, *path.parents]:
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError('symlink task destination')
        if part.exists() and part != path and not part.is_dir():
            raise ValueError('non-directory task parent')
    if path.exists() and (not path.is_dir() if directory else not path.is_file()):
        raise ValueError('nonregular task destination')
    return path


def read_bytes(path):
    try:
        return path.read_bytes()
    except OSError as error:
        raise ValueError('required regular task artifact missing') from error


def publish(path, raw):
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def new_receipt(path, value):
    if path.exists() or path.is_symlink():
        raise ValueError('immutable receipt already exists')
    publish(path, (canonical(value) + '\n').encode())


def task_root_path(value):
    path = Path(value)
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('symlink task path; use the canonical physical root')
    root = path.resolve(strict=True)
    if not root.is_dir() or 'archive' in root.parts:
        raise ValueError('fresh writes require explicit active task')
    return root


def identity(root):
    path = local_path(root, '.wos/state-replay/identity.json')
    value = strict_json(read_bytes(path))
    fields(value, {'schema_version', 'task_id', 'task_root', 'lifecycle',
                   'log_prefix', 'log_prefix_sha'})
    if (type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['task_root'] != str(root) or value['lifecycle'] != 'active'):
        raise ValueError('moved or inactive task affiliation')
    token(value['task_id'])
    hash_value(value['log_prefix_sha'])
    decode_bytes(value['log_prefix'], value['log_prefix_sha'])
    return value


def check_log(root, raw, section=None):
    if raw and not raw.endswith(b'\n'):
        raise ValueError('historical log needs complete newline-terminated records')
    entries = []
    errors = []
    for number, line in enumerate(raw.splitlines(), 1):
        obj = strict_json(line)
        errors.extend(validator().validate_line(number, line.decode()))
        entries.append((number, obj))
    errors.extend(validator().sha_chain_breaks(entries, '0000-01-01T00:00:00.000Z'))
    if section is not None:
        selected = [(n, obj) for n, obj in entries
                    if obj.get('file') == 'TASK_STATE.md' and obj.get('section') == section]
        errors.extend(validator().content_sha_findings(selected, root))
    if errors:
        raise ValueError('canonical log conflict: ' + '; '.join(errors))


def initialize(task_root, task_id=None, genesis=False):
    root = task_root_path(task_root)
    state = local_path(root, 'TASK_STATE.md')
    raw = read_bytes(state)
    snapshot(root / n for n in AUTHORITY_FILES)
    log = local_path(root, '.wos/VERIFICATION_LOG.jsonl')
    folder = local_path(root, '.wos/state-replay', directory=True)
    existing = local_path(root, '.wos/state-replay/identity.json')
    if existing.exists():
        value = identity(root)
        if task_id is not None and task_id != value['task_id']:
            raise ValueError('conflicting registered task identity')
        read_bytes(log)
        return value
    if not log.exists() or not read_bytes(log):
        if genesis is not True or b'<!-- wos:write ' in raw:
            raise ValueError('explicit new-task genesis required; never infer lost history')
    if log.exists():
        check_log(root, read_bytes(log))
    task_id = token(task_id if task_id is not None else uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=True)
    local_path(root, '.wos/state-replay/events', directory=True).mkdir(exist_ok=True)
    value = {'schema_version': 1, 'task_id': task_id,
             'task_root': str(root), 'lifecycle': 'active',
             'log_prefix': base64.b64encode(read_bytes(log) if log.exists() else b'').decode(),
             'log_prefix_sha': digest(read_bytes(log) if log.exists() else b'')}
    new_receipt(existing, value)
    if not log.exists():
        publish(log, b'')
    return value


@contextlib.contextmanager
def writer(root):
    path = local_path(root, '.wos/state-replay/writer.lock')
    with path.open('a+b') as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('another prototype writer owns this task') from error
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def section_sha(path, section):
    value = validator()._sha_of_section_port(path, section)
    return None if value == 'null' else value


def section_bounds(raw, section):
    # Split on LF only, matching the canonical Bash and Python SHA functions.
    lines = raw.split(b'\n')
    lines = [line + b'\n' for line in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
    selected = [i for i, line in enumerate(lines)
                if line.rstrip(b'\n') == section.encode()]
    if len(selected) != 1:
        raise ValueError('selected canonical H2 must exist exactly once')
    index = selected[0]
    start = index - 1 if index and lines[index - 1].startswith(b'<!-- wos:write ') else index
    end = next((i for i in range(index + 1, len(lines)) if lines[i].startswith(b'## ')), len(lines))
    if end < len(lines) and lines[end - 1].startswith(b'<!-- wos:write '):
        end -= 1
    return lines, start, index, end


def splice(raw, section, body, header):
    lines, start, _, end = section_bounds(raw, section)
    return b''.join(lines[:start]) + header + section.encode() + b'\n' + body + b'\n' + b''.join(lines[end:])


def bytes_section_sha(raw, section):
    with tempfile.NamedTemporaryFile() as stream:
        stream.write(raw)
        stream.flush()
        return section_sha(Path(stream.name), section)


def write_header(event, section):
    reason = 'state-replay-' + digest(canonical(event).encode())
    return (f"<!-- wos:write owner={event['owner']} section='{section}' "
            f"run_id={event['run_id']} ts={event['ts']} reason={reason} mode=applied -->\n").encode()


def write_record(event, section, after_sha):
    row = {'ts': event['ts'], 'run_id': event['run_id'], 'owner': event['owner'],
           'owner_type': 'command', 'invoked_by': None, 'file': 'TASK_STATE.md',
           'section': section, 'event': 'overwrite' if event['expected_section_sha'] else 'write',
           'mode': 'applied', 'sha_before': event['expected_section_sha'], 'sha_after': after_sha,
           'reason': 'state-replay-' + digest(canonical(event).encode()),
           'partials': None, 'strategy': None}
    record = (canonical(row) + '\n').encode()
    if validator().validate_line(1, record.decode()):
        raise ValueError('generated canonical record invalid')
    return record


def decode_bytes(raw, expected=None):
    try:
        decoded = base64.b64decode(raw, validate=True)
    except (TypeError, ValueError) as error:
        raise ValueError('malformed prepared bytes') from error
    if expected is not None and digest(decoded) != expected:
        raise ValueError('prepared bytes digest conflict')
    return decoded


def receipt_paths(root, event_id):
    token(event_id)
    stem = '.wos/state-replay/events/' + event_id
    return local_path(root, stem + '.prepared.json'), local_path(root, stem + '.done.json')


def stale_flags(event):
    result = {}
    for name in ('authority', 'candidate'):
        try:
            current_snapshot(event[name + '_snapshot'])
            result[name + '_stale'] = False
        except (ValueError, OSError):
            result[name + '_stale'] = True
    return result


def report(root, event, outcome):
    stale = stale_flags(event)
    verification_status = 'unknown'
    if not any(stale.values()):
        try:
            verification_status = project(root, event)['verification']
        except (ValueError, OSError):
            pass
    return {'outcome': outcome, 'verification': verification_status, **stale}


def validate_affiliation(root, event):
    value = identity(root)
    if (not isinstance(event, dict) or event.get('task_root') != str(root)
            or event.get('task_id') != value['task_id'] or event.get('target') != 'TASK_STATE.md'):
        raise ValueError('event belongs to another task')
    token(event.get('event_id'))


def decode_prepared(root, path):
    value = strict_json(read_bytes(path))
    fields(value, {'event', 'event_sha', 'section', 'bytes', 'hashes', 'record'})
    event = value['event']
    fields(event, ENVELOPE)
    validate_affiliation(root, event)
    if path != receipt_paths(root, event['event_id'])[0]:
        raise ValueError('prepared receipt filename/event conflict')
    if digest(canonical(event).encode()) != value['event_sha']:
        raise ValueError('prepared event digest conflict')
    fields(value['bytes'], {'target_before', 'target_after', 'log_before', 'log_after'})
    fields(value['hashes'], set(value['bytes']))
    decoded = {}
    for key, raw in value['bytes'].items():
        hash_value(value['hashes'][key])
        decoded[key] = decode_bytes(raw, value['hashes'][key])
    record = decode_bytes(value['record'])
    if decoded['log_after'] != decoded['log_before'] + record:
        raise ValueError('prepared log prefix conflict')
    if not isinstance(event['kind'], str) or value['section'] != SECTIONS.get(event['kind']):
        raise ValueError('prepared section conflict')
    section = value['section']
    before, after = decoded['target_before'], decoded['target_after']
    if bytes_section_sha(before, section) != event['expected_section_sha']:
        raise ValueError('prepared section preimage conflict')
    after_sha = bytes_section_sha(after, section)
    if record != write_record(event, section, after_sha):
        raise ValueError('prepared record/event conflict')
    lines, start, index, end = section_bounds(after, section)
    body = b''.join(lines[index + 1:end])
    header = write_header(event, section)
    if (b''.join(lines[start:index]) != header or not body.endswith(b'\n')
            or splice(before, section, body[:-1], header) != after):
        raise ValueError('prepared splice/header conflict')
    check_log(root, decoded['log_before'])
    check_log(root, decoded['log_after'])
    return value, decoded, record


def require_history(root, log, pending=None):
    value = identity(root)
    prefix = decode_bytes(value['log_prefix'], value['log_prefix_sha'])
    if not log.startswith(prefix):
        raise ValueError('registered historical log prefix missing')
    folder = local_path(root, '.wos/state-replay/events', directory=True)
    for path in sorted(folder.glob('*.prepared.json')):
        event_id = path.name.removesuffix('.prepared.json')
        prepared, done = receipt_paths(root, event_id)
        receipt, data, record = decode_prepared(root, prepared)
        if receipt['event']['event_id'] != event_id:
            raise ValueError('receipt filename/event conflict')
        if not done.exists():
            if event_id != pending:
                raise ValueError('recover pending event before another publication')
            continue
        completion = strict_json(read_bytes(done))
        fields(completion, {'event', 'event_sha', 'outcome'})
        if (completion['outcome'] != 'applied' or completion['event_sha'] != receipt['event_sha']
                or not same(completion['event'], receipt['event'])):
            raise ValueError('historical completion/prepared conflict')
        if not log.startswith(data['log_after']) or log.splitlines(keepends=True).count(record) != 1:
            raise ValueError('historical log record missing or duplicated')


def completed(root, event, done, prepared):
    read_bytes(local_path(root, 'TASK_STATE.md'))
    log = read_bytes(local_path(root, '.wos/VERIFICATION_LOG.jsonl'))
    require_history(root, log)
    check_log(root, log)
    value = strict_json(read_bytes(done))
    fields(value, {'event', 'event_sha', 'outcome'})
    validate_affiliation(root, value['event'])
    if (prepared, done) != receipt_paths(root, value['event']['event_id']):
        raise ValueError('completed receipt filename/event conflict')
    event_sha = digest(canonical(event).encode())
    if value['event_sha'] != event_sha or not same(value['event'], event):
        raise ValueError('event identity replay conflict')
    if value['outcome'] == 'unchanged':
        return report(root, event, 'unchanged')
    if value['outcome'] != 'applied':
        raise ValueError('invalid completion receipt')
    receipt, data, record = decode_prepared(root, prepared)
    if receipt['event_sha'] != event_sha:
        raise ValueError('completed/prepared identity conflict')
    if not log.startswith(data['log_after']) or log.splitlines(keepends=True).count(record) != 1:
        raise ValueError('historical write record missing or duplicated')
    check_log(root, log, receipt['section'])
    return report(root, event, 'already_applied')


def resume(root, prepared, done, checkpoint=None):
    receipt, data, record = decode_prepared(root, prepared)
    event = receipt['event']
    target = local_path(root, 'TASK_STATE.md')
    log = local_path(root, '.wos/VERIFICATION_LOG.jsonl')
    target_now, log_now = read_bytes(target), read_bytes(log)
    require_history(root, log_now, event['event_id'])
    if target_now == data['target_before'] and log_now == data['log_before']:
        if any(stale_flags(event).values()):
            raise ValueError('superseded prepared event; no new target publication')
        projection = project(root, event)
        if splice(data['target_before'], receipt['section'], projection['body'].encode(),
                  write_header(event, receipt['section'])) != data['target_after']:
            raise ValueError('prepared projection conflict')
        if read_bytes(target) != target_now or read_bytes(log) != log_now:
            raise ValueError('preimage changed before target publication')
        publish(target, data['target_after'])
        if checkpoint:
            checkpoint('target')
    elif target_now != data['target_after'] or log_now not in (data['log_before'], data['log_after']):
        raise ValueError('recovery conflict; preserve current target and log')
    published = log_now == data['log_before']
    if published:
        if read_bytes(log) != data['log_before'] or read_bytes(target) != data['target_after']:
            raise ValueError('preimage changed before log publication')
        publish(log, data['log_after'])
        if checkpoint:
            checkpoint('log')
    if read_bytes(target) != data['target_after'] or read_bytes(log) != data['log_after']:
        raise ValueError('publication changed before finalization')
    check_log(root, read_bytes(log), receipt['section'])
    new_receipt(done, {'event': event, 'event_sha': receipt['event_sha'], 'outcome': 'applied'})
    return report(root, event, 'applied' if published else 'already_applied')


def apply_event(task_root, event, checkpoint=None):
    root = task_root_path(task_root)
    validate_affiliation(root, event)
    with writer(root):
        prepared, done = receipt_paths(root, event['event_id'])
        event_sha = digest(canonical(event).encode())
        if done.exists():
            return completed(root, event, done, prepared)
        if prepared.exists():
            receipt, _, _ = decode_prepared(root, prepared)
            if receipt['event_sha'] != event_sha:
                raise ValueError('event identity conflict')
            return resume(root, prepared, done, checkpoint)
        projection = project(root, event)
        target = local_path(root, 'TASK_STATE.md')
        log = local_path(root, '.wos/VERIFICATION_LOG.jsonl')
        target_before, log_before = read_bytes(target), read_bytes(log)
        require_history(root, log_before)
        section = projection['section']
        if section_sha(target, section) != event['expected_section_sha']:
            raise ValueError('dirty selected section preimage')
        check_log(root, log_before, section)
        body = projection['body'].encode()
        after_sha = digest(body.rstrip(b'\n'))
        header = write_header(event, section)
        target_after = splice(target_before, section, body, header)
        if bytes_section_sha(target_after, section) != after_sha:
            raise ValueError('staged section SHA conflict')
        if after_sha == event['expected_section_sha']:
            new_receipt(done, {'event': event, 'event_sha': event_sha, 'outcome': 'unchanged'})
            return report(root, event, 'unchanged')
        record = write_record(event, section, after_sha)
        data = {'target_before': target_before, 'target_after': target_after,
                'log_before': log_before, 'log_after': log_before + record}
        receipt = {'event': event, 'event_sha': event_sha, 'section': section,
                   'bytes': {key: base64.b64encode(raw).decode() for key, raw in data.items()},
                   'hashes': {key: digest(raw) for key, raw in data.items()},
                   'record': base64.b64encode(record).decode()}
        new_receipt(prepared, receipt)
        if checkpoint:
            checkpoint('prepared')
        return resume(root, prepared, done, checkpoint)


def recover_event(task_root, event_id, checkpoint=None):
    root = task_root_path(task_root)
    identity(root)
    with writer(root):
        prepared, done = receipt_paths(root, event_id)
        if done.exists():
            value = strict_json(read_bytes(done))
            fields(value, {'event', 'event_sha', 'outcome'})
            return completed(root, value['event'], done, prepared)
        return resume(root, prepared, done, checkpoint)
