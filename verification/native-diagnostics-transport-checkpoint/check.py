import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
commands = []
for label, argv in [
    ('apple-handoff', [sys.executable, '-B', 'verification/apple-authored-toggle-runtime-preflight/verify.py']),
    ('apple-historical-cover-failure', ['/Users/andreyyurlov/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3', '-B', 'verification/apple-native-resume-2026-10-24/verify.py']),
    ('transport-integration', [sys.executable, '-B', 'verification/stripe-webhook-transport-integration/verify.py', '--live']),
    ('policy', [sys.executable, '-B', 'scripts/check-policy.py']),
    ('whitespace', ['git', 'diff', '--check', '--', 'PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json', 'hosted', 'docs']),
    ('python-version', [sys.executable, '--version']),
]:
    p = subprocess.run(argv, cwd=ROOT, capture_output=True)
    log = OUT / (label + '.log')
    log.write_bytes(p.stdout + p.stderr)
    commands.append({'argv': argv, 'exitCode': p.returncode, 'output': str(log.relative_to(ROOT)), 'sha256': sha(log)})
    assert p.returncode == 0, label
receipts = [
    'verification/apple-authored-toggle-native-root-review/receipt.json',
    'verification/android-authored-toggle-supplement-root-review/runtime-review.json',
    'verification/stripe-webhook-transport-integration/acceptance.json',
]
for name in receipts:
    receipt = json.loads((ROOT / name).read_text())
    for file, expected in receipt['bindings'].items():
        assert sha(ROOT / file) == expected, file
work = json.loads((ROOT / 'work-graph.json').read_text())
gates = json.loads((ROOT / 'gates/ga.json').read_text())
assert len(work['packages']) == 18 and len(gates['gates']) == 38
assert not any(row['status'] == 'verified' for row in gates['gates'])
files = receipts + ['PLAN.md', 'STATUS.md', 'work-graph.json', 'gates/ga.json',
                   'docs/native-toggle-diagnostics-checkpoint.md',
                   'docs/stripe-webhook-transport-integration.md',
                   'verification/swift-calls-dispatch-root-review/owner-preflight-amendment.json']
result = {
    'schema': 1,
    'status': 'passed-integrity-with-native-failures-explicit-and-private-transport-integrated',
    'sourceRevisionContext': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'commands': commands,
    'bindings': {name: sha(ROOT / name) for name in files},
    'environmentRecovery': 'Historical Apple pixel verifier initially could not import PIL using system Python3.14. Replayed successfully using the bundled Python3.12.14/Pillow12.3.0 recorded by its receipt. No original evidence changed.',
    'scope': 'Apple partial native observations and Android componentfailure retained; owned instances cleaned. Private inactive transport integration accepted; no public/physical/GA promotion.',
}
(OUT / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print(result['status'], len(commands), 'checks')
