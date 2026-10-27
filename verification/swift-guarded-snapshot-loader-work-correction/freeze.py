"""Freeze correction only after successful finite checks and immutable custody."""
import hashlib,json
from pathlib import Path
from custody import verify_inputs
D=Path(__file__).resolve().parent
inputs=verify_inputs();assert json.loads((D/'controls.json').read_text())['passed']
rows=[]
for p in sorted(D.rglob('*')):
 if p.name=='seal.json' or not p.is_file() or '__pycache__' in p.parts:continue
 assert not p.is_symlink();b=p.read_bytes();rows.append(dict(path=str(p.relative_to(D)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
v=dict(schema=1,status='frozen-receiver-specific-loader-work-correction-independent-review-pending',member_count=len(rows),member_bytes=sum(r['bytes'] for r in rows),members=rows,producer_seal_sha256=inputs['producer_seal_sha256'],root_finding_sha256=inputs['root_finding_sha256'],source_tree_sha256=inputs['source_tree_sha256'],source_members=145,host_support_members=11,operational_grant=False,source146_rebinding_required=True)
b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode();(D/'seal.json').write_bytes(b)
print(json.dumps(dict(members=len(rows),bytes=v['member_bytes'],seal_sha256=hashlib.sha256(b).hexdigest())))
