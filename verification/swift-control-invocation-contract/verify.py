#!/usr/bin/env python3
"""Offline verification of the sealed declaration packet, not product behavior."""
from pathlib import Path
import ast, hashlib, json, re, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
encoded = lambda value: (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
sha_bytes = lambda data: hashlib.sha256(data).hexdigest()
sha = lambda path: sha_bytes(path.read_bytes())
digest = lambda value: sha_bytes(encoded(value))

def verify_run(path):
    receipt = json.loads(path.read_text())
    out = path.parent
    baseline = json.loads((out/'source-manifest.json').read_text())
    overlay = json.loads((out/'overlay-manifest.json').read_text())
    assert len(baseline) == receipt['sourceFiles'] == 119
    assert digest(baseline) == receipt['sourceTreeSHA256'] == '4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4'
    assert digest(overlay) == receipt['overlayTreeSHA256']
    with tarfile.open(out/'source.tar.gz') as archive:
        contents = {member.name.removeprefix('vm/'): archive.extractfile(member).read()
                    for member in archive if member.isfile()}
    assert {name: sha_bytes(data) for name, data in contents.items()} == baseline
    collector = ast.parse((out/'collect.py').read_text())
    accessors = next(ast.literal_eval(node.value) for node in collector.body
                     if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'ACCESSORS' for target in node.targets))
    contents['src/experimental/execution/borrowed.rs'] += b'\n' + (out/'generalized-methods.rs').read_bytes()
    contents['src/experimental/execution/mod.rs'] += accessors.encode()
    contents['src/experimental_swift_reactor/frame_operations.rs'] += b'\n#[cfg(test)]\n#[path = "contract_probe.rs"]\nmod contract_probe;\n'
    contents['src/experimental_swift_reactor/contract_probe.rs'] = (out/'probe.rs').read_bytes()
    assert {name: sha_bytes(data) for name, data in contents.items()} == overlay
    assert receipt['liveVMUnchanged']
    for command in receipt['commands']:
        assert command['baselineSHA256'] == digest(baseline)
        assert command['overlaySHA256'] == digest(overlay)
        for stream in ['stdout','stderr']:
            assert sha(out/command[stream]) == command[stream+'SHA256']
    cleanup = json.loads((out/'cleanup.json').read_text())
    assert cleanup['buildRemoved'] and not cleanup['nativeInstancesStarted']
    assert not Path(cleanup['removed']).exists()
    if receipt['status'] == 'passed-declaration-borrow-layout-only':
        assert set(receipt['layouts']) == {'swift-debug','swift-release','all-debug','all-release'}
        for label, rows in receipt['layouts'].items():
            assert len(rows) == 17
            raw=(out/(label+'.stdout')).read_text()
            actual={kind:int(size) for kind,size in re.findall(r'contract_size\|([^|\n]+)\|(\d+)',raw)}
            assert actual == rows == receipt['layouts']['swift-debug']
            assert re.search(r'test result: ok\. 1 passed; 0 failed;',raw)
        assert all(command['exitCode']==0 for command in receipt['commands'])
    assert not any(receipt[k] for k in ['implementationAccepted','accountingAccepted','nativeRuntime','physicalRuntime','gaAcceptance'])
    return receipt

def main():
    seal = json.loads((HERE/'seal.json').read_text())
    for name, expected in seal['files'].items():
        assert sha(ROOT/name)==expected, name
    summary = json.loads((HERE/'summary.json').read_text())
    receipts=[verify_run(path) for path in sorted((HERE/'results').glob('*/receipt.json'))]
    qualifying=verify_run(ROOT/summary['qualifyingReceipt'])
    assert qualifying['status']=='passed-declaration-borrow-layout-only'
    assert (ROOT/summary['qualifyingReceipt']).parent.joinpath('probe.rs').read_bytes()==(HERE/'probe.rs').read_bytes()
    assert (ROOT/summary['qualifyingReceipt']).parent.joinpath('collect.py').read_bytes()==(HERE/'collect.py').read_bytes()
    assert summary['qualifyingMetadataTests']==4
    print(json.dumps(dict(status='passed-offline-declaration-packet-verification',runs=len(receipts),qualifyingMetadataTests=4,
        sourceTreeSHA256=qualifying['sourceTreeSHA256'],implementationAccepted=False,accountingAccepted=False),sort_keys=True))

if __name__ == '__main__': main()
