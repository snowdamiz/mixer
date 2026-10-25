#!/usr/bin/env python3
"""Independent finite host review of the frozen V5 namespace derivative only."""
import contextlib
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import sys
import tarfile
import tempfile
import traceback
from unittest import mock

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRODUCER = ROOT / 'verification/apple-focus-reference-runtime-v5-namespace-correction'
ORIGINAL = ROOT / 'verification/apple-focus-reference-runtime-v5'
PRIOR = ROOT / 'verification/apple-focus-reference-runtime-v5-independent-review'
DECISION = ROOT / 'verification/apple-focus-reference-runtime-v5-root-review/independent-decision.json'
EXPECTED_HANDOFF = 'bfc528c7786e681f964e93e9f022bae13dc9dd0ebd8b9f343f44f1834004d631'
EXPECTED_PACKET = '6c57bc5552a4f7e0e21ff1fdd589b270aa98b483f366f78bd88de2e26c0fd7dc'
EXPECTED_RUNTIME = 'a526e25ebe8c5ce382a86376afb6076e984c7f92d77c05ae82e7ced54b5f32ad'
CHECKS, SELECTORS, DISPATCHES, DENIED = [], [], [], []
SCRATCH = None
ALLOWED_ORIGINAL = {ORIGINAL / name for name in [
    'handoff.json', 'prepare.py', 'adapter.py', 'importer.py', 'test_importer.py',
    'packet.json', 'runtime-source-manifest.json', 'runtime-sources.tar.gz',
    'selection-template.json', 'input-bindings.json', 'frozen-inputs.tar.gz']}


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def row(path):
    info = path.lstat()
    assert path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    raw = path.read_bytes()
    return {'kind': 'file', 'mode': stat.S_IMODE(info.st_mode), 'bytes': len(raw), 'sha256': sha(raw)}


def check(name, condition, detail=None):
    assert condition, name
    CHECKS.append({'name': name, 'passed': True, 'detail': detail})


def rejection(name, fn, message):
    try:
        fn()
    except ValueError as error:
        check(name, message in str(error), str(error))
    else:
        raise AssertionError(name + ': unexpectedly accepted')


def audit(event, args):
    if (event.startswith(('subprocess.', 'os.exec', 'os.spawn', 'os.posix_spawn')) or
            event in {'os.system', 'os.fork', 'os.forkpty'} or event.startswith('socket.')):
        DENIED.append({'event': event})
        raise PermissionError('Independent host review forbids ' + event)
    if event not in {'open', 'os.scandir', 'os.listdir'} or not args or not isinstance(args[0], (str, bytes)):
        return
    candidate = Path(os.fsdecode(args[0]))
    if event == 'open' and not candidate.is_absolute():
        caller = sys._getframe(1)
        if caller.f_code is shutil._rmtree_safe_fd_step.__code__:
            candidate = Path(caller.f_locals['path'])
    path = candidate.resolve()
    if any(term in str(path).lower() for term in ('hosted', 'catalog-inspector', 'authority-driver', 'outbound-worker', 'worker-transport')):
        DENIED.append({'event': event, 'path': str(path)})
        raise PermissionError('Excluded lane unavailable to review')
    allowed = (path.is_relative_to(BASE) or path.is_relative_to(PRODUCER) or
               path.is_relative_to(Path(sys.base_prefix).resolve()) or
               path in ALLOWED_ORIGINAL or path in {PRIOR / 'handoff.json', DECISION,
                   ROOT / 'docs/apple-focus-reference-runtime-v5-namespace-correction.md', Path('/dev/null')})
    if not allowed:
        DENIED.append({'event': event, 'path': str(path)})
        raise PermissionError('Independent closed-read boundary: ' + str(path))
    if event == 'open' and len(args) > 2 and isinstance(args[2], int):
        writes = args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        if writes and not path.is_relative_to(BASE):
            raise PermissionError('Review writes confined to owned directory')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def root_fixture(run_id='11111111-1111-4111-8111-111111111111'):
    return {'schema': 'mixer.apple-focus-reference-root-selection.5', 'runID': run_id,
            'packetSHA256': EXPECTED_PACKET,
            'selectedAtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'ownedSimulatorIdentity': {'udid': '22222222-2222-4222-8222-222222222222',
                'name': 'MixerFocusReferenceV5-independent-host-synthetic',
                'runtime': 'com.apple.CoreSimulator.SimRuntime.iOS-26-5', 'build': '23F77'},
            'sourceTreeSHA256': '696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a',
            'productArchiveSHA256': '0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8',
            'developerDirectory': '/Applications/Xcode_26.6.app/Contents/Developer',
            'baselineDevices': {'devices': {}}, 'baselineFrontends': []}


