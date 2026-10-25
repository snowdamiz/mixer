"""Offline analysis of retained evidence; executes only the exact pure oracle closure."""
import copy
import datetime
import hashlib
import importlib.util
import json
import pathlib
import platform
import sys
import tarfile
import tempfile

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
INPUT = ROOT / 'verification/apple-focus-diagnostic-runtime-v1'
RUNTIME = INPUT / 'runtime'
EXPECTED_PACKET = 'd7c4c0f146434eeb7323036809acb5b4a80d41ff10f596eed8c25bdaa314e783'
ORACLES = [
    'apple-toggle-keyboard-focus-v9-preparation/keyboard_oracle.py',
    'apple-toggle-keyboard-focus/keyboard_oracle.py',
    'apple-toggle-keyboard-focus/cases.json',
    'apple-toggle-pan-commit-harness-v2/commit_oracle.py',
    'apple-toggle-pan-commit-harness-v2/cases.json',
    'apple-toggle-native-interruption/interruption_oracle.py',
    'apple-toggle-native-interruption/cases.json',
    'apple-toggle-pan-origin-correction/oracle.py',
    'apple-toggle-semantic-activation/semantic_oracle.py',
]
INPUTS = [
    'packet.json', 'host-receipt.json', 'output-manifest.json', 'selected-runtime-source-manifest.json',
    'selected-runtime-sources.tar.gz', 'runtime/runtime-verdict.json',
    'runtime/lifecycle.json', 'runtime/commands.json', 'runtime/xctest-summary.json',
    'runtime/xctest-tests.json', 'runtime/session/command-observer/observer.json',
    'runtime/captures/0001-before-1.json', 'runtime/captures/0001-after-1.json',
    'runtime/captures/0001-keyboard-witness-1.json',
    'runtime/captures/0001-focus-diagnostic-1.json',
    'runtime/captures/0001-command-1.json', 'runtime/captures/0001-command-2.json',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(rel):
    return json.loads((INPUT / rel).read_bytes())


def write(name, data):
    (BASE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def cursor_state(cursor):
    return {k: copy.deepcopy(getattr(cursor, k)) for k in (
        'done_commands', 'acquired', 'acquisitions', 'phase_index',
        'complete', 'failed', 'last_after', 'native_metadata')}


checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


input_hashes = {name: sha(INPUT / name) for name in INPUTS}
check('exact selected packet identity', input_hashes['packet.json'] == EXPECTED_PACKET)
packet = read('packet.json')
manifest = read('selected-runtime-source-manifest.json')
check('accepted source manifest bound by packet', input_hashes['output-manifest.json'] == packet['outputManifestSHA256'])
accepted_sources = read('output-manifest.json')['acceptedSources']
source_excerpts = json.loads((BASE / 'source-excerpts.json').read_bytes())
for row in source_excerpts['sources']:
    name = row['retainedSourcePath'].split('/scratch/accepted/', 1)[1]
    check('source excerpt full-file hash matches accepted manifest: ' + name,
          row['sha256'] == accepted_sources[name]['sha256'])
check('archive manifest bound by packet', input_hashes['selected-runtime-source-manifest.json'] == packet['selectedSourceArchiveManifestSHA256'])
check('source archive bound by packet and manifest', input_hashes['selected-runtime-sources.tar.gz'] == packet['selectedSourceArchive']['sha256'] == manifest['archive']['sha256'])

# Only these six Python oracle modules and three JSON case files are extracted.
# The closure was read before execution: it uses stdlib imports, pure predicates
# and case JSON. No selected orchestration, hosted authority or catalog is loaded.
oracle_hashes = {}
with tempfile.TemporaryDirectory(prefix='oracle-', dir=BASE) as temporary:
    selected = pathlib.Path(temporary)
    with tarfile.open(INPUT / 'selected-runtime-sources.tar.gz', 'r:gz') as archive:
        for rel in ORACLES:
            name = 'inputs/runtime/verification/' + rel
            member = archive.getmember('selected/' + name)
            check('regular oracle member: ' + rel, member.isfile())
            data = archive.extractfile(member).read()
            digest = hashlib.sha256(data).hexdigest()
            check('unchanged oracle bytes: ' + rel, digest == manifest['files'][name]['sha256'])
            oracle_hashes[name] = digest
            target = selected / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    spec = importlib.util.spec_from_file_location('retained_focus_oracle', selected / 'inputs/runtime/verification' / ORACLES[0])
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    baseline = read('runtime/captures/0001-before-1.json')
    after = read('runtime/captures/0001-after-1.json')
    retained = read('runtime/captures/0001-keyboard-witness-1.json')
    before_observation = copy.deepcopy(baseline['observation'])
    before_observation.update(keyboardWitness=retained['witness'], keyboardBinding=retained['binding'])
    changed = baseline['signature'] != after['signature']
    verdict = oracle.verdict('diagnostic', 'keyboard-enabled-off', 'native-keyboard',
                             before_observation, after['observation'], changed)
    recorded = copy.deepcopy(after['verdict'])
    check('bridge reporting identity agrees with retained witness', all(recorded[k] == retained['binding'][k] for k in ['generation', 'actionIndex']))
    # These three reporting fields are added outside the pure oracle.
    for field in ['ownedSimulatorIdentity', 'generation', 'actionIndex']:
        recorded.pop(field)
    if verdict != recorded:
        print(json.dumps({'replayDifference': {k: {'replayed': verdict.get(k), 'recorded': recorded.get(k)}
                                             for k in set(verdict) | set(recorded) if verdict.get(k) != recorded.get(k)}}, sort_keys=True))
    check('unchanged oracle reproduces entire retained oracle verdict', verdict == recorded)
    check('sole false predicate remains actualNativeFocusTraversal', [k for k, v in verdict['predicates'].items() if v is not True] == ['actualNativeFocusTraversal'])
    cursor = oracle.Cursor('keyboard-enabled-off')
    for index in (1, 2):
        cursor.command(read(f'runtime/captures/0001-command-{index}.json')['command'])
    oracle.witness(retained['witness'], retained['binding'])
    cursor.check(retained['witness'])
    cursor_before = cursor_state(cursor)
    # Identical fail-closed branch from the retained keyboard_bridge.py. No
    # advance is called for this failed verdict; no native action is repeated.
    if verdict['passed'] is True:
        cursor.advance(retained['witness'])
    else:
        cursor.failed = True
    cursor_after = cursor_state(cursor)
    check('failed verdict leaves cursor progression unchanged', all(cursor_before[k] == cursor_after[k] for k in cursor_before if k != 'failed') and cursor_after['failed'] is True)

witness = retained['witness']
diagnostic = read('runtime/captures/0001-focus-diagnostic-1.json')
observation = after['observation']
contexts = observation['focusContexts']
previous_contexts = baseline['observation']['focusContexts']
check('complete focus context trace preserves prefix', contexts[:len(previous_contexts)] == previous_contexts and observation['focusContextDropped'] == 0 and [c['sequence'] for c in contexts] == list(range(1, 9)))
concrete = [e for c in contexts for e in [c['previous'], c['next']] if e['state'] == 'item']
check('only concrete traced endpoint is the same attached carrier', all(e['class'] == 'AuthoredToggleCarrier' and e['identity'] == observation['state']['identity'] and e['attachedToWindow'] is True for e in concrete))
check('all replacement endpoints are explicit null or same carrier', all(e['state'] in ['null', 'item'] for c in contexts for e in [c['previous'], c['next']]))
check('follow-up is complete and all three fixed focus reads false', diagnostic['followUp']['captureStatus'] == 'complete' and [r['identifier'] for r in diagnostic['followUp']['rows']] == list(oracle.IDS) and all(r['hasFocus'] is False for r in diagnostic['followUp']['rows']))
check('paired app and authoritative AX focus agree before and after', verdict['predicates']['pairedNativeFocusBefore'] and verdict['predicates']['pairedNativeFocusAfter'])
runtime_verdict = read('runtime/runtime-verdict.json')
lifecycle = read('runtime/lifecycle.json')
observer = read('runtime/session/command-observer/observer.json')
xctest = read('runtime/xctest-summary.json')
check('official result is two methods with one pass and one fail', (xctest['totalTestCount'], xctest['passedTests'], xctest['failedTests'], xctest['result']) == (2, 1, 1, 'Failed'))
check('observer reached exit and both EOFs without surviving owned group', observer['outcome'] == 'command-exited-and-streams-EOF' and observer['exitCode'] == 65 and all(s['eof'] for s in observer['streams'].values()) and observer['ownedProcessGroup']['state'] == 'absent')
check('retained cleanup reports all five resources passed and owned device absent', len(lifecycle['cleanupResults']) == 5 and all(r['passed'] is True for r in lifecycle['cleanupResults']) and lifecycle['ownedDeviceAbsent'] and lifecycle['baselineStatesPreserved'] and lifecycle['secretConfigurationAbsent'])
check('read input evidence unchanged during offline analysis', all(sha(INPUT / n) == h for n, h in input_hashes.items()))

focus_events = [{'sequence': e['sequence'], 'uptime': e['uptime'], 'focused': e['state']['focused']}
                for e in observation['events'] if e['reason'] == 'focus']
summary = {
    'schema': 'mixer.apple-focus-diagnostic-v1-analysis.1',
    'packetSHA256': EXPECTED_PACKET,
    'strictReplay': {'passed': verdict['passed'], 'matchesRetainedVerdict': True,
                     'falsePredicates': ['actualNativeFocusTraversal'],
                     'cursorBefore': cursor_before, 'cursorAfter': cursor_after},
    'key': {k: witness[k] for k in ['phase', 'key', 'startedUptime', 'finishedUptime']},
    'keyDurationMilliseconds': (witness['finishedUptime'] - witness['startedUptime']) * 1000,
    'authoritativeAX': {'before': witness['before'], 'after': witness['after']},
    'nonAuthoritativeTimedDiagnostic': diagnostic,
    'focusOnlyDurationMilliseconds': (diagnostic['followUp']['finishedUptime'] - diagnostic['followUp']['startedUptime']) * 1000,
    'focusContexts': contexts, 'focusEvents': focus_events,
    'newContextSequencesDuringKey': [c['sequence'] for c in contexts[len(previous_contexts):]
                                    if witness['startedUptime'] <= c['uptime'] <= witness['finishedUptime']],
    'retainedOutcome': {'xcodebuildExitCode': runtime_verdict['xcodebuildExitCode'],
                        'commandElapsedSeconds': observer['elapsedSeconds'],
                        'officialMethodCount': xctest['totalTestCount'],
                        'officialPassedCount': xctest['passedTests'], 'officialFailedCount': xctest['failedTests'],
                        'ownedSimulator': lifecycle['ownedSimulator'], 'runtime': {k: lifecycle['runtime'][k] for k in ['identifier', 'version', 'buildversion']},
                        'cleanupResults': lifecycle['cleanupResults'], 'ownedDeviceAbsent': lifecycle['ownedDeviceAbsent'],
                        'baselineStatesPreserved': lifecycle['baselineStatesPreserved']},
    'limitations': ['Offline replay is host analysis, not new native execution.',
                    'Sequential fixed AX reads are not an atomic or continuous focus observation.',
                    'Explicit null focus endpoints do not identify an off-scope destination or root cause.',
                    'One selected simulator diagnostic does not qualify physical phones, six cases, carrier, comparator, FieldLog, signing, store, operational or GA gates.'],
}
write('summary.json', summary)
receipt = {
    'schema': 'mixer.apple-focus-diagnostic-v1-offline-receipt.1',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': [sys.executable, '-I', '-B', str(BASE / 'reanalyze.py')],
    'python': sys.version, 'platform': platform.platform(),
    'sourceRevisionLabel': packet['sourceRevisionLabel'],
    'sourceRevisionMeaning': packet['sourceRevisionMeaning'],
    'selectedRuntimeSourceTreeSHA256': manifest['treeSHA256'],
    'scriptSHA256': sha(BASE / 'reanalyze.py'), 'inputSHA256': input_hashes,
    'executedOracleSHA256': oracle_hashes, 'checksPassed': checks,
    'passed': True, 'nativeExecuted': False, 'nativeInstancesQueried': False,
    'serviceStarted': False, 'uiOrCaptureOperation': False, 'gitOperation': False,
    'physicalPhones': 'disconnected-deferred', 'oracleChanged': False,
    'authorityOrCatalogExecuted': False, 'scratchOracleExtractionRemoved': True,
    'outputs': {'summary.json': sha(BASE / 'summary.json'),
                'source-excerpts.json': sha(BASE / 'source-excerpts.json')},
    'scope': 'Read retained diagnostic and replay its exact unchanged pure host oracle. Does not seal or accept the native aggregate.',
}
write('receipt.json', receipt)
print(json.dumps({'passed': True, 'checks': len(checks), 'strictNativeVerdictPassed': False,
                  'soleFalsePredicate': 'actualNativeFocusTraversal', 'summarySHA256': sha(BASE / 'summary.json')}, sort_keys=True))
