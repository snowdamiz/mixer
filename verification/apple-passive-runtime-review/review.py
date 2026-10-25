#!/usr/bin/env python3
"""Independent finite host review. Selected native entry points are never called."""
import contextlib
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import socket
import stat
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / 'verification/apple-passive-lifecycle-runtime-preparation'
BUILD = ROOT / 'verification/apple-passive-lifecycle-sendable-correction/build-attempt-1'
PRIOR = ROOT / 'verification/apple-focus-system-runtime-preparation'
HANDOFF_SHA = '88ab5fbfe323510fbdf356c2f5effb6844ea2aeb3fec6758d8f88071ba30fc1f'
PACKET_SHA = 'c26a540837298c950b0b46ae244290fd830fc21121bec9b8ce5a5c991d18b658'
RUNTIME_SHA = 'f84622920bd0f59e9ce99eb6d0f44d237191302c79576731edbe67d5c344ec41'
RUNTIME_TREE = '6ba7477e4e16502bbd5058ded5fbff8f97bce15a28f4800ae883517532761dd2'
SOURCE_ARCHIVE = 'bf31888a14490e83e2424f458eac0cf8f56258d581ff2fc4034840b0d1783663'
SOURCE = 'f402eba7b6fa8abf2671e3a95441351dace37f291a9d55024232c9112b2720fb'
PRODUCT = '495f83c4702f7b229be495756f0a524c700f07159c5e21975dea471d118a8904'
PRODUCT_TREE = '1132e5c80d5fc426b7d0562a5a674ee2302be701f835852da05a4d53c4f1f5fc'
FORBIDDEN = ('catalog-inspector', 'authority-driver', 'worker-transport')
INPUTS, PROBES, DENIED = {}, [], []


