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
        expected_count = 9 if 'oracles' in command['label'] else 73 if 'minimal' in command['label'] else 320
        assert passed == expected_count
        counts[command['label']] = passed
        if 'oracles' not in command['label']:
            assert b'test experimental_swift_reactor::control::tests::optional_observation_chain_is_reserved_before_runtime_work ... ok' in data
            count += 1

for mode in ('debug', 'release'):
    data = (RUN / (mode + '-observation-layout.log')).read_text()
    assert 'running 1 test' in data and 'test result: ok. 1 passed; 0 failed; 0 ignored' in data
    assert 'raw=104 raw_align=8 optional=112 optional_align=8 count=6 old_floor=16040 new_floor=16504 added=464' in data
    count += 2

result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/swift-observation-accounting/audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__).read_bytes()),
    'passed': True, 'independent_acceptance': 'pending', 'verified_bindings': count,
    'receipt_sha256': sha((RUN / 'receipt.json').read_bytes()),
    'base_revision': receipt['base_revision'], 'source_tree_sha256': receipt['source_tree_sha256'],
    'source_overlays': overlays, 'test_counts': counts,
    'root_source_review': 'Only the named optional-observation allowance changes, from2 raw usages to6 Option usages. Five nested observed control parameters plus one retained caller are counted without last-use elision or borrowing another component envelope. No stored type, route, work, ticket count or cleanup algorithm changes. Admission rejects the old cap and new-minus1, accepts exact new cap, allocates nothing and finishes at zero.',
    'scope': 'Root isolated evidence audit; shared observation accounting correction only. Independent review and revised cache contract freeze remain pending. No cache/executor implementation, full target execution, devices or GA gate.'

}
(HERE / 'root-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'bindings': count, 'counts': counts}))
