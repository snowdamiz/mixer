import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
COMPOSITION = ROOT / 'verification/stripe-webhook-transport-composition'
MODULE = 'hosted/lib/mixer_hosted/billing/webhook_transport.ex'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
digest = lambda x: hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def manifest():
    base = ROOT / 'hosted'
    result = {str(p.relative_to(ROOT)): sha(p) for p in sorted(base.rglob('*'))
              if p.is_file() and p.name != 'erl_crash.dump'
              and not {'_build', 'deps', '__pycache__', 'cover'}.intersection(p.relative_to(base).parts)}
    for name in ['signed-release-v3.json', 'release-v3-cases.json']:
        p = ROOT / 'services/protocol/testdata' / name
        result[str(p.relative_to(ROOT))] = sha(p)
    return result

expected = read(COMPOSITION / 'attempt-4/source-inputs.json')
baseline = {k: v for k, v in expected.items() if k != MODULE}
assert len(baseline) == 71 and digest(baseline) == 'ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc'
assert manifest() == baseline
assert not (ROOT / MODULE).exists()
assert sha(COMPOSITION / 'seal.json') == '31dc092801e6f4b2e90b97fecd97b27c314fff88f2a45af0b641679303474975'
candidate = COMPOSITION / 'attempt-4/source' / MODULE
assert sha(candidate) == expected[MODULE] == '56a26cf3a56f3e5a5b2d8f5104fc7c3371b0e44918b007197be5871cf94ef1a5'
commands = []
for label, argv in [
    ('producer', [sys.executable, '-B', 'verification/stripe-webhook-transport/verify.py']),
    ('independent-review', [sys.executable, '-B', 'verification/stripe-webhook-transport-review/verify.py']),
    ('composed-source', [sys.executable, '-B', 'verification/stripe-webhook-transport-composition/verify.py']),
]:
    result = subprocess.run(argv, cwd=ROOT, capture_output=True)
    path = OUT / (label + '.log')
    path.write_bytes(result.stdout + result.stderr)
    commands.append({'argv': argv, 'exitCode': result.returncode, 'output': str(path.relative_to(ROOT)), 'sha256': sha(path)})
    assert result.returncode == 0
with (ROOT / MODULE).open('xb') as stream:
    stream.write(candidate.read_bytes())
assert manifest() == expected and len(expected) == 72
assert digest(expected) == '789b7de9b46ef2ce65ad83a4c916dde9a513a8eaa68dfc073e4c65ec97e2ee93'
result = subprocess.run([sys.executable, '-B', 'verification/stripe-webhook-transport-composition/verify.py', '--live'], cwd=ROOT, capture_output=True)
path = OUT / 'live-source.log'
path.write_bytes(result.stdout + result.stderr)
commands.append({'argv': [sys.executable, '-B', 'verification/stripe-webhook-transport-composition/verify.py', '--live'], 'exitCode': result.returncode, 'output': str(path.relative_to(ROOT)), 'sha256': sha(path)})
assert result.returncode == 0
bindings = {}
for name in ['stripe-webhook-transport', 'stripe-webhook-transport-review', 'stripe-webhook-transport-composition']:
    for p in (ROOT / 'verification' / name).rglob('*'):
        if p.is_file():
            bindings[str(p.relative_to(ROOT))] = sha(p)
for name in ['docs/stripe-webhook-transport-implementation.md', 'docs/stripe-webhook-transport-review.md', 'docs/stripe-webhook-transport-composition.md']:
    bindings[name] = sha(ROOT / name)
receipt = {
    'schema': 1,
    'status': 'accepted-and-integrated-private-inert-webhook-transport',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevisionContext': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'changedFiles': [MODULE],
    'sourceInputs': expected,
    'sourceDigest': digest(expected),
    'normalization': 'Only two formatter layout sites changed; root inspected exact diff and compiler-derived 4344-token and metadata-free AST equivalence.',
    'commands': commands,
    'bindings': bindings,
    'rootPythonVersion': sys.version,
    'fullHostedTests': {'passed': 142, 'skipped': 2, 'environment': 'macOS arm64; namespace fixtures skipped, not passed'},
    'behaviorEvidence': 'Frozen producer and independent actual HTTP1/HTTP2, permit/deadline/owner-loss and configured-sink privacy matrices. Full hosted composition does not rerun that private wire matrix.',
    'releaseEvidence': 'Four production transport modules and exact top-level exports inspected; producer/reviewer helpers and capture test clock/adapter absent. Role remains inactive.',
    'liveIntegrated': True,
    'roleActivated': False,
    'publicAdmissionAccepted': False,
    'gaAccepted': False,
    'pending': ['P11 enforced OS/container resource ceilings', 'P12 public trailer policy', 'P14 TLS/ALPN/deployed ingress', 'P15 endpoint/account/mode/generation/secret authority and provider deliveries', 'P16 durable inbox/atomic Oban enqueue and billing reconciliation', 'permanent hosted transport release regression checks', 'G23 and accountable GA review'],
}
(OUT / 'acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(receipt['status'], len(bindings), 'upstream bindings; exact72-input live closure')
