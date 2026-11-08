"""Independent bounded, child-free review. Run with -B, and separately -B -O."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANDIDATE = HERE.parent / 'cache-deadline-control-fix'
MODE = 'optimized' if sys.flags.optimize else 'normal'
START = time.monotonic()
DENIALS = []
sys.dont_write_bytecode = True


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def audit(event, args):
    if event in {'subprocess.Popen', 'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn',
                 'os.kill', 'os.killpg', 'os.exec', 'pty.spawn'} or event.startswith('socket.'):
        DENIALS.append(event)
        raise RuntimeError('Review forbids process/network action: ' + event)
    paths = []
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            paths = [(args[0], -1)]
    elif event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod'}:
        paths = [(args[0], args[-1] if isinstance(args[-1], int) else -1)]
    elif event == 'os.rename':
        paths = [(args[0], args[2]), (args[1], args[3])]
    elif event in {'os.link', 'os.symlink'}:
        paths = [(args[1], args[-1] if isinstance(args[-1], int) else -1)]
    for name, directory_fd in paths:
        if isinstance(name, int):
            continue
        path = Path(os.fsdecode(name))
        # shutil.rmtree uses descriptors opened only for our guarded scratch.
        if not path.is_absolute() and directory_fd != -1:
            continue
        if not path.resolve().is_relative_to(HERE):
            DENIALS.append(event + ':' + str(path))
            raise RuntimeError('Review write outside ownership: ' + str(path))


sys.addaudithook(audit)
sys.path.insert(0, str(CANDIDATE))
import local_support as support
import control_source
import adopt_fixture as adoption
import deadline_control

# The inspected original import chain only defines functions/classes/constants.
# A stronger review guard above replaces the candidate's namespace-only guard.
support.write_guard = lambda: None
original_workspace = support.workspace


def workspace(label, source):
    with mock.patch.object(support, 'HERE', HERE):
        return original_workspace('review-' + MODE + '-' + label, source)


support.workspace = workspace
import test_contracts as contracts


class LimitedStream(io.StringIO):
    def write(self, text):
        need(self.tell() + len(text.encode()) <= 500000, 'Review output cap reached')
        return super().write(text)


capture = LimitedStream()
result = {'mode': MODE, 'python': sys.version, 'executable': sys.executable,
          'executable_sha256': sha(Path(sys.executable).resolve()),
          'uname': list(os.uname()), 'argv': sys.argv,
          'source_revision': 'e7254f3703d5b8191aa72ec2fb11fa91b5ea99ba',
          'source_tree': '482fb5b41a203edfd517627b0e014d31eb7f02e2',
          'scope': 'No subprocess, compiler, native, UI, network, or process/group probe. Real SIGALRM only in own interpreter.'}
inputs = json.loads((CANDIDATE / 'old-inputs-before.json').read_bytes())['members']
need(len(inputs) == 163, 'Expected all 163 historical inputs')


def audit_inputs():
    mismatches = []
    for row in inputs:
        path = ROOT / row['path']
        if path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            mismatches.append(row['path'])
    need(not mismatches, 'Historical changes: ' + str(mismatches))
    return {'count': len(inputs), 'mismatches': mismatches,
            'roster_sha256': sha(CANDIDATE / 'old-inputs-before.json')}


result['historical_before'] = audit_inputs()
manifest = json.loads((CANDIDATE / 'sources.json').read_bytes())
for row in manifest['members']:
    need(sha(CANDIDATE / row['path']) == row['sha256'] and
         (CANDIDATE / row['path']).stat().st_size == row['bytes'], 'Shipping hash ' + row['path'])
result['shipping'] = manifest
result['source_manifest_sha256'] = sha(CANDIDATE / 'sources.json')
result['held_receipt_sha256'] = sha(HERE.parent / 'cache-deadline-custody-hold/receipt.json')
source_before, source_after = support.original_source(), control_source.control_source()


def method_bytes(source):
    lines = source.splitlines(keepends=True)
    owner = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == 'RunnerControls')
    return {n.name: b''.join(lines[n.lineno - 1:n.end_lineno]) for n in owner.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}


before, after = method_bytes(source_before), method_bytes(source_after)
need(len(before) == 36 and before == after, 'Test methods changed')
result['methods'] = {name: hashlib.sha256(body).hexdigest() for name, body in after.items()}
result['adoption'] = adoption.verify()
excluded = {
    'test_checks_active_under_optimized_python',
    'test_missing_and_failed_commands_keep_raw_receipts',
    'test_timeout_owned_child_group_and_output_cap',
    'test_owned_descendant_group_is_stopped',
    'test_every_child_gets_owned_default_temporary_directory',
    'test_fixture_temporary_override_stays_inside_owned_scratch',
}
need(excluded <= before.keys(), 'Explicit exclusion roster differs')
subject, destination = workspace('selected', source_after)
selected = sorted(before.keys() - excluded)
suite = unittest.TestSuite(subject.RunnerControls(name) for name in selected)
with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
    selected_result = unittest.TextTestRunner(stream=capture, verbosity=2).run(suite)
    contract_result = unittest.TextTestRunner(stream=capture, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(contracts.Contracts))
result['selected_controls'] = {'names': selected, 'excluded_real_child_tests': sorted(excluded),
                               'ran': selected_result.testsRun, 'passed': selected_result.wasSuccessful()}
result['contracts'] = {'ran': contract_result.testsRun, 'passed': contract_result.wasSuccessful()}
need(selected_result.wasSuccessful() and contract_result.wasSuccessful(), 'Selected/contract suite failed')

# Independent two-stage discrimination: delayed terminal processing must pass;
# disabled actual timer, resumed hook work, and deleted scratch must all fail.
helper = (CANDIDATE / 'deadline_control.py').read_text()
mutations = {
    'delayed-terminal': ("        return original_timer(which, seconds, interval)\n",
        "        if seconds == 0 and any(e['event'] == 'handler-raise' for e in events):\n"
        "            events.append({'event': 'review-terminal-delay', 'seconds': .16, 'wall': time.monotonic()})\n"
        "            time.sleep(.16)\n"
        "        return original_timer(which, seconds, interval)\n", True),
    'timer-disabled': ('        original_timer(signal.ITIMER_REAL, seconds)\n',
                       '        original_timer(signal.ITIMER_REAL, 0)\n', False),
    'continued-work': ('                    return handler(number, frame)\n',
        "                    try:\n                        return handler(number, frame)\n"
        "                    finally:\n                        state['after_delay'] = True\n", False),
    'scratch-deleted': ('                    return handler(number, frame)\n',
        "                    try:\n                        return handler(number, frame)\n"
        "                    finally:\n                        runner.shutil.rmtree(out / 'scratch')\n", False),
}
result['independent_cases'] = []
for label, (needle, replacement, expected) in mutations.items():
    need(helper.count(needle) == 1, 'Unique mutation site ' + label)
    altered = helper.replace(needle, replacement, 1)
    module = types.ModuleType('independent_' + label)
    exec(compile(altered, str(HERE / ('mutation-' + label + '.py')), 'exec'), module.__dict__)
    (HERE / ('mutation-' + label + '.py')).write_text(altered)
    for stage in ['postflight', 'retention']:
        case = subject.RunnerControls('test_' + stage + '_deadline_is_terminal_and_preserves_scratch')
        case.setUp()
        evidence = destination / (label + '-' + stage)
        evidence.mkdir()
        error = None
        try:
            with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
                module.run(case, subject.r, evidence, stage)
        except RuntimeError as failure:
            error = str(failure)
        finally:
            case.tearDown()
        raw = json.loads((evidence / 'logs' / ('deadline-' + stage + '-control.json')).read_bytes())
        need((error is None) == expected, 'Unexpected outcome ' + label + '-' + stage)
        need(raw['spawn_calls'] == 0 and raw['timer_disarmed'] and raw['handlers_restored'], 'Unsafe terminal state')
        result['independent_cases'].append({'label': label, 'stage': stage, 'accepted': error is None,
            'expected_acceptance': expected, 'error': error,
            'receipt': str((evidence / 'logs' / ('deadline-' + stage + '-control.json')).relative_to(HERE)),
            'test_scratch_removed': not case.base.exists()})

result['historical_after'] = audit_inputs()
need(result['source_manifest_sha256'] == sha(CANDIDATE / 'sources.json'), 'Candidate seal drift')
need(result['held_receipt_sha256'] == sha(HERE.parent / 'cache-deadline-custody-hold/receipt.json'), 'Hold receipt drift')
need(not DENIALS, 'Attempted forbidden actions: ' + str(DENIALS))
result['denied_actions'] = DENIALS
result['timer_disarmed'] = signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
result['elapsed_seconds'] = time.monotonic() - START
result['captured_output_bytes'] = len(capture.getvalue().encode())
(HERE / ('controls-' + MODE + '.log')).write_text(capture.getvalue())
result['successful'] = True
save(HERE / ('controls-' + MODE + '.json'), result)
print(json.dumps({'mode': MODE, 'selected': len(selected), 'contracts': contract_result.testsRun,
                  'independent_cases': len(result['independent_cases']), 'successful': True,
                  'output_bytes': result['captured_output_bytes'], 'elapsed_seconds': result['elapsed_seconds']}))
