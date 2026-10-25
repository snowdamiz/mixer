from pathlib import Path
import datetime, hashlib, json, os

root = Path(__file__).resolve().parents[2]
packet = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()

def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')

def file_entry(path, base=root):
    data = path.read_bytes()
    return {'path': str(path.relative_to(base)), 'sha256': sha(data), 'bytes': len(data)}

def verify(entries):
    for entry in entries:
        data = (root / entry['path']).read_bytes()
        assert sha(data) == entry['sha256'], entry['path']
        assert len(data) == entry['bytes'], entry['path']

def digest(entries):
    return sha(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode())

bindings = json.loads((packet / 'frozen-bindings.json').read_text())
verify(bindings['bindings'])
inherited = json.loads((packet / 'inherited-inputs-verified.json').read_text())
verify(inherited['checks'])
latest = json.loads((packet / 'latest-run.json').read_text())
run = root / latest['run']
assert latest['status'] == 'passed'
report = json.loads((run / 'acceptance-report.json').read_text())
assert report['status'] == 'passed' and report['groupsRun'] == 37 and report['groupsPassed'] == 37
assert all(c['exitCode'] == 0 and c['signal'] is None and c['stdoutEOF'] and c['stderrEOF'] for c in latest['commands'])
source = json.loads((run / 'source-manifest.json').read_text())
for e in source['entries']:
    for base in [packet / 'candidate', run / 'source']:
        assert file_entry(base / e['path'], base) == e
compiled = json.loads((run / 'compiled-manifest.json').read_text())
for e in compiled['entries']:
    for base in [packet / 'candidate/dist', run / 'compiled']:
        assert file_entry(base / e['path'], base) == e
production = []
production_compiled = []
producer = root / 'verification/hosted-worker-pending-migration-outbox'
for subdir, entries in [('src', production), ('dist/src', production_compiled)]:
    base = packet / 'candidate' / subdir
    for path in sorted(base.rglob('*')):
        if path.is_file():
            rel = path.relative_to(base)
            assert path.read_bytes() == (producer / 'candidate' / subdir / rel).read_bytes(), str(rel)
            entries.append(file_entry(path, packet / 'candidate' / ('dist' if subdir == 'dist/src' else '')))
prior = root / 'verification/hosted-worker-pending-migration-history/candidate/src'
current = packet / 'candidate/src'
changes = []
for p in sorted(current.rglob('*')):
    if p.is_file() and p.read_bytes() != (prior / p.relative_to(current)).read_bytes():
        changes.append(str(p.relative_to(current)))
assert changes == ['engine.ts']
old = (prior / 'engine.ts').read_bytes()
new = (current / 'engine.ts').read_bytes()
assert old.replace(b'r.registration_json===null&&r.registry_ack_version', b'r.registration_json===null&&r.track_outbox_json===null&&r.registry_ack_version', 1) == new
closures = {'schema': 1, 'acceptedProducerSourceDigest': '36dd888e47b999cb4a60c2d5f76789f878068a9f04340d86e23d70c917d50f15', 'acceptedProducerCompiledDigest': '281c5fffbb5c78bf58a2d513e29ae1d93e66664615b1caa5987e793856844f14', 'acceptedCandidateClosureSourceDigest': '0536aabfde3db677221ce6ca8acc963e67d2660f71d9583ed45b7ad579f16f2e', 'reviewSourceDigest': source['sourceDigest'], 'reviewCompiledDigest': compiled['compiledDigest'], 'productionSourceDigest': digest(production), 'productionCompiledDigest': digest(production_compiled), 'productionFiles': production, 'productionCompiledFiles': production_compiled, 'productionFilesExactProducerCopies': True, 'productionCompiledExactProducerCopies': True, 'onlyProductionDeltaFromMigrationHistory': 'r.track_outbox_json===null', 'productionImportsRelativeToReviewedSrc': True, 'excludedTestEntryNotImportedByProduction': True, 'fixtureOnlyRPCInstrumentation': True, 'newDependencies': False}
write(packet / 'source-closure.json', closures)
owned = [e for e in report['cleanup'] if 'persist' in e]
restarts = [e for e in report['cleanup'] if e.get('kind') == 'SIGKILL']
assert len(owned) == 37 and len(restarts) == 78
all_pids = set()
for e in owned:
    assert e['disposed'] and e['storageRemoved'] and e['allOwnedPidsAbsent']
    assert not Path(e['persist']).exists()
    all_pids.update(p['pid'] for p in e['ownedProcesses'])
for e in restarts:
    assert e['parentRechecked'] and e['signal'] == 'SIGKILL'
    all_pids.add(e['pid'])
for pid in all_pids:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        pass
    else:
        raise AssertionError('recorded owned PID still exists: ' + str(pid))
