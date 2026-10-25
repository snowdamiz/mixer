"""Collect only the bound offline Settings timeout evidence; no native or UI calls."""
import collections
import datetime
import hashlib
import io
import json
import pathlib
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
NATIVE = ROOT / 'verification/apple-focus-reference-v5-native'
CORRECTION = ROOT / 'verification/apple-focus-reference-runtime-v5-namespace-correction'
ORIGINAL = ROOT / 'verification/apple-focus-reference-runtime-v5'
EXPECTED_HANDOFF = 'bc226729d7133f33b52d98a4fd7446771bae7bc6c5672455927bbe343c723927'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stable(value):
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'


def main():
    inputs = {}

    def read(path, expected=None):
        data = path.read_bytes()
        if expected is not None:
            assert sha(data) == expected, str(path)
        inputs[str(path.relative_to(ROOT))] = {'bytes': len(data), 'sha256': sha(data)}
        return data

    handoff = json.loads(read(NATIVE / 'handoff.json', EXPECTED_HANDOFF))
    native_manifest_path = NATIVE / 'native-output-manifest.json'
    manifest = json.loads(read(native_manifest_path, handoff['members'][str(native_manifest_path.relative_to(ROOT))]['sha256']))
    raw_root = pathlib.Path(manifest['root'])
    assert raw_root == CORRECTION / 'native-run-v5-e7108fc8-281b-4c59-831a-f3697609017d'
    read(ROOT / 'verification/apple-focus-reference-v5-root-selection/result-binding.json')
    read(ROOT / 'AGENTS.md')
    doc = ROOT / 'docs/apple-focus-reference-v5-native.md'
    read(doc, handoff['members'][str(doc.relative_to(ROOT))]['sha256'])
    for name in ['result.json', 'official-failure-explanation.json']:
        path = NATIVE / name
        read(path, handoff['members'][str(path.relative_to(ROOT))]['sha256'])

    runtime_manifest = json.loads(read(CORRECTION / 'runtime-source-manifest.json',
        handoff['inputBindings']['verification/apple-focus-reference-runtime-v5-namespace-correction/runtime-source-manifest.json']['sha256']))
    runtime_blob = read(CORRECTION / 'runtime-sources.tar.gz', runtime_manifest['archive']['sha256'])
    frozen_blob = read(ORIGINAL / 'frozen-inputs.tar.gz', '3b509aadf2b31314ec9fd910acb4fe3b3040505a446fff8f691bf765a599da7e')
    original_packet = json.loads(read(ORIGINAL / 'packet.json',
        handoff['inputBindings']['verification/apple-focus-reference-runtime-v5/packet.json']['sha256']))
    assert original_packet['sourceTreeSHA256'] == handoff['compileSourceTreeSHA256']
    with tarfile.open(fileobj=io.BytesIO(frozen_blob)) as archive:
        accepted = archive.extractfile('verification/apple-focus-reference-diagnostic-v1/accepted-sources.tar.gz').read()
    assert sha(accepted) == 'c1e59b3e950acfe4afa46ae69e8eed29e6c8e1816e1d845e1c40548833201294'

    scratch = BASE / 'scratch'
    scratch.mkdir(exist_ok=True)
    sources = []
    selections = [
        ('inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/durable_settings.py', 'durable_settings.py'),
        ('inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py', 'settings_telemetry.py'),
        ('inputs/runtime/verification/apple-toggle-pan-origin-correction/bridge.py', 'bridge.py'),
        ('inputs/runtime/verification/apple-toggle-pan-origin-correction/harness.py', 'harness.py'),
        ('inputs/runtime/verification/apple-toggle-keyboard-focus/run.py', 'run.py'),
        ('join_support.py', 'join_support.py'), ('composition.py', 'composition.py'),
        ('runtime_bindings.py', 'runtime_bindings.py')]
    with tarfile.open(fileobj=io.BytesIO(runtime_blob)) as archive:
        for name, dest in selections:
            data = archive.extractfile('selected/' + name).read()
            assert len(data) == runtime_manifest['files'][name]['bytes']
            assert sha(data) == runtime_manifest['files'][name]['sha256']
            (scratch / dest).write_bytes(data)
            sources.append({'archive': str((CORRECTION / 'runtime-sources.tar.gz').relative_to(ROOT)),
                            'archiveSHA256': sha(runtime_blob), 'member': 'selected/' + name,
                            'bytes': len(data), 'sha256': sha(data), 'scratchName': dest})
    with tarfile.open(fileobj=io.BytesIO(accepted)) as archive:
        for name, expected in [
            ('DiagnosticTransport.swift', '7714d426ef268aeae9b7f24340e87dba269348a28e20979318df58c50aa4415c'),
            ('ToggleUITests.swift', '84427c20443b2dae064ab9ab9874aa17c514ec89b925c0c80d9cb2b03b5a3acf')]:
            member = 'accepted/harness/UITests/' + name
            data = archive.extractfile(member).read()
            assert sha(data) == expected
            (scratch / name).write_bytes(data)
            sources.append({'archive': 'verification/apple-focus-reference-runtime-v5/frozen-inputs.tar.gz!verification/apple-focus-reference-diagnostic-v1/accepted-sources.tar.gz',
                            'archiveSHA256': sha(accepted), 'member': member,
                            'bytes': len(data), 'sha256': sha(data), 'scratchName': name})
    (BASE / 'source-bindings.json').write_text(stable({'schema': 1, 'sources': sources,
        'scratchRetention': 'Exact selected members only; removed after host controls and inspection.'}))

    for name in ['runtime/session/command-observer/stdout.log', 'runtime/session/command-observer/stderr.log',
                 'runtime/captures/bridge-summary.json', 'runtime/xctest-tests.json', 'runtime/xctest-summary.json']:
        read(raw_root / name, manifest['selectedFiles'][name]['sha256'])
    log_lines = (raw_root / 'runtime/session/command-observer/stdout.log').read_text().splitlines()
    excerpts = [{'line': i, 'text': line} for i, line in enumerate(log_lines, 1)
                if any(x in line for x in ['Task <', 'first setup error', 'terminal evidence incomplete',
                                            'MIXER_SETTINGS_DIAGNOSTIC_UNAVAILABLE'])]
    captures = raw_root / 'runtime/captures'
    journals = sorted(captures.glob('0000-settings-*.json'))
    assert len(journals) == 221
    rows = [json.loads(read(path)) for path in journals]
    assert [row['record'].get('sequence', 0) for row in rows] == list(range(221))
    start = rows[0]['record']['uptime']
    timeline = []
    for row in rows:
        record = row['record']
        if record['kind'] != 'chunk' or record.get('sequence', 0) >= 191:
            reduced = {k: v for k, v in record.items()
                       if k not in ['data', 'routeWitness', 'switchWitness', 'snapshot', 'detail']}
            reduced['elapsedFromRunnerStartSeconds'] = record['uptime'] - start
            reduced['upperBoundRemainingBeforePostSeconds'] = start + 29.0 - record['uptime']
            reduced['receivedUptime'] = row['receivedUptime']
            timeline.append(reduced)
    outcomes = sorted((captures / '.settings-attempts').glob('*/outcome.json'))
    assert len(outcomes) == 221
    outcome_rows = [json.loads(read(path)) for path in outcomes]
    assert all(row['outcome'] == 'committed' for row in outcome_rows)
    assert {row['journal'] for row in outcome_rows} == {path.name for path in journals}
    assert all(row['retirement']['state'] == 'resolved' for row in outcome_rows)
    assert all(row['ancillary'] == [] for row in outcome_rows)
    assert not (captures / '.settings-transaction-guard.json').exists()
    findings = {
        'schema': 1, 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve())],
        'python': sys.version, 'sourceRevisionLabel': handoff['sourceRevisionLabel'],
        'sourceRevisionMeaning': handoff['sourceRevisionMeaning'], 'nativeHandoffSHA256': EXPECTED_HANDOFF,
        'compileSourceTreeSHA256': handoff['compileSourceTreeSHA256'],
        'runtimeSourceTreeSHA256': runtime_manifest['treeSHA256'],
        'nativeProductArchiveSHA256': handoff['nativeProductArchiveSHA256'],
        'nativeOutputRoot': str(raw_root), 'nativeOutputTreeSHA256': manifest['fullTreeSHA256'],
        'nativeTreeVerificationScope': 'Inherited root verification of all 2455 files; this collection reads only the bound files in evidence-bindings.json.',
        'observedKinds': dict(collections.Counter(row['record']['kind'] for row in rows)),
        'durableSettingsJournalCount': len(rows), 'durableAttemptOutcomeCount': len(outcomes),
        'allOutcomesCommitted': True, 'allCommittedRetirementsResolved': True, 'transactionGuardAbsent': True,
        'runnerStartUptime': start, 'fixedClientDeadlineUptime': start + 29.0,
        'terminalObserveSequence': 195,
        'terminalObserveUpperBoundRemainingSeconds': start + 29.0 - rows[195]['record']['uptime'],
        'lastCommittedSequence': 220,
        'lastCommittedUpperBoundRemainingSeconds': start + 29.0 - rows[220]['record']['uptime'],
        'timedOutBridgeRequestID': None,
        'timedOutRequestIdentityLimitation': 'URLSession task 221 is not an explicit bridge sequence binding. Last committed journal does not identify the timeout.',
        'failureExcerpts': excerpts, 'timeline': timeline,
        'nativeRunsStarted': 0, 'nativeUIOrDeviceQueries': 0, 'budgetChanges': 0,
        'productOrFrozenSourceEdits': 0, 'gitCommands': 0, 'sharedTrackerEdits': 0,
        'importerCorrectionJustified': False, 'nativePassCredited': False, 'gaAccepted': False,
        'physicalPhones': 'disconnected-deferred',
        'nextStep': 'Minimal first-failure client instrumentation with exact bridge identity and actual remaining budget; preserve the current bounds and failure latch. Server phase spans only if latency attribution is needed.'}
    (BASE / 'findings.json').write_text(stable(findings))
    (BASE / 'evidence-bindings.json').write_text(stable({'schema': 1, 'files': inputs}))
    print(json.dumps({k: findings[k] for k in ['durableSettingsJournalCount', 'allOutcomesCommitted',
        'terminalObserveUpperBoundRemainingSeconds', 'lastCommittedUpperBoundRemainingSeconds', 'timedOutBridgeRequestID']}))


if __name__ == '__main__':
    main()
