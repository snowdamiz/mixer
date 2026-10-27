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
        for change in ['missing-android', 'legacy', 'profile-1', 'profile-2', 'profile-3', 'profile-4', 'unknown', 'digest', 'default']:
            with self.subTest(change=change):
                self.refresh_lock()
                value = self.lock_value
                if change == 'missing-android': value.pop('android')
                elif change == 'legacy': value['android'].pop('profile')
                elif change == 'profile-1': value['android']['profile']['id'] = 'mixer.android-source-pair.1'
                elif change == 'profile-2': value['android']['profile']['id'] = 'mixer.android-source-pair.2'
                elif change == 'profile-3': value['android']['profile']['id'] = 'mixer.android-source-pair.3'
                elif change == 'profile-4': value['android']['profile']['id'] = 'mixer.android-source-pair.4'
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

class EditorSourcePairTests(CompatibilityFixture, unittest.TestCase):
    setUp = SourcePairTests.setUp
    reject = SourcePairTests.reject
    # Run only this class's added methods when selected; inherited protections
    # remain independently selected in SourcePairTests.
    def test_direct_editor_views_renderer_coordinator_full_negative_matrix(self):
        for filename in ['NativeEditorConnectionV2.java', 'NativeAppearanceViewsV2.java', 'NativeRenderer.java', 'NativeCoordinatorV2.java']:
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
