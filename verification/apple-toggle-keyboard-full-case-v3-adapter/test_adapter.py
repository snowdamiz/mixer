"""Focused host-only stale-input and actual composed preflight controls."""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import adapter as a


def audit(event, args):
    if event in ['subprocess.Popen', 'os.system', 'os.posix_spawn']:
        raise RuntimeError('Native/process boundary forbidden in adapter host controls')


sys.addaudithook(audit)


class AdapterControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='adapter-host-', dir=a.BASE)
        self.addCleanup(self.temp.cleanup)
        self.folder = pathlib.Path(self.temp.name)
        self.helper = a.build_helper()

    def verify(self):
        return a.verify(unsealed_host_check=True)

    def changed_digest(self):
        file = self.folder/'stale-observation'
        file.write_bytes(b'synthetic stale bytes\x00\xff')
        return self.helper.sha(file)

    def test_real_accepted_preflight_is_host_only_and_has_seven_methods(self):
        with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('No process permitted')):
            result = self.verify()
        self.assertIsNone(result['sealSHA256'])
        self.assertFalse(result['nativeExecution'])
        self.assertEqual(result['expectedXCTestMethods'], a.METHODS)
        self.assertEqual(result['productArchiveSHA256'], a.RUNNER_ARCHIVE)

    def test_unsealed_adapter_cannot_supply_native_seal(self):
        with self.assertRaisesRegex(ValueError, 'Sealed adapter required'):
            a.verify()

    def test_stale_product_observation_refused_before_archive(self):
        b = self.helper
        changed = copy.deepcopy(b.read(a.BUILD/'supplement/build-products-manifest.json')['products'])
        entry = next(name for name,row in changed.items() if row['kind']=='file')
        changed[entry]['sha256'] = self.changed_digest()
        original_tree = b.tree
        with mock.patch.object(a, 'build_helper', return_value=b), mock.patch.object(b, 'tree', side_effect=lambda path:changed if path==b.PRODUCTS else original_tree(path)), mock.patch.object(b, 'verify_archive', side_effect=AssertionError('Must stop at product failure')):
            with self.assertRaisesRegex(ValueError, 'Fresh compiled runner products changed'):
                self.verify()

    def test_stale_source_observation_refused_before_products(self):
        b = self.helper
        changed = copy.deepcopy(b.read(a.BUILD/'source-before.json'))
        changed['runner']['UITests/ToggleUITests.swift']['sha256'] = self.changed_digest()
        with mock.patch.object(a, 'build_helper', return_value=b), mock.patch.object(b, 'revalidate', return_value=changed), mock.patch.object(b, 'tree', side_effect=AssertionError('Must stop at source failure')):
            with self.assertRaisesRegex(ValueError, 'Accepted source tree changed'):
                self.verify()

    def test_stale_tool_observation_refused(self):
        b = self.helper
        changed = copy.deepcopy(b.read(a.BUILD/'supplement/tools-verified.json'))
        changed['files'][str(b.DEVELOPER/'usr/bin/xcodebuild')]['resolvedSHA256'] = self.changed_digest()
        with mock.patch.object(a, 'build_helper', return_value=b), mock.patch.object(b, 'tool_metadata', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'compiler/tool/SDK bindings changed'):
                self.verify()

    def test_stale_adapter_source_bytes_refused(self):
        (self.folder/'adapter.py').write_bytes((a.BASE/'adapter.py').read_bytes()+b'\n# synthetic changed adapter\n')
        (self.folder/'adapter-runtime-selection.json').write_text(json.dumps({'files':{'adapter.py':a.sha(a.BASE/'adapter.py')}}))
        with mock.patch.object(a, 'BASE', self.folder):
            with self.assertRaisesRegex(ValueError, 'Pinned adapter input changed'):
                self.verify()

    def test_real_byte_and_mode_validator_rejects_stale_adapter_input(self):
        file = self.folder/'selected-input'
        file.write_bytes(b'accepted')
        file.chmod(0o600)
        expected = {str(file):self.helper.file_record(file)}
        file.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'Bound bytes/mode changed'):
            a.records(self.helper, expected)
        file.chmod(0o600)
        file.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Bound bytes/mode changed'):
            a.records(self.helper, expected)

    def test_stale_v9_app_source_read_refused(self):
        selected = a.ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/source/Prototype/TogglePanAdmission.swift'
        original_sha = a.sha
        digest = self.changed_digest()
        with mock.patch.object(a, 'sha', side_effect=lambda path: digest if path==selected else original_sha(path)):
            with self.assertRaisesRegex(ValueError, 'Selected V9 app source closure changed'):
                self.verify()

    def test_stale_app_archive_read_refused(self):
        selected = a.ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/built-app.tar.gz'
        original_sha = a.sha
        digest = self.changed_digest()
        with mock.patch.object(a, 'sha', side_effect=lambda path: digest if path==selected else original_sha(path)):
            with self.assertRaisesRegex(ValueError, 'Pinned adapter input changed'):
                self.verify()

    def test_first_validation_exception_preserved_and_later_checks_not_run(self):
        b = self.helper
        primary = OSError('synthetic first source-read failure')
        with mock.patch.object(a, 'build_helper', return_value=b), mock.patch.object(b, 'revalidate', side_effect=primary), mock.patch.object(b, 'tree', side_effect=AssertionError('Later product check forbidden')) as later:
            with self.assertRaises(OSError) as result:
                self.verify()
        self.assertIs(result.exception, primary)
        later.assert_not_called()

    def prepare_host_harness(self):
        real_verify = a.verify
        with mock.patch.object(a, 'verify', side_effect=lambda:real_verify(unsealed_host_check=True)):
            return a.compose()

    def test_actual_composition_changes_only_preflight_and_archive_binding(self):
        h = self.prepare_host_harness()
        self.assertIsInstance(h.verify, a.FreshPreflight)
        self.assertEqual(h.PRODUCT_ARCHIVE, a.ARCHIVE)
        self.assertEqual(h.SCOPES['interaction']['methods'], a.METHODS)
        self.assertEqual(len(h.SCOPES['interaction']['cases']), 6)
        self.assertEqual(pathlib.Path(h.cleanup.__code__.co_filename), a.PREP/'inputs/runtime/verification/apple-toggle-pan-origin-correction/harness.py')
        self.assertEqual(pathlib.Path(h.remove_ephemeral.__code__.co_filename), a.PREP/'inputs/runtime/verification/apple-toggle-pan-origin-correction/harness.py')
        self.assertEqual(pathlib.Path(h.run.__code__.co_filename), a.PREP/'composition.py')
        self.assertEqual(pathlib.Path(h.run.__globals__['orchestration'].__file__), a.PREP/'orchestration.py')

    def test_actual_runner_refuses_before_output_and_latches_first_exception(self):
        for primary in [ValueError('synthetic stale preflight'), KeyboardInterrupt('synthetic preflight interrupt')]:
            with self.subTest(failure=type(primary).__name__):
                h = self.prepare_host_harness()
                with mock.patch.object(a, 'verify', side_effect=primary) as preflight, mock.patch.object(h, 'Commands', side_effect=AssertionError('No command recorder permitted')) as commands:
                    for _ in range(2):
                        with self.assertRaises(type(primary)) as result:
                            h.run('unselected-host-only', 'interaction')
                        self.assertIs(result.exception, primary)
                    self.assertIs(h.verify.first, primary)
                    self.assertEqual(preflight.call_count, 1)
                    commands.assert_not_called()
                self.assertFalse((a.PREP/'runtime').exists())

    def test_outside_transitive_preload_refused_by_accepted_guard(self):
        outside = type(sys)('durable_settings')
        outside.__file__ = str(self.folder/'durable_settings.py')
        outside.__spec__ = a.importlib.util.spec_from_file_location('durable_settings', outside.__file__)
        real_verify = a.verify
        with mock.patch.object(a, 'verify', side_effect=lambda:real_verify(unsealed_host_check=True)), mock.patch.dict(sys.modules, {'durable_settings':outside}):
            with self.assertRaisesRegex(ValueError, 'outside selected origin'):
                a.compose()
        self.assertFalse((a.PREP/'runtime').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
