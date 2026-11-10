"""R191: in-process output/custody controls; never launch a child or signal OS IDs."""
import ast
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import unittest
from types import ModuleType

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
TEST = ROOT / 'scripts/ci/tests/test_android_generated_java_runner.py'
CHECKER = ROOT / 'scripts/ci/check-android-generated-java.py'
START = time.monotonic()
RUNS = OUT / ('runs-' + str(time.time_ns()))


def forbid_processes(event, args):
    if (event.startswith('subprocess.') or event in
            ('os.kill', 'os.killpg', 'os.system', 'os.fork', 'os.forkpty',
             'os.posix_spawn', 'os.posix_spawnp', 'pty.spawn')):
        raise AssertionError('R191 forbids actual process operations: ' + event)


sys.addaudithook(forbid_processes)
spec = importlib.util.spec_from_file_location('r191_canonical_controls', TEST)
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
M = T.M
baseline = TEST.read_text()
results = []


class ReadyBytes(T.FakeCommandBoundary):
    """All bytes are already readable; a ready select does not spend its timeout."""
    def selector(self):
        selected = super().selector()
        original_select = selected.select
        selected.select = lambda timeout=None: original_select(0)
        return selected


def case_root(name):
    path = RUNS / name
    path.mkdir(parents=True, exist_ok=False)
    return path


def check(record, *, terminal):
    assert record['logs']['stdout']['bytes'] == M.JAVAP_STDOUT_BYTES
    assert record['stop'] == 'output-limit'
    assert record['terminal_custody'] is terminal


# Execute the exact original test, retaining every original assertion.
root = case_root('original-test-ready-cleanup')
control = T.RunnerControls('test_javap_stdout_ceiling_refuses_one_extra_byte_without_silent_success')
control.root = root
with ReadyBytes(root, stdout=b'x' * (M.JAVAP_STDOUT_BYTES + 1)) as boundary:
    control.test_javap_stdout_ceiling_refuses_one_extra_byte_without_silent_success()
    record = json.loads((root / 'commands.json').read_text())[0]
    check(record, terminal=True)
    assert len(boundary.children) == 1 and boundary.children[0].pid < 0
    assert record['descriptors_closed'] and not M._COMMAND_OWNERS and not M._PROCESS_OWNERS
results.append({'case': root.name, 'result': 'pass', 'stop': record['stop'],
                'terminal_custody': True, 'fake_pid': record['pid']})

root = case_root('exact-ceiling-success')
with ReadyBytes(root, stdout=b'x' * M.JAVAP_STDOUT_BYTES):
    commands = M.Commands(root, {}, seconds=15, command_seconds=2)
    output = commands.run('exact-ceiling', ['synthetic-only'], stdout_bytes=M.JAVAP_STDOUT_BYTES)
    assert output == 'x' * M.JAVAP_STDOUT_BYTES
    control.root = root
    control.terminal_record(commands.records[0])
    assert commands.records[0]['stop'] is None
results.append({'case': root.name, 'result': 'pass', 'terminal_custody': True})

# Same overflow, independent cleanup failures. UNKNOWN must outrank output-limit.
for name, options, operation in (
        ('denied-observation', {'observation': 'denied'}, 'observe-owned-group'),
        ('denied-signal', {'denied_signal': True}, 'signal-owned-group'),
        ('reap-failure', {'reap_error': True}, 'reap-direct-child'),
        ('pipe-close-failure', {'pipe_close_error': True}, 'close-stdout'),
        ('selector-close-failure', {'selector_close_error': True}, 'close-selector')):
    root = case_root(name)
    with ReadyBytes(root, stdout=b'x' * (M.JAVAP_STDOUT_BYTES + 1), **options) as boundary:
        commands = M.Commands(root, {}, seconds=15, command_seconds=2)
        try:
            try:
                commands.run('javap-budget-overflow', ['synthetic-only'],
                             stdout_bytes=M.JAVAP_STDOUT_BYTES)
            except RuntimeError as error:
                message = str(error)
            else:
                raise AssertionError('overflow silently succeeded')
            assert message == 'javap-budget-overflow: terminal custody unknown or cleanup failed'
            record = commands.records[0]
            check(record, terminal=False)
            assert [e['operation'] for e in record['cleanup_errors']] == [operation]
            assert not commands.custody_terminal() and commands.hold
            assert M._COMMAND_OWNERS and M._PROCESS_OWNERS
            count = len(boundary.children)
            try:
                commands.run('forbidden-followup', ['synthetic-only'])
            except RuntimeError as error:
                assert 'Sticky inner custody hold' in str(error)
            else:
                raise AssertionError('UNKNOWN allowed another command')
            assert len(boundary.children) == count
            assert json.loads((root / 'commands.json').read_text())[0] == record
            results.append({'case': name, 'result': 'pass', 'error': message,
                            'stop': record['stop'], 'cleanup_operation': operation,
                            'terminal_custody': False, 'fake_pid': record['pid']})
        finally:
            boundary.cleanup_markers()

