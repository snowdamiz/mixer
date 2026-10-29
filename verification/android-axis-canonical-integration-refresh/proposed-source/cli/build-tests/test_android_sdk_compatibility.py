"""Host admission regressions. Actual CLI rendering/codec evidence lives in the packet.

Fixtures read the one committed Swift policy literal; no duplicate expected map.
This test convenience is never imported by shipped product code.
"""
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
DRIVER = REPOSITORY / 'cli/Sources/MixerBuild/Resources/android-build.py'
POLICY_SOURCE = REPOSITORY / 'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift'
PROFILE = json.loads(POLICY_SOURCE.read_text().split('Data(#"""\n', 1)[1].split('\n        """#.utf8)', 1)[0])
RAW = DRIVER.read_text()
MARKER = '__MIXER_ANDROID_SOURCE_PROFILE_HEX__'


def load_driver(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CompatibilityFixture:
    def initialize_compatibility(self, root):
        self.root = root
        self.sdk = root / 'Generated/MixerSDK'
        self.adapter = root / 'Generated/MixerAndroid'
        for kind, directory in [('sdk', self.sdk), ('adapter', self.adapter)]:
            for relative in PROFILE[kind + '_files']:
                source = REPOSITORY / ('sdk/' + relative if kind == 'sdk' else 'native/android/' + ('engine/' if relative.startswith('Sources/') else '') + relative)
                target = directory / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        self.descriptor = self.adapter / 'app/assets/MixerAppearanceV2/descriptor.json'
        self.descriptor.parent.mkdir(parents=True)
        # Exact previous CLI-produced fixture; this does not execute its semantics.
        self.descriptor.write_bytes((REPOSITORY / 'verification/android-default-appearance-packaging/run-2/created-descriptor.json').read_bytes())
        assert len(self.descriptor.read_bytes()) == PROFILE['default_descriptor']['bytes']
        assert hashlib.sha256(self.descriptor.read_bytes()).hexdigest() == PROFILE['default_descriptor']['sha256']
        self.rendered = self.adapter / 'android-build.py'
        assert RAW.count(MARKER) == 1
        self.rendered.write_text(RAW.replace(MARKER, json.dumps(PROFILE).encode().hex()))
        self.module = load_driver(self.rendered, 'rendered_' + root.name.replace('-', '_'))
        (root / 'Resources').mkdir(exist_ok=True)
        self.config = {'schema': 1, 'name': 'SafeApp', 'application': 'dev.mixer.safe',
            'language': 'swift', 'targets': ['android'], 'toolchainLock': 'mixer.lock',
            'capabilities': [], 'updates': {'activation': 'cold-start',
                'compatibility': 'exact-runtime-fingerprint',
                'requireArtifactSignature': True, 'requireAssignmentSignature': True}}
        (root / 'mixer.yml').write_text(json.dumps(self.config))
        self.refresh_lock()

    def refresh_lock(self):
        self.lock_value = {'schema': 1, 'sdkDigest': self.module.source_tree(self.sdk),
            'android': {'adapterDigest': self.module.source_tree(self.adapter), 'toolchain': {}, 'profile': self.module.profile_lock(PROFILE)}}
        (self.root / 'mixer.lock').write_text(json.dumps(self.lock_value))


class SourcePairTests(CompatibilityFixture, unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='mixer-profile-', dir='/tmp')
        self.addCleanup(self.temporary.cleanup)
        self.initialize_compatibility(pathlib.Path(self.temporary.name).resolve())

    def reject(self, message='source compatibility rejected', profile=True):
        with mock.patch.object(self.module, 'source_tree', side_effect=AssertionError('generic hash before admission')), \
             mock.patch.object(self.module, 'inspect', side_effect=AssertionError('tools before admission')), \
             mock.patch.object(self.module, 'checked_output', side_effect=AssertionError('output before admission')):
            with self.assertRaisesRegex(RuntimeError, message):
                self.module.build(self.root)
        self.assertFalse((self.root / '.mixer').exists())
        result = subprocess.run([sys.executable, '-B', str(self.rendered), 'build', str(self.root)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn(message, result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertFalse((self.root / '.mixer').exists())

    def test_exact_relocated_pair_passes_before_tool_sentinel(self):
        self.assertEqual(self.module.admit_source_pair(self.root, self.module.source_profile()), self.descriptor.read_bytes())
        with mock.patch.object(self.module, 'inspect', side_effect=RuntimeError('TOOL-ORDER-SENTINEL')):
            with self.assertRaisesRegex(RuntimeError, 'TOOL-ORDER-SENTINEL'):
                self.module.build(self.root)
        self.assertTrue((self.root / '.mixer/android-build/build-input.json').is_file())

    def test_ascii_reserved_names_and_both_kelvin_aliases_reject_even_with_recomputed_locks(self):
        for name in ['Package@swift-6.4.swift', 'package.swift', 'PACKAGE.SWIFT', 'Package.resolved', 'Package.swift.bak', 'Pac\u212aage.swift', 'Pac\u212aage@swift-6.4.swift', 'unrelated-東京']:
            with self.subTest(name=name):
                original = (self.sdk / 'Package.swift').read_bytes()
                if name in ['package.swift', 'PACKAGE.SWIFT', 'Pac\u212aage.swift']:
                    (self.sdk / 'Package.swift').unlink()
                item = self.sdk / name
                item.write_bytes(b'unadmitted')
                self.refresh_lock()
                self.reject()
                item.unlink()
                (self.sdk / 'Package.swift').write_bytes(original)

    def test_selector_types_refuse_without_following_or_opening(self):
        item = self.sdk / 'Package@swift-6.4.swift'
        for kind in ['symlink', 'fifo', 'directory', 'oversized']:
            with self.subTest(kind=kind):
                if kind == 'symlink': item.symlink_to(self.root / 'missing')
                elif kind == 'fifo': os.mkfifo(item)
                elif kind == 'directory': item.mkdir()
                else: item.write_bytes(b'x' * 2_000_000)
                self.reject()
                if item.is_dir(): item.rmdir()
                else: item.unlink()

    def test_exact_closure_extras_types_sizes_and_ancestor_spelling(self):
        core = self.sdk / 'Sources/MixerCore'
        for name in ['.env', '.DS_Store', '.build', 'secret.key', 'unknown.txt', 'empty-directory']:
            item = core / name
            with self.subTest(extra=name):
                if name in ['.build', 'empty-directory']: item.mkdir()
                else: item.write_bytes(b'x')
                self.refresh_lock(); self.reject()
                if item.is_dir(): item.rmdir()
                else: item.unlink()
        file = core / 'Lifecycle.swift'
        original = file.read_bytes()
        for kind in ['short', 'oversized', 'same-size', 'missing', 'symlink', 'fifo', 'directory']:
            with self.subTest(kind=kind):
                file.unlink()
                if kind == 'short': file.write_bytes(b'x')
                elif kind == 'oversized': file.write_bytes(b'x' * 2_000_000)
                elif kind == 'same-size': file.write_bytes(b'x' * len(original))
                elif kind == 'symlink': file.symlink_to(self.root / 'missing')
                elif kind == 'fifo': os.mkfifo(file)
                elif kind == 'directory': file.mkdir()
                self.reject()
                if file.is_dir(): file.rmdir()
                else: file.unlink(missing_ok=True)
                file.write_bytes(original)
        for path in [core, self.sdk / 'Sources', self.adapter / 'bridge']:
            renamed = path.with_name(path.name.lower() if path.name[0].isupper() else path.name.upper())
            path.rename(renamed)
            self.reject()
            renamed.rename(path)

    def test_profile_missing_unknown_mismatched_and_configuration_missing_android_lock(self):
        for change in ['missing-android', 'legacy', 'profile-1', 'profile-2', 'profile-3', 'profile-4', 'profile-5-current', 'profile-5-prior', 'broader-6-axis', 'mixed-sdk', 'mixed-adapter', 'unknown', 'digest', 'default']:
            with self.subTest(change=change):
                self.refresh_lock()
                value = self.lock_value
                if change == 'missing-android': value.pop('android')
                elif change == 'legacy': value['android'].pop('profile')
                elif change == 'profile-1': value['android']['profile']['id'] = 'mixer.android-source-pair.1'
                elif change == 'profile-2': value['android']['profile']['id'] = 'mixer.android-source-pair.2'
                elif change == 'profile-3': value['android']['profile']['id'] = 'mixer.android-source-pair.3'
                elif change == 'profile-4': value['android']['profile']['id'] = 'mixer.android-source-pair.4'
                elif change == 'profile-5-current':
                    value['android']['profile'].update(id='mixer.android-source-pair.5',
                        sdk_compatibility_sha256='bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0',
                        adapter_compatibility_sha256='2b001980e07e0d1c8a5139e79de6ad6ca83d8db66d386bd4f77689ab32a6325a')
                elif change == 'profile-5-prior':
                    value['android']['profile'].update(id='mixer.android-source-pair.5',
                        sdk_compatibility_sha256='4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7',
                        adapter_compatibility_sha256='9d47585c18c325888c6d87914808449f1a92e4a3839d02ce5c4ae8f15801c10c')
                elif change == 'broader-6-axis':
                    # The same ID cannot authorize the unselected broader adapter24 source tuple.
                    value['android']['profile'].update(id='mixer.android-source-pair.6',
                        sdk_compatibility_sha256='bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0',
                        adapter_compatibility_sha256='ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e',
                        default_descriptor={'bytes': 9587, 'sha256': '1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3'})
                elif change == 'mixed-sdk': value['android']['profile']['sdk_compatibility_sha256'] = '4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7'
                elif change == 'mixed-adapter': value['android']['profile']['adapter_compatibility_sha256'] = '2b001980e07e0d1c8a5139e79de6ad6ca83d8db66d386bd4f77689ab32a6325a'
                elif change == 'unknown': value['android']['profile']['id'] = 'unknown'
                elif change == 'digest': value['android']['profile']['sdk_compatibility_sha256'] = '0' * 64
                else: value['android']['profile']['default_descriptor'] = {'bytes': 1, 'sha256': '0' * 64}
                (self.root / 'mixer.lock').write_text(json.dumps(value))
                self.reject('android.sdk-profile-required' if change in ['missing-android', 'legacy'] else 'android.sdk-profile-mismatch')

    def test_axis_only_profile_and_exported_session_are_exact(self):
        self.assertEqual(PROFILE['id'], 'mixer.android-source-pair.6')
        self.assertEqual(len(PROFILE['sdk_files']), 22)
        self.assertEqual(len(PROFILE['adapter_files']), 23)
        self.assertEqual(PROFILE['sdk_compatibility_sha256'], 'bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0')
        self.assertEqual(PROFILE['adapter_compatibility_sha256'], '7765667bc3e4b1d45a58ac122ff61b2fbfd7bcfe09b2172ffced62189fb00885')
        session = self.adapter / 'Sources/MixerAndroidRuntime/DocumentSession.swift'
        candidate = session.read_bytes()
        self.assertEqual(len(candidate), 4328)
        self.assertEqual(hashlib.sha256(candidate).hexdigest(), 'cf1954af12e316bcd7cf8ea4def41d2dc6b26921fffa60177bce477c7f0749b7')
        self.assertEqual(candidate, (REPOSITORY / 'native/android/engine/Sources/MixerAndroidRuntime/DocumentSession.swift').read_bytes())
        self.assertEqual(self.module.source_profile(), PROFILE)
        self.assertEqual(self.module.admit_source_pair(self.root, PROFILE), self.descriptor.read_bytes())

    def test_axis_session_baseline_and_drift_refuse_recomputed_generic_locks(self):
        session = self.adapter / 'Sources/MixerAndroidRuntime/DocumentSession.swift'
        candidate = session.read_bytes()
        axis_guard = (b"            // Android's native packet decoder does not admit an explicit axis key.\n"
                      b'            if node.kind == .textField, node.properties["axis"] != nil { throw AndroidDocumentError.unsupportedUI }\n')
        self.assertEqual(candidate.count(axis_guard), 1)
        baseline = candidate.replace(axis_guard, b'')
        self.assertEqual(len(baseline), 4128)
        self.assertEqual(hashlib.sha256(baseline).hexdigest(), '701b3d82add793a2b425bfc9673583afa8be4112406071242099da7da252bd0c')
        for changed in [baseline, b'x' * len(candidate), candidate + b'\n// drift']:
            with self.subTest(length=len(changed)):
                try:
                    session.write_bytes(changed)
                    self.refresh_lock()
                    self.reject()
                finally:
                    session.write_bytes(candidate)
                    self.refresh_lock()

    def test_previous_pair5_rendered_driver_refuses_new_session_before_output(self):
        # Reconstruct the exact immediately previous template and its old 23-member map.
        # New-profile lock rejection is covered separately; this reaches stale-map admission.
        previous_raw = RAW.replace("value['id'] != 'mixer.android-source-pair.6'", "value['id'] != 'mixer.android-source-pair.5'")
        self.assertEqual(hashlib.sha256(previous_raw.encode()).hexdigest(), '0f13545e610e527fe491314194fde1aa91698e9b458b638df6094f0e789fe4f2')
        previous = json.loads(json.dumps(PROFILE))
        previous['id'] = 'mixer.android-source-pair.5'
        previous['adapter_compatibility_sha256'] = '2b001980e07e0d1c8a5139e79de6ad6ca83d8db66d386bd4f77689ab32a6325a'
        previous['adapter_files']['Sources/MixerAndroidRuntime/DocumentSession.swift'] = {
            'bytes': 4128, 'sha256': '701b3d82add793a2b425bfc9673583afa8be4112406071242099da7da252bd0c'}
        self.rendered.write_text(previous_raw.replace(MARKER, json.dumps(previous).encode().hex()))
        self.module = load_driver(self.rendered, 'stale_pair5_' + self.root.name.replace('-', '_'))
        self.refresh_lock()
        self.lock_value['android']['profile'] = self.module.profile_lock(previous)
        (self.root / 'mixer.lock').write_text(json.dumps(self.lock_value))
        self.reject()

    def test_observer_edits_reject_even_when_generic_locks_are_recomputed(self):
        observer = self.adapter / 'app/src/dev/mixer/android/NativeEnvironmentV2.java'
        original = observer.read_bytes()
        for edited in [b'x' * len(original), original + b'\n// edited']:
            with self.subTest(length=len(edited)):
                observer.write_bytes(edited)
                self.refresh_lock()
                self.reject()
        observer.write_bytes(original)

    def test_owner_core_and_environment_edits_removals_and_renames_refuse_recomputed_locks(self):
        for filename in ['NativeOwnerV2.java', 'OwnerLifecycleV2.java', 'NativeEnvironmentV2.java', 'NativeEnvironmentPlatformV2.java']:
            source = self.adapter / 'app/src/dev/mixer/android' / filename
            original = source.read_bytes()
            renamed = source.with_suffix('.renamed')
            for change in ['same-size', 'remove', 'rename']:
                with self.subTest(filename=filename, change=change):
                    try:
                        if change == 'same-size': source.write_bytes(b'x' * len(original))
                        elif change == 'remove': source.unlink()
                        else: source.rename(renamed)
                        self.refresh_lock()
                        self.reject()
                    finally:
                        renamed.unlink(missing_ok=True)
                        source.write_bytes(original)
                        self.refresh_lock()

    def test_topology_rejection_precedes_all_required_source_reads(self):
        item = self.sdk / 'unrelated-東京'
        item.write_bytes(b'unadmitted')
        with mock.patch.object(self.module, 'pinned_read', side_effect=AssertionError('required source opened before root admission')):
            self.reject()
        item.unlink()
        source = self.sdk / 'Sources/MixerCore/Lifecycle.swift'
        source.write_bytes(b'x' * 2_000_000)
        with mock.patch.object(self.module, 'pinned_read', side_effect=AssertionError('oversized required source opened')):
            self.reject()

    def test_raw_import_inspect_inventory_independent_and_raw_build_refuses(self):
        raw = load_driver(DRIVER, 'raw_admission')
        with mock.patch.object(raw, 'probe', side_effect=RuntimeError('RAW-INSPECT-TOOL-SENTINEL')):
            with self.assertRaisesRegex(RuntimeError, 'RAW-INSPECT-TOOL-SENTINEL'): raw.inspect()
        with self.assertRaisesRegex(RuntimeError, 'not rendered or supported'): raw.build(self.root)
        for value in ['', 'not-hex', b'{}'.hex(), b'{"schema":1,"schema":1}'.hex()]:
            with mock.patch.object(raw, 'SOURCE_PROFILE_HEX', value):
                with self.assertRaisesRegex(RuntimeError, 'not rendered or supported'): raw.build(self.root)

    def test_invalid_name_and_resources_still_refuse_before_output(self):
        for name in ['../../escape', '/absolute', 'App;command']:
            self.config['name'] = name
            (self.root / 'mixer.yml').write_text(json.dumps(self.config))
            with self.assertRaisesRegex(RuntimeError, 'Invalid Android application name'): self.module.build(self.root)
            self.assertFalse((self.root / '.mixer').exists())
        self.config['name'] = 'SafeApp'; (self.root / 'mixer.yml').write_text(json.dumps(self.config))
        (self.root / 'Resources/image.png').write_bytes(b'unsupported')
        with self.assertRaisesRegex(RuntimeError, 'resources cannot be omitted'): self.module.build(self.root)
        self.assertFalse((self.root / '.mixer').exists())

if __name__ == '__main__': unittest.main()
