#!/usr/bin/env python3
"""Pure and fake-child bootstrap controls; never executes a toolchain or process probe."""
import argparse
import copy
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bootstrap_control', HERE / 'bootstrap.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


def good_result():
    outcomes = [dict(case=c, refusal={'status': 'error'}, driver_refusal='control refusal',
                     build_staging_created=False)
                for c in ('sdk', 'adapter', 'descriptor', 'extra-java', 'profile', 'missing-lock')]
    return {'status': 'passed-java-crosscompile-only', 'producer_jobs': 2,
            'consumers': {m + '-' + f: {'java_count': 18} for m in ('debug', 'release')
                          for f in ('original', 'relocated', 'exported')},
            'tamper': {m: copy.deepcopy(outcomes) for m in ('debug', 'release')},
            'cleanup': {'command_custody_terminal': True, 'owned_scratch_removed': True}}


class BootstrapControls(unittest.TestCase):
    def test_real_pair8_policy_and_all_sources(self):
        a = B.canonical()
        p = a.load_profile()
        self.assertEqual(p['id'], 'mixer.android-source-pair.8')
        self.assertEqual((len(p['sdk_files']), len(p['adapter_files']), len(a.java_roster(p))), (22, 24, 18))
        self.assertGreater(len(a.source_inputs(p)), 90)

    def test_non_hosted_cannot_admit(self):
        for env in ({}, {'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'Linux', 'RUNNER_ARCH': 'X64'},
                    {'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'macOS', 'RUNNER_ARCH': 'ARM64'}):
            with self.subTest(env=env), self.assertRaises(RuntimeError):
                B.hosted_environment(env)

    def test_hosted_missing_paths_cannot_admit(self):
        with self.assertRaises(RuntimeError):
            B.hosted_environment({'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'macOS',
                                  'RUNNER_ARCH': 'X64', 'RUNNER_TEMP': '/control'})

    def test_apple_selection_is_explicit_and_removes_inherited_routing(self):
        a = Mock()
        a.apple_producer_provenance.return_value = {'xcode_version': '26.6', 'xcode_build': '17F113', 'sdk_version': '26.5'}
        env, _ = B.apple_environment({'TOOLCHAINS': 'unrelated', 'DEVELOPER_DIR': '/other'}, a)
        self.assertNotIn('TOOLCHAINS', env)
        self.assertEqual(env['DEVELOPER_DIR'], str(B.DEVELOPER))
        self.assertEqual(env['SDKROOT'], str(B.SDKROOT))

    def test_old_xcode_cannot_admit(self):
        a = Mock()
        a.apple_producer_provenance.return_value = {'xcode_version': '26.3', 'xcode_build': '17C529', 'sdk_version': '26.2'}
        with self.assertRaises(RuntimeError):
            B.apple_environment({}, a)

    def test_download_is_bounded_and_checksum_admitted(self):
        run = Mock(return_value=B.SDK_URL)
        identify = Mock(return_value={'bytes': B.SDK_BYTES, 'sha256': B.SDK_SHA256})
        result = B.download(run, identify, 'control', B.SDK_URL, Path('/control/sdk'), B.SDK_BYTES, B.SDK_SHA256)
        self.assertEqual(result['sha256'], B.SDK_SHA256)
        argv = list(map(str, run.call_args.args[1]))
        self.assertEqual(argv[argv.index('--max-time') + 1], '300')
        self.assertEqual(argv[argv.index('--max-filesize') + 1], str(B.SDK_BYTES))
        self.assertIn('=https', argv)
        self.assertNotIn('--retry', argv)

    def test_checksum_refusal(self):
        with self.assertRaisesRegex(RuntimeError, 'checksum'):
            B.download(Mock(return_value=B.SDK_URL), lambda _: {'bytes': B.SDK_BYTES, 'sha256': '0'*64},
                       'control', B.SDK_URL, Path('/control/sdk'), B.SDK_BYTES, B.SDK_SHA256)

    def test_size_refusal(self):
        with self.assertRaisesRegex(RuntimeError, 'size'):
            B.download(Mock(return_value=B.HOST_URL), lambda _: {'bytes': 1, 'sha256': '0'*64},
                       'control', B.HOST_URL, Path('/control/host'), B.HOST_BYTES)

    def test_redirect_refusal_before_identity_read(self):
        identify = Mock()
        with self.assertRaisesRegex(RuntimeError, 'redirect'):
            B.download(Mock(return_value='https://example.invalid/other'), identify,
                       'control', B.SDK_URL, Path('/control/sdk'), B.SDK_BYTES, B.SDK_SHA256)
        identify.assert_not_called()

    def test_unsigned_package_never_expands(self):
        run = Mock(return_value='Status: no signature')
        with self.assertRaisesRegex(RuntimeError, 'trust'):
            B.extract_host(run, Path('/control/p'), Path('/control/e'), Path('/control/t'))
        self.assertEqual(run.call_count, 1)

    def test_signature_child_failure_never_expands(self):
        run = Mock(side_effect=RuntimeError('fake child nonzero'))
        with self.assertRaisesRegex(RuntimeError, 'nonzero'):
            B.extract_host(run, Path('/control/p'), Path('/control/e'), Path('/control/t'))
        self.assertEqual(run.call_count, 1)

    def test_trusted_fake_children_expand_private_payload(self):
        with tempfile.TemporaryDirectory(dir=HERE) as td:
            root = Path(td)
            archive, expanded, toolchain = root/'swift.pkg', root/'expanded', root/'swift.xctoolchain'
            archive.write_bytes(b'control package')
            events = []
            def run(label, argv):
                events.append(label)
                if label == 'swift-package-signature':
                    return 'Status: signed by a certificate trusted by macOS'
                if label == 'swift-package-expand':
                    expanded.mkdir()
                    (expanded/'Payload').write_bytes(b'control payload')
                if label == 'swift-package-payload':
                    (toolchain/'usr/bin').mkdir(parents=True)
                    swift = toolchain/'usr/bin/swift'
                    swift.write_bytes(b'control only, never executed')
                    swift.chmod(0o700)
                return ''
            result = B.extract_host(run, archive, expanded, toolchain)
            self.assertTrue(result.is_file())
            self.assertFalse(archive.exists())
            self.assertFalse(expanded.exists())
            self.assertEqual(events, ['swift-package-signature', 'swift-package-expand', 'swift-package-payload'])

    def test_actual_runner_direct_call_restores_environment_on_failure(self):
        a = Mock()
        a.execute.side_effect = RuntimeError('fake integration failure')
        args = argparse.Namespace(swift=Path('/control/swift'))
        before = dict(os.environ)
        with self.assertRaisesRegex(RuntimeError, 'integration failure'):
            B.run_integration(a, args, {'CONTROL': 'only'}, Path('/control/out'))
        self.assertEqual(dict(os.environ), before)
        selected = a.execute.call_args.args[0]
        self.assertTrue(selected.execute_toolchains)
        self.assertEqual(selected.output, Path('/control/out'))

    def test_complete_actual_result(self):
        B.validate_result(good_result())

    def test_missing_consumer_refusal(self):
        r = good_result()
        r['consumers'].pop('release-exported')
        with self.assertRaises(RuntimeError): B.validate_result(r)

    def test_missing_real_tamper_refusal(self):
        r = good_result()
        r['tamper']['release'].pop()
        with self.assertRaises(RuntimeError): B.validate_result(r)

    def test_unresolved_custody_or_scratch_refusal(self):
        for key in ('command_custody_terminal', 'owned_scratch_removed'):
            r = good_result()
            r['cleanup'][key] = False
            with self.subTest(key=key), self.assertRaises(RuntimeError): B.validate_result(r)

    def test_producer_concurrency_refusal(self):
        r = good_result()
        r['producer_jobs'] = 3
        with self.assertRaises(RuntimeError): B.validate_result(r)

    def test_full_inspection_cannot_be_platform_only(self):
        paths = {'swift': Path('/control/swift'), 'jdk': Path('/control/jdk'), 'android_sdk': Path('/control/sdk')}
        value = {'schema': 1, 'sdk_id': 'aarch64-unknown-linux-android28', 'min_api': 28, 'target_api': 37,
                 'swift_version': 'Swift version 6.3.3 control', 'javac_version': 'javac 25.control',
                 'tools': {'swift': {'path': '/control/swift'}, 'javac': {'path': '/control/jdk/bin/javac'}},
                 'distributions': {'android_platform': {'path': '/control/sdk/platforms/android-37.0'}}}
        with self.assertRaisesRegex(RuntimeError, 'Incomplete canonical distribution'):
            B.validate_inspection(value, paths)

    def test_inspection_rejects_different_tool_path(self):
        paths = {'swift': Path('/control/swift'), 'jdk': Path('/control/jdk'), 'android_sdk': Path('/control/sdk')}
        value = {'schema': 1, 'sdk_id': 'aarch64-unknown-linux-android28', 'min_api': 28, 'target_api': 37,
                 'swift_version': 'Swift version 6.3.3 control', 'javac_version': 'javac 25.control',
                 'tools': {'swift': {'path': '/other/swift'}, 'javac': {'path': '/control/jdk/bin/javac'}},
                 'distributions': {'android_platform': {'path': '/control/sdk/platforms/android-37.0'}}}
        with self.assertRaisesRegex(RuntimeError, 'unexpected tools'):
            B.validate_inspection(value, paths)

    def test_sdk_checksum_is_from_retained_official_release_metadata(self):
        text = (HERE/'sources/swift-releases.yml').read_text()
        release = text.split('- name: "6.3.3"\n', 1)[1].split('\n- name:', 1)[0]
        android = release.split('    - name: Android SDK\n', 1)[1]
        self.assertEqual(android.split('checksum: ', 1)[1].splitlines()[0], B.SDK_SHA256)

    def test_download_sizes_match_head_metadata(self):
        import json
        observed = json.loads((HERE/'sources/download-head.json').read_text())
        self.assertEqual({r['method'] for r in observed}, {'HEAD'})
        self.assertEqual({r['status'] for r in observed}, {200})
        self.assertEqual({r['name']: int(r['headers']['Content-Length']) for r in observed},
                         {'swift_host': B.HOST_BYTES, 'swift_android': B.SDK_BYTES})


if __name__ == '__main__':
    unittest.main()
