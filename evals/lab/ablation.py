"""Opt-in one-factor preparation; no provider execution or delivery attestation."""
import re
import shlex
from pathlib import Path

import attempt as attempt_module
from attempt import (POLICY_FIELDS, canonical, digest, freeze, guarded_launch, same,
                     strict_json, validate_policy, verify, write_new)

FACTORS = {'mandatory_context', 'mechanical_state', 'exposed_catalog'}
INPUT_FIELDS = {'seed': 'seed_hashes', 'helper': 'helper_hashes',
                'driver': 'driver_hashes', 'scorer': 'scorer_hashes',
                'cases': 'case_hashes'}
COMMON_FIELDS = {'baseline_commit', 'policy', 'tools', 'permissions',
                 'collaboration', 'required_checks', 'protected_files',
                 'facts', 'public_brief', *INPUT_FIELDS.values()}
BOOTSTRAP = ('## LLM execution contract', '## Editor mode policy',
             '## Global output contract', '## Cross-cutting workflow guardrails')
GUARDS = {'source', 'authorization', 'protected_work', 'latest_requirement',
          'unknown_verification', 'verification_evidence', 'one_factor', 'no_default_promotion'}
LAYERS = {'submitted_prompt', 'tool_return', 'host_inventory',
          'provider_model_visible', 'usage', 'invoice'}


def _keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('closed object fields required')


def _strings(value, *, empty=False):
    if (not isinstance(value, list) or (not empty and not value)
            or any(not isinstance(s, str) or not s.strip() for s in value)
            or len(set(value)) != len(value)):
        raise ValueError('unique explicit string list required')


