#!/usr/bin/env python3
"""Freeze this candidate after complete final own host checks; no old runner import."""
import hashlib,json,pathlib,sys
from datetime import datetime,timezone
HERE=pathlib.Path(__file__).resolve().parent
def need(v,m):
 if not v:raise RuntimeError(m)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
receipt=json.loads((HERE/'runs/rust-1-99-final2/receipt.json').read_bytes())
need(receipt['status']=='passed-host-fixture-check'and not receipt['errors'],'Final host check is not complete')
need(receipt['runner']['sha256']==sha(HERE/'check_cache_state.py'),'Final runner changed')
need(all(c['child_returned']and c['owned_group_gone']for c in receipt['commands']),'Owned children pending')
need(receipt['cleanup']['removed'],'Owned cleanup incomplete')
need(not list(HERE.rglob('__pycache__'))and not list(HERE.rglob('*.rlib'))and not list(HERE.rglob('scratch')),'Build products/scratch remain')
need(not(HERE/'seal.json').exists(),'Candidate already frozen')
rows=[]
for p in sorted(HERE.rglob('*')):
 need(not p.is_symlink(),'Symlink member')
 if p.is_file():rows.append({'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':sha(p)})
seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve())],'python':sys.version,'builder_sha256':sha(pathlib.Path(__file__).resolve()),'members':rows,'member_count':len(rows),'total_bytes':sum(r['bytes']for r in rows),'tree_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'excluded':['seal.json'],'source_sha256':'f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b','root_implementation_selection_sha256':'6628509512df7fd4bd69a4f45e4a9374c0b1653079a49236d8a2a0f69e67b0c5','status':'isolated-CI-candidate-ready-for-independent-review','actual_local_Rust_1_99_host_complete':True,'Rust_1_98_1_pending':True,'canonical_CI_integration_selected':False,'GA_qualified':False}
(HERE/'seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
print(json.dumps({'seal_sha256':sha(HERE/'seal.json'),'members':len(rows),'bytes':seal['total_bytes'],'tree_sha256':seal['tree_sha256']}))
