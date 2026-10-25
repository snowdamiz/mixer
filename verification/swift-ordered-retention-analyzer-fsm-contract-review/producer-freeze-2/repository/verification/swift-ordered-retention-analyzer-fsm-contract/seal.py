#!/usr/bin/env python3
"""Seal only this preparatory contract packet and its owned document."""
import hashlib
import json
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
EXCLUDED={BASE/'seal.json',BASE/'seal.sha256'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[ROOT/'docs/swift-ordered-retention-analyzer-fsm-contract.md']+[
 p for p in BASE.rglob('*') if p.is_file() and p not in EXCLUDED]
assert not any('__pycache__' in p.parts for p in paths)
rows=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(paths)]
seal=dict(schema=1,scope='Preparatory fixture-only FSM contract; no implementation selection or semantic authority',members=rows,
          excluded=[str(p.relative_to(ROOT)) for p in sorted(EXCLUDED)])
(BASE/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
(BASE/'seal.sha256').write_text(digest(BASE/'seal.json')+'\n')
print(json.dumps(dict(members=len(rows),bytes=sum(r['bytes'] for r in rows),sha256=digest(BASE/'seal.json')),sort_keys=True))
