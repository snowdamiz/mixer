"""Read-only binding check for the permanent host and release regressions."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true')
args = parser.parse_args()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
seal = read(OUT / 'seal.json')
actual = {str(p.relative_to(ROOT)) for p in OUT.rglob('*') if p.is_file() and p != OUT / 'seal.json'}
actual.add('docs/stripe-webhook-transport-regressions.md')
assert actual == set(seal)
for name, expected in seal.items():
    assert sha(ROOT / name) == expected, name
accepted = read(OUT / 'acceptance.json')
assert accepted['status'] == 'accepted-integrated-test-and-release-regressions-only'
assert accepted['fullHostPassed'] == 149 and accepted['namespaceSkipped'] == 2
assert accepted['productionModulesUnchanged']
assert not any(accepted[x] for x in ['roleActivated', 'publicAdmissionAccepted', 'gaAccepted'])
assert len(accepted['sourceInputs']) == 73
for name, expected in accepted['bindings'].items():
    assert sha(ROOT / name) == expected, name
run = OUT / 'attempt-1'
attempt = read(run / 'receipt.json')
nested = read(run / 'hosted/receipt.json')
assert nested['inputs'] == accepted['sourceInputs']
assert nested['source_tree_sha256'] == accepted['sourceDigest']
assert nested['status'] == 'passed'
assert nested['cleanup'] == {'postgres_stopped': True, 'scratch_removed': True}
assert attempt['scratchCleanup']['pathAbsent'] and not Path(attempt['scratchCleanup']['path']).exists()
assert 'Result: 149 passed, 2 skipped' in (run / 'hosted/tests.log').read_text()
assert 'production_transport_policy: passed; 4 production modules; test helpers absent; role inactive' in (run / 'hosted/release-test-exclusion.log').read_text()
for command in attempt['commands']:
    assert command['exitCode'] == (1 if command['label'] == 'scratch-holders' else 0)
    assert not command['timedOut'] and not command['groupCleanup']['after']
    assert sha(run / command['output']) == command['outputSHA256']
for command in nested['commands']:
    assert command['exit_code'] == command.get('expected_exit_code', 0)
    assert sha(run / 'hosted' / command['log']) == command['sha256']
if args.live:
    base = ROOT / 'hosted'
    live = {str(p.relative_to(ROOT)): sha(p) for p in base.rglob('*')
            if p.is_file() and p.name != 'erl_crash.dump'
            and not {'_build', 'deps', '__pycache__', 'cover'}.intersection(p.relative_to(base).parts)}
    for name in ['signed-release-v3.json', 'release-v3-cases.json']:
        p = ROOT / 'services/protocol/testdata' / name
        live[str(p.relative_to(ROOT))] = sha(p)
    assert live == accepted['sourceInputs']
print(json.dumps({'verified': True, 'sourceInputs': 73, 'liveChecked': args.live,
                  'fullHostPassed': 149, 'namespaceSkipped': 2,
                  'roleActivated': False, 'publicAdmissionAccepted': False, 'gaAccepted': False}))
