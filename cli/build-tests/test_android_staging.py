"""Local output containment: rejected builds must not mutate outside files."""
import ast
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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



class AndroidDependencyPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='mixer-resolver-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        (self.root / 'Platforms/Android').mkdir(parents=True)
        (self.root / 'Generated/MixerSDK').mkdir(parents=True)
        (self.root / 'Generated/MixerAndroid').mkdir(parents=True)
        (self.root / 'App.swift').write_text('let app = 1\n')
        (self.root / 'Generated/MixerAndroid/adapter.py').write_text('adapter')
        sdk = pathlib.Path(__file__).resolve().parents[2] / 'sdk/Package.resolved'
        self.sdk = sdk.read_bytes()
        (self.root / 'Generated/MixerSDK/Package.resolved').write_bytes(self.sdk)
        value = json.loads(self.sdk)
        value['originHash'] = '3' * 64
        self.platform = (json.dumps(value, indent=2) + '\n').encode()
        self.lock = self.root / 'Platforms/Android/Package.resolved'
        self.calls = []
        self.options = ['--package-path', self.lock.parent, '--scratch-path', self.root / '.mixer/swift']

    def resolve(self, command):
        self.calls.append(command)
        if not self.lock.exists():
            self.lock.write_bytes(self.platform)

    def prepare(self, resolver=None):
        return DRIVER_MODULE.prepare_dependencies(self.root, resolver or self.resolve, self.options)

    def test_missing_lock_uses_real_resolver_bytes_in_frozen_identity(self):
        before = DRIVER_MODULE.source_tree(self.root)
        identity = self.prepare()
        self.assertEqual(self.lock.read_bytes(), self.platform)
        self.assertNotEqual(self.platform, self.sdk)
        self.assertEqual(identity, {'path': 'Platforms/Android/Package.resolved', 'bytes': len(self.platform),
                                    'sha256': hashlib.sha256(self.platform).hexdigest()})
        self.assertNotEqual(before, DRIVER_MODULE.source_tree(self.root))
        self.assertEqual(self.calls[0][-1], 'resolve')
        self.assertIn('--package-path', self.calls[0])

    def test_warm_lock_remains_exact_and_forces_resolved_versions(self):
        self.lock.write_bytes(self.platform)
        before = DRIVER_MODULE.source_tree(self.root)
        self.prepare()
        self.assertEqual(self.lock.read_bytes(), self.platform)
        self.assertEqual(before, DRIVER_MODULE.source_tree(self.root))
        self.assertIn('--force-resolved-versions', self.calls[0])

    def test_missing_resolver_result_is_refused(self):
        with self.assertRaises(RuntimeError):
            self.prepare(lambda _: None)

    def test_malformed_stale_oversize_duplicate_locks_refuse_before_resolver(self):
        wrong = json.loads(self.platform)
        wrong['pins'][0]['state']['revision'] = '0' * 40
        for data in (b'{', b' ' * 65537, b'{"version":3,"version":3}',
                     json.dumps(wrong).encode(), self.platform.replace(b'"version": 3', b'"version": true')):
            with self.subTest(data=data[:60]):
                self.lock.write_bytes(data)
                with self.assertRaises(RuntimeError):
                    self.prepare()
                self.assertEqual(self.calls, [])

    def test_symlink_hardlink_and_case_alias_refuse_before_resolver(self):
        target = self.root / 'outside-lock'
        target.write_bytes(self.platform)
        self.lock.symlink_to(target)
        with self.assertRaises(RuntimeError):
            self.prepare()
        self.lock.unlink()
        os.link(target, self.lock)
        with self.assertRaises(RuntimeError):
            self.prepare()
        self.lock.unlink()
        self.lock.with_name('package.resolved').write_bytes(self.platform)
        with self.assertRaises(RuntimeError):
            self.prepare()
        self.assertEqual(self.calls, [])

    def test_resolver_mutations_refuse_all_included_source_changes(self):
        for relative in ('App.swift', 'Generated/MixerSDK/Package.resolved',
                         'Generated/MixerAndroid/adapter.py', 'foreign.txt'):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes() if path.exists() else None
                def mutate(command):
                    self.resolve(command)
                    path.write_bytes(b'changed')
                with self.assertRaises(RuntimeError):
                    self.prepare(mutate)
                if original is None:
                    path.unlink()
                else:
                    path.write_bytes(original)
                self.lock.unlink(missing_ok=True)

    def test_resolver_cannot_rewrite_existing_lock_even_with_equal_pins(self):
        self.lock.write_bytes(self.platform)
        def rewrite(command):
            self.resolve(command)
            value = json.loads(self.platform)
            value['originHash'] = '4' * 64
            self.lock.write_text(json.dumps(value))
        with self.assertRaisesRegex(RuntimeError, 'existing platform dependency lock'):
            self.prepare(rewrite)

    def test_resolver_output_wrong_pins_refuses(self):
        def wrong(command):
            self.resolve(command)
            value = json.loads(self.platform)
            value['pins'][0]['state']['version'] = '99.0.0'
            self.lock.write_text(json.dumps(value))
        with self.assertRaisesRegex(RuntimeError, 'pins differ'):
            self.prepare(wrong)

    def test_final_guard_deletes_apk_after_source_lock_or_symlink_mutation(self):
        self.prepare()
        adapter = self.root / 'Generated/MixerAndroid'
        android = {'adapterDigest': DRIVER_MODULE.source_tree(adapter)}
        lock = {'sdkDigest': DRIVER_MODULE.source_tree(self.root / 'Generated/MixerSDK')}
        frozen = DRIVER_MODULE.source_tree(self.root)
        apk = self.root / '.mixer/app.apk'
        apk.parent.mkdir()
        for relative in ('App.swift', 'Platforms/Android/Package.resolved',
                         'Generated/MixerSDK/Package.resolved', 'Generated/MixerAndroid/adapter.py'):
            with self.subTest(relative=relative):
                path = self.root / relative
                data = path.read_bytes()
                path.write_bytes(data + b' ')
                apk.write_bytes(b'rejected apk')
                with mock.patch.object(DRIVER_MODULE, 'admit_source_pair', return_value=b'appearance'), self.assertRaises(RuntimeError):
                    DRIVER_MODULE.finish_source_guard(self.root, adapter, android, lock, frozen, apk, {}, b'appearance')
                self.assertFalse(apk.exists())
                path.write_bytes(data)
        apk.write_bytes(b'rejected apk')
        (self.root / 'foreign-link').symlink_to(self.root / 'App.swift')
        with mock.patch.object(DRIVER_MODULE, 'admit_source_pair', return_value=b'appearance'), self.assertRaises(RuntimeError):
            DRIVER_MODULE.finish_source_guard(self.root, adapter, android, lock, frozen, apk, {}, b'appearance')
        self.assertFalse(apk.exists())

    def test_resolver_executable_class_mutation_refuses(self):
        path = self.root / 'App.swift'
        def chmod(command):
            self.resolve(command)
            path.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, 'source changed'):
            self.prepare(chmod)

    def test_postfreeze_source_and_lock_mutation_changes_identity(self):
        self.prepare()
        frozen = DRIVER_MODULE.source_tree(self.root)
        for path in (self.lock, self.root / 'App.swift'):
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            self.assertNotEqual(frozen, DRIVER_MODULE.source_tree(self.root))
            path.write_bytes(original)


