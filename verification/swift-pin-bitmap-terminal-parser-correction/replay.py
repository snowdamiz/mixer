#!/usr/bin/env python3
"""Bounded pure-Python replay of retained bytes and corrupted evidence controls."""
import unittest.mock
import offline
offline.install()
import ast
import collections
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import time
from unittest import mock
import admit as a
import bounded_commands as b

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'swift-pin-bitmap-match-host-admission'
ACTUAL = HERE.parent / 'swift-pin-bitmap-match-actual-review/local/extract/_temp/pin-bitmap-lint-regression-v1-evidence'
RAW_SHA = 'a6fac84a9d0db5d198a8d479d08b48ed216486a050fe4d7298b53db5daa4e59c'
RECORDS = []

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def check(name, action, evidence=None):
    row = {'name': name}
    if evidence is not None:
        row['evidenceSHA256'] = sha(evidence.encode())
    try:
        result = action()
        row.update(passed=True, result=result)
    except BaseException as error:
        row.update(passed=False, error={'type': type(error).__name__, 'message': str(error)})
    RECORDS.append(row)

def refuse(text, subject=a):
    try:
        subject.test_evidence(text)
    except RuntimeError as error:
        return {'refused': True, 'message': str(error)}
    raise AssertionError('Malformed or contradictory evidence accepted')

def accept(text):
    result = a.test_evidence(text)
    assert set(result) == {'summaries', 'terminals', 'passed', 'ignored', 'nodeOracles', 'scope'}
    assert result['passed'] == len(result['terminals']) == 699 and result['ignored'] == 0
    assert result['nodeOracles'] == list(a.ORACLES)
    assert all(status == 'ok' for _, status in result['terminals'])
    return {'passed': result['passed'], 'groups': len(result['summaries']), 'terminals': len(result['terminals']),
            'terminalNamesSHA256': sha(('\n'.join(n for n, _ in result['terminals']) + '\n').encode()),
            'oracleCounts': {n: sum(name == n for name, _ in result['terminals']) for n in a.ORACLES}}

def summary(count):
    return f'test result: ok. {count} passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1s\n'

def group(names, capture=''):
    count = len(names)
    return f'running {count} ' + ('test' if count == 1 else 'tests') + '\n' + ''.join('test ' + n + ' ... ok\n' for n in names) + capture + summary(count)

def replace_once(text, old, new):
    assert old in text
    return text.replace(old, new, 1)

def unchanged_scope():
    old_text = (BASE / 'admit.py').read_text()
    new_text = (HERE / 'admit.py').read_text()
    old_tree, new_tree = ast.parse(old_text), ast.parse(new_text)
    old = {n.name: n for n in old_tree.body if isinstance(n, ast.FunctionDef)}
    new = {n.name: n for n in new_tree.body if isinstance(n, ast.FunctionDef)}
    assert old.keys() == new.keys()
    assert [n for n in old if ast.dump(old[n], include_attributes=False) != ast.dump(new[n], include_attributes=False)] == ['test_evidence']
    assert (BASE / 'bounded_commands.py').read_bytes() == (HERE / 'bounded_commands.py').read_bytes()
    assert ast.get_source_segment(new_text, new['test_evidence']) == (HERE / 'parser_function.py').read_text().rstrip()
    assert (a.ACTIVE_SECONDS, a.CLEANUP_SECONDS, b.MAX_COMMANDS, b.OUTPUT_CAP, b.AGGREGATE_OUTPUT_CAP) == (1800, 60, 6, 8388608, 33554432)
    return {'changedDefinitions': ['test_evidence'], 'helperByteIdentical': True}

def guarded():
    import signal
    import socket
    import subprocess
    import os
    assert subprocess.Popen is subprocess.run is offline.denied
    assert os.waitpid is os.setsid is os.killpg is os.setpgid is offline.denied
    assert signal.signal is signal.setitimer is offline.denied
    assert socket.socket is offline.denied
    assert b.resource.getrusage is offline.denied
    assert not offline.ATTEMPTS
    return {'beforeSubjectImports': True, 'realNestedCalls': 0}

