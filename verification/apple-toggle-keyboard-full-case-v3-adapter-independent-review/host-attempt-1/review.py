#!/usr/bin/env python3
"""Independent, process-free review of the exact sealed V3 post-build adapter.

No proposal is executed. Actual orchestration is entered only with a failing
preflight or a mismatched reviewed seal, before runtime output and commands.
"""
import copy
import datetime
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import stat
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
ADAPTER = ROOT / 'verification/apple-toggle-keyboard-full-case-v3-adapter'
PREP = ROOT / 'verification/apple-toggle-keyboard-full-case-preparation-v3'
EXPECTED_SEAL = '137b6dc9b681eff1358712c34d9b71a3b356072ee6954b4a99e9a8c32b60f46b'
METHODS = ['test000PublicSettingsFullKeyboardAccess', 'test010EnabledFromOff',
           'test020EnabledFromOn', 'test030StaleFromOff', 'test040StaleFromOn',
           'test050DisabledFromOff', 'test060DisabledFromOn']
BOUNDARY = []
OBSERVATIONS = {}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def record(path):
    info = path.lstat()
    result = {'mode': stat.S_IMODE(info.st_mode)}
    if stat.S_ISREG(info.st_mode):
        result.update(kind='file', bytes=info.st_size, sha256=sha(path))
    elif stat.S_ISDIR(info.st_mode):
        result.update(kind='directory')
    elif stat.S_ISLNK(info.st_mode):
        result.update(kind='symlink', target=os.readlink(path))
    else:
        raise ValueError('Special file in review input: ' + str(path))
    return result


def verify_packet():
    assert sha(ADAPTER / 'packet-seal.json') == EXPECTED_SEAL
    packet = read(ADAPTER / 'packet-seal.json')
    actual = {name: record(ROOT / name) for name in packet['files']}
    assert actual == packet['files'], 'Exact sealed adapter byte/mode record differs'
    selected = read(ADAPTER / 'selected-inputs.json')
    selected_actual = {name: record(ROOT / name) for name in selected['files']}
    assert selected_actual == selected['files'], 'Selected source/build/app input differs'
    assert read(ADAPTER / 'accepted-inputs-before.json') == read(ADAPTER / 'accepted-inputs-after.json')
    counts = {}
    for label, sealpath, expected in [
        ('producer', PREP / 'packet-seal.json', packet['producerSealSHA256']),
        ('sourceReview', ROOT / 'verification/apple-toggle-keyboard-full-case-independent-review-v3/review-seal.json', packet['independentSourceReviewSealSHA256']),
        ('build', ROOT / 'verification/apple-toggle-keyboard-full-case-v3-build/packet-seal.json', packet['buildSealSHA256']),
    ]:
        assert sha(sealpath) == expected, label + ' seal differs'
        entries = read(sealpath)['files']
        for name, expected_record in entries.items():
            current = record(ROOT / name)
            if isinstance(expected_record, str):
                assert sha(ROOT / name) == expected_record, name
            else:
                assert current == expected_record, name
        counts[label] = len(entries)
    inputs = read(PREP / 'input-bindings.json')
    for name, expected in inputs.items():
        assert sha(pathlib.Path(name) if name.startswith('/') else ROOT / name) == expected, name
    counts['inputBindings'] = len(inputs)
    runtime = read(PREP / 'runtime-selection.json')['files']
    assert sum(name.endswith('.py') for name in runtime) == 22
    assert sum(name.endswith('.json') for name in runtime) == 3
    for name, expected in runtime.items():
        assert sha(PREP / name) == expected, name
    assert not os.path.lexists(PREP / 'runtime')
    return dict(adapterSealSHA256=EXPECTED_SEAL, adapterFiles=len(actual), selectedFiles=len(selected_actual),
                sealFiles=counts, closedRuntimeSources=22, closedRuntimeCaseData=3,
                adapterFilesDigest=digest(actual), selectedFilesDigest=digest(selected_actual),
                producerFailureEvidenceSHA256=sha(ADAPTER / 'host-attempt-1/receipt.json'),
                buildOriginalFailureEvidenceSHA256=sha(ROOT / 'verification/apple-toggle-keyboard-full-case-v3-build/command.json'))


def audit(event, args):
    if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.fork', 'os.forkpty',
                 'os.exec', 'socket.connect', 'socket.bind', 'socket.getaddrinfo'}:
        BOUNDARY.append(event)
        raise AssertionError('Process/network/native boundary forbidden: ' + event)
    if event == 'open':
        path, mode, flags = args
        writes = isinstance(mode, str) and any(char in mode for char in 'wax+')
        writes = writes or (isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)))
        if writes and isinstance(path, (str, bytes)) and not pathlib.Path(os.fsdecode(path)).resolve().is_relative_to(BASE):
            raise AssertionError('Review write outside owned lane: ' + os.fsdecode(path))