# Minimal proposed canonical change: opt into already-ready synthetic bytes only
# for this budget control, without changing any production code or clock limits.
proposed = baseline.replace(
    '                 pipe_close_error=False, selector_close_error=False):',
    '                 pipe_close_error=False, selector_close_error=False, ready_output=False):', 1)
proposed = proposed.replace('        self.stdout = stdout\n',
                            '        self.stdout = stdout\n        self.ready_output = ready_output\n', 1)
proposed = proposed.replace('                boundary.now += timeout or 0\n',
    '                if not boundary.ready_output:\n                    boundary.now += timeout or 0\n', 1)
tree = ast.parse(proposed)
method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and
    n.name == 'test_javap_stdout_ceiling_refuses_one_extra_byte_without_silent_success')
lines = proposed.splitlines(keepends=True)
old_method = ''.join(lines[method.lineno - 1:method.end_lineno])
new_method = '''    def test_javap_stdout_ceiling_refuses_one_extra_byte_without_silent_success(self):
        # Budget refusal has deterministic bytes and independently proven fake custody.
        with FakeCommandBoundary(self.root, stdout=b'x' * (M.JAVAP_STDOUT_BYTES + 1),
                                 ready_output=True):
            commands = M.Commands(self.root, os.environ.copy(), seconds=15, command_seconds=2)
            with self.assertRaisesRegex(RuntimeError, 'output-limit'):
                commands.run('javap-budget-overflow', ['synthetic-javap-output'],
                             stdout_bytes=M.JAVAP_STDOUT_BYTES)
            record = commands.records[-1]
            self.assertEqual(record['logs']['stdout']['bytes'], M.JAVAP_STDOUT_BYTES)
            self.assertEqual(record['stop'], 'output-limit')
            self.terminal_record(record)

    def test_javap_overflow_unknown_custody_still_takes_priority(self):
        with FakeCommandBoundary(self.root, stdout=b'x' * (M.JAVAP_STDOUT_BYTES + 1),
                                 observation='denied', ready_output=True) as boundary:
            commands = M.Commands(self.root, os.environ.copy(), seconds=15, command_seconds=2)
            try:
                with self.assertRaisesRegex(RuntimeError, 'terminal custody unknown or cleanup failed'):
                    commands.run('javap-budget-overflow', ['synthetic-javap-output'],
                                 stdout_bytes=M.JAVAP_STDOUT_BYTES)
                record = commands.records[-1]
                self.assertEqual(record['logs']['stdout']['bytes'], M.JAVAP_STDOUT_BYTES)
                self.assertEqual(record['stop'], 'output-limit')
                self.assertTrue(record['direct_child_reaped'])
                self.assertTrue(record['stdout_eof'] and record['stderr_eof'])
                self.assertFalse(record['owned_group_absent'])
                self.assertFalse(record['descriptors_closed'])
                self.assertFalse(record['terminal_custody'])
                self.assertFalse(commands.custody_terminal())
                self.assertIsNotNone(commands.hold)
                self.assertEqual(record['group_observation']['outcome'], 'denied')
                self.assertEqual([e['operation'] for e in record['cleanup_errors']],
                                 ['observe-owned-group'])
                self.assertEqual(json.loads((self.root / 'commands.json').read_text())[-1], record)
                with self.assertRaisesRegex(RuntimeError, 'Sticky inner custody hold'):
                    commands.run('no-followup', ['synthetic-only'])
                self.assertEqual(len(boundary.children), 1)
            finally:
                boundary.cleanup_markers()
'''
assert proposed.count(old_method) == 1
proposed = proposed.replace(old_method, new_method, 1)
ast.parse(proposed)
(OUT / 'proposed-test-only.patch').write_text(''.join(difflib.unified_diff(
    baseline.splitlines(keepends=True), proposed.splitlines(keepends=True),
    fromfile='a/scripts/ci/tests/test_android_generated_java_runner.py',
    tofile='b/scripts/ci/tests/test_android_generated_java_runner.py')))

