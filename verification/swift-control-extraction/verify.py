#!/usr/bin/env python3
"""Verify the saved control-adapter accounting rejection; no product acceptance."""
from pathlib import Path
import hashlib
import json
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'results/20261024T025535989853Z'


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    receipt = json.loads((OUT / 'receipt.json').read_text())
    assert receipt['status'] == 'rejected-chosen-fallible-control-transfer-inventory'
    assert receipt['productVMUnchanged'] is True
    assert receipt['implementationApplied'] is False
    assert receipt['productTestsExecuted'] is False
    assert receipt['nativeRuntimeExecuted'] is False
    assert receipt['computerUsePerformed'] is False
    source = json.loads((OUT / 'source-manifest.json').read_text())
    assert len(source) == receipt['sourceFiles'] == 116
    assert hashlib.sha256(encoded(source)).hexdigest() == receipt['sourceTreeSHA256']
    assert sha(OUT / 'source.tar.gz') == receipt['sourceArchiveSHA256']
    with tarfile.open(OUT / 'source.tar.gz') as archive:
        archived = {member.name.removeprefix('vm/'): archive.extractfile(member).read()
                    for member in archive.getmembers() if member.isfile()}
    assert {name: hashlib.sha256(data).hexdigest() for name, data in archived.items()} == source
    for name, digest in source.items():
        assert sha(ROOT / 'vm' / name) == digest, name
    assert sha(OUT / 'inputs/root-freeze.json') == receipt['rootFreezeSHA256']
    for name in ['preflight.py', 'control_candidate.rs']:
        assert (HERE / name).read_bytes() == (OUT / 'inputs' / name).read_bytes()
    for command in receipt['commands']:
        assert command['exitCode'] == 0, command['name']
        assert sha(OUT / command['output']) == command['outputSHA256'], command['name']
    expected = dict(source)
    suffix = '\n#[cfg(test)]\nmod control_preflight {\nuse super::*;\n' + (OUT / 'inputs/control_candidate.rs').read_text() + '\n}\n'
    expected['src/experimental/execution/borrowed.rs'] = hashlib.sha256(
        archived['src/experimental/execution/borrowed.rs'] + suffix.encode()).hexdigest()
    assert len(receipt['variants']) == len(receipt['binaries']) == len(receipt['measurements']) == 4
    for variant in receipt['variants']:
        actual = json.loads((OUT / variant['manifest']).read_text())
        assert actual == expected
        assert hashlib.sha256(encoded(actual)).hexdigest() == variant['treeSHA256']
    identity = 'experimental::execution::borrowed::control_preflight::control_adapter_transfer_accounting_probe'
    for binary in receipt['binaries']:
        assert sha(Path(binary['path'])) == binary['sha256']
        assert binary['executedTest'] == identity
        assert identity + ': test' in (OUT / (binary['testListCommand'] + '.log')).read_text().splitlines()
        output = (OUT / (binary['runCommand'] + '.log')).read_text()
        assert 'test result: ok. 1 passed; 0 failed; 0 ignored;' in output
        assert 'failure=392 unit_result=392 value_result=392 bool_result=392 i32_result=392 transfer=1176 align=8 scalar_component=512 overflow=664 frozen_formula=2912 minimum_with_new_transfers=3576' in output
    for measurement in receipt['measurements']:
        assert measurement['metadataOnly'] is True
        assert measurement['guestExecution'] is False
        assert measurement['records'] == receipt['measurements'][0]['records']
    summary = dict(status='verified-chosen-inventory-rejection-not-implementation-pass',
                   sourceFiles=116, metadataProbeExecutions=4,
                   newTransferBytes=1176, scalarCeilingBytes=512, uncoveredBytesAtLeast=664,
                   productVMUnchanged=True, semanticAcceptance=False,
                   alternative='proposed private macro; needs separate root freeze')
    (HERE / 'verified-summary.json').write_bytes(encoded(summary))
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
