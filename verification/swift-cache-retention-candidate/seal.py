#!/usr/bin/env python3
"""Seal only this lane's finalized finite artifacts and report."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
ROOT=H.parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(not (H/n).exists() for n in ['baseline','candidate','owned-target','owned-tmp'])
members={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name not in ['seal.json','seal.sha256']}
external={'docs/swift-cache-retention-candidate.md':sha(ROOT/'docs/swift-cache-retention-candidate.md')}
seal={'schema':1,'sealedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'isolated finite Swift SLRU candidate; no live integration or actual-target execution selected','originalSourceRevision':'7b6048642b42e4900cccff4e14aa0fe8949ab35e','baselineClosureSHA256':'16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd','candidateManifestSHA256':sha(H/'candidate-manifest.json'),'members':members,'externalMembers':external}
(H/'seal.json').write_text(json.dumps(seal,indent=2,sort_keys=True)+'\n')
(H/'seal.sha256').write_text(sha(H/'seal.json')+'\n')
print(json.dumps({'members':len(members),'sealSHA256':sha(H/'seal.json'),'candidateManifestSHA256':sha(H/'candidate-manifest.json')}))