def _logical(name):
    if (not isinstance(name, str) or not name or '\\' in name
            or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('relative logical path without aliases required')
    return name


def _hashes(value):
    if not isinstance(value, dict) or not value:
        raise ValueError('nonempty logical source hashes required')
    for name, sha in value.items():
        _logical(name)
        if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
            raise ValueError('SHA256 source digest required')


def _physical(value):
    path = Path(value).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('physical path with no symlink ancestors required')
    return path


def _file(value):
    path = _physical(value)
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise ValueError('existing regular file required')
    return path


def _common(value):
    _keys(value, COMMON_FIELDS)
    if (not isinstance(value['baseline_commit'], str)
            or not re.fullmatch('[0-9a-f]{40}', value['baseline_commit'])):
        raise ValueError('explicit repaired baseline commit required')
    validate_policy(value['policy'])
    _keys(value['policy']['values'], POLICY_FIELDS)
    _strings(value['tools'])
    _strings(value['required_checks'])
    _strings(value['facts'])
    _strings(value['protected_files'], empty=True)
    permissions = value['permissions']
    _keys(permissions, {'sandbox', 'network'})
    if (not isinstance(permissions['sandbox'], str) or not permissions['sandbox'].strip()
            or type(permissions['network']) is not bool):
        raise ValueError('explicit sandbox label and boolean network permission required')
    collaboration = value['collaboration']
    _keys(collaboration, {'allowed', 'max_agents'})
    if (type(collaboration['allowed']) is not bool
            or type(collaboration['max_agents']) is not int or collaboration['max_agents'] < 1):
        raise ValueError('explicit collaboration policy required')
    for field in INPUT_FIELDS.values():
        _hashes(value[field])
    if (value['public_brief'] not in value['facts']
            or not set(value['facts'] + value['protected_files']) <= set(value['seed_hashes'])):
        raise ValueError('facts and protected work must exist in the common seed')
    for name in value['facts'] + value['protected_files']:
        _logical(name)


def validate_pair(spec):
    _keys(spec, {'schema_version', 'pair_id', 'factor', 'arms'})
    if (type(spec['schema_version']) is not int or spec['schema_version'] != 1
            or not isinstance(spec['pair_id'], str)
            or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', spec['pair_id'])
            or not isinstance(spec['factor'], str) or spec['factor'] not in FACTORS):
        raise ValueError('valid pair version, identity and factor required')
    if not isinstance(spec['arms'], list) or len(spec['arms']) != 2:
        raise ValueError('exactly two arms required')
    for arm, expected in zip(spec['arms'], ('control', 'treatment')):
        _keys(arm, {'arm_id', 'common', 'treatment'})
        if arm['arm_id'] != expected:
            raise ValueError('distinct ordered control and treatment required')
        _common(arm['common'])
        treatment = arm['treatment']
        _keys(treatment, FACTORS)
        if (treatment['mandatory_context'] not in ('full', 'kernel')
                or treatment['mechanical_state'] not in ('manual', 'prototype')):
            raise ValueError('bounded treatment methods required')
        _strings(treatment['exposed_catalog'])
        if treatment['exposed_catalog'] != sorted(treatment['exposed_catalog']):
            raise ValueError('canonical catalog order required')
    left, right = spec['arms']
    if not same(left['common'], right['common']):
        raise ValueError('common conditions differ')
    differences = {f for f in FACTORS if not same(left['treatment'][f], right['treatment'][f])}
    if differences != {spec['factor']}:
        raise ValueError('exactly the declared factor must differ')
    if (left['treatment']['mandatory_context'] != 'full'
            or left['treatment']['mechanical_state'] != 'manual'):
        raise ValueError('fresh repaired full/manual control required')
    if spec['factor'] == 'exposed_catalog' and not (
            set(right['treatment']['exposed_catalog']) < set(left['treatment']['exposed_catalog'])):
        raise ValueError('catalog treatment must be a proper subset')
    try:
        canonical(spec)
    except (ValueError, TypeError) as exc:
        raise ValueError('finite JSON pair required') from exc
    return spec


def _inputs(common, inputs):
    _keys(inputs, INPUT_FIELDS)
    result = {}
    for role, field in INPUT_FIELDS.items():
        _keys(inputs[role], common[field])
        paths = {name: _file(path) for name, path in inputs[role].items()}
        if len(set(paths.values())) != len(paths):
            raise ValueError('ambiguous logical source aliases')
        actual = {name: digest(path.read_bytes()) for name, path in paths.items()}
        if not same(actual, common[field]):
            raise ValueError('declared input bytes changed: ' + role)
        result[role] = {name: str(path) for name, path in paths.items()}
    return result


def _workspace(workspace, names):
    expected = set(names)
    for name in names:
        expected.update(str(p) for p in Path(name).parents if p != Path('.'))
    actual = set()
    for entry in workspace.rglob('*'):
        _physical(entry)
        actual.add(str(entry.relative_to(workspace)))
    if actual != expected:
        raise ValueError('initial workspace entry set changed')


def _prompt(brief, arm):
    return (brief + '\n\nExperimental treatment declaration (not an outcome):\n'
            + canonical(arm['treatment']) + '\n'
            + 'Shared required checks: ' + canonical(arm['common']['required_checks']) + '\n')


def prepare_pair(destination, spec, inputs):
    """Freeze fresh pre-launch seeds. Failed preparation stays inspectable, never overwritten."""
    spec = strict_json(canonical(validate_pair(spec)))
    common = spec['arms'][0]['common']
    sources = _inputs(common, inputs)
    root = _physical(destination)
    if root.exists():
        raise FileExistsError(root)
    if not root.parent.is_dir():
        raise ValueError('existing physical preparation parent required')
    brief = Path(sources['seed'][common['public_brief']]).read_text()
    root.mkdir()
    spec_file = root / 'pair-spec.json'
    spec_sha = write_new(spec_file, spec)
    arms = {}
    for arm in spec['arms']:
        arm_root = root / arm['arm_id']
        workspace = arm_root / 'workspace'
        workspace.mkdir(parents=True)
        for name, path in sources['seed'].items():
            dest = workspace / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as stream:
                stream.write(_file(path).read_bytes())
        prompt = arm_root / 'prompt.txt'
        with prompt.open('x') as stream:
            stream.write(_prompt(brief, arm))
        settings = arm_root / 'settings.json'
        write_new(settings, common['policy'])
        artifacts = {
            'driver': list(dict.fromkeys([str(_file(__file__)), str(_file(attempt_module.__file__)),
                                         *sources['driver'].values(),
                                         *sources['helper'].values()])),
            'prompt': [prompt, spec_file, *sources['seed'].values()],
            'settings': [settings], 'scorer': list(sources['scorer'].values()),
            'cases': list(sources['cases'].values()),
            'source': [workspace / name for name in sources['seed']],
        }
        attempt = freeze(arm_root / 'attempt.json', spec['pair_id'] + '-' + arm['arm_id'],
                         common['policy'], artifacts)
        arms[arm['arm_id']] = {'workspace': str(workspace), 'attempt': attempt}
    _inputs(common, sources)
    record = {'schema_version': 1, 'pair_id': spec['pair_id'], 'spec': spec,
              'spec_file': {'path': str(spec_file), 'sha256': spec_sha},
              'sources': sources, 'arms': arms}
    path = root / 'pair.json'
    binding = {'path': str(path), 'sha256': write_new(path, record), 'pair_id': spec['pair_id']}
    verify_pair(binding)
    return binding


def verify_pair(binding):
    """Validate both frozen initial arms. Legitimate later implementation needs a new attempt."""
    _keys(binding, {'path', 'sha256', 'pair_id'})
    path = _file(binding['path'])
    raw = path.read_bytes()
    if digest(raw) != binding['sha256']:
        raise ValueError('pair record changed')
    record = strict_json(raw)
    _keys(record, {'schema_version', 'pair_id', 'spec', 'spec_file', 'sources', 'arms'})
    if (type(record['schema_version']) is not int or record['schema_version'] != 1
            or record['pair_id'] != binding['pair_id']):
        raise ValueError('pair identity changed')
    spec = validate_pair(record['spec'])
    if spec['pair_id'] != binding['pair_id']:
        raise ValueError('contradictory pair identity')
    _keys(record['spec_file'], {'path', 'sha256'})
    spec_path = _file(record['spec_file']['path'])
    if (spec_path != path.parent / 'pair-spec.json'
            or digest(spec_path.read_bytes()) != record['spec_file']['sha256']
            or not same(strict_json(spec_path.read_bytes()), spec)):
        raise ValueError('pair specification changed')
    common = spec['arms'][0]['common']
    sources = _inputs(common, record['sources'])
    _keys(record['arms'], {'control', 'treatment'})
    for arm in spec['arms']:
        frozen = record['arms'][arm['arm_id']]
        _keys(frozen, {'workspace', 'attempt'})
        workspace = _physical(frozen['workspace'])
        if workspace != path.parent / arm['arm_id'] / 'workspace':
            raise ValueError('workspace moved or cross-pair binding')
        _workspace(workspace, sources['seed'])
        _inputs(common, dict(sources, seed={name: workspace / name for name in sources['seed']}))
        for name in ('prompt.txt', 'settings.json', 'attempt.json'):
            _file(workspace.parent / name)
        if Path(frozen['attempt']['path']) != workspace.parent / 'attempt.json':
            raise ValueError('attempt outside its arm')
        attempt = verify(frozen['attempt'])
        if (attempt['attempt_id'] != spec['pair_id'] + '-' + arm['arm_id']
                or not same(attempt['effective_policy'], common['policy'])
                or not same(strict_json((workspace.parent / 'settings.json').read_bytes()), common['policy'])
                or (workspace.parent / 'prompt.txt').read_text()
                != _prompt(Path(sources['seed'][common['public_brief']]).read_text(), arm)):
            raise ValueError('attempt policy or prompt contradicts pair')
    return record


def guarded_pair(binding, arm, callback):
    """Guard a caller-owned local callback; this is not a provider or spend governor."""
    record = verify_pair(binding)
    if arm not in record['arms']:
        raise ValueError('unknown arm')
    return guarded_launch(record['arms'][arm]['attempt'], callback)


def _reference(path):
    path = _file(path)
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': digest(raw), 'bytes': len(raw)}


def _reference_bytes(ref):
    _keys(ref, {'path', 'sha256', 'bytes'})
    if type(ref['bytes']) is not int or ref['bytes'] < 0:
        raise ValueError('exact byte count required')
    raw = _file(ref['path']).read_bytes()
    if len(raw) != ref['bytes'] or digest(raw) != ref['sha256']:
        raise ValueError('retained source bytes changed')
    return raw


def _route(raw, names):
    if not isinstance(raw, str):
        raise ValueError('explicit registered route required')
    argv = shlex.split(raw)
    if not argv or argv[0].removeprefix('/') not in names:
        raise ValueError('unknown registered route')
    return argv[0].removeprefix('/'), argv[1:]


def catalog_closure(workflow_root, roots):
    """Static metadata closure only; dynamic dispatch and host delivery are unproved."""
    root = _physical(workflow_root)
    _strings(roots)
    catalog_path = _file(root / 'docs/command-catalog.json')
    catalog_ref = _reference(catalog_path)
    catalog = strict_json(_reference_bytes(catalog_ref))
    if (not isinstance(catalog, dict) or type(catalog.get('schema_version')) is not int
            or catalog['schema_version'] != 1 or not isinstance(catalog.get('commands'), list)
            or not catalog['commands']):
        raise ValueError('supported nonempty registered catalog required')
    entries, sources = {}, {'docs/command-catalog.json': catalog_path}
    source_refs = {'docs/command-catalog.json': catalog_ref}
    for entry in catalog['commands']:
        name = entry.get('name') if isinstance(entry, dict) else None
        if (not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_-]*(?:/[a-z][a-z0-9_-]*)*', name)
                or name in entries):
            raise ValueError('unique registered command names required')
        routes = entry.get('next_commands')
        _strings(routes, empty=True)
        source = root / 'commands' / (name + '.md')
        if not source.exists():
            source = root / 'commands' / name / 'SKILL.md'
        logical = str(source.relative_to(root))
        sources[logical] = _file(source)
        source_refs[logical] = _reference(source)
        entries[name] = entry
    if type(catalog.get('command_count')) is not int or catalog['command_count'] != len(entries):
        raise ValueError('catalog count contradicts actual registered entries')
    edges, route_records = {}, []
    for name, entry in entries.items():
        edges[name] = []
        for raw in entry['next_commands']:
            command, args = _route(raw, entries)
            edges[name].append(command)
            route_records.append({'from': name, 'raw': raw, 'command': command, 'arguments': args})
    pending = [_route(raw, entries)[0] for raw in roots]
    selected = set()
    while pending:
        name = pending.pop()
        if name not in selected:
            selected.add(name)
            pending.extend(edges[name])
    return {'names': sorted(entries), 'selected': sorted(selected), 'entries': entries,
            'routes': route_records, 'sources': sources, 'source_refs': source_refs,
            'scope': 'static next_commands closure; dynamic dispatch and actual exposure unknown'}


