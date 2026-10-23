#!/usr/bin/env python3
"""Audit retained reservation qualification against current owned sources."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
bindings = 0
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def check(path, digest):
    global bindings
    assert sha(ROOT / path) == digest, path
    bindings += 1


def artifacts(values):
    for path, value in values.items():
        if isinstance(value, dict):
            artifacts(value)
        else:
            check(path, value)


receipts = {}
for name in ('candidate-1', 'integration-1'):
    path = HERE / name / 'receipt.json'
    d = json.loads(path.read_text())
    receipts[str(path.relative_to(ROOT))] = sha(path)
    for relative, digest in d['source_files'].items():
        check(relative, digest)
        check(str(Path(d['source']) / relative), digest)
    for command in d['commands']:
        assert command['exit'] == command.get('expected_exit', 0), command['name']
        check(command['log'], command['sha256'])
    artifacts(d['artifacts'])
    if name == 'integration-1':
        check(d['dependency_receipt'], d['dependency_receipt_sha256'])
        base = json.loads((ROOT / d['dependency_receipt']).read_text())
        check(base['source_manifest'], d['dependency_source_manifest_sha256'])
        manifest = json.loads((ROOT / base['source_manifest']).read_text())
        for relative, digest in manifest['files'].items():
            check(str(Path(base['source']) / relative), digest)
            if relative.startswith(('sdk/Sources/', 'updates/Sources/', 'runtime-identity/Sources/', 'experimental-capability-runtime/Sources/')):
                check(relative, digest)
        for relative, digest in d['dependency_artifacts'].items():
            check(str(Path(base['dylib']).parents[1] / relative), digest)

receipt = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/presentation-reservation/audit.py',
    'python': platform.python_version(),
    'auditor_sha256': sha(Path(__file__)),
    'receipts': receipts,
    'verified_bindings': bindings,
    'result': 'All current source, retained source, dependency, command-output and artifact bindings match.',
    'scope': 'Scoped Debug/Release/TSan reservation XCTest and privacy negatives; complete current activation-module link and reservation XCTest. No Android runtime binding, full hosted suite, physical devices, published-consumer or GA qualification. Caller must join tails and relinquish other owner aliases before retiring the presentation obligation.',
}
(HERE / 'root-review.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'verified_bindings': bindings, 'result': receipt['result']}))
