"""Portable three-view capture regressions; no provider or private fixtures."""
import copy
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
import access_capture
from attempt import canonical, strict_json


def rechain(log):
    previous = None
    for index, row in enumerate(log):
        row.update(seq=index, previous=previous)
        previous = hashlib.sha256(canonical(row).encode()).hexdigest()


def response(payload):
    return {'type': 'response_item', 'payload': payload}


def host_output(call, text, kind='custom_tool_call_output'):
    return response({'type': kind, 'call_id': call, 'output': text})


def header(cell=None):
    state = 'Script completed' if cell is None else 'Script running with cell ID ' + cell
    return state + '\nWall time 0.25 seconds\nOutput:\n'


def fixture(workspace, mode='sync', missing=False):
    tool = 'read' if missing else 'files'
    args = {'path': 'absent/file.txt'} if missing else {}
    result = {'error': str(FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                           str(workspace / args['path'])))} if missing else {'files': ['a.py']}
    log = [{'event': 'broker.started', 'workspace': str(workspace), 'profile_sha256': 'a' * 64},
           {'event': 'tool.started', 'call_id': 1, 'tool': tool, 'arguments': args},
           {'event': 'tool.completed', 'call_id': 1, 'tool': tool, 'is_error': missing, 'result': result},
           {'event': 'broker.closed'}]
    rechain(log)
    nested = {'type': 'McpToolCall', 'id': 'nested-1', 'server': 'candidate_access',
              'tool': tool, 'arguments': args, 'status': 'failed' if missing else 'completed',
              'result': {'isError': missing, 'content': [{'type': 'text', 'text': json.dumps(result)}]}}
    event = {'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': nested}}
    if mode == 'direct':
        rollout = [response({'type': 'function_call', 'name': 'mcp__candidate_access__' + tool,
                             'call_id': 'direct-1', 'arguments': json.dumps(args)})]
    else:
        rollout = [response({'type': 'custom_tool_call', 'name': 'exec', 'call_id': 'exec-1',
                             'input': 'await tools.mcp__candidate_access__files({});'})]
        if mode == 'yield':
            rollout += [host_output('exec-1', header('7')), event]
            for index, cell in enumerate(('7', None)):
                call = 'wait-' + str(index)
                rollout += [response({'type': 'function_call', 'name': 'wait', 'call_id': call,
                                      'arguments': json.dumps({'cell_id': '7', 'max_tokens': 100})}),
                            host_output(call, header(cell), 'function_call_output')]
        else:
            rollout += [event, host_output('exec-1', header())]
    cli_item = copy.deepcopy(nested)
    cli_item.update(type='mcp_tool_call', id='item-1', error=None)
    start = copy.deepcopy(cli_item)
    start.update(status='in_progress', result=None)
    cli = [{'type': 'item.started', 'item': start}, {'type': 'item.completed', 'item': cli_item}]
    return copy.deepcopy((rollout, log, cli))


