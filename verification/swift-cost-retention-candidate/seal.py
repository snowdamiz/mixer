#!/usr/bin/env python3
"""Seal retained producer artifacts after cleanup; exclude this mutable seal."""
import hashlib,json,pathlib
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
assert json.loads((OUT/'cleanup.json').read_text())['removed'] and not (OUT/'.scratch').exists()
members={}
for path in sorted(OUT.rglob('*')):
 if path.is_file() and path.name not in ['seal.json','seal.sha256']:
  data=path.read_bytes();members[str(path.relative_to(OUT))]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
seal={'schema':1,'decision':'root-rejected-no-full-target-no-live-integration','members':members,'docSHA256':hashlib.sha256((ROOT/'docs/swift-cost-retention-candidate.md').read_bytes()).hexdigest()}
data=(json.dumps(seal,indent=2,sort_keys=True)+'\n').encode();(OUT/'seal.json').write_bytes(data)
digest=hashlib.sha256(data).hexdigest();(OUT/'seal.sha256').write_text(digest+'\n')
print(json.dumps({'sealSHA256':digest,'memberCount':len(members),'docBound':True}))
