#!/usr/bin/env python3
"""Seal only this owned design packet and its document, excluding seal pair."""
import hashlib
import json
from pathlib import Path
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
EXCLUDED = {BASE / 'seal.json', BASE / 'seal.sha256'}
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while b:=f.read(65536): h.update(b)
    return h.hexdigest()
paths=[ROOT/'docs/swift-ordered-retention-analyzer.md']+[
    p for p in BASE.rglob('*') if p.is_file() and p not in EXCLUDED]
assert not any('__pycache__' in p.parts for p in paths)
members=[{'path':str(p.relative_to(ROOT)), 'bytes':p.stat().st_size,'sha256':digest(p)}
         for p in sorted(paths)]
seal={'version':1,'scope':'Finite offline analyzer design and support only',
      'excluded':[str(p.relative_to(ROOT)) for p in sorted(EXCLUDED)],'members':members}
(BASE/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
(BASE/'seal.sha256').write_text(digest(BASE/'seal.json')+'\n')
print(json.dumps({'members':len(members),'bytes':sum(m['bytes'] for m in members),
                  'seal_sha256':digest(BASE/'seal.json')},sort_keys=True))
