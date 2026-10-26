#!/usr/bin/env python3
"""Bounded read-only audit: retained host artifacts only; never dispatch a target."""
from pathlib import Path
import ast
import copy
import datetime
import gzip
import hashlib
import importlib.util
import json
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE.parent / 'swift-current-attribution-runtime'
PREP = HERE.parent / 'swift-current-attribution-full-preparation'
FIX = HERE.parent / 'swift-attribution-schema-correction'
OLD = HERE.parent / 'swift-exact-reactor-after-plan-reuse'
OBS = HERE.parent / 'swift-cache-current-attribution-observer'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def strict(data):
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result, key
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def load(path):
    return strict(Path(path).read_bytes())


def verify_seal(directory, name, expected, count):
    assert sha(directory / name) == expected
    seal = load(directory / name)
    actual = {str(p.relative_to(directory)) for p in directory.rglob('*')
              if p.is_file() and p.name != name}
    assert actual == set(seal['files']) and len(actual) == count
    for member, digest in seal['files'].items():
        assert sha(directory / member) == digest, member
    for member, digest in seal['externalFiles'].items():
        assert sha(ROOT / member) == digest, member
    return {'sha256': expected, 'members': count, 'externalMembers': len(seal['externalFiles'])}


def exact_events(path):
    return [strict(line.split(b'MIXER_EXACT ', 1)[1]) for line in path.read_bytes().splitlines()
            if b'MIXER_EXACT ' in line]


def event(events, name):
    return next(e['payload'] for e in events if e['event'] == name)