class AndroidFinalAdmissionTests(CompatibilityFixture, unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='mixer-final-admission-')
        self.addCleanup(self.temporary.cleanup)
        self.initialize_compatibility(pathlib.Path(self.temporary.name).resolve())
        self.appearance = self.module.admit_source_pair(self.root, self.module.source_profile())
        self.frozen = self.module.source_tree(self.root)
        self.apk = self.root / '.mixer/android-build/app.apk'
        self.apk.parent.mkdir(parents=True)
        self.apk.write_bytes(b'owned rejected apk')
        self.neighbor = self.apk.with_name('other.apk')
        self.neighbor.write_bytes(b'unowned neighbor')

    def final_caller(self):
        tree = ast.parse(self.rendered.read_bytes())
        build = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build')
        start = next(i for i, n in enumerate(build.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'normalized' for t in n.targets)) + 1
        end = next(i for i, n in enumerate(build.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'receipt' for t in n.targets))
        env = dict(self.module.__dict__, root=self.root, adapter=self.adapter,
                   android=self.lock_value['android'], lock=self.lock_value,
                   source_before=self.frozen, apk_path=self.apk,
                   profile=self.module.source_profile(), appearance=self.appearance)
        exec(compile(ast.Module(body=build.body[start:end], type_ignores=[]), str(self.rendered), 'exec'), env)
        return env['source_after']

    def test_final_caller_accepts_unchanged_inputs(self):
        self.assertEqual(self.final_caller(), self.frozen)
        self.assertEqual(self.apk.read_bytes(), b'owned rejected apk')
        self.assertEqual(self.neighbor.read_bytes(), b'unowned neighbor')

    def test_final_caller_removes_apk_on_pinned_sdk_mismatch(self):
        member = next(iter(self.module.source_profile()['sdk_files']))
        path = self.sdk / member
        path.write_bytes(path.read_bytes() + b'changed')
        with self.assertRaisesRegex(RuntimeError, 'source compatibility rejected'):
            self.final_caller()
        self.assertFalse(self.apk.exists())
        self.assertEqual(self.neighbor.read_bytes(), b'unowned neighbor')

    def test_final_caller_removes_apk_on_source_observation_error(self):
        member = next(iter(self.module.source_profile()['sdk_files']))
        path = self.sdk / member
        primary = OSError('injected final pinned source read failure')
        original = pathlib.Path.open
        def observe(value, *args, **kwargs):
            if value == path:
                raise primary
            return original(value, *args, **kwargs)
        with mock.patch.object(pathlib.Path, 'open', observe):
            with self.assertRaises(OSError) as caught:
                self.final_caller()
        self.assertIs(caught.exception, primary)
        self.assertFalse(self.apk.exists())
        self.assertEqual(self.neighbor.read_bytes(), b'unowned neighbor')

    def test_final_caller_preserves_primary_error_if_unlink_fails(self):
        member = next(iter(self.module.source_profile()['sdk_files']))
        path = self.sdk / member
        primary = OSError('primary source observation error')
        original_open = pathlib.Path.open
        original_unlink = pathlib.Path.unlink
        def observe(value, *args, **kwargs):
            if value == path: raise primary
            return original_open(value, *args, **kwargs)
        def remove(value, *args, **kwargs):
            if value == self.apk: raise PermissionError('injected owned APK unlink refusal')
            return original_unlink(value, *args, **kwargs)
        with mock.patch.object(pathlib.Path, 'open', observe), mock.patch.object(pathlib.Path, 'unlink', remove):
            with self.assertRaises(OSError) as caught:
                self.final_caller()
        self.assertIs(caught.exception, primary)
        self.assertTrue(self.apk.exists())


if __name__ == '__main__':
    unittest.main()
