#!/usr/bin/env python3
"""Seal this host-only correction preparation; does not restore or select a target."""
from pathlib import Path
import ast
import copy
import datetime
import difflib
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
H = Path(__file__).resolve().parent
R = H.parent.parent
P = H.parent / 'swift-current-attribution-full-preparation'
Q = H.parent / 'swift-current-attribution-preparation-review'
C = H.parent / 'swift-cache-current-attribution-observer'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
load = lambda p: json.loads(Path(p).read_bytes())
save = lambda p, v: Path(p).write_text(json.dumps(v, indent=2, sort_keys=True) + '\n')
assert not (H / 'seal.json').exists()
assert sha(P / 'prepared-seal.json') == 'c40ab937f218baa54b45e5a5846e4dd12d05edcfb2c3786a75d27f026f70a7f1'
assert sha(Q / 'seal.json') == 'd4eff30cc7c48accf8c93621e0810ec94a68ee282699fed9a1aaf772071ac3b6'
for name in ('root-selection.json', 'target-attempt-started.json', 'owned-scratch', 'owned-tmp'):
    assert not (H / name).exists()
spec = importlib.util.spec_from_file_location('correction_read_only_verifier', H / 'verify.py')
verify = importlib.util.module_from_spec(spec); spec.loader.exec_module(verify)
driver = verify.module('correction_final_driver', H / 'diagnostic.py')
original = verify.functions(P / 'diagnostic.py'); corrected = verify.functions(H / 'diagnostic.py')
assert original.keys() == corrected.keys()
assert all(verify.normalized(corrected[n]) == body for n, body in original.items())
a = (P / 'diagnostic.py').read_text(); b = (H / 'diagnostic.py').read_text()
(H / 'driver-changes.diff').write_text(''.join(difflib.unified_diff(a.splitlines(True), b.splitlines(True),
    fromfile=str((P / 'diagnostic.py').relative_to(R)), tofile=str((H / 'diagnostic.py').relative_to(R)))))
save(H / 'source-audit.json', {'schema': 1, 'UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': [sys.executable, '-B', str(Path(__file__).resolve())], 'cwd': str(R),
    'pythonVersion': sys.version, 'pythonSHA256': sha(sys.executable),
    'sourceRevisionContext': '7b6048642b42e4900cccff4e14aa0fe8949ab35e',
    'sourceRevisionMeaning': 'root supplied delivery context; exact sealed bytes authoritative; no Git query',
    'originalDriverSHA256': sha(P / 'diagnostic.py'), 'correctedDriverSHA256': sha(H / 'diagnostic.py'),
    'allOriginalFunctionsRetained': True, 'functionCount': len(original),
    'functionsIdenticalAfterOnlyExplicitChanges': list(original),
    'allowedChanges': ['explicit immutable ASSETS paths', 'local classifier path guard',
        'original preparation seal guard', 'legacy mutation commands removed from CLI choices'],
    'originalHostTestSuiteByteIdentical': sha(H / 'test_driver.py') == sha(P / 'test_driver.py'),
    'liveVmRead': False, 'gitQueried': False, 'rustSourceOrBinaryChanged': False})
save(H / 'source-bindings.json', {'schema': 1,
    'originalPreparedSealSHA256': sha(P / 'prepared-seal.json'), 'reviewSealSHA256': sha(Q / 'seal.json'),
    'unchangedSourceManifestSHA256': sha(P / 'copied-build-manifest.json'),
    'unchangedBinarySHA256': load(P / 'binary.json')['retained']['sha256'],
    'retainedCompressedBinarySHA256': sha(P / 'bin/exact-tests.gz'),
    'acceptedObserverSourceArchiveSHA256': sha(C / 'isolated-source.tar.gz'),
    'acceptedObserverEmitterSHA256': sha(C / 'observer-and-controls.rs'),
    'unchangedAdapterSHA256': sha(P / 'adapter.rs'), 'unchangedHarnessSHA256': sha(P / 'harness.rs'),
    'schemaControlSourceSHA256': load(C / 'copied-source-manifest.json')['src/experimental_swift_reactor/control.rs'],
    'outputContractSHA256': sha(P / 'output-contract.json'), 'producerTarget': 'aarch64-apple-darwin',
    'unsignedWidths': {'sequence': 8, 'reset_count': 8, 'masks': 32, 'counters': 64,
        'optionalFunctionSome': 32, 'optionalFunctionNoneSentinel': 18446744073709551615, 'usizeOffsets': 64},
    'arrayLengths': driver.telemetry.ARRAYS, 'guestResultReplaced': False, 'cleanupFromTelemetry': False})
