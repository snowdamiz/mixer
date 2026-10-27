#!/usr/bin/env python3
"""Seal this owned candidate directory; never changes accepted/frozen inputs."""
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
members=[]
for path in sorted(D.rglob('*')):
    if path.is_file() and path.name!='seal.json':
        if path.is_symlink():raise ValueError('symlink member')
        raw=path.read_bytes();members.append({'path':str(path.relative_to(D)),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
seal={'schema':1,'status':'frozen-source146-string-provenance-candidate-ready-for-independent-review','source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','host_tree_sha256':'027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2','member_count':len(members),'bytes':sum(x['bytes'] for x in members),'members':members,'source_closure_under_exact_caller_contract':True,'L_str_candidate':5080,'independent_review_required':True,'actual_P0_caller_selected':False,'selected_whole_host_bound':False,'operational_grant':False,'runtime_or_OTA_or_GA':False}
raw=(json.dumps(seal,indent=2,sort_keys=True)+'\n').encode();(D/'seal.json').write_bytes(raw)
print(json.dumps({'members':len(members),'bytes':seal['bytes'],'seal_sha256':hashlib.sha256(raw).hexdigest(),'L_str_candidate':5080,'independent_review_required':True,'operational_grant':False},sort_keys=True))
