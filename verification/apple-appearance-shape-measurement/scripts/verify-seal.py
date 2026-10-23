#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
receipt=json.loads((ROOT/'receipt.json').read_text())
for e in receipt['artifacts']:
    p=ROOT/e['path'];assert p.stat().st_size==e['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'],e['path']
actual=[str(p.relative_to(ROOT)) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='receipt.json' and not any(t in ['build','__pycache__','xcuserdata'] for t in p.relative_to(ROOT).parts)]
assert actual==[e['path'] for e in receipt['artifacts']],'Retained artifact set changed'
assert hashlib.sha256(json.dumps(receipt['artifacts'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==receipt['artifactCollectionSHA256']
doc=receipt['externalDocument'];assert hashlib.sha256((REPO/doc['path']).read_bytes()).hexdigest()==doc['sha256']
for stage in [1,2]:
    for e in json.loads((ROOT/f'source-lock-stage{stage}.json').read_text())['files']:
        p=ROOT/e['path']
        if stage==1 and e['path']=='instrumented-sdk/Sources/MixerApple/ShapeProbe.swift':p=ROOT/'source-stages/stage1/ShapeProbe.swift'
        assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'],p
parent=json.loads((ROOT/'parent-input-lock.json').read_text())
for e in parent['files']:assert hashlib.sha256((REPO/e['path']).read_bytes()).hexdigest()==e['sha256'],e['path']
assert hashlib.sha256((ROOT.parent/'apple-appearance-measurement/receipt.json').read_bytes()).hexdigest()==parent['receiptSHA256']
print('PASS:',len(actual),'sealed shape artifacts, source stages, immutable parent inputs and findings document; collection',receipt['artifactCollectionSHA256'])
