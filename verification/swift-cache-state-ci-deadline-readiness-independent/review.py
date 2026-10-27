#!/usr/bin/env python3
"""Bounded independent host-only review of the frozen cleanup-stage test repair."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SELECTED = ROOT / 'verification/swift-cache-state-ci-deadline-readiness'
EXPECTED_TEST = 'c754ea8c8cb40d0090c676de61263939e6e58b140f9902e97901126a4287e9ab'
EXPECTED_RUNNER = 'e531311facb7b38967d3b904b26e92ff3f6c4dc7444c856cd799b70a1d91373b'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def command(name, argv, cwd, timeout=20):
    env = dict(os.environ)
    env.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(HERE / 'tmp'))
    start = time.monotonic()
    with (HERE / (name + '.stdout')).open('wb') as stdout, (HERE / (name + '.stderr')).open('wb') as stderr:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        timed_out = False
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGKILL)
            code = proc.wait(timeout=5)
    return {'name': name, 'argv': argv, 'cwd': str(cwd), 'timeout_seconds': timeout,
            'elapsed_seconds': round(time.monotonic()-start, 6), 'exit': code,
            'timed_out': timed_out, 'owned_direct_child_returned': True,
            'stdout': name + '.stdout', 'stdout_sha256': sha(HERE / (name + '.stdout')),
            'stderr': name + '.stderr', 'stderr_sha256': sha(HERE / (name + '.stderr'))}


def main():
    (HERE / 'tmp').mkdir(exist_ok=True)
    manifest = json.loads((SELECTED / 'candidate-source.json').read_text())
    source = HERE / 'source'
    source.mkdir(exist_ok=True)
    verified = []
    for row in manifest['members']:
        relative = Path(row['path']).relative_to('candidate-source')
        assert not relative.is_absolute() and '..' not in relative.parts
        original = SELECTED / row['path']
        assert not original.is_symlink() and original.stat().st_size == row['bytes']
        assert sha(original) == row['sha256']
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        verified.append({'path': str(relative), 'bytes': target.stat().st_size, 'sha256': sha(target)})
    assert len(verified) == 91
    assert sha(source / 'test_runner.py') == EXPECTED_TEST
    assert sha(source / 'check_cache_state.py') == EXPECTED_RUNNER
    (source / 'logs').mkdir(exist_ok=True)
    save(HERE / 'source-manifest.json', {'members': verified, 'member_count': len(verified),
         'selected_manifest_sha256': sha(SELECTED / 'candidate-source.json'),
         'selected_tree_sha256': manifest['tree_sha256']})
    results = []
    results.append(command('all-29', [sys.executable, '-B', 'test_runner.py'], source))
    assert results[-1]['exit'] == 0 and not results[-1]['timed_out']
    test_names = ['test_runner.RunnerControls.test_postflight_deadline_is_terminal_and_preserves_scratch',
                  'test_runner.RunnerControls.test_retention_deadline_is_terminal_and_preserves_scratch']
    original_runner = (source / 'check_cache_state.py').read_text()
    mutations = {
        'missing-cleanup-timer': ('signal.signal(signal.SIGALRM,cleanup_alarm);signal.setitimer(signal.ITIMER_REAL,max(0.000001,cleanup_deadline-time.monotonic()))',
                                  'signal.signal(signal.SIGALRM,cleanup_alarm)'),
        'wrong-cleanup-handler': ('signal.signal(signal.SIGALRM,cleanup_alarm);signal.setitimer',
                                  'signal.signal(signal.SIGALRM,alarm);signal.setitimer'),
        'ignored-cleanup-handler': ('signal.signal(signal.SIGALRM,cleanup_alarm);signal.setitimer',
                                    'signal.signal(signal.SIGALRM,lambda signum,frame:None);signal.setitimer'),
    }
    for name, (before, after) in mutations.items():
        assert original_runner.count(before) == 1
        case = HERE / name
        shutil.copytree(source, case, ignore=shutil.ignore_patterns('logs', '__pycache__'), dirs_exist_ok=True)
        (case / 'check_cache_state.py').write_text(original_runner.replace(before, after))
        result = command(name, [sys.executable, '-B', '-m', 'unittest', '-v', *test_names], case)
        result['mutation'] = {'before': before, 'after': after, 'runner_sha256': sha(case / 'check_cache_state.py')}
        result['expected_exit'] = 1
        stderr = (HERE / result['stderr']).read_text()
        assert result['exit'] == 1 and not result['timed_out'] and 'Ran 2 tests' in stderr
        assert any(summary in stderr for summary in ['FAILED (failures=2)', 'FAILED (failures=1, errors=1)', 'FAILED (errors=2)'])
        result['both_deadline_tests_rejected_mutation'] = True
        results.append(result)
    # Fresh tests of unchanged production runner without the candidate's logical clock or timer proxy.
    result = command('natural-clock', [sys.executable, '-B', str(HERE / 'natural_clock.py')], source)
    assert result['exit'] == 0 and not result['timed_out']
    results.append(result)
    # Account for each owned test temporary directory without any process discovery.
    leftovers = list((HERE / 'tmp').iterdir())
    assert leftovers == [], leftovers
    for row in verified:
        assert sha(source / row['path']) == row['sha256']
    save(HERE / 'execution.json', {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
         'host': platform.platform(), 'machine': platform.machine(), 'python': sys.version,
         'python_launcher': sys.executable, 'python_resolved': str(Path(sys.executable).resolve()),
         'python_sha256': sha(Path(sys.executable).resolve()),
         'base_revision': 'dee2d199dfbd6396153e1bb951e809b0ee0f8e86',
         'test_sha256': EXPECTED_TEST, 'runner_sha256': EXPECTED_RUNNER,
         'selected_tree_sha256': manifest['tree_sha256'], 'commands': results,
         'owned_temporary_directories_remaining': [],
         'native_execution': False, 'capture_or_ui': False, 'process_inventory': False,
         'rust_compiler_invocations': 0, 'canonical_or_git_writes': False,
         'scope': 'Independent host-only test review; no native, release, CI rerun or GA qualification.'})
    print(json.dumps({'commands': len(results), 'all_expected_results_observed': True}))


if __name__ == '__main__':
    main()
