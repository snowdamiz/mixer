#!/usr/bin/env python3
"""Record the additive v3 contract without rewriting historical v2 evidence."""
import hashlib
import json
import platform
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT = ROOT / 'verification/swift-cache-stage-contract'
OUT = HERE / 'contract-v3'
OUT.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
paths = [
    'docs/swift-cache-stage-contract.md',
    'verification/swift-cache-stage-contract/acceptance.json',
    'verification/swift-cache-stage-contract/check_contract.py',
    'verification/swift-cache-stage-contract/artifact_checks.py',
    'verification/swift-cache-stage-contract/historical-v2/archive-manifest.json',
    'verification/swift-executor-contract-review/foundation-tail-addendum.md',
    'verification/swift-executor-contract-review/observation-chain-map.json',
    'verification/swift-executor-contract-review/layout-receipt.json',
    'verification/swift-observation-accounting/isolated-1/receipt.json',
    'verification/swift-observation-accounting/root-audit.json',
    'vm/src/experimental_swift_reactor/control.rs',
    'vm/src/experimental_swift_reactor/control_tests.rs',
]
history = read(CONTRACT / 'historical-v2/archive-manifest.json')
for entry in history['files'].values():
    assert sha(ROOT / entry['archived_path']) == entry['sha256']
    paths.append(entry['archived_path'])
bindings = {p: sha(ROOT / p) for p in paths}
archive = OUT / 'source.tar.gz'
with tarfile.open(archive, 'w:gz') as tar:
    for p in paths:
        tar.add(ROOT / p, arcname=p)
commands = []
for label, argv in [
    ('python-version', [sys.executable, '--version']),
    ('contract-check', [sys.executable, '-B', str(CONTRACT / 'check_contract.py')]),
    ('contract-mutations', [sys.executable, '-B', str(CONTRACT / 'artifact_checks.py')]),
    ('diff-check', ['git', 'diff', '--check', '--', *paths]),
]:
    result = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = OUT / (label + '.log')
    log.write_bytes(result.stdout)
    commands.append({'argv': argv, 'cwd': str(ROOT), 'exit': result.returncode,
                     'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
assert all(c['exit'] == 0 for c in commands)
assert all(sha(ROOT / p) == h for p, h in bindings.items())
receipt = {
    'schema': 'mixer-swift-cache-contract-refinement-v3',
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': [sys.executable, str(Path(__file__))],
    'collector_sha256': sha(Path(__file__)), 'python': platform.python_version(),
    'bindings': bindings, 'commands': commands,
    'source_archive': str(archive.relative_to(ROOT)), 'source_archive_sha256': sha(archive),
    'passed': True, 'independent_refinement_review': 'pending',
    'scope': 'Artifact-only refinement to six optional observation shapes. Exact v2 proposal/root freeze archived. Root source correction separately passes320+9 per Debug/Release,73 minimal-Swift library per mode and lint/format; independent correction/contract acceptance pending.',
    'implementation_tests': {'named': 18, 'accepted': 0},
    'target_execution_authorized': False, 'physical_device_runs_authorized': False,
    'pending': ['Independent correction and revised contract review', 'Actual cache implementation acceptance',
                'Executor composed layouts/implementation', 'Bounded target runner',
                'Physical devices, immutable published consumer and GA qualification'],
}
(CONTRACT / 'proposal-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'passed': True, 'bindings': len(bindings), 'commands': len(commands),
                  'receipt_sha256': sha(CONTRACT / 'proposal-receipt.json')}))
