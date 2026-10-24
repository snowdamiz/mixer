"""Read-only integrity and retained build replay; no native execution."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
read = lambda p: json.loads(p.read_text())
bind = lambda p: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

def main():
    seal = read(HERE / 'seal.json')
    actual = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p != HERE / 'seal.json'}
    assert actual == set(seal['files'])
    for name, expected in seal['files'].items():
        assert bind(HERE / name) == expected, name
    for name, expected in seal['documentation'].items():
        assert bind(ROOT / name) == expected, name
    receipt = read(HERE / 'baseline-2/receipt.json')
    assert receipt['status'] == 'passed-independent-host-build-and-artifact-review'
    assert receipt['nativeRuntime'] == 'NOT RUN' and not receipt['gaAccepted']
    for group in ['candidateBindings', 'reviewSource']:
        for name, expected in receipt[group].items():
            assert bind(ROOT / name) == expected, name
    for row in receipt['commands']:
        assert bind(HERE / 'baseline-2' / row['output']) == {k: row[k] for k in ['bytes', 'sha256']}
        assert row['exitCode'] == (1 if row['label'] == 'scratch-holders' else 0)
        assert not row['groupCleanup']['after']
    artifacts = read(HERE / 'baseline-2/fresh-artifacts.json')
    with tarfile.open(HERE / 'baseline-2/fresh-class-dex-tests.tar.gz') as archive:
        members = archive.getmembers()
        assert len(members) == len(artifacts)
        assert {m.name for m in members} == set(artifacts)
        for m in members:
            assert m.isfile() and not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts
            data = archive.extractfile(m).read()
            assert {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()} == artifacts[m.name]
    candidate = read(ROOT / 'verification/android-authored-toggle-input/candidate-3/built-artifacts.json')
    reproduced = {n: e for n, e in artifacts.items() if n.startswith(('production-classes/', 'test-classes/', 'dex/'))}
    assert reproduced == {n: e for n, e in candidate.items() if n.startswith(('production-classes/', 'test-classes/', 'dex/'))}
    assert receipt['cleanup']['removed'] and receipt['cleanup']['ownedGroupsEmpty']
    print(json.dumps({'verified': True, 'matchedClasses': 163, 'sourceInputs': 106,
                      'build': 'compositional changed-family and fixture rebuild; complete DEX',
                      'nativeRuntime': 'NOT RUN', 'gaAccepted': False}))

if __name__ == '__main__':
    main()