class AccessCapture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def retain(self, data):
        paths = [self.root / name for name in ('rollout.jsonl', 'journal.jsonl', 'stdout.jsonl')]
        for path, stream in zip(paths, data):
            path.write_text(''.join(json.dumps(event) + '\n' for event in stream))
        return paths

    def audit(self, data):
        roll, log, cli = self.retain(data)
        return access_capture.access_audit([roll], log, self.root, 'a' * 64, cli)

    def reject(self, data):
        report = self.audit(data)
        self.assertFalse(report['complete'], report)
        self.assertTrue(report['issues'], report)

    def test_synchronous_yielded_repeated_wait_and_direct(self):
        for mode in ('sync', 'yield', 'direct'):
            with self.subTest(mode=mode):
                result = self.audit(fixture(self.root, mode))
                self.assertTrue(result['complete'], result)
                self.assertEqual(result['observed_tools'], 1)

    def test_exact_missing_read_is_captured_failure(self):
        for mode in ('sync', 'yield', 'direct'):
            with self.subTest(mode=mode):
                result = self.audit(fixture(self.root, mode, missing=True))
                self.assertTrue(result['complete'], result)

    def test_multi_block_host_output(self):
        data = fixture(self.root, 'yield')
        for index in (1, 4, 6):
            data[0][index]['payload']['output'] = [
                {'type': 'input_text', 'text': data[0][index]['payload']['output']},
                {'type': 'input_text', 'text': 'retained output body'}]
        result = self.audit(data)
        self.assertTrue(result['complete'], result)
        data[0][-1]['payload']['output'][1]['type'] = 'unknown'
        self.reject(data)

    def test_pending_terminal_required(self):
        data = fixture(self.root, 'yield')
        data[0][-1]['payload']['output'] = header('7')
        self.reject(data)

    def test_wait_arguments(self):
        for change in ({'cell_id': '8'}, {'cell_id': 7}, {'terminate': True},
                       {'max_tokens': True}, {'max_tokens': 0}, {'max_tokens': {}},
                       {'yield_time_ms': -1}, {'yield_time_ms': True}, {'extra': 1}):
            with self.subTest(change=change):
                data = fixture(self.root, 'yield')
                payload = data[0][3]['payload']
                args = json.loads(payload['arguments']); args.update(change)
                payload['arguments'] = json.dumps(args)
                self.reject(data)

    def test_lifecycle_headers(self):
        for output in ('Script completed\n', 'unknown', 'Script running with cell ID x\n',
                       'Script completed\nWall time .. seconds\nOutput:\n'):
            for index in (1, 4, 6):
                with self.subTest(output=output, index=index):
                    data = fixture(self.root, 'yield')
                    data[0][index]['payload']['output'] = output
                    self.reject(data)

    def test_missing_duplicate_orphan_and_wrong_gateway_outputs(self):
        for mode in ('missing', 'duplicate', 'orphan', 'type'):
            data = fixture(self.root)
            if mode == 'missing': data[0].pop()
            if mode == 'duplicate': data[0].append(copy.deepcopy(data[0][-1]))
            if mode == 'orphan': data[0][-1]['payload']['call_id'] = 'unknown'
            if mode == 'type': data[0][-1]['payload']['type'] = 'function_call_output'
            self.reject(data)

    def test_nested_corruptions(self):
        for mode in ('missing', 'extra', 'native', 'arguments', 'result', 'status', 'flag', 'identity'):
            data = fixture(self.root)
            item = data[0][1]['payload']['item']
            if mode == 'missing': data[0].pop(1)
            if mode == 'extra': data[0].insert(1, copy.deepcopy(data[0][1]))
            if mode == 'native': item['type'] = 'CommandExecution'
            if mode == 'arguments': item['arguments'] = {'path': 'other'}
            if mode == 'result': item['result']['content'][0]['text'] = '{}'
            if mode == 'status': item['status'] = 'failed'
            if mode == 'flag': item['result']['isError'] = True
            if mode == 'identity': item['id'] = ''
            self.reject(data)

    def test_cli_start_terminal_corruptions(self):
        for mode in ('start', 'missing', 'duplicate', 'result', 'native', 'status', 'error'):
            data = fixture(self.root)
            item = data[2][1]['item']
            if mode == 'start': data[2][0]['item']['arguments'] = {'path': 'other'}
            if mode == 'missing': data[2].pop()
            if mode == 'duplicate': data[2].append(copy.deepcopy(data[2][-1]))
            if mode == 'result': item['result']['content'][0]['text'] = '{}'
            if mode == 'native': item['type'] = 'command_execution'
            if mode == 'status': item['status'] = 'failed'
            if mode == 'error': item['error'] = {'message': 'unknown'}
            self.reject(data)

    def test_journal_integrity_scope_and_membership(self):
        for mode in ('hash', 'seq-type', 'scope', 'profile', 'missing', 'terminal', 'flag'):
            data = fixture(self.root)
            if mode == 'hash': data[1][1]['previous'] = 'altered'
            if mode == 'seq-type': data[1][1]['seq'] = True; rechain(data[1]); data[1][1]['seq'] = True
            if mode == 'scope': data[1][0]['workspace'] = '/workspace/other'; rechain(data[1])
            if mode == 'profile': data[1][0]['profile_sha256'] = 'b' * 64; rechain(data[1])
            if mode == 'missing': data[1].pop(2); rechain(data[1])
            if mode == 'terminal': data[1].pop()
            if mode == 'flag': data[1][2]['is_error'] = 0; rechain(data[1])
            self.reject(data)

    def test_missing_read_denied_paths_and_unknown_errors(self):
        for path, error in (('../private.txt', None), ('/private.txt', None), ('a//b', None),
                            ('./file', None), ('absent/file.txt', 'permission denied')):
            data = fixture(self.root, missing=True)
            args = {'path': path}
            result = {'error': error or str(FileNotFoundError(2, os.strerror(2), str(self.root / path)))}
            data[1][1]['arguments'] = args; data[1][2]['result'] = result; rechain(data[1])
            data[0][1]['payload']['item'].update(arguments=args)
            data[0][1]['payload']['item']['result']['content'][0]['text'] = json.dumps(result)
            for row in data[2]: row['item']['arguments'] = args
            data[2][1]['item']['result']['content'][0]['text'] = json.dumps(result)
            self.reject(data)

    def test_missing_read_symlink_and_cross_view_mismatch(self):
        (self.root / 'absent').symlink_to(self.root / 'outside')
        self.reject(fixture(self.root, missing=True))
        (self.root / 'absent').unlink()
        for stream in (0, 2):
            data = fixture(self.root, missing=True)
            item = data[0][1]['payload']['item'] if stream == 0 else data[2][1]['item']
            item['result']['content'][0]['text'] = '{"error":"altered"}'
            self.reject(data)

    def test_unknown_native_and_mixed_modes(self):
        for payload in ({'type': 'function_call', 'name': 'exec_command', 'arguments': '{}', 'call_id': 'native'},
                        {'type': 'function_call', 'name': 'mcp__candidate_access__files', 'arguments': '{}', 'call_id': 'direct'},
                        {'type': 'future_tool'}):
            data = fixture(self.root); data[0].append(response(payload)); self.reject(data)

    def test_direct_duplicate_identity_and_wrong_call_type(self):
        data = fixture(self.root, 'direct')
        second_start, second_end = copy.deepcopy(data[1][1:3])
        second_start['call_id'] = second_end['call_id'] = 2
        data[1][3:3] = [second_start, second_end]; rechain(data[1])
        second_cli = copy.deepcopy(data[2])
        for event in second_cli: event['item']['id'] = 'item-2'
        data[2].extend(second_cli)
        data[0].append(copy.deepcopy(data[0][0]))
        self.reject(data)
        data = fixture(self.root, 'direct')
        data[0][0]['payload']['type'] = 'custom_tool_call'
        self.reject(data)

    def test_direct_outputs_match_or_reject(self):
        data = fixture(self.root, 'direct')
        wrapper = data[2][1]['item']['result']
        output = response({'type': 'function_call_output', 'call_id': 'direct-1',
                           'output': json.dumps(wrapper)})
        data[0].append(output)
        self.assertTrue(self.audit(data)['complete'])
        for mode in ('orphan', 'duplicate', 'result'):
            variant = copy.deepcopy(data)
            if mode == 'orphan': variant[0][-1]['payload']['call_id'] = 'orphan'
            if mode == 'duplicate': variant[0].append(copy.deepcopy(output))
            if mode == 'result': variant[0][-1]['payload']['output'] = '{}'
            self.reject(variant)

    def test_journal_identity_types(self):
        for value in (True, 1.0, None):
            data = fixture(self.root)
            data[1][2]['call_id'] = value; rechain(data[1])
            self.reject(data)

    def test_cli_updates_reconcile_live_start(self):
        data = fixture(self.root)
        update = {'type': 'item.updated', 'item': copy.deepcopy(data[2][0]['item'])}
        data[2].insert(1, update)
        self.assertTrue(self.audit(data)['complete'])
        for field, value in (('id', 'unknown'), ('tool', 'unknown_tool'), ('arguments', {'unknown': 1}),
                             ('status', 'failed'), ('result', {}), ('error', {})):
            variant = copy.deepcopy(data)
            variant[2][1]['item'][field] = value
            self.reject(variant)

    def test_cli_start_schema(self):
        for field, value in (('status', 'unknown_lifecycle'), ('error', {'message': 'denied'}),
                             ('result', {'unknown': 'schema'})):
            data = fixture(self.root)
            data[2][0]['item'][field] = value
            self.reject(data)

    def test_broker_argument_value_types_in_all_views(self):
        for mode in ('sync', 'direct'):
            data = fixture(self.root, mode)
            data[1][1].update(tool='read', arguments={'path': 1}); data[1][2]['tool'] = 'read'
            rechain(data[1])
            for event in data[2]: event['item'].update(tool='read', arguments={'path': 1})
            if mode == 'sync':
                data[0][1]['payload']['item'].update(tool='read', arguments={'path': 1})
            else:
                data[0][0]['payload'].update(name='mcp__candidate_access__read', arguments='{"path":1}')
            self.reject(data)

    def test_concurrent_gateway_and_changed_wait_cell(self):
        data = fixture(self.root, 'yield')
        second_exec = copy.deepcopy(data[0][0])
        second_exec['payload']['call_id'] = 'exec-2'
        data[0][2:2] = [second_exec, host_output('exec-2', header())]
        self.reject(data)
        data = fixture(self.root, 'yield')
        data[0][4]['payload']['output'] = header('8')
        self.reject(data)

    def test_strict_json_and_malformed_objects(self):
        for stream in (0, 1, 2):
            for bad in ('{"type":"ignored","type":"response_item"}', '{"v":NaN}', '{"v":1e999}', '[]'):
                paths = self.retain(fixture(self.root))
                paths[stream].write_text(bad + '\n')
                result = access_capture.access_audit([paths[0]], paths[1], self.root, 'a' * 64, paths[2])
                self.assertFalse(result['complete'], (stream, bad, result))
        for value in (-1, 2**63, 'quote " and newline\n', {'n': 0}):
            self.assertEqual(strict_json(canonical(value)), value)

    def test_missing_file_is_incomplete(self):
        self.retain(fixture(self.root))
        result = access_capture.access_audit([self.root / 'unavailable'], self.root / 'journal.jsonl',
                                            self.root, 'a' * 64, self.root / 'stdout.jsonl')
        self.assertFalse(result['complete'], result)

    def test_cli_report_and_exit_status(self):
        paths = self.retain(fixture(self.root, 'yield'))
        command = [sys.executable, '-B', str(LAB / 'access_capture.py'), '--journal', str(paths[1]),
                   '--stdout', str(paths[2]), '--rollout', str(paths[0]), '--workspace', str(self.root),
                   '--profile-sha256', 'a' * 64]
        valid = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertTrue(json.loads(valid.stdout)['complete'])
        paths[0].write_text('')
        invalid = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 1, invalid.stderr)
        self.assertFalse(json.loads(invalid.stdout)['complete'])


if __name__ == '__main__':
    unittest.main()