# Execute proposed source entirely in memory. No canonical file is changed.
namespace = {'__file__': str(TEST), '__name__': 'r191_proposed_controls'}
exec(compile(proposed, str(TEST), 'exec'), namespace)
P = namespace['RunnerControls']
for name in (
        'test_javap_stdout_ceiling_refuses_one_extra_byte_without_silent_success',
        'test_javap_overflow_unknown_custody_still_takes_priority',
        'test_invalid_stdout_budgets_fail_before_spawning',
        'test_denied_signal_retains_receipt_even_after_child_exits',
        'test_denied_or_unknown_group_observation_cannot_pass',
        'test_live_child_denied_cleanup_still_persists_unknown_terminal_facts',
        'test_one_stream_read_error_cannot_be_reported_as_eof',
        'test_nested_reap_and_selector_cleanup_errors_still_persist',
        'test_command_receipt_write_failure_retains_in_memory_facts',
        'test_exited_fake_parent_with_inherited_pipes_cannot_hang_runner'):
    control = P(name)
    control.root = case_root('proposed-' + name)
    getattr(control, name)()
    results.append({'case': 'proposed:' + name, 'result': 'pass'})

# Mutation checks prove the proposed controls still reject the two relevant
# regressions. These checkers exist only as Python objects in this interpreter.
checker_source = CHECKER.read_text()
terminal_guard = "        require(record['terminal_custody'], label + ': terminal custody unknown or cleanup failed')\n"
stop_guard = "        require(record['stop'] is None, label + ': ' + str(record['stop']))\n"
for label, source, name in (
        ('ceiling-plus-one', checker_source.replace(
            "        require(len(self.records) < 160, 'Command count budget exhausted')",
            "        stream_limits['stdout'] += 1\n        require(len(self.records) < 160, 'Command count budget exhausted')", 1),
         'test_javap_stdout_ceiling_refuses_one_extra_byte_without_silent_success'),
        ('output-before-custody', checker_source.replace(
            terminal_guard + stop_guard, stop_guard + terminal_guard, 1),
         'test_javap_overflow_unknown_custody_still_takes_priority')):
    assert source != checker_source
    mutant = ModuleType('r191_mutant_' + label)
    mutant.__file__ = str(CHECKER)
    exec(compile(source, str(CHECKER), 'exec'), mutant.__dict__)
    namespace['M'] = mutant
    control = P(name)
    control.root = case_root('mutant-' + label)
    try:
        getattr(control, name)()
    except AssertionError as error:
        results.append({'case': 'mutation:' + label, 'result': 'correctly rejected',
                        'assertion': str(error)})
    else:
        raise AssertionError('proposed control missed mutation: ' + label)
namespace['M'] = M

assert TEST.read_text() == baseline
receipt = {'scope': 'source-only synthetic controls; no hosted OS diagnosis',
    'source_revision_supplied_by_root': 'cff82c2d2db402aaabbea17569c5856f7d08bf82',
    'source116_supplied_by_root': '306221cc4d05bfd448deb5674162d1a79469ded6c047325eaf80df49c237187f',
    'python': sys.version, 'platform': list(os.uname()),
    'command': 'python3 -B verification/plan-continuation-2026-11-07/javap-output-limit-source-controls-r191/controls.py',
    'source_files': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (TEST, CHECKER)},
    'canonical_unchanged': True, 'audit_rejects_actual_process_operations': True,
    'actual_child_count': 0, 'results': results,
    'run_directory': str(RUNS),
    'elapsed_seconds': time.monotonic() - START}
# Compact only this lane's known synthetic stream files; command receipts retain
# their byte counts and digests. No live or held process resources exist here.
removed = []
for run_root in OUT.glob('runs*'):
    assert run_root.is_dir() and not run_root.is_symlink()
    for stream in run_root.glob('*/*.stdout'):
        assert stream.is_relative_to(OUT) and not stream.is_symlink()
        size = stream.stat().st_size
        if size > 1024:
            removed.append({'path': str(stream.relative_to(OUT)), 'bytes': size})
            stream.unlink()
receipt['cleanup'] = {'scope': 'owned synthetic stdout only; digests retained in commands.json',
                      'removed_streams': removed, 'bytes_removed': sum(p['bytes'] for p in removed),
                      'real_process_resources': 'none'}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'passed': len(results), 'elapsed_seconds': receipt['elapsed_seconds'],
                  'receipt': str(OUT / 'receipt.json')}))
