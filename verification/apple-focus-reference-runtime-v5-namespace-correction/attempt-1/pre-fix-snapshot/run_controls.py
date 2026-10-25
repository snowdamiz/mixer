#!/usr/bin/env python3
"""One finite host-only replay. Every original native selector is a recorder."""
import argparse
import ast
import contextlib
import copy
import datetime
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import textwrap
import types
import unittest
from unittest import mock

import prepare as p

ATTEMPT = None
SCRATCH = None
PAYLOAD = None
RECORDS = []
DISPATCH_RECORDS = []
DENIED = []


def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'socket.bind',
                 'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo'):
        raise AssertionError('Host-only correction forbids ' + event)
    if event in ('open', 'os.scandir', 'os.listdir') and args and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0])).resolve()
        if any(word in str(path).lower() for word in ('hosted', 'catalog', 'authority-driver', 'worker-transport')):
            raise AssertionError('Excluded lane read refused')
        allowed_files = {p.ORIGINAL / name for name in ['handoff.json', 'prepare.py', 'adapter.py', 'importer.py',
                         'test_importer.py', 'packet.json', 'runtime-source-manifest.json', 'runtime-sources.tar.gz',
                         'selection-template.json', 'input-bindings.json', 'frozen-inputs.tar.gz']}
        allowed_files |= {p.REVIEW / 'handoff.json', p.ROOT / 'verification/apple-focus-reference-runtime-v5-root-review/independent-decision.json'}
        if not (path.is_relative_to(p.BASE) or path.is_relative_to(Path(sys.base_prefix).resolve())
                or path in allowed_files or str(path) == '/dev/null'):
            DENIED.append({'event': event, 'path': str(path)})
            raise PermissionError('Correction closed-read boundary: ' + str(path))


