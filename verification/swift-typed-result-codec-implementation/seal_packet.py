"""Close or read-only verify the exact packet. No inferred neighboring artifacts."""
from pathlib import Path
import hashlib,json,sys
H=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def members():
 out=[]
 for p in sorted(H.rglob('*')):
  if p.is_file() and p!=H/'seal.json':
   b=p.read_bytes();out.append({'path':str(p.relative_to(H)),'bytes':len(b),'sha256':sha(b)})
 return out
if '--create' in sys.argv:
 assert not (H/'seal.json').exists(),'already frozen'
 m=members();s={'schema':1,'status':'frozen-actual-private-typed-result-codec-host-packet','member_count':len(m),'member_bytes':sum(x['bytes'] for x in m),'members':m,'canonical_integration_operational_reservation_provenance_native_OTA_GA_accepted':False}
 (H/'seal.json').write_text(json.dumps(s,indent=2,sort_keys=True)+'\n')
raw=(H/'seal.json').read_bytes();s=json.loads(raw);m=members()
assert s['members']==m and s['member_count']==len(m) and s['member_bytes']==sum(x['bytes'] for x in m)
print(json.dumps({'seal_sha256':sha(raw),'member_count':len(m),'member_bytes':s['member_bytes'],'exact_path_set':True}))
