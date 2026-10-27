"""Freeze this compact independent review only; no compiler/runtime/subprocess."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
assert not (HERE/'seal.json').exists() and not (HERE/'owned-work').exists()
assert json.loads((HERE/'cleanup.json').read_bytes())['completed']
members=[]
for p in sorted(HERE.rglob('*')):
    if p.is_file():
        b=p.read_bytes();members.append({'path':str(p.relative_to(HERE)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
canonical=json.dumps(members,sort_keys=True,separators=(',',':')).encode()
value={'schema':1,'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'members':members,'tree_sha256':hashlib.sha256(canonical).hexdigest(),'scope':'Independent exact source145/host11 descriptor preparation custody, identity preimages, pure checks and production metadata only; no actual loader/VM/guest/engine/writer execution or final-composition/GA acceptance'}
raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode();(HERE/'seal.json').write_bytes(raw)
print(json.dumps({'seal_sha256':hashlib.sha256(raw).hexdigest(),'members':value['member_count'],'bytes':value['member_bytes'],'tree_sha256':value['tree_sha256']},sort_keys=True))
