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
HISTORICAL = pathlib.Path(__file__).parent / 'fixtures'
PAIR9_POLICY = (HISTORICAL / 'source-pair9-policy.swift.txt').read_bytes()
PAIR9_DRIVER = (HISTORICAL / 'source-pair9-driver.py.txt').read_bytes()
assert hashlib.sha256(PAIR9_POLICY).hexdigest() == '65d176da09ca858ef1b045cc172b4197243dbb895ef54de69935f3c1078c694f'
assert hashlib.sha256(PAIR9_DRIVER).hexdigest() == '59b74d6db2ce2462a55fc2ea99f16deca3ec54cfc2fe92463e6412d0426b0002'
PAIR9_PROFILE = json.loads(PAIR9_POLICY.decode().split('Data(#"""\n', 1)[1].split('\n        """#.utf8)', 1)[0])
PAIR9_RAW = PAIR9_DRIVER.decode()


def load_driver(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Rewritten historical drivers can have equal sizes and timestamp granularity.
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
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
        for change in ['missing-android', 'legacy', 'profile-1', 'profile-2', 'profile-3', 'profile-4', 'profile-5-current', 'profile-5-prior', 'broader-6-axis', 'profile-6-current', 'profile-7-current', 'profile-8-current', 'pair8-old-tuple', 'pair9-old-tuple', 'pair9-r1-tuple', 'proposal-6-suffixed', 'mixed-axis-only', 'mixed-sdk', 'mixed-adapter', 'unknown', 'digest', 'default']:
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
                elif change == 'profile-6-current':
                    value['android']['profile'].update(id='mixer.android-source-pair.6', adapter_compatibility_sha256='7765667bc3e4b1d45a58ac122ff61b2fbfd7bcfe09b2172ffced62189fb00885')
                elif change == 'profile-7-current':
                    value['android']['profile'].update(id='mixer.android-source-pair.7', adapter_compatibility_sha256='ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e')
                elif change == 'profile-8-current':
                    value['android']['profile'].update(id='mixer.android-source-pair.8', adapter_compatibility_sha256='a2e1508c6dc0ad714ae3af6d39c334311876456cf577932a530a543480e7c015')
                elif change == 'pair8-old-tuple':
                    value['android']['profile'].update(id='mixer.android-source-pair.8', adapter_compatibility_sha256='ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e')
                elif change == 'pair9-old-tuple':
                    value['android']['profile']['adapter_compatibility_sha256'] = 'a2e1508c6dc0ad714ae3af6d39c334311876456cf577932a530a543480e7c015'
                elif change == 'pair9-r1-tuple':
                    value['android']['profile']['adapter_compatibility_sha256'] = 'b8aad7b23e2917176d4ab1da2912e2acc098265609ffd40741283607496225b3'
                elif change == 'proposal-6-suffixed':
                    value['android']['profile'].update(id='mixer.android-source-pair.6-editor-view-api29-30-bc03288599ec-8cd611a5b07f',
                        adapter_compatibility_sha256='8cd611a5b07fbf96adb270fa30042577789d4b87b252108697003809f00599b4')
                elif change == 'mixed-axis-only': value['android']['profile']['adapter_compatibility_sha256'] = '7765667bc3e4b1d45a58ac122ff61b2fbfd7bcfe09b2172ffced62189fb00885'
                elif change == 'mixed-sdk': value['android']['profile']['sdk_compatibility_sha256'] = '4c2e74bbdb1c060ffa2219ed378d11ed390e7a4454b95df4a2ee72074bb9b5a7'
                elif change == 'mixed-adapter': value['android']['profile']['adapter_compatibility_sha256'] = '2b001980e07e0d1c8a5139e79de6ad6ca83d8db66d386bd4f77689ab32a6325a'
                elif change == 'unknown': value['android']['profile']['id'] = 'unknown'
                elif change == 'digest': value['android']['profile']['sdk_compatibility_sha256'] = '0' * 64
                else: value['android']['profile']['default_descriptor'] = {'bytes': 1, 'sha256': '0' * 64}
                (self.root / 'mixer.lock').write_text(json.dumps(value))
                self.reject('android.sdk-profile-required' if change in ['missing-android', 'legacy'] else 'android.sdk-profile-mismatch')

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
        for filename in ['AndroidUINativeSurface.java', 'ExternalFrameSourceV2.java', 'NativeOwnerV2.java', 'OwnerLifecycleV2.java', 'NativeEnvironmentV2.java', 'NativeEnvironmentPlatformV2.java']:
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


    def test_profile18_preserves_exact_profile_session(self):
        self.assertEqual(PROFILE['id'], 'mixer.android-source-pair.18')
        self.assertEqual(len(PROFILE['sdk_files']), 24)
        self.assertEqual(len(PROFILE['adapter_files']), 27)
        self.assertEqual(PROFILE['sdk_compatibility_sha256'], 'a689f5653ff2d353e3b0ae202ee6169d64c03448a56ec1d5fee389a9a8ff536f')
        self.assertEqual(PROFILE['adapter_compatibility_sha256'], 'b377710dcd2bf3704c8402643fe82caa0f2738aff2bae0a51a4aecca1ad9104c')
        session = self.adapter / 'Sources/MixerAndroidRuntime/DocumentSession.swift'
        candidate = session.read_bytes()
        self.assertEqual(len(candidate), 5338)
        self.assertEqual(hashlib.sha256(candidate).hexdigest(), '3b9a6054e3c238a43d9428b142feb00f0086af0cc4aedf55a36f5554fda21f02')
        self.assertEqual(candidate, (REPOSITORY / 'native/android/engine/Sources/MixerAndroidRuntime/DocumentSession.swift').read_bytes())
        self.assertEqual(self.module.source_profile(), PROFILE)
        self.assertEqual(self.module.admit_source_pair(self.root, PROFILE), self.descriptor.read_bytes())


    def test_axis_session_baseline_and_drift_refuse_recomputed_generic_locks(self):
        session = self.adapter / 'Sources/MixerAndroidRuntime/DocumentSession.swift'
        candidate = session.read_bytes()
        axis_guard = b'            // The legacy decoder rejects every explicit axis key, including horizontal.\n            if profile == .legacyHorizontal, node.kind == .textField, node.properties["axis"] != nil { throw AndroidDocumentError.unsupportedUI }\n'
        self.assertEqual(candidate.count(axis_guard), 1)
        baseline = candidate.replace(axis_guard, b'')
        self.assertEqual(len(baseline), 5103)
        self.assertEqual(hashlib.sha256(baseline).hexdigest(), 'e5eb19409e0075438627d3d180b3f62bb6880048bfd24158619e8e2f633ff356')
        for changed in [baseline, b'x' * len(candidate), candidate + b'\n// drift']:
            with self.subTest(length=len(changed)):
                try:
                    session.write_bytes(changed)
                    self.refresh_lock()
                    self.reject()
                finally:
                    session.write_bytes(candidate)
                    self.refresh_lock()


    def test_profile10_public_swift_sources_refuse_recomputed_generic_locks(self):
        for name in ['AndroidUIHost.swift', 'AndroidUIProfile.swift']:
            source = self.sdk / 'Sources/MixerAndroid' / name
            original = source.read_bytes()
            for changed in [original + b'\n// drift', b'x' * len(original)]:
                with self.subTest(name=name, length=len(changed)):
                    try:
                        source.write_bytes(changed)
                        self.refresh_lock()
                        self.reject()
                    finally:
                        source.write_bytes(original)
                        self.refresh_lock()

    def test_exact_frozen_pair9_driver_refuses_profile10_sources(self):
        self.assertEqual(PAIR9_PROFILE['id'], 'mixer.android-source-pair.9')
        self.assertEqual(len(PAIR9_PROFILE['sdk_files']), 22)
        self.assertEqual(len(PAIR9_PROFILE['adapter_files']), 24)
        self.rendered.write_text(PAIR9_RAW.replace(MARKER, json.dumps(PAIR9_PROFILE).encode().hex()))
        self.module = load_driver(self.rendered, 'exact_pair9')
        self.assertEqual(self.module.source_profile(), PAIR9_PROFILE)
        self.refresh_lock()
        self.lock_value['android']['profile'] = self.module.profile_lock(PAIR9_PROFILE)
        (self.root / 'mixer.lock').write_text(json.dumps(self.lock_value))
        self.reject()


    def test_r1_pair9_driver_refuses_r2_sources(self):
        previous = json.loads(json.dumps(PAIR9_PROFILE))
        previous['adapter_compatibility_sha256'] = 'b8aad7b23e2917176d4ab1da2912e2acc098265609ffd40741283607496225b3'
        previous['adapter_files']['app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'] = {'bytes': 17696, 'sha256': '8396a3f5b923a40f3fd1a9121b8d5feaddd88583675e6596c1812c9c76520e1a'}
        self.rendered.write_text(PAIR9_RAW.replace(MARKER, json.dumps(previous).encode().hex()))
        self.module = load_driver(self.rendered, 'stale_r1_' + self.root.name.replace('-', '_'))
        self.assertEqual(self.module.source_profile(), previous)
        self.refresh_lock()
        self.lock_value['android']['profile'] = self.module.profile_lock(previous)
        (self.root / 'mixer.lock').write_text(json.dumps(self.lock_value))
        self.reject()

    def test_r2_refuses_exact_r1_source_with_recomputed_generic_lock(self):
        source = self.adapter / 'app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'
        r1 = source.read_text().replace(
            '                // Acquire every notice coalesced before this drain, before rereading the getter.\n'
            '                queued.getAndSet(false);', '                queued.set(false);').replace(
            '                if (observed != Phase.REGISTERING && observed != Phase.ACTIVE) return;\n'
            "                // Even true -> true publishes the producer's effective-scale write. A notice\n"
            "                // after the drain's exchange reserves a new delivery instead of being lost.\n"
            '                if (queued.getAndSet(true)) return;',
            '                if ((observed != Phase.REGISTERING && observed != Phase.ACTIVE) || !queued.compareAndSet(false, true)) return;').encode()
        self.assertEqual(len(r1), 17696)
        self.assertEqual(hashlib.sha256(r1).hexdigest(), '8396a3f5b923a40f3fd1a9121b8d5feaddd88583675e6596c1812c9c76520e1a')
        source.write_bytes(r1)
        self.refresh_lock()
        self.reject()

    def test_previous_pair8_driver_refuses_thread_fixed_sources(self):
        previous = json.loads(json.dumps(PAIR9_PROFILE))
        previous['id'] = 'mixer.android-source-pair.8'
        previous['adapter_compatibility_sha256'] = 'a2e1508c6dc0ad714ae3af6d39c334311876456cf577932a530a543480e7c015'
        previous['adapter_files']['app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'] = {'bytes': 15032, 'sha256': '04173e90ffb79ea87f9553691c95e26dbf627f5d269b60630daa7871eec793c6'}
        previous_raw = PAIR9_RAW.replace("value['id'] != 'mixer.android-source-pair.9'", "value['id'] != 'mixer.android-source-pair.8'")
        self.rendered.write_text(previous_raw.replace(MARKER, json.dumps(previous).encode().hex()))
        self.module = load_driver(self.rendered, 'stale_pair8_' + self.root.name.replace('-', '_'))
        self.assertEqual(self.module.source_profile(), previous)
        self.refresh_lock()
        self.lock_value['android']['profile'] = self.module.profile_lock(previous)
        (self.root / 'mixer.lock').write_text(json.dumps(self.lock_value))
        self.reject()

    def test_previous_pair7_driver_refuses_effective_motion_sources(self):
        previous = json.loads(json.dumps(PAIR9_PROFILE))
        previous['id'] = 'mixer.android-source-pair.7'
        previous['adapter_compatibility_sha256'] = 'ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e'
        previous['adapter_files']['app/src/dev/mixer/android/NativeEnvironmentV2.java'] = {'bytes': 15696, 'sha256': '2cff6cc20d1c3c9ae751e217bba3192e315125f438312f29e933d0c79d339eb1'}
        previous['adapter_files']['app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'] = {'bytes': 14154, 'sha256': '2f871e9813380b2d645b3ee636f67a7b3eae072f140163e14c7ec7ed60c562b2'}
        previous_raw = PAIR9_RAW.replace("value['id'] != 'mixer.android-source-pair.9'", "value['id'] != 'mixer.android-source-pair.7'")
        self.rendered.write_text(previous_raw.replace(MARKER, json.dumps(previous).encode().hex()))
        self.module = load_driver(self.rendered, 'stale_pair7_' + self.root.name.replace('-', '_'))
        self.refresh_lock()
        self.lock_value['android']['profile'] = self.module.profile_lock(previous)
        (self.root / 'mixer.lock').write_text(json.dumps(self.lock_value))
        self.reject()

    def test_previous_pair6_rendered_driver_refuses_broader_sources_before_output(self):
        # Reconstruct exact canonical6 template/map as data, then reach its stale-map admission.
        previous_raw = PAIR9_RAW.replace("value['id'] != 'mixer.android-source-pair.9'", "value['id'] != 'mixer.android-source-pair.6'")
        previous_raw = previous_raw.replace("('adapter', 24)", "('adapter', 23)")
        previous_raw = previous_raw.replace("'-proc:none', '-sourcepath', '', ", "")
        self.assertEqual(hashlib.sha256(previous_raw.encode()).hexdigest(), 'e1e1c57e56d71fe2cadcf9e0b43d8760a5745587f76a8326068a7b8363493a13')
        previous = json.loads(json.dumps(PAIR9_PROFILE))
        previous['id'] = 'mixer.android-source-pair.6'
        previous['adapter_compatibility_sha256'] = '7765667bc3e4b1d45a58ac122ff61b2fbfd7bcfe09b2172ffced62189fb00885'
        previous['adapter_files'].pop('app/src/dev/mixer/android/NativeEditorConnectionV2.java')
        previous['adapter_files']['app/src/dev/mixer/android/NativeEnvironmentV2.java'] = {'bytes': 15696, 'sha256': '2cff6cc20d1c3c9ae751e217bba3192e315125f438312f29e933d0c79d339eb1'}
        previous['adapter_files']['app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'] = {'bytes': 14154, 'sha256': '2f871e9813380b2d645b3ee636f67a7b3eae072f140163e14c7ec7ed60c562b2'}
        previous['adapter_files']['app/src/dev/mixer/android/NativeAppearanceViewsV2.java'] = {'bytes': 81532, 'sha256': 'a217d0b178869f3e5c3fc2d80f30f559a22c76a303195e62bfcb73d3cce91cce'}
        previous['adapter_files']['app/src/dev/mixer/android/NativeCoordinatorV2.java'] = {'bytes': 13468, 'sha256': '16597f90e5f9989404d88a94d35c531a06c964cd9a40dde94cc54c0aaaec5587'}
        previous['adapter_files']['app/src/dev/mixer/android/NativeRenderer.java'] = {'bytes': 47378, 'sha256': 'fa523aa1c9cd2f11a77022b008a5e983c8fda697a93e2a76585c01f79f50d725'}
        self.rendered.write_text(previous_raw.replace(MARKER, json.dumps(previous).encode().hex()))
        self.module = load_driver(self.rendered, 'stale_pair6_' + self.root.name.replace('-', '_'))
        self.refresh_lock()
        self.lock_value['android']['profile'] = self.module.profile_lock(previous)
        (self.root / 'mixer.lock').write_text(json.dumps(self.lock_value))
        self.reject()


class EditorSourcePairTests(CompatibilityFixture, unittest.TestCase):
    setUp = SourcePairTests.setUp
    reject = SourcePairTests.reject
    # Run only this class's added methods when selected; inherited protections
    # remain independently selected in SourcePairTests.
    def test_direct_editor_views_renderer_coordinator_full_negative_matrix(self):
        for filename in ['NativeEditorConnectionV2.java', 'NativeAppearanceViewsV2.java', 'NativeRenderer.java', 'NativeCoordinatorV2.java', 'AndroidUIProfile.java']:
            source = self.adapter / 'app/src/dev/mixer/android' / filename
            original = source.read_bytes()
            renamed = source.with_suffix('.renamed')
            alias = source.with_name(source.name.lower())
            sibling = source.with_name('unknown.txt')
            for change in ['same-size', 'append', 'remove', 'rename', 'case', 'symlink', 'fifo', 'directory', 'extra', 'oversized']:
                with self.subTest(filename=filename, change=change):
                    try:
                        source.unlink()
                        if change == 'same-size': source.write_bytes(b'x' * len(original))
                        elif change == 'append': source.write_bytes(original + b' ')
                        elif change == 'rename': renamed.write_bytes(original)
                        elif change == 'case': alias.write_bytes(original)
                        elif change == 'symlink': source.symlink_to(self.root / 'missing')
                        elif change == 'fifo': os.mkfifo(source)
                        elif change == 'directory': source.mkdir()
                        elif change == 'extra': source.write_bytes(original); sibling.write_bytes(b'')
                        elif change == 'oversized': source.write_bytes(b'x' * 2_000_000)
                        if change not in ['symlink', 'fifo', 'directory']:
                            self.refresh_lock()
                        # Topology faults must complete before even bounded reads.
                        if change != 'same-size':
                            with mock.patch.object(self.module, 'pinned_read', side_effect=AssertionError('source read before full topology')):
                                self.reject()
                        else:
                            self.reject()
                    finally:
                        for item in [source, renamed, alias, sibling]:
                            if item.is_dir() and not item.is_symlink(): item.rmdir()
                            else: item.unlink(missing_ok=True)
                        source.write_bytes(original)
                        self.refresh_lock()

    def test_each_canonical_only_extra_is_forbidden_in_generated_product_even_if_pinned(self):
        names = ['AppearanceDescriptorV1.java', 'AppearanceResolutionV1.java', 'AdapterInstrumentation.java']
        for subset in [[name] for name in names] + [names]:
            with self.subTest(subset=subset):
                for name in subset:
                    shutil.copyfile(REPOSITORY / 'native/android/app/src/dev/mixer/android' / name,
                                    self.adapter / 'app/src/dev/mixer/android' / name)
                self.refresh_lock()
                with mock.patch.object(self.module, 'pinned_read', side_effect=AssertionError('required source opened before closed inventory')):
                    self.reject()
                for name in subset: (self.adapter / 'app/src/dev/mixer/android' / name).unlink()

    def test_profile_exact_schema_keys_types_projections_and_old4_rendered_driver(self):
        changes = ['extra', 'missing', 'wrong-type', 'wrong-count', 'projection', 'identity-upper', 'identity-bool', 'wire-extra', 'wire-type', 'old4', 'descriptor']
        for change in changes:
            value = json.loads(json.dumps(PROFILE))
            if change == 'extra': value['extra'] = True
            elif change == 'missing': value.pop('wire')
            elif change == 'wrong-type': value['schema'] = True
            elif change == 'wrong-count': value['adapter_files'].pop('app/src/dev/mixer/android/NativeEditorConnectionV2.java')
            elif change == 'projection': value['adapter_compatibility_sha256'] = '0' * 64
            elif change == 'identity-upper': value['default_descriptor']['sha256'] = 'A' * 64
            elif change == 'identity-bool': value['default_descriptor']['bytes'] = True
            elif change == 'wire-extra': value['wire']['extra'] = True
            elif change == 'wire-type': value['wire']['document_schema'] = True
            elif change == 'old4': value['id'] = 'mixer.android-source-pair.4'
            else: value['default_descriptor']['bytes'] += 1
            with self.subTest(change=change):
                rendered = RAW.replace(MARKER, json.dumps(value).encode().hex())
                self.rendered.write_text(rendered)
                module = load_driver(self.rendered, 'invalid_' + change)
                with mock.patch.object(module, 'source_tree', side_effect=AssertionError('generic hasher reached')), \
                     mock.patch.object(module, 'inspect', side_effect=AssertionError('tool reached')), \
                     mock.patch.object(module, 'checked_output', side_effect=AssertionError('output reached')):
                    with self.assertRaises(RuntimeError): module.build(self.root)
                self.assertFalse((self.root / '.mixer').exists())
        self.rendered.write_text(RAW.replace(MARKER, json.dumps(PROFILE).encode().hex()))


if __name__ == '__main__': unittest.main()
