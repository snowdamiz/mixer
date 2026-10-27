"""Bounded host-only receipts for the CI group-termination test repair."""
import argparse
import contextlib
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CASE = 'test_timeout_kills_all_owned_group_members_and_returns_children'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def focused(mode):
    sys.path.insert(0, str(ROOT / 'scripts/ci/tests'))
    import test_analyzer_envelope_runner as tests
    popen, killpg = subprocess.Popen, tests.os.killpg
    run = tests.r.Commands.run
    children, waits, commands, signals = [], [], [], []

    def record_spawn(*args, **kwargs):
        child = popen(*args, **kwargs)
        children.append(child)
        wait = child.wait

        def record_wait(timeout=None):
            row = {'pid': child.pid, 'timeout': timeout}
            start = time.monotonic()
            try:
                row['returncode'] = wait(timeout=timeout)
                return row['returncode']
            except BaseException as error:
                row['exception'] = type(error).__name__
                raise
            finally:
                row['elapsed_seconds'] = time.monotonic() - start
                waits.append(row)

        child.wait = record_wait
        return child

    def record_run(self, *args, **kwargs):
        try:
            return run(self, *args, **kwargs)
        finally:
            commands.extend(copy.deepcopy(self.receipt['commands']))
            for row in self.receipt['commands']:
                for stream in ('stdout', 'stderr'):
                    path = self.out / 'commands' / (row['name'] + '.' + stream)
                    if path.is_file():
                        (OUT / (mode + '-command.' + stream)).write_bytes(path.read_bytes())

    def kill_direct_child_only(pgid, sig):
        signals.append({'pgid': pgid, 'signal': sig})
        if sig == signal.SIGKILL:
            return tests.os.kill(pgid, sig)
        return killpg(pgid, sig)

    result = unittest.TestResult()
    start = time.monotonic()
    mutation = (mock.patch.object(tests.r.os, 'killpg', kill_direct_child_only)
                if mode == 'negative-direct-child-only' else contextlib.nullcontext())
    with mock.patch.object(tests.subprocess, 'Popen', record_spawn), \
            mock.patch.object(tests.r.Commands, 'run', record_run), mutation:
        tests.RunnerControls(CASE).run(result)
    returned = [{'pid': child.pid, 'returncode': child.returncode,
                 'direct_child_returned': child.returncode is not None} for child in children]
    receipt = {'schema': 1, 'mode': mode, 'test': CASE,
               'at': datetime.now(timezone.utc).isoformat(),
               'elapsed_seconds': time.monotonic() - start,
               'passed': result.wasSuccessful(),
               'failures': [text for _, text in result.failures],
               'errors': [text for _, text in result.errors],
               'commands': commands, 'signals': signals,
               'owned_children': returned, 'waits': waits,
               'all_exact_owned_children_returned': all(row['direct_child_returned'] for row in returned),
               'production_runner_sha256': sha(ROOT / 'scripts/ci/check-analyzer-envelope.py'),
               'test_source_sha256': sha(ROOT / 'scripts/ci/tests/test_analyzer_envelope_runner.py'),
               'scope': 'two directly waitable real group members; no orphan-reaping qualification'}
    write(OUT / (mode + '.json'), receipt)
    print(json.dumps(receipt, indent=2))
    expected = result.wasSuccessful() if mode == 'positive' else not result.wasSuccessful()
    if len(children) != 2 or not expected or not receipt['all_exact_owned_children_returned']:
        raise SystemExit(1)


def suite():
    argv = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts/ci/tests', '-v']
    start = time.monotonic()
    with (OUT / 'host-suite.stdout').open('xb') as stdout, (OUT / 'host-suite.stderr').open('xb') as stderr:
        result = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=120)
    receipt = {'schema': 1, 'command': argv, 'cwd': str(ROOT), 'exit': result.returncode,
               'at': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
               'python_path': sys.executable, 'python_sha256': sha(Path(sys.executable).resolve()),
               'elapsed_seconds': time.monotonic() - start,
               'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'test_source_sha256': sha(ROOT / 'scripts/ci/tests/test_analyzer_envelope_runner.py'),
               'production_runner_sha256': sha(ROOT / 'scripts/ci/check-analyzer-envelope.py'),
               'direct_suite_child_returned': True,
               'scope': 'Python host CI-selection controls only; no native runtime or compiler suite'}
    write(OUT / 'host-suite.json', receipt)
    print(json.dumps(receipt, indent=2))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['positive', 'negative-direct-child-only', 'suite'])
    mode = parser.parse_args().mode
    suite() if mode == 'suite' else focused(mode)
