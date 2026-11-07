#!/usr/bin/env python3
"""Read-only hash and closure verification; no network or Rust execution."""
import hashlib,json,pathlib
root=pathlib.Path(__file__).resolve().parent;repo=root.parents[1]
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=root/'seal.json';j=json.loads(s.read_text());seen=set()
for m in j['members']:
 p=repo/m['path'];assert p.is_relative_to(root)and not p.is_symlink()
 assert m['path']not in seen;seen.add(m['path'])
 assert p.stat().st_size==m['bytes']and digest(p)==m['sha256']
assert {str(p.relative_to(repo))for p in root.rglob('*')if p.is_file()and p!=s}==seen
assert len(seen)==j['member_count']and sum(m['bytes']for m in j['members'])==j['member_bytes']
b=json.loads((root/'custody.json').read_text())
assert digest(repo/b['target_source']['path'])==b['target_source']['sha256']
for old in b['verified_old_packets']:
 p=repo/old['path'];assert digest(p)==old['sha256']
 for m in json.loads(p.read_text())['members']:
  q=repo/m['path'];assert q.stat().st_size==m['bytes']and digest(q)==m['sha256']
print(json.dumps({'seal_sha256':digest(s),'members_verified':len(seen),
 'member_bytes_verified':j['member_bytes'],'all_bound_old_members_verified':True,
 'source_accounting_accepted':False,'lifetime_proof_accepted':False},indent=2))
