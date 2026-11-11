#!/usr/bin/env python3
"""Pure fail-closed profile10 successor controls; no compiler or fixture execution."""
from pathlib import Path
import sys
import importlib.util
import json
import unittest
import hashlib
import os
from contextlib import contextmanager
import tempfile
import shutil
import zipfile
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('rebind_guard', ROOT / 'verification/envelope-rust-1991-default-ci-adoption/offline_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
sys.path.insert(0,str(HERE)); __import__('metadata_guard').install(guard,HERE)
import adopt_envelope as a

@contextmanager
def patched(obj, key, value):
    old = getattr(obj, key)
    setattr(obj, key, value)
    try: yield
    finally: setattr(obj, key, old)

class Rebinding(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HERE / 'control-scratch')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.base = a.bind()

    def test_current_r2_refuses_source113_at_first_changed_input(self):
        old = self.base.module_at('untouched_r2', HERE.parent / 'envelope-output-ownership-fix-r2/adopt_envelope.py')
        with self.assertRaisesRegex(RuntimeError, 'Pinned source differs: cli/Package.swift'):
            old.bind().verify(True)

    def test_successor_binds_current_source_and_actual_cli(self):
        proof = self.base.verify(False)
        source = json.loads((HERE / 'binding.json').read_text())['source']
        self.assertEqual(source['manifest'], 'source-inputs.json')
        frozen = json.loads((HERE / source['manifest']).read_text())
        digest = hashlib.sha256(''.join(
            path + '\0' + row['sha256'] + '\n'
            for path, row in sorted(frozen.items())).encode()).hexdigest()
        expected = (source['count'], source['sha256'])
        self.assertEqual((len(frozen), digest), expected)
        self.assertEqual((proof['source_count'], proof['source_sha256']), expected)
        self.assertFalse(proof['exact_compiler_qualified'])
        flow = self.work / 'verify.yml'
        flow.write_bytes((HERE / 'verify.yml.candidate').read_bytes())
        with patched(a, 'WORKFLOW', flow):
            self.assertTrue(self.base.verify(True)['installed_job_verified'])
        text = flow.read_text()
        self.assertIn(a.CALLER_AFTER, text)
        for before, after in [('--product mixer -j 2', '--product mixer -j 3'),
                              ('MIXER_STORE_TEST_CLI="$MIXER_STORE_CLI_BIN_DIR/mixer"', 'MIXER_STORE_TEST_CLI="/foreign/mixer"')]:
            flow.write_text(text.replace(before, after))
            with patched(a, 'WORKFLOW', flow), self.assertRaisesRegex(RuntimeError, 'Installed ordinary'):
                self.base.verify(True)

    def test_each_changed_frozen_source_is_refused(self):
        before = json.loads((HERE.parent / 'envelope-output-ownership-fix-r2/source103.json').read_text())
        after = json.loads((HERE / 'source-inputs.json').read_text())
        changed = [p for p in before if before[p] != after[p]]
        historical_changed = ['cli/Package.swift', 'cli/Sources/MixerBuild/AndroidProject.swift', 'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift', 'cli/Sources/MixerBuild/AppStoreConnectBuildStatus.swift', 'cli/Sources/MixerBuild/AppleProject.swift', 'cli/Sources/MixerBuild/Configuration.swift', 'cli/Sources/MixerBuild/LocalUpdateValidation.swift', 'cli/Sources/MixerBuild/ProcessRunner.swift', 'cli/Sources/MixerBuild/ProjectGenerator.swift', 'cli/Sources/MixerBuild/Resources/android-build.py', 'cli/Sources/MixerBuild/StoreReconciliation.swift', 'cli/Sources/MixerCLI/main.swift', 'native/android/app/src/dev/mixer/android/AppearanceGeometryV2.java', 'native/android/app/src/dev/mixer/android/AppearanceResolverV2.java', 'native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java', 'native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java', 'native/android/app/src/dev/mixer/android/NativeOwnerV2.java', 'native/android/app/src/dev/mixer/android/NativeRenderer.java', 'native/android/app/src/dev/mixer/android/OwnerLifecycleV2.java', 'native/android/app/src/dev/mixer/android/UiPacket.java', 'native/android/engine/Sources/MixerAndroidRuntime/DocumentSession.swift', 'scripts/ci/check-android-generated-java.py', 'sdk/Package.swift', 'sdk/Sources/MixerApple/MixerNativeView.swift', 'sdk/Sources/MixerGuest/GuestUIExchangeV1.swift', 'sdk/Sources/MixerGuest/GuestUIProtocolV1.swift', 'sdk/Sources/MixerUI/AppearanceResolutionV2.swift', 'sdk/Sources/MixerUI/NativePacketV1.swift', 'sdk/Sources/MixerUI/Protocol.swift', 'sdk/Sources/MixerUI/Reconciliation.swift', 'sdk/Sources/MixerUI/Validation.swift']
        transition = json.loads((HERE / 'binding.json').read_text())['guest_ui_v2_transition']
        successor_changed = {row['path'] for row in transition['owningChanges']
                             if row['path'] in before and before[row['path']] != row['after']}
        self.assertEqual(set(changed), set(historical_changed) | successor_changed)
        self.assertIn("sdk/Sources/MixerApple/MixerNativeView.swift", changed)
        original = self.base.regular
        for name in changed:
            fake = self.work / 'wrong-source'
            fake.write_bytes((ROOT / name).read_bytes() + b'\nchanged')
            def redirected(p): return original(fake if p == ROOT / name else p)
            with patched(self.base, 'regular', redirected), self.subTest(path=name), self.assertRaisesRegex(RuntimeError, 'Pinned source differs'):
                self.base.verify(False)

    def test_additional_source_cannot_escape_manifest(self):
        frozen = json.loads((HERE / 'source-inputs.json').read_text())
        projection = self.work / 'source'
        for name in frozen:
            target = projection / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        (projection / 'cli/Sources/MixerCLI/Unreviewed.swift').write_text('// extra source\n')
        module_at = self.base.module_at
        def load(name, source):
            return module_at(name, projection / 'scripts/ci/check-android-generated-java.py')
        with patched(self.base, 'module_at', load), self.assertRaisesRegex(RuntimeError, 'Current owning source closure differs'):
            self.base.verify(False)

    def test_each_sealed_history_member_remains_byte_pinned(self):
        rows = json.loads((HERE / 'historical-closure.json').read_text())
        original = self.base.regular
        for row in rows:
            fake = self.work / 'wrong-history'
            fake.write_bytes((ROOT / row['path']).read_bytes() + b'\nchanged')
            def redirected(p): return original(fake if p == ROOT / row['path'] else p)
            with patched(self.base, 'regular', redirected), self.subTest(path=row['path']), self.assertRaisesRegex(RuntimeError, 'Pinned source differs'):
                self.base.verify(False)

    def test_source_manifest_and_metadata_mutations_fail_even_with_resealed_rows(self):
        original = self.base.regular
        seal = json.loads((HERE / 'seal.json').read_text())
        for name, field in (('source-inputs.json', 'manifest'),
                            ('binding.json', 'profile'),
                            ('binding.json', 'source-count'),
                            ('binding.json', 'source-digest')):
            value = json.loads((HERE / name).read_text())
            if field == 'manifest': value.pop(next(iter(value)))
            elif field == 'profile': value['profile']['sdk_count'] = 23
            elif field == 'source-count': value['source']['count'] -= 1
            else: value['source']['sha256'] = '0' * 64
            fake = self.work / name
            fake.write_text(json.dumps(value))
            changed = json.loads(json.dumps(seal))
            for row in changed['members']:
                if row['path'] == name:
                    row.update(bytes=fake.stat().st_size, sha256=self.base.sha(fake))
            changed['tree_sha256'] = self.base.tree(changed['members'])
            seal_path = self.work / 'fake-seal.json'
            seal_path.write_text(json.dumps(changed))
            def redirect(p):
                return original(seal_path if p == HERE / 'seal.json' else fake if p == HERE / name else p)
            with patched(self.base, 'regular', redirect), self.subTest(name=name, field=field), self.assertRaises(RuntimeError):
                self.base.verify(False)

    def test_standard_compiler_policy_and_fixture_body_are_unchanged(self):
        previous = (HERE.parent / 'envelope-output-ownership-fix-r2/adopt_envelope.py').read_text()
        current = (HERE / 'adopt_envelope.py').read_text()
        self.assertEqual(previous[previous.index('class FreshOutput:'):previous.index('def run_fixture')],
                         current[current.index('class FreshOutput:'):current.index('def run_fixture')])
        old_body = previous[previous.index('def run_fixture'):previous.index('def main():')]
        new_body = current[current.index('def run_fixture'):current.index('def main():')]
        self.assertEqual(old_body.replace("'source103.json'", "'source-inputs.json', 'binding.json', 'historical-closure.json'"), new_body)
        self.base.validate_profile(self.base.PROFILE_IDENTITY, self.base.PROFILE_SHA256)
        runner, ordinary, proof = self.base.load_runner()
        self.assertIs(runner.rustc_identity, ordinary.rustc_identity)
        self.assertEqual((runner.OUTPUT_CAP, runner.TOTAL_OUTPUT_CAP), (8388608, 67108864))
        self.assertEqual(self.base.selection()['execution']['required_commands'], 40)

    def test_frozen_failure_evidence_is_bound_without_retry(self):
        binding = json.loads((HERE / 'binding.json').read_text())['failed_attempt']
        evidence = json.loads((HERE / 'failure-current.json').read_text())
        self.assertEqual(evidence['archive'], binding['archive'])
        self.assertEqual(evidence['archive']['members'], 54)
        self.assertEqual(evidence['swift_log_sha256'], binding['swift_log_sha256'])
        self.assertEqual((evidence['run'], evidence['job'], evidence['head']),
                         (42545709402, 128930148206, '924b155f9d319bb9bbee2b4e082960706edbfb25'))
        actual = evidence['refusals']
        self.assertEqual(len(actual), 2)
        self.assertTrue(all('Pinned source differs: cli/Sources/MixerBuild/AndroidSDKCompatibility.swift' in e['text'] for e in actual))
        self.assertFalse(binding['rerun_authorized'])

    def test_all_other_jobs_and_top_level_remain_identical(self):
        before = (HERE / 'current-verify.yml').read_text()
        after = (HERE / 'verify.yml.candidate').read_text()
        self.assertEqual(before.replace(self.base.job_text(before), ''), after.replace(self.base.job_text(after), ''))
        self.assertEqual(after.count('adopt_envelope.py" run '), before.count('adopt_envelope.py" run '))
        old = self.base.job_text(before)
        expected = old
        for edit in json.loads((HERE / 'job-changes.json').read_text()):
            self.assertEqual(expected.count(edit['before']), edit['count'])
            expected = expected.replace(edit['before'], edit['after'])
        self.assertEqual(expected, self.base.job_text(after))
        sparse = self.base.job_text(after).split('          sparse-checkout: |\n', 1)[1].split('      - name:', 1)[0]
        entries = [line.strip().lstrip('/') for line in sparse.splitlines()]
        history = json.loads((HERE / 'historical-closure.json').read_text())
        for row in history:
            self.assertTrue(any(row['path'] == entry or entry.endswith('/') and row['path'].startswith(entry)
                                for entry in entries), row['path'])


    def test_auxiliary_collision_preserves_existing_evidence(self):
        runner, _, _ = self.base.load_runner()
        ownership = a.FreshOutput(self.base)
        ownership.observe(runner)
        self.addCleanup(ownership.close)
        out = runner.fresh_output(self.work / 'fresh', self.work / 'synthetic-repo')
        (out / 'caller-binding-result.json').write_text('preserved')
        with self.assertRaisesRegex(RuntimeError, 'Successor evidence collision'):
            ownership.persist({'would-be-new.json': b'new', 'caller-binding-result.json': b'overwrite'})
        self.assertEqual((out / 'caller-binding-result.json').read_text(), 'preserved')
        self.assertFalse((out / 'would-be-new.json').exists())

    def test_unadopted_workflow_still_refuses_installed_verification(self):
        flow = self.work / 'verify.yml'
        flow.write_bytes((HERE / 'current-verify.yml').read_bytes())
        with patched(a, 'WORKFLOW', flow), self.assertRaisesRegex(RuntimeError, 'Installed ordinary Swift job differs'):
            self.base.verify(True)

    def test_source_snapshot_covers_profile_and_history_authority(self):
        body = (HERE / 'adopt_envelope.py').read_text()
        for name in ('source-inputs.json', 'binding.json', 'historical-closure.json'):
            self.assertIn("'" + name + "'", body[body.index('def run_fixture'):])

if __name__ == '__main__':
    (HERE / 'control-scratch').mkdir(exist_ok=True)
    result = unittest.main(exit=False, verbosity=2)
    (HERE / 'control-scratch').rmdir()
    if guard.DENIED: raise RuntimeError('Denied runtime attempts: ' + repr(guard.DENIED))
    sys.exit(0 if result.result.wasSuccessful() else 1)