def root_fixture():
    return {'schema': 'mixer.apple-focus-reference-root-selection.5',
            'runID': '11111111-1111-4111-8111-111111111111', 'packetSHA256': 'a' * 64,
            'selectedAtUTC': '2026-10-25T02:00:00+00:00',
            'ownedSimulatorIdentity': {'udid': '22222222-2222-4222-8222-222222222222',
                'name': 'MixerFocusReferenceV5-host-synthetic',
                'runtime': 'com.apple.CoreSimulator.SimRuntime.iOS-26-5', 'build': '23F77'},
            'sourceTreeSHA256': '696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a',
            'productArchiveSHA256': p.PRODUCT,
            'developerDirectory': '/Applications/Xcode_26.6.app/Contents/Developer',
            'baselineDevices': {'devices': {}}, 'baselineFrontends': []}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def selected_namespace(kind='archive'):
    temporary = Path(tempfile.mkdtemp(prefix='module-', dir=SCRATCH))
    try:
        p.materialize(temporary / 'selected', p.manifest(PAYLOAD), PAYLOAD)
        selected = temporary / 'selected'
        with mock.patch.dict(sys.modules):
            importer = load('importer', selected / 'importer.py')
            classifier = load('reference_contract', selected / 'reference_contract.py')
            load('settings_telemetry', selected / 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py')
            auxiliary = load('auxiliary_inventory', selected / 'auxiliary_inventory.py')
            if kind == 'archive':
                module = load('join_support', selected / 'join_support.py')
                namespace = vars(module)
            else:
                original = p.original_payload()['join_support.py']
                frozen_adapter = (p.ORIGINAL / 'adapter.py').read_bytes()
                prefix = original[:-len(frozen_adapter)]
                source = prefix + (p.BASE / 'adapter.py').read_bytes()
                assert source == PAYLOAD['join_support.py']
                namespace = {'__name__': '_packet_local_adapter_copy'}
                exec(compile(source, str(p.BASE / 'adapter.py'), 'exec'), namespace)
            yield namespace, importer, classifier, auxiliary
    finally:
        shutil.rmtree(temporary)


def select_probe(namespace, importer, parent, prefix, mutation=None, root=None, configure=True):
    root = copy.deepcopy(root or root_fixture())
    if configure:
        namespace['configure_root'](root)
    output = parent / (prefix + root['runID'])
    session = output / 'runtime/session'
    session.mkdir(mode=0o700, parents=True)
    session.chmod(0o700)
    calls = []
    def recorder(h, argv, selected_session):
        calls.append({'argv': list(map(str, argv)), 'session': str(selected_session)})
        namespace['_selected'] = {'session': selected_session, 'argv': list(map(str, argv))}
    namespace['_ORIGINAL_SELECT'] = recorder
    argv = importer.command_argv(root, session)
    if mutation:
        session, argv = mutation(session, argv)
    try:
        namespace['select_command'](object(), argv, session)
        error = None
    except ValueError as caught:
        error = str(caught)
    result = {'adapterSource': namespace.get('__name__'), 'outputPrefix': prefix,
              'accepted': error is None, 'originalSelectorCalls': len(calls), 'error': error,
              'session': str(session), 'syntheticOnly': True, 'nativeExecuted': False}
    RECORDS.append(result)
    return result


class PrefixControls(unittest.TestCase):
    def test_01_exact_three_routing_corrections_and_other_bytes(self):
        original = p.original_payload()
        self.assertEqual(len(original), 31)
        self.assertEqual(set(original), set(PAYLOAD))
        self.assertEqual([name for name in original if original[name] != PAYLOAD[name]], ['join_support.py'])
        self.assertEqual(PAYLOAD['join_support.py'], original['join_support.py'].replace(p.OLD_PREFIX, p.NEW_PREFIX, 1))
        self.assertEqual(PAYLOAD['importer.py'], (p.ORIGINAL / 'importer.py').read_bytes())
        self.assertEqual((p.BASE / 'importer.py').read_bytes(), PAYLOAD['importer.py'])
        self.assertEqual((p.BASE / 'selection-template.json').read_bytes(), (p.ORIGINAL / 'selection-template.json').read_bytes())
        original_dispatch = (p.ORIGINAL / 'prepare.py').read_text().split('\ndef dispatch(', 1)[1].split("\n\nif __name__", 1)[0]
        actual_dispatch = (p.BASE / 'prepare.py').read_text().split('\ndef _dispatch(', 1)[1].split('\n\n@contextlib.contextmanager', 1)[0]
        self.assertEqual(actual_dispatch, original_dispatch.replace("'native-run-v4-'", "'native-run-v5-'", 1))
        self.assertEqual((p.BASE / 'adapter.py').read_bytes(), (p.ORIGINAL / 'adapter.py').read_bytes().replace(p.OLD_PREFIX, p.NEW_PREFIX, 1))

    def test_02_actual_archive_and_local_adapter_accept_v5_reject_old_and_other_prefixes(self):
        for kind in ['archive', 'adapter']:
            for version in [5, 4, 3, 6]:
                with self.subTest(kind=kind, version=version), selected_namespace(kind) as (n, importer, _, _):
                    parent = Path(tempfile.mkdtemp(prefix='prefix-', dir=SCRATCH))
                    result = select_probe(n, importer, parent, 'native-run-v' + str(version) + '-')
                    self.assertEqual(result['accepted'], version == 5)
                    self.assertEqual(result['originalSelectorCalls'], int(version == 5))

    def test_03_wrong_argv_and_absent_configuration_reject_before_original(self):
        for configured in [False, True]:
            with self.subTest(configured=configured), selected_namespace() as (n, importer, _, _):
                parent = Path(tempfile.mkdtemp(prefix='argv-', dir=SCRATCH))
                result = select_probe(n, importer, parent, 'native-run-v5-',
                                      mutation=(lambda session, argv: (session, argv + ['-unselected'])) if configured else None,
                                      configure=configured)
                self.assertFalse(result['accepted']); self.assertEqual(result['originalSelectorCalls'], 0)

    def test_04_existing_result_and_symlink_workspace_reject_before_original(self):
        def existing(session, argv):
            (session / 'session.xcresult').mkdir()
            return session, argv
        def symlink(session, argv):
            alias = session.parent / 'alias'; alias.symlink_to(session, target_is_directory=True)
            return alias, importer.command_argv(root_fixture(), alias)
        for mutation in [existing, symlink]:
            with self.subTest(mutation=mutation.__name__), selected_namespace() as (n, importer, _, _):
                parent = Path(tempfile.mkdtemp(prefix='path-', dir=SCRATCH))
                result = select_probe(n, importer, parent, 'native-run-v5-', mutation=mutation)
                self.assertFalse(result['accepted']); self.assertEqual(result['originalSelectorCalls'], 0)

    def test_05_old_schema_and_simulator_names_still_reject(self):
        for version in [3, 4, 6]:
            for field in ['schema', 'name']:
                with self.subTest(version=version, field=field), selected_namespace() as (n, _, _, _):
                    root = root_fixture()
                    if field == 'schema':
                        root['schema'] = 'mixer.apple-focus-reference-root-selection.' + str(version)
                    else:
                        root['ownedSimulatorIdentity']['name'] = 'MixerFocusReferenceV' + str(version) + '-rejected'
                    with self.assertRaises(ValueError):
                        n['configure_root'](root)
                    self.assertIsNone(n['_ROOT'])

    def test_06_actual_dispatch_staging_and_configured_selected_adapter_agree(self):
        root = root_fixture(); root['runID'] = '33333333-3333-4333-8333-333333333333'
        root['packetSHA256'] = p.verify()['packetSHA256']
        root['selectedAtUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        selection_file = SCRATCH / 'root-selection.json'; selection_file.write_bytes(p.stable(root))
        output = p.BASE / ('native-run-v5-' + root['runID'])
        self.assertFalse(output.exists())
        real_spec = importlib.util.spec_from_file_location
        calls = []
        def select_composition(name, path, *args, **kwargs):
            spec = real_spec(name, path, *args, **kwargs)
            if name != 'composition':
                return spec
            original_loader = spec.loader
            class Loader:
                def create_module(self, selected_spec):
                    return original_loader.create_module(selected_spec)
                def exec_module(self, module):
                    # Load the actual selected composition with all byte/origin
                    # guards. Only its final h.run is replaced before invocation.
                    original_loader.exec_module(module)
                    actual = module.join_support
                    self_outer.assertEqual(module.h.verify()['nativeAcceptanceGranted'], False)
                    def no_native_run(seal):
                        session = output / 'runtime/session'; session.mkdir(mode=0o700, parents=True)
                        def recorder(h, argv, selected_session):
                            calls.append({'session': str(selected_session), 'argv': list(argv)})
                            actual._selected = {'session': selected_session, 'argv': list(argv)}
                        actual._ORIGINAL_SELECT = recorder
                        actual.select_command(module.h, module.importer.command_argv(root, session), session)
                        selection = json.loads((output / 'selected/runtime-selection.json').read_bytes())
                        DISPATCH_RECORDS.append({'outputBase': selection['outputBase'], 'selectedArchiveSHA256':
                            p.row(p.BASE / 'runtime-sources.tar.gz')['sha256'], 'selectionSealSHA256': seal,
                            'configuredRoot': copy.deepcopy(actual._ROOT), 'originalSelectorCalls': len(calls),
                            'selectedByteVerification': module.h.verify(), 'nativeRunReplacedWithRecorder': True,
                            'nativeExecuted': False, 'syntheticOnly': True})
                        return 'host-dispatch-recorder-only'
                    module.h.run = no_native_run
            self_outer = self
            spec.loader = Loader()
            return spec
        before_path = list(sys.path)
        cleanup_files_before = set(p.BASE.glob('dispatch-products-owned-*-cleanup.json'))
        try:
            with mock.patch.dict(sys.modules), mock.patch.object(importlib.util, 'spec_from_file_location', side_effect=select_composition):
                for alias in json.loads((p.BASE / 'selection-template.json').read_bytes())['moduleAliases']:
                    sys.modules.pop(alias, None)
                result = p.dispatch(root['packetSHA256'], selection_file, p.row(selection_file)['sha256'])
            self.assertEqual(result, 'host-dispatch-recorder-only')
            self.assertEqual(len(calls), 1)
            self.assertEqual(DISPATCH_RECORDS[-1]['outputBase'], str(output))
            self.assertTrue(json.loads((output / 'scratch-cleanup.json').read_bytes())['scratchAbsent'])
            # A second dispatch with the same UUID rejects before composition.
            with mock.patch.object(importlib.util, 'spec_from_file_location', side_effect=select_composition):
                with self.assertRaisesRegex(ValueError, 'Fresh run output required'):
                    p.dispatch(root['packetSHA256'], selection_file, p.row(selection_file)['sha256'])
            self.assertEqual(len(calls), 1)
            new_cleanup = sorted(set(p.BASE.glob('dispatch-products-owned-*-cleanup.json')) - cleanup_files_before)
            self.assertEqual(len(new_cleanup), 2)
            for path in new_cleanup:
                receipt = json.loads(path.read_bytes()); self.assertTrue(receipt['scratchAbsent'])
                shutil.move(str(path), ATTEMPT / path.name)
            shutil.copytree(output, ATTEMPT / 'synthetic-dispatch-output')
        finally:
            sys.path[:] = before_path
            if output.exists():
                shutil.rmtree(output)
        self.assertFalse(output.exists())

    def test_07_selection_hash_rejects_without_composition(self):
        root = root_fixture(); root['packetSHA256'] = p.verify()['packetSHA256']
        root['selectedAtUTC'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        path = SCRATCH / 'bad-selection-binding.json'; path.write_bytes(p.stable(root))
        before = set(p.BASE.glob('dispatch-products-owned-*-cleanup.json'))
        try:
            with self.assertRaisesRegex(ValueError, 'Root out-of-band selection hash differs'):
                p.dispatch(root['packetSHA256'], path, '0' * 64)
        finally:
            for receipt_path in set(p.BASE.glob('dispatch-products-owned-*-cleanup.json')) - before:
                self.assertTrue(json.loads(receipt_path.read_bytes())['scratchAbsent'])
                shutil.move(str(receipt_path), ATTEMPT / receipt_path.name)
        self.assertFalse((p.BASE / ('native-run-v5-' + root['runID'])).exists())

    def test_08_live_workspace_reads_and_scans_are_denied(self):
        with self.assertRaises(PermissionError):
            (p.ROOT / 'AGENTS.md').read_bytes()
        with self.assertRaises(PermissionError):
            list((p.ROOT / 'verification/apple-focus-diagnostic-runtime-v1/runtime/captures').iterdir())


def retained_suite():
    # Preserve method bytes from the frozen V5 test source. Bounded setup uses
    # only the selected archive; the original full fixture/setUpClass is not run.
    source = (p.ORIGINAL / 'test_importer.py').read_text()
    tree = ast.parse(source)
    klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'RuntimeControls')
    names = ['test_011_derived_modules_compile_without_tools', 'test_015_fresh_root_selection_requires_now_and_packet',
             'test_021_archive_round_trip_and_corruption_rejected',
             'test_023_adapter_actual_tool_capture_and_one_shot_binding',
             'test_024_dispatch_refuses_unreviewed_packet_before_native_import']
    methods = [(node.name, textwrap.dedent(ast.get_source_segment(source, node))) for node in klass.body
               if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(methods) == len(names)
    (ATTEMPT / 'retained-exact-methods.py').write_text('\n\n'.join(raw for _, raw in methods) + '\n')
    with selected_namespace() as (_, importer, classifier, auxiliary):
        namespace = {'prepare': p, 'i': importer, 'Path': Path, 'tempfile': tempfile, 'mock': mock,
                     'datetime': datetime, 'sys': sys}
        attributes = {'derived': PAYLOAD, 'classifier': classifier, 'auxiliary': auxiliary}
        def fixture(self):
            root = root_fixture(); session = SCRATCH / 'retained-synthetic/session'
            return {'root': root, 'session': session, 'observer': {'argv': importer.command_argv(root, session)}}
        attributes['fixture'] = fixture
        for name, raw in methods:
            exec(compile(raw, str(ATTEMPT / 'retained-exact-methods.py'), 'exec'), namespace)
            attributes[name] = namespace[name]
        retained = type('RetainedAffectedControls', (unittest.TestCase,), attributes)
        yield unittest.defaultTestLoader.loadTestsFromTestCase(retained), importer, classifier, auxiliary


def main():
    global ATTEMPT, SCRATCH, PAYLOAD
    parser = argparse.ArgumentParser(); parser.add_argument('--attempt', required=True, type=int); args = parser.parse_args()
    p.require(args.attempt > 0, 'Positive fresh attempt required')
    ATTEMPT = p.BASE / ('attempt-' + str(args.attempt)); ATTEMPT.mkdir()
    command = [sys.executable, '-B', str(p.BASE / 'run_controls.py'), '--attempt', str(args.attempt)]
    before = p.verify()
    snapshot = {name: p.row(p.BASE / name) for name in p.SOURCES + p.ARTIFACTS + ['packet.json']}
    (ATTEMPT / 'source-bindings.json').write_bytes(p.stable(snapshot))
    SCRATCH = Path(tempfile.mkdtemp(prefix='controls-owned-', dir=p.BASE))
    sys.dont_write_bytecode = True
    sys.addaudithook(audit)
    result = None
    error = None
    try:
        manifest = json.loads((p.BASE / 'runtime-source-manifest.json').read_bytes())
        PAYLOAD = p.archive_payload(p.BASE / 'runtime-sources.tar.gz', manifest['files'], manifest['archive']['sha256'], 'selected/')
        with (ATTEMPT / 'unittest.log').open('w') as log:
            for suite, importer, classifier, auxiliary in retained_suite():
                with mock.patch.dict(sys.modules, {'importer': importer, 'reference_contract': classifier, 'auxiliary_inventory': auxiliary}):
                    combined = unittest.TestSuite([suite, unittest.defaultTestLoader.loadTestsFromTestCase(PrefixControls)])
                    result = unittest.TextTestRunner(stream=log, verbosity=2).run(combined)
    except BaseException as caught:
        import traceback
        error = traceback.format_exc()
        (ATTEMPT / 'uncaught-error.txt').write_text(error)
    finally:
        shutil.rmtree(SCRATCH)
    after = p.verify()
    receipt = {'schema': 'mixer.apple-focus-reference-runtime-v5-namespace-correction-controls.1',
               'command': command, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'python': sys.version, 'pythonExecutable': str(Path(sys.executable).resolve()),
               'sourceTreeSHA256': p.sha(p.stable(snapshot)), 'packetSHA256': before['packetSHA256'],
               'testsRun': result.testsRun if result else 0, 'testsPassed': result.testsRun - len(result.failures) - len(result.errors) if result else 0,
               'controlsPassed': bool(result and result.wasSuccessful() and error is None), 'uncaughtError': error,
               'failures': [{'name': str(test), 'traceback': trace} for test, trace in result.failures] if result else [],
               'errors': [{'name': str(test), 'traceback': trace} for test, trace in result.errors] if result else [],
               'skipped': result.skipped if result else [], 'retainedExactTests': 5,
               'actualConfiguredSelectorProbes': len(RECORDS), 'dispatchCompositionRecorderRuns': len(DISPATCH_RECORDS),
               'deniedLiveReads': DENIED, 'packetUnchanged': before == after,
               'cleanup': {'ownedControlsScratchAbsent': not SCRATCH.exists(),
                           'ownedSyntheticNativeRunAbsent': not (p.BASE / 'native-run-v5-33333333-3333-4333-8333-333333333333').exists(),
                           'productInputScratchAbsent': not list(p.BASE.glob('dispatch-products-owned-*')),
                           'nativeInstancesCreatedOrQueried': 0, 'servicesStarted': 0, 'otherProjectsTouched': False},
               'nativeCommandsInvoked': 0, 'nativeExecuted': False, 'runtimeSelected': False,
               'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}
    (ATTEMPT / 'selector-probes.json').write_bytes(p.stable(RECORDS))
    (ATTEMPT / 'dispatch-probes.json').write_bytes(p.stable(DISPATCH_RECORDS))
    (ATTEMPT / 'receipt.json').write_bytes(p.stable(receipt))
    print(json.dumps({key: receipt[key] for key in ['testsRun', 'testsPassed', 'controlsPassed',
          'actualConfiguredSelectorProbes', 'dispatchCompositionRecorderRuns', 'cleanup']}, indent=2))
    if not receipt['controlsPassed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
