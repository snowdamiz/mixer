"""Read-only exact integration replay; source archives retain historical baselines."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    seal = read(HERE / 'seal.json')
    actual = {str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p != HERE / 'seal.json'}
    actual.add('docs/stripe-raw-body-integration.md')
    assert actual == set(seal)
    for name, entry in seal.items():
        p = ROOT / name
        assert not p.is_symlink() and sha(p) == entry['sha256'] and p.stat().st_size == entry['bytes'], name
    accepted = read(HERE / 'acceptance.json')
    assert accepted['status'] == 'accepted-and-integrated-private-raw-capture-only'
    assert accepted['liveIntegrated'] and not accepted['publicAdmissionAccepted'] and not accepted['gaAccepted']
    for name, digest in accepted['bindings'].items():
        assert sha(ROOT / name) == digest, name
    attempt = HERE / 'attempt-1'
    composed = read(attempt / 'receipt.json')
    nested = read(attempt / 'hosted/receipt.json')
    expected = read(attempt / 'source-inputs.json')
    assert expected == accepted['sourceInputs'] == nested['inputs'] and len(expected) == 71
    digest = hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert digest == accepted['sourceDigest'] == nested['source_tree_sha256'] == composed['sourceDigest']
    with tarfile.open(attempt / 'hosted/source.tar.gz') as archive:
        observed = {}
        for member in archive.getmembers():
            p = PurePosixPath(member.name)
            assert member.isfile() and not p.is_absolute() and '..' not in p.parts and member.name not in observed
            observed[member.name] = hashlib.sha256(archive.extractfile(member).read()).hexdigest()
        assert observed == expected
    assert sha(attempt / 'hosted/source.tar.gz') == nested['source_archive_sha256']
    for name, digest in expected.items():
        assert sha(attempt / 'source' / name) == digest
        if args.live:
            assert sha(ROOT / name) == digest, name
    reviewed = ROOT / 'verification/stripe-raw-body-capture/candidate/lib/mixer_hosted/billing/raw_webhook_capture.ex'
    normalized = attempt / 'source/hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex'
    assert normalized.read_bytes() == reviewed.read_bytes().rstrip(b'\n') + b'\n'
    assert composed['productionNormalization'] == accepted['normalization']
    for command in composed['commands']:
        assert sha(attempt / command['output']) == command['outputSHA256']
        assert not command['timedOut'] and not command['groupCleanup']['after']
        assert command['exitCode'] == (1 if command['label'] == 'scratch-holders' else 0)
    for command in nested['commands']:
        assert sha(attempt / 'hosted' / command['log']) == command['sha256']
        assert command['exit_code'] == command.get('expected_exit_code', 0)
    assert nested['status'] == 'passed' and nested['cleanup'] == {'postgres_stopped': True, 'scratch_removed': True}
    assert composed['scratchCleanup']['pathAbsent'] and not Path(composed['scratchCleanup']['path']).exists()
    assert 'Result: 142 passed, 2 skipped' in (attempt / 'hosted/tests.log').read_text()
    release = (attempt / 'hosted/release-test-exclusion.log').read_text()
    assert 'test_clock_absent: true' in release and 'test_adapter_absent: true' in release
    print(json.dumps({'verified': True, 'integrationFiles': len(seal), 'upstreamBindings': len(accepted['bindings']),
                      'sourceFiles': 71, 'hostPassed': 142, 'hostSkipped': 2, 'liveChecked': args.live,
                      'publicAdmissionAccepted': False, 'gaAccepted': False}))


if __name__ == '__main__':
    main()
