#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
members=[]
for path in sorted(D.rglob('*')):
    if not path.is_file() or path.name=='seal.json' or '__pycache__' in path.parts:continue
    raw=path.read_bytes();members.append({'path':str(path.relative_to(D)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
value={'schema':1,'status':'frozen-independent-conditional-whole-host-work-review','source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','host_tree_sha256':'027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2','candidate_seal_sha256':'95c1a3087b36996dc06e8411f97e3ebce2610120f9ac742326824a52ab9c63ca','members':members,'whole_host_funding':False,'operational_grant':False,'new_compiler_or_product_or_native_run':False}
raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode();(D/'seal.json').write_bytes(raw)
print(json.dumps({'seal_sha256':hashlib.sha256(raw).hexdigest(),'members':len(members),'bytes':sum(m['bytes'] for m in members)},sort_keys=True))
