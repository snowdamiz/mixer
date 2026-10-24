#!/usr/bin/env python3
"""Record scoped implementation authorization from exact reviewed contract inputs."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def main():
    producer = ROOT / 'verification/swift-active-frame-contract'
    review = ROOT / 'verification/swift-active-frame-contract-review'
    seal = producer / 'seal.json'
    expected_seal = 'fad763b5f7afa20f7d2c33b5bdd71c731a8e093db82bb41373380007c8825ac2'
    assert sha(seal) == expected_seal
    replay_path = HERE / 'results/20261024T041306773795Z/receipt.json'
    replay = json.loads(replay_path.read_text())
    assert replay['status'] == 'passed-retained-host-metadata-and-abi-replay'
    assert replay['producerSealSHA256'] == expected_seal
    decision_path = review / 'review.json'
    decision = json.loads(decision_path.read_text())
    assert decision['status'] == 'reviewed-amended-frozen-contract-proposal-no-blocking-findings'
    assert decision['producerSealSHA256'] == expected_seal
    assert (decision['inventoryFields'], decision['newFrameEnvelopeBytes']) == (1061, 360352)
    independent_path = ROOT / decision['independentReceipt']
    assert sha(independent_path) == decision['independentReceiptSHA256']
    independent = json.loads(independent_path.read_text())
    assert independent['status'] == 'independently-verified-declaration-compiler-layout-only'
    assert independent['compilerFreshConfigurations'] == 2
    assert independent['metadataReplays'] == 16
    assert not any(independent[k] for k in ['accountingCompletenessAccepted', 'frameExecution',
                   'gaAcceptance', 'guestExecution', 'nativeRuntime', 'physicalRuntime',
                   'productSourceEdited', 'semanticAcceptance'])
    bindings = dict(replay['bindings'])
    review_seal_path = review / 'review-seal.json'
    review_seal_sha = '0f5ca40e028d5fc28cb6bad78a58e5fac11a5640f10c43187134f1832963b42a'
    assert sha(review_seal_path) == review_seal_sha
    review_seal = json.loads(review_seal_path.read_text())
    bindings.update(review_seal['bindings'])

    def bind(path):
        bindings[str(path.relative_to(ROOT))] = sha(path)

    bind(replay_path)
    bind(review_seal_path)
    bind(HERE / 'results/20261024T041306773795Z/live-source-manifest.json')
    bind(independent_path)
    bind(Path(__file__).resolve())
    bind(HERE / 'README.md')
    bind(HERE / 'check_saved.py')
    # This immutable decision snapshot keeps later artifact packaging supplements
    # independent of the accepted declaration decision.
    snapshot = HERE / 'independent-decision.json'
    snapshot.write_bytes(decision_path.read_bytes())
    bind(snapshot)
    for row in replay['commands']:
        assert row['exitCode'] == 0
        for stream in ['stdout', 'stderr']:
            path = ROOT / row[stream]
            assert sha(path) == row[stream + 'SHA256']
            bind(path)
    fresh = 0
    for row in independent['commands']:
        assert row['exitCode'] == 0
        for stream in ['stdout', 'stderr']:
            path = independent_path.parent / row[stream]
            assert sha(path) == row[stream + 'SHA256']
            bind(path)
        if row['name'].startswith('fresh-'):
            fresh += 1
            assert row['sourceBefore'] == row['sourceAfter']
            assert hashlib.sha256(encoded(row['sourceBefore'])).hexdigest() == row['sourceTreeSHA256']
            assert row['sourceTreeSHA256'] == decision['candidateDeclarationTreeSHA256']
    assert fresh == 2
    for name, expected in bindings.items():
        assert sha(ROOT / name) == expected, name
    result = {
        'status': 'accepted-private-active-frame-contract-for-implementation',
        'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': 'root',
        'producerSealSHA256': expected_seal,
        'independentReviewSealSHA256': review_seal_sha,
        'producerReceiptSHA256': decision['producerReceiptSHA256'],
        'sourceTreeSHA256': decision['producerSourceTreeSHA256'],
        'rootReplay': str(replay_path.relative_to(ROOT)),
        'independentDecision': str(snapshot.relative_to(ROOT)),
        'compilerChecks': 81,
        'independentFreshCompilerChecks': 2,
        'rootMetadataReplays': 16,
        'rootABIInspections': 8,
        'inventoryFields': 1061,
        'permanentBytes': {'production': 175144, 'unit': 175336},
        'frameOperationBytes': {'newFrameEdges': 240776, 'freshFullNestedValue': 119576, 'total': 360352},
        'scope': 'Ownership/declaration/accounting proposal and implementation authorization only. Actual frame algorithm, literal implementation binding completeness and AF01-AF22 runtime acceptance remain unproven.',
        'implementationRequirements': [
            'Use actual original State/cache/control/WASI; retain each failed pin in its actual same-index frame or unpublished State entry guard.',
            'Capture pre-entry actual lengths in synchronous entry locals, pass them to rollback before returning; no persisted or inferred stale offsets on resume.',
            'Add both consuming-cleanup and zero-frame value preparation barriers in the coherent slice; retain sticky mismatch and nested/outer restoration obligations.',
            'Use matches_layout only after original reservation-owner validation; no new authority, refunds or ledger reassignment follow from its bool.',
            'Use exact positive final declaration inventory plus separately positive positions for every additional actual binding before admitted runtime execution. Independent actual-source accounting review remains required.',
            'Run all AF01-AF22 with real constructed owners and real cache/frame pins, preserving exact original failure/effect/work order, allocation scope and actual WASI observations.',
            'Test-only ticket replacement retains original authority; test-only live budget narrowing returns original scalar and never repairs live ledger; decoded-control fixtures preserve actual decoded-kind provenance.',
            'AF04 invalid257 may reject at real validation before owner construction; distinguish that from valid255/256 frame execution.',
            'Do not add public invoke/dispatch/Ready behavior or change Frozen method bodies, public Limits/C ABI, old value scratch or2912-byte Frozen reservation.'
        ],
        'runtimeImplementationAccepted': False,
        'nativeRuntimeAccepted': False,
        'gaGatePassed': False,
        'bindings': bindings
    }
    (HERE / 'acceptance.json').write_bytes(encoded(result))
    print(json.dumps({'status': result['status'], 'bindings': len(bindings)}))


if __name__ == '__main__':
    main()