def payload(archive, manifest):
    rows = json.loads(manifest.read_bytes())['files']
    with tarfile.open(archive, 'r:gz') as source:
        result = {item.name.removeprefix('selected/'): source.extractfile(item).read()
                  for item in source.getmembers() if item.isfile()}
    check('independent exact selected archive inventory: ' + archive.parent.name,
          set(result) == set(rows) and all(row['bytes'] == len(result[name]) and
          row['sha256'] == sha(result[name]) for name, row in rows.items()))
    return result


@contextlib.contextmanager
def adapter_namespace(p, selected, corrected, original, kind):
    directory = Path(tempfile.mkdtemp(prefix='selector-owned-', dir=SCRATCH))
    try:
        destination = directory / 'selected'
        p.materialize(destination, selected['files'], corrected)
        with mock.patch.dict(sys.modules):
            importer = load('importer', destination / 'importer.py')
            load('reference_contract', destination / 'reference_contract.py')
            load('settings_telemetry', destination / 'inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py')
            load('auxiliary_inventory', destination / 'auxiliary_inventory.py')
            if kind == 'selected-archive':
                namespace = vars(load('join_support', destination / 'join_support.py'))
            else:
                adapter = (ORIGINAL / 'adapter.py').read_bytes()
                source = original['join_support.py'][:-len(adapter)] + (PRODUCER / 'adapter.py').read_bytes()
                assert source == corrected['join_support.py']
                namespace = {'__name__': '_independent_actual_local_adapter'}
                exec(compile(source, str(PRODUCER / 'adapter.py'), 'exec'), namespace)
            yield namespace, importer, directory
    finally:
        shutil.rmtree(directory)


def selectors(p, selected, corrected, original):
    for kind in ['selected-archive', 'packet-local-adapter']:
        for version in [5, 4]:
            with adapter_namespace(p, selected, corrected, original, kind) as (namespace, importer, directory):
                root = root_fixture()
                namespace['configure_root'](root)
                session = directory / ('native-run-v' + str(version) + '-' + root['runID']) / 'runtime/session'
                session.mkdir(mode=0o700, parents=True)
                calls = []
                def recorder(h, argv, target):
                    calls.append({'argv': list(argv), 'session': str(target)})
                    namespace['_selected'] = {'session': target, 'argv': list(argv)}
                namespace['_ORIGINAL_SELECT'] = recorder
                error = None
                try:
                    namespace['select_command'](object(), importer.command_argv(root, session), session)
                except ValueError as caught:
                    error = str(caught)
                check(kind + ': actual V' + str(version) + ' selector routing',
                      (error is None) == (version == 5) and len(calls) == int(version == 5), error)
                SELECTORS.append({'source': kind, 'version': version, 'accepted': error is None,
                                  'originalSelectorCalls': len(calls), 'session': str(session), 'error': error})


