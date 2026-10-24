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
seal = json.loads((OUT / 'seal.json').read_text())
actual = {str(p.relative_to(ROOT)) for p in OUT.rglob('*') if p.is_file() and p.name != 'seal.json'}
actual.add('docs/stripe-webhook-transport-integration.md')
assert actual == set(seal)
for name, expected in seal.items():
    assert sha(ROOT / name) == expected
accepted = json.loads((OUT / 'acceptance.json').read_text())
assert accepted['status'] == 'accepted-and-integrated-private-inert-webhook-transport'
assert accepted['liveIntegrated'] and not accepted['roleActivated']
assert not accepted['publicAdmissionAccepted'] and not accepted['gaAccepted']
assert len(accepted['bindings']) == 1099 and len(accepted['sourceInputs']) == 72
for name, expected in accepted['bindings'].items():
    assert sha(ROOT / name) == expected, name
for command in accepted['commands']:
    assert command['exitCode'] == 0 and sha(ROOT / command['output']) == command['sha256']
assert accepted['fullHostedTests']['passed'] == 142 and accepted['fullHostedTests']['skipped'] == 2
if args.live:
    base = ROOT / 'hosted'
    live = {str(p.relative_to(ROOT)): sha(p) for p in sorted(base.rglob('*'))
            if p.is_file() and p.name != 'erl_crash.dump'
            and not {'_build', 'deps', '__pycache__', 'cover'}.intersection(p.relative_to(base).parts)}
    for name in ['signed-release-v3.json', 'release-v3-cases.json']:
        p = ROOT / 'services/protocol/testdata' / name
        live[str(p.relative_to(ROOT))] = sha(p)
    assert live == accepted['sourceInputs']
print(json.dumps({'verified': True, 'upstreamBindings': 1099, 'sourceInputs': 72,
                  'liveChecked': args.live, 'fullHostPassed': 142, 'namespaceSkipped': 2,
                  'roleActivated': False, 'publicAdmissionAccepted': False, 'gaAccepted': False}))
