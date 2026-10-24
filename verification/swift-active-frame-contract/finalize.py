#!/usr/bin/env python3
"""Freeze an existing successful compiler packet for independent contract review."""
from pathlib import Path
import datetime, hashlib, json, sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def encoded(x): return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
folder=Path(sys.argv[1]).resolve()
r=json.loads((folder/'receipt.json').read_text())
assert r['status']=='contract-compiler-layout-abi-privacy-preflight-only'
schema=json.loads((folder/'inventory-schema.json').read_text())
mapping=[]
for layout in r['layouts']:
    if not layout['label'].startswith('candidate'): continue
    fields={}
    for line in layout['records']:
        if line.startswith('AF_FIELD '):
            _,name,offset,width,align=line.split()
            fields[name]=dict(offset=int(offset),bytes=int(width),alignment=int(align))
    mapping.append(dict(configuration=layout['label'],positions=[dict(row,**fields[row['field']]) for row in schema]))
(folder/'binding-map.json').write_bytes(encoded(dict(schema=1,status='proposal-declaration-association-not-runtime-completeness',configurations=mapping,nestedComponent=json.loads((folder/'nested-value-component.json').read_text()))))
bindings={}
for path in sorted(HERE.rglob('*')):
    if path.is_file() and 'build' not in path.relative_to(HERE).parts and '__pycache__' not in path.parts and path.name!='seal.json':
        bindings[str(path.relative_to(ROOT))]=sha(path)
doc=ROOT/'docs/swift-active-frame-contract.md'
bindings[str(doc.relative_to(ROOT))]=sha(doc)
seal=dict(schema=1,status='frozen-proposal-awaiting-independent-accounting-and-root-review',
    frozenUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    results=str(folder.relative_to(HERE)),sourceTreeSHA256=r['sourceTreeSHA256'],
    model='gpt-6.1-sol',reasoningEffort='xhigh',bindings=bindings,
    implementationApplied=False,frameExecution=False,nativeRuntime=False,
    semanticAcceptance=False,accountingCompletenessAccepted=False)
(HERE/'seal.json').write_bytes(encoded(seal))
print(json.dumps(dict(status=seal['status'],results=seal['results'],sealSHA256=sha(HERE/'seal.json'),bindings=len(bindings)),sort_keys=True))
