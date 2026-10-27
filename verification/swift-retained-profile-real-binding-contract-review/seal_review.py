"""Check by default; --write freezes only this owned review directory."""
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def observed():
    out=[]
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and path.name!='seal.json':
            data=path.read_bytes()
            out.append({'path':str(path.relative_to(HERE)),'bytes':len(data),'sha256':sha(data)})
    return out
def main():
    members=observed()
    if sys.argv[1:]==['--write']:
        seal={'schema':1,'status':'closed-independent-contract-review-data-codec-selection',
            'member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),
            'members':members,'reviewed_input_seal_sha256':'e6e4b3b1d32ade11ef3136f3e4416e86bb8c0a32889af6bbe62a1799cb093b01',
            'actual_product_behavior_executed':False,'canonical_or_release_authority_accepted':False,
            'self_seal':'seal.json excluded; no sidecar declared'}
        (HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    else:
        assert not sys.argv[1:],'only --write is supported'
        seal=json.loads((HERE/'seal.json').read_text())
        assert members==seal['members'],'member mismatch'
        assert len(members)==seal['member_count']
        assert sum(m['bytes'] for m in members)==seal['member_bytes']
    print(json.dumps({'seal_sha256':sha((HERE/'seal.json').read_bytes()),'members':seal['member_count'],'bytes':seal['member_bytes'],'exact_file_set':True}))
if __name__=='__main__':main()
