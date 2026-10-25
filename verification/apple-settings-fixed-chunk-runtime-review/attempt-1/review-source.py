#!/usr/bin/env python3
"""Independent closed-input source review and finite host-only runtime controls."""
import contextlib
import copy
import datetime
from decimal import Decimal, Inexact, localcontext
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile
import tempfile
import types
import unittest
from unittest import mock

ARTIFACT_ROOT = Path(__file__).resolve().parent
BASE = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else ARTIFACT_ROOT / 'attempt-1'
ROOT = ARTIFACT_ROOT.parents[1]
PRODUCER = ROOT / 'verification/apple-settings-fixed-chunk-runtime-preparation'
PRIOR = ROOT / 'verification/apple-settings-instrumented-runtime-preparation'
BUILD = ROOT / 'verification/apple-settings-fixed-chunk-native-build/attempt-1'
ENDPOINT = ROOT / 'verification/apple-settings-fixed-chunk-implementation'
EXPECTED_HANDOFF = 'bcb2b7135eaa594b6a6ac0a84866cf0877ec1a3cb0264b1a51fcc33afd0860b2'
EXPECTED_PACKET = '2a1804ce1a6ece3b7b2125f4aa677e40c54f31846d94f3fec13e1f74d786eed7'
RECEIVER = 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'
DENIED = []
ALLOWED = set()
FIXTURE = None


def stable(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def row(path):
    info = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            'Canonical single-link regular input required: ' + str(path))
    raw = path.read_bytes()
    return {'kind': 'file', 'mode': stat.S_IMODE(info.st_mode), 'bytes': len(raw), 'sha256': sha(raw)}


def audit(event, args):
    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.exec',
            'os.posix_spawn', 'os.fork', 'os.forkpty', 'pty.spawn', 'os.kill', 'os.killpg',
            'ctypes.dlopen'}:
        DENIED.append({'event': event, 'category': 'process-network-native-denied'})
        raise AssertionError('Closed host review forbids ' + event)
    if event in {'open', 'os.scandir', 'os.listdir'} and args and isinstance(args[0], (str, bytes)):
        candidate = Path(os.fsdecode(args[0]))
        if event == 'open' and not candidate.is_absolute():
            frame = sys._getframe(1)
            if frame.f_code is shutil._rmtree_safe_fd_step.__code__:
                candidate = Path(frame.f_locals['path'])
        path = candidate.resolve()
        if any(part in str(path).lower() for part in ('catalog-inspector', 'authority-driver', 'worker-transport')):
            raise PermissionError('Excluded lane denied')
        writing = event == 'open' and ((isinstance(args[1], str) and any(c in args[1] for c in 'wax+'))
                   or len(args) > 2 and isinstance(args[2], int) and args[2] & (os.O_WRONLY | os.O_RDWR))
        if writing and not path.is_relative_to(BASE):
            raise PermissionError('Review cannot mutate accepted inputs')
        if not (path.is_relative_to(BASE) or path.is_relative_to(Path(sys.base_prefix).resolve())
                or path in ALLOWED or str(path) == '/dev/null'):
            DENIED.append({'event': event, 'path': str(path), 'category': 'ambient-read-denied'})
            raise PermissionError('Closed host review read boundary')


def archive(path, rows, prefix='', explicit_directories=False):
    payload, seen, directories = {}, set(), set()
    expected_dirs = {prefix.rstrip('/')} if prefix else set()
    for name in rows:
        expected_dirs.update(str(p) for p in PurePosixPath(prefix + name).parents if str(p) != '.')
    with tarfile.open(path, 'r:gz') as source:
        for member in source.getmembers():
            name = member.name
            canonical = PurePosixPath(name)
            require(name and str(canonical) == name and not canonical.is_absolute()
                    and '..' not in canonical.parts and name not in seen, 'Unsafe/repeated archive path')
            seen.add(name)
            if member.isdir():
                require(member.mode == 0o755, 'Archive directory mode differs')
                directories.add(name)
                continue
            require(member.isfile() and name.startswith(prefix), 'Archive file type/prefix differs')
            relative = name[len(prefix):]
            require(relative in rows, 'Unexpected archive member')
            raw = source.extractfile(member).read()
            require({'kind': 'file', 'mode': member.mode, 'bytes': len(raw), 'sha256': sha(raw)} == rows[relative],
                    'Archive member differs: ' + relative)
            payload[relative] = raw
    require(set(payload) == set(rows), 'Archive file inventory differs')
    require(directories == (expected_dirs if explicit_directories else set()), 'Archive directory inventory differs')
    return payload