def dispatch_controls(p):
    mirror = SCRATCH / 'producer-exact-mirror'
    mirror.mkdir()
    for name in p.SOURCES + p.ARTIFACTS + ['packet.json']:
        shutil.copyfile(PRODUCER / name, mirror / name)
        (mirror / name).chmod((PRODUCER / name).stat().st_mode & 0o777)
        assert row(mirror / name) == row(PRODUCER / name)
    p.BASE = mirror  # Relocate data/output only; executable function code stays frozen producer code.
    check('exact mirror passes actual correction verifier', p.verify()['packetSHA256'] == EXPECTED_PACKET)
    root = root_fixture('33333333-3333-4333-8333-333333333333')
    selection_file = SCRATCH / 'root-selection.json'
    selection_file.write_bytes(stable(root))
    selected_sha = sha(selection_file.read_bytes())
    before = set(mirror.iterdir())
    rejection('changed reviewed packet rejects before staging',
              lambda: p.dispatch('0' * 64, selection_file, selected_sha), 'Root reviewed packet hash differs')
    check('wrong reviewed packet makes no staging/output', set(mirror.iterdir()) == before)
    rejection('changed out-of-band selection digest rejects',
              lambda: p.dispatch(EXPECTED_PACKET, selection_file, '0' * 64), 'Root out-of-band selection hash differs')
    changed_root = copy.deepcopy(root); changed_root['packetSHA256'] = 'f' * 64
    changed_file = SCRATCH / 'changed-root-packet.json'; changed_file.write_bytes(stable(changed_root))
    rejection('changed root packet binding rejects',
              lambda: p.dispatch(EXPECTED_PACKET, changed_file, sha(changed_file.read_bytes())), 'Root selected packet differs')
    check('invalid selections create no native output', not list(mirror.glob('native-run-*')))
    manifest_path = mirror / 'runtime-source-manifest.json'
    original_manifest = manifest_path.read_bytes()
    manifest_path.write_bytes(original_manifest + b' ')
    try:
        rejection('changed source manifest rejects before staging',
                  lambda: p.dispatch(EXPECTED_PACKET, selection_file, selected_sha), 'Correction packet member changed')
    finally:
        manifest_path.write_bytes(original_manifest)
    original_spec = importlib.util.spec_from_file_location
    composition_calls = []
    output = mirror / ('native-run-v5-' + root['runID'])
    def intercept(name, path, *args, **kwargs):
        spec = original_spec(name, path, *args, **kwargs)
        if name != 'composition':
            return spec
        original_loader = spec.loader
        class Loader:
            def create_module(self, selected_spec):
                return original_loader.create_module(selected_spec)
            def exec_module(self, module):
                original_loader.exec_module(module)
                composition_calls.append(str(path))
                def no_native_run(seal):
                    verification = module.h.verify()
                    check('actual selected verifier accepts immutable staged bytes', verification['nativeAcceptanceGranted'] is False)
                    runtime_selection = json.loads((output / 'selected/runtime-selection.json').read_bytes())
                    check('dispatch stages exactly 55 immutable native product files',
                          len(runtime_selection['productManifest']['products']) == 55 and
                          p.tree(output / 'products') == runtime_selection['productManifest']['products'])
                    check('dispatch stages correction packet source digests',
                          runtime_selection['files'] == {name: item['sha256'] for name, item in
                          json.loads((mirror / 'runtime-source-manifest.json').read_bytes())['files'].items()})
                    source_file = output / 'selected/reference_contract.py'
                    source_bytes = source_file.read_bytes()
                    source_file.write_bytes(source_bytes + b'\n')
                    try:
                        rejection('actual selected verifier rejects changed source bytes', module.h.verify, 'Selected runtime bytes changed')
                    finally:
                        source_file.write_bytes(source_bytes)
                    product_name = next(iter(runtime_selection['productManifest']['products']))
                    product_file = output / 'products' / product_name
                    product_bytes = product_file.read_bytes()
                    product_file.write_bytes(product_bytes + b'\0')
                    try:
                        rejection('actual selected verifier rejects changed product bytes', module.h.verify, 'Compiled product changed')
                    finally:
                        product_file.write_bytes(product_bytes)
                    session = output / 'runtime/session'; session.mkdir(mode=0o700, parents=True)
                    calls = []
                    def select_recorder(h, argv, target):
                        calls.append({'argv': list(argv), 'session': str(target)})
                        module.join_support._selected = {'argv': list(argv), 'session': target}
                    module.join_support._ORIGINAL_SELECT = select_recorder
                    argv = module.importer.command_argv(root, session)
                    module.join_support.select_command(module.h, argv, session)
                    check('actual dispatcher and configured selector agree on V5 path',
                          len(calls) == 1 and calls[0]['session'] == str(session) and
                          runtime_selection['outputBase'] == str(output))
                    check('actual composition retains root selection and seal',
                          module.join_support._ROOT == root and verification['sealSHA256'] == seal)
                    DISPATCHES.append({'syntheticOnly': True, 'nativeRunnerReplaced': True,
                        'composition': str(path), 'outputBase': str(output), 'originalSelectorCalls': len(calls),
                        'selectedByteVerification': verification, 'productFiles': 55,
                        'runtimeSourceArchiveSHA256': EXPECTED_RUNTIME, 'rootSelectionSHA256': selected_sha,
                        'argv': argv, 'nativeExecuted': False})
                    return 'independent-host-recorder-only'
                module.h.run = no_native_run
        spec.loader = Loader()
        return spec
    before_path = list(sys.path)
    try:
        with mock.patch.dict(sys.modules), mock.patch.object(importlib.util, 'spec_from_file_location', side_effect=intercept):
            for name in json.loads((mirror / 'selection-template.json').read_bytes())['moduleAliases']:
                sys.modules.pop(name, None)
            result = p.dispatch(EXPECTED_PACKET, selection_file, selected_sha)
            check('actual dispatch returns recorder without native execution', result == 'independent-host-recorder-only')
            rejection('same dispatch UUID rejects before composition',
                      lambda: p.dispatch(EXPECTED_PACKET, selection_file, selected_sha), 'Fresh run output required')
            check('only one selected composition imported', len(composition_calls) == 1)
    finally:
        sys.path[:] = before_path
    check('actual dispatcher retires exact product and selected scratch',
          json.loads((output / 'scratch-cleanup.json').read_bytes())['scratchAbsent'])
    receipts = [json.loads(path.read_bytes()) for path in mirror.glob('dispatch-products-owned-*-cleanup.json')]
    check('all four immutable input staging workspaces cleaned', len(receipts) == 4 and
          all(item['verifiedBeforeRemoval'] and item['scratchAbsent'] for item in receipts))
    (BASE / 'dispatch-cleanup.json').write_bytes(stable({'productInputWorkspaces': receipts,
        'selectedProductScratch': json.loads((output / 'scratch-cleanup.json').read_bytes())}))
    (BASE / 'synthetic-root-selection.json').write_bytes(selection_file.read_bytes())
    # The immutable input source itself is never changed: exercise its actual
    # digest guard against a deliberately changed review-owned copy instead.
    original_location = p.ORIGINAL
    tamper = SCRATCH / 'changed-frozen-input'; tamper.mkdir()
    shutil.copyfile(original_location / 'input-bindings.json', tamper / 'input-bindings.json')
    (tamper / 'frozen-inputs.tar.gz').write_bytes(b'changed immutable input')
    p.ORIGINAL = tamper
    try:
        rejection('actual immutable input digest guard rejects changed archive',
                  p.frozen_product_inputs, 'Immutable V5 input archive changed')
    finally:
        p.ORIGINAL = original_location


