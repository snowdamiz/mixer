"""Seal and verify this review's exact files. No producer program or runtime."""
from pathlib import Path
import hashlib,json,sys
P=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
members=[{'path':str(p.relative_to(P)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(P.rglob('*')) if p.is_file() and p.name!='seal.json']
seal={'schema':1,'member_count':len(members),'member_bytes':sum(r['bytes'] for r in members),'members':members,'tree_sha256':sha(canonical(members)),'scope':'independent conditional additive delta only; no owner-base or full-floor acceptance'}
if sys.argv[1:] == ['--verify']:
 assert json.loads((P/'seal.json').read_text())==seal
 print(json.dumps({'verified_members':len(members),'verified_bytes':seal['member_bytes'],'seal_sha256':sha((P/'seal.json').read_bytes())}))
elif not sys.argv[1:]:
 assert not (P/'seal.json').exists()
 (P/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'sealed_members':len(members),'sealed_bytes':seal['member_bytes'],'seal_sha256':sha((P/'seal.json').read_bytes())}))
else:raise ValueError('expected no argument or --verify')