def nonzero_command_exit():
    # Exercise the unchanged Commands.run exit guard using only in-memory fake
    # children/selectors. No OS child, session, group, signal, wait or timer call.
    class Process:
        pid = 111
        returncode = 101
        def __init__(self):
            self.stdout, self.stderr = io.BytesIO(), io.BytesIO()
        def poll(self): return self.returncode
        def wait(self, timeout): return self.returncode
    class Selector:
        def register(self, pipe, event, data):
            data['file'].close()
            pipe.close()
        def get_map(self): return {}
        def close(self): pass
    def stopped(proc, row):
        row.update(child_returned=True, owned_group_gone=True)
    usage = dict(ru_utime=0, ru_stime=0, ru_minflt=0, ru_majflt=0)
    directory = tempfile.mkdtemp(prefix='nonzero-', dir=HERE / 'local')
    try:
        c = b.Commands(Path(directory), {'commands': []}, time.monotonic() + 1000)
        with mock.patch.object(c, 'child_environment', return_value={}), mock.patch.object(c, 'gone', return_value=True), mock.patch.object(c, 'stop', side_effect=stopped), mock.patch.object(b, 'child_usage', return_value=usage), mock.patch.object(b.subprocess, 'Popen', return_value=Process()), mock.patch.object(b.selectors, 'DefaultSelector', return_value=Selector()):
            try:
                c.run('debug-regression', ['frozen-argv-placeholder'], HERE, seconds=600, accepted_exits=(0,))
            except RuntimeError as error:
                assert str(error).startswith('Command failed; retained receipt:')
                assert c.receipt['commands'][0]['exit'] == 101
                assert c.receipt['commands'][0]['accepted_exit_codes'] == [0]
                return {'mockExit': 101, 'refusedBeforeParser': True}
            raise AssertionError('Nonzero mocked command accepted')
    finally:
        work = Path(directory)
        for path in sorted(work.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if path.is_file() or path.is_symlink(): path.unlink()
            else: path.rmdir()
        work.rmdir()

def main():
    # The first mock-exit control left only files when TemporaryDirectory's
    # relative-dirfd cleanup hit the write guard. Preserve that setup evidence
    # as an inert archive and retire the fixture without weakening the guard.
    archived = []
    for path in (HERE / 'local').glob('nonzero-*'):
        row = b.json_data((path / 'commands/debug-regression.json').read_bytes())
        assert row['pid'] == row['pgid'] == 111 and row['argv'] == ['frozen-argv-placeholder']
        destination = HERE / 'local/setup-remnants' / path.name
        destination.parent.mkdir(exist_ok=True)
        assert not destination.exists()
        path.rename(destination)
        archived.append(str(destination.relative_to(HERE)))
    if archived:
        save(HERE / 'local/setup-cleanup.json', {'retainedMockFixtures': archived, 'liveProcessQueriesOrActions': 0})
    raw = (ACTUAL / 'commands/debug-regression.stdout').read_bytes()
    assert len(raw) == 3262384 and sha(raw) == RAW_SHA
    text = raw.decode('utf-8')
    command = b.json_data((ACTUAL / 'commands/debug-regression.json').read_bytes())
    assert command['exit'] == 0 and command['stdout_sha256'] == RAW_SHA
    assert command['accepted_exit_codes'] == [0] and not command['timed_out'] and not command['output_capped']
    assert command['child_returned'] and command['owned_group_gone'] and not command['custody_hold']
    assert sha((BASE / 'admit.py').read_bytes()) == 'd1e3be943bb5a15a2e1d0a87d0a8f1e455c42d81594760f1a8dd1257251a9fe1'
    spec = importlib.util.spec_from_file_location('frozen_original_admit', BASE / 'admit.py')
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    check('guard-installed-before-subject-imports', guarded)
    check('only-test-evidence-AST-changes-and-frozen-policies', unchanged_scope)
    check('actual-original-parser-refusal-retained', lambda: refuse(text, original), text)
    check('actual-corrected-parser-accepts-all-699', lambda: accept(text), text)
    check('nonzero-command-exit-refused-before-parser', nonzero_command_exit)
    names = list(a.ORACLES) + ['fixture_' + str(i) for i in range(690)]
    complete = group(names)
    positives = {
        'grammar-normal-terminals': complete,
        'grammar-zero-test-group-before': group([]) + complete,
        'grammar-zero-test-group-after': complete + group([]),
        'grammar-two-groups': group(names[:9]) + group(names[9:]),
        'grammar-singular-group': group(names[:1]) + group(names[1:]),
        'grammar-no-duration-summary': complete.replace('; finished in 1s', ';'),
        'grammar-captured-output-after-complete-terminals': group(names, '\nsuccesses:\n\n---- fixture_0 stdout ----\nordinary captured text\ntest mailbox poison\n\nsuccesses:\n    fixture_0\n\n'),
        'grammar-spaced-compile-fail-doctest': group(names[:-1] + ['src/module.rs - module::Item (line 12) - compile fail']),
        'grammar-spaced-ordinary-doctest': group(names[:-1] + ['src/module.rs - module::Item (line 12)']),
    }
    split_lines = text.splitlines()
    split_start = next(i for i, line in enumerate(split_lines) if line.startswith('test shared_control_branch_targets_and_frame_boundary ... '))
    split_end = next(i for i in range(split_start + 1, len(split_lines)) if split_lines[i] == 'ok')
    split = '\n'.join(split_lines[split_start:split_end + 1]) + '\n'
    positives['grammar-actual-serialized-split-form'] = replace_once(complete, 'test fixture_0 ... ok\n', split)
    for name, value in positives.items():
        check(name, lambda value=value: accept(value), value)
    first_header = next(line for line in text.splitlines() if line.startswith('test ') and line.endswith(' ... ok'))
    first_summary = next(line for line in text.splitlines() if line.startswith('test result:'))
    first_doctest = next(line for line in text.splitlines() if line.startswith('test src/') and ' - compile fail ... ok' in line)
    split_header = split_lines[split_start]
    trace = split_lines[split_start + 1]
    negatives = {
        'actual-summary-FAILED-with-zero-failed': replace_once(text, first_summary, first_summary.replace('ok.', 'FAILED.')),
        'actual-summary-failed-count': replace_once(text, first_summary, first_summary.replace('0 failed', '1 failed')),
        'actual-summary-ignored-count': replace_once(text, first_summary, first_summary.replace('0 ignored', '1 ignored')),
        'actual-summary-measured-count': replace_once(text, first_summary, first_summary.replace('0 measured', '1 measured')),
        'actual-summary-filtered-count': replace_once(text, first_summary, first_summary.replace('0 filtered', '1 filtered')),
        'actual-summary-unknown-result': replace_once(text, first_summary, first_summary.replace('ok.', 'unknown.')),
        'actual-summary-malformed-duration': replace_once(text, first_summary, first_summary + ' forged'),
        'actual-summary-indented': replace_once(text, first_summary, '  ' + first_summary),
        'actual-summary-missing': replace_once(text, first_summary, ''),
        'actual-summary-duplicate': replace_once(text, first_summary, first_summary + '\n' + first_summary),
        'actual-running-missing': replace_once(text, 'running 467 tests', ''),
        'actual-running-duplicate': replace_once(text, 'running 467 tests', 'running 467 tests\nrunning 467 tests'),
        'actual-running-count-mismatch': replace_once(text, 'running 467 tests', 'running 468 tests'),
        'actual-running-malformed': replace_once(text, 'running 467 tests', 'running -467 tests'),
        'actual-terminal-missing': replace_once(text, first_header + '\n', ''),
        'actual-header-duplicate': replace_once(text, first_header, first_header + '\n' + first_header),
        'actual-header-failed': replace_once(text, first_header, first_header.replace(' ... ok', ' ... FAILED')),
        'actual-header-ignored': replace_once(text, first_header, first_header.replace(' ... ok', ' ... ignored')),
        'actual-header-extra-delimiter': replace_once(text, first_header, first_header.replace(' ... ok', ' ... ok ... ok')),
        'actual-doctest-arbitrary-spaced-name': replace_once(text, first_doctest, 'test garbage words (not a libtest identity) ... ok'),
        'actual-doctest-invalid-line-zero': replace_once(text, first_doctest, re.sub(r'\(line \d+\)', '(line 0)', first_doctest)),
        'actual-doctest-missing-line': replace_once(text, first_doctest, re.sub(r' \(line \d+\)', '', first_doctest)),
        'actual-doctest-trailing-name-space': replace_once(text, first_doctest, first_doctest.replace(' ... ok', '  ... ok')),
        'actual-oracle-missing-identity': replace_once(text, 'test ' + a.ORACLES[0] + ' ... ok', 'test absent_oracle ... ok'),
        'actual-oracle-duplicate-identity': replace_once(text, 'test ' + a.ORACLES[0] + ' ... ok', 'test ' + a.ORACLES[1] + ' ... ok'),
        'actual-oracle-prefix-is-not-exact': replace_once(text, 'test ' + a.ORACLES[0] + ' ... ok', 'test suffix_' + a.ORACLES[0] + ' ... ok'),
        'actual-split-unknown-name': replace_once(text, split_header, split_header.replace('shared_control_branch_targets_and_frame_boundary', 'forged_split_test')),
        'actual-split-marker-forged': replace_once(text, split_header, split_header.replace('serialized lane', 'forged lane')),
        'actual-split-no-traces': replace_once(text, split, split_header + '\nok\n'),
        'actual-split-unfinished': replace_once(text, split, split.rsplit('ok\n', 1)[0]),
        'actual-split-duplicate-standalone-ok': replace_once(text, split, split + 'ok\n'),
        'actual-split-standalone-FAILED': replace_once(text, split, split.rsplit('ok\n', 1)[0] + 'FAILED\n'),
        'actual-split-standalone-ignored': replace_once(text, split, split.rsplit('ok\n', 1)[0] + 'ignored\n'),
        'actual-split-standalone-malformed': replace_once(text, split, split.rsplit('ok\n', 1)[0] + 'ok forged\n'),
        'actual-split-overlapping-header': replace_once(text, split_header, split_header + '\n' + first_header),
        'actual-split-forged-running-transition': replace_once(text, trace, 'running 0 tests'),
        'actual-split-forged-summary-transition': replace_once(text, trace, summary(0).strip()),
        'actual-split-forged-capture-transition': replace_once(text, trace, 'successes:'),
        'actual-split-duplicate-observer': replace_once(text, trace, 'control_observer serialized lane'),
        'actual-split-arbitrary-output': replace_once(text, trace, 'arbitrary bytes before standalone ok'),
        'actual-split-blank-interruption': replace_once(text, trace, ''),
        'actual-split-malformed-trace-envelope': replace_once(text, trace, 'control_trace block-empty config=forged allocations=(0, 0, 0)'),
        'actual-split-ceiling-output-wrong-test': replace_once(text, trace, next(line for line in split_lines if line.startswith('control_validation_ceiling '))),
        'actual-split-warm-output-wrong-test': replace_once(text, trace, 'control_warm block-empty usage=Usage {} cache=Cache {} allocations=(0, 0, 0)'),
        'actual-orphan-standalone-before-all-groups': 'ok\n' + text,
        'actual-orphan-standalone-after-all-groups': text + 'ok\n',
        'actual-orphan-trace-after-all-groups': text + trace + '\n',
        'actual-orphan-observer-after-all-groups': text + 'control_observer serialized lane\n',
        'actual-captured-test-header-is-not-a-terminal': replace_once(text, '\nsuccesses:\n', '\nsuccesses:\ntest forged_captured_test ... ok\n'),
        'actual-captured-malformed-summary-is-not-payload': replace_once(text, '\nsuccesses:\n', '\nsuccesses:\ntest result : FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out;\n'),
        'actual-premature-capture-before-tests': replace_once(text, 'running 467 tests\n', 'running 467 tests\nsuccesses:\n'),
        'actual-carriage-return-injection': replace_once(text, first_header, first_header + '\rtest forged ... ok'),
        'actual-ANSI-injection': replace_once(text, first_header, '\x1b[0m' + first_header),
    }
    for name, value in negatives.items():
        check(name, lambda value=value: refuse(value), value)
    grammar_negatives = {
        'grammar-unfinished-last-group': complete + 'running 1 test\n',
        'grammar-terminal-without-running': complete.partition('\n')[2],
        'grammar-summary-without-running': complete + summary(0),
        'grammar-running-singular-mismatch': complete.replace('running 699 tests', 'running 699 test'),
        'grammar-running-leading-zero': complete.replace('running 699 tests', 'running 0699 tests'),
        'grammar-sum-698': group(names[:-1]),
        'grammar-sum-700': group(names + ['extra_fixture']),
        'grammar-duplicate-across-groups': group(names[:9]) + group(names[9:-1] + [names[9]]),
        'grammar-summary-negative-count': complete.replace('699 passed', '-699 passed'),
        'grammar-summary-junk-suffix': complete + 'test result: ok.\n',
        'grammar-stray-nonempty-output': 'forged transport line\n' + complete,
        'grammar-name-invalid-colon': complete.replace('fixture_0 ...', 'fixture_0:bad ...', 1),
        'grammar-name-tab': complete.replace('fixture_0 ...', 'fixture\t0 ...', 1),
    }
    for name, value in grammar_negatives.items():
        check(name, lambda value=value: refuse(value), value)
    assert sha((ACTUAL / 'commands/debug-regression.stdout').read_bytes()) == RAW_SHA
    actual_receipt = b.json_data((ACTUAL / 'receipt.json').read_bytes())
    result = {'schema': 1, 'pythonVersion': sys.version, 'guardBeforeSubjectImports': True,
              'subjectRuntimeRuns': 0, 'nestedProcessSessionGroupSignalTimerWaitSocketCalls': 0,
              'liveApiAttempts': offline.ATTEMPTS, 'sourceRevision': '1eec8e0fc270c0409c8920ee22fd2374f3bd249f',
              'sourceTree': 'f20be7de5a047f1983931961cc3d774e56de80a3', 'actualRun': 40824584975,
              'actualStdout': {'bytes': len(raw), 'sha256': RAW_SHA}, 'actualCommandExit': command['exit'],
              'actualCommandElapsedSeconds': command['elapsed_seconds'], 'originalHostStatus': actual_receipt['status'],
              'actualReleaseStarted': any(c['name'] == 'release-regression' for c in actual_receipt['commands']),
              'proposedHarnessSHA256': sha((HERE / 'admit.py').read_bytes()),
              'controls': RECORDS, 'checks': len(RECORDS), 'passed': sum(r['passed'] for r in RECORDS),
              'failures': sum(not r['passed'] for r in RECORDS), 'actualCorruptionControls': len(negatives),
              'focusedGrammarPositives': len(positives), 'focusedGrammarNegatives': len(grammar_negatives),
              'rawEvidenceUnchanged': True, 'scratchRemaining': [p.name for p in (HERE / 'local').glob('nonzero-*')]}
    attempts = list((HERE / 'local').glob('replay-attempt-*.json'))
    assert len(attempts) < 10
    target = HERE / 'local' / ('replay-attempt-' + str(len(attempts) + 1) + '.json')
    save(target, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'controls'}, sort_keys=True))
    assert result['failures'] == 0 and not offline.ATTEMPTS and not result['scratchRemaining']

if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        failures = list((HERE / 'local').glob('setup-failure-*.json'))
        save(HERE / 'local' / ('setup-failure-' + str(len(failures) + 1) + '.json'),
             {'error': {'type': type(error).__name__, 'message': str(error)}, 'completedControls': RECORDS,
              'pythonVersion': sys.version, 'guardBeforeSubjectImports': True, 'liveApiAttempts': offline.ATTEMPTS})
        raise
