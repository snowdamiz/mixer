#!/usr/bin/env python3
"""Finite original host controls. Every native command/runner is replaced before invocation."""
import contextlib
import copy
import datetime
from decimal import Decimal, localcontext, Inexact
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
import uuid
from unittest import mock

import prepare as p

ATTEMPT = SCRATCH = PAYLOAD = None
SELECTORS = []
DISPATCH = []
DENIED = []
CLEANUP_PROBES = []
RECEIVER_PROBES = []


def audit(event, args):
    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'pty.spawn'}:
        raise AssertionError('Host-only control forbids ' + event)
    if event in {'open', 'os.scandir', 'os.listdir'} and args and isinstance(args[0], (str, bytes)):
        candidate = Path(os.fsdecode(args[0]))
        if event == 'open' and not candidate.is_absolute():
            caller = sys._getframe(1)
            if caller.f_code is shutil._rmtree_safe_fd_step.__code__:
                candidate = Path(caller.f_locals['path'])
        path = candidate.resolve()
        if any(word in str(path).lower() for word in ('catalog-inspector', 'authority-driver', 'worker-transport')):
            raise AssertionError('Excluded lane refused')
        allowed = set(REFERENCE_PATHS)
        writing = event == 'open' and ((isinstance(args[1], str) and any(c in args[1] for c in 'wa+'))
                                       or len(args) > 2 and isinstance(args[2], int)
                                       and bool(args[2] & (os.O_WRONLY | os.O_RDWR)))
        if writing and not path.is_relative_to(p.BASE):
            raise PermissionError('Host controls cannot mutate accepted inputs')
        if not (path.is_relative_to(p.BASE) or path.is_relative_to(Path(sys.base_prefix).resolve())
                or path in allowed or str(path) == '/dev/null'):
            DENIED.append({'event': event, 'path': str(path)})
            raise PermissionError('Closed packet host read boundary')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def root_fixture():
    return {'schema': 'mixer.apple-focus-reference-root-selection.8',
            'runID': '11111111-1111-4111-8111-111111111111', 'packetSHA256': p.sha((p.BASE / 'packet.json').read_bytes()),
            'selectedAtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'ownedSimulatorIdentity': {'udid': '22222222-2222-4222-8222-222222222222',
                'name': 'MixerFocusReferenceV8-host-synthetic',
                'runtime': 'com.apple.CoreSimulator.SimRuntime.iOS-26-5', 'build': '23F77'},
            'sourceTreeSHA256': p.SOURCE, 'productArchiveSHA256': p.PRODUCT,
            'developerDirectory': '/Applications/Xcode_26.6.app/Contents/Developer',
            'baselineDevices': {'devices': {}}, 'baselineFrontends': []}


