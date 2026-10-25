#!/usr/bin/env python3
"""Finalize reviewer metadata and seal only assigned evidence/report paths."""
import hashlib
import json
import pathlib
import stat
import sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORT = ROOT / 'docs/apple-focus-system-join-correction-review.md'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

assert not (HERE / 'handoff.json').exists()
receipt = json.loads((HERE / 'receipt.json').read_bytes())
assert receipt['passed'] and receipt['independentFiniteControlsPassed'] == 57 and receipt['producerHostMethodsPassed'] == 38
failure = HERE / 'failure.json'
assert failure.read_bytes() == (HERE / 'attempts/attempt-1/failure.json').read_bytes()
failure.unlink()
command = {
    'argv': [sys.executable, '-B', 'verification/apple-focus-system-join-correction-review/review.py'],
    'cwd': str(ROOT), 'toolVersion': sys.version, 'exitCode': 0,
    'stdout': 'stdout', 'stderr': 'stderr', 'scriptSHA256': sha((HERE / 'review.py').read_bytes()),
    'shellRedirection': '> verification/apple-focus-system-join-correction-review/stdout 2> verification/apple-focus-system-join-correction-review/stderr',
    'scope': 'Successful second review attempt; independent controls plus bounded host method rerun',
}
write(HERE / 'command.json', command)
receipt['command'] = command
receipt['successfulAttempt'] = 2
receipt['retainedFailedAttempts'] = [{
    'attempt': 1, 'failure': 'attempts/attempt-1/failure.json',
    'reason': 'Reviewer inventory checker assumed one external document and no checksum sidecar; stopped before behavior tests',
    'behaviorControlsExecuted': 0, 'candidateChanges': False,
}]
receipt['seal'] = {'argv': [sys.executable, '-B', str(HERE / 'seal.py')], 'toolVersion': sys.version,
                   'scriptSHA256': sha(pathlib.Path(__file__).read_bytes()),
                   'observedUTC': datetime.now(timezone.utc).isoformat(),
                   'verificationCommand': [sys.executable, '-B', str(HERE / 'verify_seal.py')]}
write(HERE / 'receipt.json', receipt)
assert not list(HERE.rglob('__pycache__'))
files = [p for p in HERE.rglob('*') if p.is_file()] + [REPORT]
members = {}
for path in sorted(files):
    path.chmod(0o444)
    raw = path.read_bytes()
    members[str(path.relative_to(ROOT))] = {'bytes': len(raw), 'sha256': sha(raw), 'mode': stat.S_IMODE(path.stat().st_mode)}
handoff = {
    'schema': 1, 'scope': receipt['scope'], 'status': receipt['status'], 'members': members,
    'correctionHandoffSHA256': '2121ef09603e12a5c69a8918a1494c1d3e2f34dc5e6354080cfe38b50649b16d',
    'producerHandoffSHA256': '5d88cd0069f7e83e73b95903ecf0e9e6b721a73328193653e8e1da8903c81427',
    'initialReviewHandoffSHA256': 'e66d1f5710d5614fc668bec3fc6759fb6080a91002516f13d43994dca2ab35a4',
    'frozenReplayHostAccepted': True, 'futureRuntimeIngestionAccepted': False,
    'nativeAccepted': False, 'nativePass': False, 'gaAccepted': False,
    'sourceRevisionReportedByRoot': receipt['sourceRevisionReportedByRoot'],
    'sourceArchiveSHA256': receipt['sourceArchiveSHA256'], 'sourceMembers': 40,
    'independentFiniteControlsPassed': 57, 'producerHostMethodsPassed': 38,
    'originalOraclePassed': False, 'originalFailingPredicates': ['actualNativeFocusTraversal'],
    'physicalPhones': 'disconnected-deferred',
}
path = HERE / 'handoff.json'
write(path, handoff)
path.chmod(0o444)
print(json.dumps({'members': len(members), 'handoffSHA256': sha(path.read_bytes()), 'frozenReplayHostAccepted': True, 'nativePass': False}, sort_keys=True))
