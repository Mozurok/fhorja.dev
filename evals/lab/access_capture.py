#!/usr/bin/env python3
"""Opt-in access consistency audit for trusted retained broker captures.

This adapter observes access only. Hash links do not authenticate a journal;
origin, resource accounting and sandbox enforcement need separate evidence.
"""
import argparse
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re

from attempt import same, strict_json


def broker_arguments(tool, arguments):
    schemas = {'files': (set(), set()), 'read': ({'path'}, {'path'}),
               'write': ({'path', 'text'}, {'path', 'text'}),
               'run': ({'path', 'language'}, {'path', 'language', 'args', 'stdin'})}
    if (tool not in schemas or not isinstance(arguments, dict)
            or not schemas[tool][0] <= set(arguments) <= schemas[tool][1]):
        return False
    for key in ('path', 'text', 'language', 'stdin'):
        if key in arguments and not isinstance(arguments[key], str):
            return False
    return ('args' not in arguments or isinstance(arguments['args'], list)
            and all(isinstance(value, str) for value in arguments['args']))


def rows(path):
    return [strict_json(line) for line in Path(path).read_text().splitlines() if line.strip()]


def known_missing_read(start, end, workspace):
    """Only the trusted broker's exact scoped ENOENT response is observable failure."""
    args = start.get('arguments')
    if start.get('tool') != 'read' or not isinstance(args, dict) or set(args) != {'path'}:
        return False
    value = args['path']
    if not isinstance(value, str) or not value or '\x00' in value:
        return False
    parts = value.split('/')
    if any(part in ('', '.', '..') for part in parts):
        return False
    root = Path(workspace).resolve()
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            return False
    expected = str(FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(path)))
    return end.get('is_error') is True and end.get('result') == {'error': expected}


def gateway_text(output):
    if isinstance(output, str):
        return output
    if (isinstance(output, list) and output
            and all(isinstance(block, dict) and block.get('type') in ('text', 'input_text')
                    and isinstance(block.get('text'), str) for block in output)):
        return output[0]['text']
    return ''


def cell_status(text):
    """Require the retained host's whole lifecycle header, with finite duration."""
    pattern = r'^(Script running with cell ID ([0-9]+)|Script completed)\nWall time ([0-9]+(?:\.[0-9]+)?) seconds\nOutput:\n'
    match = re.match(pattern, text)
    if not match or not math.isfinite(float(match.group(3))):
        return None
    return ('yielded', match.group(2)) if match.group(2) is not None else ('completed', None)


