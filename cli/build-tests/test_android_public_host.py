"""Explicit public host admission; compiler/linker/APK evidence is a separate run."""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from test_android_sdk_compatibility import CompatibilityFixture, DRIVER, load_driver


class AndroidPublicHostTests(CompatibilityFixture, unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='mixer-public-host-')
        self.addCleanup(self.temporary.cleanup)
        self.initialize_compatibility(pathlib.Path(self.temporary.name).resolve())
        self.package = self.root / 'Platforms/Android'

    def write_config(self):
        (self.root / 'mixer.yml').write_text(json.dumps(self.config))

    def public_inputs(self):
        self.config['androidHost'] = 'public-v3'
        self.write_config()
        java = 'Java/dev/mixer/safe/androidhost/'
        for relative in ['Sources/AppAndroid/NativeEntry.swift', 'Sources/AppAndroid/PublicFactory.swift',
                         'Bridge/PublicBridge.c', java + 'PublicActivity.java', java + 'PublicBridge.java']:
            target = self.package / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('compiler input; admission does not validate semantics\n')
        (self.package / 'public-host-v3.json').write_text(json.dumps(
            {'host': 'public-v3', 'profile': 'MEASURED_MULTILINE_RETIREMENT_V3'}))

    def refusal(self, message):
        self.write_config()
        # The executable entry must refuse before source hashing, inspection or
        # staging. A malformed source pair cannot mask these input refusals.
        with mock.patch.object(self.module, 'source_profile', side_effect=AssertionError('source work')):
            with self.assertRaisesRegex(RuntimeError, message):
                self.module.build(self.root)
        result = subprocess.run([sys.executable, '-B', str(self.rendered), 'build', str(self.root)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(message, result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertFalse((self.root / '.mixer').exists())

    def test_default_and_explicit_legacy_use_existing_admission(self):
        for explicit in (False, True):
            with self.subTest(explicit=explicit):
                if explicit:
                    self.config['androidHost'] = 'legacy-v1'
                self.write_config()
                self.assertFalse(self.module.public_host(self.root, self.module.configuration(self.config)))
                with mock.patch.object(self.module, 'inspect', side_effect=RuntimeError('tool sentinel')):
                    with self.assertRaisesRegex(RuntimeError, 'tool sentinel'):
                        self.module.build(self.root)
                self.assertTrue((self.root / '.mixer/android-build/build-input.json').is_file())

    def test_unknown_host_and_all_non_string_types_refuse_before_work(self):
        for value in ('public-v2', '', 'PUBLIC-V3', None, True, 3, [], {}, ['public-v3']):
            with self.subTest(value=value):
                self.config['androidHost'] = value
                self.refusal('Unsupported Android host')

    def test_unknown_fields_and_update_signature_bypass_still_refuse(self):
        self.config['androidHost'] = 'public-v3'
        for change in ('extra', 'signature', 'numeric-signature'):
            original = copy.deepcopy(self.config)
            with self.subTest(change=change):
                if change == 'extra':
                    self.config['host'] = 'public-v3'
                    self.refusal('Unsupported Android local configuration')
                else:
                    self.config['updates']['requireArtifactSignature'] = False if change == 'signature' else 1
                    self.refusal('Unsupported Android update policy')
            self.config = original

    def test_public_configuration_requires_matching_selection(self):
        self.config['androidHost'] = 'public-v3'
        self.refusal('Android host mismatch')
        self.public_inputs()
        for value in ({'host': 'legacy-v1', 'profile': 'MEASURED_MULTILINE_RETIREMENT_V3'},
                      {'host': 'public-v3', 'profile': 'PRIVATE_V2'},
                      {'host': 'public-v3', 'profile': 'MEASURED_MULTILINE_RETIREMENT_V3', 'extra': True}):
            (self.package / 'public-host-v3.json').write_text(json.dumps(value))
            self.refusal('Android host mismatch')

    def test_legacy_configuration_cannot_consume_public_selection(self):
        self.public_inputs()
        for value in (None, 'legacy-v1'):
            if value is None:
                self.config.pop('androidHost', None)
            else:
                self.config['androidHost'] = value
            self.refusal('Android host mismatch')

    def test_private_package_and_java_keywords_refuse(self):
        self.config['androidHost'] = 'public-v3'
        for application in ('dev.mixer.android', 'dev.mixer.android.consumer', 'example.class.consumer'):
            self.config['application'] = application
            self.refusal('Public Android host requires an app-owned Java package')

    def test_public_inputs_reach_existing_source_and_tool_admission(self):
        self.public_inputs()
        self.assertTrue(self.module.public_host(self.root, self.module.configuration(self.config)))
        with mock.patch.object(self.module, 'inspect', side_effect=RuntimeError('tool sentinel')):
            with self.assertRaisesRegex(RuntimeError, 'tool sentinel'):
                self.module.build(self.root)
        self.assertTrue((self.root / '.mixer/android-build/build-input.json').is_file())

    def test_private_namespace_extra_java_and_redirected_inputs_refuse(self):
        self.public_inputs()
        extra = self.package / 'Java/dev/mixer/android/PrivateAccess.java'
        extra.parent.mkdir(parents=True)
        extra.write_text('package dev.mixer.android; class PrivateAccess {}')
        self.refusal('Public Android host Java inventory')
        extra.unlink()
        bridge = self.package / 'Bridge/PublicBridge.c'
        bridge.unlink()
        bridge.symlink_to(self.root / 'missing')
        self.refusal('Public Android host requires a bounded ordinary input')


    def test_legacy_unrendered_profile_precedes_invalid_application_name(self):
        module = load_driver(DRIVER, 'raw_legacy_driver')
        sentinel = self.root / 'outside-unsigned.apk'
        sentinel.write_bytes(b'preserve')
        for host in (None, 'legacy-v1'):
            if host is None:
                self.config.pop('androidHost', None)
            else:
                self.config['androidHost'] = host
            for name in (str(self.root / 'outside'), '../../outside', 'bad/name', 'App;command'):
                with self.subTest(host=host, name=name):
                    self.config['name'] = name
                    self.write_config()
                    with self.assertRaisesRegex(RuntimeError, 'Android SDK source profile is not rendered or supported'):
                        module.build(self.root)
                    self.assertFalse((self.root / '.mixer').exists())
                    self.assertEqual(sentinel.read_bytes(), b'preserve')

    def test_legacy_tampered_sources_and_appearance_precede_capability_refusal(self):
        names = ('AndroidUINativeSurface.java', 'ExternalFrameSourceV2.java',
                 'NativeEditorConnectionV2.java', 'NativeAppearanceViewsV2.java',
                 'NativeRenderer.java', 'NativeCoordinatorV2.java', 'AuthoredToggleInputV2.java',
                 'NativeOwnerV2.java', 'OwnerLifecycleV2.java', 'NativeEnvironmentV2.java',
                 'NativeEnvironmentPlatformV2.java')
        self.config['capabilities'] = ['unsupported-capability']
        for host in (None, 'legacy-v1'):
            if host is None:
                self.config.pop('androidHost', None)
            else:
                self.config['androidHost'] = host
            self.write_config()
            for path in [self.adapter / 'app/src/dev/mixer/android' / name for name in names] + [self.descriptor]:
                original = path.read_bytes()
                changes = ('edit', 'remove', 'rename', 'symlink') if path == self.descriptor else ('edit', 'remove', 'rename')
                for change in changes:
                    with self.subTest(host=host, file=path.name, change=change):
                        moved = path.with_name(path.name + '.renamed')
                        path.unlink()
                        try:
                            if change == 'edit': path.write_bytes(b'changed source')
                            elif change == 'rename': moved.write_bytes(original)
                            elif change == 'symlink': path.symlink_to(self.root / 'missing')
                            message = 'Android appearance' if path == self.descriptor and change != 'edit' else 'Android SDK source compatibility rejected'
                            with self.assertRaisesRegex(RuntimeError, message):
                                self.module.build(self.root)
                            self.assertFalse((self.root / '.mixer').exists())
                        finally:
                            path.unlink(missing_ok=True)
                            moved.unlink(missing_ok=True)
                            path.write_bytes(original)

    def test_legacy_configuration_still_refuses_before_output_and_tools(self):
        original = copy.deepcopy(self.config)
        for host in (None, 'legacy-v1'):
            for key, value, message in (
                ('name', '../../outside', 'Invalid Android application name'),
                ('application', 'bad/name', 'Invalid Android application identifier'),
                ('capabilities', ['unsupported-capability'], 'Android host supports an empty capability list'),
                ('targets', ['ios'], 'Android local targets')):
                with self.subTest(host=host, field=key):
                    self.config = copy.deepcopy(original)
                    if host is not None: self.config['androidHost'] = host
                    self.config[key] = value
                    self.write_config()
                    with mock.patch.object(self.module, 'checked_output', side_effect=AssertionError('output before refusal')), \
                         mock.patch.object(self.module, 'inspect', side_effect=AssertionError('tools before refusal')):
                        with self.assertRaisesRegex(RuntimeError, message):
                            self.module.build(self.root)
                    self.assertFalse((self.root / '.mixer').exists())

    def test_public_invalid_application_and_capabilities_precede_source_work(self):
        self.public_inputs()
        original = copy.deepcopy(self.config)
        for key, value, message in (
            ('name', '../../outside', 'Invalid Android application name'),
            ('application', 'bad/name', 'Invalid Android application identifier'),
            ('capabilities', ['unsupported-capability'], 'Android host supports an empty capability list')):
            with self.subTest(field=key):
                self.config = copy.deepcopy(original)
                self.config[key] = value
                self.refusal(message)


if __name__ == '__main__':
    unittest.main()
