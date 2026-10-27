#!/usr/bin/env python3
"""Freeze this owned packet only. No Git, compiler or external execution."""
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
members=[]
for p in sorted(D.rglob('*')):
    if not p.is_file() or p.name=='seal.json' or '__pycache__' in p.parts:continue
    raw=p.read_bytes();members.append({'path':str(p.relative_to(D)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
seal={'schema':1,'status':'frozen-conditional-source146-whole-host-logical-work-composition-candidate',
 'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
 'host_tree_sha256':'027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2',
 'members':members,'new_compiler_or_product_execution':False,'whole_host_funding_or_grant':False}
raw=(json.dumps(seal,indent=2,sort_keys=True)+'\n').encode();(D/'seal.json').write_bytes(raw)
print(json.dumps({'seal_sha256':hashlib.sha256(raw).hexdigest(),'members':len(members),'bytes':sum(x['bytes'] for x in members)},sort_keys=True))
