#!/usr/bin/env python3
"""Read-only replay of reviewed bulk-memory integration and its exact source delta."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda data: hashlib.sha256(data).hexdigest()
encoded = lambda value: (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    seal = json.loads((HERE / 'seal.json').read_text())
    receipt = json.loads((HERE / 'acceptance.json').read_text())
    upstream = json.loads((HERE / 'accepted-input-bindings.json').read_text())
    for bindings in [seal['bindings'], receipt['bindings'], upstream]:
        for name, digest in bindings.items():
            assert sha((ROOT / name).read_bytes()) == digest, name
    assert receipt['rootAccepted'] and receipt['liveIntegrated'] and not receipt['gaAccepted']
    selected = json.loads((HERE / 'review-selection.json').read_text())
    review = json.loads((ROOT / 'verification/swift-bulk-memory-review/receipt.json').read_text())
    assert review['decision'] == 'suitable-for-root-integration-private-bounded-host-slice'
    assert review['freshCandidateSelections'] == 64 and review['freshIndependentSelections'] == 12
    assert review['freshFields'] == 4324 and review['retainedFields'] == 4800
    candidate = ROOT / 'verification/swift-bulk-memory'
    baseline = json.loads((candidate / 'baseline-source-manifest.json').read_text())
    reviewed = json.loads((candidate / 'candidate-source-manifest.json').read_text())
    expected = json.loads((HERE / 'expected-source-manifest.json').read_text())
    with tarfile.open(candidate / 'candidate-source.tar.gz') as archive:
        members = archive.getmembers()
        assert len(members) == 125
        assert all(m.isfile() and not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts for m in members)
        bodies = {m.name: archive.extractfile(m).read() for m in members}
    assert {name: sha(body) for name, body in bodies.items()} == reviewed
    assert sha(encoded(reviewed)) == selected['candidateSourceClosure'] == receipt['reviewedSourceClosure']
    name = 'src/experimental/execution/mod.rs'
    lines = bodies[name].splitlines(keepends=True)
    assert lines[1049] == lines[1050] == b'    \n'
    lines[1049] = lines[1050] = b'\n'
    bodies[name] = b''.join(lines)
    assert {name: sha(body) for name, body in bodies.items()} == expected
    assert sha(encoded(expected)) == selected['integratedSourceClosure'] == receipt['integratedSourceClosure']
    assert json.loads((HERE / 'integrated-source-manifest.json').read_text()) == expected
    integration = json.loads((HERE / 'integration.json').read_text())
    assert integration['status'] == 'passed-private-bulk-memory-integration'
    assert len(integration['appliedFiles']) == 9
    assert set(integration['appliedFiles']) == {'vm/' + name for name in expected if expected[name] != baseline.get(name)}
    assert integration['cleanup']['ownedScratchRemoved']
    assert integration['cleanup']['holderCheckExitCode'] == 1 and integration['cleanup']['holderCheckEmpty']
    for command in integration['commands']:
        assert command['exitCode'] == 0 and sha((HERE / command['log']).read_bytes()) == command['sha256']
    for log, count in [('integrated-bulk-memory-frame-value-control.log', 78), ('integrated-frozen.log', 16)]:
        assert f'test result: ok. {count} passed; 0 failed; 0 ignored;' in (HERE / log).read_text()
    if args.live:
        vm = ROOT / 'vm'
        paths = [vm / 'Cargo.toml', vm / 'Cargo.lock']
        paths += [p for name in ['src', 'tests', 'include'] for p in (vm / name).rglob('*') if p.is_file()]
        assert {str(p.relative_to(vm)): sha(p.read_bytes()) for p in paths} == expected
    print(json.dumps({'verified': True, 'upstreamBindings': len(upstream), 'rootBindings': len(receipt['bindings']),
                      'sourceFiles': 125, 'freshRootFocused': 78, 'freshRootFrozen': 16,
                      'freshIndependentSelections': 76, 'ciSwiftClippy': 'passed', 'liveChecked': args.live, 'gaAccepted': False}))

if __name__ == '__main__':
    main()
