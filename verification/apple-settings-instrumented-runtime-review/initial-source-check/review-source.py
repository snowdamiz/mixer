#!/usr/bin/env python3
"""Finite independent source and host review; never invokes native tools."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest import mock

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / 'verification/apple-settings-instrumented-runtime-preparation'
BUILD = ROOT / 'verification/apple-settings-instrumented-native-build'
PRIOR = ROOT / 'verification/apple-focus-reference-runtime-v5-namespace-correction'
EXPECTED_HANDOFF = 'ca361bde1632c4ad4bbaf517817b9d8a5a9426a25d462738a9e03eeeb1786a3c'
EXPECTED_PACKET = 'f7ef1ed54b65a71e666646d1e4b54cef1cea5b7afdfee804810ffaf2c65eaeb6'
EXPECTED_BUILD = '246f5e9486f804d2ab784ba474696bcf7905873aa5a1200117b570bd66933e91'


def require(value, message):
    if not value:
        raise AssertionError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stable(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def row(path):
    info = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            'Canonical regular single-link input required')
    raw = path.read_bytes()
    return {'kind': 'file', 'mode': stat.S_IMODE(info.st_mode), 'bytes': len(raw), 'sha256': sha(raw)}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def archive(path, rows, expected_sha, prefix=''):
    require(row(path)['sha256'] == expected_sha, 'Archive identity differs')
    result, seen, directories = {}, set(), set()
    expected_dirs = {prefix.rstrip('/')} if prefix else set()
    for name in rows:
        expected_dirs.update(str(p) for p in PurePosixPath(prefix + name).parents if str(p) != '.')
    with tarfile.open(path, 'r:gz') as tar:
        for entry in tar.getmembers():
            name = PurePosixPath(entry.name)
            require(not name.is_absolute() and '..' not in name.parts and str(name) == entry.name
                    and entry.name not in seen, 'Archive path or duplicate differs')
            seen.add(entry.name)
            if entry.isdir():
                require(entry.mode == 0o755, 'Archive directory mode differs')
                directories.add(entry.name)
                continue
            require(entry.isfile() and entry.name.startswith(prefix), 'Archive type differs')
            key = entry.name[len(prefix):]
            require(key in rows, 'Unlisted archive member')
            raw = tar.extractfile(entry).read()
            require({'kind': 'file', 'mode': entry.mode, 'bytes': len(raw), 'sha256': sha(raw)} == rows[key],
                    'Archive member bytes/mode differ')
            result[key] = raw
    require(set(result) == set(rows) and directories == expected_dirs, 'Archive exact inventory differs')
    return result


def verify_inputs():
    handoff = json.loads((PRODUCER / 'handoff.json').read_bytes())
    require(sha((PRODUCER / 'handoff.json').read_bytes()) == EXPECTED_HANDOFF, 'Producer handoff differs')
    require(len(handoff['members']) == 61, 'Exact 61-member producer handoff required')
    require(sha(stable(handoff['members'])) == handoff['memberTreeSHA256'], 'Producer member digest differs')
    for name, expected in handoff['members'].items():
        require(row(ROOT / name) == expected, 'Producer member changed: ' + name)
    packet = json.loads((PRODUCER / 'packet.json').read_bytes())
    require(sha((PRODUCER / 'packet.json').read_bytes()) == EXPECTED_PACKET, 'Packet differs')
    require(sha((BUILD / 'handoff.json').read_bytes()) == EXPECTED_BUILD, 'Build handoff differs')
    for name, expected in packet['references'].items():
        require(row(ROOT / name) == expected, 'Direct reference changed: ' + name)
    for name, expected in packet['files'].items():
        require(row(PRODUCER / name) == expected, 'Prepared file changed: ' + name)
    old_manifest = json.loads((PRIOR / 'runtime-source-manifest.json').read_bytes())
    new_manifest = json.loads((PRODUCER / 'runtime-source-manifest.json').read_bytes())
    old = archive(PRIOR / 'runtime-sources.tar.gz', old_manifest['files'], old_manifest['archive']['sha256'], 'selected/')
    new = archive(PRODUCER / 'runtime-sources.tar.gz', new_manifest['files'], new_manifest['archive']['sha256'], 'selected/')
    changed = sorted(name for name in new if new[name] != old.get(name))
    require(changed == ['composition.py', 'importer.py', 'join_support.py', 'local_first_failure.py'],
            'Selected delta differs')
    require(len(old) == 31 and len(new) == 32 and sum(new[k] == old[k] for k in old) == 28,
            'Selected source counts differ')
    require(sha(stable(new_manifest['files'])) == packet['runtimeSourceTreeSHA256'] == new_manifest['treeSHA256'],
            'Runtime tree digest differs')
    restored = new['importer.py']
    old_source = '696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a'
    old_product = '0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8'
    for before, after in [(packet['sourceTreeSHA256'], old_source), (packet['nativeProductArchiveSHA256'], old_product),
                          ('mixer.apple-focus-reference-root-selection.6', 'mixer.apple-focus-reference-root-selection.5'),
                          ('MixerFocusReferenceV6-', 'MixerFocusReferenceV5-'),
                          ('mixer.apple-focus-reference-runtime-import.6', 'mixer.apple-focus-reference-runtime-import.5')]:
        require(restored.count(before.encode()) == 1, 'Expected single importer substitution')
        restored = restored.replace(before.encode(), after.encode(), 1)
    require(restored == old['importer.py'], 'Original strict importer changed beyond five identities')
    source = json.loads((BUILD / 'attempt-1/source-manifest.json').read_bytes())
    products = json.loads((BUILD / 'attempt-1/product-manifest.json').read_bytes())
    accepted_sources = archive(BUILD / 'attempt-1/accepted-sources.tar.gz', source['sources'], source['archive']['sha256'])
    archive(BUILD / 'attempt-1/products.tar.gz', products['products'], packet['nativeProductArchiveSHA256'])
    require(len(source['sources']) == 40 and len(products['products']) == 55, 'Fresh source/product counts differ')
    require(sha(stable(source['sources'])) == packet['sourceTreeSHA256'], 'Fresh compile source tree differs')
    require(sha(stable(products['products'])) == products['productTreeSHA256'], 'Fresh product tree differs')
    old_selection = json.loads((PRIOR / 'selection-template.json').read_bytes())
    application_names = [name for name in products['products'] if name.startswith('MixerToggleDiagnostics.app/')]
    require(len(application_names) == 13 and all(products['products'][n] == old_selection['productManifest']['products'][n]
                                               for n in application_names), 'Original 13 application files changed')
    acceptance_path = ROOT / 'verification/apple-settings-failure-instrumentation-root-review/acceptance.json'
    require(sha(acceptance_path.read_bytes()) == '9956f0384828da9cdd8082ca387716c439131f6a2f0c4fcde4065cc5c96995ff',
            'Diagnostic source acceptance differs')
    accepted = json.loads(acceptance_path.read_bytes())
    for name, digest in accepted['sourceFiles'].items():
        require(sha(accepted_sources['accepted/harness/UITests/' + name]) == digest, 'Compiled diagnostic source differs')
    first = json.loads((PRODUCER / 'commands/prepare/receipt.json').read_bytes())
    require(first['exitCode'] == 1 and first['ownedProcessGroup']['state'] == 'absent'
            and all(v['eof'] for v in first['streams'].values()), 'Initial validator failure not retained')
    for attempt in [2, 3]:
        control = json.loads((PRODUCER / f'attempt-{attempt}/receipt.json').read_bytes())
        require(control['passed'] and control['testsRun'] == 14 and control['skipped'] == 0
                and control['acceptedInputsAndPacketUnchanged'], 'Final producer controls differ')
    return {'schema': 1, 'producerHandoffSHA256': EXPECTED_HANDOFF, 'producerMembersVerified': 61,
            'packetSHA256': EXPECTED_PACKET, 'buildHandoffSHA256': EXPECTED_BUILD,
            'directReferencesVerified': len(packet['references']), 'compileSourcesVerified': 40,
            'nativeProductsVerified': 55, 'originalApplicationFilesUnchanged': 13,
            'runtimeSourceFilesVerified': 32, 'unchangedV5SourceFiles': 28, 'changedSelectedFiles': changed,
            'strictImporterRestoredByteExactlyAfterFiveIdentitySubstitutions': True,
            'sourceTreeSHA256': packet['sourceTreeSHA256'], 'runtimeSourceTreeSHA256': packet['runtimeSourceTreeSHA256'],
            'productArchiveSHA256': packet['nativeProductArchiveSHA256'], 'initialValidatorFailureRetained': True,
            'finalProducerControls': {'attempts': [2, 3], 'testsEach': 14, 'skippedEach': 0},
            'nativeExecuted': False, 'gaAccepted': False}


def controls(subject):
    # Load only the exact directly accepted producer sources. Relocate the data
    # and write root before installing their closed host audit boundary.
    p = load('prepare', PRODUCER / 'prepare.py')
    p.BASE = subject
    c = load('reviewed_original_controls', PRODUCER / 'run_controls.py')

    class IndependentControls(c.RuntimeControls):
        def test_15_real_capture_storage_failure_preserves_original_exception(self):
            with c.namespace() as (adapter, root, output):
                streams = {'stdout': adapter.local_first_failure.PREFIX + json.dumps(c.safe_sample()).encode() + b'\n', 'stderr': b''}
                session, _ = c.observe_files(adapter, root, output, streams)
                adapter.configure_root(root)
                adapter._selected = {'session': session}
                original = RuntimeError('synthetic authoritative command failure')
                def fail(*args):
                    raise original
                adapter._ORIGINAL_RUN_OBSERVED = fail
                with mock.patch.object(adapter.local_first_failure.os, 'open', side_effect=OSError('synthetic storage failure')):
                    with self.assertRaises(RuntimeError) as caught:
                        adapter.run_observed(None, [], 600, False, None)
                self.assertIs(caught.exception, original)
                self.assertFalse((session / 'local-settings-first-failure.json').exists())

        def test_16_success_result_preserved_and_real_receipt_mode_is_private(self):
            with c.namespace() as (adapter, root, output):
                streams = {'stdout': adapter.local_first_failure.PREFIX + json.dumps(c.safe_sample()).encode() + b'\n', 'stderr': b''}
                session, _ = c.observe_files(adapter, root, output, streams)
                (session / 'session.xcresult').mkdir()
                adapter.configure_root(root)
                adapter._selected = {'session': session, 'sessionIdentity': adapter.path_identity(session, 0o700)}
                original = object()
                adapter._ORIGINAL_RUN_OBSERVED = lambda *args: original
                self.assertIs(adapter.run_observed(None, [], 600, False, None), original)
                target = session / 'local-settings-first-failure.json'
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
                self.assertEqual(json.loads(target.read_bytes())['observedXCTestExitCode'], 65)

        def test_17_real_invalid_diagnostic_preserves_exception_and_first_receipt(self):
            with c.namespace() as (adapter, root, output):
                unsafe = c.safe_sample(); unsafe['payload'] = 'UNSAFE-NEVER-RETAIN'
                streams = {'stdout': adapter.local_first_failure.PREFIX + json.dumps(unsafe).encode() + b'\n', 'stderr': b''}
                session, _ = c.observe_files(adapter, root, output, streams)
                adapter.configure_root(root)
                adapter._selected = {'session': session}
                original = RuntimeError('UNSAFE-EXCEPTION-NEVER-RETAIN')
                def fail(*args):
                    raise original
                adapter._ORIGINAL_RUN_OBSERVED = fail
                with self.assertRaises(RuntimeError) as caught:
                    adapter.run_observed(None, [], 600, False, None)
                self.assertIs(caught.exception, original)
                target = session / 'local-settings-first-failure.json'; first = target.read_bytes()
                self.assertNotIn(b'UNSAFE', first)
                self.assertEqual(json.loads(first)['status'], 'unavailable-or-invalid')
                adapter.local_first_failure.capture(session, root)
                self.assertEqual(first, target.read_bytes())

        def test_18_nonterminal_exit_and_invalid_utf8_cannot_supply_metadata(self):
            for mode in ['exit', 'utf8']:
                with self.subTest(mode=mode), c.namespace() as (adapter, root, output):
                    raw = adapter.local_first_failure.PREFIX + (b'\xff' if mode == 'utf8' else json.dumps(c.safe_sample()).encode()) + b'\n'
                    session, observer = c.observe_files(adapter, root, output, {'stdout': raw, 'stderr': b''})
                    if mode == 'exit':
                        observer['exitCode'] = 1
                        (session / 'command-observer/observer.json').write_bytes(p.stable(observer))
                    result = adapter.local_first_failure.capture(session, root)
                    self.assertEqual(result['status'], 'unavailable-or-invalid')
                    self.assertIsNone(result['diagnostic'])
                    self.assertFalse(result['runPassed'])

        def test_19_missing_marker_code65_grants_no_native_credit(self):
            with c.namespace() as (adapter, root, output):
                session, _ = c.observe_files(adapter, root, output, {'stdout': b'console only\n', 'stderr': b''})
                result = adapter.local_first_failure.capture(session, root)
                self.assertEqual(result['status'], 'marker-not-observed')
                self.assertEqual(result['observedXCTestExitCode'], 65)
                self.assertIsNone(result['diagnostic'])
                for field in ['nativeImporterAcceptanceGranted', 'settingsPreconditionPassed', 'runPassed', 'gaAccepted']:
                    self.assertFalse(result[field])

    c.RuntimeControls = IndependentControls
    c.main()


def group_absent(group):
    try:
        os.killpg(group, 0)
        return False
    except ProcessLookupError:
        return True


def main():
    before = verify_inputs()
    (BASE / 'source-verification.json').write_bytes(stable(before))
    subject = Path(tempfile.mkdtemp(prefix='review-owned-', dir=BASE))
    packet = json.loads((PRODUCER / 'packet.json').read_bytes())
    for name in [*packet['files'], 'packet.json']:
        shutil.copyfile(PRODUCER / name, subject / name)
        (subject / name).chmod(0o644)
    argv = [sys.executable, '-B', str(Path(__file__).resolve()), '--controls', str(subject)]
    started = time.monotonic()
    process = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    timed_out, signals = False, []
    try:
        stdout, stderr = process.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out = True
        for chosen in [signal.SIGTERM, signal.SIGKILL]:
            if not group_absent(process.pid):
                os.killpg(process.pid, chosen); signals.append(int(chosen))
            try:
                stdout, stderr = process.communicate(timeout=2)
                break
            except subprocess.TimeoutExpired:
                continue
        else:
            raise RuntimeError('Owned review streams did not reach EOF')
    if not group_absent(process.pid):
        os.killpg(process.pid, signal.SIGKILL); signals.append(int(signal.SIGKILL))
    absent = group_absent(process.pid)
    (BASE / 'stdout.log').write_bytes(stdout)
    (BASE / 'stderr.log').write_bytes(stderr)
    if (subject / 'attempt-1').exists():
        shutil.copytree(subject / 'attempt-1', BASE / 'host-attempt')
    if (subject / 'dispatch-attempts').exists():
        shutil.copytree(subject / 'dispatch-attempts', BASE / 'synthetic-attempt-markers')
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'argv': argv, 'cwd': str(ROOT), 'reviewSource': row(Path(__file__).resolve()),
               'python': sys.version, 'pythonExecutable': str(Path(sys.executable).resolve()),
               'pythonExecutableSHA256': sha(Path(sys.executable).resolve().read_bytes()),
               'producerControls': row(PRODUCER / 'run_controls.py'), 'producerPrepare': row(PRODUCER / 'prepare.py'),
               'PID': process.pid, 'processGroup': process.pid, 'startNewSession': True,
               'exitCode': process.returncode, 'timedOut': timed_out, 'signals': signals,
               'elapsedSeconds': time.monotonic() - started,
               'ownedProcessGroup': {'state': 'absent' if absent else 'present', 'targetProcessGroup': process.pid},
               'streams': {name: {'bytes': len(raw), 'sha256': sha(raw), 'eof': True, 'readerFailed': False}
                           for name, raw in [('stdout', stdout), ('stderr', stderr)]},
               'packetSHA256': EXPECTED_PACKET, 'runtimeSourceTreeSHA256': before['runtimeSourceTreeSHA256'],
               'sourceRevisionMeaning': 'Inherited revision label 8b9b4950d23fd4595018deb751395e6bcc27d3e4; exact source hashes authoritative; no Git query',
               'nativeCommandsExecuted': 0, 'nativeInstancesCreatedOrQueried': 0, 'listenersStarted': 0,
               'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}
    (BASE / 'command-receipt.json').write_bytes(stable(receipt))
    shutil.rmtree(subject)
    after = verify_inputs()
    (BASE / 'cleanup.json').write_bytes(stable({'schema': 1, 'ownedScratch': str(subject),
        'ownedScratchAbsent': not subject.exists(), 'ownedProcessGroupAbsent': absent,
        'producerAndDirectInputBindingsUnchanged': before == after, 'nativeInstancesTouched': 0,
        'otherProjectsTouched': False, 'retained': 'Compact original controls receipt, synthetic dispatch output/marker, complete streams'}))
    require(process.returncode == 0 and not timed_out and absent and before == after, 'Independent review did not pass')
    print(json.dumps({'passed': True, 'tests': 19, 'packetSHA256': EXPECTED_PACKET,
                      'nativeExecuted': False, 'ownedScratchAbsent': not subject.exists()}))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--controls':
        controls(Path(sys.argv[2]))
    else:
        main()
