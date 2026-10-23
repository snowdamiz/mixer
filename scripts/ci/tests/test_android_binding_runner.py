"""Provenance checks for the fresh Android host binding runner."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'check-android-binding.py'
SPEC = importlib.util.spec_from_file_location('android_binding_runner', RUNNER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DependencyProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'
        self.build = self.root / 'build'
        self.source.mkdir()
        self.build.mkdir()
        self.pin = {'identity': 'test-dependency', 'kind': 'remoteSourceControl',
                    'location': 'https://example.invalid/fixture.git',
                    'state': {'revision': 'a' * 40, 'version': '1.0.0'}}
        self.dependency = {
            'packageRef': {key: self.pin[key] for key in ['identity', 'kind', 'location']},
            'state': {'checkoutState': copy.deepcopy(self.pin['state'])},
            'subpath': 'test-dependency',
        }
        self.revision = self.pin['state']['revision']
        self.status = ''

    def run_git(self, label, argv):
        self.assertEqual(argv[:3], ['git', '-C', self.build / 'checkouts/test-dependency'])
        if argv[3:] == ['rev-parse', 'HEAD']:
            return self.revision + '\n'
        self.assertEqual(argv[3:], ['status', '--porcelain', '--untracked-files=all'])
        return self.status

    def check(self, dependencies=None):
        (self.source / 'Package.resolved').write_text(json.dumps({'pins': [self.pin]}))
        (self.build / 'workspace-state.json').write_text(json.dumps({
            'object': {'dependencies': [self.dependency] if dependencies is None else dependencies}}))
        return MODULE.dependency_checkouts(self.source, self.build, self.run_git)

    def test_exact_pinned_clean_checkout_is_recorded(self):
        result = self.check()
        self.assertEqual(result['test-dependency']['revision'], self.revision)
        self.assertEqual(result['test-dependency']['status'], '')

    def test_resolution_origin_revision_and_identity_changes_reject(self):
        original = copy.deepcopy(self.dependency)
        for field, value in [('location', 'https://example.invalid/replaced.git'),
                             ('identity', 'extra-dependency'), ('kind', 'registry')]:
            with self.subTest(field=field):
                self.dependency = copy.deepcopy(original)
                self.dependency['packageRef'][field] = value
                with self.assertRaises(RuntimeError):
                    self.check()
        self.dependency = copy.deepcopy(original)
        self.dependency['state']['checkoutState']['revision'] = 'b' * 40
        with self.assertRaisesRegex(RuntimeError, 'resolution changed'):
            self.check()

    def test_actual_checkout_revision_is_checked(self):
        self.revision = 'b' * 40
        with self.assertRaisesRegex(RuntimeError, 'checkout revision changed'):
            self.check()

    def test_dirty_tracked_and_untracked_files_reject(self):
        for status in [' M Sources/Changed.swift\n', '?? Sources/Extra.swift\n']:
            with self.subTest(status=status):
                self.status = status
                with self.assertRaisesRegex(RuntimeError, 'checkout is dirty'):
                    self.check()

    def test_missing_pin_checkout_rejects(self):
        with self.assertRaisesRegex(RuntimeError, 'dependency set differs'):
            self.check([])

    def test_duplicate_checkout_rejects(self):
        with self.assertRaisesRegex(RuntimeError, 'Duplicate dependency checkout'):
            self.check([self.dependency, self.dependency])

    def test_python_optimization_cannot_disable_gate(self):
        result = subprocess.run([sys.executable, '-O', '-c',
                                 'import runpy,sys; runpy.run_path(sys.argv[1])["require"](False,"expected rejection")',
                                 str(RUNNER)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('RuntimeError: expected rejection', result.stderr)

    def test_native_preflight_rejects_invalid_inputs_under_optimization(self):
        native = self.root / 'native'
        (native / 'lib').mkdir(parents=True)
        (native / 'lib/libmixer_vm_capability_experimental.a').write_bytes(b'invalid archive')
        complete = {'target_selector': 'host', 'feature': 'experimental-capability-native',
                    'source_revision': 'a' * 40, 'library': {'sha256': '0' * 64},
                    'headers': {name: {} for name in ['mixer_vm.h', 'mixer_vm_capability.h', 'mixer_vm_guest_ui.h']}}
        for index, (kind, message) in enumerate([
                ('revision', 'Native VM source revision differs'),
                ('headers', 'complete capability VM header set'),
                ('archive', 'Native VM archive digest differs')]):
            with self.subTest(kind=kind):
                receipt = copy.deepcopy(complete)
                extra = []
                if kind == 'revision':
                    extra = ['--expected-native-revision', 'b' * 40]
                if kind == 'headers':
                    receipt['headers'].pop('mixer_vm_guest_ui.h')
                (native / 'receipt.json').write_text(json.dumps(receipt))
                result = subprocess.run([sys.executable, '-O', str(RUNNER),
                                         '--native-root', str(native), '--output', str(self.root / str(index)),
                                         *extra], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)


if __name__ == '__main__':
    unittest.main()
