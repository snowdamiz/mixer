#!/usr/bin/env python3
"""Seal only this review's explicit owned closure, using standard SHA-256."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DOC = ROOT / 'docs/swift-ordered-retention-analyzer-review.md'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(65536):
            h.update(chunk)
    return h.hexdigest()


excluded = {BASE / 'seal.json', BASE / 'seal.sha256'}
paths = [DOC] + sorted(p for p in BASE.rglob('*') if p.is_file() and p not in excluded)
rows = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size,
         'sha256': digest(p)} for p in paths]
assert len(rows) == len({r['path'] for r in rows})
raw = (json.dumps({'schema': 1, 'scope': 'independent bounded design review only',
                   'excluded': [str((BASE / n).relative_to(ROOT))
                                for n in ('seal.json', 'seal.sha256')],
                   'members': rows}, indent=2, sort_keys=True) + '\n').encode()
(BASE / 'seal.json').write_bytes(raw)
(BASE / 'seal.sha256').write_text(hashlib.sha256(raw).hexdigest() + '\n')
print(json.dumps({'sha256': hashlib.sha256(raw).hexdigest(), 'members': len(rows),
                  'bytes': sum(row['bytes'] for row in rows)}, sort_keys=True))
