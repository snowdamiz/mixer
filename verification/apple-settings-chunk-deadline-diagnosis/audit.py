"""Bound, offline inspection of one selected failure; never a runtime producer."""
import base64
import decimal
import hashlib
import importlib.util
import json
import pathlib
import stat
import sys
import tarfile

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
RUN = ROOT / 'verification/apple-settings-instrumented-runtime-preparation/native-run-v6-4c0ed51e-8060-4646-83a5-873b875d4d30'
NATIVE = ROOT / 'verification/apple-settings-instrumented-native'
EXPECTED_HANDOFF = '3e068b73e1a5ee88227657f0708477e6e1feb3a99d20cfb95c0c9ca0e2339a53'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def checked(path, row):
    assert path.resolve() == path and path.is_file() and not path.is_symlink(), str(path)
    raw = path.read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], str(path)
    assert stat.S_IMODE(path.stat().st_mode) == row['mode'], str(path)
    return raw


def main():
    handoff_path = NATIVE / 'handoff.json'
    assert sha(handoff_path.read_bytes()) == EXPECTED_HANDOFF
    handoff = read(handoff_path)
    assert len(handoff['members']) == 48
    for name, row in handoff['members'].items():
        assert not any(word in name for word in ['catalog-inspector', 'authority-driver', 'transportV2'])
        checked(ROOT / name, row)
    manifest_path = NATIVE / 'result/native-files.json'
    manifest = read(manifest_path)
    receipt = read(NATIVE / 'result/receipt.json')
    assert sha(manifest_path.read_bytes()) == receipt['nativeManifestSHA256']
    assert len(manifest) == receipt['nativeFiles'] == 2257
    for name, row in manifest.items():
        assert name.startswith(str(RUN.relative_to(ROOT)) + '/')
        checked(ROOT / name, row)
    assert sum(row['bytes'] for row in manifest.values()) == receipt['nativeFileBytes']

    runtime_path = ROOT / 'verification/apple-settings-instrumented-runtime-preparation/runtime-sources.tar.gz'
    runtime_manifest = read(runtime_path.with_name('runtime-source-manifest.json'))
    checked(runtime_path, runtime_manifest['archive'])
    archive_bindings = {}
    for path, prefix, count, expected in [
        (runtime_path, 'selected/', 32, '765bd6b2caf703a65bf2f7d91e716f65c7b6cee6091a530e5106a96835dab13c'),
        (ROOT / 'verification/apple-settings-instrumented-native-build/attempt-1/accepted-sources.tar.gz', 'accepted/', 40, '82b88c3ee0d55b3cf10930904f0f2eaed6d44b368659c9b2665f58cd28e764a9'),
    ]:
        assert sha(path.read_bytes()) == expected
        with tarfile.open(path) as archive:
            files = [m for m in archive.getmembers() if m.isfile()]
            assert len(files) == count and all(m.name.startswith(prefix) and '..' not in pathlib.PurePosixPath(m.name).parts for m in files)
            archive_bindings[str(path.relative_to(ROOT))] = {'sha256': expected, 'files': count}
            for member in files:
                raw = archive.extractfile(member).read()
                if prefix == 'selected/':
                    row = runtime_manifest['files'][member.name[len(prefix):]]
                    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
                snapshot = BASE / 'sources' / member.name
                if snapshot.exists():
                    assert snapshot.read_bytes() == raw

    # Only the selected strict setup Session is imported. Persistence is replaced
    # by collection callbacks; its original validator/reassembly is unchanged.
    source = BASE / 'sources/selected/inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'
    spec = importlib.util.spec_from_file_location('bounded_selected_settings_session', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    captures = RUN / 'runtime/captures'
    journals = sorted(captures.glob('0000-settings-*.json'))
    values = [read(path) for path in journals]
    assert len(values) == 166
    assert [v['record'].get('sequence', 0) for v in values] == list(range(166))
    clock = [values[0]['receivedUptime']]
    files = []
    replayed = []
    session = module.Session(lambda suffix, value: replayed.append((suffix, value)), lambda slot, form, payload: files.append((slot, form, payload)), values[0]['sessionDeadlineUptime'], now=lambda: clock[0], token=values[0]['generation'])
    for path, value in zip(journals, values):
        clock[0] = value['receivedUptime']
        session.request(value['record'])
        assert replayed[-1] == (path.stem[5:], {k: v for k, v in value.items() if k != 'ownedSimulatorIdentity'})
    for slot, form, payload in files:
        target = captures / (slot + ('.png' if form == 'png' else '.txt'))
        assert target.read_bytes() == payload
    summary = session.summary()
    assert summary['settingsEvidenceComplete'] is False and summary['setupObservationSatisfied'] is False
    assert session.before['sequence'] == 46 and session.after['sequence'] == 118 and session.terminal is None
    assert summary['pendingSlots'] == ['settings-0118-png']
    assert len(session.uploads['settings-0118-png']['parts']) == 43
    outcomes = []
    for path in sorted((captures / '.settings-attempts').glob('*/outcome.json')):
        value = read(path)
        assert value['outcome'] == 'committed' and value['retirement']['state'] == 'resolved' and value['ancillary'] == []
        outcomes.append(value)
    assert len(outcomes) == len(values) and not (captures / '.settings-transaction-guard.json').exists()

    failure_path = RUN / 'runtime/session/local-settings-first-failure.json'
    local = read(failure_path)
    failure = local['diagnostic']['record']
    assert failure == receipt['supplementalFirstFailure']
    last = values[-1]['record']
    assert all(failure[k] == last[v] for k, v in [('generation', 'generation'), ('sequence', 'sequence'), ('kind', 'kind'), ('slot', 'slot'), ('chunkIndex', 'index'), ('chunkCount', 'count')])
    assert failure['requestOrdinal'] == failure['sequence'] + 1 == 166
    assert failure['absoluteDeadlineUptime'] - failure['beginUptime'] == failure['actualAllowanceSeconds']
    assert failure['branch'] == 'semaphore-expiration' and failure['overallDeadlineClipped'] is True
    stdout_path = RUN / 'runtime/session/command-observer/stdout.log'
    loglines = stdout_path.read_text().splitlines()
    matching = [(i, line) for i, line in enumerate(loglines, 1) if line.startswith('MIXER_SETTINGS_FIRST_FAILURE ')]
    assert len(matching) == 1 and json.loads(matching[0][1].split(' ', 1)[1]) == failure

    start = values[0]['record']['uptime']
    timeline = []
    counterfactual_counts = []
    for value in values:
        record = value['record']
        if record['kind'] != 'chunk':
            timeline.append({'sequence': record.get('sequence', 0), 'kind': record['kind'], 'stage': record.get('stage'), 'clientSecondsSinceStart': record['uptime'] - start, 'initialDeadlineRemainingUpperBoundSeconds': start + 29 - record['uptime'], 'captureDurationSeconds': record['captureFinishedUptime'] - record['captureStartedUptime'] if 'captureStartedUptime' in record else None})
        if record['kind'] == 'observe':
            for form, descriptor in record['files'].items():
                counterfactual_counts.append({'observationSequence': record['sequence'], 'stage': record['stage'], 'format': form, 'bytes': descriptor['bytes'], 'sha256': descriptor['sha256'], 'current3072Chunks': (descriptor['bytes'] + 3071)//3072, 'alternative4096Chunks': (descriptor['bytes'] + 4095)//4096, 'proposed4992Chunks': (descriptor['bytes'] + 4991)//4992})
    # Exact available complete native files plus finite explicit edge payloads.
    controls = []
    payloads = [(slot, payload) for slot, _, payload in files]
    payloads += [('edge-' + str(n), bytes([255]) * n) for n in [1, 4095, 4096, 4097, 4991, 4992, 4993, 200_000, 2_000_000]]
    for chunk_size in [4096, 4992]:
        for name, payload in payloads:
            parts = [payload[i:i+chunk_size] for i in range(0, len(payload), chunk_size)]
            assert all(0 < len(part) <= chunk_size for part in parts)
            assert len(parts) == (len(payload) + chunk_size - 1)//chunk_size
            assert b''.join(parts) == payload and sha(b''.join(parts)) == sha(payload)
            assert all(base64.b64decode(base64.b64encode(part), validate=True) == part for part in parts)
            controls.append({'chunkSize': chunk_size, 'name': name, 'bytes': len(payload), 'parts': len(parts), 'lastBytes': len(parts[-1]), 'identityUnchanged': True})
    # This is only evidence that the old protocol is incompatible; no new
    # receiver is implemented or credited by these controls.
    before_png = next(payload for slot, form, payload in files if slot == 'settings-0046-png')
    expected_old = session.uploads['settings-0046-png']['count']
    expected_new = (len(before_png) + 4991)//4992
    assert expected_old == 66 and expected_new == 41 and expected_old != expected_new
    # Conservative mathematical decimal ceiling, not a claim about Foundation's
    # exhaustive shortest/round-trip formatting behavior. No admission guard.
    envelope = {'settingsDiagnostic': {'kind': 'chunk', 'case': module.CASE,
        'generation': 'ffffffff-ffff-ffff-ffff-ffffffffffff', 'sequence': 2500,
        'uptime': 0, 'slot': 'settings-2500-png', 'index': 488, 'count': 489,
        'bytes': 2_000_000, 'sha256': 'f' * 64, 'data': ''}}
    serialized = json.dumps(envelope, sort_keys=True, separators=(',', ':')).encode()
    fixed_envelope = len(serialized) - 1  # Replace the single uptime token 0.
    assert fixed_envelope == 316
    with decimal.localcontext() as context:
        context.prec = 1100
        exact_minimum_token = format(decimal.Decimal(2) ** -1074, 'f')
    assert len(exact_minimum_token) == 1076
    metadata_ceiling = fixed_envelope + len(exact_minimum_token)
    assert metadata_ceiling == 1392
    assert 4 * ((4096 + 2)//3) + metadata_ceiling == 6856 <= 8192
    assert 4 * ((4992 + 2)//3) + metadata_ceiling == 8048 <= 8192
    assert 4 * ((5120 + 2)//3) + metadata_ceiling == 8220 > 8192
    report = {
        'schema': 1, 'scope': 'One exact selected offline failure diagnosis and proposed wire-packing arithmetic; no implementation acceptance',
        'nativeHandoffSHA256': EXPECTED_HANDOFF, 'compactMembersVerified': 48, 'nativeFilesVerified': len(manifest), 'nativeBytesVerified': sum(row['bytes'] for row in manifest.values()),
        'sourceRevisionLabel': receipt['sourceRevisionLabel'], 'sourceTreeSHA256': receipt['sourceTreeSHA256'], 'archives': archive_bindings,
        'nativeManifestSHA256': sha(manifest_path.read_bytes()), 'rawDiagnosticLogLine': matching[0][0], 'supplementalFirstFailure': failure,
        'committedJournalRecords': len(values), 'committedResolvedAttemptOutcomes': len(outcomes), 'strictOriginalSessionPrefixReplayed': True,
        'replayedSummary': summary, 'timeline': timeline, 'declaredPayloadChunkCounts': counterfactual_counts,
        'finiteSplitReassemblyControls': controls, 'oldFormatIncompatibility': {'beforePNG3072Count': expected_old, 'proposed4992Count': expected_new, 'unversionedMixedEndpointsSafe': False},
        'conservativeBodyAccounting': {'fixedEnvelopeExcludingUptimeAndDataBytes': fixed_envelope,
            'binary64ExactFixedDecimalTokenCeiling': len(exact_minimum_token),
            'metadataCeilingBytes': metadata_ceiling, 'proposed4096Base64CeilingBytes': 5464,
            'proposed4096ConservativeBodyCeilingBytes': 6856,
            'proposed4992Base64CeilingBytes': 6656,
            'proposed4992ConservativeBodyCeilingBytes': 8048,
            'proposed4992MaximumPNGCount': 401, 'proposed4992MaximumPNGIndex': 400,
            'proposed4992MaximumAXCount': 41,
            'candidate5120ConservativeBodyCeilingBytes': 8220,
            'newMetadataAdmissionRestrictionProposed': False,
            'foundationAllFiniteDoubleFormattingMaximumProven': False},
        'observedFailureElapsedSeconds': failure['endUptime'] - failure['beginUptime'], 'observedFailureEndPastAbsoluteDeadlineSeconds': failure['endUptime'] - failure['absoluteDeadlineUptime'],
        'allCleanupOperationsPassed': receipt['cleanupOperationsPassed'] == 5, 'ownedSimulatorAbsentFromBoundReceipt': receipt['ownedSimulatorAbsent'],
        'strictImporterFailure': receipt['strictImporterReportingFailures'], 'physicalPhones': 'disconnected-deferred',
        'nativeSettingsPassed': False, 'dependentTabSkipped': True, 'proposedOptimizationImplemented': False, 'causalServerPhaseProven': False, 'gaAccepted': False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
