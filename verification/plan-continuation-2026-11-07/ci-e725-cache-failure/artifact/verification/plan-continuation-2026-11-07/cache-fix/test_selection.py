#!/usr/bin/env python3
"""Bounded pure/fake-child checks. No fixture or actual compiler execution."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from offline_guard import DENIED, install
install(HERE)
import adopt_fixture as a


class SelectionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = a.baseline()
        cls.runner, cls.ordinary, _ = cls.old.load_runner()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=HERE, prefix='control-')
        self.scratch = Path(self.temporary.name)
        self.compiler = self.scratch / 'inert-compiler-data'
        self.compiler.write_bytes(b'not executable; fake hash observation only')
        self.evidence = {'path': str(self.compiler), 'sha256': a.COMPILER_SHA256,
                         'identity': dict(a.IDENTITY), 'version_verbose': a.VERBOSE}

    def tearDown(self):
        # Avoid shutil's fd-relative deletion: remove only this owned file tree.
        for path in sorted(self.scratch.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            path.rmdir() if path.is_dir() else path.unlink()
        self.scratch.rmdir()
        self.temporary.cleanup()

    def test_01_baseline_reproduces_actual_refusal(self):
        with self.assertRaisesRegex(RuntimeError, 'Actual compiler host/release not selected'):
            self.ordinary.rust_identity(a.VERBOSE)
        for release in ['1.98.1', '1.99.0']:
            self.assertEqual(self.ordinary.rust_identity(a.VERBOSE.replace('1.99.1', release))['release'], release)

    def test_02_exact_identity_with_matching_fake_binary_observation(self):
        with mock.patch.object(self.runner, 'sha', return_value=a.COMPILER_SHA256) as hashed:
            self.assertEqual(a.select_identity(a.VERBOSE, self.evidence, self.runner), a.IDENTITY)
            hashed.assert_called_once_with(self.compiler)

    def test_03_each_identity_field_and_header_are_exact(self):
        for value in [a.VERBOSE + 'host: aarch64-apple-darwin\n', a.VERBOSE.rstrip(),
                      a.VERBOSE.replace('1.99.1', '1.98.1'),
                      a.VERBOSE.replace('1.99.1', '1.99.1-nightly'),
                      *[a.VERBOSE.replace(f'{key}: {value}\n', f'{key}: changed\n')
                        for key, value in a.IDENTITY.items()]]:
            with self.subTest(value=value), self.assertRaises(RuntimeError), \
                 mock.patch.object(self.runner, 'sha') as hashed:
                try:
                    a.select_identity(value, self.evidence, self.runner)
                finally:
                    hashed.assert_not_called()

    def test_04_wrong_or_changed_binary_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'fingerprint'):
            a.select_identity(a.VERBOSE, self.evidence, self.runner)
        changed = {**self.evidence, 'sha256': '0' * 64}
        with self.assertRaises(RuntimeError), mock.patch.object(self.runner, 'sha') as hashed:
            try:
                a.select_identity(a.VERBOSE, changed, self.runner)
            finally:
                hashed.assert_not_called()

    def test_05_relative_missing_or_symlink_binary_refused(self):
        for name in ['relative-compiler', str(self.scratch / 'missing')]:
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                a.select_identity(a.VERBOSE, {**self.evidence, 'path': name}, self.runner)
        link = self.scratch / 'link'
        link.symlink_to(self.compiler)
        with self.assertRaises(RuntimeError):
            a.select_identity(a.VERBOSE, {**self.evidence, 'path': str(link)}, self.runner)

    def test_06_original_closure_and_new_source_manifest_verify(self):
        proof = a.verify(False)
        self.assertFalse(proof['compiler_qualified'])
        self.assertFalse(proof['installed_job_verified'])
        self.assertEqual(proof['historical_adoption']['compiler_policy']['allowlist'],
                         [['aarch64-apple-darwin', '1.99.0'], ['aarch64-apple-darwin', '1.98.1']])
        self.assertEqual((self.runner.CHILD_SECONDS, self.runner.ACTIVE_SECONDS,
                          self.runner.CLEANUP_SECONDS, self.runner.OUTPUT_CAP),
                         (60, 600, 60, 8388608))

    def test_07_exact_installed_job_and_drift_refusal(self):
        candidate = self.scratch / 'workflow.yml'
        candidate.write_text('jobs:\n' + (HERE / 'workflow/swift-cache-state-fixture.yml').read_text())
        with mock.patch.object(a, 'WORKFLOW', candidate):
            self.assertTrue(a.verify(True)['installed_job_verified'])
            candidate.write_text(candidate.read_text().replace('timeout-minutes: 12', 'timeout-minutes: 13'))
            with self.assertRaises(RuntimeError):
                a.verify(True)

    def test_08_original_controls_and_finite_workflow_are_retained(self):
        before = (a.OLD / 'workflow/swift-cache-state-fixture.yml').read_text()
        after = (HERE / 'workflow/swift-cache-state-fixture.yml').read_text()
        controls = before.split('      - name: Shared fixture runner,', 1)[1].split('      - name:', 1)[0]
        # The three commands/redirections remain together verbatim; one extra
        # source-only control command follows them in the same finite step.
        self.assertIn(controls.rstrip(), after)
        self.assertEqual(after.count('adopt_fixture.py" run '), 1)
        self.assertEqual(after.count('        if: always()'), 2)
        for value in ["      RUSTUP_AUTO_INSTALL: '0'", '    timeout-minutes: 30',
                      '        timeout-minutes: 12', '          retention-days: 14',
                      '          include-hidden-files: true']:
            self.assertIn(value, after)
        for value in ['rustup toolchain install', 'RUSTUP_TOOLCHAIN:', 'continue-on-error:', 'workflow_dispatch:']:
            self.assertNotIn(value, after)

    def test_09_hook_uses_current_receipt_before_compilation(self):
        self.runner.save(self.scratch / 'receipt.json', {'rustc': self.evidence})
        runner = a.load_runner(self.scratch)
        with mock.patch.object(runner, 'sha', return_value=a.COMPILER_SHA256):
            self.assertEqual(runner.rust_identity(a.VERBOSE), a.IDENTITY)
        self.runner.save(self.scratch / 'receipt.json', {'rustc': {**self.evidence, 'sha256': '0' * 64}})
        with self.assertRaises(RuntimeError):
            runner.rust_identity(a.VERBOSE)
        source = Path(runner.__file__).read_text()
        self.assertLess(source.index("receipt['rustc'].update(path="), source.index('selected=rust_identity(verbose)'))
        self.assertLess(source.index('selected=rust_identity(verbose)'), source.index("'source-revision'"))

    def run_fake(self, status=0, raises=False, mutate_snapshot=False, count=103):
        runs = self.scratch / 'runs'
        runs.mkdir()
        output = runs / 'one'
        workflow = self.scratch / 'workflow.yml'
        workflow.write_text('jobs:\n' + (HERE / 'workflow/swift-cache-state-fixture.yml').read_text())
        def execute(out, requested):
            self.assertEqual(requested, '/synthetic/rustc')
            if raises:
                raise RuntimeError('synthetic child failure')
            (out / 'commands').mkdir()
            (out / 'commands/compiler-identity.stdout').write_text(a.VERBOSE)
            self.runner.save(out / 'receipt.json', {
                'status': 'passed-host-fixture-check' if status == 0 else 'failed',
                'active_checks_completed': status == 0, 'errors': [],
                'commands': [{'synthetic': True} for _ in range(count)], 'rustc': self.evidence})
            if mutate_snapshot:
                (out / 'compiler-selection-sources/adopt_fixture.py').write_text('drift')
            return status
        with mock.patch.dict(a.os.environ, {'RUSTUP_AUTO_INSTALL': '0'}), \
             mock.patch.object(a, 'WORKFLOW', workflow), \
             mock.patch.object(a, 'load_runner', return_value=self.runner), \
             mock.patch.object(self.runner, 'RUNS', runs), \
             mock.patch.object(self.runner, 'sha', return_value=a.COMPILER_SHA256), \
             mock.patch.object(self.runner, 'execute', side_effect=execute) as child:
            result = a.run_fixture(output, '/synthetic/rustc')
            child.assert_called_once()
        return result, json.loads((output / 'selection-result.json').read_bytes())

    def test_10_fake_success_requires_full_fixture_and_keeps_qualification_false(self):
        result, receipt = self.run_fake()
        self.assertEqual(result, 0)
        self.assertFalse(receipt['compiler_qualified'])
        self.assertEqual(receipt['errors'], [])

    def test_11_fake_fixture_failure_never_retries(self):
        result, receipt = self.run_fake(status=1)
        self.assertEqual(result, 1)
        self.assertEqual(receipt['fixture_return_status'], 1)

    def test_12_fake_exception_retains_result_and_runs_postflight(self):
        result, receipt = self.run_fake(raises=True)
        self.assertEqual(result, 1)
        self.assertEqual(receipt['errors'][0]['phase'], 'fixture')

    def test_13_snapshot_drift_overrides_fake_success(self):
        result, receipt = self.run_fake(mutate_snapshot=True)
        self.assertEqual(result, 1)
        self.assertIn('Retained selection source changed', receipt['errors'][0]['message'])

    def test_14_partial_fake_fixture_cannot_pass(self):
        result, receipt = self.run_fake(count=102)
        self.assertEqual(result, 1)
        self.assertIn('103-command', receipt['errors'][0]['message'])

    def test_15_auto_install_policy_refuses_before_output(self):
        output = self.scratch / 'never-created'
        with mock.patch.dict(a.os.environ, {'RUSTUP_AUTO_INSTALL': '1'}), \
             self.assertRaises(RuntimeError), mock.patch.object(a, 'load_runner') as load:
            try:
                a.run_fixture(output, '/synthetic/rustc')
            finally:
                load.assert_not_called()
        self.assertFalse(output.exists())

    def test_16_duplicate_json_selection_is_refused(self):
        candidate = self.scratch / 'duplicate.json'
        candidate.write_text('{"release":"1.99.1","release":"1.99.0"}')
        with self.assertRaisesRegex(RuntimeError, 'Duplicate'):
            a.read_json(candidate)

    @classmethod
    def tearDownClass(cls):
        if DENIED:
            raise RuntimeError('Unexpected denied runtime attempts: ' + repr(DENIED))


if __name__ == '__main__':
    program = unittest.main(exit=False)
    print(json.dumps({'tests': program.result.testsRun, 'passed': program.result.wasSuccessful(),
                      'python': sys.version, 'executable': sys.executable,
                      'denied_runtime_attempts': DENIED, 'compiler_or_fixture_executed': False,
                      'scope': 'Pure source/data controls and fake runner invocation; binary hash mocked only in synthetic positives'},
                     sort_keys=True))
    sys.exit(0 if program.result.wasSuccessful() else 1)
