"""Seal only this owned packet; no Git or root metadata actions."""
from pathlib import Path
import datetime,hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
assert not (HERE/'seal.json').exists(),'already frozen'
assert json.loads((HERE/'results.json').read_bytes())['all_passed']
rows=[]
for p in sorted(HERE.rglob('*')):
 if p.is_dir():continue
 assert not p.is_symlink() and '__pycache__' not in p.parts,p
 b=p.read_bytes();rows.append({'path':str(p.relative_to(HERE)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
s={'schema':1,'status':'frozen-bounded-complete-conditional-source146-storage-interface','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','host_tree_sha256':'027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2','member_count':len(rows),'total_bytes':sum(r['bytes'] for r in rows),'members':rows,'whole_host_quote_or_grant':False,'native_runtime_or_GA':False}
(HERE/'seal.json').write_text(json.dumps(s,sort_keys=True,indent=2)+'\n')
print(json.dumps({'seal_sha256':hashlib.sha256((HERE/'seal.json').read_bytes()).hexdigest(),'members':len(rows),'bytes':s['total_bytes']}))
