#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
count = 0


def check(path, expected):
    global count
    assert sha(ROOT / path) == expected, path
    count += 1


def manifest(path):
    for line in (ROOT / path).read_text().splitlines():
        digest, name = line.split('  ', 1)
        check(name, digest)


owner_path = ROOT / 'verification/android-facade-transport/receipt.json'
review_path = ROOT / 'verification/android-facade-transport-review/receipt.json'
portable_path = ROOT / 'verification/android-facade-transport-ci/host-1/receipt.json'
owner = json.loads(owner_path.read_text())
review = json.loads(review_path.read_text())
portable = json.loads(portable_path.read_text())
check(str(owner_path.relative_to(ROOT)), review['owner_receipt_sha256'])
assert review['findings'] == []
for receipt in (owner, review):
    check(receipt['source_manifest'], receipt['source_tree_digest'])
    manifest(receipt['source_manifest'])
    for field in ('tool_input_sha256', 'tool_inputs_sha256', 'android_artifact_sha256', 'android_artifacts_sha256'):
        for path, digest in receipt.get(field, {}).items():
            check(path, digest)
    for command in receipt['commands']:
        expected = command.get('expected_success', command.get('expected', 0) == 0)
        assert (command['exit_code'] == 0) == expected
        assert (ROOT / command['output']).is_file()
manifest('verification/android-facade-transport-review/evidence.sha256')
for path, digest in portable['source_files'].items():
    check(path, digest)
for command in portable['commands']:
    assert command['exit'] == 0
    check(command['log'], command['sha256'])
for path, digest in portable['artifacts'].items():
    check(path, digest)
check('scripts/ci/check-android-transport.py', portable['collector_sha256'])
assert sum(portable['counts'].values()) == 146
logs = {str(p.relative_to(ROOT)): sha(p) for p in owner_path.parent.glob('*.log')}
receipt = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/android-facade-transport-root-review/audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__)),
    'receipts': {str(p.relative_to(ROOT)): sha(p) for p in (owner_path, review_path, portable_path)},
    'verified_bindings': count, 'owner_log_sha256': logs,
    'review': 'Root accepts private C facade/UI-entry/progress implementation. Independent review has no open findings; root inspected lease identity, callback pre-read rejection, return fences, fixed slot ownership, first fault fanout and reclaim conditions.',
    'counts': {'owner_host': 248, 'independent_host': 292, 'portable_host': 146},
    'scope': 'Host C/Looper simulations plus official Android API30 arm64 object/link checks. Portable host CI driver also passes locally. C cannot prove Swift Task.value, final resource destruction or Java UI entry provenance. Android signed binding, actual runtime/display/health and physical devices remain pending; no GA acceptance.',
}
(HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'verified_bindings': count, 'result': 'passed'}))