original_events = load(Q / 'parser-original-events.json')
cases = []
for case in load(Q / 'parser-classifications.json')['cases']:
    path = Q / case['path']; before = copy.deepcopy(original_events)
    result = driver.telemetry.classify(path, original_events)
    assert case['classification']['status'] == 'valid' and result['status'] == 'invalid_or_missing'
    assert before == original_events
    cases.append({'path': str(path.relative_to(R)), 'stdoutSHA256': sha(path),
        'originalStatus': 'valid', 'correctedStatus': result['status'], 'correctedIssues': result['issues'],
        'originalEventsUnchanged': True, 'originalResultReplaced': False, 'cleanupTruthInferredFromTelemetry': False})
positive = []
for name in ('control-001', 'control-002'):
    result = driver.telemetry.classify(P / 'commands' / name / 'stdout', load(P / (name + '-events.json')))
    assert result == load(P / (name + '-telemetry.json')) and result['status'] == 'valid'
    positive.append({'path': str((P / 'commands' / name / 'stdout').relative_to(R)),
        'stdoutSHA256': sha(P / 'commands' / name / 'stdout'), 'status': 'valid', 'classificationByteValuesUnchanged': True})
save(H / 'classifications.json', {'schema': 1, 'sixReproductions': cases, 'realFiniteProducerOutputs': positive})
final = load(H / 'commands/host-003/receipt.json'); assert final['passed'] and final['exitCode'] == 0
save(H / 'receipt.json', {'schema': 1, 'status': 'prepared-awaiting-independent-review; no target selected',
    'hostMethodsPassed': 38, 'originalHostMethodsPassed': 14, 'adaptedIndependentHostMethodsPassed': 8,
    'schemaMethodsPassed': 16, 'sixReviewReproductionsRejected': 6, 'retainedProducerOutputsStillValid': 2,
    'initialAuthoringFixtureFailuresPreserved': 2, 'finalHostCommand': 'commands/host-003/receipt.json',
    'scratchCleaned': True, 'scratchContainedNoFiles': True, 'allOwnedProcessGroupsAbsentAfterCommands': True,
    'legacyMutationCommandsDisabled': ['prepare', 'build', 'propose', 'cleanup'],
    'rootOwnsLaterRestorationAndExplicitCleanup': True, 'originalCompressedExecutablePreserved': True,
    'fullTargetAttempts': 0, 'realTargetValidations': 0, 'realTargetInitializeCalls': 0,
    'realTargetCorpusCalls': 0, 'rootSelectionCreated': False, 'attemptMarkerCreated': False,
    'productionSourceChanged': False, 'sourceOrBinaryRestored': False, 'gitQueried': False,
    'liveVmRead': False, 'nativeOrDeviceRuns': 0, 'gaAccepted': False,
    'originalResultReplaced': False, 'cleanupTruthInferredFromTelemetry': False})
selection = load(P / 'root-selection-template.json')
selection.update(exactCommandSelected=False, originalPreparedSealSHA256=sha(P / 'prepared-seal.json'),
    driverSHA256=sha(H / 'diagnostic.py'), telemetryClassifierSHA256=sha(H / 'telemetry.py'),
    outerCommand=['python3', '-B', str((H / 'diagnostic.py').relative_to(R)), 'target'])
local = ('telemetry.py', 'diagnostic.py', 'test_driver.py', 'driver-changes.diff')
selection['boundEvidence'] = {n if n in local else '../' + P.name + '/' + n: sha((H if n in local else P) / n)
                              for n in selection['boundEvidence']}
for name in ('verify.py', 'source-audit.json', 'source-bindings.json', 'classifications.json', 'receipt.json',
             'test_schema.py', 'test_selection.py', 'commands/host-003/receipt.json'):
    selection['boundEvidence'][name] = sha(H / name)
selection['status'] = 'template-only; independent review and root exact selection required'
save(H / 'root-selection-template.json', selection)
save(H / 'seal.json', {'schema': 1, 'status': 'correction prepared; independent review pending',
    'files': {str(p.relative_to(H)): sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name != 'seal.json'},
    'externalFiles': {str(p.relative_to(R)): sha(p) for p in
        (R / 'docs/swift-attribution-schema-correction.md', P / 'prepared-seal.json', Q / 'seal.json')},
    'fullTargetAttempts': 0, 'rootSelectionCreated': False, 'gaAccepted': False})
print(json.dumps({'sealedMembers': len(load(H / 'seal.json')['files']), 'sealSHA256': sha(H / 'seal.json'),
    'hostMethodsPassed': 38, 'fullTargetAttempts': 0}, sort_keys=True))