def stable(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def row(path):
    ensure(not any(part in str(path).lower() for part in FORBIDDEN), 'Excluded lane')
    info = path.lstat()
    ensure(path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
           'Canonical single-link regular input required: ' + str(path))
    raw = path.read_bytes()
    return {'kind': 'file', 'mode': stat.S_IMODE(info.st_mode), 'bytes': len(raw), 'sha256': sha(raw)}


def bind(path, expected=None):
    result = row(path)
    if isinstance(expected, str):
        ensure(result['sha256'] == expected, 'Pinned digest mismatch: ' + str(path))
    elif expected is not None:
        ensure(set(expected) <= {'kind','bytes','mode','sha256','linkCount'}
               and {'bytes','mode','sha256'} <= set(expected)
               and {k: {**result, 'linkCount': 1}[k] for k in expected} == expected,
               'Pinned input metadata mismatch: ' + str(path))
    INPUTS[str(path.relative_to(ROOT))] = result
    return json.loads(path.read_bytes()) if path.suffix == '.json' else result


def handoff(path, digest, count):
    value = bind(path, digest)
    ensure(len(value['members']) == count, 'Handoff count differs')
    if 'memberTreeSHA256' in value:
        ensure(sha(stable(value['members'])) == value['memberTreeSHA256'], 'Handoff tree differs')
    for name, expected in value['members'].items():
        bind(ROOT / name, expected)
    return value


def archive(path, expected_sha, files, prefix='', directories=None):
    bind(path, expected_sha)
    result, seen, actual_dirs = {}, set(), set()
    with tarfile.open(path, 'r:gz') as stream:
        for item in stream:
            name = item.name
            pure = PurePosixPath(name)
            ensure(name and str(pure) == name and not pure.is_absolute() and '..' not in pure.parts
                   and name not in seen, 'Unsafe/duplicate archive name')
            seen.add(name)
            if item.isdir():
                ensure(item.mode == 0o755, 'Archive directory mode differs')
                actual_dirs.add(name)
                continue
            ensure(item.isfile() and name.startswith(prefix), 'Archive type/prefix differs')
            key = name[len(prefix):]
            ensure(key in files, 'Unexpected archive file')
            raw = stream.extractfile(item).read()
            ensure(files[key] == {'kind': 'file', 'mode': item.mode, 'bytes': len(raw), 'sha256': sha(raw)},
                   'Archive byte/mode mismatch: ' + key)
            result[key] = raw
    ensure(set(result) == set(files) and actual_dirs == set(directories or []), 'Archive inventory differs')
    return result


def inputs():
    sealed = handoff(PRODUCER / 'handoff.json', HANDOFF_SHA, 49)
    packet = bind(PRODUCER / 'packet.json', PACKET_SHA)
    ensure(sealed['packetSHA256'] == PACKET_SHA and len(packet['references']) == 8, 'Compact packet linkage differs')
    immediate = [
      ('verification/apple-focus-system-runtime-preparation/handoff.json', '20dd17885f3c9b923465299da1cff9044ae178cb448b026c531552be87f332c5', 59),
      ('verification/apple-focus-system-runtime-review/handoff.json', '874ce792b4353f5b8ae21a5e08ea655c7909ba5111a104a28708caed600c8d89', 26),
      ('verification/apple-focus-system-native-result/handoff.json', '0d4ff885c95e54386cd06e53794077defa7acac5cf63525583a8053f053c90de', 10),
      ('verification/apple-passive-lifecycle-sendable-correction/handoff.json', '207821bc258c351b1767932ad7b2e85dd7f621f3ad7e56054bcb3cfdcf87ed88', 81),
      ('verification/apple-passive-sendable-review/handoff.json', '859892145e06424104de36370c5811fb47dedacf34a6a0546e8f796b9fb3e2e1', 29)]
    seals = {name: handoff(ROOT/name, digest, count) for name,digest,count in immediate}
    ensure(sum(count for _,_,count in immediate) == 205, 'Immediate member checks differ')
    for name, expected in packet['references'].items(): bind(ROOT/name, expected)
    for name, expected in packet['files'].items(): bind(PRODUCER/name, expected)
    ensure(set(packet['references']) == {name for name,_,_ in immediate} | {
      'verification/current-diagnostic-corrections-root-review/apple-acceptance.json',
      'verification/apple-focus-system-native-build/attempt-1/source-manifest.json',
      'verification/apple-focus-system-native-build/attempt-1/sources.tar.gz'}, 'Immediate reference inventory differs')
    acceptance = bind(ROOT/'verification/current-diagnostic-corrections-root-review/apple-acceptance.json',
      'f86d268cb38cbbcce4578bfec10175be95900c9bb2281b95564b1e4a52d3df66')
    ensure(acceptance['sourceAndGenericBuildAccepted'] is True and acceptance['hostRuntimePreparationSelected'] is True
      and acceptance['nativeRunSelected'] is False and acceptance['candidateArchiveSHA256'] == SOURCE_ARCHIVE
      and acceptance['productArchiveSHA256'] == PRODUCT and acceptance['producerMembers'] == 81
      and acceptance['independentMembers'] == 29 and acceptance['gaAccepted'] is False, 'Root scope differs')
    review = seals[immediate[1][0]]
    ensure(review['status'] == 'source-and-host-runtime-preparation-accepted' and review['blockingFindings'] == []
      and review['packetSHA256'] == '70dcc748cf67ce6573215b3815736aca4689707cc081d34c8069f9b5f13c3a82'
      and review['nativeSelected'] is False, 'Immediate accepted V8 review differs')
    correction = seals[immediate[4][0]]['audit']
    ensure(correction['passed'] is True and correction['blockingFindings'] == [] and correction['producerByteIdenticalMembers'] == 41
      and correction['producerChangedMembers'] == 1 and correction['baselineByteIdenticalMembers'] == 39
      and correction['candidateArchiveSHA256'] == SOURCE_ARCHIVE and correction['productArchiveSHA256'] == PRODUCT
      and correction['futureRuntimeIngestionAccepted'] is False and correction['nativeExecuted'] is False
      and correction['runtimeSelected'] is False, 'Correction review scope differs')
    m = bind(PRODUCER/'runtime-source-manifest.json')
    ensure(len(m['files']) == 32 and sha(stable(m['files'])) == m['treeSHA256'] == RUNTIME_TREE, 'Runtime tree differs')
    runtime = archive(PRODUCER/'runtime-sources.tar.gz', RUNTIME_SHA, m['files'], 'selected/', m['directories'])
    old_manifest = bind(PRIOR/'runtime-source-manifest.json')
    old = archive(PRIOR/'runtime-sources.tar.gz', old_manifest['archive']['sha256'], old_manifest['files'], 'selected/', old_manifest['directories'])
    delta = bind(PRODUCER/'binding-delta.json')
    ensure(delta['baselinePacketSHA256'] == '70dcc748cf67ce6573215b3815736aca4689707cc081d34c8069f9b5f13c3a82', 'Baseline packet differs')
    changed = sorted(k for k in runtime if runtime[k] != old[k])
    ensure(changed == ['importer.py','join_support.py','local_first_failure.py'], 'Changed-file set differs')
    ensure(sorted(set(runtime)-set(changed)) == delta['unchangedRuntimeFiles'] and len(runtime)-len(changed) == 29, 'Unchanged bytes differ')
    for name,replacements in delta['changedRuntimeFiles'].items():
        derived = old[name]
        for replacement in replacements:
            before,after = replacement['before'].encode(),replacement['after'].encode()
            ensure(derived.count(before) == replacement['occurrences'], 'Old literal count differs')
            derived = derived.replace(before,after)
        ensure(derived == runtime[name], 'Full literal derivative differs')
        restored = runtime[name]
        for replacement in reversed(replacements):
            before,after = replacement['before'].encode(),replacement['after'].encode()
            ensure(restored.count(after) == replacement['occurrences'], 'New literal count differs')
            restored = restored.replace(after,before)
        ensure(restored == old[name], 'Reverse whole-file recovery differs')
    # Fix the allowed literal set independently of the producer's self-description.
    ensure(delta['changedRuntimeFiles'] == {
      'importer.py': [{'before':a,'after':b,'occurrences':1} for a,b in [
        ('ddd4036d785c1c5f0161f8146ee7295b8df8dcd2bd615b45eebefc4112fcfb0d',SOURCE),
        ('681059d32edbd63128c8f4552af2ed161d6dce05847397ffa6ce57b5402364d9',PRODUCT),
        ('mixer.apple-focus-reference-root-selection.8','mixer.apple-focus-reference-root-selection.9'),
        ('MixerFocusReferenceV8-','MixerFocusReferenceV9-'),
        ('mixer.apple-focus-reference-runtime-import.8','mixer.apple-focus-reference-runtime-import.9')]],
      'join_support.py': [{'before':'native-run-v8-','after':'native-run-v9-','occurrences':1},
        {'before':'mixer.apple-focus-reference-runtime.8','after':'mixer.apple-focus-reference-runtime.9','occurrences':1}],
      'local_first_failure.py': [{'before':'native-run-v8-','after':'native-run-v9-','occurrences':2}]}, 'Allowed literal inventory differs')
    sm = bind(BUILD/'source-manifest.json')
    ensure(len(sm['sources']) == len(sm['selectedArchiveMembers']) == 42 and sha(stable(sm['sources'])) == sm['sourceTreeSHA256'] == SOURCE
      and sm['overallSwiftFiles'] == 37 and len(sm['prototypeSwiftFiles']) == 12, 'Compile source closure differs')
    compile_payload = archive(BUILD/'sources.tar.gz', '42fce2c1e14ef5672677430ab730008d3349bf80cb064a794d38c500ef1dc6eb', sm['sources'])
    selected = archive(BUILD.parent/'review-source-package.tar.gz', SOURCE_ARCHIVE, sm['selectedArchiveMembers'])
    ensure(compile_payload == {n.removeprefix('accepted/'):r for n,r in selected.items()} and all(r['mode'] == 0o444 for r in sm['sources'].values()), 'Exact source bytes/modes differ')
    old_build = ROOT/'verification/apple-focus-system-native-build/attempt-1'
    old_sm = bind(old_build/'source-manifest.json')
    old_compile = archive(old_build/'sources.tar.gz', '3cfd2e83369b566a48cc50f263ff879bc7da2c7b49cb0a836980da7c5b39cdc1', old_sm['sources'])
    ensure(len(old_compile) == 40 and sorted(set(compile_payload)-set(old_compile)) == ['source/Prototype/PassiveLifecycleData.swift','source/Prototype/PassiveLifecycleObserver.swift']
      and not (set(old_compile)-set(compile_payload)) and [n for n in sorted(old_compile) if old_compile[n] != compile_payload[n]] == ['source/Prototype/main.swift']
      and sum(old_compile[n] == compile_payload[n] for n in old_compile) == 39, 'Passive source delta differs')
    transport = compile_payload['harness/UITests/DiagnosticTransport.swift']
    tests = compile_payload['harness/UITests/ToggleUITests.swift']
    ensure(transport == old_compile['harness/UITests/DiagnosticTransport.swift'] and tests == old_compile['harness/UITests/ToggleUITests.swift']
      and b'private let chunkBytes = 4992' in tests and b'data.count <= 8192' in transport and b'body.count <= 8192' in tests, 'Unchanged native chunk/8 KiB guards differ')
    pm = bind(BUILD/'product-manifest.json')
    ensure(len(pm['products']) == 55 and sha(stable(pm['products'])) == pm['productTreeSHA256'] == PRODUCT_TREE
      and pm['sourceTreeSHA256'] == SOURCE and pm['appProductFiles'] == 13 and pm['runnerProductFiles'] == 42
      and pm['oldAppProductFilesCopied'] == 0 and pm['appProductsFresh'] is True and pm['runnerProductsFresh'] is True, 'Product freshness differs')
    products = archive(BUILD/'products.tar.gz', PRODUCT, pm['products'])
    history = bind(ROOT/'verification/apple-focus-system-native-result/result.json')
    ensure(history['officialMethods'] == {'test000PublicSettingsFullKeyboardAccess':'Passed','test010ReferenceFirstTab':'Failed'}
      and history['nativePassed'] is False and history['xcodebuildExitCode'] == 65 and history['failedOriginalPredicates'] == ['actualNativeFocusTraversal']
      and history['otherOriginalPredicatesPassed'] == 19 and history['sourceAndProductScratchAbsent'] is True, 'Original V8 failed verdict differs')
    producer_result = bind(PRODUCER/'attempt-1/receipt.json')
    ensure(producer_result['testsRun'] == 16 and producer_result['passed'] is True and [producer_result[k] for k in ['failures','errors','skipped']] == [0,0,0], 'Producer controls differ')
    for label in ['prepare','controls']:
        failed = bind(PRODUCER/('commands/'+label+'/receipt.json'))
        ensure(failed['exitCode'] == 1 and failed['timedOut'] is False and failed['ownedProcessGroup']['state'] == 'absent', 'Retained initial failure differs')
    ensure(b'linkCount' in (PRODUCER/'attempts/preflight-1/explanation.json').read_bytes()
      and b'Sealed member changed: docs/apple-focus-system-native-result.md' in (PRODUCER/'commands/prepare/stderr.log').read_bytes()
      and b'FileNotFoundError' in (PRODUCER/'commands/controls/stderr.log').read_bytes(), 'Failure explanation/streams differ')
    ensure(packet['futureRuntimeOriginalsSelected'] is False and packet['futureSupplementalJoinSelected'] is False
      and packet['nativeExecuted'] is False and packet['runtimeSelected'] is False and packet['gaAccepted'] is False
      and packet['outputPrefix'] == 'native-run-v9-' and packet['rootSelectionSchema'] == 'mixer.apple-focus-reference-root-selection.9'
      and packet['simulatorNamePrefix'] == 'MixerFocusReferenceV9-' and delta['frozenV7JoinAnchorAuthority'] == 'replay-only', 'Selection authority differs')
    selection = bind(PRODUCER/'selection-template.json')
    ensure(set(selection['files']) == set(runtime) and selection['files'] == {n:sha(r) for n,r in runtime.items()}, 'Selection runtime source mapping differs')
    ensure(not any('focus_system_join' in n or 'focus-system-join' in n for n in selection['moduleAliases'].values()), 'Frozen join entered composition')
    PROBES.append({'control':'closed-input-identity','v9Members':49,'immediateSeals':5,'immediateMemberChecks':205,
      'recursiveHistoricalRowsCopied':False,'runtimeFiles':32,'unchangedRuntimeFiles':29,'compileSourceMembers':42,'overallSwiftFiles':37,
      'prototypeSwiftFiles':12,'freshProductFiles':55,'retainedV8Failure':True,'retainedPreflightFailures':2,'nativeChunkBytes':4992,'nativeRequestResponseGuardBytes':8192})
    return packet,m,runtime,pm,products,selection


def audit(event, args):
    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'pty.spawn'}:
        DENIED.append({'event': event})
        raise PermissionError('Independent review forbids native/process/network activity')
    if event in {'open', 'os.scandir', 'os.listdir'} and args and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0]))
        if not path.is_absolute() and event == 'open':
            caller = sys._getframe(1)
            if caller.f_code is shutil._rmtree_safe_fd_step.__code__:
                path = Path(caller.f_locals['path'])
        path = path.resolve()
        ensure(not any(part in str(path).lower() for part in FORBIDDEN), 'Excluded lane access')
        writing = event == 'open' and ((isinstance(args[1], str) and any(c in args[1] for c in 'wax+'))
                   or len(args) > 2 and isinstance(args[2], int) and bool(args[2] & (os.O_WRONLY | os.O_RDWR)))
        if writing and not path.is_relative_to(BASE):
            raise PermissionError('Independent review cannot write outside owned lane')
        if not (path.is_relative_to(BASE) or path.is_relative_to(Path(sys.base_prefix).resolve())
                or str(path) in ALLOWED or str(path) == '/dev/null'):
            DENIED.append({'event': event, 'path': str(path)})
            raise PermissionError('Independent closed-input read boundary')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def materialize(destination, rows, payload):
    destination.mkdir(mode=0o755)
    for name, metadata in rows.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload[name]); path.chmod(metadata['mode'])