def access_audit(rollouts, journal, expected_workspace, expected_profile, exec_path):
    failures = []; calls = []; nested = []; gateway = {}; outputs = set(); active = set(); all_outputs = set()
    pending = set(); wait_cells = {}; gateway_names = {}; direct_outputs = []
    try:
        log = rows(journal); previous = None
        for i, row in enumerate(log):
            raw = json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
            if type(row.get('seq')) is not int or row.get('seq') != i or row.get('previous') != previous:
                failures.append('access journal integrity')
            previous = hashlib.sha256(raw).hexdigest()
        if not log or log[0].get('event') != 'broker.started' or log[-1].get('event') != 'broker.closed':
            failures.append('access journal not terminal')
        if log and (log[0].get('workspace') != str(Path(expected_workspace).resolve())
                    or log[0].get('profile_sha256') != expected_profile):
            failures.append('access journal scope differs from invocation')
        starts = [r for r in log if r.get('event') == 'tool.started']
        ends = [r for r in log if r.get('event') == 'tool.completed']
        if len(starts) != len(ends) or len({r['call_id'] for r in starts}) != len(starts):
            failures.append('access call membership')
        for start, end in zip(starts, ends):
            if (not same((start['call_id'], start['tool']), (end['call_id'], end['tool']))
                    or type(start['call_id']) not in (int, str)
                    or type(end['call_id']) not in (int, str)):
                failures.append('access pair mismatch')
            if type(end.get('is_error')) is not bool or 'result' not in end:
                failures.append('access result unavailable')
            if end.get('is_error') is True and not known_missing_read(start, end, expected_workspace):
                failures.append('broker access denied or unknown')
        expected_events = ['broker.started'] + [item for _ in starts for item in ('tool.started', 'tool.completed')] + ['broker.closed']
        if [r.get('event') for r in log if r.get('event') not in ('mcp.initialize', 'mcp.tools_list')] != expected_events:
            failures.append('access event schema or ordering')
        for path in rollouts:
            for event in rows(path):
                if not isinstance(event, dict): raise ValueError('rollout event is not an object')
                if event.get('type') != 'response_item':
                    if event.get('type') not in ('session_meta', 'turn_context', 'event_msg', 'token_usage_record', 'compacted', 'world_state') or not isinstance(event.get('payload'), dict):
                        failures.append('unknown rollout event or payload schema: ' + str(event.get('type')))
                    elif event['type'] == 'event_msg' and event['payload'].get('type') not in ('task_started', 'task_complete', 'item_completed', 'token_count', 'agent_message', 'agent_reasoning'):
                        failures.append('unknown rollout message schema: ' + str(event['payload'].get('type')))
                    if event.get('type') == 'event_msg' and event['payload'].get('type') == 'item_completed':
                        item = event['payload'].get('item', {})
                        kind = item.get('type')
                        if kind == 'McpToolCall':
                            if (not active and len(pending) != 1) or item.get('server') != 'candidate_access':
                                failures.append('nested access outside scoped gateway')
                            nested.append(item)
                        elif kind not in ('AgentMessage', 'Reasoning', 'UserMessage'):
                            failures.append('unobserved nested tool item: ' + str(kind))
                    continue
                payload = event.get('payload', {})
                if not isinstance(payload, dict): raise ValueError('response payload is not an object')
                if payload.get('type') in ('function_call_output', 'custom_tool_call_output'):
                    all_outputs.add(payload.get('call_id'))
                    if payload.get('call_id') not in gateway:
                        direct_outputs.append(payload)
                if payload.get('type') in ('function_call', 'custom_tool_call'):
                    if payload.get('name') in ('exec', 'wait'):
                        identifier = payload.get('call_id')
                        if not isinstance(identifier, str) or not identifier or identifier in gateway:
                            failures.append('gateway identity unavailable or duplicated')
                        if payload['name'] == 'exec':
                            valid = payload['type'] == 'custom_tool_call' and isinstance(payload.get('input'), str)
                            if active or pending:
                                failures.append('ambiguous concurrent gateway execution')
                        else:
                            arguments = strict_json(payload.get('arguments', '{}'))
                            valid = (payload['type'] == 'function_call' and isinstance(arguments, dict)
                                     and isinstance(arguments.get('cell_id'), str)
                                     and set(arguments) <= {'cell_id', 'yield_time_ms', 'max_tokens', 'terminate'})
                            if valid:
                                valid = (all(type(arguments[key]) is int and arguments[key] >= (1 if key == 'max_tokens' else 0)
                                             for key in ('yield_time_ms', 'max_tokens') if key in arguments)
                                         and ('terminate' not in arguments or type(arguments['terminate']) is bool))
                            if valid:
                                cell = arguments['cell_id']
                                if cell not in pending or arguments.get('terminate', False) is not False or cell in wait_cells.values():
                                    failures.append('unknown or interrupted pending cell')
                                wait_cells[identifier] = cell
                        if not valid: failures.append('unknown gateway schema')
                        gateway_names[identifier] = payload['name']
                        gateway[identifier] = payload['type']; active.add(identifier)
                    else:
                        calls.append(payload)
                elif payload.get('type') in ('custom_tool_call_output', 'function_call_output') and payload.get('call_id') in gateway:
                    identifier = payload['call_id']
                    if identifier in outputs or identifier not in active or payload['type'] != gateway[identifier] + '_output' or 'output' not in payload:
                        failures.append('gateway output pairing unavailable')
                    text = gateway_text(payload.get('output'))
                    status = cell_status(text)
                    yielded = status is not None and status[0] == 'yielded'
                    if status is None:
                        failures.append('unknown cell lifecycle schema')
                    if gateway_names[identifier] == 'exec' and yielded:
                        cell = status[1]
                        if cell in pending:
                            failures.append('duplicate pending cell')
                        pending.add(cell)
                        if len(pending) > 1:
                            failures.append('ambiguous concurrent pending cells')
                    elif gateway_names[identifier] == 'wait':
                        cell = wait_cells.pop(identifier, None)
                        if yielded:
                            if status[1] != cell:
                                failures.append('wait yielded a different cell')
                        elif status is not None and status[0] == 'completed':
                            pending.discard(cell)
                        else:
                            failures.append('wait completion unavailable')
                    outputs.add(identifier); active.discard(identifier)
                elif payload.get('type') not in ('message', 'reasoning', 'function_call_output', 'custom_tool_call_output', 'compaction'):
                    failures.append('unobserved response event: ' + str(payload.get('type')))
        if active or set(gateway) != outputs: failures.append('gateway output unavailable')
        if pending or wait_cells: failures.append('pending cell terminal unavailable')
        if gateway and all_outputs != set(gateway): failures.append('orphan gateway output')
        if gateway and calls: failures.append('mixed direct and gateway tool mode')
        if not calls and not nested:
            failures.append('mandatory observed tool access unavailable')
        observed = []
        direct_ids = set()
        for call in calls:
            name = call.get('name', '')
            if not name.startswith('mcp__candidate_access__'):
                failures.append('unobserved access via tool: ' + name); continue
            arguments = strict_json(call.get('arguments', '{}'))
            tool = name.removeprefix('mcp__candidate_access__')
            if not broker_arguments(tool, arguments):
                failures.append('unknown broker tool or argument schema')
            if (call.get('type') != 'function_call' or not isinstance(call.get('call_id'), str)
                    or not call['call_id'] or call['call_id'] in direct_ids):
                failures.append('provider tool call identity unavailable')
            direct_ids.add(call.get('call_id'))
            observed.append((tool, arguments))
        if not gateway and direct_outputs:
            direct_calls = {call.get('call_id'): index for index, call in enumerate(calls)}
            seen = set()
            for output in direct_outputs:
                identifier = output.get('call_id')
                if (identifier not in direct_calls or identifier in seen
                        or output.get('type') != 'function_call_output'):
                    failures.append('direct output pairing unavailable')
                    continue
                seen.add(identifier)
                end = ends[direct_calls[identifier]]
                result = strict_json(output.get('output', ''))
                content = result.get('content', [])
                if (result.get('isError') is not end.get('is_error') or len(content) != 1
                        or content[0].get('type') != 'text'
                        or not same(strict_json(content[0]['text']), end.get('result'))):
                    failures.append('direct output differs from broker journal')
            if seen != set(direct_calls):
                failures.append('direct output unavailable')
        if gateway:
            identities = set()
            for item, end in zip(nested, ends):
                identifier = item.get('id')
                if not isinstance(identifier, str) or not identifier or identifier in identities:
                    failures.append('nested tool identity unavailable or duplicated')
                identities.add(identifier)
                status = 'failed' if end.get('is_error') is True else 'completed'
                if item.get('status') != status or item.get('result', {}).get('isError') is not end.get('is_error'):
                    failures.append('nested tool result unavailable')
                content = item.get('result', {}).get('content', [])
                if len(content) != 1 or content[0].get('type') != 'text' or not same(strict_json(content[0]['text']), end['result']):
                    failures.append('nested result differs from broker journal')
            observed = [(item.get('tool'), item.get('arguments')) for item in nested]
            for tool, arguments in observed:
                if not broker_arguments(tool, arguments):
                    failures.append('unknown nested broker schema')
        expected = [(r['tool'], r['arguments']) for r in starts]
        if not same(observed, expected):
            failures.append('tool trace differs from broker journal')
        emitted = []; started_items = {}; completed_items = set()
        for event in rows(exec_path):
            if not isinstance(event, dict): raise ValueError('exec event is not an object')
            if event.get('type') not in ('item.started', 'item.updated', 'item.completed'):
                kind = event.get('type')
                if kind == 'thread.started':
                    valid = isinstance(event.get('thread_id'), str) and bool(event['thread_id'])
                elif kind == 'turn.started': valid = True
                elif kind == 'turn.completed': valid = isinstance(event.get('usage'), dict)
                elif kind in ('error', 'turn.failed'): valid = isinstance(event.get('message'), str) or isinstance(event.get('error'), dict)
                else: valid = False
                if not valid: failures.append('unknown exec event or payload schema: ' + str(kind))
                continue
            item = event.get('item', {}); kind = item.get('type')
            if kind in ('agent_message', 'reasoning', 'todo_list'):
                continue
            if kind != 'mcp_tool_call' or item.get('server') != 'candidate_access':
                failures.append('unobserved exec tool item: ' + str(kind)); continue
            identifier = item.get('id')
            if not isinstance(identifier, str) or not identifier:
                failures.append('exec tool item identity unavailable'); continue
            if event['type'] == 'item.started':
                if identifier in started_items: failures.append('duplicate exec tool start')
                if (item.get('status') != 'in_progress' or item.get('result') is not None
                        or item.get('error') is not None):
                    failures.append('unknown exec tool start')
                started_items[identifier] = item
            if event['type'] == 'item.updated':
                start_item = started_items.get(identifier, {})
                if (identifier not in started_items or identifier in completed_items
                        or any(not same(start_item.get(key), item.get(key))
                               for key in ('server', 'tool', 'arguments'))
                        or item.get('status') != 'in_progress'
                        or item.get('result') is not None or item.get('error') is not None):
                    failures.append('unknown exec tool update')
            if event['type'] == 'item.completed':
                if identifier in completed_items or identifier not in started_items: failures.append('exec tool pairing unavailable')
                completed_items.add(identifier)
                start_item = started_items.get(identifier, {})
                if any(not same(start_item.get(key), item.get(key)) for key in ('server', 'tool', 'arguments')):
                    failures.append('exec tool start differs from terminal')
                end = ends[len(emitted)] if len(emitted) < len(ends) else {}
                content = (item.get('result') or {}).get('content', [])
                status = 'failed' if end.get('is_error') is True else 'completed'
                if (item.get('status') != status or item.get('error') is not None or len(content) != 1
                        or content[0].get('type') != 'text' or not same(strict_json(content[0]['text']), end.get('result'))):
                    failures.append('exec result differs from broker journal')
                arguments = item.get('arguments')
                if isinstance(arguments, str): arguments = strict_json(arguments)
                emitted.append((item.get('tool'), arguments))
        if set(started_items) != completed_items or not same(emitted, expected):
            failures.append('exec access trace differs from broker journal')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, RecursionError) as exc:
        failures.append('unknown access trace: ' + str(exc))
    return {'complete': not failures, 'issues': sorted(set(failures)), 'observed_tools': len(nested) if gateway else len(calls),
            'scope': 'paired scoped broker access observations; origin, resources and enforcement are separate'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal', required=True, type=Path)
    parser.add_argument('--stdout', required=True, type=Path)
    parser.add_argument('--rollout', required=True, action='append', type=Path,
                        help='retained rollout, repeat in observed order')
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--profile-sha256', required=True)
    args = parser.parse_args(argv)
    if not re.fullmatch(r'[0-9a-f]{64}', args.profile_sha256):
        parser.error('--profile-sha256 requires a lowercase SHA-256 digest')
    report = access_audit(args.rollout, args.journal, args.workspace,
                          args.profile_sha256, args.stdout)
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0 if report['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
