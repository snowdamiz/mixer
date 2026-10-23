#!/usr/bin/env python3
"""Audit owner and root executable receipts without rerunning or rewriting them."""
import hashlib
import io
import json
import platform
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
count = 0
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())

def bind(path, digest):
    global count
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    assert sha(path) == digest, str(path)
    count += 1

descriptor_dir = ROOT / 'verification/swift-execution-descriptors'
descriptor_path = descriptor_dir / '2026-10-23-host-v2/receipt.json'
descriptor = read(descriptor_path)
assert descriptor['passed'] and descriptor['sourceComparisonPassed']
assert len(descriptor['commands']) == 68
for command in descriptor['commands']:
    assert command['passed'] and command['exitCode'] == command['expectedExitCode']
    if command['expectedErrorCodes'] is not None:
        assert sorted(command['observedErrorCodes']) == sorted(command['expectedErrorCodes'])
    for stream in ('stdout', 'stderr'):
        bind(descriptor_path.parent / command[stream]['path'], command[stream]['sha256'])
for item in descriptor['verificationInputs']:
    bind(descriptor_dir / item['path'], item['sha256'])
raw = subprocess.check_output(['git', 'archive', descriptor['baseline'], 'vm'], cwd=ROOT)
assert hashlib.sha256(raw).hexdigest() == descriptor['baselineArchiveSha256']
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
    baseline = {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                for m in archive.getmembers() if m.isfile()}
assert baseline == {i['path']: i['sha256'] for i in descriptor['baselineSource']['files']}
count += len(baseline)
candidate = dict(baseline)
for item in descriptor['overlay']:
    bind(item['path'], item['sha256'])
    candidate[item['path']] = item['sha256']
assert candidate == {i['path']: i['sha256'] for i in descriptor['candidateSource']['files']}
count += len(candidate)

receipts = [ROOT / 'verification/swift-cache-control-boundary/isolated-2/receipt.json', HERE / 'combined-1/receipt.json']
for path in receipts:
    data = read(path)
    assert data['passed']
    bind(path.parent.parent / 'collect.py', data['collector_sha256'])
    bind(data['source_archive'], data['source_archive_sha256'])
    with tarfile.open(ROOT / data['source_archive']) as archive:
        files = {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                 for m in archive.getmembers() if m.isfile()}
    assert files == data['source_files']
    count += len(files)
    for name, digest in files.items():
        bind(Path(data['source']) / name, digest)
    for command in data['commands']:
        assert command['exit'] == 0 and command['source_stable']
        bind(command['log'], command['sha256'])
combined = read(receipts[1])
isolated = read(receipts[0])
for name in isolated['overlays']:
    assert combined['source_files'][name] == isolated['source_files'][name]
    count += 1
for item in descriptor['overlay']:
    assert combined['source_files'][item['path']] == item['sha256']
    count += 1
for name, digest in combined['source_files'].items():
    bind(name, digest)
result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/swift-cache-prerequisites-root-review/audit_owned.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__)),
    'passed': True, 'verified_bindings': count,
    'source_tree_sha256': combined['source_tree_sha256'],
    'receipts': {str(p.relative_to(ROOT)): sha(p) for p in [descriptor_path, *receipts]},
    'root_source_review': 'Root read the five descriptor changes and wrote/reviewed the four observed-control changes. No stored field or public route changed. Absolute index/offset/declaration borrows preserve original proof allocation. Both adopted tickets are checked, and actual WASI observation pairing separates foreign identity from same-owner accounting failure. Root combined Debug/Release each pass318 tests plus9 explicit reference checks, scoped lint and formatting.',
    'scope': 'Owner and root evidence binding only. Independent adversarial prerequisite review and whole-cache acceptance are separately pending. No full target execution, physical device, immutable published consumer or GA qualification.'
}
(HERE / 'owner-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'verified_bindings': count}))
