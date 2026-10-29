#!/usr/bin/env python3
"""Independent sealed-source review plus bounded, fully mocked clock checks."""
import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = ROOT / 'verification/shared-fixture-clock-controls-correction'
EXPECTED_SEAL = '2c4b7f295d275694b5541113f17f0e9216a073a864b01b95b0078632d4145d71'
DENIED = []
FD_PATHS = {}
sys.dont_write_bytecode = True


def denied(*args, **kwargs):
    DENIED.append('process/session/group/signal/timer/wait/socket API')
    raise RuntimeError('Independent review prohibits actual process or socket APIs')


def audit(event, args):
    if event.startswith(('subprocess.', 'socket.')) or event in {
        'os.system', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty',
        'os.exec', 'os.kill', 'os.killpg', 'os.startfile',
    }:
        DENIED.append(event)
        raise RuntimeError('Independent review prohibits ' + event)
    targets = []
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            targets = [(args[0], None)]
    elif event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod', 'os.truncate'}:
        directory = args[-1] if event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod'} else None
        targets = [(args[0], directory)]
    elif event in {'os.rename', 'os.link', 'os.symlink'}:
        targets = [(args[0], args[2] if len(args) > 2 else None),
                   (args[1], args[3] if len(args) > 3 else None)]
    for target, directory in targets:
        path = Path(os.fsdecode(target))
        if not path.is_absolute() and directory is not None and directory != -1:
            if directory not in FD_PATHS:
                DENIED.append('untracked relative directory write')
                raise RuntimeError('Untracked directory descriptor')
            path = FD_PATHS[directory] / path
        path = path.resolve()
        if not path.is_relative_to(HERE):
            DENIED.append('write outside reviewer ownership')
            raise RuntimeError('Write outside independent review folder: ' + str(path))


sys.addaudithook(audit)
_original_open, _original_close = os.open, os.close
def tracked_open(path, flags, mode=0o777, *, dir_fd=None):
    target = Path(os.fsdecode(path))
    if not target.is_absolute() and dir_fd is not None:
        target = FD_PATHS[dir_fd] / target
    descriptor = _original_open(path, flags, mode, dir_fd=dir_fd)
    FD_PATHS[descriptor] = target.resolve()
    return descriptor
def tracked_close(descriptor):
    try:
        return _original_close(descriptor)
    finally:
        FD_PATHS.pop(descriptor, None)
os.open, os.close = tracked_open, tracked_close
for owner, names in [
    (os, ['system', 'posix_spawn', 'posix_spawnp', 'fork', 'forkpty',
          'setsid', 'setpgid', 'getsid', 'getpgid', 'getpgrp', 'kill', 'killpg',
          'wait', 'waitpid', 'waitid', 'wait3', 'wait4', 'abort', '_exit',
          'execl', 'execle', 'execlp', 'execlpe', 'execv', 'execve', 'execvp',
          'execvpe', 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe', 'spawnv',
          'spawnve', 'spawnvp', 'spawnvpe', 'pidfd_open', 'openpty']),
    (subprocess, ['Popen', 'run', 'call', 'check_call', 'check_output',
                  'getstatusoutput', 'getoutput']),
    (signal, ['signal', 'alarm', 'setitimer', 'pause', 'sigwait', 'sigwaitinfo',
              'sigtimedwait', 'pthread_kill', 'pthread_sigmask', 'raise_signal',
              'siginterrupt', 'getitimer', 'getsignal', 'sigpending', 'pidfd_send_signal']),
    (socket, ['socket', 'create_connection', 'socketpair', 'fromfd', 'fromshare',
              'create_server', 'getaddrinfo', 'gethostbyname', 'gethostbyname_ex',
              'gethostbyaddr']),
    (time, ['sleep', 'clock_settime', 'clock_settime_ns']),
]:
    for name in names:
        if hasattr(owner, name):
            setattr(owner, name, denied)