def source_review(packet, handoff):
    require(len(handoff['members']) == 66 and len(packet['references']) == 116, 'Exact sealed input counts differ')
    require(sha(stable(handoff['members'])) == handoff['memberTreeSHA256'], 'Handoff tree differs')
    inputs = {**packet['references'], **handoff['members']}
    for name, expected in inputs.items():
        require(row(ROOT / name) == expected, 'Independent input check differs: ' + name)
    for name, expected in packet['files'].items():
        require(row(PRODUCER / name) == expected, 'Packet artifact differs: ' + name)
    runtime_manifest = json.loads((PRODUCER / 'runtime-source-manifest.json').read_bytes())
    prior_manifest = json.loads((PRIOR / 'runtime-source-manifest.json').read_bytes())
    compile_manifest = json.loads((BUILD / 'source-manifest.json').read_bytes())
    product_manifest = json.loads((BUILD / 'product-manifest.json').read_bytes())
    endpoint_rows = json.loads((ENDPOINT / 'source-package-manifest.json').read_bytes())
    for directory, name, manifest in [(PRODUCER, 'runtime-sources.tar.gz', runtime_manifest),
                                    (PRIOR, 'runtime-sources.tar.gz', prior_manifest),
                                    (BUILD, 'accepted-sources.tar.gz', compile_manifest),
                                    (BUILD, 'products.tar.gz', product_manifest)]:
        require(row(directory / name) == manifest['archive'], 'Archive identity differs')
    selected = archive(PRODUCER / 'runtime-sources.tar.gz', runtime_manifest['files'], 'selected/', True)
    original = archive(PRIOR / 'runtime-sources.tar.gz', prior_manifest['files'], 'selected/', True)
    compiled = archive(BUILD / 'accepted-sources.tar.gz', compile_manifest['sources'])
    products = archive(BUILD / 'products.tar.gz', product_manifest['products'])
    endpoint = archive(ENDPOINT / 'review-source-package.tar.gz', endpoint_rows, 'package/')
    require((len(selected), len(compiled), len(products), len(endpoint)) == (32, 40, 55, 97), 'Closure counts differ')
    require(all(endpoint['sources/' + name] == raw for name, raw in compiled.items()), 'Compile/review source mismatch')
    require(selected[RECEIVER] == endpoint['sources/selected/' + RECEIVER], 'Actual receiver differs from reviewed source')
    changed = sorted(name for name in selected if selected[name] != original[name])
    require(changed == sorted([RECEIVER, 'importer.py', 'join_support.py', 'local_first_failure.py']), 'Nonlocal selected delta')
    reverse = {}
    substitutions = {
        'importer.py': [(packet['sourceTreeSHA256'], '2b44b02dbd702becefa8b609435928890ad7c1a5f7cb11b3cc0fd1f5000ca101'),
            (packet['nativeProductArchiveSHA256'], 'c3e696b102d0a5daefa928e2941437739c5c418eb876dc31a65f0acef8e6e924'),
            ('mixer.apple-focus-reference-root-selection.7', 'mixer.apple-focus-reference-root-selection.6'),
            ('MixerFocusReferenceV7-', 'MixerFocusReferenceV6-'),
            ('mixer.apple-focus-reference-runtime-import.7', 'mixer.apple-focus-reference-runtime-import.6')],
        'join_support.py': [('native-run-v7-', 'native-run-v6-'),
            ('mixer.apple-focus-reference-runtime.7', 'mixer.apple-focus-reference-runtime.6')],
        'local_first_failure.py': [('native-run-v7-', 'native-run-v6-')],
    }
    for name, pairs in substitutions.items():
        restored = selected[name]
        for before, after in pairs:
            require(restored.count(before.encode()) == (2 if name == 'local_first_failure.py' else 1), 'Literal count differs')
            restored = restored.replace(before.encode(), after.encode())
        require(restored == original[name], 'Nonliteral semantic delta in ' + name)
        reverse[name] = {'restoredSHA256': sha(restored), 'acceptedV6SHA256': sha(original[name]), 'byteIdentical': True}
    require(sha(stable(runtime_manifest['files'])) == packet['runtimeSourceTreeSHA256'] == runtime_manifest['treeSHA256'], 'Runtime tree mismatch')
    require(sha(stable(compile_manifest['sources'])) == packet['sourceTreeSHA256'] == compile_manifest['sourceTreeSHA256'], 'Compile tree mismatch')
    require(sha(stable(product_manifest['products'])) == product_manifest['productTreeSHA256'], 'Product tree mismatch')
    require(packet['rootSelectionSchema'].endswith('.7') and packet['outputPrefix'] == 'native-run-v7-'
            and packet['simulatorNamePrefix'] == 'MixerFocusReferenceV7-', 'Packet namespace mismatch')
    require(product_manifest['runnerProductFiles'] == 42 and product_manifest['originalApplicationFilesUnchanged'] == 13,
            'Accepted fresh/original product provenance differs')
    template = json.loads((PRODUCER / 'selection-template.json').read_bytes())
    require(template['productArchive'] == str(BUILD / 'products.tar.gz') and template['productManifest'] == product_manifest,
            'Selection template does not bind actual fresh archive/manifest')
    require(template['files'] == {name: sha(raw) for name, raw in selected.items()}, 'Selection source identities differ')
    producer_runs = [json.loads((PRODUCER / ('attempt-' + str(n)) / 'receipt.json').read_bytes()) for n in [1, 2, 3]]
    require((producer_runs[0]['testsRun'], producer_runs[0]['failures'], producer_runs[0]['errors']) == (16, 1, 0), 'Initial namespace failure not preserved')
    require(all(r['testsRun'] == 16 and r['passed'] and r['failures'] == r['errors'] == r['skipped'] == 0 for r in producer_runs[1:]), 'Producer final controls differ')
    receipt = {'schema': 1, 'passed': True, 'handoffMembers': 66, 'acceptedReferences': 116,
        'selectedRuntimeFiles': 32, 'compileSources': 40, 'productFiles': 55, 'reviewedEndpointMembers': 97,
        'changedSelectedFiles': changed, 'unchangedSelectedFiles': 28, 'reverseSubstitutions': reverse,
        'runtimeSourceTreeSHA256': packet['runtimeSourceTreeSHA256'], 'compileSourceTreeSHA256': packet['sourceTreeSHA256'],
        'productArchiveSHA256': packet['nativeProductArchiveSHA256'], 'productTreeSHA256': product_manifest['productTreeSHA256'],
        'compileArchiveSHA256': compile_manifest['archive']['sha256'], 'runtimeArchiveSHA256': runtime_manifest['archive']['sha256'],
        'nativeExecutionSelected': False, 'nativeExecuted': False, 'inputs': inputs,
        'sourceRevisionContext': packet['sourceRevisionContext'], 'revisionMeaning': 'Inherited label; no Git query; exact hashes authoritative',
        'producerControls': [{'attempt': n, 'testsRun': r['testsRun'], 'passed': r['passed'], 'failures': r['failures']} for n, r in zip([1,2,3], producer_runs)]}
    (BASE / 'source-verification.json').write_bytes(stable(receipt))
    return selected, original


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class IndependentControls(unittest.TestCase):
    def test_missing_v7_diagnostic_prefix_regression(self):
        with c.namespace() as (adapter, root, output):
            diagnostic = adapter.local_first_failure
            streams = {'stdout': diagnostic.PREFIX + json.dumps(c.safe_sample()).encode() + b'\n', 'stderr': b''}
            session, observer = c.observe_files(adapter, root, output, streams)
            report = diagnostic.collect(session, root)
            self.assertEqual(report['status'], 'captured-safe-local-record')
            old_path = output / 'selected/local_first_failure_old_prefix.py'
            current = (output / 'selected/local_first_failure.py').read_bytes()
            self.assertEqual(current.count(b'native-run-v7-'), 2)
            old_path.write_bytes(current.replace(b'native-run-v7-', b'native-run-v6-'))
            old = load('_diagnostic_old_prefix_regression', old_path)
            self.assertEqual(old.capture(session, root)['status'], 'unavailable-or-invalid')
            self.assertFalse((session / 'local-settings-first-failure.json').exists())
            result = diagnostic.capture(session, root)
            target = session / 'local-settings-first-failure.json'
            first = target.read_bytes()
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(result['observedXCTestExitCode'], 65)
            self.assertFalse(any(result[k] for k in ['nativeImporterAcceptanceGranted', 'runPassed', 'settingsPreconditionPassed', 'gaAccepted']))
            self.assertFalse(adapter.importer.import_selected(root, session, observer, streams, {}, {}, {}, [], None, None)['provenanceAccepted'])
            self.assertEqual(target.read_bytes(), first)

    def test_metadata_storage_failure_preserves_primary_error_and_success_identity(self):
        with c.namespace() as (adapter, root, output):
            adapter.configure_root(root)
            session = output / 'runtime/session'; session.mkdir(parents=True, mode=0o700)
            error = RuntimeError('explicit selected-command recorder failure')
            adapter._selected = {'session': session}
            def fail(*args): raise error
            adapter._ORIGINAL_RUN_OBSERVED = fail
            with mock.patch.object(adapter.local_first_failure.os, 'open', side_effect=OSError('explicit storage recorder failure')):
                with self.assertRaises(RuntimeError) as caught:
                    adapter.run_observed(None, [], 600, False, None)
            self.assertIs(caught.exception, error)
            value = object()
            adapter._ORIGINAL_RUN_OBSERVED = lambda *args: value
            adapter._selected['sessionIdentity'] = adapter.path_identity(session, 0o700)
            self.assertIs(adapter.run_observed(None, [], 600, False, None), value)

    def test_host_boundary_is_active_before_selected_imports(self):
        with self.assertRaises(PermissionError): (ROOT / 'AGENTS.md').read_bytes()
        with self.assertRaises(AssertionError): sys.audit('subprocess.Popen', 'forbidden', [], None, None)
        with self.assertRaises(AssertionError): sys.audit('socket.bind', None, ('127.0.0.1', 0))
        self.assertTrue(any(item.get('path') == str(ROOT / 'AGENTS.md') for item in DENIED))


