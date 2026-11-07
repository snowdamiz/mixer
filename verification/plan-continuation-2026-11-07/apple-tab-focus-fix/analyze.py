#!/usr/bin/env python3
"""Replay retained native evidence without invoking any device or application."""
import copy
import datetime
import hashlib
import importlib.util
import json
import pathlib
import plistlib
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PREVIOUS = HERE.parent / 'apple-settings-runtime-r2'
FIX = HERE.parent / 'apple-settings-fix'
RAW = pathlib.Path('/private/tmp/mixer-20261107-apple-settings-runtime-agcvpnc6/native-run-v9-44c60fae-a897-4a6e-ad42-7b9dbfb1d6a1')
SCRATCH = pathlib.Path(tempfile.mkdtemp(prefix='mixer-20261107-apple-tab-focus-', dir='/tmp'))

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

checks = []
def check(name, condition):
    assert condition, name
    checks.append(name)

bindings = {}
def bind(path, expected=None):
    data = path.read_bytes()
    actual = digest(data)
    if expected is not None:
        assert actual == expected, str(path)
    bindings[str(path)] = {'sha256': actual, 'bytes': len(data)}
    return data

retained = read(PREVIOUS / 'raw-artifacts.json')
for name, row in retained['members'].items():
    bind(RAW / name, row['sha256'])
check('every retained raw artifact matches sealed manifest', True)
previous = read(PREVIOUS / 'result.json')
for name in ['REPORT.txt', 'result.json', 'handoff.json', 'raw-artifacts.json', 'packet.json']:
    bind(PREVIOUS / name)
packet = read(PREVIOUS / 'packet.json')['acceptedBindings']
for key in ['candidatePacket', 'retainedProducts', 'runtimeArchive', 'review']:
    bind(REPO / packet[key]['path'], packet[key]['sha256'])
compile_archive = REPO / 'verification/apple-passive-lifecycle-sendable-correction/review-source-package.tar.gz'
bind(compile_archive)
compile_members = {}
with tarfile.open(compile_archive) as archive:
    for member in archive.getmembers():
        if member.isfile():
            compile_members[member.name] = digest(archive.extractfile(member).read())
write('compiled-source-members.json', compile_members)

runtime = SCRATCH / 'oracle-replay'
runtime.mkdir(exist_ok=False)
with tarfile.open(REPO / packet['runtimeArchive']['path']) as archive:
    members = archive.getmembers()
    assert len(members) <= 256
    for member in members:
        name = pathlib.PurePosixPath(member.name)
        assert not name.is_absolute() and '..' not in name.parts
        assert member.isdir() or member.isfile()
        if member.isfile():
            assert member.size < 2_000_000
            target = runtime / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())

commands_before = subprocess.Popen
def forbidden(*args, **kwargs):
    raise AssertionError('Host replay attempted a process or socket')
