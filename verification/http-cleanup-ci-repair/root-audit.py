#!/usr/bin/env python3
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
count = 0


def check(path, expected):
    global count
    assert sha(ROOT / path) == expected, path
    count += 1


d = json.loads((HERE / 'investigation.json').read_text())
r = json.loads((HERE / 'receipt.json').read_text())
assert r['scopedChecksPassed'] and r['productTransportUnchanged']
assert not r['exactHostedFailureBranchAttributed']
for row in d['initialSource']['files']:
    original = subprocess.check_output(['git', 'show', '401e16c:' + row['path']], cwd=ROOT)
    assert hashlib.sha256(original).hexdigest() == row['sha256'], row['path']
    count += 1
for row in d['finalSource']['files']:
    check(row['path'], row['sha256'])
    check(str(Path(d['snapshot']) / row['path']), row['sha256'])
for command in d['commands']:
    assert command['exitCode'] == command['expectedExitCode'], command['name']
    check(command['output'], command['outputSHA256'])
for command in r['finalCommands']:
    assert command['exitCode'] == 0
    assert command['sourceDigest'] == r['finalSourceDigest']
    check(command['output'], command['outputSHA256'])
check(d['hostedFailure']['output'], d['hostedFailure']['sha256'])
receipt = {'observed_utc': datetime.now(timezone.utc).isoformat(),
           'command': 'python3 verification/http-cleanup-ci-repair/root-audit.py',
           'python': platform.python_version(), 'auditor_sha256': sha(Path(__file__)),
           'owner_receipt_sha256': sha(HERE / 'receipt.json'),
           'investigation_sha256': sha(HERE / 'investigation.json'),
           'verified_bindings': count,
           'review': 'Test-only ordering correction preserves capacity reuse, exact started-request stop counts and the existing cleanup wait bound. Separate pre-resume expiry regression requires native invalidation. Original probe fails for a legal no-start ordering; exact hosted branch remains unknown.',
           'scope': 'Retained scoped host evidence audit; no independent test rerun, product transport change, physical-device, production TLS or GA claim. Pinned Swift6.2.4 remains pending hosted CI.'}
(HERE / 'root-review.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'verified_bindings': count, 'result': 'passed'}))
