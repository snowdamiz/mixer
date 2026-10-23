#!/usr/bin/env python3
"""Root audit of exact foundation inputs and independently retained evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
count = 0

def bound(path, digest):
    global count
    p = Path(path)
    if not p.is_absolute(): p = ROOT / p
    assert sha(p) == digest, str(p)
    count += 1

def rows(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
            bound(value['path'], value['sha256'])
        for item in value.values(): rows(item)
    elif isinstance(value, list):
        for item in value: rows(item)

paths = [ROOT / 'verification/swift-runtime-control/2026-10-23-foundation/receipt.json', ROOT / 'verification/swift-runtime-control-review/2026-10-23-foundation/receipt.json', HERE / 'combined-1/receipt.json']
owner, review, combined = [json.loads(p.read_text()) for p in paths]
assert owner['success'] and owner['source_stable'] and owner['revision_stable']
assert review['success'] and review['source_stable'] and review['private_module_diagnostic_confirmed']
assert combined['passed']
rows(owner)
rows(json.loads(Path(owner['source_manifest']['path']).read_text()))
rows(review['tool_binaries'])
assert review['source_before'] == review['source_after']
for path, digest in review['source_before'].items(): bound(path, digest)
for path, digest in combined['source_files'].items(): bound(path, digest)
for item in owner['commands']: assert item['exit_code'] == 0
for item in review['commands']:
    assert item['passed'] and item['exit_code'] == item['expected_exit_code']
    bound(item['log'], item['log_sha256'])
for item in combined['commands']:
    assert item['exit'] == 0 and item['source_stable']
    bound(item['log'], item['sha256'])
for archive, digest, manifest in [(review['snapshot_archive'], review['snapshot_archive_sha256'], review['snapshot_manifest']), (combined['source_archive'], combined['source_archive_sha256'], combined['source_files'])]:
    bound(archive, digest)
    with tarfile.open(ROOT / archive) as tar:
        for path, expected in manifest.items():
            data = tar.extractfile(path).read()
            assert hashlib.sha256(data).hexdigest() == expected, path
            count += 1
bound('verification/swift-runtime-control-review/probes.rs', review['probe_source_sha256'])
bound('verification/swift-runtime-control-review/collect.py', review['collector_sha256'])
bound(HERE / 'collect.py', combined['collector_sha256'])
counts = {c['label']: sum(map(int, re.findall(r'test result: ok\. (\d+) passed', (ROOT / c['log']).read_text()))) for c in combined['commands'] if c['label'] in ['debug', 'release', 'debug-oracles', 'release-oracles']}
assert counts == {'debug': 287, 'debug-oracles': 9, 'release': 287, 'release-oracles': 9}, counts
result = {'observed_utc': datetime.now(timezone.utc).isoformat(), 'command': 'python3 verification/swift-runtime-control-root-review/audit.py', 'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__)), 'receipt_bindings': {str(p.relative_to(ROOT)): sha(p) for p in paths}, 'verified_bindings': count, 'source_tree_sha256': combined['source_tree_sha256'], 'combined_passed_tests': counts, 'result': 'accepted private runtime-control foundation', 'source_review': ['Consuming opaque proof adoption and inline owner-bound tickets; no proof or legacy owner layout widening.', 'Atomic disjoint category/combined admission; cumulative counters and earliest carried deadline.', 'Actual storage drop precedes refunds; unclosed enlarged construction phase remains charged; immutable first failure plus separate cleanup observations.', 'Cancellation requested backing layout verified with official local Rust source and actual native allocation observation.'], 'limitations': ['No actual Swift cache, executor or accounted WASI composition; WASI None is absent observation, not zero.', 'Generic private release callers must pass every actual covered owner; composition must prove it.', 'No target reactor initialization/invocation, RSS or compiler stack claim, mobile/device, publication, FieldLog or GA acceptance.', 'Owner broad all-feature integration lint failure remains retained; scoped library and selected integration lint passes.']}
(HERE / 'receipt.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'verified_bindings': count, 'counts': counts, 'result': result['result']}))