# No subject import occurs before the audit/API guards above.
sys.path.insert(0, str(CANDIDATE))
import adopt_fixture as adoption
import control_source as controls


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_provenance():
    seal_data = (CANDIDATE / 'seal.json').read_bytes()
    assert sha(seal_data) == EXPECTED_SEAL
    seal = json.loads(seal_data)
    assert seal['member_count'] == 16
    assert sum(row['bytes'] for row in seal['members']) == 92848
    proof = adoption.verify()
    original_adoption = ROOT / 'verification/shared-fixture-default-ci-adoption'
    old = json.loads((original_adoption / 'dependencies.json').read_bytes())
    new = json.loads((CANDIDATE / 'dependencies.json').read_bytes())
    assert len(old['members']) == 123 and len(new['members']) == 137
    rows = {row['path']: row for row in new['members']}
    assert all(rows[row['path']] == row for row in old['members'])
    closure = json.loads((original_adoption / 'seal.json').read_bytes())
    expected = {str((original_adoption / row['path']).relative_to(ROOT)) for row in closure['members']}
    expected.add(str((original_adoption / 'seal.json').relative_to(ROOT)))
    assert set(rows) - {row['path'] for row in old['members']} == expected
    for name in ['adopt_fixture.py', 'test_adoption.py', 'offline_guard.py']:
        assert (CANDIDATE / name).read_bytes() == (original_adoption / name).read_bytes()
    for key in ['compiler_policy', 'fixture_source']:
        assert old[key] == new[key]
    original, effective = controls.control_source(False), controls.control_source(True)
    assert effective == original.replace(controls.BEFORE, controls.AFTER, 1)
    assert effective.replace(controls.AFTER, controls.BEFORE, 1) == original
    assert controls.AFTER + b'  if timed_out:clock.monotonic.side_effect=[100.0,101.0,101.0]\n' in effective
    def test_bodies(source):
        cls = next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == 'RunnerControls')
        return {node.name: ast.dump(node, include_attributes=False) for node in cls.body
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}
    assert len(test_bodies(original)) == 36 and test_bodies(original) == test_bodies(effective)
    old_job = (CANDIDATE / 'workflow/original-job.yml').read_text()
    job = (CANDIDATE / 'workflow/swift-cache-state-fixture.yml').read_text()
    assert old_job == (original_adoption / 'workflow/swift-cache-state-fixture.yml').read_text()
    expected_job = old_job.replace('            /verification/shared-fixture-default-ci-adoption/\n',
        '            /verification/shared-fixture-default-ci-adoption/\n            /verification/shared-fixture-clock-controls-correction/\n', 1)
    expected_job = expected_job.replace('MIXER_ADOPTION_DIR="$GITHUB_WORKSPACE/verification/shared-fixture-default-ci-adoption"',
        'MIXER_ADOPTION_DIR="$GITHUB_WORKSPACE/verification/shared-fixture-clock-controls-correction"')
    expected_job = expected_job.replace('python3 -B "$MIXER_SHARED_INPUT_DIR/test_runner.py" -v',
        'python3 -B "$MIXER_ADOPTION_DIR/test_runner.py" -v', 1)
    expected_job = expected_job.replace('            ${{ github.workspace }}/verification/shared-fixture-default-ci-adoption/\n',
        '            ${{ github.workspace }}/verification/shared-fixture-default-ci-adoption/\n            ${{ github.workspace }}/verification/shared-fixture-clock-controls-correction/\n', 1)
    assert job == expected_job
    # Every bound dependency is included by the non-cone sparse closure.
    sparse = job.split('          sparse-checkout: |\n', 1)[1].split('      - name:', 1)[0]
    patterns = [line.strip().lstrip('/') for line in sparse.splitlines() if line.strip()]
    assert all(any(row['path'] == pattern or
        (pattern.endswith('/') and row['path'].startswith(pattern)) for pattern in patterns) for row in new['members'])
    # Canonical equality is deliberately left to root installation and remote pre/postflight.
    canonical_state = adoption.job_text((ROOT / '.github/workflows/verify.yml').read_text())
    assert canonical_state in {old_job, job}
    runner, base, _ = adoption.load_runner()
    assert runner.rust_identity is base.rust_identity
    assert runner.rust_identity.__globals__ is base.__dict__
    assert (runner.CHILD_SECONDS, runner.ACTIVE_SECONDS, runner.CLEANUP_SECONDS, runner.OUTPUT_CAP) == (60, 600, 60, 8388608)
    main = types.ModuleType('__main__')
    main.__file__ = str(CANDIDATE / 'test_runner.py')
    discoveries = []
    def discover(*args, **kwargs):
        assert not args and kwargs == {'verbosity': 2}
        discoveries.append(unittest.defaultTestLoader.loadTestsFromModule(sys.modules['__main__']).countTestCases())
    search_path = list(sys.path)
    try:
        with mock.patch.dict(sys.modules, {'__main__': main}), mock.patch.object(unittest, 'main', side_effect=discover):
            exec(compile((CANDIDATE / 'test_runner.py').read_bytes(), main.__file__, 'exec'), main.__dict__)
    finally:
        sys.path[:] = search_path
    assert discoveries == [36] and main.HERE == controls.FROZEN.parent
    assert main.__file__ == str(controls.FROZEN)
    assert main.RunnerControls.test_checks_active_under_optimized_python.__code__.co_filename == str(controls.FROZEN)
    return {'seal_sha256': EXPECTED_SEAL, 'member_count': 16, 'member_bytes': 92848,
            'effective_control_sha256': sha(effective), 'dependency_count': 137,
            'dependencies_tree_sha256': new['tree_sha256'], 'actual_main_discovery': discoveries,
            'canonical_job_at_review': 'corrected' if canonical_state == job else 'original',
            'adoption_proof': proof}