sys.addaudithook(audit)
spec = importlib.util.spec_from_file_location('independent_sealed_adapter', ADAPTER / 'adapter.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class ReviewControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='review-host-', dir=BASE)
        cls.folder = pathlib.Path(cls.scratch.name)
        cls.helper = a.build_helper()
        cls.fixture = cls.folder / 'changed-real-bytes'
        cls.fixture.write_bytes(b'independent changed bytes\x00\xff\n')
        cls.fixture.chmod(0o600)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def test_exact_sealed_preflight_and_unselected_proposal(self):
        result = a.verify()
        self.assertEqual(result['sealSHA256'], EXPECTED_SEAL)
        self.assertEqual(result['expectedXCTestMethods'], METHODS)
        self.assertEqual(result['productArchiveSHA256'], '1064c8082add39b2dbaa5e0757c95673f8c54064a3e43adea49f3416fe3b2b1b')
        self.assertFalse(result['nativeExecution'])
        proposal = read(ADAPTER / 'run-proposal.json')
        self.assertEqual(proposal['status'], 'proposed-not-selected')
        self.assertFalse(proposal['executed'])
        self.assertFalse(proposal['compilerRetryPermitted'])
        self.assertFalse(proposal['applicationRebuildPermitted'])
        self.assertEqual(proposal['maximumOwnedInstances'], 1)
        self.assertEqual(proposal['methods'], METHODS)
        self.assertEqual(proposal['runtimePath'], str(PREP / 'runtime'))
        self.assertEqual(len(proposal['prerequisites']), 5)
        OBSERVATIONS['sealedPreflight'] = result

    def test_stale_source_stops_before_product_observation(self):
        stale = copy.deepcopy(read(a.BUILD / 'source-before.json'))
        stale['runner']['UITests/ToggleUITests.swift'] = record(self.fixture)
        with mock.patch.object(a, 'build_helper', return_value=self.helper), \
             mock.patch.object(self.helper, 'revalidate', return_value=stale), \
             mock.patch.object(self.helper, 'tree', side_effect=AssertionError('Product observation after stale source')) as later:
            with self.assertRaisesRegex(ValueError, 'Accepted source tree changed'):
                a.verify()
            later.assert_not_called()

    def test_stale_product_mode_stops_before_archive_or_tools(self):
        real_tree = self.helper.tree
        products = copy.deepcopy(read(a.BUILD / 'supplement/build-products-manifest.json')['products'])
        name = next(name for name, row in products.items() if row['kind'] == 'file')
        products[name]['mode'] ^= 0o100
        with mock.patch.object(a, 'build_helper', return_value=self.helper), \
             mock.patch.object(self.helper, 'tree', side_effect=lambda path: products if path == self.helper.PRODUCTS else real_tree(path)), \
             mock.patch.object(self.helper, 'verify_archive', side_effect=AssertionError('Archive after stale product')) as archive, \
             mock.patch.object(self.helper, 'tool_metadata', side_effect=AssertionError('Tool read after stale product')) as tools:
            with self.assertRaisesRegex(ValueError, 'Fresh compiled runner products changed'):
                a.verify()
            archive.assert_not_called()
            tools.assert_not_called()

    def test_stale_tool_actual_metadata_record_refused(self):
        real_record = self.helper.file_record
        selected = self.helper.DEVELOPER / 'usr/bin/xcodebuild'
        with mock.patch.object(a, 'build_helper', return_value=self.helper), \
             mock.patch.object(self.helper, 'file_record', side_effect=lambda path: record(self.fixture) if path == selected else real_record(path)):
            with self.assertRaisesRegex(ValueError, 'compiler/tool/SDK bindings changed'):
                a.verify()

    def test_stale_diagnostic_source_read_refused(self):
        selected = ROOT / 'verification/apple-toggle-keyboard-focus-v9-preparation/source/Prototype/TogglePanAdmission.swift'
        original = a.sha
        with mock.patch.object(a, 'sha', side_effect=lambda path: sha(self.fixture) if path == selected else original(path)):
            with self.assertRaisesRegex(ValueError, 'Selected V9 app source closure changed'):
                a.verify()

    def test_both_stale_app_archive_reads_refused(self):
        for folder in ['apple-toggle-keyboard-focus-v9-preparation', 'apple-toggle-native-failure-analysis/sdk26-comparator']:
            with self.subTest(folder=folder):
                selected = ROOT / 'verification' / folder / 'built-app.tar.gz'
                original = a.sha
                with mock.patch.object(a, 'sha', side_effect=lambda path: sha(self.fixture) if path == selected else original(path)):
                    with self.assertRaisesRegex(ValueError, 'Pinned adapter input changed'):
                        a.verify()

    def test_stale_sealed_adapter_bytes_stop_before_source(self):
        original = self.helper.file_record
        with mock.patch.object(a, 'build_helper', return_value=self.helper), \
             mock.patch.object(self.helper, 'file_record', side_effect=lambda path: record(self.fixture) if path == ADAPTER / 'adapter.py' else original(path)), \
             mock.patch.object(self.helper, 'revalidate', side_effect=AssertionError('Source after stale adapter')) as later:
            with self.assertRaisesRegex(ValueError, 'Bound bytes/mode changed'):
                a.verify()
            later.assert_not_called()

    def test_real_selected_byte_mode_and_symlink_controls(self):
        file = self.folder / 'mode-control'
        file.write_bytes(b'accepted independent control')
        file.chmod(0o600)
        expected = {str(file): record(file)}
        file.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'Bound bytes/mode changed'):
            a.records(self.helper, expected)
        file.chmod(0o600)
        file.write_bytes(b'changed independent control')
        with self.assertRaisesRegex(ValueError, 'Bound bytes/mode changed'):
            a.records(self.helper, expected)
        file.unlink()
        file.symlink_to(self.fixture)
        with self.assertRaisesRegex(ValueError, 'Bound bytes/mode changed'):
            a.records(self.helper, expected)

    def test_actual_composition_changes_exactly_two_bindings(self):
        snapshots = []
        def profile(frame, event, result):
            if event == 'return' and frame.f_code.co_filename == str(PREP / 'composition.py') and frame.f_code.co_name == 'compose':
                snapshots.append(dict(vars(result)))
        sys.setprofile(profile)
        try:
            h = a.compose()
        finally:
            sys.setprofile(None)
        self.assertTrue(snapshots)
        before = snapshots[-1]
        after = dict(vars(h))
        changes = sorted(name for name in before.keys() | after.keys() if before.get(name) is not after.get(name))
        self.assertEqual(changes, ['PRODUCT_ARCHIVE', 'verify'])
        self.assertIsInstance(h.verify, a.FreshPreflight)
        self.assertEqual(h.PRODUCT_ARCHIVE, a.ARCHIVE)
        self.assertEqual(h.SCOPES['interaction']['methods'], METHODS)
        self.assertEqual(len(h.SCOPES['interaction']['cases']), 6)
        self.assertEqual(h.RUN_DIR, PREP / 'runtime')
        OBSERVATIONS['compositionChanges'] = changes
        OBSERVATIONS['orchestrationSHA256'] = sha(PREP / 'orchestration.py')
        OBSERVATIONS['compositionSHA256'] = sha(PREP / 'composition.py')
        OBSERVATIONS['runtimeOrigins'] = {name: str(pathlib.Path(getattr(h, name).__code__.co_filename)) for name in ['cleanup', 'remove_ephemeral', 'run']}

    def test_preflight_failure_identity_stops_actual_runner_before_output(self):
        for error in [OSError('independent first read failure'), KeyboardInterrupt('independent interrupted read'), SystemExit('independent first exit')]:
            with self.subTest(error=type(error).__name__):
                h = a.compose()
                with mock.patch.object(a, 'verify', side_effect=error) as check, \
                     mock.patch.object(h, 'Commands', side_effect=AssertionError('Command recorder constructed')) as commands, \
                     mock.patch.object(h.secrets, 'token_hex', side_effect=AssertionError('Capability allocated')) as allocation, \
                     mock.patch.object(pathlib.Path, 'mkdir', side_effect=AssertionError('Runtime directory created')) as mkdir:
                    for _ in range(2):
                        with self.assertRaises(type(error)) as raised:
                            h.run(EXPECTED_SEAL, 'interaction')
                        self.assertIs(raised.exception, error)
                    self.assertIs(h.verify.first, error)
                    self.assertEqual(check.call_count, 1)
                    commands.assert_not_called()
                    allocation.assert_not_called()
                    mkdir.assert_not_called()
                self.assertFalse(os.path.lexists(PREP / 'runtime'))

    def test_real_stale_preflight_latches_before_native_boundary(self):
        h = a.compose()
        stale = OSError('independent accepted-source observation failed')
        with mock.patch.object(a, 'build_helper', return_value=self.helper), \
             mock.patch.object(self.helper, 'revalidate', side_effect=stale) as source, \
             mock.patch.object(h, 'Commands', side_effect=AssertionError('Command recorder constructed')) as commands, \
             mock.patch.object(pathlib.Path, 'mkdir', side_effect=AssertionError('Runtime output created')) as mkdir:
            for _ in range(2):
                with self.assertRaises(OSError) as raised:
                    h.run(EXPECTED_SEAL, 'interaction')
                self.assertIs(raised.exception, stale)
            self.assertIs(h.verify.first, stale)
            self.assertEqual(source.call_count, 1)
            commands.assert_not_called()
            mkdir.assert_not_called()

    def test_mismatched_review_seal_refuses_before_output(self):
        h = a.compose()
        with mock.patch.object(h, 'Commands', side_effect=AssertionError('Command recorder constructed')) as commands, \
             mock.patch.object(pathlib.Path, 'mkdir', side_effect=AssertionError('Runtime output created')) as mkdir:
            with self.assertRaisesRegex(ValueError, 'Root reviewed seal does not match'):
                h.run('unaccepted-independent-control', 'interaction')
            commands.assert_not_called()
            mkdir.assert_not_called()

    def test_outside_closed_import_is_refused(self):
        outside = types.ModuleType('durable_settings')
        outside.__file__ = str(self.folder / 'outside-durable-settings.py')
        outside.__spec__ = importlib.util.spec_from_file_location('durable_settings', outside.__file__)
        with mock.patch.dict(sys.modules, {'durable_settings': outside}):
            with self.assertRaisesRegex(ValueError, 'outside selected origin'):
                a.compose()
        self.assertFalse(os.path.lexists(PREP / 'runtime'))


