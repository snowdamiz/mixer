#!/usr/bin/env python3
"""Pure controls for ordinary fixture adoption; imports follow the operation guard."""
from pathlib import Path
import sys
import unittest
from unittest import mock
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from offline_guard import install, DENIED
install(HERE)

import importlib.util
import json
import tempfile

spec = importlib.util.spec_from_file_location('fixture_adoption', HERE / 'adopt_fixture.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def identity(release='1.98.1', host='aarch64-apple-darwin'):
    commit = '48a229ceaefd4985c50990b14116b6d856af0985'
    return (f'rustc {release} ({commit[:9]} 2026-09-01)\n'
            f'binary: rustc\ncommit-hash: {commit}\ncommit-date: 2026-09-01\n'
            f'host: {host}\nrelease: {release}\nLLVM version: 22.1.8\n')


class AdoptionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner, cls.base, cls.proof = a.load_runner()

    def test_complete_exact_source_closure(self):
        proof = a.verify()
        self.assertEqual(proof['fixture_source']['accepted_shared_input_source_sha256'],
                         'f7d62c01e251642677e22f7595af9683f9c451f1db43683be5d2ef86fedba141')
        self.assertEqual(proof['compiler_policy']['allowlist'],
                         [['aarch64-apple-darwin', '1.99.0'], ['aarch64-apple-darwin', '1.98.1']])
        self.assertFalse(proof['installed_job_verified'])

    def test_exact_existing_validator_object_and_globals(self):
        self.assertIs(self.runner.rust_identity, self.base.rust_identity)
        self.assertIs(self.runner.rust_identity.__globals__, self.base.__dict__)
        self.assertEqual(Path(self.runner.rust_identity.__code__.co_filename), a.BASE_RUNNER)
        self.assertEqual(self.runner.__file__, str(a.V2 / 'check_cache_state.py'))
        self.assertEqual((self.runner.CHILD_SECONDS, self.runner.ACTIVE_SECONDS,
                          self.runner.CLEANUP_SECONDS, self.runner.OUTPUT_CAP),
                         (60, 600, 60, 8388608))

    def test_both_existing_compiler_releases_admitted_as_data(self):
        for release in ['1.98.1', '1.99.0']:
            with self.subTest(release=release):
                self.assertEqual(self.runner.rust_identity(identity(release))['release'], release)

    def test_new_or_nightly_compiler_not_a_fallback(self):
        for value in [identity('1.100.0'), identity().replace('1.98.1', '1.98.1-nightly')]:
            with self.assertRaises(RuntimeError):
                self.runner.rust_identity(value)

    def test_wrong_compiler_platform_rejected(self):
        for host in ['x86_64-apple-darwin', 'aarch64-unknown-linux-gnu']:
            with self.assertRaises(RuntimeError):
                self.runner.rust_identity(identity(host=host))

    def test_compiler_incoherence_duplicate_missing_fields_rejected(self):
        valid = identity()
        invalid = [valid.replace('release: 1.98.1', 'release: 1.99.0'),
                   valid + 'host: aarch64-apple-darwin\n',
                   valid.replace('LLVM version: 22.1.8\n', ''),
                   valid.replace('commit-hash: 48a', 'commit-hash: 111'),
                   valid.replace('commit-date: 2026-09-01', 'commit-date: 2026-09-02')]
        for value in invalid:
            with self.assertRaises(RuntimeError):
                self.runner.rust_identity(value)

    def test_frozen_v2_exact_compiler_validator_is_unchanged(self):
        original = a.module_at('unadapted_v2_control', a.V2 / 'check_cache_state.py')
        self.assertEqual(original.rust_identity(identity())['release'], '1.98.1')
        with self.assertRaises(RuntimeError):
            original.rust_identity(identity('1.99.0'))

    def test_source_mutation_is_rejected_before_import(self):
        original_sha = a.sha
        with mock.patch.object(a, 'sha', side_effect=lambda p: '0' * 64 if p == a.BASE_RUNNER else original_sha(p)), \
             mock.patch.object(a, 'module_at') as importer:
            with self.assertRaises(RuntimeError):
                a.load_runner()
            importer.assert_not_called()

    def test_installed_job_is_exact_and_unrelated_job_is_independent(self):
        job = (HERE / 'workflow/swift-cache-state-fixture.yml').read_text()
        document = 'name: Checks\njobs:\n  other:\n    runs-on: ubuntu-24.04\n' + job + '  later:\n    runs-on: macos-15\n'
        self.assertEqual(a.job_text(document), job)
        with mock.patch.object(a, 'WORKFLOW', HERE / 'workflow/swift-cache-state-fixture.yml'):
            self.assertTrue(a.verify(installed=True)['installed_job_verified'])
        with mock.patch.object(a, 'WORKFLOW', HERE / 'workflow/original-job.yml'):
            with self.assertRaises(RuntimeError):
                a.verify(installed=True)

    def test_duplicate_or_absent_job_rejected(self):
        job = (HERE / 'workflow/swift-cache-state-fixture.yml').read_text()
        for document in ['jobs:\n  other:\n', job + job]:
            with self.assertRaises(RuntimeError):
                a.job_text(document)

    def test_sparse_checkout_covers_every_runtime_dependency(self):
        job = (HERE / 'workflow/swift-cache-state-fixture.yml').read_text()
        sparse = job.split('          sparse-checkout: |\n', 1)[1].split('      - name:', 1)[0]
        entries = [line.strip().lstrip('/') for line in sparse.splitlines() if line.strip()]
        dependencies = json.loads((HERE / 'dependencies.json').read_text())['members']
        for row in dependencies:
            self.assertTrue(any(row['path'] == entry or
                                (entry.endswith('/') and row['path'].startswith(entry))
                                for entry in entries), row['path'])
        self.assertNotIn('/verification/cache-fixture-compiler-admission-v3/', sparse)
        self.assertNotIn('/verification/cache-fixture-workflow-context-v4/', sparse)

    def test_workflow_has_one_invocation_no_install_and_always_postflight_archive(self):
        job = (HERE / 'workflow/swift-cache-state-fixture.yml').read_text()
        self.assertEqual(job.count('adopt_fixture.py" run '), 1)
        self.assertEqual(job.count('test_runner.py"'), 1)
        self.assertEqual(job.count('test_materializer.py"'), 1)
        self.assertEqual(job.count('adopt_fixture.py" verify --workflow-installed'), 2)
        for forbidden in ['rustup toolchain install', 'RUSTUP_TOOLCHAIN:', 'RUSTUP_HOME:',
                          'continue-on-error:', 'retry', 'timeout-minutes: 13']:
            self.assertNotIn(forbidden, job)
        self.assertEqual(job.count('        if: always()'), 2)
        self.assertIn("      RUSTUP_AUTO_INSTALL: '0'", job)
        self.assertIn('          include-hidden-files: true', job)
        self.assertIn('          retention-days: 14', job)

    def test_github_context_placement_source_check(self):
        job = (HERE / 'workflow/swift-cache-state-fixture.yml').read_text()
        job_env = job.split('    env:\n', 1)[1].split('    steps:', 1)[0]
        opener = chr(36) + '{{'
        self.assertNotIn(opener, job_env)
        self.assertNotIn(opener + ' runner.', job)
        # All candidate expressions are github properties in step/action inputs,
        # where the recorded official GitHub context table admits github.
        for fragment in job.split(opener)[1:]:
            expression = fragment.split('}}', 1)[0].strip()
            self.assertIn(expression, {'github.sha', 'github.run_id',
                                       'github.run_attempt', 'github.workspace'})

    def test_rejected_install_policy_before_fixture_or_output_creation(self):
        with mock.patch.dict(a.os.environ, {'RUSTUP_AUTO_INSTALL': '1'}), \
             mock.patch.object(a, 'load_runner') as load:
            with self.assertRaises(RuntimeError):
                a.run_fixture(HERE / 'never-created', '/synthetic/rustc')
            load.assert_not_called()
        self.assertFalse((HERE / 'never-created').exists())

    def test_fake_failure_is_not_retried_and_records_actual_compiler(self):
        self.run_synthetic(1, '1.99.0')

    def test_fake_success_records_selected_compiler_and_adapter_source(self):
        self.run_synthetic(0, '1.98.1')

    def run_synthetic(self, status, release):
        scratch = HERE / 'control-scratch'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch, prefix='synthetic-') as temporary:
            runs = Path(temporary) / 'runs'
            runs.mkdir()
            output = runs / 'one'
            real_verify = a.verify
            observed_compiler = {'identity': {'host': 'aarch64-apple-darwin', 'release': release},
                                 'scope': 'synthetic data only; compiler not run'}
            def fake_execute(out, requested):
                self.assertEqual(requested, '/synthetic/rustc')
                self.runner.save(out / 'receipt.json',
                                 {'status': 'synthetic-return', 'rustc': observed_compiler})
                return status
            with mock.patch.dict(a.os.environ, {'RUSTUP_AUTO_INSTALL': '0'}), \
                 mock.patch.object(a, 'verify', side_effect=lambda installed=False: real_verify(False)), \
                 mock.patch.object(a, 'load_runner', return_value=(self.runner, self.base, self.proof)), \
                 mock.patch.object(self.runner, 'RUNS', runs), \
                 mock.patch.object(self.runner, 'execute', side_effect=fake_execute) as execute:
                self.assertEqual(a.run_fixture(output, '/synthetic/rustc'), status)
                execute.assert_called_once()
            result = json.loads((output / 'adapter-result.json').read_text())
            start = json.loads((output / 'adapter-start.json').read_text())
            self.assertEqual(result['actual_compiler'], observed_compiler)
            self.assertEqual(result['fixture_return_status'], status)
            self.assertTrue(start['identity_validator_reused_exact_function'])
            self.assertEqual(a.sha(output / 'executed-adapter.py'), a.sha(HERE / 'adopt_fixture.py'))

    @classmethod
    def tearDownClass(cls):
        scratch = HERE / 'control-scratch'
        if scratch.is_dir():
            if list(scratch.iterdir()):
                raise RuntimeError('Control scratch not empty')
            scratch.rmdir()
        if DENIED:
            raise RuntimeError('Unexpected blocked operation attempts: ' + repr(DENIED))


if __name__ == '__main__':
    program = unittest.main(exit=False)
    print(json.dumps({'schema': 1, 'tests': program.result.testsRun,
                      'passed': program.result.wasSuccessful(), 'python': sys.version,
                      'python_executable': sys.executable, 'denied_operation_attempts': DENIED,
                      'control_scratch_absent': not (HERE / 'control-scratch').exists(),
                      'compiler_runtime_or_fixture_executed': False,
                      'scope': 'Guarded pure source/contract controls; synthetic invocation tests only'},
                     sort_keys=True))
    sys.exit(0 if program.result.wasSuccessful() else 1)
