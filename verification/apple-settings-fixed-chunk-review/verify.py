#!/usr/bin/env python3
"""Read-only sealed review verification; writes only its unsealed result."""
import hashlib,json,pathlib,stat
B=pathlib.Path(__file__).resolve().parent;ROOT=B.parents[1]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
handoff=json.loads((B/'handoff.json').read_bytes())
actual=sha((B/'handoff.json').read_bytes());assert actual==(B/'handoff.sha256').read_text().strip()
for name,row in handoff['members'].items():
    path=ROOT/name;assert stat.S_ISREG(path.lstat().st_mode),name
    raw=path.read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],name
p=ROOT/'verification/apple-settings-fixed-chunk-implementation'
assert sha((p/'handoff.json').read_bytes())==handoff['producerHandoffSHA256']
for name,row in json.loads((p/'handoff.json').read_bytes())['members'].items():
    path=ROOT/name;assert stat.S_ISREG(path.lstat().st_mode) and sha(path.read_bytes())==row['sha256'],name
assert not any((B/n).exists() for n in ['owned-host','owned-typecheck','synthetic-attempts'])
result=dict(passed=True,reviewHandoffSHA256=actual,reviewMembers=len(handoff['members']),producerMembers=176,producerUnchanged=True,ownedScratchAbsent=True,nativeAccepted=False,gaAccepted=False)
(B/'verification-result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,sort_keys=True))
