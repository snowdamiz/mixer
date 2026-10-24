#!/usr/bin/env python3
"""Read-only saved compiler/contract packet checks, never runtime acceptance."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = '3dee84f70c852c2a26572c1d6e3463e45e56760a6bba403fabfb9c355ccb1cd3'
V7 = '78e2586b41f698c60e1bcd4cdd4abb33fbf98d747d1ee183a793988dea7b5237'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def read(path):
    return json.loads(path.read_text())

def archive(path):
    with tarfile.open(path) as stream:
        members = stream.getmembers()
        assert len(members) == len({member.name for member in members})
        for member in members:
            path = PurePosixPath(member.name)
            assert member.isfile() and not path.is_absolute() and '..' not in path.parts
        return {member.name: stream.extractfile(member).read() for member in members}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--unsealed', action='store_true')
    args = parser.parse_args()
    if not args.unsealed:
        seal = read(HERE / 'seal.json')
        actual = {str(path.relative_to(HERE)) for path in HERE.rglob('*')
                  if path.is_file() and path != HERE / 'seal.json'}
        assert actual == set(seal['files']), 'packet file closure changed'
        for name, pin in seal['files'].items():
            assert digest((HERE / name).read_bytes()) == pin, name
        assert not seal['selected'] and not seal['runtime']
    receipt = read(HERE / 'receipt.json')
    assert receipt['status'] == 'prepared-for-root-contract-review'
    for key in ['selected', 'runtime', 'implementationAccepted', 'accountingAccepted',
                'nativeAccepted', 'gaAccepted', 'targetArtifactRead', 'gitQueried']:
        assert receipt[key] is False, key
    assert receipt['vmExecutions'] == receipt['nativeInstancesCreated'] == 0
    bindings = read(HERE / 'input-bindings.json')
    for name, pin in bindings.items():
        assert digest((HERE / 'inputs' / name).read_bytes()) == pin, name
    assert digest(encoded(bindings)) == receipt['inputBindingsSHA256']
    prefix = HERE / 'inputs/verification/swift-calls-dispatch-root-review/live-v7-integration-retry'
    manifest = read(prefix / 'final-live-manifest.json')
    assert len(manifest) == 130 and digest(encoded(manifest)) == BASELINE
    normalized = read(prefix / 'formatting-normalization.json')
    assert normalized['integratedSourceClosure'] == BASELINE and normalized['candidateSourceClosure'] == V7
    assert normalized['retainedOriginalCandidateUnchanged'] and not normalized['newRuntimeOrGAClaim']
    assert normalized['selectedLines'] == [598, 654, 669, 677, 690, 843, 859]
    assert normalized['freshPreNormalizationLiveAllFeatureTests'] == 342
    original = read(HERE / 'inputs/verification/swift-calls-dispatch/v7-fixture-expectations/candidate-final-manifest.json')
    assert len(original) == 130 and digest(encoded(original)) == V7
    changed = {name for name in manifest if manifest[name] != original[name]}
    assert changed == {'src/experimental/execution/borrowed.rs'}
    assert manifest['src/experimental/execution/borrowed.rs'] == normalized['integratedSHA256']
    assert original['src/experimental/execution/borrowed.rs'] == normalized['qualifiedSHA256']
    root_runtime = read(HERE / 'inputs/verification/swift-calls-dispatch-root-review/sealed-v7/runtime-review.json')
    assert root_runtime['privateRuntimeAccepted'] and root_runtime['candidateSourceClosure'] == V7
    assert root_runtime['plannedAndPassedCommands'] == 27
    live_run = read(prefix / 'live-check.json')
    assert live_run['passed'] and live_run['testsPassed'] and live_run['cleanupPassed']
    matrix = read(HERE / 'matrix.json')
    assert not matrix['selected'] and not matrix['runtime'] and matrix['runtimeRowsPassed'] == 0
    assert [row['id'] for row in matrix['groups']] == [f'SL{i:02}' for i in range(1, 25)]
    assert all(row['status'] == 'planned' and row['cases'] and row['assertions']
               and row['testPrefix'] == f'swift_lifecycle_sl{i:02}_'
               for i, row in enumerate(matrix['groups'], 1))
    assert len(matrix['futureCommands']) == 4
    assert all(row['status'] == 'planned' and row['argv'][1] == 'test'
               for row in matrix['futureCommands'])
    attempt = HERE / receipt['compositionAttempt']
    observed = read(attempt / 'receipt.json')
    assert observed['compositionPassed'] and observed['cleanupPassed'] and observed['liveBaselineRecheckedAfter']
    assert not observed['selected'] and not observed['runtime'] and not observed['targetArtifactRead']
    assert observed['vmExecutions'] == observed['nativeInstancesCreated'] == 0
    baseline = archive(attempt / 'baseline-source.tar.gz')
    assert len(baseline) == 130
    assert {name: digest(data) for name, data in baseline.items()} == manifest
    witness = archive(attempt / 'witness-source.tar.gz')
    witness_manifest = {name: digest(data) for name, data in witness.items()}
    assert len(witness) == 131
    assert witness_manifest == read(attempt / 'witness-manifest.json')
    witness_digest = digest(encoded(witness_manifest))
    assert witness_digest == observed['witnessClosure'] == receipt['witnessClosure']
    extra = 'src/experimental_swift_reactor/lifecycle_contract_probe.rs'
    frame = 'src/experimental_swift_reactor/frame_operations.rs'
    assert set(witness) - set(baseline) == {extra}
    assert witness[extra] == (HERE / 'composition_probe.rs').read_bytes()
    assert witness[frame] == baseline[frame] + b'\n#[path="lifecycle_contract_probe.rs"]\nmod lifecycle_contract_probe;\n'
    assert all(witness[name] == data for name, data in baseline.items() if name != frame)
    negative_digests = {}
    for name in ['owner-during-growth', 'ready-before-retained-completion']:
        negative = read(attempt / f'negative-{name}-manifest.json')
        assert set(negative) == set(witness_manifest)
        assert all(pin == witness_manifest[path] for path, pin in negative.items() if path != extra)
        assert digest((attempt / f'negative-{name}.rs').read_bytes()) == negative[extra]
        negative_digests['negative-' + name] = digest(encoded(negative))
    commands = read(attempt / 'commands.json')
    assert commands == observed['commands'] and len(commands) == 9
    expected = {'rustc-version', 'cargo-version', 'python-version', 'swift-debug',
                'swift-release', 'all-debug', 'all-release', *negative_digests}
    assert {row['label'] for row in commands} == expected
    for row in commands:
        raw = gzip.decompress((attempt / row['log']).read_bytes())
        assert digest(raw) == row['outputSHA256']
        assert row['sourceUnchanged'] and row['sourceBefore'] == row['sourceAfter']
        assert not row['remainingGroup'] and not row['timedOut']
        argv = row['argv']
        if row['label'] in negative_digests:
            assert not row['expectedSuccess'] and row['exitCode'] != 0
            assert row['sourceBefore'] == negative_digests[row['label']]
            assert b'lifecycle_contract_probe.rs' in raw
            assert any(code in raw for code in [b'error[E0499]', b'error[E0502]', b'error[E0506]'])
        else:
            assert row['expectedSuccess'] and row['exitCode'] == 0
            assert row['sourceBefore'] == witness_digest
        if row['target'] is not None:
            assert argv[1] == 'check' and '--lib' in argv and '--offline' in argv and '--locked' in argv
            assert 'test' not in argv and 'run' not in argv
    cleanup = read(attempt / 'cleanup.json')
    assert cleanup['ownedScratchRemoved'] and cleanup['holderCheckEmpty'] and cleanup['groupsEmpty']
    assert not any(cleanup['remainingCommandGroups'].values())
    assert cleanup['scratch'] == observed['scratch']
    if args.live:
        assert not Path(cleanup['scratch']).exists()
        for name, pin in manifest.items():
            assert digest((ROOT / 'vm' / name).read_bytes()) == pin, name
        for name, pin in bindings.items():
            assert digest((ROOT / name).read_bytes()) == pin, name
    print(json.dumps({'status': 'passed-read-only-contract-packet-verification',
                      'selected': False, 'runtime': False, 'baselineFiles': 130,
                      'baselineClosure': BASELINE, 'witnessFiles': 131,
                      'witnessClosure': witness_digest, 'recordedCommands': 9,
                      'positiveProductionTypecheckContexts': 4,
                      'expectedBorrowRejections': 2, 'runtimeGroupsPlanned': 24,
                      'vmExecutions': 0, 'targetArtifactRead': False,
                      'liveSourceChecked': args.live, 'accountingAccepted': False}, sort_keys=True))

if __name__ == '__main__':
    main()