def run():
    global SCRATCH
    start = datetime.datetime.now(datetime.timezone.utc)
    sys.dont_write_bytecode = True
    signal.signal(signal.SIGALRM, lambda *args: (_ for _ in ()).throw(TimeoutError('60 second review bound exceeded')))
    signal.alarm(60)
    sys.addaudithook(audit)
    handoff_bytes = (PRODUCER / 'handoff.json').read_bytes()
    check('root-supplied correction handoff digest', sha(handoff_bytes) == EXPECTED_HANDOFF)
    handoff = json.loads(handoff_bytes)
    check('compact correction handoff has exact 36-member tree', len(handoff['members']) == 36 and
          sha(stable(handoff['members'])) == handoff['memberTreeSHA256'])
    check('all 36 producer handoff members independently verified',
          all(row(ROOT / name) == expected for name, expected in handoff['members'].items()))
    producer_before = {name: row(ROOT / name) for name in handoff['members']}
    check('root-supplied correction packet and runtime archive digests',
          row(PRODUCER / 'packet.json')['sha256'] == EXPECTED_PACKET and
          row(PRODUCER / 'runtime-sources.tar.gz')['sha256'] == EXPECTED_RUNTIME)
    decision = json.loads(DECISION.read_bytes())
    check('prior root closure evidence remains explicit',
          sorted(item['membersVerified'] for item in decision['bindings'].values()) == [33, 4673])
    selected = json.loads((PRODUCER / 'runtime-source-manifest.json').read_bytes())
    original = payload(ORIGINAL / 'runtime-sources.tar.gz', ORIGINAL / 'runtime-source-manifest.json')
    corrected = payload(PRODUCER / 'runtime-sources.tar.gz', PRODUCER / 'runtime-source-manifest.json')
    changed = [name for name in sorted(original) if original[name] != corrected.get(name)]
    old_join, new_join = original['join_support.py'], corrected['join_support.py']
    differences = [{'offset': i, 'oldASCII': a, 'newASCII': b}
                   for i, (a, b) in enumerate(zip(old_join, new_join)) if a != b]
    check('31 runtime files: one ASCII byte in join_support, other 30 exact',
          len(original) == len(corrected) == 31 and set(original) == set(corrected) and
          changed == ['join_support.py'] and len(old_join) == len(new_join) and
          len(differences) == 1 and differences[0]['oldASCII'] == ord('4') and differences[0]['newASCII'] == ord('5'), differences)
    old_adapter = (ORIGINAL / 'adapter.py').read_bytes(); new_adapter = (PRODUCER / 'adapter.py').read_bytes()
    check('local adapter correction exact and selected adapter suffix exact',
          new_adapter == old_adapter.replace(b"'native-run-v4-'+_ROOT['runID']", b"'native-run-v5-'+_ROOT['runID']", 1)
          and old_join.endswith(old_adapter) and new_join.endswith(new_adapter))
    old_dispatch = (ORIGINAL / 'prepare.py').read_text().split('\ndef dispatch(', 1)[1].split('\n\nif __name__', 1)[0]
    new_dispatch = (PRODUCER / 'prepare.py').read_text().split('\ndef _dispatch(', 1)[1].split('\n\n@contextlib.contextmanager', 1)[0]
    check('actual retained dispatcher body exact except one V4 to V5 prefix',
          old_dispatch.count("'native-run-v4-'") == 1 and
          new_dispatch == old_dispatch.replace("'native-run-v4-'", "'native-run-v5-'", 1))
    check('importer and selection template preserve frozen V5 bytes',
          corrected['importer.py'] == (ORIGINAL / 'importer.py').read_bytes() == (PRODUCER / 'importer.py').read_bytes()
          and (PRODUCER / 'selection-template.json').read_bytes() == (ORIGINAL / 'selection-template.json').read_bytes())
    SCRATCH = Path(tempfile.mkdtemp(prefix='independent-review-owned-', dir=BASE))
    error = None
    try:
        p = load('_independent_v5_namespace_prepare', PRODUCER / 'prepare.py')
        check('actual correction verify passes exact packet and 13 references',
              p.verify()['packetSHA256'] == EXPECTED_PACKET and len(p.references()) == 13)
        selectors(p, selected, corrected, original)
        dispatch_controls(p)
    except BaseException:
        error = traceback.format_exc()
    finally:
        shutil.rmtree(SCRATCH)
        signal.alarm(0)
    producer_after = {name: row(ROOT / name) for name in handoff['members']}
    check('producer closure untouched after independent probes', producer_before == producer_after and
          sha((PRODUCER / 'handoff.json').read_bytes()) == EXPECTED_HANDOFF)
    receipt = {'schema': 'mixer.apple-focus-reference-runtime-v5-namespace-independent-review.1',
        'command': [sys.executable, '-B', str(BASE / 'review.py')], 'observedUTC': start.isoformat(),
        'completedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'python': sys.version, 'pythonExecutable': str(Path(sys.executable).resolve()),
        'reviewSource': row(BASE / 'review.py'), 'inheritedCompileRevisionLabel': 'ba9ad4372f94463ba4d363cdfd76dd565c96413f',
        'revisionMeaning': 'Inherited compile label only; exact bound source and packet digests define this review. No Git query.',
        'producerHandoffSHA256': EXPECTED_HANDOFF, 'producerPacketSHA256': EXPECTED_PACKET,
        'runtimeArchiveSHA256': EXPECTED_RUNTIME, 'selectedSourceTreeSHA256': selected['treeSHA256'],
        'producerMemberTreeSHA256': handoff['memberTreeSHA256'], 'membersVerified': 36,
        'checksPassed': len(CHECKS), 'checks': CHECKS, 'selectorProbes': SELECTORS, 'dispatchProbes': DISPATCHES,
        'error': error, 'passed': error is None, 'deniedEvents': DENIED, 'wallBoundSeconds': 60,
        'cleanup': {'ownedScratchAbsent': not SCRATCH.exists(), 'producerUnchanged': producer_before == producer_after,
                    'nativeInstancesCreatedOrQueried': 0, 'otherProjectsTouched': False},
        'nativeCommandsInvoked': 0, 'nativeExecuted': False, 'nativeSelected': False, 'gaAccepted': False,
        'physicalPhones': 'disconnected-deferred',
        'scope': 'Three prefix corrections and immutable staging only; no broad arithmetic replay or native authorization'}
    (BASE / 'receipt.json').write_bytes(stable(receipt))
    print(json.dumps({key: receipt[key] for key in ['passed', 'checksPassed', 'error', 'cleanup']}, indent=2))
    if error is not None:
        raise SystemExit(1)


if __name__ == '__main__':
    run()
