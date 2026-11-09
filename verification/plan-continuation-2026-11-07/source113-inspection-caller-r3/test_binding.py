#!/usr/bin/env python3
"""Pure source controls, with independent denial of processes/groups/sockets."""
from pathlib import Path
import sys
import os
import importlib.util
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('binding_guard', ROOT / 'verification/envelope-rust-1991-default-ci-adoption/offline_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
sys.path.insert(0,str(HERE)); __import__('metadata_guard').install(guard,HERE)
os.chdir(HERE)
sys.path.insert(0, str(HERE))
import adopt_envelope as a
from contextlib import contextmanager
import hashlib
import json
import tempfile
import unittest


@contextmanager
def patched(obj, key, value):
    old = getattr(obj, key)
    setattr(obj, key, value)
    try:
        yield
    finally:
        setattr(obj, key, old)


class BindingControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HERE / 'control-scratch')
        self.addCleanup(self.temp.cleanup)
        self.workflow = Path(self.temp.name) / 'verify.yml'
        self.base = a.bind()

    def installed(self, text):
        self.workflow.write_text(text)
        with patched(a, 'WORKFLOW', self.workflow):
            return self.base.verify(True)

    def test_original_refusal_and_exact_current_caller_delta(self):
        original = a.load()
        with self.assertRaisesRegex(RuntimeError, 'Installed ordinary Swift job differs from sealed candidate'):
            original.verify(True)
        before = (HERE / 'current-verify.yml').read_text()
        prior = HERE.parent / 'source113-sparse-closure-fix-r2'
        self.assertEqual(original.job_text(before), (prior / 'swift-job.yml').read_text())
        expected = original.job_text(before)
        changes = json.loads((HERE / 'job-changes.json').read_text())
        for change in changes:
            self.assertEqual(expected.count(change['before']), change['count'])
            expected = expected.replace(change['before'], change['after'])
        self.assertEqual(expected, (HERE / 'swift-job.yml').read_text())
        self.assertIn(a.CALLER_AFTER, expected)
        self.assertIn('scripts/ci/prepare-cli-host-tests.py', expected)

    def test_actual_current_job_is_intentionally_selected_then_successor_installs(self):
        proof = self.base.verify(False)
        self.assertFalse(proof['installed_job_verified'])
        self.assertFalse(proof['exact_compiler_qualified'])
        self.assertTrue(self.installed((HERE / 'verify.yml.candidate').read_text())['installed_job_verified'])

    def test_unrelated_workflow_mutations_fail_closed(self):
        text = (HERE / 'verify.yml.candidate').read_text()
        for old, new in [('timeout-minutes: 12', 'timeout-minutes: 13'),
                         ('--product mixer -j 2', '--product mixer -j 3'),
                         ('Xcode_26.3.app', 'Xcode_26.6.app'),
                         ('export RUSTUP_AUTO_INSTALL=0', 'export RUSTUP_AUTO_INSTALL=1'),
                         ('--rustc "$MIXER_ENVELOPE_RUSTC_LAUNCHER"', '--rustc /unreviewed/rustc'),
                         ('      - name: Verify prospective envelope adoption source postflight\n        if: always()',
                          '      - name: Verify prospective envelope adoption source postflight\n        if: success()')]:
            self.assertIn(old, text)
            with self.subTest(mutation=old), self.assertRaisesRegex(RuntimeError, 'Installed ordinary'):
                self.installed(text.replace(old, new, 1))

    def test_exact_compiler_and_each_identity_field_refuse_mutations(self):
        self.base.validate_profile(self.base.PROFILE_IDENTITY, self.base.PROFILE_SHA256)
        for key in self.base.PROFILE_IDENTITY:
            changed = dict(self.base.PROFILE_IDENTITY)
            changed[key] += '-changed'
            with self.subTest(field=key), self.assertRaisesRegex(RuntimeError, 'compiler identity'):
                self.base.validate_profile(changed, self.base.PROFILE_SHA256)
        with self.assertRaisesRegex(RuntimeError, 'compiler fingerprint'):
            self.base.validate_profile(self.base.PROFILE_IDENTITY, '0' * 64)

    def test_runner_policy_source_limits_and_selection_remain_original(self):
        runner, ordinary, proof = self.base.load_runner()
        self.assertEqual((runner.OUTPUT_CAP, runner.TOTAL_OUTPUT_CAP), (8388608, 67108864))
        self.assertIs(runner.rustc_identity, ordinary.rustc_identity)
        selected = self.base.selection()
        self.assertEqual(selected['execution']['required_commands'], 40)
        self.assertEqual(selected['execution']['active_seconds'], 480)
        self.assertEqual(selected['execution']['retention_cleanup_seconds'], 60)
        self.assertEqual(selected['execution']['per_producer_group_seconds'], 120)
        self.assertEqual(proof['prospective_selection_sha256'], self.base.SELECTION_SHA256)

    def test_outside_swift_job_unchanged_and_old_controls_retained(self):
        old = (HERE / 'current-verify.yml').read_text()
        new = (HERE / 'verify.yml.candidate').read_text()
        self.assertEqual(old.replace(self.base.job_text(old), ''), new.replace(self.base.job_text(new), ''))
        old_job, new_job = self.base.job_text(old), self.base.job_text(new)
        self.assertEqual(old_job.count('python3 -B "$MIXER_ADOPTION_DIR/test_adoption.py" -v'), 1)
        self.assertEqual(new_job.count('python3 -B "$MIXER_ADOPTION_DIR/test_adoption.py" -v'), 1)
        self.assertEqual(new_job.count('adopt_envelope.py" run '), old_job.count('adopt_envelope.py" run '))

    def test_historical_artifact_refusal_retained(self):
        evidence = json.loads((HERE / 'failure-evidence.json').read_text())
        self.assertEqual(evidence['zip_sha256'], '6cb7cc2b83b2700686211828169da08c70dba81a1bd1c01c0aa9d38bf2870940')
        self.assertEqual(len(evidence['refusals']), 2)
        self.assertTrue(all('Installed ordinary Swift job differs from sealed candidate' in r['text'] for r in evidence['refusals']))

    def test_successor_drift_and_changed_source_inputs_rejected(self):
        original = self.base.regular
        fake = Path(self.temp.name) / 'changed-job.yml'
        fake.write_text((HERE / 'swift-job.yml').read_text() + '# unreviewed\n')
        def redirected(path):
            return original(fake if path == HERE / 'swift-job.yml' else path)
        with patched(self.base, 'regular', redirected), self.assertRaisesRegex(RuntimeError, 'Pinned source differs'):
            self.base.verify(False)
        fake.write_text('{}')
        def changed_source(path):
            return original(fake if path == HERE / 'source-inputs.json' else path)
        with patched(self.base, 'regular', changed_source), self.assertRaises(RuntimeError):
            self.base.verify(False)

    def test_fake_fixture_failure_keeps_original_evidence_and_successor_snapshots(self):
        self.workflow.write_text((HERE / 'verify.yml.candidate').read_text())
        output = Path(self.temp.name) / 'output'
        def failed(out, compiler):
            self.assertEqual(compiler, '/synthetic/no-process')
            out = self.base.load_runner()[0].fresh_output(out, root=Path(self.temp.name) / 'synthetic-repo')
            (out / 'adapter-result.json').write_text('{"fixture_return_status": 1}')
            return 1
        with patched(a, 'WORKFLOW', self.workflow), patched(self.base, 'run_fixture', failed):
            self.assertEqual(a.run_fixture(self.base, output, '/synthetic/no-process'), 1)
        self.assertEqual((output / 'adapter-result.json').read_text(), '{"fixture_return_status": 1}')
        receipt = json.loads((output / 'caller-binding-result.json').read_text())
        self.assertEqual(receipt['fixture_return_status'], 1)
        self.assertEqual(receipt['errors'], [])
        self.assertEqual((output / 'executed-caller-binding-swift-job.yml').read_bytes(), (HERE / 'swift-job.yml').read_bytes())

    def test_fake_fixture_exception_has_failure_receipt(self):
        self.workflow.write_text((HERE / 'verify.yml.candidate').read_text())
        output = Path(self.temp.name) / 'output'
        def raised(out, compiler):
            out = self.base.load_runner()[0].fresh_output(out, root=Path(self.temp.name) / 'synthetic-repo')
            raise RuntimeError('synthetic preserved exception')
        with patched(a, 'WORKFLOW', self.workflow), patched(self.base, 'run_fixture', raised):
            self.assertEqual(a.run_fixture(self.base, output, '/synthetic/no-process'), 1)
        receipt = json.loads((output / 'caller-binding-result.json').read_text())
        self.assertEqual(receipt['errors'][0]['message'], 'synthetic preserved exception')


if __name__ == '__main__':
    (HERE / 'control-scratch').mkdir(exist_ok=True)
    result = unittest.main(exit=False, verbosity=2)
    (HERE / 'control-scratch').rmdir()
    if guard.DENIED:
        raise RuntimeError('Unexpected denied runtime operations: ' + repr(guard.DENIED))
    sys.exit(0 if result.result.wasSuccessful() else 1)