@contextlib.contextmanager
def namespace(output=None, composition=False):
    parent = Path(tempfile.mkdtemp(prefix='module-', dir=SCRATCH))
    root = root_fixture()
    output = output or parent / ('native-run-v8-' + root['runID'])
    output.mkdir()
    selected = output / 'selected'
    p.materialize(selected, p.manifest(PAYLOAD), PAYLOAD)
    saved_path = list(sys.path)
    aliases = set(p.selection_template(PAYLOAD)['moduleAliases']) | {'composition'}
    try:
        with mock.patch.dict(sys.modules):
            for name in aliases:
                sys.modules.pop(name, None)
            sys.path.insert(0, str(selected))
            if composition:
                products = json.loads((p.BUILD_ATTEMPT / 'product-manifest.json').read_bytes())
                product_payload = p.archive_payload(p.BUILD_ATTEMPT / 'products.tar.gz', products['products'], p.PRODUCT, explicit_directories=False)
                p.materialize(output / 'products', products['products'], product_payload)
                selection = p.selection_template(PAYLOAD)
                selection.update(repositoryRoot=str(p.ROOT), outputBase=str(output), productsRoot=str(output / 'products'),
                                 trustedRootSelection=root)
                (selected / 'runtime-selection.json').write_bytes(p.stable(selection))
                yield load('composition', selected / 'composition.py'), root, output
            else:
                importer = load('importer', selected / 'importer.py')
                load('reference_contract', selected / 'reference_contract.py')
                load('settings_telemetry', selected / 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py')
                load('auxiliary_inventory', selected / 'auxiliary_inventory.py')
                yield load('join_support', selected / 'join_support.py'), root, output
    finally:
        sys.path[:] = saved_path
        shutil.rmtree(parent)


def safe_sample():
    return {'schema': 1, 'kind': 'chunk', 'start': False,
            'generation': '33333333-3333-4333-8333-333333333333', 'sequence': 17,
            'stage': None, 'slot': 'settings-0017-ax', 'chunkIndex': 2, 'chunkCount': 3,
            'requestOrdinal': 18, 'taskIdentifier': 18, 'beginUptime': 100.0, 'endUptime': 100.012,
            'absoluteDeadlineUptime': 100.012, 'actualAllowanceSeconds': 0.012,
            'overallDeadlineClipped': True, 'branch': 'semaphore-expiration', 'status': None, 'errorCode': None}


def observer_fixture(importer, root, session, streams, code=65):
    return {'schema': 'mixer.apple-command-finalization-observer.2',
            'argv': importer.command_argv(root, session), 'resultBundle': str(session / 'session.xcresult'),
            'exitCode': code, 'startNewSession': True, 'successInferredFromConsoleOrMarkers': False,
            'PID': 10101, 'processGroup': 10101,
            'ownedProcessGroup': {'state': 'absent', 'targetProcessGroup': 10101},
            'cleanup': {'attempted': False, 'complete': None, 'signals': []},
            'streams': {name: {'eof': True, 'readerFailed': False, 'readerErrors': [],
                               'observedBytes': len(raw), 'retainedBytes': len(raw), 'retainedSHA256': p.sha(raw)}
                        for name, raw in streams.items()}}


def observe_files(adapter, root, output, streams):
    session = output / 'runtime/session'; session.mkdir(parents=True, mode=0o700)
    folder = session / 'command-observer'; folder.mkdir()
    observer = observer_fixture(adapter.importer, root, session, streams)
    (folder / 'observer.json').write_bytes(p.stable(observer))
    for name, raw in streams.items():
        (folder / (name + '.log')).write_bytes(raw)
    return session, observer


class RuntimeControls(unittest.TestCase):
    def test_01_exact_semantic_boundary_and_fresh_bindings(self):
        original = p.prior_payload()
        self.assertEqual(len(PAYLOAD), 32)
        self.assertEqual(sorted(name for name in PAYLOAD if PAYLOAD[name] != original.get(name)),
                         sorted(p.literal_delta()))
        restored = PAYLOAD['importer.py']
        for before, after in [(p.SOURCE, p.OLD_SOURCE), (p.PRODUCT, p.OLD_PRODUCT),
                              ('mixer.apple-focus-reference-root-selection.8', 'mixer.apple-focus-reference-root-selection.7'),
                              ('MixerFocusReferenceV8-', 'MixerFocusReferenceV7-'),
                              ('mixer.apple-focus-reference-runtime-import.8', 'mixer.apple-focus-reference-runtime-import.7')]:
            restored = p.replace_once(restored, before.encode(), after.encode())
        self.assertEqual(restored, original['importer.py'])
        self.assertEqual(PAYLOAD['local_first_failure.py'].replace(b'native-run-v8-', b'native-run-v7-'), original['local_first_failure.py'])
        self.assertEqual(PAYLOAD['join_support.py'].replace(b'native-run-v8-', b'native-run-v7-').replace(b'mixer.apple-focus-reference-runtime.8', b'mixer.apple-focus-reference-runtime.7'), original['join_support.py'])
        self.assertEqual(PAYLOAD['runtime_bindings.py'], original['runtime_bindings.py'])
        self.assertEqual(PAYLOAD['orchestration.py'], original['orchestration.py'])
        self.assertEqual(PAYLOAD['command_observer.py'], original['command_observer.py'])
        for name, raw in PAYLOAD.items():
            if name.endswith('.py'):
                compile(raw, str(p.BASE / name), 'exec')
        self.assertEqual(p.verify()['packetSHA256'], p.sha((p.BASE / 'packet.json').read_bytes()))

    def test_02_actual_composition_exact_products_and_origin_guard(self):
        with namespace(composition=True) as (module, root, output):
            verified = module.h.verify()
            self.assertFalse(verified['nativeAcceptanceGranted'])
            self.assertEqual(module.importer.SOURCE, p.SOURCE)
            self.assertEqual(module.importer.PRODUCT, p.PRODUCT)
            self.assertIn(module.local_first_failure, module.RUNTIME_ROOTS)
            self.assertIn(module.telemetry, module.RUNTIME_ROOTS)
            self.assertEqual(module.telemetry.CHUNK, 4992)
            self.assertEqual(Path(module.telemetry.__file__), output / 'selected' / p.RECEIVER)
            self.assertEqual(Path(module.telemetry.__file__).read_bytes(), p.prior_payload()[p.RECEIVER])
            self.assertEqual(module.METHODS, ['test000PublicSettingsFullKeyboardAccess', 'test010ReferenceFirstTab'])
            self.assertEqual(module.selection['cases'], ['keyboard-enabled-off'])
            module.bindings.check(module.RUNTIME_ROOTS)
            selected = output / 'selected/local_first_failure.py'
            original = selected.read_bytes(); selected.write_bytes(original + b'\n# altered\n')
            with self.assertRaises(ValueError):
                module.bindings.check(module.RUNTIME_ROOTS)
            selected.write_bytes(original)
            module.bindings.check(module.RUNTIME_ROOTS)

    def test_03_false_module_origin_rejects(self):
        with namespace(composition=True) as (module, _, _):
            real = module.local_first_failure
            fake = types.ModuleType('local_first_failure')
            fake.__file__ = real.__file__; fake.__spec__ = real.__spec__
            exec(compile('def injected(): return None\n', '/unselected/injected.py', 'exec'), vars(fake))
            with self.assertRaises(ValueError):
                module.bindings.module(fake)

    def test_04_actual_configured_adapter_selector_prefixes_and_exact_argv(self):
        for version in [8, 7, 6, 9]:
            for wrong_argv in [False, True]:
                with self.subTest(version=version, wrong_argv=wrong_argv), namespace() as (adapter, root, output):
                    adapter.configure_root(root)
                    other = output.parent / ('native-run-v' + str(version) + '-' + root['runID'])
                    if other != output:
                        other.mkdir()
                    session = other / 'runtime/session'; session.mkdir(parents=True, mode=0o700)
                    calls = []
                    def recorder(h, argv, path):
                        calls.append(list(argv)); adapter._selected = {'session': path, 'argv': list(argv)}
                    adapter._ORIGINAL_SELECT = recorder
                    argv = adapter.importer.command_argv(root, session)
                    if wrong_argv:
                        argv += ['-unselected']
                    accepted = version == 8 and not wrong_argv
                    if accepted:
                        adapter.select_command(object(), argv, session)
                    else:
                        with self.assertRaises(ValueError):
                            adapter.select_command(object(), argv, session)
                    self.assertEqual(len(calls), int(accepted))
                    SELECTORS.append({'namespace': version, 'wrongArgv': wrong_argv,
                                      'accepted': accepted, 'originalRecorderCalls': len(calls)})

    def test_05_unconfigured_existing_result_and_redirected_path_reject(self):
        for mode in ['unconfigured', 'existing-result', 'symlink']:
            with self.subTest(mode=mode), namespace() as (adapter, root, output):
                if mode != 'unconfigured':
                    adapter.configure_root(root)
                session = output / 'runtime/session'; session.mkdir(parents=True, mode=0o700)
                if mode == 'existing-result':
                    (session / 'session.xcresult').mkdir()
                if mode == 'symlink':
                    alias = session.parent / 'alias'; alias.symlink_to(session, target_is_directory=True); session = alias
                calls = []
                adapter._ORIGINAL_SELECT = lambda *args: calls.append(args)
                with self.assertRaises(ValueError):
                    adapter.select_command(object(), adapter.importer.command_argv(root, session), session)
                self.assertEqual(calls, [])

    def test_06_old_identity_schema_and_stale_selection_reject(self):
        for field in ['schema', 'name', 'source', 'product', 'stale']:
            with self.subTest(field=field), namespace() as (adapter, root, _):
                if field == 'schema': root['schema'] = 'mixer.apple-focus-reference-root-selection.7'
                if field == 'name': root['ownedSimulatorIdentity']['name'] = 'MixerFocusReferenceV7-rejected'
                if field == 'source': root['sourceTreeSHA256'] = p.OLD_SOURCE
                if field == 'product': root['productArchiveSHA256'] = p.OLD_PRODUCT
                if field == 'stale': root['selectedAtUTC'] = '2026-10-24T01:00:00+00:00'
                with self.assertRaises(ValueError):
                    adapter.importer.validate_root(root, fresh=True)

    def test_07_actual_dispatch_routes_exact_products_once_with_no_native_runner(self):
        root = root_fixture(); root['runID'] = str(uuid.uuid4())
        selection_path = SCRATCH / 'root-selection.json'; selection_path.write_bytes(p.stable(root))
        output = p.BASE / ('native-run-v8-' + root['runID'])
        self.assertFalse(output.exists())
        real_spec = importlib.util.spec_from_file_location
        saved_path = list(sys.path)
        calls = []
        def intercepted(name, path, *args, **kwargs):
            spec = real_spec(name, path, *args, **kwargs)
            if name != 'composition':
                return spec
            original_loader = spec.loader
            class Loader:
                def create_module(self, selected): return original_loader.create_module(selected)
                def exec_module(self, module):
                    original_loader.exec_module(module)
                    self_outer.assertFalse(module.h.verify()['nativeAcceptanceGranted'])
                    def no_native(seal):
                        self_outer.assertEqual(seal, p.sha((output / 'selected/runtime-selection.json').read_bytes()))
                        session = output / 'runtime/session'; session.mkdir(parents=True, mode=0o700)
                        def recorder(h, argv, path):
                            calls.append({'argv': list(argv), 'session': str(path)})
                            module.join_support._selected = {'session': path, 'argv': list(argv)}
                        module.join_support._ORIGINAL_SELECT = recorder
                        module.join_support.select_command(module.h, module.importer.command_argv(root, session), session)
                        return {'syntheticOnly': True, 'nativeExecuted': False}
                    module.h.run = no_native
            spec.loader = Loader()
            return spec
        self_outer = self
        aliases = set(p.selection_template(PAYLOAD)['moduleAliases']) | {'composition'}
        try:
            with mock.patch.dict(sys.modules), mock.patch.object(importlib.util, 'spec_from_file_location', intercepted):
                for alias in aliases: sys.modules.pop(alias, None)
                result = p.dispatch(root['packetSHA256'], selection_path, p.sha(selection_path.read_bytes()))
                self.assertTrue(result['syntheticOnly']); self.assertEqual(len(calls), 1)
                cleanup = json.loads((output / 'scratch-cleanup.json').read_bytes())
                self.assertTrue(cleanup['verifiedBeforeRemoval']); self.assertTrue(cleanup['scratchAbsent'])
                with self.assertRaises(ValueError):
                    p.dispatch(root['packetSHA256'], selection_path, p.sha(selection_path.read_bytes()))
                output.rename(ATTEMPT / 'synthetic-dispatch-output')
                with self.assertRaises(FileExistsError):
                    p.dispatch(root['packetSHA256'], selection_path, p.sha(selection_path.read_bytes()))
                selection_path.write_bytes(selection_path.read_bytes() + b'\n')
                with self.assertRaises(ValueError):
                    p.dispatch(root['packetSHA256'], selection_path, p.sha(p.stable(root)))
        finally:
            sys.path[:] = saved_path
        DISPATCH.extend(calls)
        self.assertFalse(output.exists())

    def test_08_marker_extracts_safe_record_without_console_prefix(self):
        with namespace() as (adapter, _, _):
            diagnostic = adapter.local_first_failure
            record = safe_sample()
            streams = {'stdout': b'console URL=http://redacted.invalid secret-header\n2026 console ' + diagnostic.PREFIX
                       + json.dumps(record).encode() + b'\n', 'stderr': b''}
            result = diagnostic.extract(streams)
            self.assertEqual(result, {'stream': 'stdout', 'record': record})
            rendered = p.stable(result)
            self.assertNotIn(b'redacted.invalid', rendered); self.assertNotIn(b'secret-header', rendered)
            self.assertIsNone(diagnostic.extract({'stdout': b'no marker\n', 'stderr': b''}))

    def test_09_unknown_secrets_malformed_identity_duplicates_and_size_reject(self):
        mutations = [dict(url='https://should-never-appear.invalid'), dict(headers={'secret': 'never-copy'}),
                     dict(payload='never-copy'), dict(capability='never-copy'), dict(stage='URL-never-copy'),
                     dict(slot='settings-0000-ax'), dict(generation='not-a-uuid'), dict(requestOrdinal=True),
                     dict(actualAllowanceSeconds=3), dict(overallDeadlineClipped=False), dict(sequence=0),
                     dict(chunkCount=653), dict(beginUptime=float('inf'))]
        with namespace() as (adapter, _, _):
            diagnostic = adapter.local_first_failure
            for mutation in mutations:
                with self.subTest(fields=sorted(mutation)):
                    record = safe_sample(); record.update(mutation)
                    with self.assertRaises((ValueError, TypeError)):
                        diagnostic.extract({'stdout': diagnostic.PREFIX + json.dumps(record).encode(), 'stderr': b''})
            raw = diagnostic.PREFIX + json.dumps(safe_sample()).encode() + b'\n'
            for streams in [{'stdout': raw + raw, 'stderr': b''}, {'stdout': raw, 'stderr': raw},
                            {'stdout': diagnostic.PREFIX + b'{' + b' ' * 2049 + b'}', 'stderr': b''},
                            {'stdout': diagnostic.PREFIX + b'{"schema":1,"schema":1}', 'stderr': b''}]:
                with self.assertRaises(ValueError): diagnostic.extract(streams)

    def test_10_actual_selected_stream_binding_captures_failed_native_command(self):
        with namespace() as (adapter, root, output):
            diagnostic = adapter.local_first_failure
            streams = {'stdout': diagnostic.PREFIX + json.dumps(safe_sample()).encode() + b'\n', 'stderr': b''}
            session, observer = observe_files(adapter, root, output, streams)
            report = diagnostic.capture(session, root)
            self.assertEqual(report['status'], 'captured-safe-local-record')
            self.assertEqual(report['observedXCTestExitCode'], 65)
            self.assertFalse(report['nativeImporterAcceptanceGranted'])
            self.assertFalse(report['settingsPreconditionPassed']); self.assertFalse(report['runPassed'])
            target = session / 'local-settings-first-failure.json'; first = target.read_bytes()
            (session / 'command-observer/stdout.log').write_bytes(b'changed\n')
            self.assertEqual(diagnostic.capture(session, root)['status'], 'unavailable-or-invalid')
            self.assertEqual(target.read_bytes(), first)
            # A supplemental record never supplies an official captured result.
            imported = adapter.importer.import_selected(root, session, observer, streams, {}, {}, {}, [], None, None)
            self.assertFalse(imported['provenanceAccepted']); self.assertFalse(imported['runPassed'])

    def test_11_incomplete_eof_wrong_command_group_and_redirected_log_reject(self):
        for mode in ['eof', 'command', 'group', 'hash', 'symlink']:
            with self.subTest(mode=mode), namespace() as (adapter, root, output):
                diagnostic = adapter.local_first_failure
                streams = {'stdout': diagnostic.PREFIX + json.dumps(safe_sample()).encode() + b'\n', 'stderr': b''}
                session, observer = observe_files(adapter, root, output, streams)
                if mode == 'eof': observer['streams']['stdout']['eof'] = False
                if mode == 'command': observer['argv'] += ['-unselected']
                if mode == 'group': observer['ownedProcessGroup']['state'] = 'present'
                if mode == 'hash': observer['streams']['stdout']['retainedSHA256'] = '0' * 64
                (session / 'command-observer/observer.json').write_bytes(p.stable(observer))
                if mode == 'symlink':
                    path = session / 'command-observer/stdout.log'; other = session / 'saved.log'; path.rename(other); path.symlink_to(other)
                report = diagnostic.capture(session, root)
                self.assertEqual(report['status'], 'unavailable-or-invalid')
                self.assertIsNone(report['diagnostic'])

    def test_12_diagnostic_wrapper_runs_on_native_exception_without_replacing_it(self):
        with namespace() as (adapter, root, output):
            adapter.configure_root(root)
            session = output / 'runtime/session'; session.mkdir(parents=True, mode=0o700)
            adapter._selected = {'session': session}
            error = RuntimeError('synthetic original native failure')
            calls = []
            def fail(*args): raise error
            adapter._ORIGINAL_RUN_OBSERVED = fail
            with mock.patch.object(adapter.local_first_failure, 'capture', lambda *args: calls.append(args)):
                with self.assertRaises(RuntimeError) as caught:
                    adapter.run_observed(None, [], 600, False, None)
            self.assertIs(caught.exception, error); self.assertEqual(len(calls), 1)

    def test_13_decimal_and_exact_timestamp_semantics_stay_original(self):
        with namespace() as (adapter, _, _):
            importer = adapter.importer
            with localcontext() as context:
                context.prec = 1; context.traps[Inexact] = True
                self.assertEqual(importer.decimal_timestamp_ns(Decimal('1234567890.123456789')), 1234567890123456789)
                self.assertEqual(importer.decimal_timestamp_ns(Decimal('0e999999999')), 0)
                with self.assertRaises(ValueError): importer.decimal_timestamp_ns(Decimal('1.0000000001'))
            self.assertEqual(importer.datetime_ns('2026-10-25T00:00:00+00:00'), 1792886400000000000)

    def test_14_host_boundary_forbids_live_reads_processes_and_sockets(self):
        with self.assertRaises(PermissionError): (p.ROOT / 'AGENTS.md').read_bytes()
        with self.assertRaises(AssertionError): sys.audit('subprocess.Popen', 'forbidden', [], None, None)
        with self.assertRaises(AssertionError): sys.audit('socket.bind', None, ('127.0.0.1', 0))
        self.assertTrue(DENIED)


    def test_15_actual_composed_reviewed_receiver_exact_start_agreement(self):
        with namespace(composition=True) as (module, _, _):
            receiver = module.telemetry
            self.assertEqual(receiver.CHUNK, 4992)
            for value in [None, True, 4992.0, '4992', 0, 3072, 6144, 4993]:
                records = []
                session = receiver.Session(lambda *args: records.append(args), lambda *args: records.append(args),
                                           100.0, now=lambda: 1.0, token='33333333-3333-4333-8333-333333333333')
                body = {'kind': 'start', 'case': receiver.CASE, 'uptime': 10.0}
                if value is not None: body['chunkBytes'] = value
                with self.subTest(value=value), self.assertRaises(ValueError): session.request(body)
                self.assertIsNone(session.start_host); self.assertEqual(session.requests, 0)
                self.assertEqual(session.sequence, 0); self.assertEqual(records, [])
                RECEIVER_PROBES.append({'suppliedChunkBytes': value, 'accepted': False, 'cursorAdvanced': False})
            records = []
            session = receiver.Session(lambda *args: records.append(args), lambda *args: records.append(args),
                                       100.0, now=lambda: 1.0, token='33333333-3333-4333-8333-333333333333')
            body = {'kind': 'start', 'case': receiver.CASE, 'uptime': 10.0, 'chunkBytes': 4992}
            result = session.request(body)
            self.assertEqual(result['chunkBytes'], 4992); self.assertIs(type(result['chunkBytes']), int)
            self.assertEqual(session.requests, 1); self.assertEqual(session.sequence, 0)
            first = copy.deepcopy(records)
            with self.assertRaises(ValueError): session.request(body)
            self.assertEqual(records, first); self.assertEqual(session.requests, 1)
            RECEIVER_PROBES.append({'suppliedChunkBytes': 4992, 'accepted': True, 'echo': result['chunkBytes'],
                                    'journalRecords': len(records), 'duplicateAdvanced': False})

    def test_16_actual_orchestration_attempts_all_five_cleanup_actions_after_failure(self):
        expected = ['loopback-server-shutdown', 'loopback-server-close', 'loopback-thread-join',
                    'ephemeral-capability-workspace-removal', 'owned-simulator-and-baseline-reconciliation']
        for fail_cleanup in [False, True]:
            with self.subTest(failCleanup=fail_cleanup), namespace(composition=True) as (module, root, output):
                events = []
                selected = []
                primary = RuntimeError('explicit synthetic selected-command failure')
                def record(label):
                    events.append(label)
                    if fail_cleanup: raise RuntimeError('explicit synthetic cleanup failure: ' + label)
                class Commands:
                    def __init__(self, path, capability): self.reporting_error = None; self.cleanup_mode = False
                    def redact(self, value): return value
                    def record(self, *args): pass
                    def simctl(self, *args):
                        self_outer.assertEqual(args, ('list', 'runtimes', '--json'))
                        return json.dumps({'runtimes': [{'identifier': 'host-synthetic-runtime', 'buildversion': 'host-synthetic-build', 'isAvailable': True}]})
                    def run(self, argv, **kwargs):
                        if argv[:3] == ['/usr/bin/xcrun', 'simctl', 'bootstatus']: return (0, '', '')
                        self_outer.assertEqual(argv, module.importer.command_argv(root, output / 'runtime/session'))
                        raise primary
                class Server:
                    server_port = 0
                    def serve_forever(self): raise AssertionError('Host recorder must never start a real server')
                    def shutdown(self): record(expected[0])
                    def server_close(self): record(expected[1])
                class Thread:
                    def __init__(self, target, daemon): pass
                    def start(self): pass
                    def join(self, timeout): record(expected[2])
                    def is_alive(self): return False
                def allocate(h, lifecycle):
                    path = output / 'runtime/session'; path.mkdir(mode=0o700)
                    return path
                h = types.SimpleNamespace(
                    select_runtime_directory=lambda scope: output / 'runtime',
                    SCOPES={'interaction': {'cases': {'keyboard-enabled-off'}, 'methods': module.METHODS}},
                    verify=lambda: {'sealSHA256': 'explicit-host-recorder-seal'},
                    require=p.require, secrets=types.SimpleNamespace(token_hex=lambda n: 'explicit-host-recorder'),
                    Commands=Commands, json=json, RUNTIME='host-synthetic-runtime', RUNTIME_BUILD='host-synthetic-build',
                    write=lambda *args: None, devices=lambda commands: {}, owned_device=lambda lifecycle, devices: {'state': 'Booted'},
                    packet=types.SimpleNamespace(CONFIGS={}), Bridge=lambda *args, **kwargs: object(),
                    server_for=lambda bridge: Server(), threading=types.SimpleNamespace(Thread=Thread),
                    DEVELOPER=Path(root['developerDirectory']),
                    cleanup=lambda *args: record(expected[4]),
                    runtime_summary=lambda scope, bridge, code, failure, cleanups: {'runPassed': False, 'cleanupResults': cleanups})
                self_outer = self
                def selector(harness, argv, path):
                    selected.append(list(argv)); module.join_support._selected = {'session': path, 'argv': list(argv)}
                with mock.patch.object(module.join_support, 'prepare_session', allocate), \
                     mock.patch.object(module.join_support, 'session_configuration', lambda *args: output / 'runtime/session/session.xctestrun'), \
                     mock.patch.object(module.join_support, 'retire_session', lambda *args: record(expected[3])), \
                     mock.patch.object(module.join_support, '_ORIGINAL_SELECT', selector):
                    with self.assertRaises(RuntimeError) as caught:
                        module.orchestration.run(h, types.SimpleNamespace(check=lambda roots: None), [], 'explicit-host-recorder-seal')
                self.assertIs(caught.exception, primary)
                self.assertEqual(events, expected); self.assertEqual(len(selected), 1)
                self.assertEqual([value['resource'] for value in h.last_runtime_summary['cleanupResults']], expected)
                self.assertEqual([value['passed'] for value in h.last_runtime_summary['cleanupResults']], [not fail_cleanup] * 5)
                self.assertFalse(h.last_runtime_summary['runPassed'])
                CLEANUP_PROBES.append({'syntheticOnly': True, 'cleanupFailuresInjected': fail_cleanup,
                                       'actionsAttemptedInOrder': events, 'originalExceptionPreserved': True,
                                       'selectedCommandRecorderCalls': len(selected), 'nativeExecuted': False})


def main():
    global ATTEMPT, SCRATCH, PAYLOAD, REFERENCE_PATHS
    packet_before = (p.BASE / 'packet.json').read_bytes()
    REFERENCE_PATHS = {p.ROOT / name for name in json.loads(packet_before)['references']}
    number = 1
    while (p.BASE / ('attempt-' + str(number))).exists(): number += 1
    ATTEMPT = p.BASE / ('attempt-' + str(number)); ATTEMPT.mkdir()
    SCRATCH = Path(tempfile.mkdtemp(prefix='controls-owned-', dir=p.BASE))
    sys.addaudithook(audit)
    before = p.references()
    PAYLOAD = p.derived_payload()[0]
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeControls)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        shutil.rmtree(SCRATCH)
    unchanged = p.references() == before and (p.BASE / 'packet.json').read_bytes() == packet_before
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'packetSHA256': p.sha(packet_before), 'python': sys.version,
               'testsRun': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'skipped': len(result.skipped), 'passed': result.wasSuccessful(),
               'selectorProbes': SELECTORS, 'syntheticDispatchRecorderCalls': DISPATCH,
               'deniedLiveReads': DENIED, 'reviewedReceiverProbes': RECEIVER_PROBES, 'independentCleanupProbes': CLEANUP_PROBES, 'acceptedInputsAndPacketUnchanged': unchanged,
               'ownedScratchAbsent': not SCRATCH.exists(), 'ownedChildProcessesCreated': 0,
               'nativeCommandsExecuted': 0, 'nativeInstancesCreatedOrQueried': 0,
               'listenersStarted': 0, 'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}
    (ATTEMPT / 'receipt.json').write_bytes(p.stable(receipt))
    print(json.dumps({'passed': result.wasSuccessful(), 'testsRun': result.testsRun,
                      'ownedScratchAbsent': not SCRATCH.exists(), 'nativeExecuted': False}))
    if not result.wasSuccessful() or not unchanged:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