def root_fixture():
    return {'schema': 'mixer.apple-focus-reference-root-selection.9',
            'runID': 'aaaabbbb-cccc-4ddd-8eee-ffff00001111', 'packetSHA256': PACKET_SHA,
            'selectedAtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'ownedSimulatorIdentity': {'udid': 'ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF',
                'name': 'MixerFocusReferenceV9-independent-host-fixture',
                'runtime': 'com.apple.CoreSimulator.SimRuntime.iOS-26-5', 'build': '23F77'},
            'sourceTreeSHA256': SOURCE, 'productArchiveSHA256': PRODUCT,
            'developerDirectory': '/Applications/Xcode_26.6.app/Contents/Developer',
            'baselineDevices': {'devices': {}}, 'baselineFrontends': []}


@contextlib.contextmanager
def composed():
    folder = Path(tempfile.mkdtemp(prefix='module-', dir=SCRATCH))
    root = root_fixture(); output = folder / ('native-run-v9-' + root['runID']); output.mkdir()
    materialize(output / 'selected', MANIFEST['files'], RUNTIME)
    materialize(output / 'products', PRODUCTS['products'], PRODUCT_BYTES)
    selection = copy.deepcopy(SELECTION)
    selection.update(repositoryRoot=str(ROOT), outputBase=str(output), productsRoot=str(output / 'products'), trustedRootSelection=root)
    (output / 'selected/runtime-selection.json').write_bytes(stable(selection))
    saved = list(sys.path)
    try:
        with mock.patch.dict(sys.modules):
            for alias in selection['moduleAliases']: sys.modules.pop(alias, None)
            sys.path.insert(0, str(output / 'selected'))
            yield load('composition', output / 'selected/composition.py'), root, output
    finally:
        sys.path[:] = saved
        shutil.rmtree(folder)