def run_mocked(source, label, origin, method):
    name = 'independent_clock_' + label.replace('-', '_')
    subject = types.ModuleType(name)
    subject.__file__ = str(controls.FROZEN)
    sys.modules[name] = subject
    with mock.patch.object(sys, 'path', [str(controls.FROZEN.parent), *sys.path]):
        exec(compile(source, str(controls.FROZEN), 'exec'), subject.__dict__)
    commands = []
    original_mocked = subject.RunnerControls.mocked_command
    def capture(instance):
        result = original_mocked(instance)
        commands.append(result[0])
        return result
    output = io.StringIO()
    with mock.patch.object(subject, 'time', types.SimpleNamespace(monotonic=lambda: origin)), \
         mock.patch.object(subject.RunnerControls, 'mocked_command', capture):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.TestSuite([subject.RunnerControls(method)]))
    (HERE / 'logs' / (label + '.txt')).write_text(output.getvalue())
    assert len(commands) == 1 and result.testsRun == 1
    return result, commands[0], output.getvalue()


def main():
    (HERE / 'logs').mkdir(exist_ok=True)
    scratch = HERE / 'scratch'
    scratch.mkdir(exist_ok=True)
    tempfile.tempdir = str(scratch)
    provenance = verify_provenance()
    observations = []
    method = 'test_mocked_cpu_timeout_retains_failure_and_aggregate'
    # New boundary profiles distinguish nonpositive remaining budget from a valid
    # timeout; producer already covered origins 0 and 1000 for all four methods.
    for corrected in [False, True]:
        for origin in [80.0, 80.5]:
            label = ('corrected' if corrected else 'baseline') + '-boundary-' + str(origin)
            result, command, output = run_mocked(controls.control_source(corrected), label, origin, method)
            expected_error = not corrected and origin == 80.0
            assert len(result.errors) == int(expected_error) and not result.failures
            if expected_error:
                assert not command.receipt['commands'] and 'IndexError: list index out of range' in output
            else:
                row = command.receipt['commands'][0]
                assert result.wasSuccessful() and row['timed_out'] and row['elapsed_seconds'] == 1.0
                assert row['effective_timeout_seconds'] == 0.5
                assert row['child_resource_usage']['aggregate_delta'] == {'ru_utime': .5, 'ru_stime': .25, 'ru_minflt': 5, 'ru_majflt': 2}
            observations.append({'corrected': corrected, 'origin': origin, 'tests': 1,
                'errors': len(result.errors), 'receipt_count': len(command.receipt['commands'])})
    # An in-memory ordering mutant consumes the timeout sequence's first tick.
    # It must fail the original timeout method, proving position is material.
    source = controls.control_source(True)
    pair = b'  c.deadline=clock.monotonic()+20\n  if timed_out:clock.monotonic.side_effect=[100.0,101.0,101.0]\n'
    mutant = source.replace(pair, b'  if timed_out:clock.monotonic.side_effect=[100.0,101.0,101.0]\n  c.deadline=clock.monotonic()+20\n', 1)
    assert mutant != source
    result, command, output = run_mocked(mutant, 'misplaced-reset-negative', 80.0, method)
    assert len(result.errors) == 1 and not result.failures and 'StopIteration' in output
    assert len(command.receipt['commands']) == 1
    assert not DENIED and not list(scratch.iterdir())
    scratch.rmdir()
    summary = {'schema': 1, 'decision': 'ready for root adoption and remote ordinary-job execution',
        'findings': [], 'provenance': provenance, 'boundary_observations': observations,
        'misplaced_reset_mutant': {'tests': 1, 'expected_errors': 1, 'observed_errors': len(result.errors), 'discriminator': 'StopIteration'},
        'guards_installed_before_subject_imports': True, 'denied_operation_attempts': DENIED,
        'local_scope': 'Four boundary timeout-method executions and one in-memory negative mutant; no full runner or fixture execution',
        'fresh_writes_confined_to_review_folder': True, 'scratch_removed': True,
        'python': sys.version, 'python_executable': sys.executable,
        'command': '/opt/homebrew/bin/python3 -B verification/shared-fixture-clock-independent-review/review_clock.py',
        'source_revision': 'No Git invoked; supplied failing Engine revision 836fc67b is historical context only',
        'pending': ['Remote 16 adoption + 9 materializer + all 36 runner controls', 'Remote complete 103-command fixture',
                    'Installed-job preflight and postflight', 'All existing native, physical-phone, custody, Unit A, hosted and GA holds']}
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'decision': summary['decision'], 'boundary_checks': 4, 'negative_mutant_rejected': True,
        'denied_operation_attempts': DENIED, 'seal_sha256': EXPECTED_SEAL}, sort_keys=True))


if __name__ == '__main__':
    main()
