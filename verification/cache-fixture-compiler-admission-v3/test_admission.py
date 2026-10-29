#!/usr/bin/env python3
"""Pure actual admission methods plus exact workflow source controls; no rustup."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
import offline_guard
offline_guard.install(HERE)

from datetime import datetime, timezone
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
import compiler_admission as admission
import verify_candidate as verifier

WORKFLOW_SHA256 = 'eba3999e14305e3b4edcca6046536087f129a82598af195aa1db1239a453e25c'


class AdmissionControls(unittest.TestCase):
    def setUp(self):
        self.scratch = HERE / 'control-scratch'
        self.scratch.mkdir(exist_ok=True)
        self.owner = Path(tempfile.mkdtemp(dir=self.scratch))
        self.logs = self.owner / 'logs'
        self.logs.mkdir()
        self.env = {
            'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'macOS', 'RUNNER_ARCH': 'ARM64',
            'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_RUN_ID': '101', 'GITHUB_SHA': 'a' * 40,
            'RUSTUP_TOOLCHAIN': admission.TOOLCHAIN, 'RUSTUP_AUTO_INSTALL': '0',
            'RUSTUP_DIST_SERVER': 'https://static.rust-lang.org',
            'RUSTUP_UPDATE_ROOT': 'https://static.rust-lang.org/rustup',
            'RUNNER_TEMP': str(self.owner),
            'RUSTUP_HOME': str(self.owner / 'mixer-fixture-rustup-101-1')}

    def tearDown(self):
        shutil.rmtree(self.owner)
        if not any(self.scratch.iterdir()):
            self.scratch.rmdir()

    def streams(self):
        for name in ['rustup-version.stdout', 'rustup-version.stderr',
                     'rustup-install.stdout', 'rustup-install.stderr']:
            (self.logs / name).write_text('synthetic pure control output\n')

    def prepared(self, status=0):
        admission.begin(self.env, self.logs)
        self.streams()
        return admission.finish(self.env, self.logs, status)

    def test_success_claim_exactly_once(self):
        self.prepared()
        admission.claim(self.env, self.logs)
        with self.assertRaises(FileExistsError):
            admission.claim(self.env, self.logs)

    def test_missing_install_result_cannot_launch(self):
        admission.begin(self.env, self.logs)
        with self.assertRaises(FileNotFoundError):
            admission.claim(self.env, self.logs)

    def test_install_failure_is_retained_and_cannot_launch(self):
        with self.assertRaisesRegex(RuntimeError, 'install failed'):
            self.prepared(1)
        self.assertEqual(admission.read_json(self.logs / 'provision-result.json')['install_exit'], 1)
        with self.assertRaisesRegex(RuntimeError, 'Successful explicit install'):
            admission.claim(self.env, self.logs)

    def test_interrupted_install_no_hidden_retry(self):
        admission.begin(self.env, self.logs)
        with self.assertRaisesRegex(RuntimeError, 'already attempted'):
            admission.begin(self.env, self.logs)
        with self.assertRaises(FileNotFoundError):
            admission.claim(self.env, self.logs)

    def test_failed_install_no_hidden_retry(self):
        with self.assertRaises(RuntimeError):
            self.prepared(124)
        with self.assertRaisesRegex(RuntimeError, 'already attempted'):
            admission.begin(self.env, self.logs)
        with self.assertRaises(FileExistsError):
            admission.finish(self.env, self.logs, 0)

    def test_no_fallback_compiler(self):
        self.env['RUSTUP_TOOLCHAIN'] = '1.99.0-aarch64-apple-darwin'
        with self.assertRaisesRegex(RuntimeError, 'Exact compiler'):
            admission.begin(self.env, self.logs)

    def test_auto_install_rejected(self):
        self.env['RUSTUP_AUTO_INSTALL'] = '1'
        with self.assertRaisesRegex(RuntimeError, 'Exact compiler'):
            admission.begin(self.env, self.logs)

    def test_local_execution_rejected(self):
        self.env.pop('GITHUB_ACTIONS')
        with self.assertRaisesRegex(RuntimeError, 'Remote GitHub'):
            admission.begin(self.env, self.logs)

    def test_wrong_host_and_rerun_rejected(self):
        for key, value in [('RUNNER_OS', 'Linux'), ('RUNNER_ARCH', 'X64'),
                           ('GITHUB_RUN_ATTEMPT', '2')]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                admission.context({**self.env, key: value})

    def test_nonofficial_distribution_rejected(self):
        for key in ['RUSTUP_DIST_SERVER', 'RUSTUP_UPDATE_ROOT']:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                admission.context({**self.env, key: 'https://example.invalid'})

    def test_shared_or_reused_home_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'Exact job-owned'):
            admission.context({**self.env, 'RUSTUP_HOME': str(self.owner)})
        Path(self.env['RUSTUP_HOME']).mkdir()
        with self.assertRaisesRegex(RuntimeError, 'Fresh job-owned'):
            admission.begin(self.env, self.logs)

    def test_cross_run_receipt_rejected(self):
        self.prepared()
        self.env['GITHUB_SHA'] = 'b' * 40
        with self.assertRaisesRegex(RuntimeError, 'context changed'):
            admission.claim(self.env, self.logs)

    def test_missing_output_and_tampered_output_rejected(self):
        admission.begin(self.env, self.logs)
        with self.assertRaisesRegex(RuntimeError, 'Missing regular'):
            admission.finish(self.env, self.logs, 0)
        self.streams()
        admission.finish(self.env, self.logs, 0)
        (self.logs / 'rustup-install.stderr').write_text('mutated')
        with self.assertRaisesRegex(RuntimeError, 'evidence changed'):
            admission.claim(self.env, self.logs)

    def test_finish_requires_begin(self):
        self.streams()
        with self.assertRaises(FileNotFoundError):
            admission.finish(self.env, self.logs, 0)

    def test_status_validation(self):
        admission.begin(self.env, self.logs)
        for status in [None, True, -1, 256, '0']:
            with self.subTest(status=status), self.assertRaisesRegex(RuntimeError, 'Shell exit'):
                admission.finish(self.env, self.logs, status)

    def test_source_member_mutation_rejected(self):
        target = self.owner / 'source'
        target.mkdir()
        data = b'expected\n'
        (target / 'one.txt').write_bytes(data)
        (target / 'seal.json').write_text('{}')
        rows = [{'path': 'one.txt', 'bytes': len(data), 'sha256': verifier.digest(data)}]
        seal = {'members': rows, 'member_count': 1, 'total_bytes': len(data),
                'tree_sha256': verifier.digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())}
        verifier.verify_members(target, seal)
        (target / 'one.txt').write_bytes(b'different\n')
        with self.assertRaisesRegex(RuntimeError, 'Bound member differs'):
            verifier.verify_members(target, seal)

    def test_workflow_source_order_pin_and_no_hidden_retry(self):
        workflow = (HERE / 'workflow/cache-fixture-compiler-admission-v3.yml').read_bytes()
        self.assertEqual(hashlib.sha256(workflow).hexdigest(), WORKFLOW_SHA256)
        source = workflow.decode()
        ordered = ['verify_candidate.py" --workflow-installed', 'materialize_pack.py"',
                   'test_admission.py"', 'test_materializer.py"', 'test_runner.py"',
                   'compiler_admission.py" begin', 'rustup --version',
                   ' '.join(admission.INSTALL_ARGV), 'compiler_admission.py" finish',
                   'compiler_admission.py" claim', 'check_cache_state.py"']
        positions = [source.index(marker) for marker in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(source.count('rustup toolchain install '), 1)
        self.assertEqual(source.count('check_cache_state.py" \\'), 1)
        installer = source.split('      - name: Explicitly provision')[1].split('      - name:')[0]
        self.assertIn('timeout-minutes: 2', installer)
        self.assertNotIn('if:', installer)
        fixture = source.split('      - name: One complete fixture')[1].split('      - name:')[0]
        self.assertNotIn('if:', fixture)
        for forbidden in ['continue-on-error', '||', 'until ', 'while ', 'rustup update', 'rustup default']:
            self.assertNotIn(forbidden, source)
        self.assertIn('timeout-minutes: 12', fixture)
        self.assertIn("RUSTUP_AUTO_INSTALL: '0'", source)
        self.assertIn('/.github/workflows/cache-fixture-shared-input-controls-v2.yml', source)
        self.assertIn('/.github/workflows/cache-fixture-compiler-admission-v3.yml', source)

    def test_full_frozen_source_closure(self):
        result = verifier.verify()
        self.assertEqual(result['frozen_v2_seal_sha256'], verifier.V2_SEAL)


if __name__ == '__main__':
    output = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AdmissionControls)
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    text = output.getvalue()
    print(text, end='')
    logs = HERE / 'logs'
    logs.mkdir(exist_ok=True)
    (logs / 'pure-controls.stdout').write_text(text)
    receipt = {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
        'command': 'python3 -B verification/cache-fixture-compiler-admission-v3/test_admission.py',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'forbidden_operations_attempted': offline_guard.DENIED,
        'control_scratch_absent': not (HERE / 'control-scratch').exists(),
        'scope': 'Actual file-only admission methods and source bindings; no compiler or install executed',
        'real_rustup_provisioning_and_103_command_fixture': 'pending',
        'workflow_execution_and_bash_syntax_validation': 'pending remote GitHub Actions',
        'workflow_sha256': WORKFLOW_SHA256}
    (logs / 'pure-controls.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    sys.exit(0 if result.wasSuccessful() and not offline_guard.DENIED else 1)
