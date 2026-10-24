#!/usr/bin/env python3
"""Offline integrity/behavior-receipt audit; does not run devices or mutate VM."""
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda body: hashlib.sha256(body).hexdigest()
enc = lambda value: (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
read = lambda name: json.loads((HERE / name).read_text())

def source_archive(name):
    with tarfile.open(HERE / name) as archive:
        entries = archive.getmembers()
        assert all(entry.isfile() and not PurePosixPath(entry.name).is_absolute() and '..' not in PurePosixPath(entry.name).parts for entry in entries)
        return {entry.name: archive.extractfile(entry).read() for entry in entries}

def main():
    seal = read('seal.json')
    actual_files = {str(path.relative_to(HERE)) for path in HERE.rglob('*') if path.is_file() and path != HERE / 'seal.json'}
    assert actual_files == set(seal['files']), 'packet path set drift'
    for relative, digest in seal['files'].items():
        assert sha((HERE / relative).read_bytes()) == digest, relative
    for relative, digest in seal['externalFiles'].items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    bindings = read('input-bindings.json')
    for relative, digest in bindings.items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    for path in (HERE / 'inputs').rglob('*'):
        if path.is_file():
            assert sha(path.read_bytes()) == bindings[str(path.relative_to(HERE / 'inputs'))]
    receipt = read('receipt.json')
    assert receipt['status'] == 'baseline-attribution-gap-reproduced-contract-only'
    assert all(receipt[name] is False for name in ['liveVmWritten', 'implementationAuthorized', 'g08Accepted', 'fullSwiftAccepted', 'nativeAccepted', 'releaseAccepted', 'gaAccepted'])
    baseline = source_archive('baseline-source.tar.gz')
    probe = source_archive('probe-source.tar.gz')
    for context, bodies in [('baseline', baseline), ('probe', probe)]:
        manifest = {name: sha(body) for name, body in bodies.items()}
        assert len(manifest) == 127 and manifest == read(context + '-source-manifest.json')
        expected = receipt['contexts'][context]
        assert sha(enc(manifest)) == expected['sourceSHA256']
        artifact = read(context + '-artifact.json')
        assert artifact['sourceSHA256'] == expected['sourceSHA256']
        assert sha(gzip.decompress((HERE / (context + '-binary.gz')).read_bytes())) == artifact['binarySHA256'] == expected['binarySHA256']
        assert artifact['cargoArtifact']['fresh'] is False
        assert artifact['features'] == 'all' and artifact['profile'] == 'release'
        listed = (HERE / (context + '-test-list.log')).read_text().splitlines()
        full = [line.removesuffix(': test') for line in listed if line.endswith(': test')]
        assert len(full) == expected['fullTestCount'] == (249 if context == 'baseline' else 252)
        for index, test in enumerate(expected['selectedTests'], 1):
            assert full.count(test) == 1
            output = (HERE / (context + '-test-' + str(index) + '.log')).read_text()
            assert 'running 1 test\n' in output and 'test result: ok. 1 passed; 0 failed; 0 ignored;' in output
    changed = sorted(name for name in baseline if baseline[name] != probe[name])
    assert changed == ['src/experimental_swift_reactor/control_tests.rs', 'src/experimental_swift_reactor/memory_operations_tests.rs']
    for leaf, target in [('control_probe.rs', changed[0]), ('memory_probe.rs', changed[1])]:
        assert probe[target] == baseline[target] + (HERE / leaf).read_bytes()
    assert receipt['acceptedBaselineSourceSHA256'] == 'a0bbe77aca3021e48f1fb76dc97cfbc0406c24e5ba7eacdd33d5dabe8f998d9b'
    commands = read('commands.json')
    assert commands == receipt['commands'] and len(commands) == 16
    targets = {row['environment']['CARGO_TARGET_DIR'] for row in commands if row['label'].endswith('-compile')}
    assert len(targets) == 2 and None not in targets
    for row in commands:
        assert row['exitCode'] == 0 and not row['timedOut'] and row['sourceUnchanged']
        assert row['sourceBeforeSHA256'] == row['sourceAfterSHA256']
        assert not row['groupCleanup']['after']
        assert sha((HERE / row['log']).read_bytes()) == row['outputSHA256']
    cleanup = read('cleanup.json')
    assert cleanup == receipt['cleanup'] and cleanup['ownedScratchRemoved']
    assert cleanup['holderCheckExitCode'] == 1 and cleanup['holderCheckEmpty'] and not cleanup['groupCleanup']['after']
    assert not (HERE / 'cleanup-open-holders.log').read_bytes()
    assert cleanup['nativeInstancesStarted'] == cleanup['physicalRuns'] == 0
    matrix = read('repair-acceptance-matrix.json')
    assert matrix['status'] == 'pending-no-implementation-candidate' and not matrix['implementationAuthorized']
    assert len(matrix['requiredProducerGroups']) == 16 and all(row['status'] == 'pending' for row in matrix['requiredProducerGroups'])
    inventory = read('callsite-inventory.json')
    assert inventory['productionCallsiteCount'] == len(inventory['productionCallsites']) == 12
    for row in inventory['productionCallsites']:
        body = baseline[row['source']]
        assert sha(body) == row['sourceSHA256']
        assert 'remove_live_with_wasi(' in body.decode().splitlines()[row['line'] - 1]
    assert 'actualFunction=34 actualOffset=1713 actualStage=Invocation reportedStage=Cleanup function=None offset=None resource=None' in (HERE / 'probe-test-1.log').read_text()
    print(json.dumps({'status': 'passed-contract-only-audit', 'sealedFiles': len(seal['files']),
        'boundInputs': len(bindings), 'baselineTestsExecuted': 5, 'probeGroupsExecuted': 3,
        'productionCallsites': 12, 'repairGroupsPending': 16, 'g08Accepted': False,
        'scratchRemoved': True}, sort_keys=True))

if __name__ == '__main__':
    main()
