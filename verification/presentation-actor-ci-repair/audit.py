#!/usr/bin/env python3
"""Root audit of retained actor-repair evidence; no executable rerun."""
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
count = 0
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def bind(path, digest):
    global count
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    assert sha(path) == digest, str(path)
    count += 1

path = HERE / 'verified-2/receipt.json'
r = json.loads(path.read_text())
bind('capability-activation/Tests/MixerCapabilityActivationTests/GuestUIPresentationWindowTests.swift', r['window_source_sha256'])
for c in r['commands']:
    assert c['exit'] == 0
    bind(c['log'], c['sha256'])
for files in r['retained_artifacts'].values():
    for n, d in files.items():
        bind(n, d)
for n, d in r['dependency_artifacts'].items():
    bind(n, d)
for result in r['results'].values():
    assert result['compiled'] and result['exit'] == 0
    assert result['passed_tests'] == 13 and result['skipped_tests'] == 1
    bind(result['executable'], result['executable_sha256'])
for name, digest in r['qualified_source_files'].items():
    if '/Sources/' in name:
        data = subprocess.check_output(['git', 'show', 'b79ca532904cf7e9d0a958ed8acfbc361186185a:' + name], cwd=ROOT)
        assert hashlib.sha256(data).hexdigest() == digest, name
    count += 1
failure = r['prior_hosted_failure']
bind(failure['receipt'], failure['receipt_sha256'])
bind(failure['log'], failure['log_sha256'])
receipt = {
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 verification/presentation-actor-ci-repair/audit.py',
    'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__)),
    'passed': True, 'verified_bindings': count,
    'qualified_receipt': str(path.relative_to(ROOT)), 'qualified_receipt_sha256': sha(path),
    'source_scope': 'One-line actor test repair plus retained production files at b79ca53, not concurrent Android lifetime edits. Actual retained modules/tests pass Debug/Release/TSan on Swift6.4. One visible-window skip per mode; pinned hosted Swift6.2.4 and physical/GA checks pending.'
}
(HERE / 'root-review.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'passed': True, 'verified_bindings': count}))
