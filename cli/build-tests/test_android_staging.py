"""Local output containment: rejected builds must not mutate outside files."""
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from test_android_sdk_compatibility import CompatibilityFixture

DRIVER = pathlib.Path(__file__).resolve().parents[1] / 'Sources/MixerBuild/Resources/android-build.py'
SPEC = importlib.util.spec_from_file_location('android_build', DRIVER)
DRIVER_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER_MODULE)


class AndroidStagingTests(CompatibilityFixture, unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='mixer-staging-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = pathlib.Path(self.temporary.name).resolve()
        self.root = self.base / 'app'
        self.outside = self.base / 'outside'
        self.root.mkdir()
        self.outside.mkdir()
        self.initialize_compatibility(self.root)

    def output(self):
        path = self.root / '.mixer/android-build'
        path.mkdir(parents=True)
        return path

    def reject(self, message):
        before = {str(p.relative_to(self.outside)): p.read_bytes()
                  for p in self.outside.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, '-B', str(self.rendered), 'build', str(self.root)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(message, result.stderr)
        after = {str(p.relative_to(self.outside)): p.read_bytes()
                 for p in self.outside.rglob('*') if p.is_file()}
        self.assertEqual(after, before)
        self.assertNotIn('Traceback', result.stderr)

    def sentinels(self, folder):
        for name in ['build-receipt.json', 'SafeApp-unsigned.apk', 'keep.txt']:
            (folder / name).write_bytes(b'outside sentinel: ' + name.encode())

    def test_mixer_parent_symlink_rejects_before_cleanup(self):
        (self.outside / 'android-build').mkdir()
        self.sentinels(self.outside / 'android-build')
        (self.root / '.mixer').symlink_to(self.outside, target_is_directory=True)
        self.reject('Unsafe Android staging directory')

    def test_output_directory_symlink_rejects_before_cleanup(self):
        (self.root / '.mixer').mkdir()
        self.sentinels(self.outside)
        (self.root / '.mixer/android-build').symlink_to(self.outside, target_is_directory=True)
        self.reject('Unsafe Android staging directory')

    def test_deep_directory_symlinks_reject_before_cleanup(self):
        output = self.output()
        self.sentinels(self.outside)
        for name in ['swift', 'apk', 'classes', 'dex', 'apk/lib/arm64-v8a']:
            with self.subTest(name=name):
                link = output / name
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(self.outside, target_is_directory=True)
                self.reject('Unsafe Android staging link escapes output')
                link.unlink()

    def test_file_symlinks_reject_before_write_or_unlink(self):
        output = self.output()
        sentinel = self.outside / 'sentinel'
        sentinel.write_bytes(b'preserve outside file')
        for name in ['build-input.json.tmp', 'unaligned.apk', 'build-receipt.json',
                     'SafeApp-unsigned.apk', 'swift/cache']:
            with self.subTest(name=name):
                link = output / name
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(sentinel)
                self.reject('Unsafe Android staging link escapes output')
                link.unlink()

    def test_hardlinks_reject_before_write_or_unlink(self):
        output = self.output()
        sentinel = self.outside / 'sentinel'
        sentinel.write_bytes(b'preserve shared inode')
        for name in ['build-input.json.tmp', 'unaligned.apk', 'build-receipt.json',
                     'SafeApp-unsigned.apk', 'swift/cache']:
            with self.subTest(name=name):
                link = output / name
                link.parent.mkdir(parents=True, exist_ok=True)
                os.link(sentinel, link)
                self.reject('Unsafe Android staging hard link')
                link.unlink()

    def test_dangling_link_and_fifo_reject_without_opening(self):
        output = self.output()
        link = output / 'build-input.json.tmp'
        link.symlink_to(output / 'missing')
        self.reject('Unsafe Android staging link')
        link.unlink()
        os.mkfifo(link)
        self.reject('Unsafe Android staging special file')

    def test_non_directory_parent_rejects_without_modification(self):
        path = self.root / '.mixer'
        path.write_bytes(b'keep existing file')
        self.reject('Unsafe Android staging directory')
        self.assertEqual(path.read_bytes(), b'keep existing file')

    def test_internal_swiftpm_links_are_allowed_and_source_untouched(self):
        output = self.output()
        target = output / 'swift/aarch64-unknown-linux-android/release'
        target.mkdir(parents=True)
        (target / 'module.o').write_bytes(b'cached object')
        (output / 'swift/release').symlink_to(target, target_is_directory=True)
        (output / 'swift/module.o').symlink_to(target / 'module.o')
        self.assertEqual(DRIVER_MODULE.checked_output(self.root), output)
        self.assertEqual((target / 'module.o').read_bytes(), b'cached object')

    def test_fresh_output_is_created_without_touching_project_source(self):
        config = (self.root / 'mixer.yml').read_bytes()
        output = DRIVER_MODULE.checked_output(self.root, create=True)
        self.assertTrue(output.is_dir())
        self.assertEqual(list(output.iterdir()), [])
        self.assertEqual((self.root / 'mixer.yml').read_bytes(), config)


if __name__ == '__main__':
    unittest.main()
