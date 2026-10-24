#!/usr/bin/env python3
"""Read-only V3 source, raw compiler, ordered proof and cleanup replay.

No compiler, test binary, subprocess, scratch, source or output mutation occurs.
"""
from pathlib import Path
import collections, gzip, hashlib, json, tarfile
import collect as c
import prepare
import reconcile

HERE, ROOT = c.HERE, c.ROOT
OLD = ROOT / 'verification/swift-reactor-lifecycle-runtime-v2'
SOURCE = '93adb6ac2d00acab30c02df8d96e044452edc14d704a6738a58874b0968b5f38'

def verify():
    assert c.sha((OLD / 'seal.json').read_bytes()) == '36d70c601ce2930ef18ca7adb58dcb96b4e3e3e15d816406c0b7df092e81d749'
    for name, pin in c.read_json(OLD / 'seal.json')['files'].items():
        assert c.sha((OLD / name).read_bytes()) == pin, ('prior sealed file', name)
    source = c.manifest(HERE / 'candidate')
    assert source == c.read_json(HERE / 'candidate-manifest.json')
    assert c.sha(c.enc(source)) == SOURCE
    before = c.manifest(OLD / 'candidate')
    assert c.sha(c.enc(before)) == '0fa7ae254ac2b3aa3390e6fbc935e920422fc9024db220256074ec6ef4e3cd56'
    assert set(before) == set(source)
    assert [name for name in source if before[name] != source[name]] == [prepare.FILE]
    assert prepare.mask((OLD / 'candidate' / prepare.FILE).read_text()) == prepare.mask((HERE / 'candidate' / prepare.FILE).read_text())
    assert c.sha((HERE / 'test-repair-selection.json').read_bytes()) == '27c2c8a4a134a5c1d3b4510487b4c67eb95a1cd75b36d9b688c0c5f320ac096e'
    assert (HERE / 'test-repair-selection.json').read_bytes() == prepare.SELECTION.read_bytes()
    # The accepted finite rules and annotation partition are exact, not broadened.
    old_script = (OLD / 'reconcile_runtime.py').read_text()
    a, b = old_script.index('def footer('), old_script.index('def main():')
    assert (HERE / 'finite_metadata.py').read_text() == '"""Exact V2 accepted finite representation rules; no broader normalization."""\nimport re\n' + old_script[a:b]
    assert (HERE / 'partition_annotations.py').read_bytes() == (ROOT / 'verification/swift-reactor-lifecycle-accounting/partition_annotations.py').read_bytes()
    # Fresh raw streams, full body graphs, all positions and role joins regenerate exactly.
    generated = reconcile.build()
    for name, raw in generated.items():
        assert (HERE / name).read_bytes() == raw, ('regenerated proof', name)
    summary = json.loads(generated['unchanged-runtime-proof.json'])
    roles = json.loads(generated['role-reconciliation-summary.json'])
    assert summary['runtimeBodies'] == 160 and summary['positions'] == 2744
    assert summary['fullOwnerCarrierDeclarations'] == 116
    assert summary['fullTypeGraphAndLayoutRecords'] == 2330
    assert summary['ctfeAnnotations'] == 256
    assert summary['sourceCoordinatesAndScopeChanges'] == 0
    assert summary['canonicalActualBodyChanges'] == 0
    assert roles['fourRoleJoins'] == 11760 and roles['functionItemZeroByteRoleJoins'] == 1296
    assert roles['kinds']['constant-operand'] == 498
    baseline_query = c.read_json(OLD / 'exact-query-swift-debug-unit.json')
    baseline = c.read_json(OLD / baseline_query['attempt'] / 'tools.json')['actualCompiler']
    attempts = sorted((HERE / 'attempts').iterdir())
    assert len(attempts) == 5
    for attempt in attempts:
        command = c.read_json(attempt / 'command.json')
        tools = c.read_json(attempt / 'tools.json')
        cleanup = c.read_json(attempt / 'cleanup.json')
        assert command['argv'][:3] == ['cargo', 'rustc', '--lib']
        assert command['exitCode'] == 0 and command['sourceUnchanged']
        assert not command['remainingGroup']
        assert cleanup['removed'] and cleanup['holderCheckEmpty'] and not cleanup['remainingGroup']
        assert not Path(cleanup['scratch']).exists()
        assert tools['actualCompiler'] == baseline
        assert command['sourceClosure'] == SOURCE
        for stream in ['stdout', 'stderr']:
            raw = gzip.decompress((attempt / (stream + '.log.gz')).read_bytes())
            assert c.sha(raw) == command[stream + 'SHA256']
        assert c.read_json(attempt / 'source-manifest.json') == source
        with tarfile.open(attempt / 'source.tar.gz', 'r:gz') as archive:
            members = archive.getmembers()
            assert len(members) == len(source)
            assert {m.name: c.sha(archive.extractfile(m).read()) for m in members} == source
        for artifact in c.read_json(attempt / 'artifacts.json'):
            raw = gzip.decompress((attempt / artifact['path']).read_bytes())
            assert len(raw) == artifact['bytes'] and c.sha(raw) == artifact['sha256']
    compiler = c.read_json(HERE / 'compiler-results.json')
    assert [x['context'] for x in compiler] == ['swift-debug-unit','swift-release-unit','all-debug-unit','all-release-unit']
    for query in compiler:
        assert query['sourceClosure'] == SOURCE and query['exitCode'] == 0 and not query['runtimeExecuted']
        assert query == c.read_json(HERE / ('exact-query-' + query['context'] + '.json'))
        raw = gzip.decompress((HERE / query['attempt'] / 'exact-layouts.jsonl.gz').read_bytes())
        assert len(raw) == query['bytes'] and len(raw.splitlines()) == query['records'] and c.sha(raw) == query['sha256']
    frozen = c.read_json(HERE / 'frozen-identity-proof.json')
    assert frozen['methods'] == 39 and frozen['sourceClosure'] == SOURCE
    assert frozen['oldExpandedMethods'] == frozen['newExpandedMethods']
    assert frozen['methodSHA256'] == {k: c.sha(v.encode()) for k, v in frozen['newExpandedMethods'].items()}
    metadata_cleanup = c.read_json(HERE / 'metadata-tool-cleanup.json')
    assert metadata_cleanup['removed'] and metadata_cleanup['holderCheckEmpty']
    assert not Path(metadata_cleanup['scratch']).exists()
    for name in ['authored-coverage.json', 'planned-matrix-unchanged.json']:
        assert (HERE / name).read_bytes() == (OLD / name).read_bytes()
    if (HERE / 'receipt.json').exists():
        receipt = c.read_json(HERE / 'receipt.json')
        assert c.sha((ROOT / 'docs/swift-reactor-lifecycle-runtime-v3.md').read_bytes()) == receipt['documentSHA256']
    if (HERE / 'seal.json').exists():
        seal = c.read_json(HERE / 'seal.json')
        assert seal['candidateClosure'] == SOURCE
        for name, pin in seal['files'].items():
            assert c.sha((HERE / name).read_bytes()) == pin, ('sealed packet file', name)
        assert c.sha(c.enc(seal['files'])) == seal['closureSHA256']
    return {'verified': True, 'candidateClosure': SOURCE, 'runtimeBodies': 160, 'rawOccurrences': 2744, 'constantOccurrences': 498, 'fourRoleJoins': 11760, 'functionItemZeroByteRoleJoins': 1296, 'FrozenMethodsExact': 39, 'compilerContexts': 4, 'runtimeExecuted': False, 'finiteRepresentationRootSelectionPending': True, 'allOwnedScratchCleaned': True}

if __name__ == '__main__':
    print(c.enc(verify()).decode())
