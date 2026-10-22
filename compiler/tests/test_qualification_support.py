from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qualification_support import (CommandRecorder, clean_environment, digest,
                                   model_observations, strict_json, tool_identity, vm_receipt)


class QualificationTests(unittest.TestCase):
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

    def test_failed_exit_retains_exact_logs_and_binary_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder, commands = self.recorder(folder)
            with self.assertRaises(RuntimeError):
                recorder.run('failed', [sys.executable, '-c', 'import sys; print("before"); sys.stderr.write("reason"); sys.exit(7)'])
            item = commands[0]
            self.assertEqual(item['exitCode'], 7)
            self.assertEqual(Path(folder, 'failed.stdout').read_text(), 'before\n')
            self.assertEqual(item['stdout']['sha256'], digest(Path(folder, 'failed.stdout')))
            self.assertEqual(item['executable'], tool_identity(sys.executable))

    def test_timeout_retains_partial_stdout_and_failure_record(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder, commands = self.recorder(folder)
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                recorder.run('timeout', [sys.executable, '-c', 'import time; print("partial",flush=True); time.sleep(10)'], timeout=.15)
            self.assertTrue(commands[0]['timedOut'])
            self.assertLess(commands[0]['exitCode'], 0)
            self.assertEqual(Path(folder, 'timeout.stdout').read_text(), 'partial\n')

    def test_command_output_and_in_memory_results_are_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            recorder, commands = self.recorder(folder, log_limit=4096, result_limit=1024)
            with self.assertRaisesRegex(RuntimeError, 'log byte limit'):
                recorder.run('flood', [sys.executable, '-c', 'import os; os.write(1,b"x"*100000)'])
            self.assertTrue(commands[0]['outputLimitExceeded'])
            with self.assertRaisesRegex(RuntimeError, 'result byte limit'):
                recorder.run('result', [sys.executable, '-c', 'print("x"*2048)'])
            self.assertEqual(commands[1]['exitCode'], 0)

    def test_changed_executable_fails_even_with_successful_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            tool = Path(folder, 'tool')
            # The local tool deliberately mutates its own source as the regression.
            tool.write_text('#!/bin/sh\nprintf "# mutation\\n" >> "$0"\nprintf "passed\\n"\n')
            tool.chmod(0o700)
            recorder, commands = self.recorder(folder)
            with self.assertRaisesRegex(RuntimeError, 'executable changed'):
                recorder.run('mutation', [tool])
            self.assertEqual(commands[0]['exitCode'], 0)


if __name__ == '__main__':
    unittest.main()
