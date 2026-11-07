"""Pure Python review reproductions, not toolchain qualification or fixed tests."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location(
    'reviewed_generated_java', ROOT / 'scripts/ci/check-android-generated-java.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class ReviewReproductions(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='owned-review-', dir=HERE)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_cleanup_exception_loses_command_terminal_receipt(self):
        commands = M.Commands(self.root, os.environ.copy(), seconds=3,
                              command_seconds=0.1)
        children = []
        real_popen, real_killpg = subprocess.Popen, os.killpg

        def popen(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child

        try:
            with mock.patch.object(M.subprocess, 'Popen', side_effect=popen), \
                 mock.patch.object(M.os, 'killpg', side_effect=PermissionError('review-injected cleanup unknown')):
                with self.assertRaisesRegex(PermissionError, 'cleanup unknown'):
                    commands.run('owned-python-only', [sys.executable, '-B', '-c',
                        'import time; print("owned",flush=True); time.sleep(5)'])
            self.assertIsNone(commands.records[0]['exit_code'])
            self.assertNotIn('logs', commands.records[0])
            self.assertFalse((self.root / 'commands.json').exists())
            print('REPRODUCED: cleanup exception prevents direct-child reap, pipe closure and commands.json persistence')
        finally:
            for child in children:
                try:
                    real_killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(timeout=3)
                for stream in (child.stdout, child.stderr):
                    if stream is not None:
                        stream.close()
                try:
                    real_killpg(child.pid, 0)
                except ProcessLookupError:
                    continue
                raise AssertionError('Owned review child group did not disappear')

    def fake_execute_to_producer(self, *, cleanup_unknown):
        paths = {k: self.root / k for k in ('swift', 'swift_sdks', 'android_artifact', 'jdk', 'android_sdk')}
        inspection = {'schema': 1, 'sdk_id': 'aarch64-unknown-linux-android28',
            'min_api': 28, 'target_api': 37, 'javac_version': 'javac 25.review-control',
            'tools': {'swift': {'path': str(paths['swift'])},
                      'javac': {'path': str(paths['jdk'] / 'bin/javac')}},
            'distributions': {'android_platform': {'path': str(paths['android_sdk'] / 'platforms/android-37.0')}}}
        jar = paths['android_sdk'] / 'platforms/android-37.0/android.jar'
        jar.parent.mkdir(parents=True)
        jar.write_bytes(b'review-dummy-never-compiled')
        observed = {}

        def run(_self, label, argv, **kwargs):
            if label == 'official-inspect':
                return json.dumps(inspection)
            if label.endswith('-producer-build'):
                observed['argv'] = list(map(str, argv))
                scratch = Path(argv[argv.index('--scratch-path') + 1]).parent
                observed['scratch'] = str(scratch)
                (scratch / 'custody-sentinel').write_text('retain on unknown cleanup')
                if cleanup_unknown:
                    raise PermissionError('review-injected owned group cleanup unknown')
                raise RuntimeError('review stops before any real producer')
            return 'review-dummy-identity'

        with mock.patch.object(M, 'tool_environment', return_value=(paths, {})), \
             mock.patch.object(M.sys, 'platform', 'darwin'), \
             mock.patch.object(M.Commands, 'run', run):
            receipt = M.execute(SimpleNamespace(output=self.root / 'evidence', execute_toolchains=True))
        return receipt, observed

    def test_execute_deletes_scratch_when_cleanup_is_unknown(self):
        receipt, observed = self.fake_execute_to_producer(cleanup_unknown=True)
        self.assertIn('cleanup unknown', receipt['error'])
        self.assertEqual(receipt['status'], 'failed')
        self.assertTrue(receipt['cleanup']['owned_scratch_removed'])
        self.assertFalse(Path(observed['scratch']).exists())
        print('REPRODUCED: execute deletes custody sentinel despite unknown owned group cleanup')

    def test_producer_argv_has_no_explicit_job_bound(self):
        _, observed = self.fake_execute_to_producer(cleanup_unknown=False)
        self.assertFalse(any(a == '--jobs' or a.startswith('--jobs=') or a == '-j' or a.startswith('-j')
                             for a in observed['argv']))
        print('REPRODUCED: producer argv has no -j/--jobs bound:', json.dumps(observed['argv']))

    def test_successful_python_command_omits_terminal_custody_facts(self):
        commands = M.Commands(self.root, os.environ.copy(), seconds=3, command_seconds=1)
        self.assertEqual(commands.run('owned-python-success', [sys.executable, '-B', '-c', 'print("ok")']), 'ok\n')
        record = commands.records[0]
        self.assertEqual(record['exit_code'], 0)
        self.assertNotIn('pid', record)
        self.assertNotIn('pgid', record)
        self.assertNotIn('stdout_eof', record)
        self.assertNotIn('stderr_eof', record)
        self.assertNotIn('owned_group_absent', record)
        print('REPRODUCED: successful command receipt has signal/reap result but no PGID, EOF or group-absence observation')


if __name__ == '__main__':
    unittest.main(verbosity=2)
