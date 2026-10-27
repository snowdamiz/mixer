"""Freeze only this owned packet after successful pure checks and cleanup."""
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
assert not (D/'owned-work').exists()
assert json.loads((D/'controls.json').read_text())['passed']
rows=[]
for p in sorted(D.rglob('*')):
 if p.name=='seal.json' or not p.is_file() or '__pycache__' in p.parts:continue
 assert not p.is_symlink();b=p.read_bytes();rows.append(dict(path=str(p.relative_to(D)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
value=dict(schema=1,status='frozen-finite-loader-MIR-work-proposal-independent-review-pending',member_count=len(rows),member_bytes=sum(r['bytes'] for r in rows),members=rows,operational_grant=False,source_members=145,host_support_members=11)
b=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode();(D/'seal.json').write_bytes(b)
print(json.dumps(dict(members=len(rows),bytes=value['member_bytes'],seal_sha256=hashlib.sha256(b).hexdigest())))