def _guard_packet(root, guards):
    """Preserve audited caller-selected passages; this does not judge their semantics."""
    _keys(guards, GUARDS)
    records, sources, source_refs = [], {}, {}
    for name in sorted(GUARDS):
        ref = guards[name]
        _keys(ref, {'path', 'start_line', 'end_line', 'sha256'})
        path = _file(root / _logical(ref['path']))
        source_refs.setdefault(ref['path'], _reference(path))
        lines = _reference_bytes(source_refs[ref['path']]).decode('utf-8').splitlines(keepends=True)
        if (type(ref['start_line']) is not int or type(ref['end_line']) is not int
                or not 1 <= ref['start_line'] <= ref['end_line'] <= len(lines)):
            raise ValueError('bounded exact guard passage required')
        text = ''.join(lines[ref['start_line'] - 1:ref['end_line']])
        if not text.strip() or digest(text.encode('utf-8')) != ref['sha256']:
            raise ValueError('missing or changed audited guard passage')
        records.append({'guard': name, 'source': ref, 'text': text})
        sources[ref['path']] = path
    return records, sources, source_refs


def _factor_payloads(workflow_root, spec, guards, catalog_roots):
    root = _physical(workflow_root)
    catalog = catalog_closure(root, catalog_roots)
    control, treatment = spec['arms']
    if control['treatment']['exposed_catalog'] != catalog['names']:
        raise ValueError('control must declare the actual complete catalog')
    expected = catalog['selected'] if spec['factor'] == 'exposed_catalog' else catalog['names']
    if treatment['treatment']['exposed_catalog'] != expected:
        raise ValueError('treatment catalog differs from its static closure')
    # Imported lazily so the slice01 freezer still works without payload helpers.
    from context import sections
    import context as context_module
    wos = _file(root / 'WORKFLOW_OPERATING_SYSTEM.md')
    wos_ref = _reference(wos)
    rows = sections(_reference_bytes(wos_ref).decode('utf-8'))
    bootstrap = _file(root / 'commands/_shared/mandatory-context-bootstrap.md')
    bootstrap_ref = _reference(bootstrap)
    bootstrap_raw = _reference_bytes(bootstrap_ref)
    chosen = []
    for heading in BOOTSTRAP:
        candidates = [row for row in rows if row['heading'] == heading]
        if len(candidates) != 1:
            raise ValueError('missing or ambiguous full bootstrap section')
        chosen.append(candidates[0]['text'])
    guard_records, guard_sources, guard_refs = _guard_packet(root, guards)
    common_guards = ('Audited common task guard passages (both arms):\n'
                     + canonical(guard_records) + '\n')
    full = ''.join(chosen).encode('utf-8') + b'\n' + bootstrap_raw
    # Task guard packet is common, not an extra requirement added only to kernel.
    kernel = ('Source-backed task kernel. Full canonical policies remain available on demand.\n'
              'Coverage is limited to the audited task passages below; model compliance is unknown.\n'
              + common_guards).encode('utf-8')
    state_source_names = ['evals/lab/state.py', 'evals/lab/attempt.py',
                          'scripts/verify-log-validator.py', 'scripts/emit-substrate-write.sh']
    sources = dict(catalog['sources'], **guard_sources)
    sources['WORKFLOW_OPERATING_SYSTEM.md'] = wos
    sources['commands/_shared/mandatory-context-bootstrap.md'] = bootstrap
    for name in state_source_names:
        sources[name] = _file(root / name)
    sources['payload-context-runtime.py'] = _file(context_module.__file__)
    sources['payload-builder-runtime.py'] = _file(__file__)
    source_refs = dict(catalog['source_refs'])
    for name, ref in dict(guard_refs, **{'WORKFLOW_OPERATING_SYSTEM.md': wos_ref,
                          'commands/_shared/mandatory-context-bootstrap.md': bootstrap_ref}).items():
        if name in source_refs and source_refs[name] != ref:
            raise ValueError('source changed between payload reads')
        source_refs[name] = ref
    for name, path in sources.items():
        source_refs.setdefault(name, _reference(path))
        _reference_bytes(source_refs[name])
    manual = ('Use the existing canonical substrate writer for factual state. The model selects '
              'events, phase, command, requirements and activity status. Check obligations and '
              'trusted records are common; missing or stale verification stays unknown.\n')
    prototype = ('Use the opt-in state.py projection and publication for factual state. The model '
                 'selects events, phase, command, requirements and activity status. Check obligations '
                 'and trusted records are common; missing or stale verification stays unknown.\n')
    payloads = {}
    for arm in spec['arms']:
        treatment_values = arm['treatment']
        names = treatment_values['exposed_catalog']
        payloads[arm['arm_id']] = {
            'mandatory_context': full if treatment_values['mandatory_context'] == 'full' else kernel,
            'mechanical_state': (manual if treatment_values['mechanical_state'] == 'manual'
                                 else prototype).encode('utf-8'),
            'exposed_catalog': canonical([catalog['entries'][n] for n in names]).encode('utf-8'),
        }
    changed = {name for name in FACTORS
               if payloads['control'][name] != payloads['treatment'][name]}
    if changed != {spec['factor']}:
        raise ValueError('actual payloads do not vary exactly the declared factor')
    return {'payloads': payloads, 'sources': sources, 'source_refs': source_refs,
            'common_guards': common_guards.encode('utf-8'),
            'catalog': {k: catalog[k] for k in ('names', 'selected', 'routes', 'scope')},
            'guard_records': guard_records, 'state_sources': state_source_names}


