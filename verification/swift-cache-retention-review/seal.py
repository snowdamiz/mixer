#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;ROOT=H.parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(not(H/n).exists()for n in ['owned-source','owned-target','owned-tmp'])
assert not(H/'seal.json').exists()
members={str(p.relative_to(H)):sha(p)for p in sorted(H.rglob('*'))if p.is_file()and p.name not in ['seal.json','seal.sha256']}
seal={'schema':1,'sealedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'members':members,'externalMembers':{'docs/swift-cache-retention-review.md':sha(ROOT/'docs/swift-cache-retention-review.md')}}
(H/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n');(H/'seal.sha256').write_text(sha(H/'seal.json')+'\n')
print(json.dumps({'sealSHA256':sha(H/'seal.json'),'members':len(members),'externalMembers':1,'sealedUTC':seal['sealedUTC']}))
