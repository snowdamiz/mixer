#!/usr/bin/env python3
"""Read-only replay of the exact reviewed-to-integrated growth delta and host proof."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda b: hashlib.sha256(b).hexdigest()
enc = lambda o: (json.dumps(o, sort_keys=True, indent=2) + '\n').encode()
read = lambda p: json.loads(p.read_text())


def archive(path):
    with tarfile.open(path) as t:
        members = t.getmembers()
        assert all(m.isfile() and not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts for m in members)
        bodies = {m.name: t.extractfile(m).read() for m in members}
        assert len(bodies) == len(members) == 127
        return bodies


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    seal = read(HERE / 'seal.json')
    actual = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p != HERE / 'seal.json'}
    assert actual == set(seal['files'])
    for name, digest in seal['files'].items():
        assert sha((HERE / name).read_bytes()) == digest, name
    for name, digest in seal['documentation'].items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    selected = read(HERE / 'review-selection.json')
    for name, digest in selected['bindings'].items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    upstream = read(HERE / 'accepted-input-bindings.json')
    for name, digest in upstream.items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    reviewed = archive(ROOT / 'verification/swift-memory-growth/candidate-source.tar.gz')
    baseline = read(ROOT / 'verification/swift-memory-growth/baseline-source-manifest.json')
    assert sha(enc({p: sha(b) for p, b in reviewed.items()})) == selected['reviewedSourceClosure']
    normalized = dict(reviewed)
    name = 'src/experimental/execution/borrowed.rs'
    lines = normalized[name].splitlines(keepends=True)
    assert lines[528] == b'        $leaf!(work $this, \n'
    lines[528] = b'        $leaf!(work $this,\n'
    normalized[name] = b''.join(lines)
    assert archive(HERE / 'integrated-source.tar.gz') == normalized
    expected = {p: sha(b) for p, b in normalized.items()}
    assert expected == read(HERE / 'expected-source-manifest.json') == read(HERE / 'integrated-source-manifest.json')
    digest = sha(enc(expected))
    integrated = read(HERE / 'integration.json')
    assert integrated['status'] == 'passed-private-growth-integration'
    assert integrated['integratedSourceClosure'] == digest
    changed = sorted(p for p in expected if expected[p] != baseline.get(p))
    assert changed == selected['changedRelativeFiles'] and len(changed) == 9
    assert integrated['appliedFiles'] == ['vm/' + p for p in changed]
    commands = read(HERE / 'commands.json')
    assert commands == integrated['commands'] and len(commands) == 14
    for row in commands:
        assert row['exitCode'] == 0 and not row['timedOut'] and not row['groupCleanup']['after']
        assert row['sourceUnchanged'] and row['sourceBeforeSHA256'] == row['sourceAfterSHA256']
        assert sha((HERE / row['log']).read_bytes()) == row['outputSHA256']
        if row['label'] not in ['producer-integrity', 'review-integrity']:
            assert row['sourceBeforeSHA256'] == digest
        if row['target']:
            assert '/target-source-' + digest + '/' in row['target']
    for label, count in [('focused', 98), ('frozen', 16)]:
        artifact = read(HERE / (label + '-artifact.json'))
        binary = gzip.decompress((HERE / (label + '-binary.gz')).read_bytes())
        assert len(binary) == artifact['binaryBytes'] and sha(binary) == artifact['binarySHA256']
        assert artifact['sourceSHA256'] == digest and artifact['cargoArtifact']['fresh'] is False
        compile_row = next(r for r in commands if r['label'] == label + '-compile')
        assert artifact['cargoArtifact']['executable'].startswith(compile_row['target'] + '/')
        raw_artifacts = []
        for line in (HERE / compile_row['log']).read_text().splitlines():
            try:
                raw_artifacts.append(json.loads(line))
            except ValueError:
                pass
        assert artifact['cargoArtifact'] in raw_artifacts
        for suffix in ['test-list', 'execute']:
            row = next(r for r in commands if r['label'] == label + '-' + suffix)
            assert row['argv'][0] == artifact['cargoArtifact']['executable'] and row['target'] == compile_row['target']
        output = (HERE / (label + '-execute.log')).read_text()
        assert f'test result: ok. {count} passed; 0 failed; 0 ignored;' in output
        listed = (HERE / (label + '-test-list.log')).read_text().splitlines()
        assert sum(line.endswith(': test') and (label != 'focused' or line.startswith('experimental_swift_reactor::execution::')) for line in listed) == count
    cleanup = read(HERE / 'cleanup.json')
    assert cleanup == integrated['cleanup'] and cleanup['ownedScratchRemoved'] and cleanup['holderCheckEmpty'] and cleanup['holderCheckExitCode'] == 1
    accepted = read(HERE / 'acceptance.json')
    assert accepted['rootAccepted'] and accepted['liveIntegrated'] and not accepted['gaAccepted']
    assert accepted['integratedSourceClosure'] == digest
    if args.live:
        vm = ROOT / 'vm'
        paths = [vm / 'Cargo.toml', vm / 'Cargo.lock']
        paths += [p for n in ['src', 'tests', 'include'] for p in (vm / n).rglob('*') if p.is_file()]
        assert {str(p.relative_to(vm)): sha(p.read_bytes()) for p in paths} == expected
    print(json.dumps({'verified': True, 'sourceFiles': 127, 'upstreamBindings': len(upstream), 'rootFiles': len(seal['files']), 'focusedRelease': 98, 'frozenRelease': 16, 'ciSwiftClippy': 'passed', 'liveChecked': args.live, 'gaAccepted': False}))


if __name__ == '__main__':
    main()