def main():
    seals = {
        'runtime': verify_seal(RUN, 'result-seal.json', '46449fdf0a02fd6c10140803eea197505540f70616f8f0e27174da68ea9619ba', 26),
        'preparation': verify_seal(PREP, 'prepared-seal.json', 'c40ab937f218baa54b45e5a5846e4dd12d05edcfb2c3786a75d27f026f70a7f1', 104),
        'schemaCorrection': verify_seal(FIX, 'seal.json', 'c00ce1412238f08f176d7983b882c25891cbafd6570c0e489dc4733875935c20', 32),
        'originalPreparationReview': verify_seal(HERE.parent / 'swift-current-attribution-preparation-review', 'seal.json', 'd4eff30cc7c48accf8c93621e0810ec94a68ee282699fed9a1aaf772071ac3b6', 69),
    }
    assert (RUN / 'diagnostic.py').read_bytes() == (FIX / 'diagnostic.py').read_bytes()
    assert (RUN / 'telemetry.py').read_bytes() == (FIX / 'telemetry.py').read_bytes()
    assert (RUN / 'commands/target-once/diagnostic.py').read_bytes() == (RUN / 'diagnostic.py').read_bytes()
    assert (RUN / 'commands/target-once/harness.rs').read_bytes() == (PREP / 'harness.rs').read_bytes()
    source = {}
    with tarfile.open(OBS / 'isolated-source.tar.gz', 'r:gz') as archive:
        members = archive.getmembers()
        assert len(members) == 132 and len({m.name for m in members}) == 132
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        source = {m.name: archive.extractfile(m).read() for m in members}
    assert {n: hashlib.sha256(b).hexdigest() for n, b in source.items()} == load(OBS / 'copied-source-manifest.json')
    source['src/experimental_swift_reactor/cache_tests.rs'] += b'\n' + (PREP / 'adapter.rs').read_bytes() + b'\n' + (PREP / 'adapter-controls.rs').read_bytes()
    append = '\n// Isolated diagnostic only; baseline production bytes are unchanged.\ninclude!(' + json.dumps(str(PREP / 'harness.rs')) + ');\n'
    source['src/experimental_swift_reactor/lifecycle_tests.rs'] += append.encode()
    manifest = {n: hashlib.sha256(b).hexdigest() for n, b in source.items()}
    assert manifest == load(PREP / 'copied-build-manifest.json') == load(RUN / 'commands/target-once/source-manifest.json')
    assert sha(PREP / 'baseline-manifest.json') == '16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
    digest = hashlib.sha256()
    binary_bytes = 0
    with gzip.open(PREP / 'bin/exact-tests.gz', 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            binary_bytes += len(block)
            digest.update(block)
    binary_hash = digest.hexdigest()
    assert binary_hash == 'fc27c22f8f771e7f148bcb73781b09a974a2bcebce7be7466b951ff85d9fafaf' and binary_bytes == 4960000
    selection = load(RUN / 'root-selection.json')
    command = load(RUN / 'selected-command.json')
    marker = load(RUN / 'target-attempt-started.json')
    inner = load(RUN / 'commands/target-once/receipt.json')
    outer = load(RUN / 'outer-receipt.json')
    started = load(RUN / 'commands/target-once/started.json')
    for name, value in selection['boundEvidence'].items():
        assert sha(RUN / name) == value, name
    assert selection['argv'] == command['argv'] == inner['argv'] == started['argv']
    assert selection['outerCommand'] == command['outerCommand'] == outer['argv']
    assert selection['maxTargetAttempts'] == command['maxTargetAttempts'] == 1
    assert selection['exactCommandSelected'] and selection['selectedBy'] == '/root'
    assert selection['binarySHA256'] == marker['binary']['sha256'] == inner['argvFileIdentities'][0]['sha256'] == binary_hash
    assert selection['binaryBytes'] == marker['binary']['bytes'] == binary_bytes
    assert selection['sourceManifestSHA256'] == sha(PREP / 'copied-build-manifest.json') == inner['sourceClosure']
    assert marker['rootSelection']['sha256'] == sha(RUN / 'root-selection.json')
    target = Path(marker['targetOriginal']['path'])
    assert sha(target) == selection['targetSHA256'] == marker['targetOriginal']['sha256'] == marker['boundInputCopy']['sha256'] == '24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994'
    assert target.stat().st_size == selection['targetBytes'] == marker['targetOriginal']['bytes'] == marker['boundInputCopy']['bytes'] == 53777114
    assert datetime.datetime.fromisoformat(selection['selectedAt']) < datetime.datetime.fromisoformat(outer['startedAt']) < datetime.datetime.fromisoformat(inner['UTC'])
    assert sorted(p.name for p in (RUN / 'commands').iterdir()) == ['target-once']
    proposal = load(PREP / 'proposed-command.json')
    for key in ('validationDeadlineMs', 'cumulativeRuntimeDeadlineMs', 'cumulativeWasiDeadlineMs', 'outerDeadlineSeconds', 'terminationGraceSeconds', 'killWaitSeconds', 'maxTargetAttempts'):
        assert command[key] == proposal[key], key
    assert inner['timeoutSeconds'] == command['outerDeadlineSeconds'] == 170
    assert inner['exitCode'] == 101 and outer['exitCode'] == 1 and not inner['passed'] and not inner['timedOut']
    assert inner['signalSent'] == [] and inner['processGroupEmpty'] and inner['rawStreamEOFConfirmed']
    assert all(inner[k] for k in ('sourceUnchanged', 'toolsUnchanged', 'argvFilesUnchanged', 'allBoundInputsUnchanged', 'harnessUnchanged', 'driverUnchanged', 'commandFailurePreserved'))
    assert inner['toolsBefore'] == load(PREP / 'binding.json')['compilerTools']
    for stream in ('stdout', 'stderr'):
        assert sha(RUN / 'commands/target-once' / stream) == inner[stream]['sha256']
        assert sha(RUN / ('outer.' + stream)) == outer[stream + 'SHA256']
    original = exact_events(RUN / 'commands/target-once/stdout')
    assert original == load(RUN / 'target-once-events.json')
    previous = exact_events(OLD / 'commands/target-once/stdout')
    for budget in ('validation_budget', 'run_budget', 'wasi_budget', 'wasi_grants'):
        assert event(original, budget) == event(previous, budget), budget
    failure = event(original, 'runtime_failure')
    historical = load(OLD / 'target-once-classification.json')['firstTypedFailure']
    for key in ('stage', 'kind', 'code', 'function', 'offset', 'resource', 'attempted', 'limit', 'deadline_origin'):
        assert failure[key] == historical[key], key
    assert (failure['resource'], failure['attempted'], failure['limit'], failure['at_failure']['instructions']) == ('CacheWork', 64000001, 64000000, 23358291)
    phases = [e['payload'] for e in original if e['event'] == 'phase_begin']
    assert phases == ['validation', 'initialize', 'corpus_1'] and event(original, 'phase_reply') == 'Initialized'
    assert not any(e['event'] in ('validation_failure', 'corpus_2', 'guest_output_native_equal') for e in original)
    result = load(RUN / 'target-once-result.json')
    assert result['firstFailure'] == {'event': 'runtime_failure', 'payload': failure}
    assert result['phasesBegun'] == phases and result['targetAttempted'] and result['targetBytesUnchangedAfterAttempt']
    assert all(result[k] is False for k in ('commandPassed', 'diagnosticCompleted', 'ownedCleanupEmpty', 'nativeParity', 'fullSLMatrixAccepted', 'productionAccountingAccepted', 'nativeSignedPublicAccepted', 'performanceSizeMemoryAccepted', 'GAaccepted'))
    driver = (RUN / 'diagnostic.py').read_text()
    execute = next(n for n in ast.parse(driver).body if isinstance(n, ast.FunctionDef) and n.name == 'execute')
    body = ast.get_source_segment(driver, execute)
    assert body.index('save(name + "-result.json", result)') < body.index('telemetry.classify(stdout, observed)')
    assert '(HERE / "target-attempt-started.json").open("x")' in body
    assert event(original, 'cleanup_empty') is False and event(original, 'diagnostic_execution_complete') is False
    final = event(original, 'final_cleanup_usage')
    assert all(v['current'] == 0 for v in final['reservations'].values() if type(v) is dict)
    assert all(v['current'] == 0 for v in final['live'].values())
    assert final['reservations']['live_tickets'] == 0 and final['cleanup_invariant'] is None
    assert event(original, 'cleanup_reservations_and_live_empty') is True
    spec = importlib.util.spec_from_file_location('audited_runtime_telemetry', RUN / 'telemetry.py')
    telemetry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(telemetry)
    before = copy.deepcopy(original)
    classified = telemetry.classify(RUN / 'commands/target-once/stdout', original)
    assert classified == load(RUN / 'target-once-telemetry.json') and original == before
    assert classified['status'] == 'valid' and classified['issues'] == [] and classified['outputBytes'] == 4430
    assert classified['originalResultReplaced'] is False and classified['cleanupTruthInferredFromTelemetry'] is False
    rows = classified['snapshots']
    assert [r['lifecycle'] for r in rows] == ['constructed', 'initialize', 'corpus_1', 'before_cleanup', 'final_cleanup']
    assert [r['sequence'] for r in rows] == [1, 2, 3, 4, 5]
    raw = [line[line.index(b'MIXER_ATTRIBUTION '):] for line in (RUN / 'commands/target-once/stdout').read_bytes().splitlines(keepends=True) if b'MIXER_ATTRIBUTION ' in line]
    assert sum(map(len, raw)) == 4430 and max(map(len, raw)) <= 4608 and all(line.endswith(b'\n') for line in raw)
    for row in rows:
        p = row['payload']
        assert sum(p['credits']) == row['cache_work'] and p['distinct'] + p['repeated'] == p['completed'] == row['cache_decodes']
        assert sum(p['build_credits']) == p['credits'][13] and sum(p['scan_credits']) == p['credits'][6]
    for a, b in zip(rows, rows[1:]):
        for key in (*telemetry.ARRAYS, *telemetry.COUNTERS):
            aa = a['payload'][key] if key in telemetry.ARRAYS else [a['payload'][key]]
            bb = b['payload'][key] if key in telemetry.ARRAYS else [b['payload'][key]]
            assert all(x <= y for x, y in zip(aa, bb)), key
    p = rows[-1]['payload']
    assert (p['completed'], p['distinct'], p['repeated']) == (61627, 485, 61142)
    assert p['build_credits'] == [434091, 34500496] and p['scan_credits'] == [330379, 3590363]
    assert p['first_rejection'] == {'site': 13, 'requested': 1, 'cursor_function': 23610, 'cursor_offset': 4154038, 'kind': 'WorkExhausted', 'resource': 'Some(CacheWork)', 'function': 23610, 'offset': 4154038, 'attempted': 64000001, 'limit': 64000000}
    assert rows[2]['payload'] == rows[3]['payload'] == rows[4]['payload']
    schema_cases = load(FIX / 'classifications.json')['sixReproductions']
    review_original = load(HERE.parent / 'swift-current-attribution-preparation-review/parser-original-events.json')
    rejected = []
    for case in schema_cases:
        sample = ROOT / case['path']
        assert sha(sample) == case['stdoutSHA256']
        probe = telemetry.classify(sample, review_original)
        assert probe['status'] == 'invalid_or_missing' and probe['issues'] == case['correctedIssues']
        rejected.append(sample.name)
    class MemoryInput:
        def __init__(self, data): self.data = data
        def read_bytes(self): return self.data
    lowered = copy.deepcopy(rows)
    lowered[-1]['payload']['build_credits'][1] -= 1
    sample = b''.join(b'MIXER_ATTRIBUTION ' + json.dumps(r, separators=(',', ':')).encode() + b'\n' for r in lowered)
    assert 'cumulative_counter_regression' in telemetry.classify(MemoryInput(sample), original)['issues']
    wrong = copy.deepcopy(rows)
    wrong[-1]['payload']['first_rejection']['attempted'] += 1
    sample = b''.join(b'MIXER_ATTRIBUTION ' + json.dumps(r, separators=(',', ':')).encode() + b'\n' for r in wrong)
    assert 'rejection_original_failure_mismatch' in telemetry.classify(MemoryInput(sample), original)['issues']
    assert original == before
    root_review = HERE.parent / 'current-diagnostic-corrections-root-review'
    accepted = load(root_review / 'swift-acceptance.json')
    initial = load(root_review / 'swift-host-review-initial.json')
    assert accepted['exitCode'] == 0 and accepted['hostMethodsPassed'] == 38 and accepted['priorBlockingFindingsClosed'] == 6
    assert accepted['initialRootFixtureSetupFailurePreserved'] and accepted['temporaryDirectoriesRemovedByEmptyRmdir']
    assert initial['exitCode'] == 1 and initial['testsRun'] == 38 and initial['errors'] == 5 and initial['sourceFix'] is False
    for stream in ('stdout', 'stderr'):
        assert sha(root_review / ('swift-host-review.' + stream)) == accepted[stream + 'SHA256']
    assert 'FAILED (errors=5)' in (root_review / 'swift-host-review-initial.stderr').read_text()
    assert 'Ran 38 tests' in (root_review / 'swift-host-review.stderr').read_text() and (root_review / 'swift-host-review.stderr').read_text().endswith('OK\n')
    assert not (FIX / 'owned-scratch').exists() and not (FIX / 'owned-tmp').exists()
    cleanup = load(RUN / 'root-cleanup.json')
    assert cleanup['ownedPaths'] == load(RUN / 'owned-paths.json')
    assert cleanup['removed'] and cleanup['logicalBytesRemoved'] == 78030702 and cleanup['signalsSent'] == []
    assert sum(len(b) for b in source.values()) + binary_bytes + target.stat().st_size == cleanup['logicalBytesRemoved']
    assert all(not Path(path).exists() for path in cleanup['ownedPaths'])
    assert all(c['exitCode'] == 1 and c['stdout'] == c['stderr'] == '' for c in cleanup['holderChecks'])
    groups = {inner['processGroup'], outer['pgid']}
    assert groups == {x['pgid'] for x in cleanup['ownedGroups']} and all(x['state'] == 'absent' for x in cleanup['ownedGroups'])
    ps_argv = ['/bin/ps', '-axo', 'pid=,pgid=,comm=']
    ps = subprocess.check_output(ps_argv, text=True, timeout=10)
    matches = [line for line in ps.splitlines() if len(line.split()) >= 2 and int(line.split()[1]) in groups]
    assert not matches
    assert sha(PREP / 'bin/exact-tests.gz') == cleanup['originalCompressedBinarySHA256'] == '1e0fffa6fcce33123d052dd3c3f3c40d68d88cb089f3fbdce8fe9cf232c54f98'
    summary = load(RUN / 'result-summary.json')
    assert summary['legacyOwnedCleanupEmpty'] is False and summary['finalConsumingUsageZero'] is True and not summary['gaAccepted']
    build_pct = p['build_credits'][1] * 100 / failure['limit']
    combined = p['build_credits'][1] + p['scan_credits'][1]
    combined_pct = combined * 100 / failure['limit']
    assert summary['repeatedBuildBudgetPercent'] == build_pct and summary['repeatedScanAndBuildBudgetPercent'] == combined_pct
    print(json.dumps({'acceptedHostDiagnosticEvidence': True, 'blockingFindings': [], 'seals': seals,
        'sourceRevisionContext': summary['sourceRevision'], 'baselineClosure': inner['baselineClosure'],
        'sourceManifestSHA256': inner['sourceClosure'], 'sourceFilesReconstructedInMemory': len(source),
        'binarySHA256': binary_hash, 'binaryBytes': binary_bytes, 'driverSHA256': sha(RUN / 'diagnostic.py'),
        'classifierSHA256': sha(RUN / 'telemetry.py'), 'harnessSHA256': sha(PREP / 'harness.rs'),
        'retainedTargetAttempts': 1, 'auditTargetAttempts': 0, 'outerExitCode': outer['exitCode'], 'libtestExitCode': inner['exitCode'],
        'originalFailure': {k: failure[k] for k in ('resource', 'attempted', 'limit', 'function', 'offset')},
        'instructions': failure['at_failure']['instructions'], 'corpus2Executed': False,
        'telemetrySnapshots': len(rows), 'telemetryOutputBytes': classified['outputBytes'],
        'completedDecodes': p['completed'], 'distinctFunctions': p['distinct'], 'repeatedDecodes': p['repeated'],
        'firstBuildCredits': p['build_credits'][0], 'repeatedBuildCredits': p['build_credits'][1], 'repeatedBuildBudgetPercent': build_pct,
        'firstScanCredits': p['scan_credits'][0], 'repeatedScanCredits': p['scan_credits'][1],
        'repeatedScanAndBuildCredits': combined, 'repeatedScanAndBuildBudgetPercent': combined_pct,
        'sixPriorInvalidInputsRejected': rejected, 'additionalInMemoryNegativeChecks': 2,
        'retainedRootHostMethodsPassed': 38, 'retainedRootFixtureErrorsPreserved': 5, 'hostMethodsRerunByAudit': 0,
        'legacyOwnedCleanupEmpty': False, 'finalConsumingUsageZero': True,
        'cleanupPathsAbsent': True, 'cleanupLogicalBytes': cleanup['logicalBytesRemoved'],
        'ownedGroupsAbsent': sorted(groups), 'processObservationCommand': ps_argv,
        'processObservationSHA256': hashlib.sha256(ps.encode()).hexdigest(),
        'originalResultReplaced': False, 'completeWorkloadPassed': False, 'performanceQualified': False,
        'nativeSignedPublishedFieldLogOrGAAccepted': False}, sort_keys=True))


if __name__ == '__main__':
    main()
