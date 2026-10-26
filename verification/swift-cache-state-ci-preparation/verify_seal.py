#!/usr/bin/env python3
"""Read-only closure verification; never execute packed tests or compilers."""
import hashlib,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent
def need(v,m):
 if not v:raise RuntimeError(m)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
s=json.loads((HERE/'seal.json').read_bytes());rows=[]
for p in sorted(HERE.rglob('*')):
 need(not p.is_symlink(),'Symlink member')
 if p.is_file()and p.name!='seal.json':rows.append({'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':sha(p)})
need(rows==s['members']and len(rows)==s['member_count']and sum(r['bytes']for r in rows)==s['total_bytes'],'Complete sealed roster differs')
need(hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()==s['tree_sha256'],'Sealed tree differs')
print(json.dumps({'seal_sha256':sha(HERE/'seal.json'),'verified_members':len(rows),'verified_bytes':s['total_bytes'],'read_only':True}))
