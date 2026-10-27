#!/usr/bin/env python3
"""Seal this review only; --verify performs no writes."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def main():
    assert not (HERE/'owned-scratch').exists()
    members=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and p!=HERE/'seal.json':
            raw=p.read_bytes();members.append({'path':str(p.relative_to(HERE)),'bytes':len(raw),'sha256':sha(raw)})
    seal={'schema':1,'scope':'Independent frozen145-overlay emission arithmetic and logical-action review; pure helper/geometry host controls only; no writer/debit/storage/GA selection',
        'member_count':len(members),'member_bytes':sum(r['bytes'] for r in members),'tree_sha256':sha(canonical(members)),'members':members}
    raw=(json.dumps(seal,indent=2,sort_keys=True)+'\n').encode()
    if '--verify' in sys.argv:assert (HERE/'seal.json').read_bytes()==raw
    else:
        assert not (HERE/'seal.json').exists(),'Preserve a previous seal'
        (HERE/'seal.json').write_bytes(raw)
    print(json.dumps({k:v for k,v in seal.items() if k!='members'},sort_keys=True))
    print('seal_sha256='+sha(raw))
if __name__=='__main__':main()