subprocess.Popen = forbidden
socket.socket = forbidden
try:
    selected = runtime / 'selected'
    verification = selected / 'inputs/runtime/verification'
    oracle_path = verification / 'apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py'
    oracle = load('tab_original_oracle', oracle_path)
    contract = load('tab_original_contract', selected / 'reference_contract.py')
    before_record = read(RAW / 'runtime/captures/0001-before-1.json')
    after_record = read(RAW / 'runtime/captures/0001-after-1.json')
    witness_record = read(RAW / 'runtime/captures/0001-keyboard-witness-1.json')
    before, after = before_record['observation'], after_record['observation']
    witness = witness_record['witness']
    verdict = after_record['verdict']
    premise = read(RAW / 'runtime/attachments/5CEFD571-091C-4D01-AACB-15E58DAF37FC.json')
    pair = {'before': before, 'after': after, 'fileChanged': before_record['signature'] != after_record['signature']}
    replay = contract.result([premise], [verdict], oracle, [pair])
    check('complete original oracle replay exactly matches retained failure', replay['status'] == 'one-original-oracle-result' and not replay['singleTabDiagnosticEvidencePassed'])
    failed = [k for k, v in verdict['predicates'].items() if v is not True]
    check('only actualNativeFocusTraversal fails', failed == ['actualNativeFocusTraversal'])
    forged = copy.deepcopy(verdict)
    forged['predicates']['actualNativeFocusTraversal'] = True
    forged['passed'] = True
    forged['originalOraclePassed'] = True
    rejected = contract.result([premise], [forged], oracle, [pair])
    check('claiming traversal passed cannot override unchanged native evidence', rejected['status'] == 'invalid-or-incomplete-evidence')
    missing = contract.result([premise], [verdict], oracle, [])
    check('missing native observation pair fails closed', missing['status'] == 'invalid-or-incomplete-evidence')
    write('original-oracle-replay.json', replay)
    write('negative-controls.json', {'forgedPass': rejected, 'missingPair': missing})
    contexts = after['focusContexts']
    focus = after['focusSystemDiagnostic']
    lifecycle = after['passiveLifecycleDiagnostic']
    rows = [dict(zip(lifecycle['columns'], row)) for row in lifecycle['entries']]
    start, finish = witness['startedUptime'], witness['finishedUptime']
    in_key = [row for row in focus['entries'] if start <= row['startedUptime'] <= finish]
    check('focus system unavailable then recreated within original key call', [r['system']['state'] for r in in_key] == ['present', 'unavailable', 'present', 'present'])
    final = focus['entries'][-1]
    check('focus system unavailable in final app snapshot', final['system']['state'] == final['scene']['state'] == 'unavailable')
    identities = [r['system']['identity'] for r in in_key if r['system']['identity'] is not None]
    check('focus system recreated with distinct identity', len(set(identities)) == 2)
    tail = [row for row in focus['entries'] if row['startedUptime'] >= start]
    check('every fixed view stays attached and focus eligible in captured transition', all(c['attachedToWindow'] and c['canBecomeFocused'] for row in tail for c in row['controls']))
    life_tail = [row for row in rows if row['systemUptime'] >= start]
    check('app window and scene stay active in captured transition', bool(life_tail) and all(row['applicationState'] == 'active' and row['ownedWindowIsKey'] and row['ownedSceneActivationState'] == 'foreground-active' for row in life_tail))
    check('no focus or lifecycle diagnostic overflow', after['focusContextDropped'] == focus['dropped'] == lifecycle['dropped'] == 0 and not lifecycle['truncated'])
    check('no native callback reaches another fixed control', len(contexts) == 4 and all(c['next']['state'] == 'null' or c['next']['identity'] == contexts[0]['next']['identity'] for c in contexts))
    event = plistlib.loads((RAW / 'runtime/attachments/6E73ADE0-89F2-40F7-A4B8-B7BEB501CBB2').read_bytes())
    objects = event['$objects']
    root = objects[event['$top']['root'].data]
    event_rows = [x for x in objects if isinstance(x, dict) and 'keyModifierFlags' in x]
    check('actual XCTest event targets observed app PID with unmodified Tab', root['targetProcessID'] == rows[0]['processIdentifier'] and len(event_rows) == 1 and objects[event_rows[0]['key'].data] == '\t' and objects[event_rows[0]['keyModifierFlags'].data] == 0)
    timeline = [{'sequence': r['sequence'], 'offsetFromKeyStartSeconds': r['startedUptime'] - start, 'system': r['system'], 'scene': r['scene'], 'controls': r['controls']} for r in tail]
    analysis = {'failedPredicates': failed, 'passedPredicates': [k for k,v in verdict['predicates'].items() if v is True], 'keyDurationSeconds': finish-start, 'primarySampleCompletedAfterKeySeconds': witness['after']['uptime']-finish, 'keyStart': start, 'keyFinish': finish, 'focusTimeline': timeline, 'focusContexts': contexts, 'lifecycleDuringKeyAndFinalSnapshot': life_tail, 'focusFollowUp': read(RAW / 'runtime/captures/0001-focus-diagnostic-1.json'), 'xctestEvent': {'name': objects[root['name'].data], 'targetProcessID': root['targetProcessID'], 'key': '\t', 'modifierFlags': 0}, 'baselineFrontends': previous['baselineFrontends'], 'observedFailureBoundary': 'Scene/window UIFocusSystem availability changes during the key API call; no fixed destination acquired.', 'underlyingCauseProven': False, 'leadingHypothesis': 'Headless simulator keyboard connection/input lifecycle destabilizes focus system; not yet proven.', 'viewEligibilityOverrideJustified': False, 'longerTimeoutJustified': False}
    write('analysis.json', analysis)
    oracle_members = {str(p.relative_to(selected)): digest(p.read_bytes()) for p in verification.rglob('*') if p.is_file() and (p.name.endswith('oracle.py') or p.name == 'cases.json')}
    write('oracle-preservation.json', {'allBytesUnmodified': True, 'runtimeArchiveSHA256': packet['runtimeArchive']['sha256'], 'members': oracle_members, 'exactOriginalFailureReproduced': True, 'syntheticKeyboardCallbackUsed': False, 'productChanges': 0, 'sourceChanges': 0})
finally:
    subprocess.Popen = commands_before
    shutil.rmtree(SCRATCH)
    check('temporary oracle extraction removed', not SCRATCH.exists())

for path, row in bindings.items():
    assert digest(pathlib.Path(path).read_bytes()) == row['sha256'], path
write('input-bindings.json', bindings)
write('host-tests.json', {'passed': True, 'checks': checks, 'count': len(checks), 'command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve())], 'python': sys.version, 'scriptSHA256': digest(pathlib.Path(__file__).read_bytes()), 'sourceRevision': read(HERE / 'environment.json')['head'], 'finishedAtUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'nativeAttempts': 0, 'builds': 0, 'scope': 'Real retained native evidence replay and host assertions only; no new native pass.', 'allBoundInputsUnchanged': True, 'scratch': str(SCRATCH), 'scratchRemoved': not SCRATCH.exists()})
print(json.dumps({'hostChecksPassed': len(checks), 'originalNativeFailurePreserved': failed, 'nativeAttempts': 0, 'builds': 0}))
