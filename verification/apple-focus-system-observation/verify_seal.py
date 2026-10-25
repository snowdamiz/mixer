#!/usr/bin/env python3
"""Read-only sealed handoff verifier; never dispatches compiler or native work."""
import hashlib,json,pathlib,stat,tarfile
H=pathlib.Path(__file__).resolve().parent
ROOT=H.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=(H/'handoff.json').read_bytes();assert sha(raw)==(H/'handoff.sha256').read_text().strip()
v=json.loads(raw)
for name,item in v['members'].items():
 p=ROOT/name;assert p.is_file() and not p.is_symlink(),name
 b=p.read_bytes();assert len(b)==item['bytes'] and sha(b)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']==0o444,name
manifest=json.loads((H/'review-source-package-manifest.json').read_bytes())
with tarfile.open(H/'review-source-package.tar.gz') as t:
 members=t.getmembers();assert len(members)==40 and all(m.isfile() for m in members)
 assert {m.name for m in members}==set(manifest['members'])
 for m in members:
  b=t.extractfile(m).read();e=manifest['members'][m.name]
  assert sha(b)==e['sha256'] and len(b)==e['bytes'] and m.mode==e['mode']==0o444
  assert b==(H/'candidate'/m.name).read_bytes()
assert not (H/'.owned-typecheck').exists() and not list(H.rglob('__pycache__'))
print(json.dumps({'schema':1,'verifiedMembers':len(v['members']),'handoffSHA256':sha(raw),'sourceArchiveSHA256':sha((H/'review-source-package.tar.gz').read_bytes()),'candidateMembers':40,'nativeAccepted':False,'gaAccepted':False,'scope':'Read-only seal verification'},sort_keys=True))
