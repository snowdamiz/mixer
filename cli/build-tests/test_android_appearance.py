"""Closed internal asset admission and exact final APK packaging; no codec authority."""
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from unittest import mock

DRIVER = pathlib.Path(__file__).resolve().parents[1] / 'Sources/MixerBuild/Resources/android-build.py'
SPEC = importlib.util.spec_from_file_location('android_appearance_build', DRIVER)
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class AppearanceInputTests(unittest.TestCase):
    def setUp(self):
        # Short host scratch also permits a real AF_UNIX special-file fixture.
        self.temporary = tempfile.TemporaryDirectory(prefix='ma-', dir='/tmp')
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name).resolve()
        self.adapter = self.root / 'Generated/MixerAndroid'
        self.descriptor = self.adapter / 'app' / BUILD.APPEARANCE_ASSET
        self.descriptor.parent.mkdir(parents=True)
        (self.root / 'Generated/MixerSDK').mkdir()
        (self.root / 'Resources').mkdir()
        # Intentionally not semantic data: direct admission is layout/size only.
        self.descriptor.write_bytes(b'not a canonical default')
        self.lock()
        (self.root / 'mixer.yml').write_text(json.dumps({
            'schema': 1, 'name': 'AssetApp', 'application': 'dev.mixer.asset',
            'language': 'swift', 'targets': ['android'], 'toolchainLock': 'mixer.lock',
            'capabilities': [], 'updates': {'activation': 'cold-start',
                'compatibility': 'exact-runtime-fingerprint',
                'requireArtifactSignature': True, 'requireAssignmentSignature': True}}))

    def lock(self):
        (self.root / 'mixer.lock').write_text(json.dumps({
            'schema': 1, 'sdkDigest': BUILD.source_tree(self.root / 'Generated/MixerSDK'),
            'android': {'adapterDigest': BUILD.source_tree(self.adapter), 'toolchain': {}}}))

    def rejects_before_hash_or_output(self, message):
        with mock.patch.object(BUILD, 'source_tree', side_effect=AssertionError('source hashed before admission')), \
             mock.patch.object(BUILD, 'inspect', side_effect=AssertionError('tools before admission')):
            with self.assertRaisesRegex(RuntimeError, message):
                BUILD.build(self.root)
        self.assertFalse((self.root / '.mixer').exists())

    def test_layout_only_accepts_bounded_regular_bytes(self):
        self.assertEqual(BUILD.appearance_input(self.adapter), self.descriptor.read_bytes())
        self.descriptor.write_bytes(b'x' * 65_536)
        self.assertEqual(len(BUILD.appearance_input(self.adapter)), 65_536)

    def test_missing_empty_oversized_renamed_and_directory_reject_before_hash(self):
        for case in ['missing', 'empty', 'oversized', 'renamed', 'directory']:
            with self.subTest(case=case):
                self.descriptor.unlink(missing_ok=True)
                if case == 'empty': self.descriptor.write_bytes(b'')
                elif case == 'oversized': self.descriptor.write_bytes(b'x' * 65_537)
                elif case == 'renamed': self.descriptor.with_suffix('.renamed').write_bytes(b'x')
                elif case == 'directory': self.descriptor.mkdir()
                self.rejects_before_hash_or_output('Android appearance')
                if case == 'directory': self.descriptor.rmdir()
                self.descriptor.with_suffix('.renamed').unlink(missing_ok=True)
                self.descriptor.write_bytes(b'x')

    def test_complete_inventory_rejects_hidden_skipped_and_excluded_names_even_with_new_lock(self):
        for location in [self.descriptor.parent, self.descriptor.parent.parent]:
            for name in ['extra.json', '.env', '.DS_Store', 'secret.key', '.build']:
                with self.subTest(location=location.name, name=name):
                    item = location / name
                    if name == '.build': item.mkdir()
                    else: item.write_bytes(b'extra')
                    self.lock()
                    self.rejects_before_hash_or_output('must contain only')
                    if item.is_dir(): item.rmdir()
                    else: item.unlink()

    def test_empty_oversized_with_recomputed_lock_still_reject(self):
        for size in [0, 65_537]:
            self.descriptor.write_bytes(b'x' * size)
            self.lock()
            self.rejects_before_hash_or_output('1..65536')

    def test_descriptor_fifo_socket_and_symlink_reject_without_opening(self):
        self.descriptor.unlink()
        os.mkfifo(self.descriptor)
        self.rejects_before_hash_or_output('regular file')
        # Also exercise the direct executable with a timeout: a FIFO must not hang.
        result = subprocess.run([sys.executable, '-B', str(DRIVER), 'build', str(self.root)], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertIn('regular file', result.stderr)
        self.descriptor.unlink()
        with socket.socket(socket.AF_UNIX) as endpoint:
            endpoint.bind(str(self.descriptor))
            self.rejects_before_hash_or_output('regular file')
        self.descriptor.unlink()
        target = self.root / 'outside.json'
        target.write_bytes(b'outside')
        self.descriptor.symlink_to(target)
        self.rejects_before_hash_or_output('regular file')

    def test_redirected_ancestors_reject_before_hash(self):
        for path in [self.descriptor.parent, self.descriptor.parent.parent,
                     self.adapter / 'app', self.adapter, self.adapter.parent]:
            with self.subTest(path=path.name):
                relocated = path.with_name(path.name + '-moved')
                path.rename(relocated)
                path.symlink_to(relocated, target_is_directory=True)
                self.rejects_before_hash_or_output('ordinary directories')
                path.unlink()
                relocated.rename(path)

    def test_original_lock_byte_drift_and_java_drift_reject_before_output(self):
        for source in [self.descriptor, self.adapter / 'app/AuthoredToggleInputV2.java']:
            with self.subTest(source=source.name):
                self.lock()
                source.write_bytes(b'changed')
                with mock.patch.object(BUILD, 'inspect', side_effect=AssertionError('tools before lock rejection')):
                    with self.assertRaisesRegex(RuntimeError, 'differs from mixer.lock'):
                        BUILD.build(self.root)
                self.assertFalse((self.root / '.mixer').exists())

    def test_app_resources_still_reject_before_output(self):
        (self.root / 'Resources/image.png').write_bytes(b'unsupported')
        with mock.patch.object(BUILD, 'inspect', side_effect=AssertionError('tools before resource rejection')):
            with self.assertRaisesRegex(RuntimeError, 'resources cannot be omitted'):
                BUILD.build(self.root)
        self.assertFalse((self.root / '.mixer').exists())


class AppearanceArchiveTests(unittest.TestCase):
    def archive(self, entries):
        data = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(data, 'w') as archive:
                for name, value in entries: archive.writestr(name, value)
        data.seek(0)
        return zipfile.ZipFile(data)

    def test_exact_singleton_bytes_and_identity(self):
        expected = b'locked bytes'
        with self.archive([(BUILD.APPEARANCE_ASSET, expected), ('classes.dex', b'dex')]) as archive:
            result = BUILD.appearance_archive(archive, expected)
        self.assertEqual(result['bytes'], len(expected))
        self.assertEqual(result['sha256'], hashlib.sha256(expected).hexdigest())

    def test_missing_extra_renamed_directory_and_mismatch_reject(self):
        expected = b'locked bytes'
        for entries in [[], [('assets/renamed.json', expected)],
                        [(BUILD.APPEARANCE_ASSET, expected), ('assets/.hidden', b'x')],
                        [(BUILD.APPEARANCE_ASSET, expected), ('assets/', b'')],
                        [(BUILD.APPEARANCE_ASSET, b'wrong')]]:
            with self.subTest(entries=entries), self.archive(entries) as archive:
                with self.assertRaises(RuntimeError): BUILD.appearance_archive(archive, expected)

    def test_duplicate_asset_and_nonasset_names_reject_before_dictionary(self):
        for name in [BUILD.APPEARANCE_ASSET, 'classes.dex']:
            with self.subTest(name=name), self.archive([(BUILD.APPEARANCE_ASSET, b'x'), (name, b'x'), (name, b'x')]) as archive:
                with self.assertRaisesRegex(RuntimeError, 'Duplicate ZIP'):
                    BUILD.appearance_archive(archive, b'x')


if __name__ == '__main__':
    unittest.main()
