"""Freeze source146 preparation without promoting quote or root authority."""
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
assert not (D/'owned-work').exists();assert json.loads((D/'controls.json').read_text())['passed']
rows=[]
for p in sorted(D.rglob('*')):
 if p.name=='seal.json' or not p.is_file() or '__pycache__' in p.parts:continue
 assert not p.is_symlink();b=p.read_bytes();rows.append(dict(path=str(p.relative_to(D)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
v=dict(schema=1,status='frozen-exact-source146-loader-work-rebind-preparation-independent-review-pending',member_count=len(rows),member_bytes=sum(r['bytes'] for r in rows),members=rows,source_members=146,host_support_members=11,source_tree_sha256='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',corrected145_root_acceptance_sha256='e819f93e5219c631255c4322f291539c72b2660f8b7cb593a51cb4beb78742c7',source146_quote_accepted=False,operational_grant=False)
b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode();(D/'seal.json').write_bytes(b);print(json.dumps(dict(members=len(rows),bytes=v['member_bytes'],seal_sha256=hashlib.sha256(b).hexdigest())))
