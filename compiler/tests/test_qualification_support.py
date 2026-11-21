from contextlib import contextmanager
from pathlib import Path
import errno
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qualification_support import (CommandRecorder, clean_environment, digest,
                                   model_observations, strict_json, tool_identity, vm_receipt)
from swift_support_matrix import OUTPUT, render


class QualificationTests(unittest.TestCase):
    def test_public_swift_support_matrix_matches_its_test_mapping(self):
        self.assertEqual(OUTPUT.read_text(encoding='utf-8'), render(),
                         'Run python3 -B compiler/swift_support_matrix.py')

    def test_ambiguous_json_and_nonfinite_numbers_rejected(self):
        for value in ['{"valid":false,"valid":true}', '{"nested":{"x":1,"x":2}}', 'NaN', 'Infinity']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                strict_json(value)

    def test_model_receipts_require_actual_corpus_expectations(self):
        expected = {'status': 'passed', 'taskCount': 1000, 'completionBasisPoints': 5000,
                    'codableRoundTrip': True, 'unicodePreserved': True, 'reordered': True,
                    'committedEntries': 1, 'pendingChanges': 1503, 'emptyTitleRejected': True,
                    'repeatedCommitRejected': True, 'reportIncludesEntry': True}
        self.assertEqual(model_observations(expected), expected)
        for value in [{}, dict(expected, pendingChanges=1502), dict(expected, codableRoundTrip=1),
                      dict(expected, extra='ignored')]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                model_observations(value)

    def test_vm_receipts_match_exit_profile_and_complete_inventory(self):
        accepted = {'profile': 'mixer-integer-v1', 'valid': True, 'inventory_complete': True,
                    'imports': [], 'exports': [], 'opcodes': [], 'extended_opcodes': [],
                    'error': None, 'inventory_error': None}
        rejected = dict(accepted, valid=False, error={'code': 'limit', 'message': 'too large'})
        self.assertEqual(vm_receipt(accepted, 0), accepted)
        self.assertEqual(vm_receipt(rejected, 2), rejected)
        for value, exit_code in [(accepted, 2), (rejected, 0), (dict(accepted, valid=1), 0),
                                 (dict(accepted, profile='unknown'), 0),
                                 (dict(accepted, inventory_complete=False), 0),
                                 (dict(rejected, error=None), 2), (dict(accepted, extra=True), 0)]:
            with self.subTest(value=value, exit_code=exit_code), self.assertRaises(ValueError):
                vm_receipt(value, exit_code)

    def test_clean_environment_removes_code_injection_and_tool_overrides(self):
        value = clean_environment({'HOME': '/tmp/home', 'PATH': '/usr/bin', 'LANG': 'C',
                                   'LC_ALL': 'C', 'NODE_OPTIONS': '--require evil.js',
                                   'DYLD_INSERT_LIBRARIES': 'evil.dylib', 'LD_PRELOAD': 'evil.so',
                                   'SWIFT_EXEC': 'fake', 'DEVELOPER_DIR': 'ambient',
                                   'SWIFTPM_CUSTOM_BIN_DIR': 'fake', 'MIXER_VM': 'fake'})
        self.assertEqual(value, {'HOME': '/tmp/home', 'PATH': '/usr/bin', 'LANG': 'C', 'LC_ALL': 'C'})

    def recorder(self, folder, **kwargs):
        commands = []
        return CommandRecorder(folder, commands, folder, **kwargs), commands

    @contextmanager
    def owned_recorder(self, **kwargs):
        folder = Path(tempfile.mkdtemp(prefix='qualification-recorder-'))
        recorder, commands = self.recorder(folder, **kwargs)
        try:
            yield folder, recorder, commands
        finally:
            unknown_groups = [item.get('pgid') for item in commands
                              if item['terminalCustody'] == 'UNKNOWN']
            if unknown_groups:
                self.fail(f'UNKNOWN command custody for groups {unknown_groups}. Preserved {folder}')
            shutil.rmtree(folder)

    def test_failed_exit_retains_exact_logs_and_binary_identity(self):
        with self.owned_recorder() as (folder, recorder, commands):
            with self.assertRaises(RuntimeError):
                recorder.run('failed', [sys.executable, '-c', 'import sys; print("before"); sys.stderr.write("reason"); sys.exit(7)'],
                             timeout=1)
            item = commands[0]
            self.assertEqual(item['exitCode'], 7)
            self.assertEqual(Path(folder, 'failed.stdout').read_text(), 'before\n')
            self.assertEqual(item['stdout']['sha256'], digest(Path(folder, 'failed.stdout')))
            self.assertEqual(item['executable'], tool_identity(sys.executable))

    def test_denied_log_limit_stop_records_unknown_without_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder, commands = self.recorder(folder, log_limit=4)
            child = Mock(pid=314, **{'poll.return_value': None})

            def launch(*args, stdout, stderr, **kwargs):
                self.assertTrue(kwargs['start_new_session'])
                stdout.write(b'overflow')
                stdout.flush()
                stderr.write(b'partial')
                return child

            with (patch('qualification_support._QualificationProcess', side_effect=launch),
                  patch('qualification_support.os.killpg',
                        side_effect=PermissionError(errno.EPERM, 'kill denied')) as killpg):
                with self.assertRaisesRegex(RuntimeError, 'log byte limit.*UNKNOWN'):
                    recorder.run('denied-flood', [sys.executable])

            killpg.assert_called_once_with(child.pid, signal.SIGKILL)
            child.poll.assert_called_once()
            child.wait.assert_not_called()
            item = commands[0]
            self.assertTrue(item['outputLimitExceeded'])
            self.assertEqual(item['terminalCustody'], 'UNKNOWN')
            self.assertEqual(item['pgid'], child.pid)
            self.assertIsNone(item['exitCode'])
            self.assertIn('kill denied', item['cleanupError'])
            self.assertIn('elapsedSeconds', item)
            self.assertEqual(item['stdout'], {'path': 'denied-flood.stdout', 'bytes': 8})
            self.assertEqual(Path(folder, item['stderr']['path']).read_bytes(), b'partial')

    def test_cleanup_failures_keep_command_error_and_evidence(self):
        for cleanup_error in (PermissionError(errno.EPERM, 'kill denied'),
                              subprocess.TimeoutExpired('stub', 3)):
            with self.subTest(cleanup_error=cleanup_error), tempfile.TemporaryDirectory() as folder:
                recorder, commands = self.recorder(folder)
                child = Mock(pid=314, **{'poll.return_value': None})
                signal_error = cleanup_error if isinstance(cleanup_error, PermissionError) else None
                child.wait.side_effect = cleanup_error
                with (patch('qualification_support._QualificationProcess', return_value=child),
                      patch('qualification_support.os.fstat',
                            side_effect=OSError(errno.EIO, 'log measurement failed')),
                      patch('qualification_support.os.killpg', side_effect=signal_error) as killpg):
                    with self.assertRaisesRegex(OSError, 'log measurement failed'):
                        recorder.run('measurement', [sys.executable])

                killpg.assert_called_once_with(child.pid, signal.SIGKILL)
                if signal_error:
                    child.wait.assert_not_called()
                else:
                    self.assertGreater(child.wait.call_args.kwargs['timeout'], 0)
                    child.wait.assert_called_once()
                item = commands[0]
                self.assertEqual(item['terminalCustody'], 'UNKNOWN')
                self.assertIn(str(cleanup_error), item['cleanupError'])
                self.assertIn('elapsedSeconds', item)
                self.assertEqual(item['stdout']['bytes'], 0)

    def test_evidence_read_failure_preserves_other_log_and_terminal_status(self):
        for exit_code, message in [(7, r'failed \(7\)'), (0, 'log evidence')]:
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as folder:
                recorder, commands = self.recorder(folder)
                child = Mock(pid=314, **{'poll.return_value': exit_code})

                def hash_log(path):
                    if Path(path).name == 'digest.stdout':
                        raise OSError(errno.EIO, 'evidence read failed')
                    return digest(path)

                with (patch('qualification_support._QualificationProcess', return_value=child),
                      patch('qualification_support.os.killpg', side_effect=ProcessLookupError) as killpg,
                      patch('qualification_support.digest', side_effect=hash_log)):
                    with self.assertRaisesRegex(RuntimeError, message):
                        recorder.run('digest', [sys.executable])

                killpg.assert_called_once_with(child.pid, 0)
                item = commands[0]
                self.assertEqual(item['terminalCustody'], 'TERMINAL')
                self.assertEqual(item['exitCode'], exit_code)
                self.assertIn('evidence read failed', item['stdout']['error'])
                self.assertEqual(item['stderr']['sha256'], digest(Path(folder, 'digest.stderr')))

    def test_log_creation_failure_retains_first_log_without_launching(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder, commands = self.recorder(folder)
            open_log = Path.open

            def fail_stderr(path, mode='r', *args, **kwargs):
                if path.name == 'write.stderr' and mode == 'xb':
                    raise OSError(errno.ENOSPC, 'log creation failed')
                return open_log(path, mode, *args, **kwargs)

            with (patch.object(Path, 'open', fail_stderr),
                  patch('qualification_support._QualificationProcess') as launch):
                with self.assertRaisesRegex(OSError, 'log creation failed'):
                    recorder.run('write', [sys.executable])

            launch.assert_not_called()
            item = commands[0]
            self.assertEqual(item['terminalCustody'], 'NOT_STARTED')
            self.assertEqual(item['stdout']['sha256'], digest(Path(folder, 'write.stdout')))
            self.assertNotIn('stderr', item)

    def test_denied_group_observation_is_unknown_after_child_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder, commands = self.recorder(folder)
            child = Mock(pid=314, **{'poll.return_value': 0})
            with (patch('qualification_support._QualificationProcess', return_value=child),
                  patch('qualification_support.os.killpg',
                        side_effect=PermissionError(errno.EPERM, 'observation denied')) as killpg):
                with self.assertRaisesRegex(RuntimeError, 'UNKNOWN'):
                    recorder.run('denied-observation', [sys.executable])

            killpg.assert_called_once_with(child.pid, 0)
            child.wait.assert_not_called()
            self.assertEqual(commands[0]['exitCode'], 0)
            self.assertEqual(commands[0]['terminalCustody'], 'UNKNOWN')

    def test_timeout_retains_partial_stdout_and_failure_record(self):
        with self.owned_recorder() as (folder, recorder, commands):
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                recorder.run('timeout', [sys.executable, '-c', 'import time; print("partial",flush=True); time.sleep(10)'], timeout=.15)
            self.assertTrue(commands[0]['timedOut'])
            self.assertLess(commands[0]['exitCode'], 0)
            self.assertEqual(Path(folder, 'timeout.stdout').read_text(), 'partial\n')

    def test_command_output_and_in_memory_results_are_bounded(self):
        with self.owned_recorder(log_limit=4096, result_limit=1024) as (_, recorder, commands):
            with self.assertRaisesRegex(RuntimeError, 'log byte limit'):
                recorder.run('flood', [sys.executable, '-c', 'import os; os.write(1,b"x"*100000)'], timeout=1)
            self.assertTrue(commands[0]['outputLimitExceeded'])
            self.assertEqual(commands[0]['terminalCustody'], 'TERMINAL')
            with self.assertRaisesRegex(RuntimeError, 'result byte limit'):
                recorder.run('result', [sys.executable, '-c', 'print("x"*2048)'], timeout=1)
            self.assertEqual(commands[1]['exitCode'], 0)

    def test_changed_executable_fails_even_with_successful_exit(self):
        with self.owned_recorder() as (folder, recorder, commands):
            tool = Path(folder, 'tool')
            # The local tool deliberately mutates its own source as the regression.
            tool.write_text('#!/bin/sh\nprintf "# mutation\\n" >> "$0"\nprintf "passed\\n"\n')
            tool.chmod(0o700)
            with self.assertRaisesRegex(RuntimeError, 'executable changed'):
                recorder.run('mutation', [tool], timeout=1)
            self.assertEqual(commands[0]['exitCode'], 0)


if __name__ == '__main__':
    unittest.main()
