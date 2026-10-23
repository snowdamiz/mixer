#!/usr/bin/env python3
"""Read-only evidence audit, then write the scoped root review."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda data: hashlib.sha256(data).hexdigest()
bindings = {}
def bind(path, expected=None):
    data = (ROOT / path).read_bytes()
    digest = sha(data)
    assert expected is None or expected == digest, path
    bindings[path] = digest
    return data

prefix = str(HERE.relative_to(ROOT))
r = json.loads(bind(prefix + '/isolated-2/receipt.json'))
assert r['passed']
assert r['overlays'] == ['vm/tests/swift_reactor_validation_allocations.rs']
bind(prefix + '/collect.py', r['collector_sha256'])
archive = bind(r['source_archive'], r['source_archive_sha256'])
with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tar:
    files = {m.name: sha(tar.extractfile(m).read()) for m in tar.getmembers() if m.isfile()}
assert files == r['source_files']
assert sha(json.dumps(files, sort_keys=True).encode()) == r['source_tree_sha256']
base = subprocess.check_output(['git', 'archive', r['base_revision'], 'vm'], cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(base)) as tar:
    original = {m.name: sha(tar.extractfile(m).read()) for m in tar.getmembers() if m.isfile()}
assert set(original) == set(files)
assert [p for p in sorted(files) if original[p] != files[p]] == r['overlays']
bind(r['overlays'][0], files[r['overlays'][0]])
assert [c['label'] for c in r['commands']] == ['rust-version', 'cargo-version', 'format', 'debug', 'release', 'clippy-test']
for command in r['commands']:
    assert command['exit'] == 0 and command['source_stable']
    log = bind(command['log'], command['sha256']).decode()
    if command['label'] in ['debug', 'release']:
        assert '1 passed; 0 failed; 0 ignored' in log
        assert 'allocation_ordinals=56;' in log
        assert log.count('early expiry at 0 allocations with 0 ms; ordinal coverage not accepted') == 3
        assert 'source/metadata/body deadline stages=true' in log
first = json.loads(bind(prefix + '/isolated-1/receipt.json'))
bind(prefix + '/isolated-1/collect.py', first['collector_sha256'])
bind(first['source_archive'], first['source_archive_sha256'])
assert not first['passed']
assert [c['label'] for c in first['commands'] if c['exit'] != 0] == ['clippy-test']
for command in first['commands']:
    bind(command['log'], command['sha256'])
failure = bind(prefix + '/prior-attempt/cache-regressions.json').decode()
assert 'deadline cleanup allocated at ordinal 38' in failure
assert 'left: 22' in failure and 'right: 38' in failure
retry = bind(prefix + '/prior-attempt/isolated-retry.log').decode()
assert 'allocation_ordinals=56;' in retry and '1 passed; 0 failed' in retry
result = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/swift-validation-deadline-repair/audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__).read_bytes()),
    'bindings': bindings, 'verified_source_bindings': len(files),
    'base_revision': r['base_revision'], 'source_tree_sha256': r['source_tree_sha256'],
    'decision': 'Accept isolated test-only timing repair; no production/runtime change.',
    'evidence': 'Debug and Release each pass all56 exact allocation failure, cancellation and reached-deadline ordinals, with leak-free cleanup and no reallocation. Actual zero-deadline retries and exhaustion are deterministic in the same single observer test. All-feature targeted Clippy and formatting pass.',
    'retained_failures': 'Original cache qualification expired after22 allocations before target38. Original isolated rerun passed unchanged. First repaired test run passed Debug/Release but minimal-feature Clippy found pre-existing unused GlobalView fields in39199ae; preserved separately, not called a pass. Final all-feature Clippy exercises the existing descriptor consumer without editing production sources.',
    'limits': 'Root-authored repair and root audit; separate cache implementation review pending. Bounded retries can still fail on a sufficiently stalled host; exhaustion never accepts missing ordinal coverage. Host requested-byte observation only, no physical devices, full Swift target or GA acceptance.',
}
(HERE / 'root-review.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'accepted': True, 'source_bindings': len(files), 'artifact_bindings': len(bindings)}))
