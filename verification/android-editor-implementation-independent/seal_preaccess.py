#!/usr/bin/env python3
"""Freeze only this lane's preaccess evidence, without any producer access."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / 'preaccess-seal.json'
members = []
for path in sorted(HERE.rglob('*')):
    if not path.is_file() or path == OUTPUT:
        continue
    assert not path.is_symlink()
    data = path.read_bytes()
    members.append({'path': path.relative_to(HERE).as_posix(), 'bytes': len(data),
                    'sha256': hashlib.sha256(data).hexdigest()})
OUTPUT.write_text(json.dumps({
    'schema': 1, 'at': datetime.datetime.now(datetime.UTC).isoformat(),
    'scope': 'Preaccess independent procedure, descriptor oracle and validator controls; no candidate access or qualification',
    'members': members, 'candidate_reads': 0, 'candidate_executions': 0,
    'next_stage': 'Await exact root-released frozen actual-source candidate',
}, indent=2) + '\n')
print(json.dumps({'members': len(members), 'bytes': sum(row['bytes'] for row in members),
                  'seal_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                  'candidate_reads': 0, 'candidate_executions': 0}))
