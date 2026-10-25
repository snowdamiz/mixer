#!/usr/bin/env python3
"""Independent, host-only controls for one exact prepared diagnostic packet."""
import argparse
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/apple-focus-diagnostic-runtime-v1'
METHODS = ['test000PublicSettingsFullKeyboardAccess', 'test010EnabledFromOff']
CASE = 'keyboard-enabled-off'


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def row(path):
    info = path.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and path.resolve() == path, path
    data = path.read_bytes()
    return {'kind': 'file', 'bytes': len(data), 'mode': stat.S_IMODE(info.st_mode), 'sha256': digest(data)}


def parents(names):
    return {str(parent) for name in names for parent in PurePosixPath(name).parents if str(parent) != '.'}


def exact_tree(path, expected):
    observed, directories = {}, set()
    assert path.resolve() == path and path.is_dir() and not path.is_symlink(), path
    for item in sorted(path.rglob('*')):
        name = str(item.relative_to(path))
        info = item.lstat()
        if stat.S_ISDIR(info.st_mode):
            assert stat.S_IMODE(info.st_mode) == 0o755, item
            directories.add(name)
        elif stat.S_ISLNK(info.st_mode):
            observed[name] = {'kind': 'symlink', 'mode': stat.S_IMODE(info.st_mode), 'target': os.readlink(item)}
        else:
            observed[name] = row(item)
    assert observed == expected, path
    assert directories == parents(expected), (path, directories ^ parents(expected))


def exact_archive(path, expected, prefix=''):
    files = {prefix + name: value for name, value in expected.items()}
    directories = parents(files)
    seen = set()
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive:
            assert member.name not in seen
            seen.add(member.name)
            name = PurePosixPath(member.name)
            assert str(name) == member.name and not name.is_absolute() and '..' not in name.parts
            if member.isdir():
                assert member.name in directories and member.mode == 0o755 and member.size == 0
            else:
                value = files[member.name]
                assert member.mode == value['mode']
                if value['kind'] == 'file':
                    assert member.isfile() and member.size == value['bytes']
                    payload = archive.extractfile(member).read(member.size + 1)
                    assert len(payload) == value['bytes'] and digest(payload) == value['sha256']
                else:
                    assert member.issym() and member.linkname == value['target']
    assert seen == set(files) | directories