def main():
    global c, ALLOWED, FIXTURE
    packet_raw = (PRODUCER / 'packet.json').read_bytes()
    handoff_raw = (PRODUCER / 'handoff.json').read_bytes()
    require(sha(packet_raw) == EXPECTED_PACKET and sha(handoff_raw) == EXPECTED_HANDOFF, 'Assigned input identities differ')
    packet, handoff = json.loads(packet_raw), json.loads(handoff_raw)
    ALLOWED = {ROOT / name for name in set(packet['references']) | set(handoff['members'])}
    ALLOWED.update({PRODUCER / 'handoff.json', ROOT / 'verification/apple-settings-fixed-chunk-runtime-root-review/input-verification.json'})
    sys.addaudithook(audit)
    selected, original = source_review(packet, handoff)
    fixture = BASE / 'host-fixture'
    fixture.mkdir()
    for name in packet['files']:
        (fixture / name).write_bytes((PRODUCER / name).read_bytes())
    (fixture / 'packet.json').write_bytes(packet_raw)
    p = load('prepare', fixture / 'prepare.py')
    p.ROOT, p.PRIOR, p.BUILD, p.BUILD_ATTEMPT, p.ENDPOINT = ROOT, PRIOR, BUILD.parent, BUILD, ENDPOINT
    c = load('_producer_finite_controls', fixture / 'run_controls.py')
    c.ATTEMPT = BASE / 'host-attempt'; c.ATTEMPT.mkdir()
    c.SCRATCH = Path(tempfile.mkdtemp(prefix='review-owned-', dir=BASE))
    c.PAYLOAD = selected
    methods = ['test_02_actual_composition_exact_products_and_origin_guard', 'test_03_false_module_origin_rejects',
        'test_04_actual_configured_adapter_selector_prefixes_and_exact_argv',
        'test_05_unconfigured_existing_result_and_redirected_path_reject',
        'test_06_old_identity_schema_and_stale_selection_reject',
        'test_07_actual_dispatch_routes_exact_products_once_with_no_native_runner',
        'test_09_unknown_secrets_malformed_identity_duplicates_and_size_reject',
        'test_10_actual_selected_stream_binding_captures_failed_native_command',
        'test_11_incomplete_eof_wrong_command_group_and_redirected_log_reject',
        'test_12_diagnostic_wrapper_runs_on_native_exception_without_replacing_it',
        'test_13_decimal_and_exact_timestamp_semantics_stay_original',
        'test_15_actual_composed_reviewed_receiver_exact_start_agreement',
        'test_16_actual_orchestration_attempts_all_five_cleanup_actions_after_failure']
    suite = unittest.TestSuite(c.RuntimeControls(name) for name in methods)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls))
    try:
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        shutil.rmtree(c.SCRATCH)
    unchanged = all(row(ROOT / name) == expected for name, expected in {**packet['references'], **handoff['members']}.items())
    unchanged = unchanged and (PRODUCER / 'packet.json').read_bytes() == packet_raw and (PRODUCER / 'handoff.json').read_bytes() == handoff_raw
    fixture_inputs = {name: row(fixture / name) for name in packet['files']}
    require(all(value == packet['files'][name] for name, value in fixture_inputs.items()), 'Review host utility copies changed')
    retained = {}
    for path in sorted((fixture / 'dispatch-attempts').glob('*.json')):
        retained[path.name] = path.read_bytes()
    markers = BASE / 'host-attempt/dispatch-attempts'; markers.mkdir()
    for name, raw in retained.items():
        (markers / name).write_bytes(raw); (markers / name).chmod(0o600)
    shutil.rmtree(fixture)
    receipt = {'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'packetSHA256': EXPECTED_PACKET, 'handoffSHA256': EXPECTED_HANDOFF,
        'testsRun': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped), 'passed': result.wasSuccessful(), 'selectedProducerMethods': methods,
        'independentMethods': unittest.defaultTestLoader.getTestCaseNames(IndependentControls),
        'producerControlSourceSHA256': sha((PRODUCER / 'run_controls.py').read_bytes()),
        'copiedUtilityBindings': fixture_inputs, 'auditInstalledBeforeDispatcherAndSelectedImports': True,
        'deniedControls': DENIED, 'selectorProbes': c.SELECTORS, 'syntheticDispatchRecorderCalls': c.DISPATCH,
        'fixed4992ReceiverProbes': c.RECEIVER_PROBES, 'independentCleanupProbes': c.CLEANUP_PROBES,
        'acceptedInputsAndPacketUnchanged': unchanged, 'ownedScratchAbsent': not c.SCRATCH.exists(),
        'hostFixtureRemoved': not fixture.exists(), 'nativeCommandsExecuted': 0, 'nativeInstancesQueriedOrCreated': 0,
        'ownedChildProcessesCreatedByControls': 0, 'listenersStarted': 0, 'nativeExecuted': False,
        'nativeExecutionSelected': False, 'physicalPhones': 'disconnected-deferred', 'gaAccepted': False}
    (BASE / 'host-attempt/receipt.json').write_bytes(stable(receipt))
    (BASE / 'cleanup.json').write_bytes(stable({'scope': 'Owned host source/module/product staging only',
        'hostFixtureRemoved': not fixture.exists(), 'moduleScratchAbsent': not c.SCRATCH.exists(),
        'dispatcherSourceAndProductScratchAbsent': all(json.loads(path.read_bytes())['scratchAbsent'] for path in (BASE / 'host-attempt').glob('*/scratch-cleanup.json')),
        'nativeInstancesOperatedOrCreated': 0, 'otherProjectsTouched': False}))
    print(json.dumps({'passed': result.wasSuccessful(), 'testsRun': result.testsRun, 'inputsUnchanged': unchanged,
                      'ownedScratchAbsent': not c.SCRATCH.exists() and not fixture.exists(), 'nativeExecuted': False}))
    if not result.wasSuccessful() or not unchanged:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
