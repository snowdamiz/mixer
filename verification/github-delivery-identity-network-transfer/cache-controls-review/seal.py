#!/usr/bin/env python3
"""Seal this offline review packet; no runner, child, or process-group work."""
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

base = pathlib.Path(__file__).resolve().parent
rows = []
for path in sorted(base.rglob('*')):
    if path.is_file() and path.name != 'packet-manifest.json':
        if path.is_symlink():
            raise RuntimeError('Symlink in review packet')
        data = path.read_bytes()
        rows.append({'path': path.relative_to(base).as_posix(), 'bytes': len(data),
                     'sha256': hashlib.sha256(data).hexdigest()})
manifest = {'schema': 1, 'sealed_at': datetime.now(timezone.utc).isoformat(),
            'python': sys.version, 'files': rows,
            'tree_sha256': hashlib.sha256(json.dumps(rows, sort_keys=True,
                            separators=(',', ':')).encode()).hexdigest(),
            'scope': 'Offline failed-attempt cache controls review; no execution/pass claim'}
with (base / 'packet-manifest.json').open('x') as stream:
    stream.write(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
print(json.dumps({'sealed': True, 'files': len(rows),
                  'tree_sha256': manifest['tree_sha256']}))