class Review(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet = json.loads((PRODUCER / 'packet.json').read_bytes())
        cls.manifest = json.loads((PRODUCER / 'output-manifest.json').read_bytes())
        cls.selection = json.loads((PRODUCER / 'scratch/selected/runtime-selection.json').read_bytes())
        spec = importlib.util.spec_from_file_location('_independent_runtime_prepare', PRODUCER / 'prepare.py')
        cls.prepare = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.prepare)

    def setUp(self):
        self.work = RUN / self._testMethodName
        self.work.mkdir()

    @contextlib.contextmanager
    def producer_fixture(self):
        for source in sorted(PRODUCER.iterdir()):
            if source.is_file() and not source.is_symlink():
                shutil.copyfile(source, self.work / source.name)
                (self.work / source.name).chmod(stat.S_IMODE(source.stat().st_mode))
        with patch.object(self.prepare, 'BASE', self.work):
            self.assertEqual(self.prepare.verify()['packetSHA256'], EXPECTED_PACKET,
                             'A negative fixture must first pass unchanged.')
            yield

    def test_01_independent_exact_input_archive_output_and_source_closure(self):
        self.assertEqual(digest((PRODUCER / 'packet.json').read_bytes()), EXPECTED_PACKET)
        own = {name: row(PRODUCER / name) for name in self.packet['ownedSourceFiles']}
        self.assertEqual(own, self.packet['ownedSourceFiles'])
        self.assertEqual(digest(stable(own)), EXPECTED_SOURCE)
        self.assertEqual(digest(stable(own)), self.packet['ownedSourceTreeSHA256'])
        lock = json.loads((PRODUCER / 'input-lock.json').read_bytes())
        self.assertEqual(digest(stable(lock)), self.packet['inputLockSHA256'])
        for name, expected in lock['files'].items():
            self.assertEqual(row(ROOT / name), expected, name)
        self.assertEqual(row(ROOT / 'docs/apple-focus-diagnostic-runtime-v1.md'), self.packet['documentation'])
        self.assertEqual(digest(stable(self.manifest)), self.packet['outputManifestSHA256'])
        for key, folder in [('products', 'products'), ('acceptedSources', 'accepted'), ('selectedRuntime', 'selected')]:
            exact_tree(PRODUCER / 'scratch' / folder, self.manifest[key])
        build = ROOT / 'verification/apple-toggle-keyboard-focus-diagnostic-v1-build'
        exact_archive(build / 'products.tar.gz', self.manifest['products'])
        exact_archive(build / 'accepted-sources.tar.gz', self.manifest['acceptedSources'], 'accepted/')
        selected_archive = json.loads((PRODUCER / 'selected-runtime-source-manifest.json').read_bytes())
        self.assertEqual(digest(stable(selected_archive)), self.packet['selectedSourceArchiveManifestSHA256'])
        self.assertEqual(selected_archive['files'], self.manifest['selectedRuntime'])
        self.assertEqual(selected_archive['treeSHA256'], digest(stable(self.manifest['selectedRuntime'])))
        self.assertEqual(selected_archive['directoryMode'], 0o755)
        self.assertEqual(selected_archive['directories'], sorted(parents('selected/' + name for name in self.manifest['selectedRuntime'])))
        self.assertEqual(row(PRODUCER / 'selected-runtime-sources.tar.gz'), self.packet['selectedSourceArchive'])
        self.assertEqual(selected_archive['archive'], self.packet['selectedSourceArchive'])
        exact_archive(PRODUCER / 'selected-runtime-sources.tar.gz', self.manifest['selectedRuntime'], 'selected/')
        self.assertEqual(len(self.manifest['products']), 55)
        self.assertEqual(len(self.manifest['acceptedSources']), 39)
        original = json.loads((self.prepare.V3 / 'runtime-selection.json').read_bytes())
        changes = json.loads((PRODUCER / 'derivations.json').read_bytes())['changes']
        actual_changes = {}
        for name, after in self.selection['files'].items():
            before = original['files'].get(name)
            if before != after:
                actual_changes[name] = {'beforeSHA256': before, 'afterSHA256': after}
            if 'oracle.py' in name:
                self.assertEqual(before, after, name)
        self.assertEqual(changes, actual_changes)
        self.assertEqual(self.prepare.verify()['packetSHA256'], EXPECTED_PACKET)

    def test_02_reviewed_packet_rejects_replaced_input_lock(self):
        with self.producer_fixture():
            # Exact reviewed packet, exact sources and outputs; only the external
            # lock has been replaced in this owned fixture. No native call occurs.
            (self.work / 'input-lock.json').write_bytes(stable({'files': {}}))
            self.assertEqual(digest((self.work / 'packet.json').read_bytes()), EXPECTED_PACKET)
            with self.assertRaises(ValueError):
                self.prepare.verify()

    def test_03_packet_rejects_inconsistent_claimed_owned_source_digest(self):
        with self.producer_fixture():
            packet = json.loads((self.work / 'packet.json').read_bytes())
            packet['ownedSourceTreeSHA256'] = '0' * 64
            (self.work / 'packet.json').write_bytes(stable(packet))
            with self.assertRaises(ValueError):
                self.prepare.verify()

    def test_04_closed_import_binding_and_no_native_or_service_side_effect(self):
        selected = PRODUCER / 'scratch/selected'
        spec = importlib.util.spec_from_file_location('composition', selected / 'composition.py')
        fake = types.ModuleType('join_support')
        fake.__file__ = str(self.work / 'shadow.py')
        fake.__spec__ = importlib.util.spec_from_file_location('join_support', fake.__file__)
        with patch.dict(sys.modules, {'join_support': fake}):
            with self.assertRaisesRegex(ValueError, 'outside selected origin'):
                spec.loader.exec_module(importlib.util.module_from_spec(spec))
        module = importlib.util.module_from_spec(spec)
        def forbidden(*args, **kwargs):
            raise AssertionError('Native/process/service boundary invoked by import')
        sys.path.insert(0, str(selected))
        sys.modules['composition'] = module
        with patch.object(subprocess, 'Popen', forbidden), patch.object(socket, 'socket', forbidden):
            spec.loader.exec_module(module)
            module.bindings.check(module.RUNTIME_ROOTS)
        self.assertEqual(module.h.SCOPES['interaction'], {'cases': {CASE}, 'methods': METHODS})
        self.assertEqual(set(module.h.packet.CONFIGS), {'diagnostic'})
        code = compile('def injected(): return None\n', str(self.work / 'foreign-code.py'), 'exec')
        foreign = {'__name__': 'join_support'}
        exec(code, foreign)
        with patch.object(module.join_support, 'injected', foreign['injected'], create=True):
            with self.assertRaisesRegex(ValueError, 'function code outside selected origin'):
                module.bindings.check(module.RUNTIME_ROOTS)
        module.bindings.check(module.RUNTIME_ROOTS)
        Review.composition = module

    def test_05_method_selection_and_terminal_result_cannot_expand_scope(self):
        module = self.composition
        support = module.join_support
        session = self.work
        argv = [str(module.h.DEVELOPER / 'usr/bin/xcodebuild'), 'test-without-building', '-xctestrun',
                str(session / 'session.xctestrun'), '-destination',
                'platform=iOS Simulator,id=11111111-1111-4111-8111-111111111111',
                '-parallel-testing-enabled', 'NO', '-maximum-concurrent-test-simulator-destinations', '1',
                '-resultBundlePath', str(session / 'session.xcresult')]
        argv += ['-only-testing:MixerToggleUITests/ToggleUITests/' + method for method in METHODS]
        with patch.object(support, '_selected', None):
            for changed in [argv[:-1], argv + ['-only-testing:MixerToggleUITests/ToggleUITests/test020EnabledFromOn']]:
                with self.assertRaises(ValueError): support.select_command(module.h, changed, session)
            support.select_command(module.h, argv, session)
            self.assertTrue(support.is_selected(argv))
        runtime = self.work / 'runtime'
        runtime.mkdir()
        summary = {'result': 'Passed', 'totalTestCount': 2, 'passedTests': 2, 'failedTests': 0, 'skippedTests': 0, 'expectedFailures': 0}
        tests = [{'nodeType': 'Test Case', 'nodeIdentifier': 'ToggleUITests/' + method, 'result': 'Passed'} for method in METHODS]
        (runtime / 'xctest-summary.json').write_bytes(stable(summary))
        (runtime / 'xctest-tests.json').write_bytes(stable(tests))
        self.assertTrue(support.official_methods(self.work))
        tests[1]['nodeIdentifier'] = 'ToggleUITests/test020EnabledFromOn'
        (runtime / 'xctest-tests.json').write_bytes(stable(tests))
        self.assertFalse(support.official_methods(self.work))
        result = support.runtime_summary(self.work, module.h, module.oracle, module.setup_ready, 'interaction', None, 0, None, [])
        for key in ['runPassed', 'comparatorCredit', 'fullSixCaseQualification', 'nativeKeyboardQualification', 'carrierAccepted', 'gaAccepted']:
            self.assertIs(result[key], False, key)

    def test_06_secret_retirement_preserves_evidence_and_refuses_hardlink(self):
        module = self.composition
        support = module.join_support
        h = types.SimpleNamespace(RUN_DIR=self.work, PRODUCTS=module.h.PRODUCTS, write=module.h.write)
        life = {}
        session = support.prepare_session(h, life)
        config = support.session_configuration(h, session, 12345, 'a' * 64)
        retained = session / 'session.xcresult'
        retained.mkdir()
        (retained / 'retained').write_bytes(b'observer/result evidence')
        link = self.work / 'owned-hardlink-negative'
        os.link(config, link)
        with self.assertRaisesRegex(ValueError, 'Secret configuration identity changed'):
            support.retire_session(h, life)
        link.unlink()
        support.retire_session(h, life)
        self.assertFalse(config.exists())
        self.assertEqual((retained / 'retained').read_bytes(), b'observer/result evidence')
        self.assertNotIn(b'a' * 64, (session / 'configuration-derivation.json').read_bytes())
        self.assertTrue(life['secretConfigurationAbsent'])
        self.assertTrue(life['sessionEvidenceRetained'])

    def test_07_materialized_empty_directory_substitution_rejected(self):
        nested = self.work / 'nested'
        nested.mkdir(mode=0o755)
        payload = nested / 'payload'
        payload.write_bytes(b'exact materialized bytes')
        payload.chmod(0o644)
        baseline = self.prepare.tree(self.work)
        self.assertEqual(baseline, {'nested/payload': row(payload)})
        (self.work / 'unmanifested-empty-directory').mkdir(mode=0o755)
        for implementation in [self.prepare.tree, self.composition.join_support.product_tree]:
            with self.subTest(implementation=implementation.__module__ + '.' + implementation.__name__):
                with self.assertRaises(ValueError):
                    implementation(self.work)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--packet-sha', required=True)
    parser.add_argument('--source-tree-sha', required=True)
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    EXPECTED_PACKET, EXPECTED_SOURCE = args.packet_sha, args.source_tree_sha
    assert args.attempt.isidentifier()
    RUN = HERE / 'attempts' / args.attempt
    RUN.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(HERE / 'review.py', RUN / 'review-source.py')
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Review))
    (RUN / 'tests.log').write_text(log.getvalue())
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'command': [sys.executable, '-B', str(HERE / 'review.py'), *sys.argv[1:]], 'cwd': str(ROOT),
               'python': sys.version, 'pythonExecutable': str(Path(sys.executable).resolve()), 'platform': platform.platform(),
               'packetSHA256': EXPECTED_PACKET, 'ownedSourceTreeSHA256': EXPECTED_SOURCE,
               'reviewSource': row(HERE / 'review.py'), 'testsRun': result.testsRun,
               'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
               'passed': result.wasSuccessful(), 'testLog': row(RUN / 'tests.log'),
               'nativeExecuted': False, 'nativeInstancesQueried': False, 'serviceStarted': False,
               'physicalPhones': 'disconnected-deferred', 'fullSixCaseQualification': False, 'gaAccepted': False,
               'scope': 'Independent exact archive/input/output/source review plus isolated lock/digest/import/method/capability controls; host Python only.'}
    (RUN / 'receipt.json').write_bytes(stable(receipt))
    print(log.getvalue(), end='')
    raise SystemExit(0 if result.wasSuccessful() else 1)
