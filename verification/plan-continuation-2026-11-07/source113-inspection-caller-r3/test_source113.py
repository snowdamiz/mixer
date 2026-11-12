#!/usr/bin/env python3
"""Exercise the actual owner algorithm against the source113 projection."""
from pathlib import Path
import importlib.util
import sys
import json
import hashlib
import tempfile
import unittest
from contextlib import contextmanager
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('source113_guard', ROOT/'verification/envelope-rust-1991-default-ci-adoption/offline_guard.py')
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard); sys.path.insert(0,str(HERE)); __import__('metadata_guard').install(guard,HERE)
import adopt_envelope as a
@contextmanager
def patched(obj, key, value):
    old = getattr(obj, key); setattr(obj, key, value)
    try: yield
    finally: setattr(obj, key, old)
class Source113(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=HERE/'control-scratch')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.base = a.bind()
        self.frozen = json.loads((HERE/'current-source-inputs.json').read_text())
    def project(self):
        p = self.work/'source'
        for name in self.frozen:
            target = p/name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT/name).read_bytes())
        return p
    def from_projection(self, p):
        module_at = self.base.module_at
        def load(name, source):
            return module_at(name, p/'scripts/ci/check-android-generated-java.py')
        return patched(self.base, 'module_at', load)
    def refused_without_output(self):
        target = self.work/'refused-output'
        with self.assertRaises((RuntimeError, FileNotFoundError)):
            a.run_fixture(self.base, target, '/never-executed/rustc')
        self.assertFalse(target.exists())
        self.assertEqual(sorted(p.name for p in self.work.iterdir()), ['source'])
    def test_actual_owner_and_installed_candidate(self):
        proof = self.base.verify(False)
        owner = self.base.module_at('source113_actual', ROOT/'scripts/ci/check-android-generated-java.py')
        actual = owner.source_inputs(owner.load_profile(ROOT))
        self.assertEqual(actual, self.frozen)
        source = json.loads((HERE / 'binding.json').read_text())['source']
        self.assertEqual(source['manifest'], 'current-source-inputs.json')
        digest = hashlib.sha256(''.join(
            path + '\0' + row['sha256'] + '\n'
            for path, row in sorted(self.frozen.items())).encode()).hexdigest()
        expected = (source['count'], source['sha256'])
        self.assertEqual((len(self.frozen), digest), expected)
        self.assertEqual((len(actual), owner.source_digest(actual)), expected)
        self.assertEqual((proof['source_count'], proof['source_sha256']), expected)
        with patched(a, 'WORKFLOW', HERE/'verify.yml.candidate'):
            self.assertTrue(self.base.verify(True)['installed_job_verified'])
    def test_each_of_113_changed_owner_inputs_refuses_without_auxiliary_writes(self):
        p = self.project()
        with self.from_projection(p):
            for name in self.frozen:
                target = p/name; data = target.read_bytes()
                try:
                    target.write_bytes(data+b'\n# source113 mutation\n')
                    with self.subTest(path=name): self.refused_without_output()
                finally: target.write_bytes(data)
    def test_each_of_113_missing_owner_inputs_refuses_without_auxiliary_writes(self):
        p = self.project()
        with self.from_projection(p):
            for name in self.frozen:
                target = p/name; data = target.read_bytes()
                try:
                    target.unlink()
                    with self.subTest(path=name): self.refused_without_output()
                finally: target.write_bytes(data)
    def test_extra_source_and_c_header_refuse_from_actual_owner(self):
        p = self.project()
        with self.from_projection(p):
            for name in ('cli/Sources/MixerCLI/Extra.swift', 'cli/Sources/MixerProcessIO/include/extra.h'):
                target=p/name; target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    target.write_text('// extra owning input\n')
                    with self.subTest(path=name): self.refused_without_output()
                finally: target.unlink()
    def test_c_target_is_in_actual_owner_and_sparse_shipping_closure(self):
        job = (HERE/'swift-job.yml').read_text()
        self.assertIn('            /*\n', job)
        self.assertNotIn('!/cli', job)
        for name in ('cli/Sources/MixerProcessIO/process.c', 'cli/Sources/MixerProcessIO/include/MixerProcessIO.h',
                     'cli/Sources/MixerProcessIO/include/module.modulemap'):
            self.assertIn(name, self.frozen)
        self.assertIn('name: "MixerProcessIO"', (ROOT/'cli/Package.swift').read_text())
    def test_fresh_output_and_fixture_body_remain_byte_exact_r3(self):
        old = (HERE.parent/'envelope-profile10-rebind-r3/adopt_envelope.py').read_text()
        new = (HERE/'adopt_envelope.py').read_text()
        self.assertEqual(old[old.index('class FreshOutput:'):old.index('def main():')], new[new.index('class FreshOutput:'):new.index('def main():')])
    def test_metadata_only_literals_and_actual_admission(self):
        spec = importlib.util.spec_from_file_location('source113_bootstrap', HERE.parent/'generated-java-ci-integration/bootstrap.py')
        b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
        owner = b.canonical()
        actual = owner.source_inputs(owner.load_profile())
        binding = json.loads((HERE/'binding.json').read_bytes())
        predecessor = a.cli_advisory_predecessor(self.base, binding, a.play_cli_predecessor(self.base, binding, actual, owner), owner)
        from types import SimpleNamespace
        historical_authority = SimpleNamespace(source_inputs=lambda profile: predecessor, source_digest=owner.source_digest)
        self.assertEqual(b.admit_source_inputs(owner, owner.load_profile()), actual)
        with self.assertRaisesRegex(RuntimeError, 'owning inputs'):
            b.admit_source_inputs(historical_authority, owner.load_profile())
        self.assertEqual(actual, self.frozen)
        source = binding['source']
        self.assertEqual((b.SOURCE_INPUT_COUNT, b.SOURCE_INPUT_SHA256), (source['count'], source['sha256']))
        # Reconstruct the independently pinned old bootstrap, retaining its refusal.
        transition = binding['cli_advisory_caller_transition']
        raw = a.play_cli_bootstrap_predecessor(self.base, (HERE.parent/'generated-java-ci-integration/bootstrap.py').read_bytes())
        old = raw.replace(transition['sourceAfter'].encode(), transition['sourceBefore'].encode(), 1)
        self.assertEqual({'bytes':len(old), 'sha256':hashlib.sha256(old).hexdigest()}, transition['before'])
        namespace = {'__file__':str(HERE.parent/'generated-java-ci-integration/bootstrap.py'), '__name__':'old_bootstrap_control'}
        exec(compile(old, namespace['__file__'], 'exec'), namespace)
        self.assertEqual(namespace['admit_source_inputs'](historical_authority, owner.load_profile()), predecessor)
        with self.assertRaisesRegex(RuntimeError, 'owning inputs'):
            namespace['admit_source_inputs'](owner, owner.load_profile())
        for name, value in (('cli/Sources/MixerCLI/Extra.swift', b'// extra\n'),):
            p = self.project(); target=p/name; target.write_bytes(value)
            actual_owner = self.base.module_at('source113_extra_bootstrap', p/'scripts/ci/check-android-generated-java.py')
            with self.assertRaisesRegex(RuntimeError, 'owning inputs'):
                b.admit_source_inputs(actual_owner, actual_owner.load_profile())
    def test_bootstrap_actual_source_profile_lock_and_extraneous_mutants(self):
        spec = importlib.util.spec_from_file_location('mutant_bootstrap', HERE.parent/'generated-java-ci-integration/bootstrap.py')
        b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
        p = self.project()
        cases = [('changed-source', 'cli/Sources/MixerBuild/MigrationInspector.swift', 'change'),
                 ('extraneous-file', 'cli/Sources/MixerCLI/Unreviewed.swift', 'extra'),
                 ('changed-profile', 'native/android/contracts/android-profile-v1.json', 'change'),
                 ('missing-lock', 'cli/Package.resolved', 'missing')]
        for label, name, operation in cases:
            target = p/name
            before = target.read_bytes() if target.exists() else None
            try:
                if operation == 'missing': target.unlink()
                else: target.write_bytes((before or b'') + b'\n// unreviewed\n')
                owner = self.base.module_at('bootstrap_mutant_owner', p/'scripts/ci/check-android-generated-java.py')
                with self.subTest(mutation=label), self.assertRaises((RuntimeError, FileNotFoundError, ValueError)):
                    b.admit_source_inputs(owner, owner.load_profile())
            finally:
                if before is None: target.unlink()
                else: target.write_bytes(before)

    def test_unaccepted_r3_dependency_and_no_consumer_promotion(self):
        dep = json.loads((HERE/'binding.json').read_text())['dependency']
        self.assertFalse(dep['source106_R3']['independently_accepted'])
        self.assertTrue(dep['source106_R3']['fresh_combined_review_required'])
        self.assertIn('pending', dep['source113_six_consumers'])
if __name__ == '__main__':
    (HERE/'control-scratch').mkdir(exist_ok=True)
    result = unittest.main(exit=False, verbosity=2)
    (HERE/'control-scratch').rmdir()
    if guard.DENIED: raise RuntimeError('Denied runtime attempts: '+repr(guard.DENIED))
    sys.exit(0 if result.result.wasSuccessful() else 1)
