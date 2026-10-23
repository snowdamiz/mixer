#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'receipt.json').read_text())
for e in r['artifacts']:
 p=ROOT/e['path'];assert p.stat().st_size==e['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'],e['path']
actual=[str(p.relative_to(ROOT)) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='receipt.json' and not any(part in ['build','__pycache__','xcuserdata'] for part in p.relative_to(ROOT).parts)]
assert actual==[e['path'] for e in r['artifacts']],'retained artifact set changed'
collection=hashlib.sha256(json.dumps(r['artifacts'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
assert collection==r['artifactCollectionSHA256']
e=r['externalDocument'];p=ROOT.parents[1]/e['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256']
print(f'PASS: sealed {len(actual)} measurement artifacts and external findings document; collection {collection}')
print('Receipt SHA-256: '+hashlib.sha256((ROOT/'receipt.json').read_bytes()).hexdigest())
