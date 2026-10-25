#!/usr/bin/env python3
"""Verify this lane's own sealed outputs; read-only and offline."""
import hashlib
import json
from pathlib import Path
import stat

base = Path(__file__).resolve().parent
root = base.parents[1]
raw = (base / 'handoff.json').read_bytes()
assert hashlib.sha256(raw).hexdigest() == (base / 'handoff.sha256').read_text().strip()
handoff = json.loads(raw)
assert hashlib.sha256((json.dumps(handoff['members'], indent=2, sort_keys=True) + '\n').encode()).hexdigest() == handoff['memberTreeSHA256']
for name, expected in handoff['members'].items():
    path = root / name
    assert path.is_file() and not path.is_symlink(), name
    content = path.read_bytes()
    assert len(content) == expected['bytes'] and hashlib.sha256(content).hexdigest() == expected['sha256'], name
    assert stat.S_IMODE(path.stat().st_mode) == 0o444, name
assert stat.S_IMODE((base / 'handoff.json').stat().st_mode) == 0o444
assert stat.S_IMODE((base / 'handoff.sha256').stat().st_mode) == 0o444
for directory in [base] + [p for p in base.rglob('*') if p.is_dir()]:
    assert stat.S_IMODE(directory.stat().st_mode) == 0o555, str(directory)
print(json.dumps({'passed': True, 'members': len(handoff['members']), 'memberTreeSHA256': handoff['memberTreeSHA256'], 'handoffSHA256': hashlib.sha256(raw).hexdigest(), 'gaAccepted': False}))
