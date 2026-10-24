#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,datetime
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
enc=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda x:hashlib.sha256(x).hexdigest()
r=json.loads((H/'receipt.json').read_text());clean=json.loads((H/'cleanup.json').read_text());assert clean['ownedScratchRemoved']and clean['holderCheckEmpty']
for name in ['cleanup.json','helper-repair-notes.json','complete-owned-type-layout-replay.json']:r['bindings'][name]=sha((H/name).read_bytes())
r['cleanup']=clean;(H/'receipt.json').write_bytes(enc(r))
files={str(p.relative_to(H)):sha(p.read_bytes())for p in sorted(H.rglob('*'))if p.is_file()and p.name!='seal.json'}
seal={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'sealed-isolated-producer-not-integrated','files':files,'externalBindings':{'docs/swift-cleanup-diagnostic-implementation.md':sha((ROOT/'docs/swift-cleanup-diagnostic-implementation.md').read_bytes())}}
(H/'seal.json').write_bytes(enc(seal));print('sealed',len(files),'files')