def observer(importer, root, session, streams, code):
    return {'schema': 'mixer.apple-command-finalization-observer.2',
            'argv': importer.command_argv(root, session), 'resultBundle': str(session / 'session.xcresult'),
            'exitCode': code, 'startNewSession': True, 'successInferredFromConsoleOrMarkers': False,
            'PID': 43210, 'processGroup': 43210, 'ownedProcessGroup': {'state': 'absent', 'targetProcessGroup': 43210},
            'cleanup': {'attempted': False, 'complete': None, 'signals': []},
            'streams': {n: {'eof': True, 'readerFailed': False, 'readerErrors': [], 'observedBytes': len(b),
                            'retainedBytes': len(b), 'retainedSHA256': sha(b)} for n,b in streams.items()}}


CLEANUPS = ['loopback-server-shutdown', 'loopback-server-close', 'loopback-thread-join',
            'ephemeral-capability-workspace-removal', 'owned-simulator-and-baseline-reconciliation']


class Controls(unittest.TestCase):
    def test_01_actual_composition_and_mode_product_origin_negatives(self):
        with composed() as (m, root, output):
            self.assertFalse(m.h.verify()['nativeAcceptanceGranted'])
            m.bindings.check(m.RUNTIME_ROOTS)
            self.assertEqual(m.importer.SOURCE, SOURCE); self.assertEqual(m.importer.PRODUCT, PRODUCT)
            self.assertEqual(m.METHODS, list(m.importer.METHODS))
            self.assertEqual(m.selection['cases'], ['keyboard-enabled-off'])
            self.assertEqual((m.telemetry.CHUNK, m.telemetry.MAX_DURATION, m.telemetry.MAX_UPLOADS,
                              m.telemetry.MAX_TOTAL, m.telemetry.MAX_REQUESTS, m.telemetry.MAX_EVENTS),
                             (4992, 29.0, 32, 7_000_000, 2500, 100))
            source = output / 'selected/importer.py'; raw = source.read_bytes()
            source.write_bytes(raw + b'\n# independent mutation\n')
            with self.assertRaises(ValueError): m.bindings.check(m.RUNTIME_ROOTS)
            source.write_bytes(raw)
            name = next(iter(PRODUCTS['products'])); product = output / 'products' / name
            mode = stat.S_IMODE(product.stat().st_mode); product.chmod(mode ^ 0o100)
            with self.assertRaises(ValueError): m.h.verify()
            product.chmod(mode)
            raw = product.read_bytes(); product.write_bytes(raw + b'changed')
            with self.assertRaises(ValueError): m.h.verify()
            product.write_bytes(raw); m.h.verify()
            fake = types.ModuleType('importer'); fake.__file__ = m.importer.__file__; fake.__spec__ = m.importer.__spec__
            exec(compile('def fake(): return None\n', '/unselected/independent.py', 'exec'), vars(fake))
            with self.assertRaises(ValueError): m.bindings.module(fake)
            PROBES.append({'control':'actual-composition', 'runtimeFiles':32, 'productFiles':55,
                           'sourceByteMutationRejected':True,'productModeAndByteMutationRejected':True,
                           'foreignCodeOriginRejected':True})

    def test_02_v9_root_accepts_and_mixed_old_identities_reject(self):
        with composed() as (m, root, _):
            self.assertEqual(m.importer.validate_root(root, PACKET_SHA, fresh=True), root)
            mutations = [('schema', 'mixer.apple-focus-reference-root-selection.8'),
                         ('sourceTreeSHA256', 'ddd4036d785c1c5f0161f8146ee7295b8df8dcd2bd615b45eebefc4112fcfb0d'),
                         ('productArchiveSHA256', '681059d32edbd63128c8f4552af2ed161d6dce05847397ffa6ce57b5402364d9'),
                         ('packetSHA256', '0'*64), ('selectedAtUTC', '2026-10-24T00:00:00+00:00'),
                         ('selectedAtUTC', (datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=10)).isoformat())]
            for field, value in mutations:
                changed = copy.deepcopy(root); changed[field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    m.importer.validate_root(changed, PACKET_SHA, fresh=True)
            changed = copy.deepcopy(root); changed['ownedSimulatorIdentity']['name'] = 'MixerFocusReferenceV8-fixture'
            with self.assertRaises(ValueError): m.importer.validate_root(changed)
            with self.assertRaises(ValueError): m.join_support.configure_root(root)
            PROBES.append({'control':'root-identities','acceptedV9':True,'rejectedMixedIdentities':7,
                           'secondConfigureRejected':True})

    def test_03_actual_selector_once_v9_and_bad_session_mode(self):
        with composed() as (m, root, output):
            session = output / 'runtime/session'; session.mkdir(parents=True, mode=0o755)
            argv = m.importer.command_argv(root, session)
            with self.assertRaises(ValueError): m.join_support.select_command(m.h, argv, session)
            # The original selector records before the mode check; this failed
            # selection is intentionally poisoned, so use a fresh composition.
        with composed() as (m, root, output):
            session = output / 'runtime/session'; session.mkdir(parents=True, mode=0o700)
            argv = m.importer.command_argv(root, session)
            m.join_support.select_command(m.h, argv, session)
            with self.assertRaises(ValueError): m.join_support.select_command(m.h, argv, session)
            self.assertFalse(m.join_support._selected['called'])
            PROBES.append({'control':'actual-selector','v9SelectedOnce':True,'badSessionModeRejected':True,
                           'nativeCommandCalled':False})

    def test_04_v9_local_capture_accepts_old_output_namespace_rejects(self):
        with composed() as (m, root, output):
            for prefix, accepted in [('native-run-v8-', False), ('native-run-v9-', True)]:
                folder = output if accepted else output.parent / (prefix + root['runID'])
                session = folder / 'runtime/session'; session.mkdir(parents=True, mode=0o700)
                obs = session / 'command-observer'; obs.mkdir()
                streams = {'stdout': b'no local failure marker\n', 'stderr': b''}
                (obs / 'observer.json').write_bytes(stable(observer(m.importer, root, session, streams, 65)))
                for n,raw in streams.items(): (obs / (n+'.log')).write_bytes(raw)
                result = m.local_first_failure.capture(session, root)
                self.assertEqual(result['status'], 'marker-not-observed' if accepted else 'unavailable-or-invalid')
                self.assertEqual((session / 'local-settings-first-failure.json').exists(), accepted)
                self.assertFalse(result['runPassed']); self.assertFalse(result['nativeImporterAcceptanceGranted'])
            PROBES.append({'control':'local-failure-namespace','v9Retained':True,'v8RejectedWithoutWrite':True})

    def test_05_synthetic_official_import_schemas_preserve_failed_and_incomplete(self):
        with composed() as (m, root, output):
            session = output / 'runtime/session'
            i = m.importer; identity = root['ownedSimulatorIdentity']
            device = {'deviceId':identity['udid'],'deviceName':identity['name'],'platform':'iOS Simulator',
                      'osVersion':'26.5','osBuildNumber':'23F77','architecture':'arm64'}
            start = i.datetime_ns(root['selectedAtUTC']) / 1_000_000_000 + 1
            for failed in [False, True]:
                code = 65 if failed else 0
                counts = {'passedTests':1 if failed else 2,'failedTests':1 if failed else 0,'skippedTests':0,'expectedFailures':0}
                summary = dict(counts,totalTestCount=2,result='Failed' if failed else 'Passed',startTime=start,finishTime=start+2,
                               devicesAndConfigurations=[dict(counts,device=device,testPlanConfiguration={'configurationId':'1','configurationName':'Test Scheme Action'})])
                tests = {'devices':[device],'testNodes':[{'nodeType':'Test Case','nodeIdentifier':'ToggleUITests/'+method+'()',
                         'nodeIdentifierURL':i.PREFIX+method,'name':method+'()', 'result':'Failed' if failed and index==1 else 'Passed'}
                         for index,method in enumerate(i.METHODS)]}
                settings = stable({'schema':'mixer.apple-toggle.keyboard-settings.1','step':'setup-enabled','passed':True,
                                   'bundle':'com.apple.Preferences','route':m.telemetry.ROUTE,'fullKeyboardAccessValue':'1'})
                manifest = [{'testIdentifier':'ToggleUITests/'+method+'()','testIdentifierURL':i.PREFIX+method,
                             'attachments':([] if index else [{'exportedFileName':'settings.json','deviceId':identity['udid'],
                               'deviceName':identity['name'],'configurationName':'Test Scheme Action',
                               'suggestedHumanReadableName':'Public Settings setup-enabled_independent','timestamp':start+1}])}
                            for index,method in enumerate(i.METHODS)]
                raw = {'summary':stable(summary),'tests':stable(tests),'manifest':stable(manifest)}
                payloads = {'settings.json':settings}; streams = {'stdout':b'', 'stderr':b''}
                official = i.CapturedOfficial(i._CAPTURE_TOKEN,root,session,code,raw,payloads,{})
                o = observer(i,root,session,streams,code); cleanups = [{'resource':n,'passed':True} for n in CLEANUPS]
                result = i.import_selected(root,session,o,streams,official,payloads,{},cleanups,m.oracle,m.reference_contract)
                self.assertEqual(result['schema'], 'mixer.apple-focus-reference-runtime-import.9')
                self.assertTrue(result['provenanceAccepted']); self.assertEqual(result['officialMethodResults'][i.METHODS[1]], 'Failed' if failed else 'Passed')
                self.assertFalse(result['runPassed']); self.assertFalse(result['singleTabDiagnosticEvidencePassed'])
                self.assertEqual(result['diagnosticOutcome'], 'unknown')
                for mutation in ['wrong-exit','missing-cleanup','foreign-root','absent-official']:
                    broken_o = copy.deepcopy(o); broken_cleanups = copy.deepcopy(cleanups); broken_root = copy.deepcopy(root); cap = official
                    if mutation=='wrong-exit': broken_o['exitCode'] = 0 if failed else 65
                    if mutation=='missing-cleanup': broken_cleanups.pop()
                    if mutation=='foreign-root': broken_root['runID'] = 'bbbbcccc-dddd-4eee-8fff-000011112222'
                    if mutation=='absent-official': cap = {}
                    rejected = i.import_selected(broken_root,session,broken_o,streams,cap,payloads,{},broken_cleanups,m.oracle,m.reference_contract)
                    self.assertFalse(rejected['provenanceAccepted']); self.assertFalse(rejected['runPassed'])
                    self.assertEqual(rejected['diagnosticOutcome'], 'invalid-or-incomplete-evidence')
                PROBES.append({'control':'synthetic-official-import','officialTabResult':'Failed' if failed else 'Passed',
                               'schema':result['schema'],'missingOriginalsGrantNoVerdict':True,'runPassed':False,
                               'negativeMutationsRejected':4,'syntheticOnly':True})
            result = m.join_support.runtime_summary(output,m.h,m.oracle,m.setup_ready,'interaction',None,65,None,None)
            self.assertEqual(result['schema'],'mixer.apple-focus-reference-runtime.9'); self.assertFalse(result['runPassed'])

    def test_06_capture_writer_retains_new_original_bytes_without_join_authority(self):
        with composed() as (m, _, output):
            folder = output / 'runtime/captures'; folder.mkdir(parents=True)
            instance = object.__new__(m.transport.Bridge); instance.output = folder; instance.generation = 1
            raw = {'state':{'focused':False},'events':[{'sequence':1}],
                   'focusSystemDiagnostic':{'independentHostSynthetic':True,'callbacks':[{'sequence':1,'focused':False}]}}
            for suffix in ['before-1','after-1','keyboard-witness-1']:
                instance.save(suffix, raw)
                path = folder / ('0001-'+suffix+'.json'); before = path.read_bytes()
                self.assertEqual(json.loads(before), raw)
                with self.assertRaises(ValueError): instance.save(suffix, {'substitute':True})
                self.assertEqual(path.read_bytes(), before)
            self.assertFalse(any('focus-system-join' in str(getattr(v,'__file__','')) for v in sys.modules.values() if v))
            PROBES.append({'control':'unchanged-capture-writer','rawOriginalRolesRetained':3,
                           'substitutionRejected':True,'frozenJoinImported':False,'futureOriginalsSelected':False})

    def test_07_actual_failed_dispatch_keeps_marker_and_retires_scratch(self):
        clone = SCRATCH / 'producer-clone'; clone.mkdir()
        for name in set(PACKET['files']) | {'packet.json'}:
            original = PRODUCER / name; target = clone / name
            target.write_bytes(original.read_bytes()); target.chmod(stat.S_IMODE(original.stat().st_mode))
        saved = list(sys.path)
        try:
            with mock.patch.dict(sys.modules):
                p = load('_independent_preparation', PRODUCER / 'prepare.py'); p.BASE = clone
                root = root_fixture(); selection = clone / 'synthetic-root-selection.json'; selection.write_bytes(stable(root))
                output = clone / ('native-run-v9-' + root['runID'])
                real_spec = importlib.util.spec_from_file_location
                primary = RuntimeError('independent synthetic selected-entry failure before native activity')
                calls = []
                def intercepted(name, path, *args, **kwargs):
                    spec = real_spec(name, path, *args, **kwargs)
                    if name != 'composition': return spec
                    original = spec.loader
                    class Loader:
                        def create_module(self, value): return original.create_module(value)
                        def exec_module(self, module):
                            original.exec_module(module)
                            def entry(seal):
                                calls.append(seal)
                                self_outer.assertFalse(module.h.verify()['nativeAcceptanceGranted'])
                                raise primary
                            module.h.run = entry
                    spec.loader = Loader(); return spec
                self_outer = self
                with mock.patch.object(importlib.util, 'spec_from_file_location', intercepted):
                    for alias in SELECTION['moduleAliases']: sys.modules.pop(alias, None)
                    with self.assertRaises(RuntimeError) as caught: p.dispatch(PACKET_SHA, selection, sha(selection.read_bytes()))
                    self.assertIs(caught.exception, primary); self.assertEqual(len(calls),1)
                    cleanup = json.loads((output / 'scratch-cleanup.json').read_bytes())
                    self.assertTrue(cleanup['verifiedBeforeRemoval']); self.assertTrue(cleanup['scratchAbsent'])
                    marker = clone / ('dispatch-attempts/'+root['runID']+'.json'); first = marker.read_bytes()
                    self.assertEqual(stat.S_IMODE(marker.stat().st_mode),0o600)
                    retained = BASE / 'synthetic-dispatch'; retained.mkdir()
                    (retained / 'marker.json').write_bytes(first)
                    (retained / 'scratch-cleanup.json').write_bytes((output / 'scratch-cleanup.json').read_bytes())
                    (retained / 'root-selection.json').write_bytes(selection.read_bytes())
                    output.rename(clone / 'completed-synthetic-output')
                    with self.assertRaises(FileExistsError): p.dispatch(PACKET_SHA, selection, sha(selection.read_bytes()))
                    self.assertEqual(marker.read_bytes(),first); self.assertEqual(len(calls),1)
                    selection.write_bytes(selection.read_bytes()+b'\n')
                    with self.assertRaises(ValueError): p.dispatch(PACKET_SHA, selection, sha(stable(root)))
                PROBES.append({'control':'actual-failed-dispatch','compositionEntries':1,'primaryFailurePreserved':True,
                               'sourceProductScratchRetired':True,'markerMode':0o600,'markerBytesUnchanged':True,
                               'retryRejectedAfterOutputMove':True,'changedOutOfBandSelectionRejected':True,
                               'nativeEntryReplacedBeforeInvocation':True})
        finally:
            sys.path[:] = saved
            shutil.rmtree(clone)

    def test_08_audit_denies_ambient_process_and_network(self):
        with self.assertRaises(PermissionError): (ROOT / 'AGENTS.md').read_bytes()
        with self.assertRaises(PermissionError): sys.audit('subprocess.Popen','not-launched',[],None,None)
        with self.assertRaises(PermissionError): sys.audit('socket.bind',None,('127.0.0.1',0))
        PROBES.append({'control':'audit-boundary','ambientReadProcessSocketProbesDenied':3})

    def test_09_actual_cleanup_survives_primary_cleanup_and_reporting_failures(self):
        with composed() as (m, root, output):
            events = []; primary = RuntimeError('independent primary selected-command failure')
            reporting = RuntimeError('independent reporting failure')
            def clean(label):
                events.append(label)
                if label == 'loopback-server-close': raise RuntimeError('independent close failure')
            class Commands:
                def __init__(self, *args): self.reporting_error = None
                def redact(self, value): return value
                def record(self, *args): raise reporting
                def simctl(self, *args):
                    self_outer.assertEqual(args, ('list','runtimes','--json'))
                    return json.dumps({'runtimes':[{'identifier':'synthetic-runtime','buildversion':'synthetic-build','isAvailable':True}]})
                def run(self, argv, **kwargs):
                    if argv[:3] == ['/usr/bin/xcrun','simctl','bootstatus']: return (0,'','')
                    self_outer.assertEqual(argv, m.importer.command_argv(root, output / 'runtime/session'))
                    raise primary
            class Server:
                server_port = 12345
                def serve_forever(self): raise AssertionError('Synthetic server must never start')
                def shutdown(self): clean(CLEANUPS[0])
                def server_close(self): clean(CLEANUPS[1])
            class Thread:
                def __init__(self, **kwargs): pass
                def start(self): pass
                def join(self, timeout): clean(CLEANUPS[2])
                def is_alive(self): return False
            def allocate(*args):
                path = output / 'runtime/session'; path.mkdir(mode=0o700); return path
            h = types.SimpleNamespace(select_runtime_directory=lambda _:output/'runtime',
                SCOPES={'interaction':{'cases':{'keyboard-enabled-off'},'methods':m.METHODS}},
                verify=lambda:{'sealSHA256':'synthetic-host-seal'}, require=ensure,
                secrets=types.SimpleNamespace(token_hex=lambda _:'synthetic-ephemeral-token'),
                Commands=Commands,json=json,RUNTIME='synthetic-runtime',RUNTIME_BUILD='synthetic-build',
                write=lambda *args:None,devices=lambda _: {},owned_device=lambda *args:{'state':'Booted'},
                packet=types.SimpleNamespace(CONFIGS={}),Bridge=lambda *args,**kwargs:object(),
                server_for=lambda _:Server(),threading=types.SimpleNamespace(Thread=Thread),
                DEVELOPER=Path(root['developerDirectory']),ROOT=ROOT,
                cleanup=lambda *args:clean(CLEANUPS[4]),
                runtime_summary=lambda scope,bridge,code,failure,cleanup:{'runPassed':False,'cleanupResults':cleanup})
            self_outer = self
            with mock.patch.object(m.join_support,'prepare_session',allocate), \
                 mock.patch.object(m.join_support,'session_configuration',lambda *args:output/'runtime/session/session.xctestrun'), \
                 mock.patch.object(m.join_support,'retire_session',lambda *args:clean(CLEANUPS[3])):
                with self.assertRaises(RuntimeError) as caught:
                    m.orchestration.run(h,types.SimpleNamespace(check=lambda _:None),[],'synthetic-host-seal')
            self.assertIs(caught.exception, primary)
            self.assertEqual(events,CLEANUPS)
            self.assertEqual([r['passed'] for r in h.last_runtime_summary['cleanupResults']],[True,False,True,True,True])
            self.assertFalse(h.last_runtime_summary['runPassed'])
            self.assertEqual(h.last_outcome.first,primary)
            self.assertIn('session-failure-report',[r['operation'] for r in h.last_outcome.failures])
            self.assertIn('cleanup-report',[r['operation'] for r in h.last_outcome.failures])
            PROBES.append({'control':'actual-orchestration-cleanup','actionsAttemptedInOrder':events,
                           'cleanupPasses':[True,False,True,True,True],'primaryFailurePreserved':True,
                           'reportingFailuresCannotSkipCleanup':True,'runPassed':False,'syntheticOnly':True})


def main():
    global PACKET, MANIFEST, RUNTIME, PRODUCTS, PRODUCT_BYTES, SELECTION, SCRATCH, ALLOWED
    ensure(not (BASE / 'result.json').exists(), 'Preserve first review result')
    PACKET, MANIFEST, RUNTIME, PRODUCTS, PRODUCT_BYTES, SELECTION = inputs()
    before = dict(INPUTS)
    ALLOWED = {str(ROOT / n) for n in INPUTS}
    # The sealed producer sources are imported only under host controls; no
    # producer control main, frozen supplemental join, or native runner executes.
    SCRATCH = Path(tempfile.mkdtemp(prefix='review-owned-',dir=BASE))
    sys.addaudithook(audit)
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        shutil.rmtree(SCRATCH)
    unchanged = all(row(ROOT/n) == expected for n,expected in before.items())
    (BASE / 'input-bindings.json').write_bytes(stable(before))
    report = {'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'status':'source-and-host-runtime-preparation-accepted' if result.wasSuccessful() and unchanged else 'review-failed',
              'sourceRevisionReportedByRoot':'7b6048642b42e4900cccff4e14aa0fe8949ab35e',
              'inheritedBuildRevision':'6b8aba350224ed19f678669bdbea6b359d8de68b',
              'sourceRevisionMeaning':'Root-provided context only; no Git query. Exact sealed archives authoritative.',
              'packetSHA256':PACKET_SHA,'producerHandoffSHA256':HANDOFF_SHA,
              'runtimeArchiveSHA256':RUNTIME_SHA,'runtimeTreeSHA256':RUNTIME_TREE,
              'sourceArchiveSHA256':SOURCE_ARCHIVE,'compileSourceTreeSHA256':SOURCE,
              'productArchiveSHA256':PRODUCT,'productTreeSHA256':PRODUCT_TREE,
              'producerHostMethodsInherited':16,'independentMethodsRun':result.testsRun,
              'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
              'blockingFindings':[] if result.wasSuccessful() and unchanged else ['Review execution incomplete or failed'],
              'probes':PROBES,'deniedActions':DENIED,'verifiedInputFiles':len(before),
              'inputsUnchanged':unchanged,'ownedScratchAbsent':not SCRATCH.exists(),
              'python':sys.version,'reviewScriptSHA256':sha(Path(__file__).read_bytes()),
              'nativeCommandsExecuted':0,'nativeInstancesCreatedOrQueried':0,'listenersStarted':0,
              'nestedChildProcessesCreated':0,'nativeExecuted':False,'nativeSelected':False,
              'frozenV7JoinImportedOrExecuted':False,'futureRuntimeOriginalsSelected':False,
              'futureSupplementalJoinSelected':False,'physicalPhones':'disconnected-deferred','gaAccepted':False}
    (BASE / 'result.json').write_bytes(stable(report))
    print(json.dumps({'status':report['status'],'methods':result.testsRun,'inputsUnchanged':unchanged,
                      'ownedScratchAbsent':report['ownedScratchAbsent'],'nativeExecuted':False}))
    if not result.wasSuccessful() or not unchanged: raise SystemExit(1)


if __name__ == '__main__': main()
