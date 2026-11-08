#!/usr/bin/env python3
"""Replay the exact CI import failure in process; deny process and timer APIs."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import traceback
import types
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE
ORIGINAL = ROOT / 'verification/cache-fixture-shared-input-candidate/test_runner.py'
METHOD = 'test_checks_active_under_optimized_python'
OLD = "p=subprocess.run([sys.executable,'-B','-O','-c',code],capture_output=True,timeout=15);"
NEW = "p=subprocess.run([sys.executable,'-B','-O','-c',code],capture_output=True,timeout=15,cwd=HERE);"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    source = ORIGINAL.read_text()
    assert source.count(OLD) == 1
    proposed = source.replace(OLD, NEW)
    assert proposed == (CANDIDATE / 'test_runner.py').read_text()
    patch = ''.join(difflib.unified_diff(
        source.splitlines(keepends=True), proposed.splitlines(keepends=True),
        fromfile='a/verification/cache-fixture-shared-input-candidate/test_runner.py',
        tofile='b/verification/cache-fixture-shared-input-candidate-v2/test_runner.py'))
    (HERE / 'control-cwd-amendment.diff').write_text(patch)
    denied = []
    calls = []

    def deny(name):
        def fail(*args, **kwargs):
            denied.append(name)
            raise AssertionError('Forbidden in-process review API: ' + name)
        return fail

    def emulate_python_command(argv, **kwargs):
        assert argv[1:4] == ['-B', '-O', '-c']
        assert kwargs['capture_output'] is True and kwargs['timeout'] == 15
        cwd = Path(kwargs.get('cwd', ROOT)).resolve()
        calls.append({'cwd': str(cwd), 'argv_flags': argv[1:4],
                      'mode': 'in-process import replay; no Python child'})
        # Python -c searches its cwd. runpy.run_path for a source file does not
        # add that source file's directory; retain this distinction explicitly.
        search = [str(cwd)] + [entry for entry in sys.path[1:]
                                   if entry and Path(entry).resolve() != CANDIDATE]
        stdout, stderr = io.StringIO(), io.StringIO()
        status = 0
        old_overlay = sys.modules.pop('materialize_pack', None)
        try:
            with mock.patch.object(sys, 'path', search), redirect_stdout(stdout), redirect_stderr(stderr):
                try:
                    exec(compile(argv[4], '<in-process Python -c replay>', 'exec', optimize=1), {})
                except BaseException:
                    status = 1
                    traceback.print_exc()
        finally:
            sys.modules.pop('materialize_pack', None)
            if old_overlay is not None:
                sys.modules['materialize_pack'] = old_overlay
        result = subprocess.CompletedProcess(argv, status, stdout.getvalue().encode(), stderr.getvalue().encode())
        calls[-1].update(returncode=status, stderr=result.stderr.decode())
        return result

    with ExitStack() as stack:
        for module, names in [
            (subprocess, ['Popen', 'call', 'check_call', 'check_output']),
            (os, ['system', 'fork', 'forkpty', 'posix_spawn', 'posix_spawnp', 'kill', 'killpg', 'wait', 'wait3', 'wait4', 'waitpid']),
            (signal, ['signal', 'setitimer', 'alarm', 'pause']),
            (socket, ['socket', 'create_connection']),
            (time, ['sleep']),
        ]:
            for name in names:
                if hasattr(module, name):
                    stack.enter_context(mock.patch.object(module, name, deny(module.__name__ + '.' + name)))
        stack.enter_context(mock.patch.object(subprocess, 'run', emulate_python_command))
        stack.enter_context(mock.patch.object(sys, 'path', [str(CANDIDATE)] + sys.path))
        old_overlay = sys.modules.pop('materialize_pack', None)
        try:
            observations = []
            for label, text in [('delivered-baseline', source), ('proposed-cwd-only', proposed)]:
                module = types.ModuleType('review_' + label.replace('-', '_'))
                module.__file__ = str(CANDIDATE / 'test_runner.py')
                exec(compile(text, str(ORIGINAL), 'exec'), module.__dict__)
                case = module.RunnerControls(METHOD)
                try:
                    getattr(case, METHOD)()
                    observations.append({'case': label, 'passed': True})
                except AssertionError as error:
                    observations.append({'case': label, 'passed': False,
                                         'exception_type': type(error).__name__, 'message': str(error)})
            assert observations[0]['passed'] is False
            assert "No module named 'materialize_pack'" in calls[0]['stderr']
            assert observations[1]['passed'] is True
            assert 'RuntimeError: Noncanonical member path' in calls[1]['stderr']
            assert 'ModuleNotFoundError' not in calls[1]['stderr']
            # Compile the complete unchanged runner with optimization explicitly
            # enabled and exercise its guard directly; no -O child is started.
            runner = {'__file__': str(CANDIDATE / 'check_cache_state.py'), '__name__': 'optimized_review'}
            exec(compile((CANDIDATE / 'check_cache_state.py').read_bytes(), runner['__file__'], 'exec', optimize=1), runner)
            try:
                runner['member']('../escape')
                raise AssertionError('optimized guard accepted traversal')
            except RuntimeError as error:
                assert str(error) == 'Noncanonical member path'
                optimized_guard = {'optimize': 1, 'exception_type': type(error).__name__, 'message': str(error)}
        finally:
            sys.modules.pop('materialize_pack', None)
            if old_overlay is not None:
                sys.modules['materialize_pack'] = old_overlay
    assert denied == []
    result = {
        'schema': 1, 'scope': 'Exact delivered Python control and one-keyword proposal, in-process imports plus optimize=1 guard; no actual -O child or full 36-control rerun',
        'python': sys.version, 'source_sha256': sha(source.encode()),
        'proposed_source_sha256': sha(proposed.encode()), 'actual_v2_control_sha256': sha((CANDIDATE / 'test_runner.py').read_bytes()), 'patch_sha256': sha(patch.encode()),
        'change': 'Add cwd=HERE to only the optimized-Python test subprocess invocation',
        'observations': observations, 'in_process_calls': calls,
        'explicit_optimized_runner_guard': optimized_guard,
        'denied_api_invocations': denied, 'native_or_compiler_executed': False,
        'child_processes_started': 0, 'signals_registered': 0,
        'actual_remote_corrected_test_pending': True,
    }
    (HERE / 'probe-replay.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': 'passed-in-process-only', 'observations': observations,
                      'child_processes_started': 0, 'patch_sha256': result['patch_sha256']}))


if __name__ == '__main__':
    main()