def main():
    before = verify_packet()
    stream = io.StringIO()
    start = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReviewControls)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    output = stream.getvalue()
    (BASE / 'host-controls.stdout').write_text('')
    (BASE / 'host-controls.stderr').write_text(output)
    after = verify_packet()
    assert before == after, 'Accepted inputs changed during independent controls'
    cleanup = dict(schema=1, observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   ownedScratchAbsent=not any(BASE.glob('review-host-*')),
                   fixedRuntimeAbsent=not os.path.lexists(PREP / 'runtime'),
                   acceptedBeforeAfterEqual=before == after, prohibitedBoundaryAttempts=BOUNDARY,
                   nativeInstancesQueried=False, simulatorInstancesCreated=0, compilerInvoked=False,
                   nativeExecution=False, computerUse=False, screenCapture=False,
                   otherProjectProcessesOrDataAddressed=False, physicalPhones='disconnected-deferred')
    assert cleanup['ownedScratchAbsent'] and cleanup['fixedRuntimeAbsent'] and not BOUNDARY
    (BASE / 'cleanup.json').write_text(json.dumps(cleanup, sort_keys=True, indent=2) + '\n')
    receipt = dict(schema=1, observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   status='pass' if result.wasSuccessful() else 'failed',
                   argv=[sys.executable, '-B', str(pathlib.Path(__file__).resolve())], cwd=str(ROOT),
                   pythonVersion=sys.version, pythonExecutable=str(pathlib.Path(sys.executable).resolve()),
                   pythonBinarySHA256=sha(pathlib.Path(sys.executable).resolve()),
                   sourceRevision=read(ROOT / 'verification/apple-toggle-keyboard-full-case-root-review/v3-source/acceptance.json')['sourceRevision'],
                   revisionObservation='Inherited exact root acceptance metadata; no Git query',
                   reviewSourceSHA256=sha(pathlib.Path(__file__).resolve()),
                   methodsRun=result.testsRun, failureCount=len(result.failures), errorCount=len(result.errors),
                   elapsedSeconds=time.monotonic()-start, exitCode=0 if result.wasSuccessful() else 1,
                   stdoutSHA256=sha(BASE / 'host-controls.stdout'), stderrSHA256=sha(BASE / 'host-controls.stderr'),
                   inputVerification=before, observations=OBSERVATIONS,
                   environmentObservation='Inherited host environment; -B; process, network and outside-lane writes blocked by audit',
                   syntheticControls='Owned real byte/mode/symlink fixtures and selected read-boundary injection; no accepted input mutated',
                   applicationCasesExecuted=0, nativeExecution=False, gaAccepted=False)
    (BASE / 'host-controls.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(output, end='')
    print(json.dumps({'status': receipt['status'], 'methodsRun': result.testsRun, 'adapterSealSHA256': EXPECTED_SEAL,
                      'acceptedInputsUnchanged': before == after, 'ownedScratchAbsent': cleanup['ownedScratchAbsent']}))
    return receipt['exitCode']


if __name__ == '__main__':
    raise SystemExit(main())
