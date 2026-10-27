"""Seal or read-only rehash this owned review directory; no process launches."""
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
members=[]
for p in sorted(D.rglob('*')):
    assert not p.is_symlink(),str(p)
    if p.is_file() and p.name!='seal.json':
        assert '__pycache__' not in p.parts and p.suffix!='.pyc',str(p)
        b=p.read_bytes();members.append(dict(path=str(p.relative_to(D)),bytes=len(b),sha256=sha(b)))
seal=dict(schema=1,status='frozen-independent-native-open-interface-review-pending-root-selection',members=members,
    member_count=len(members),member_bytes=sum(r['bytes'] for r in members),tree_sha256=sha(canonical(members)),
    candidate_seal_sha256='7b5762f1955fefa2060b0d4fdb4dd393cb8b38c94078159ddf6bc538a22c67f5',
    source_tree_sha256='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
    actual_immutable_caller_or_executable_bound=False,actual_pricing_policy_grant=False,product_runtime=False,native_runtime=False,GA_verified=False)
raw=(json.dumps(seal,indent=2,sort_keys=True)+'\n').encode()
if '--check' in sys.argv:assert (D/'seal.json').read_bytes()==raw,'independent frozen member drift'
else:
    assert not (D/'seal.json').exists(),'already frozen'
    (D/'seal.json').write_bytes(raw)
print(json.dumps(dict(seal_sha256=sha(raw),members=len(members),bytes=seal['member_bytes'],checked='--check' in sys.argv)))
