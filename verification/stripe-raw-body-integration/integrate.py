"""One-time integration of the independently reviewed, composed private capture."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())


def main():
    assert not (HERE / 'acceptance.json').exists(), 'one-time integration only'
    bindings = {}
    for name, digest in [
        ('stripe-raw-body-capture', '52f4c4aadd5ee949521c906bf2306ad5a77d0f4f61b53db2cee054ac38bd3c31'),
        ('stripe-raw-body-capture-review', 'afa16aa81097fc54781d3065a004d3f950fc2185342c9aff2c9e043bf50a785c')
    ]:
        seal = ROOT / 'verification' / name / 'seal.json'
        assert sha(seal) == digest
        bindings[str(seal.relative_to(ROOT))] = digest
        for path, item in read(seal).items():
            p = ROOT / path
            assert p.is_file() and not p.is_symlink()
            assert p.stat().st_size == item['bytes'] and sha(p) == item['sha256'], path
            bindings[path] = item['sha256']
    reviewed = read(ROOT / 'verification/stripe-raw-body-capture-review/review.json')
    assert reviewed['blockingFindings'] == []
    assert reviewed['candidateSHA256'] == '7797a09d3a99f5dabafb681bf2e5bda4bb1f01bc3974beb94176965f9f30546e'
    attempt = HERE / 'attempt-1'
    tested = read(attempt / 'receipt.json')
    assert tested['status'] == 'passed-isolated-hosted-composition-review-pending'
    for name, item in read(attempt / 'seal.json').items():
        p = attempt / name
        assert p.stat().st_size == item['bytes'] and sha(p) == item['sha256']
        bindings[str(p.relative_to(ROOT))] = item['sha256']
    bindings[str((attempt / 'seal.json').relative_to(ROOT))] = sha(attempt / 'seal.json')
    nested = read(attempt / 'hosted/receipt.json')
    assert nested['status'] == 'passed' and nested['cleanup'] == {'postgres_stopped': True, 'scratch_removed': True}
    assert 'Result: 142 passed, 2 skipped' in (attempt / 'hosted/tests.log').read_text()
    assert 'test_clock_absent: true' in (attempt / 'hosted/release-test-exclusion.log').read_text()
    assert 'test_adapter_absent: true' in (attempt / 'hosted/release-test-exclusion.log').read_text()
    expected = read(attempt / 'source-inputs.json')
    assert expected == nested['inputs'] and len(expected) == 71
    assert nested['source_tree_sha256'] == tested['sourceDigest']
    for name, digest in tested['baselineInputs'].items():
        assert sha(ROOT / name) == digest, 'live baseline drift: ' + name
    for name, digest in tested['additions'].items():
        assert not (ROOT / name).exists() and sha(attempt / 'source' / name) == digest
    for name, item in tested['replacements'].items():
        assert sha(ROOT / name) == item['beforeSHA256'] and sha(attempt / 'source' / name) == item['afterSHA256']
    candidate = ROOT / 'verification/stripe-raw-body-capture/candidate/lib/mixer_hosted/billing/raw_webhook_capture.ex'
    module = attempt / 'source/hosted/lib/mixer_hosted/billing/raw_webhook_capture.ex'
    assert module.read_bytes() == candidate.read_bytes().rstrip(b'\n') + b'\n'
    assert tested['scratchCleanup']['pathAbsent'] and not Path(tested['scratchCleanup']['path']).exists()
    applied = sorted(set(tested['additions']) | set(tested['replacements']))
    for name in applied:
        target = ROOT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(attempt / 'source' / name, target)
    assert all(sha(ROOT / name) == digest for name, digest in expected.items())
    result = {'schema': 1, 'status': 'accepted-and-integrated-private-raw-capture-only',
              'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'sourceParent': tested['sourceRevision'], 'sourceDigest': tested['sourceDigest'],
              'sourceInputs': expected, 'appliedFiles': applied, 'bindings': bindings,
              'normalization': tested['productionNormalization'],
              'validation': {'composedHostPassed': 142, 'composedHostSkipped': 2,
                             'skipReason': 'Existing Linux network namespace fixture is not enabled on this macOS run',
                             'newProductionModeTests': 15, 'independentGroups': 38, 'independentWireClients': 110,
                             'independentActualVerifierCalls': 31,
                             'release': 'build, expected missing-configuration rejection, prior fixture exclusions and new raw capture test-clock/adapter exclusions pass'},
              'cleanup': {'postgresStopped': True, 'ownedGroupsEmpty': True, 'scratchRemoved': True,
                          'rootScratchBytesRemoved': tested['scratchCleanup']['bytes']},
              'liveIntegrated': True, 'publicAdmissionAccepted': False, 'gaAccepted': False,
              'scope': 'Private exact-byte capture only. No route, response acknowledgment, provider, billing state, configuration secret, migration or database admission added.',
              'pending': ['exact-head Linux CI', 'endpoint-owned privacy and hard cancellation',
                          'header/resource limits and stream/connection disposal', 'TLS/ALPN/deployed ingress',
                          'server-owned endpoint/account/mode/generation/secrets', 'durable deduplicated inbox and atomic Oban enqueue',
                          'Stripe test-mode reconciliation', 'usage ledger and G23']}
    (HERE / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'integrated': applied, 'sourceInputs': len(expected), 'bindings': len(bindings),
                      'sourceDigest': tested['sourceDigest'], 'hostPassed': 142, 'skipped': 2, 'gaAccepted': False}))


if __name__ == '__main__':
    main()