cleanup = {'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'ownedStorageEnvironmentsRemoved': len(owned), 'ownedHardRestarts': len(restarts), 'recordedOwnedPIDs': sorted(all_pids), 'allRecordedOwnedPidsAbsent': True, 'allOwnedStorageAbsent': True, 'otherProjectProcessesOrDataChanged': False}
write(packet / 'cleanup-at-seal.json', cleanup)
write(packet / 'inputs-at-seal.json', {'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producerArtifactsVerified': bindings['producerArtifacts'], 'boundInputsVerified': len(bindings['bindings']), 'inheritedFrozenInputsVerified': len(inherited['checks']), 'allMatched': True})
attempts = []
for folder in sorted((packet / 'runs').iterdir()):
    if (folder / 'summary.json').exists():
        attempt = json.loads((folder / 'summary.json').read_text())
        attempts.append({k: v for k, v in attempt.items() if k != 'commands'})
write(packet / 'attempts.json', attempts)
receipt = {'schema': 1, 'status': 'independent-null-outbox-acceptance-review-passed', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'rootProvidedHEAD': 'be472ce6424a691de5673e3438d2768264827d23', 'gitRevisionRead': False, 'producerReceiptSHA256': 'a27b0ce3438705f0bd30ae4dd088f19d4ece3367cb91f78ad42eab8b1413bca1', 'producerSourceDigest': closures['acceptedProducerSourceDigest'], 'producerCompiledDigest': closures['acceptedProducerCompiledDigest'], 'producerCandidateClosureSourceDigest': closures['acceptedCandidateClosureSourceDigest'], 'patchSHA256': '94f76c441b8a86f224dafb43403aa2b83446c089bf0ad823cc3a1c486faff7b3', 'immediateFailedReviewReceiptSHA256': '43992550d3fff245b10e0d019c484f904f24f6de1b4de6bb2645635e0cc3aa06', 'reviewSourceDigest': source['sourceDigest'], 'reviewCompiledDigest': compiled['compiledDigest'], 'productionSourceDigest': closures['productionSourceDigest'], 'productionCompiledDigest': closures['productionCompiledDigest'], 'run': latest['run'], 'groupsRun': report['groupsRun'], 'groupsPassed': report['groupsPassed'], 'actionableFindings': 0, 'acceptedForRootSelectedEngineDevelopmentIntegration': True, 'allFourOriginalGapControlsPass': True, 'schema1And2NullOutboxEnrollmentPasses': True, 'registeredValidOutboxUnchanged': True, 'asyncFinalRowRechecksPass': True, 'producer769RerunForCount': False, 'producerArtifactsVerified': bindings['producerArtifacts'], 'boundInputsVerified': len(bindings['bindings']), 'inheritedFrozenInputBindingsVerified': len(inherited['checks']), 'allFrozenInputsUnchanged': True, 'productionFilesByteIdentical': len(production), 'productionCompiledFilesByteIdentical': len(production_compiled), 'exactOneProductionNullOutboxCondition': True, 'originalFailuresPreserved': True, 'attempts': attempts, 'commands': latest['commands'], 'versions': json.loads((run / 'tool-versions.json').read_text()), 'ownedStorageEnvironmentsRemoved': len(owned), 'ownedHardRestarts': len(restarts), 'allRecordedOwnedPidsAbsent': True, 'allOwnedStorageAbsent': True, 'liveIntegrated': False, 'liveRootSourceChanged': False, 'gitChanged': False, 'publicScheduledEntryQualified': False, 'nativeDeviceRuns': False, 'physicalPhonesDisconnectedDeferred': True, 'forbiddenFrozenLanesReadImportedExecuted': False, 'providerDeploymentCredentialCustomerPublicationChanges': False, 'remoteRollbackCancellationClaimed': False, 'gaAccepted': False, 'limitations': ['finite local actual-workerd SQLite tests with synthetic clock/provider only', 'cumulative Engine development acceptance relies on retained previous independent reviews and this narrow correction review', 'no live Engine or entry integration; public/scheduled entry remains separate', 'no fresh producer769 or live controller71/process20 suite rerun', 'no production provider/clock, deployed alarms/restore/fleet/capacity qualification', 'immutable published-package FieldLog, signing/store, final physical phones and accountable GA acceptance pending', 'migration-consistent shape is not historical provenance or execution authority', 'explicit async registration RPC may have committed remotely before final local rejection; no remote rollback or distributed atomicity claim']}
artifacts = [file_entry(p) for p in sorted(packet.rglob('*')) if p.is_file() and p.name != 'receipt.json']
artifacts.append(file_entry(root / 'docs/hosted-worker-pending-migration-outbox-review.md'))
receipt['artifacts'] = artifacts
write(packet / 'receipt.json', receipt)
print(json.dumps({'status': receipt['status'], 'groupsRun': receipt['groupsRun'], 'groupsPassed': receipt['groupsPassed'], 'artifacts': len(artifacts), 'receiptSHA256': sha((packet / 'receipt.json').read_bytes()), 'productionSourceDigest': closures['productionSourceDigest'], 'productionCompiledDigest': closures['productionCompiledDigest']}, indent=2))
