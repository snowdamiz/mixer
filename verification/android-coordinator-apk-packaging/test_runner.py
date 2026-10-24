#!/usr/bin/env python3
"""Actual transformed runner host guards; SDK/native operations are injected fakes."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import struct
import tarfile
from types import SimpleNamespace, ModuleType
import unittest
import warnings
import zipfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('packaging_adapter', HERE / 'run.py')
ADAPTER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ADAPTER)
RUNNER, SOURCE, DIFF = ADAPTER.load_runner()
PROBE = ADAPTER.load_module('accepted_identity_probe', ADAPTER.PROBE)
EVIDENCE = None
CASES = []
PACKAGING_CASES = []


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


class Clock:
    value = 0

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class Child:
    pid = 210000

    def __init__(self, harness):
        self.h = harness
        self.actions = []
        self.code = 1 if harness.mode == 'early-exit' else None

    def poll(self):
        return self.code

    def wait(self, timeout):
        if self.code is None:
            raise subprocess.TimeoutExpired('host-fake-child', timeout)
        return self.code

    def terminate(self):
        self.actions.append('terminate')
        if self.h.mode != 'kill-fallback':
            self.code = -15

    def kill(self):
        self.actions.append('kill')
        self.code = -9


class Harness:
    def __init__(self, mode, metadata):
        self.mode, self.metadata = mode, metadata
        self.clock = Clock()
        self.commands, self.spawns, self.group_stops = [], [], []
        self.child = None
        packet = b'host synthetic packet; not a native result'
        self.packet = packet
        self.native = {'hostFixtureOnly': True, 'status': 'passed', 'checks': 9,
                       'operations': 7 if mode == 'operation-budget' else 8,
                       'packets': {'fixture': {'file': 'jni-fixture.bin',
                           'sha256': 'wrong' if mode == 'packet-hash' else hashlib.sha256(packet).hexdigest()}}}

    def popen(self, argv, **kwargs):
        self.spawns.append({'argv': argv, 'start_new_session': kwargs['start_new_session']})
        self.child = Child(self)
        return self.child

    def stop_group(self, group):
        self.group_stops.append(group)
        if self.mode == 'group-cleanup-unavailable':
            raise RuntimeError('host fake unavailable group cleanup')
        return {'group': group, 'before': [], 'after': [], 'signals': []}

    def execute(self, argv, **kwargs):
        self.commands.append({'argv': argv, 'timeout': kwargs['timeout']})
        code, output = 0, b''
        if argv[0] in ('lsof', '/usr/sbin/lsof'):
            code = 1
            if argv[0] == '/usr/sbin/lsof' and self.mode == 'extraction-cleanup-unavailable':
                code, output = 2, b'host fake unavailable holder check\n'
            elif argv[0] == 'lsof' and ((self.mode == 'occupied-port' and self.child is None)
                    or (self.mode == 'port-remains' and self.child is not None)):
                code, output = 0, b'host fake unrelated port holder\n'
        elif argv[:2] == ['git', 'rev-parse']:
            output = ('host-fixture-' + argv[2] + '\n').encode()
        elif argv[:2] == ['ps', '-axo']:
            port = 5586 if self.mode == 'reserved-process' else 5554
            output = f'999 1 /unrelated/emulator -avd other-project -port {port}\n'.encode()
        elif argv[:2] == ['ps', '-p']:
            assert argv[-1] == 'pid=,pgid=,command='
            args = PROBE.expected_argv()
            args[0] = '/wrong/qemu-system-aarch64-headless' if self.mode == 'identity-drift' else PROBE.HEADLESS
            if self.mode == 'feature-drift':
                args[-1] = 'WiFiPacketStream'
            output = (f'{self.child.pid} {self.child.pid} ' + ' '.join(args) + '\n').encode()
        elif argv[0].endswith('/adb'):
            if argv[1:] == ['version']:
                output = b'host fake adb version\n'
            else:
                assert argv[1:3] == ['-s', RUNNER.SERIAL], 'global/other-target adb prohibited'
                tail = argv[3:]
                if tail[:2] == ['emu', 'kill']:
                    if self.mode not in ('terminate-fallback', 'kill-fallback'):
                        self.child.code = 0
                elif tail[:2] == ['shell', 'getprop']:
                    if self.mode == 'boot-timeout':
                        code, output = 1, b'host fake offline\n'
                    else:
                        value = PROBE.PROPS[tail[2]]
                        if self.mode == 'wrong-target' and tail[2] == 'ro.build.version.sdk':
                            value = '36'
                        output = (value + '\n').encode()
                elif tail[:3] == ['shell', 'wm', 'size'] or tail[:3] == ['shell', 'wm', 'density']:
                    pass
                elif tail[:3] == ['shell', 'settings', 'get']:
                    output = b'1.0\n'
                elif tail[0] == 'install':
                    if self.mode == 'install-failure':
                        code, output = 1, b'host fake install failure\n'
                elif tail[:3] == ['shell', 'pm', 'path']:
                    output = b'package:/data/app/host-fixture/base.apk\n'
                elif tail[:2] == ['shell', 'sha256sum']:
                    digest = 'wrong' if self.mode == 'installed-hash' else self.metadata['apkSHA256']
                    output = (digest + '  /data/app/host-fixture/base.apk\n').encode()
                elif tail[:3] == ['shell', 'am', 'instrument']:
                    code = 1 if self.mode == 'instrument-failure' else 0
                    output = b'INSTRUMENTATION_RESULT: status=passed\nINSTRUMENTATION_CODE: -1\n'
                elif tail[:3] == ['exec-out', 'run-as', RUNNER.PACKAGE]:
                    if tail[-1] == 'files/native-results.json':
                        code = 1 if self.mode == 'no-native-result' else 0
                        output = json.dumps(self.native).encode()
                    elif tail[-1] == 'files/jni-fixture.bin':
                        output = self.packet
                    else:
                        raise AssertionError('unexpected packet')
                else:
                    raise AssertionError('unexpected fake SDK operation ' + repr(argv))
        elif argv[0] == str(RUNNER.SDK / 'build-tools/37.0.0/zipalign'):
            assert argv[1:6] == ['-c', '-P', '16', '-v', '4']
            if self.mode == 'zipalign-failure':
                code, output = 1, b'host fake zipalign failure\n'
        elif argv[0] in (sys.executable, str(RUNNER.SDK / 'emulator/emulator')):
            output = b'host fake tool version\n'
        else:
            raise AssertionError('unrecognized host command ' + repr(argv))
        return SimpleNamespace(returncode=code, stdout=output,
                               groupCleanup={'group': 220000, 'before': [], 'after': [], 'signals': []})


class ContractGuards(unittest.TestCase):
    def test_exact_source_delta_and_unchanged_app_assertions(self):
        contract, _ = ADAPTER.load_contract()
        self.assertEqual(len(contract['sourceDeltas']), 9)
        self.assertTrue(all(change['count'] == 1 for change in contract['sourceDeltas']))
        source = SOURCE
        for _, old, new in reversed(ADAPTER.transformations()):
            self.assertEqual(source.count(new), 1)
            source = source.replace(new, old, 1)
        self.assertEqual(source, ADAPTER.load_module('packaging_test_parent', ADAPTER.PARENT).load_runner()[1])
        def function(text, name):
            return ast.dump(next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name))
        for name in ('remove_owned_extraction', 'validate_members', 'validate_target'):
            self.assertEqual(function(SOURCE, name), function(source, name))
        start = '# Approved disposable instance-only viewport'
        normalized = SOURCE.replace(ADAPTER.transformations()[-1][2], ADAPTER.transformations()[-1][1], 1)
        self.assertEqual(normalized.split(start)[1].split('    except BaseException')[0],
                         source.split(start)[1].split('    except BaseException')[0])
        metadata = RUNNER.bind_candidate(RUNNER.BUILDS / 'candidate-1')
        self.assertEqual(metadata['apkSHA256'], contract['frozenAPK_SHA256'])
        self.assertEqual(len(json.loads((RUNNER.BUILDS / 'candidate-1/built-artifacts.json').read_text())), 177)
        self.assertEqual(len(json.loads((RUNNER.BUILDS / 'candidate-1/source-lock.json').read_text())['files']), 105)

    def test_drift_and_replacement_count_fail_closed(self):
        with patch.object(ADAPTER, 'sha', return_value='drift'):
            with self.assertRaisesRegex(ValueError, 'contract drift'):
                ADAPTER.load_contract()
        source = ADAPTER.BASE.read_text()
        for _, old, _ in ADAPTER.transformations():
            with self.assertRaisesRegex(ValueError, 'exactly one source site'):
                ADAPTER.transform(source.replace(old, '', 1))
            with self.assertRaisesRegex(ValueError, 'exactly one source site'):
                ADAPTER.transform(source + '\n' + old)
        for relative in ADAPTER.BINDINGS:
            real_sha = ADAPTER.sha
            def changed(path):
                return 'drift' if Path(path) == ADAPTER.ROOT / relative else real_sha(path)
            with patch.object(ADAPTER, 'sha', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'bound input drift'):
                    ADAPTER.load_contract()

    def test_exact_installed_executable_pid_group_flags_and_hash(self):
        def identity(args, pid=210000, group=210000):
            return RUNNER.owned_identity(f'{pid} {group} ' + ' '.join(args), 210000)
        for exe in ADAPTER.EXECUTABLES:
            args = PROBE.expected_argv(); args[0] = exe
            self.assertTrue(identity(args))
        args = PROBE.expected_argv()
        for pid, group in ((210001, 210000), (210000, 210001)):
            self.assertFalse(identity(args, pid, group))
        for flag, value in (('-avd', 'other'), ('-port', '55860'), ('-gpu', 'host'), ('-feature', 'WiFiPacketStream')):
            altered = list(args); altered[altered.index(flag) + 1] = value
            self.assertFalse(identity(altered))
        for flag in ('-read-only', '-no-snapshot', '-no-window', '-no-audio', '-no-boot-anim', '-WiFiPacketStream'):
            altered = list(args); altered.remove(flag)
            self.assertFalse(identity(altered))
            self.assertFalse(identity(args + [flag]))
        for executable in ('/wrong/qemu-system-aarch64-headless', '/sdk/emulator', '/bin/echo'):
            altered = list(args); altered[0] = executable
            self.assertFalse(identity(altered))
        with patch.dict(RUNNER._accepted_wifi_sha_globals, sha=lambda _: 'changed-executable'):
            self.assertFalse(identity(args))
        with patch.dict(RUNNER._accepted_wifi_sha_globals, sha=lambda _: (_ for _ in ()).throw(OSError('unavailable'))):
            self.assertFalse(identity(args))
        self.assertFalse(RUNNER.owned_identity('210000 210000 unclosed"', 210000))

    def test_cli_requires_dispatch_bound_build_fresh_attempt(self):
        for suffix in ([], ['--execute-native', '--build', 'candidate-3'],
                       ['--execute-native', '--attempt', '../outside']):
            args = [sys.executable, '-B', str(HERE / 'run.py'), '--build', 'candidate-1',
                    '--attempt', 'runtime-987654'] + suffix
            result = subprocess.run(args, cwd=ADAPTER.ROOT, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((HERE / 'runtime-987654').exists())
        occupied = EVIDENCE / 'existing-output-guard'
        occupied.mkdir(); (occupied / 'runtime-1').mkdir()
        with patch.object(ADAPTER, 'HERE', occupied), patch.object(sys, 'argv',
                ['run.py', '--build', 'candidate-1', '--attempt', 'runtime-1', '--execute-native']), \
                patch.object(ADAPTER, 'load_runner') as load:
            with self.assertRaises(SystemExit):
                ADAPTER.main()
            load.assert_not_called()


class FixtureGuards(unittest.TestCase):
    def test_actual_bad_packaging_fails_before_native_commands_or_launch(self):
        guard = ADAPTER.load_module('packaging_predispatch_bad_guard', HERE / 'apk_packaging.py')
        archive = ADAPTER.ROOT / 'verification/android-coordinator-click-fixture/candidate-1/built-artifacts.tar.gz'
        with tarfile.open(archive, 'r:gz') as stream:
            bad_apk = stream.extractfile('coordinator-join.apk').read()
        out = EVIDENCE / 'actual-bad-APK-before-native'; out.mkdir()
        real_execute = RUNNER.execute
        calls = []
        def host_only(argv, **kwargs):
            self.assertEqual(str(argv[0]), '/usr/sbin/lsof')
            calls.append(list(map(str, argv)))
            return real_execute(argv, **kwargs)
        with patch.object(RUNNER, 'HERE', out), patch.object(RUNNER, 'execute', host_only), \
                patch.object(RUNNER, '_packaging_check_archive', lambda *_: guard.validate(bad_apk)), \
                patch.object(RUNNER, 'subprocess', SimpleNamespace(
                    Popen=lambda *_args, **_kwargs: self.fail('native launch prohibited'),
                    TimeoutExpired=subprocess.TimeoutExpired)), \
                patch.object(sys, 'argv', ['host-actual-bad-APK', '--build', 'candidate-1', '--attempt', 'runtime-1', '--execute-native']):
            with self.assertRaisesRegex(ValueError, 'resources.arsc must be ZIP_STORED'):
                RUNNER.main()
        receipt = json.loads((out / 'runtime-1/receipt.json').read_text())
        self.assertEqual(receipt['commands'], [])
        self.assertEqual(receipt['cleanup'], 'not-started')
        self.assertEqual(receipt['extractionCleanup']['status'], 'removed')
        self.assertEqual(len(calls), 1)
        save(out / 'host-scope.json', {'nativeCommandsExecuted': 0, 'nativeInstancesStarted': 0,
            'actualCompressedResourceAPKRejected': True, 'ownedExtractionRemoved': True})

    def test_actual_derived_artifact_bytes_and_exact_delta(self):
        verifier = ADAPTER.load_module('click_host_candidate_verifier', HERE / 'verify_candidate.py')
        result = verifier.check()
        self.assertEqual(result['status'], 'passed-APK-only-artifact-and-packaging-identity')
        self.assertEqual(result['unchangedCompiledArtifacts'], 176)
        self.assertEqual(result['nativeInstancesStarted'], 0)

    def test_previous_actual_failed_APK_is_rejected_by_packaging_guard(self):
        guard = ADAPTER.load_module('packaging_actual_failed_guard', HERE / 'apk_packaging.py')
        archive = ADAPTER.ROOT / 'verification/android-coordinator-click-fixture/candidate-1/built-artifacts.tar.gz'
        with tarfile.open(archive, 'r:gz') as stream:
            data = stream.extractfile('coordinator-join.apk').read()
        with self.assertRaisesRegex(ValueError, 'resources.arsc must be ZIP_STORED'):
            guard.validate(data)

    def test_every_corrected_build_binding_fails_closed(self):
        contract, _ = ADAPTER.load_contract()
        real_sha = ADAPTER.sha
        for name in contract['buildBindings']:
            target = HERE / 'candidate-1' / name
            with patch.object(ADAPTER, 'sha', side_effect=lambda p, t=target:
                    'drift' if Path(p) == t else real_sha(p)):
                with self.assertRaisesRegex(ValueError, 'APK packaging build binding drift'):
                    ADAPTER.load_contract()

    def test_frozen_source_inputs_and_original_failure_are_bound(self):
        real_sha = RUNNER.sha
        built = HERE / 'candidate-1'
        for name in ('native/android/app/src/dev/mixer/android/NativeCoordinatorV2.java',
                     'verification/android-coordinator-join/CoordinatorJoinInstrumentation.java',
                     'native/android/bridge/jni.c'):
            target = built / 'inputs' / name
            with patch.object(RUNNER, 'sha', side_effect=lambda p, t=target:
                    'drift' if Path(p) == t else real_sha(p)):
                with self.assertRaisesRegex(ValueError, 'input changed'):
                    RUNNER.bind_candidate(built)
        failure = json.loads((ADAPTER.ROOT / 'verification/android-coordinator-wifi-runner/runtime-1/native-results.json').read_text())
        self.assertEqual(failure['status'], 'failed')
        self.assertEqual(failure['checks'], 27)
        self.assertEqual(failure['observations'][-2], {'check': 'actual Switch.performClick', 'passed': False})


class LifecycleGuards(unittest.TestCase):
    def test_packaging_recheck_or_official_zipalign_failure_prevents_install(self):
        for mode in ('packaging-recheck-failure', 'zipalign-failure'):
            harness, receipt, failure = self.exercise(mode)
            self.assertIsNotNone(failure)
            self.assertEqual(receipt['cleanup'], 'stopped')
            self.assertFalse(any(call['argv'][3:4] == ['install'] for call in harness.commands))

    def exercise(self, mode):
        out = EVIDENCE / mode
        out.mkdir()
        built = out / 'fixture-builds/candidate-1'
        built.mkdir(parents=True)
        payload = b'host synthetic extraction only; never a real APK'
        archive = built / 'built-artifacts.tar.gz'
        with tarfile.open(archive, 'w:gz') as stream:
            member = tarfile.TarInfo('coordinator-join.apk'); member.size = len(payload)
            stream.addfile(member, io.BytesIO(payload))
        metadata = {'hostFixtureOnly': True, 'status': 'actual-private-apk-built-runtime-NOT-RUN', 'sourceUnchanged': True,
                    'builtArchiveSHA256': ADAPTER.sha(archive), 'apkSHA256': hashlib.sha256(payload).hexdigest(),
                    'descriptorSHA256': 'host-fixture', 'sourceRevision': 'host-fixture',
                    'sourceClosureSHA256': 'host-fixture', 'debugCertificateSHA256': 'host-fixture', 'packagingPreDispatch': {'hostFixtureOnly': True}}
        save(built / 'receipt.json', metadata)
        save(built / 'source-lock.json', {'hostFixtureOnly': True})
        save(built / 'built-artifacts.json', {'coordinator-join.apk': {'sha256': metadata['apkSHA256']}})
        session = built / 'inputs/verification/android-native-appearance-v2/emulator-session.json'
        session.parent.mkdir(parents=True)
        save(session, {'argv': PROBE.expected_argv()[:-2], 'serial': RUNNER.SERIAL, 'metadataSHA256': {}})
        harness = Harness(mode, metadata)
        failure = None
        with contextlib.ExitStack() as stack:
            for name, value in {'HERE': out, 'BUILDS': out / 'fixture-builds',
                    'bind_candidate': lambda _: metadata, 'execute': harness.execute,
                    '_packaging_check_path': lambda path: (_ for _ in ()).throw(ValueError('host fake packaging rejection'))
                        if mode == 'packaging-recheck-failure' else {'hostFixtureOnly': True},
                    'stop_group': harness.stop_group,
                    'time': SimpleNamespace(monotonic=harness.clock.now, sleep=harness.clock.sleep),
                    'subprocess': SimpleNamespace(Popen=harness.popen, TimeoutExpired=subprocess.TimeoutExpired,
                                                 STDOUT=subprocess.STDOUT),
                    '_ADAPTATION': dict(RUNNER._ADAPTATION)}.items():
                stack.enter_context(patch.object(RUNNER, name, value))
            stack.enter_context(patch.object(sys, 'argv', ['host-fixture', '--build', 'candidate-1', '--attempt', 'runtime-1', '--execute-native']))
            try:
                RUNNER.main()
            except BaseException as error:
                failure = repr(error)
        attempt = out / 'runtime-1'
        receipt = json.loads((attempt / 'receipt.json').read_text())
        seal = json.loads((attempt / 'artifact-seal.json').read_text())
        for relative, binding in seal.items():
            self.assertNotIn('.build', Path(relative).parts)
            self.assertEqual(ADAPTER.sha(attempt / relative), binding['sha256'])
        self.assertEqual(receipt['adaptation']['apkPackagingFixture']['transformedRunnerSHA256'], hashlib.sha256(SOURCE.encode()).hexdigest())
        self.assertEqual(receipt['adaptation']['runnerSourceRevision'], 'host-fixture-HEAD')
        self.assertEqual(receipt['adaptation']['runnerSourceTree'], 'host-fixture-HEAD^{tree}')
        self.assertLessEqual(len(harness.spawns), 1)
        if harness.spawns:
            self.assertEqual(harness.spawns[0]['argv'], PROBE.expected_argv())
            self.assertTrue(harness.spawns[0]['start_new_session'])
        self.assertFalse(any('devices' in call['argv'] for call in harness.commands))
        if (attempt / '.build').exists():
            ownership = (attempt / '.build').stat()
            cleanup = RUNNER.remove_owned_extraction(attempt / '.build', attempt,
                {'coordinator-join.apk': {}}, (ownership.st_dev, ownership.st_ino))
            save(out / 'recovered-extraction-cleanup.json', cleanup)
        self.assertFalse((attempt / '.build').exists())
        scope = {'mode': mode, 'hostFixtureOnly': True, 'actualTransformedMainExecuted': True,
                 'nativeCommandsExecuted': 0, 'nativeInstancesStarted': 0, 'physicalTargetsQueried': False,
                 'appAcceptance': 'NOT QUALIFIED: all SDK operations and child objects are injected fakes',
                 'failure': failure, 'fakeCommands': harness.commands, 'fakeSpawns': harness.spawns,
                 'fakeGroupStops': harness.group_stops, 'fakeChildActions': harness.child.actions if harness.child else [],
                 'allOwnedHostExtractionsAbsent': True}
        save(out / 'host-fixture-scope.json', scope)
        CASES.append(scope)
        return harness, receipt, failure

    def test_success_all_original_operations_and_cleanup(self):
        h, r, failure = self.exercise('success')
        self.assertIsNone(failure)
        self.assertEqual(r['status'], 'actual-API37-private-ordinary-join-bounded-subset-passed')
        self.assertEqual(r['native']['operations'], 8)
        self.assertEqual(r['cleanup'], 'stopped')
        self.assertEqual(h.group_stops, [h.child.pid])
        self.assertEqual(r['extractionCleanup']['status'], 'removed')

    def test_reservation_guards_never_spawn_or_stop(self):
        for mode in ('occupied-port', 'reserved-process'):
            h, r, failure = self.exercise(mode)
            self.assertIsNotNone(failure); self.assertEqual(h.spawns, []); self.assertEqual(h.group_stops, [])
            self.assertEqual(r['cleanup'], 'not-started')

    def test_boot_failure_and_deadline_clean_up(self):
        for mode in ('early-exit', 'boot-timeout'):
            h, r, failure = self.exercise(mode)
            self.assertIsNotNone(failure); self.assertEqual(r['cleanup'], 'stopped')
            self.assertEqual(h.group_stops, [h.child.pid])
            if mode == 'boot-timeout':
                self.assertEqual(h.clock.value, 180)

    def test_original_target_install_and_assertions_fail_closed(self):
        for mode in ('wrong-target', 'install-failure', 'installed-hash', 'instrument-failure',
                     'no-native-result', 'operation-budget', 'packet-hash'):
            _, r, failure = self.exercise(mode)
            self.assertIsNotNone(failure)
            self.assertEqual(r['status'], 'failed-native-attempt-retained')
            self.assertEqual(r['cleanup'], 'stopped')

    def test_identity_drift_never_authorizes_stop(self):
        for mode in ('identity-drift', 'feature-drift'):
            h, r, failure = self.exercise(mode)
            self.assertIsNotNone(failure); self.assertEqual(r['cleanup'], 'failed')
            self.assertEqual(h.child.actions, []); self.assertEqual(h.group_stops, [])
            self.assertFalse(any(call['argv'][-2:] == ['emu', 'kill'] for call in h.commands))

    def test_exact_owned_termination_fallbacks(self):
        for mode, actions in (('terminate-fallback', ['terminate']), ('kill-fallback', ['terminate', 'kill'])):
            h, r, failure = self.exercise(mode)
            self.assertIsNone(failure); self.assertEqual(h.child.actions, actions)
            self.assertEqual(r['cleanup'], 'stopped')

    def test_cleanup_failure_never_passes_and_extraction_is_recovered(self):
        for mode in ('group-cleanup-unavailable', 'port-remains', 'extraction-cleanup-unavailable'):
            _, r, failure = self.exercise(mode)
            self.assertIsNotNone(failure)
            self.assertIn(r['status'], ('failed-owned-cleanup', 'failed-owned-extraction-cleanup'))


def minimal_elf(align=16384):
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, 3, 183, 1, 0, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    return header + struct.pack('<IIQQQQQQ', 1, 5, 0, 0, 0, 120, 120, align)


def minimal_zip(entries):
    target = io.BytesIO()
    with warnings.catch_warnings(), zipfile.ZipFile(target, 'w') as archive:
        warnings.simplefilter('ignore', UserWarning)
        for name, data, method, alignment in entries:
            info = zipfile.ZipInfo(name); info.compress_type = method
            if alignment > 1:
                base = archive.fp.tell() + 30 + len(name.encode('utf-8'))
                padding = (-(base + 4)) % alignment
                info.extra = struct.pack('<HH', 0xFFFF, padding) + bytes(padding)
            archive.writestr(info, data)
    return target.getvalue()


class PackagingGuards(unittest.TestCase):
    def inspect(self, label, data, failure=None):
        guard = ADAPTER.load_module('packaging_negative_fixture_guard', HERE / 'apk_packaging.py')
        fixtures = EVIDENCE / 'minimal-packaging-fixtures'; fixtures.mkdir(exist_ok=True)
        (fixtures / (label + '.zip')).write_bytes(data)
        if failure:
            with self.assertRaisesRegex(ValueError, failure) as rejected:
                guard.validate(data)
            result = {'name': label, 'expectedRejected': True, 'failure': str(rejected.exception)}
        else:
            checked = guard.validate(data)
            result = {'name': label, 'expectedRejected': False, 'status': checked['status']}
        PACKAGING_CASES.append(result)

    def test_aligned_stored_resource_and_native_ELF_pass(self):
        self.inspect('aligned-stored-resource-and-native', minimal_zip([
            ('resources.arsc', b'resource table fixture', 0, 4),
            ('lib/arm64-v8a/libfixture.so', minimal_elf(), 0, 16384)]))

    def test_compressed_or_misaligned_resources_fail(self):
        self.inspect('compressed-resource-aligned', minimal_zip([('resources.arsc', b'r', 8, 4)]), 'resources.arsc must be ZIP_STORED')
        self.inspect('stored-resource-misaligned', minimal_zip([
            ('p', b'a', 8, 1), ('resources.arsc', b'r', 0, 1)]), 'resources.arsc must be ZIP_STORED')

    def test_compressed_or_misaligned_native_libraries_fail(self):
        self.inspect('compressed-native', minimal_zip([('resources.arsc', b'r', 0, 4),
            ('lib/arm64-v8a/libfixture.so', minimal_elf(), 8, 16384)]), 'native ZIP entry must be stored')
        self.inspect('native-4k-local-data', minimal_zip([('resources.arsc', b'r', 0, 4),
            ('lib/arm64-v8a/libfixture.so', minimal_elf(), 0, 4096)]), '16KiB local data alignment')

    def test_native_ELF_small_alignment_or_invalid_identity_fails(self):
        self.inspect('native-ELF-4k-load', minimal_zip([('resources.arsc', b'r', 0, 4),
            ('lib/arm64-v8a/libfixture.so', minimal_elf(4096), 0, 16384)]), '16KiB-compatible alignment')
        self.inspect('native-ELF-wrong-identity', minimal_zip([('resources.arsc', b'r', 0, 4),
            ('lib/arm64-v8a/libfixture.so', b'not an ELF', 0, 16384)]), 'unsupported AArch64 ELF identity')

    def test_local_header_method_or_name_mismatch_fails(self):
        data = bytearray(minimal_zip([('resources.arsc', b'r', 0, 4)]))
        method = bytearray(data); struct.pack_into('<H', method, 8, 8)
        self.inspect('local-method-central-mismatch', bytes(method), 'local/central ZIP metadata mismatch')
        name = bytearray(data); name[30] = ord('R')
        self.inspect('local-name-central-mismatch', bytes(name), 'local/central ZIP metadata mismatch')

    def test_duplicate_or_missing_resource_entries_fail(self):
        self.inspect('duplicate-resources', minimal_zip([('resources.arsc', b'r', 0, 4),
            ('resources.arsc', b'r', 0, 4)]), 'duplicate or empty ZIP membership')
        self.inspect('missing-resource', minimal_zip([('classes.dex', b'd', 8, 1)]), 'exact resources.arsc entry required')


def accepted_guard_suite():
    # Reuse unchanged accepted guards; replace only their runner object/evidence root.
    # Original exact-source and basename assertions are superseded by ContractGuards.
    sys.path.insert(0, str(ADAPTER.BASE.parent))
    cleanup_path = ADAPTER.BASE.with_name('test_cleanup.py')
    cleanup_source = cleanup_path.read_text()
    if cleanup_source.count('candidate-2') != 4:
        raise ValueError('accepted cleanup guard fixture-label sites drifted')
    # Four build fixture labels and one synthetic metadata field adapt; guard expectations remain inherited.
    metadata_site = "'debugCertificateSHA256': 'controlled-host-fixture'"
    if cleanup_source.count(metadata_site) != 1:
        raise ValueError('accepted synthetic metadata site drifted')
    cleanup_source = cleanup_source.replace(metadata_site, metadata_site + ", 'packagingPreDispatch': {'hostFixtureOnly': True}", 1)
    old = ModuleType('accepted_cleanup_guards_for_corrected_fixture')
    old.__file__ = str(cleanup_path)
    exec(compile(cleanup_source.replace('candidate-2', 'candidate-1'), str(cleanup_path), 'exec'), old.__dict__)
    old.runner = RUNNER
    old.EVIDENCE = EVIDENCE / 'accepted-cleanup-guards'; old.EVIDENCE.mkdir()
    guards = ADAPTER.load_module('accepted_runner_guards', ADAPTER.BASE.with_name('test_runner_guards.py'))
    guards.runner = RUNNER
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(old.ExtractionGuards))
    for name in ('test_main_failure_after_extraction_cleans_and_retains_receipt',
                 'test_main_cleanup_failure_retains_then_recovers_extraction'):
        suite.addTest(old.MainGuards(name))
    for name in ('test_timed_out_owned_command_and_its_child_are_stopped',
                 'test_archive_refuses_traversal_links_duplicates_and_unsealed_members',
                 'test_runtime_contract_is_exact_and_rejects_physical_or_unqualified_api'):
        suite.addTest(guards.RunnerGuards(name))
    return suite, old


if __name__ == '__main__':
    if len(sys.argv) != 2 or not sys.argv[1].startswith('host-tests-') or not sys.argv[1][11:].isdigit():
        raise SystemExit('usage: python3 -B test_runner.py host-tests-N (fresh output)')
    EVIDENCE = HERE / sys.argv.pop(); EVIDENCE.mkdir()
    suite, old = accepted_guard_suite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ContractGuards))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(FixtureGuards))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(PackagingGuards))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(LifecycleGuards))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    remaining = [str(path.relative_to(EVIDENCE)) for path in EVIDENCE.rglob('.build')]
    save(EVIDENCE / 'fixture-cleanup-ledger.json', {'acceptedExtractionCases': old.RESULTS,
         'actualTransformedMainFixtureCases': CASES, 'remainingOwnedExtractions': remaining,
         'scope': 'host files/processes only; SDK/native child operations injected'})
    save(EVIDENCE / 'packaging-guard-cases.json', PACKAGING_CASES)
    save(EVIDENCE / 'receipt.json', {'schema': 1, 'status': 'passed' if result.wasSuccessful() and not remaining else 'failed',
         'testsRun': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
         'acceptedGuardsReused': 21, 'acceptedCleanupFixtureBuildLabelsAdapted': 4,
         'contractGuardTests': 4, 'fixtureGuardTests': 5, 'lifecycleGuardTests': 8, 'packagingGuardTests': 6,
         'nativeCommandsExecuted': 0, 'nativeInstancesStarted': 0, 'physicalTargetsQueried': False,
         'nativeRuntime': 'NOT RUN; host fixtures never qualify app acceptance'})
    raise SystemExit(0 if result.wasSuccessful() and not remaining else 1)
