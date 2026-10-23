#!/usr/bin/env python3
"""Bind isolated runtime evidence without including concurrent lane edits."""
import hashlib
import io
import json
import platform
import re
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / 'isolated-1'
sha = lambda data: hashlib.sha256(data).hexdigest()
read = lambda path: json.loads(path.read_text())
receipt = read(RUN / 'receipt.json')
assert receipt['passed']
assert sha((HERE / 'collect.py').read_bytes()) == receipt['collector_sha256']
archive_path = ROOT / receipt['source_archive']
assert sha(archive_path.read_bytes()) == receipt['source_archive_sha256']
with tarfile.open(archive_path) as archive:
    observed = {item.name: sha(archive.extractfile(item).read()) for item in archive.getmembers() if item.isfile()}
assert observed == receipt['source_files']
assert sha(json.dumps(observed, sort_keys=True).encode()) == receipt['source_tree_sha256']
raw = subprocess.check_output(['git', 'archive', receipt['base_revision'], 'vm'], cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
    baseline = {item.name: sha(archive.extractfile(item).read()) for item in archive.getmembers() if item.isfile()}
expected = dict(baseline)
overlays = {name: sha((ROOT / name).read_bytes()) for name in receipt['overlays']}
expected.update(overlays)
assert expected == observed
count = len(observed) + len(expected) + len(overlays) + 3
counts = {}
for command in receipt['commands']:
    assert command['exit'] == 0 and command['source_stable']
    data = (ROOT / command['log']).read_bytes()
    assert sha(data) == command['sha256']
    count += 1
    if command['label'] in ('debug', 'release', 'debug-oracles', 'release-oracles', 'debug-minimal-swift', 'release-minimal-swift'):
        totals = re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored', data.decode())
        assert totals and all(int(item[1]) == 0 for item in totals)
        passed = sum(int(item[0]) for item in totals)
        expected_count = 9 if 'oracles' in command['label'] else 72 if 'minimal' in command['label'] else 319
        assert passed == expected_count
        counts[command['label']] = passed
        if 'oracles' not in command['label']:
            assert b'test experimental_swift_reactor::control::tests::instruction_and_bulk_fuel_failures_retain_actual_wasi_counters ... ok' in data
            count += 1

result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/swift-instruction-observation/audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__).read_bytes()),
    'passed': True, 'independent_acceptance': 'pending', 'verified_bindings': count,
    'receipt_sha256': sha((RUN / 'receipt.json').read_bytes()),
    'base_revision': receipt['base_revision'], 'source_tree_sha256': receipt['source_tree_sha256'],
    'source_overlays': overlays, 'test_counts': counts,
    'root_source_review': 'Exactly two private observed method variants, old signatures delegating None, same checked arithmetic and mutation order. Instruction still charges one fuel before its checked instruction increment. No stored type, policy, allocation, ticket, host dispatch or public route changed. Eleven cases use one actual WASI dispatch before each operation; repeated failures retain original context counters and produce no further effects. Internal overflow cases corrupt only test scalars.',
    'scope': 'Root isolated evidence audit; private control prerequisite only. Independent review remains pending; no executor/cache implementation acceptance, target execution, devices or GA gate.'
}
(HERE / 'root-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'bindings': count, 'counts': counts}))
