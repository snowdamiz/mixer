"""Close or read-only verify this independent review's exact member set."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def members():
    result=[]
    for p in sorted(HERE.rglob('*')):
        assert not p.is_symlink(),str(p)
        if p.is_file() and p!=HERE/'seal.json':
            b=p.read_bytes();result.append({'path':str(p.relative_to(HERE)),'bytes':len(b),'sha256':sha(b)})
    return result
if '--create' in sys.argv:
    assert not (HERE/'seal.json').exists(),'already closed'
    m=members()
    seal={'schema':1,'status':'closed-independent-actual-source-pure-codec-review','member_count':len(m),'member_bytes':sum(x['bytes'] for x in m),'members':m,
        'root_acceptance_canonical_runtime_operational_provenance_native_OTA_GA':False}
    (HERE/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
raw=(HERE/'seal.json').read_bytes();s=json.loads(raw);m=members()
assert s['members']==m and s['member_count']==len(m) and s['member_bytes']==sum(x['bytes'] for x in m)
print(json.dumps({'seal_sha256':sha(raw),'member_count':len(m),'member_bytes':s['member_bytes'],'exact_file_set':True}))
