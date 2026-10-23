#!/usr/bin/env python3
"""Audit the frozen observer-only source overlay and its retained host evidence."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OWNER = ROOT / 'verification/allocator-observer-ci-repair'
digest = lambda data: hashlib.sha256(data).hexdigest()
receipt_bytes = (OWNER / 'receipt.json').read_bytes()
r = json.loads(receipt_bytes)
checks = []

def check(label, condition):
    checks.append({'check': label, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(label)

def archive_files(data):
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        return {entry.name: archive.extractfile(entry).read() for entry in archive if entry.isfile()}

snapshot_bytes = (ROOT / r['full_snapshot']).read_bytes()
check('retained snapshot digest', digest(snapshot_bytes) == r['full_snapshot_sha256'])
snapshot = archive_files(snapshot_bytes)
manifest = {name: digest(data) for name, data in sorted(snapshot.items())}
check('complete snapshot file manifest', manifest == r['source_before']['files'])
check('immutable source before and after', r['source_before'] == r['source_after'])
check('complete source digest', digest(json.dumps(manifest, sort_keys=True).encode()) == r['source_before']['sha256'])
base_bytes = subprocess.check_output(['git', 'archive', '--format=tar', r['baseline_revision'], 'vm'], cwd=ROOT)
check('baseline export identity', digest(base_bytes) == r['baseline_vm_export_sha256'])
baseline = archive_files(base_bytes)
check('only named overlay paths differ', {name for name in set(baseline) | set(snapshot) if baseline.get(name) != snapshot.get(name)} == set(r['overlay']))
for name, expected in r['overlay'].items():
    check('current overlay ' + name, digest((ROOT / name).read_bytes()) == expected == manifest[name])
for item in r['checks']:
    check('successful command ' + item['name'], item['exit'] == 0)
    check('stable command source ' + item['name'], item['source_before_sha256'] == item['source_after_sha256'] == r['source_before']['sha256'])
    log = (ROOT / item['log']).read_bytes()
    check('log identity ' + item['name'], digest(log) == item['log_sha256'])
    if item['name'] != 'clippy':
        text = log.decode()
        check('both test processes pass ' + item['name'], text.count('test result: ok. 1 passed; 0 failed;') == 2)
        check('cache exact original measurements ' + item['name'], 'constructor_allocations=2 decode_allocations=3 constructor_requested_peak=1248 decode_requested_peak=4277' in text)
        check('executor exact original measurements ' + item['name'], 'constructor_allocations=6 initial_invoke_allocations=4 constructor_requested_peak=462872 invoke_requested_peak=131357' in text)

result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/allocator-observer-root-review/audit.py',
    'python': platform.python_version(),
    'auditor_source_sha256': digest(Path(__file__).read_bytes()),
    'owner_receipt_sha256': digest(receipt_bytes),
    'baseline_revision': r['baseline_revision'],
    'snapshot_sha256': r['full_snapshot_sha256'],
    'tested_tree_sha256': r['source_before']['sha256'],
    'snapshot_files': len(manifest),
    'overlay': r['overlay'],
    'checks': checks,
    'source_review': [
        'Root reviewed both full test diffs and the allocation observer helper; all original product assertions and fault ordinals remain.',
        'Fault and cancellation state are thread local, with a retained Cancellation and non-Send interval guards. Background allocations cannot consume foreground ordinals.',
        'Fixed pointer ownership accounting spans preparation, measurement and destruction; cross-thread free/realloc follows recorded pointer ownership. System realloc is serialized with address lifetime bookkeeping.',
        'All allocator hook bookkeeping is bounded and allocation free; ledger exhaustion aborts. The single synchronous owner requirement is explicit.',
        'Root inspected deterministic failures in preserved original-observer logs and the repaired four-configuration observations. CI allocation stack remains unattributed.'
    ],
    'scope': 'Test instrumentation only, audited against immutable baseline plus exactly three test files. No production changes or new physical, execution, published-package or GA qualification. Active Swift validator changes are excluded and require separate integration checks.'
}
(OUT / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'checks': len(checks), 'snapshot_files': len(manifest), 'result': 'passed'}))