def _write_bytes(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
    return _reference(path)


def prepare_factor(destination, spec, inputs, workflow_root, guards, catalog_roots):
    """Build concrete offline payloads. Host configuration/delivery still needs an adapter."""
    spec = strict_json(canonical(validate_pair(spec)))
    original = _inputs(spec['arms'][0]['common'], inputs)
    assets = _factor_payloads(workflow_root, spec, guards, catalog_roots)
    for ref in assets['source_refs'].values():
        _reference_bytes(ref)
    root = _physical(destination)
    if root.exists():
        raise FileExistsError(root)
    if not root.parent.is_dir():
        raise ValueError('existing physical preparation parent required')
    root.mkdir()
    asset_root = root / 'assets'
    asset_root.mkdir()
    shared = _write_bytes(asset_root / 'common-guards.txt', assets['common_guards'])
    payloads = {}
    for arm, values in assets['payloads'].items():
        payloads[arm] = {name: _write_bytes(asset_root / (arm + '-' + name + '.txt'), raw)
                         for name, raw in values.items()}
    # Both methods and canonical sources are equally available in both arms.
    additions = {**{'workflow/' + name: path for name, path in assets['sources'].items()},
                 'prepared/common-guards.txt': Path(shared['path'])}
    for arm, values in payloads.items():
        additions.update({'prepared/' + arm + '-' + name + '.txt': Path(ref['path'])
                          for name, ref in values.items()})
    if set(additions) & set(original['helper']):
        raise ValueError('reserved preparation helper identity collision')
    helper = dict(original['helper'], **{n: str(p) for n, p in additions.items()})
    helper_hashes = dict(spec['arms'][0]['common']['helper_hashes'])
    helper_hashes.update({'workflow/' + n: ref['sha256']
                          for n, ref in assets['source_refs'].items()})
    helper_hashes['prepared/common-guards.txt'] = shared['sha256']
    for arm, values in payloads.items():
        helper_hashes.update({'prepared/' + arm + '-' + name + '.txt': ref['sha256']
                             for name, ref in values.items()})
    for arm in spec['arms']:
        arm['common']['helper_hashes'] = dict(helper_hashes)
    pair = prepare_pair(root / 'pair', spec, dict(original, helper=helper))
    frozen_pair = verify_pair(pair)
    invocations = {}
    brief = _file(original['seed'][spec['arms'][0]['common']['public_brief']]).read_bytes()
    for arm in spec['arms']:
        name = arm['arm_id']
        prompt = asset_root / (name + '-invocation-prompt.txt')
        raw = brief + b'\n\n' + assets['common_guards']
        for factor in ('mandatory_context', 'mechanical_state', 'exposed_catalog'):
            raw += b'\n' + factor.encode() + b':\n' + _reference_bytes(payloads[name][factor])
        prompt_ref = _write_bytes(prompt, raw)
        attempt_record = verify(frozen_pair['arms'][name]['attempt'])
        roles = {role: list(paths) for role, paths in attempt_record['artifacts'].items()}
        roles['prompt'].append(str(prompt))
        binding = freeze(asset_root / (name + '-invocation.json'),
                         spec['pair_id'] + '-' + name + '-payload', arm['common']['policy'], roles)
        invocations[name] = {'prompt': prompt_ref, 'attempt': binding}
    record = {'schema_version': 1, 'pair': pair, 'factor': spec['factor'],
              'payloads': payloads, 'common_guards': shared, 'catalog': assets['catalog'],
              'guard_records': assets['guard_records'], 'state_sources': assets['state_sources'],
              'source_refs': assets['source_refs'],
              'invocations': invocations, 'model_delivery': 'unknown'}
    path = root / 'factor.json'
    binding = {'path': str(path), 'sha256': write_new(path, record)}
    verify_factor(binding)
    return binding


def verify_factor(binding):
    _keys(binding, {'path', 'sha256'})
    raw = _file(binding['path']).read_bytes()
    if digest(raw) != binding['sha256']:
        raise ValueError('factor record changed')
    record = strict_json(raw)
    _keys(record, {'schema_version', 'pair', 'factor', 'payloads', 'common_guards', 'catalog',
                   'guard_records', 'state_sources', 'source_refs', 'invocations', 'model_delivery'})
    if type(record['schema_version']) is not int or record['schema_version'] != 1:
        raise ValueError('unsupported factor record')
    pair = verify_pair(record['pair'])
    if record['factor'] != pair['spec']['factor'] or record['model_delivery'] != 'unknown':
        raise ValueError('contradictory factor identity or delivery claim')
    if not isinstance(record['source_refs'], dict) or not record['source_refs']:
        raise ValueError('consumed source references required')
    for name, ref in record['source_refs'].items():
        logical = 'workflow/' + _logical(name)
        _reference_bytes(ref)
        if (pair['sources']['helper'].get(logical) != ref['path']
                or pair['spec']['arms'][0]['common']['helper_hashes'].get(logical) != ref['sha256']):
            raise ValueError('consumed source differs from frozen helper')
    shared = _reference_bytes(record['common_guards'])
    _keys(record['payloads'], {'control', 'treatment'})
    _keys(record['invocations'], {'control', 'treatment'})
    values = {}
    brief = _file(pair['sources']['seed'][pair['spec']['arms'][0]['common']['public_brief']]).read_bytes()
    for arm in pair['spec']['arms']:
        name = arm['arm_id']
        _keys(record['payloads'][name], FACTORS)
        values[name] = {f: _reference_bytes(ref) for f, ref in record['payloads'][name].items()}
        invocation = record['invocations'][name]
        _keys(invocation, {'prompt', 'attempt'})
        expected = brief + b'\n\n' + shared
        for f in ('mandatory_context', 'mechanical_state', 'exposed_catalog'):
            expected += b'\n' + f.encode() + b':\n' + values[name][f]
        if _reference_bytes(invocation['prompt']) != expected:
            raise ValueError('prepared invocation contradicts actual factor payloads')
        attempt = verify(invocation['attempt'])
        if (attempt['attempt_id'] != pair['spec']['pair_id'] + '-' + name + '-payload'
                or not same(attempt['effective_policy'], arm['common']['policy'])):
            raise ValueError('invocation policy or identity changed')
    if {f for f in FACTORS if values['control'][f] != values['treatment'][f]} != {record['factor']}:
        raise ValueError('actual prepared factor difference changed')
    return record


def guarded_factor(binding, arm, callback):
    """Caller-owned local preflight, not a provider, exposure or spending governor."""
    record = verify_factor(binding)
    if arm not in record['invocations']:
        raise ValueError('unknown arm')
    return guarded_launch(record['invocations'][arm]['attempt'], callback)


def _provenance(provenance):
    _keys(provenance, {'origin', 'producer', 'episode_id', 'arm_id', 'adapter_id'})
    if (provenance['origin'] not in ('synthetic', 'host-recorded')
            or provenance['arm_id'] not in ('control', 'treatment')
            or any(not isinstance(provenance[k], str) or not provenance[k].strip()
                   for k in ('producer', 'episode_id'))
            or (provenance['adapter_id'] is not None
                and (not isinstance(provenance['adapter_id'], str) or not provenance['adapter_id'].strip()))):
        raise ValueError('explicit observation provenance labels required')


def retain_observation(destination, kind, source, provenance):
    """Bind exact local bytes; caller labels never authenticate provider provenance."""
    if not isinstance(kind, str) or kind not in LAYERS:
        raise ValueError('explicit separate observation layer required')
    _provenance(provenance)
    source_ref = _reference(source)
    raw = _reference_bytes(source_ref)
    root = _physical(destination)
    if root.exists():
        raise FileExistsError(root)
    if not root.parent.is_dir():
        raise ValueError('existing physical observation parent required')
    root.mkdir()
    retained = _write_bytes(root / 'raw.bin', raw)
    record = {'schema_version': 1, 'kind': kind, 'provenance': provenance,
              'source': source_ref, 'retained': retained}
    path = root / 'observation.json'
    return {'path': str(path), 'sha256': write_new(path, record)}


def inspect_observation(binding):
    _keys(binding, {'path', 'sha256'})
    raw = _file(binding['path']).read_bytes()
    if digest(raw) != binding['sha256']:
        raise ValueError('observation record changed')
    record = strict_json(raw)
    _keys(record, {'schema_version', 'kind', 'provenance', 'source', 'retained'})
    if (type(record['schema_version']) is not int or record['schema_version'] != 1
            or not isinstance(record['kind'], str) or record['kind'] not in LAYERS):
        raise ValueError('unsupported observation')
    _provenance(record['provenance'])
    source = _reference_bytes(record['source'])
    if _reference_bytes(record['retained']) != source:
        raise ValueError('retained observation contradicts original source')
    return {'record': record, 'raw': source, 'model_delivery': 'unknown',
            'provenance_attestation': 'unknown', 'invoice_attestation': 'unknown'}


def catalog_inventory(binding, arm, observation):
    """Compare retained inventory labels only; no host/model fidelity certification."""
    factor = verify_factor(binding)
    pair = verify_pair(factor['pair'])
    if arm not in factor['invocations']:
        raise ValueError('unknown arm')
    result = inspect_observation(observation)
    record = result['record']
    if (record['kind'] != 'host_inventory' or record['provenance']['arm_id'] != arm
            or record['provenance']['episode_id'] != pair['spec']['pair_id']):
        raise ValueError('inventory belongs to a different layer, arm or episode')
    inventory = strict_json(result['raw'])
    _keys(inventory, {'enabled', 'truncated', 'observed_routes'})
    _strings(inventory['enabled'], empty=True)
    _strings(inventory['observed_routes'], empty=True)
    if type(inventory['truncated']) is not bool:
        raise ValueError('exact truncation flag required')
    expected = pair['spec']['arms'][0 if arm == 'control' else 1]['treatment']['exposed_catalog']
    missing = sorted(set(expected) - set(inventory['enabled']))
    extra = sorted(set(inventory['enabled']) - set(expected))
    unsupported = []
    for route in inventory['observed_routes']:
        try:
            name, _ = _route(route, expected)
        except ValueError:
            unsupported.append(route)
    matches = not (missing or extra or unsupported or inventory['truncated'])
    return {'inventory_consistency': 'match' if matches else 'mismatch', 'missing': missing,
            'extra': extra, 'unsupported_routes': unsupported, 'truncated': inventory['truncated'],
            'actual_exposure': 'unknown', 'model_delivery': 'unknown',
            'provenance': record['provenance']}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', metavar='REQUEST_JSON')
    action.add_argument('--verify', metavar='BINDING_JSON')
    args = parser.parse_args()
    request = strict_json(_file(args.prepare or args.verify).read_bytes())
    if args.prepare:
        _keys(request, {'destination', 'spec', 'inputs', 'workflow_root', 'guards', 'catalog_roots'})
        result = prepare_factor(**request)
    else:
        record = verify_factor(request)
        result = {'factor': record['factor'], 'local_integrity': 'verified', 'model_delivery': 'unknown'}
    print(canonical(result))


if __name__ == '__main__':
    main()
