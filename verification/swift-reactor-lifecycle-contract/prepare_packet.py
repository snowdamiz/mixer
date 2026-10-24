#!/usr/bin/env python3
"""Snapshot only named contract inputs; never reads the retained Wasm target."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ATTEMPT = 'attempts/20261024T194625118230Z'
INPUTS = [
    'AGENTS.md', 'mixer-product-plan.md',
    'docs/swift-reactor-lifecycle-contract.md',
    'docs/swift-dispatch-v7-runtime-checkpoint.md',
    'docs/swift-calls-dispatch-contract.md',
    'docs/swift-reactor-execution-stage-design.md',
    'verification/swift-calls-dispatch-root-review/live-v7-integration-retry/final-live-manifest.json',
    'verification/swift-calls-dispatch-root-review/live-v7-integration-retry/formatting-normalization.json',
    'verification/swift-calls-dispatch-root-review/live-v7-integration-retry/live-check.json',
    'verification/swift-calls-dispatch-root-review/live-v7-integration-retry/whitespace-only.diff',
    'verification/swift-calls-dispatch-root-review/sealed-v7/runtime-review.json',
    'verification/swift-calls-dispatch/v7-fixture-expectations/candidate-final-manifest.json',
]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def main():
    assert not (HERE / 'seal.json').exists(), 'never rewrite a sealed packet'
    assert not (HERE / 'receipt.json').exists(), 'prepare once; preserve existing packet'
    bindings = {}
    for name in INPUTS:
        data = (ROOT / name).read_bytes()
        path = HERE / 'inputs' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        assert (ROOT / name).read_bytes() == data, name
        bindings[name] = digest(data)
    (HERE / 'input-bindings.json').write_bytes(encoded(bindings))
    observed = json.loads((HERE / ATTEMPT / 'receipt.json').read_text())
    commands = json.loads((HERE / ATTEMPT / 'commands.json').read_text())
    versions = {row['label']: gzip.decompress((HERE / ATTEMPT / row['log']).read_bytes()).decode()
                for row in commands if row['target'] is None}
    reference = json.loads((ROOT / INPUTS[8]).read_text())
    receipt = {
        'schema': 'mixer.swift-lifecycle.contract-packet.1',
        'status': 'prepared-for-root-contract-review',
        'observedUTC': datetime.now(timezone.utc).isoformat(),
        'selected': False, 'runtime': False, 'implementationAccepted': False,
        'accountingAccepted': False, 'nativeAccepted': False, 'gaAccepted': False,
        'vmExecutions': 0, 'nativeInstancesCreated': 0,
        'targetArtifactRead': False, 'gitQueried': False,
        'sourceRevisionContext': reference['sourceRevisionContext'],
        'sourceRevisionContextAuthority': INPUTS[8] + ' (historical root receipt; no new Git query)',
        'baselineClosure': observed['baselineClosure'], 'baselineFileCount': 130,
        'compositionAttempt': ATTEMPT, 'witnessClosure': observed['witnessClosure'],
        'compositionPassed': observed['compositionPassed'],
        'positiveProductionTypecheckContexts': 4, 'expectedBorrowRejections': 2,
        'recordedCompositionCommands': 9, 'runtimeGroupsPlanned': 24,
        'toolVersions': versions, 'pinnedToolSHA256': observed['toolSHA256'],
        'collectorPython': {'path': str(Path(sys.executable).resolve()),
                            'observedExecutableSHA256': digest(Path(sys.executable).read_bytes()),
                            'scope': 'Observed at packet preparation; not a prelaunch binary pin.'},
        'inputBindingsSHA256': digest(encoded(bindings)),
        'cleanupPassed': observed['cleanupPassed'],
        'requiredRootDecision': 'Select publication-aware common growth completion and bounded file ownership before implementation.',
        'limitations': ['No lifecycle implementation or runtime matrix execution.',
                       'Uncalled witness has an intentionally copied vacancy predicate and boolean publication selector, not the proposed product API.',
                       'No complete owner-entry/runner borrow proof or MIR/layout/accounting acceptance.',
                       'Final normalized baseline typechecks do not replay predecessor runtime results.',
                       'No retained reactor read/hash/run, native/device/provider/Git/network activity or GA evidence.'],
    }
    (HERE / 'receipt.json').write_bytes(encoded(receipt))
    print(json.dumps({'inputs': len(bindings), 'status': receipt['status'],
                      'selected': False, 'runtime': False, 'baselineClosure': observed['baselineClosure']}))

if __name__ == '__main__':
    main()
