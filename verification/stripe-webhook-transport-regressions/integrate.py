import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = OUT / 'attempt-1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
producer = read(RUN / 'receipt.json')
nested = read(RUN / 'hosted/receipt.json')
expected = read(RUN / 'source-inputs.json')
baseline = producer['baselineInputs']
assert len(baseline) == 72 and len(expected) == 73
assert producer['status'] == 'passed-isolated-hosted-composition-review-pending'
assert producer['productionCodeUnchanged'] and nested['status'] == 'passed'
assert nested['inputs'] == expected
assert nested['cleanup'] == {'postgres_stopped': True, 'scratch_removed': True}
assert producer['scratchCleanup']['pathAbsent'] and not Path(producer['scratchCleanup']['path']).exists()
for name, entry in read(RUN / 'seal.json').items():
    assert sha(RUN / name) == entry['sha256'] and (RUN / name).stat().st_size == entry['bytes']
for name, value in baseline.items():
    assert sha(ROOT / name) == value
changed = [name for name in expected if baseline.get(name) != expected[name]]
assert set(changed) == {'hosted/scripts/test-local.py', 'hosted/test/mixer_hosted/billing/webhook_transport_test.exs'}
assert 'Result: 149 passed, 2 skipped' in (RUN / 'hosted/tests.log').read_text()
assert 'production_transport_policy: passed; 4 production modules; test helpers absent; role inactive' in (RUN / 'hosted/release-test-exclusion.log').read_text()
for c in producer['commands']:
    assert c['exitCode'] == (1 if c['label'] == 'scratch-holders' else 0)
    assert not c['timedOut'] and not c['groupCleanup']['after']
    assert sha(RUN / c['output']) == c['outputSHA256']
for c in nested['commands']:
    assert c['exit_code'] == c.get('expected_exit_code', 0)
    assert sha(RUN / 'hosted' / c['log']) == c['sha256']
for name in changed:
    data = (RUN / 'source' / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected[name]
    (ROOT / name).write_bytes(data)
for name, value in expected.items():
    assert sha(ROOT / name) == value
result = {
    'schema': 1,
    'status': 'accepted-integrated-test-and-release-regressions-only',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevisionContext': '09ee31fff245aa14f89cd4054b7df5a214efbb93',
    'changedFiles': sorted(changed),
    'sourceInputs': expected,
    'sourceDigest': nested['source_tree_sha256'],
    'fullHostPassed': 149,
    'namespaceSkipped': 2,
    'productionModulesUnchanged': True,
    'tests': 'Seven permanent regressions cover metadata reconstruction, raw/extra report rejection, finite counter/schema edges, noninvocation of arbitrary callbacks, inactive ordinary application, and missing/forged-context refusal before adapter reads. They do not replace the isolated wire/deadline/sink matrix.',
    'releaseChecks': 'Existing collector now inspects all four production transport modules, exact top-level exports, absent isolated and permanent test helpers, absent clock/adapter parameters and inactive role.',
    'cleanup': 'Isolated PostgreSQL stopped; command groups empty;64146951bytes scratch removed after holder and identity checks.',
    'roleActivated': False,
    'publicAdmissionAccepted': False,
    'gaAccepted': False,
    'bindings': {str(p.relative_to(ROOT)): sha(p) for p in RUN.rglob('*') if p.is_file()},
}
result['bindings'][str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__))
(OUT / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
print(result['status'], result['sourceDigest'], '149passed2skipped')
