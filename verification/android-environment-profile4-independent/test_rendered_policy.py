#!/usr/bin/env python3
"""New independent scalar/projection/authority tests on the retained generated driver.

Only imported source-profile functions are called. All tool/output functions are
replaced by tripwires; no compiler/native/UI command may run in this test module.
"""
import copy
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RENDERED = HERE / 'actual-generated/android-build.py'
RAW = ROOT / 'verification/android-environment-platform-profile4/source/cli/Sources/MixerBuild/Resources/android-build.py'
PROFILE = json.loads((ROOT / 'verification/android-environment-platform-profile4/proposed-profile4.json').read_text())
PRIOR = json.loads((ROOT / 'verification/android-environment-platform-profile4/prior-profile3.json').read_text())
sys.dont_write_bytecode = True


def module(path):
    spec = importlib.util.spec_from_file_location('independent_policy_test_driver', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def project(files):
    return hashlib.sha256(''.join(n + '\0' + files[n]['sha256'] + '\n' for n in sorted(files)).encode()).hexdigest()


class RenderedPolicyTests(unittest.TestCase):
    def setUp(self):
        self.driver = module(RENDERED)
        self.events = []
        self.tmp = tempfile.TemporaryDirectory(prefix='mixer-independent-profile4-policy-', dir='/tmp')
        self.root = Path(self.tmp.name)
        for name in ['read_json', 'inspect', 'source_tree', 'checked_output', 'probe']:
            def forbidden(*args, name=name, **kwargs):
                self.events.append(name)
                raise AssertionError('Unexpected side effect: ' + name)
            setattr(self.driver, name, forbidden)

    def tearDown(self):
        self.tmp.cleanup()
        self.assertFalse(self.root.exists())

    def replace(self, profile):
        self.driver.SOURCE_PROFILE_HEX = json.dumps(profile, separators=(',', ':')).encode().hex()

    def refuse_before_build_inputs(self, profile):
        self.replace(profile)
        with self.assertRaisesRegex(RuntimeError, 'source profile is not rendered or supported'):
            self.driver.build(self.root)
        self.assertEqual(self.events, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_exact_rendered_policy_is_the_reviewed_map(self):
        self.assertEqual(self.driver.source_profile(), PROFILE)
        self.assertEqual(len(PROFILE['sdk_files']), 22)
        self.assertEqual(len(PROFILE['adapter_files']), 23)
        self.assertEqual(self.events, [])

    def test_raw_import_is_inert_and_unrendered_build_fails_first(self):
        raw = module(RAW)
        self.assertEqual(raw.SOURCE_PROFILE_HEX, '__MIXER_ANDROID_SOURCE_PROFILE_HEX__')
        raw.read_json = lambda *args: self.fail('Raw template read a lock before policy refusal')
        with self.assertRaisesRegex(RuntimeError, 'source profile is not rendered or supported'):
            raw.build(self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_profile3_rendering_never_reads_lock_or_tools(self):
        self.refuse_before_build_inputs(PRIOR)

    def test_closed_counts_still_fail_after_projection_recomputation(self):
        for kind in ['sdk', 'adapter']:
            with self.subTest(kind=kind):
                changed = copy.deepcopy(PROFILE)
                files = changed[kind + '_files']
                del files[sorted(files)[-1]]
                changed[kind + '_compatibility_sha256'] = project(files)
                self.refuse_before_build_inputs(changed)

    def test_inconsistent_projection_hashes_fail_before_inputs(self):
        for kind in ['sdk', 'adapter']:
            with self.subTest(kind=kind):
                changed = copy.deepcopy(PROFILE)
                changed[kind + '_compatibility_sha256'] = '0' * 64
                self.refuse_before_build_inputs(changed)

    def test_bool_and_oversized_identity_scalars_fail_before_inputs(self):
        changes = [(['schema'], True), (['default_descriptor', 'bytes'], True),
                   (['default_descriptor', 'bytes'], 65537),
                   (['sdk_files', 'Package.swift', 'bytes'], 1048577),
                   (['wire', 'document_schema'], True), (['wire', 'native_packet_schema'], True)]
        for path, replacement in changes:
            with self.subTest(path=path, value=replacement):
                changed = copy.deepcopy(PROFILE)
                parent = changed
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = replacement
                self.refuse_before_build_inputs(changed)

    def test_duplicate_rendered_profile_keys_fail_before_inputs(self):
        text = json.dumps(PROFILE, separators=(',', ':'))
        text = '{"schema":1,' + text[1:]
        self.driver.SOURCE_PROFILE_HEX = text.encode().hex()
        with self.assertRaisesRegex(RuntimeError, 'source profile is not rendered or supported'):
            self.driver.build(self.root)
        self.assertEqual(self.events, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_unsupported_profile_top_level_key_fails_before_inputs(self):
        changed = copy.deepcopy(PROFILE)
        changed['publicationAllowed'] = True
        self.refuse_before_build_inputs(changed)

    def test_local_lock_profile_has_no_release_or_signature_authority(self):
        lock = self.driver.profile_lock(self.driver.source_profile())
        self.assertEqual(set(lock), {'id', 'sdk_compatibility_sha256', 'adapter_compatibility_sha256', 'default_descriptor'})
        self.assertEqual(lock['default_descriptor'], PROFILE['default_descriptor'])
        self.assertNotIn('publicationAllowed', lock)
        self.assertNotIn('signature', lock)
        self.assertEqual(self.events, [])


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RenderedPolicyTests))
    mode = 'optimized' if sys.flags.optimize else 'normal'
    receipt = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'argv': sys.argv,
               'python': sys.version, 'optimization': sys.flags.optimize, 'methods': result.testsRun,
               'errors': len(result.errors), 'failures': len(result.failures), 'skips': len(result.skipped),
               'rendered_driver': identity(RENDERED), 'raw_template': identity(RAW),
               'scope': 'Host imported source-profile decoder and pre-build input/tool/output tripwires; not native runtime or publication authority',
               'owned_temporary_directories_removed': True, 'native_UI_capture_process_inventory_or_Git': False}
    (HERE / ('policy-tests-' + mode + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    sys.exit(0 if result.wasSuccessful() else 1)
