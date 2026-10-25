#!/usr/bin/env python3
"""Seal only the explicitly owned review doc and directory."""
import datetime
import hashlib
import json
from pathlib import Path

base = Path(__file__).resolve().parent
root = base.parents[1]
doc = root / 'docs/apple-settings-fixed-chunk-native-result-review.md'
members = {}
for path in [doc] + sorted(p for p in base.rglob('*') if p.is_file() and p.name not in ['handoff.json', 'handoff.sha256']):
    assert not path.is_symlink()
    content = path.read_bytes()
    members[str(path.relative_to(root))] = {'kind': 'file', 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(), 'mode': 0o444}
stable = lambda value: (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
handoff = {'schema': 1, 'status': 'offline-review-complete-original-native-failure-retained',
           'observedUTC': datetime.datetime.now(datetime.UTC).isoformat(),
           'rootResultManifestSHA256': 'ccb7ce47693677fcfc43f68939fdb9eeaa86bdeb6090ee9cfb5a5257a232382c',
           'rootSelectionSHA256': 'abc1d883af3ad8b62e537ee10c7f1d7a925bfc0e6f0422ccfa5819da6d907b27',
           'originalOracleUnchanged': True, 'originalOracleReplayExact': True,
           'nativeAttemptsByReview': 0, 'nativeQueriesByReview': 0,
           'originalRunPassed': False, 'nativeKeyboardQualification': False,
           'fullSixCaseQualification': False, 'gaAccepted': False,
           'physicalPhones': 'disconnected-deferred', 'members': members,
           'memberTreeSHA256': hashlib.sha256(stable(members)).hexdigest()}
raw = stable(handoff)
(base / 'handoff.json').write_bytes(raw)
(base / 'handoff.sha256').write_text(hashlib.sha256(raw).hexdigest() + '\n')
for path in [doc] + [p for p in base.rglob('*') if p.is_file()]: path.chmod(0o444)
for directory in sorted([p for p in base.rglob('*') if p.is_dir()], key=lambda p: len(p.parts), reverse=True): directory.chmod(0o555)
base.chmod(0o555)
print(json.dumps({'handoffSHA256': hashlib.sha256(raw).hexdigest(), 'members': len(members), 'memberTreeSHA256': handoff['memberTreeSHA256']}))
