#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,os
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (H/'owned-scratch').exists() and not (H/'seal.json').exists()
files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file()}
external=json.loads((H/'input-bindings.json').read_text());external['docs/swift-decode-plan-reuse-diagnosis.md']=sha(R/'docs/swift-decode-plan-reuse-diagnosis.md')
for n,v in external.items():assert sha(R/n)==v,(n,'drift before seal')
seal={'version':1,'scope':'finite isolated prototype diagnosis; not live acceptance','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'externalFiles':external}
(H/'seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
for p in H.rglob('*'):
 if p.is_file():p.chmod(0o444)
(R/'docs/swift-decode-plan-reuse-diagnosis.md').chmod(0o444)
for p in sorted((p for p in H.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):p.chmod(0o555)
H.chmod(0o555)
print(json.dumps({'sealedFiles':len(files),'sealSHA256':sha(H/'seal.json'),'readonly':True}))
