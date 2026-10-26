#!/usr/bin/env python3
"""Read-only finite packet custody check; runs no predecessor or host code."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent;seal=ROOT/'seal.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads(seal.read_text());seen=set()
for row in d['members']:
 p=ROOT/row['path']
 if p.is_symlink()or not p.is_relative_to(ROOT)or row['path']in seen:raise ValueError('invalid member')
 seen.add(row['path'])
 if p.stat().st_size!=row['bytes']or sha(p)!=row['sha256']:raise ValueError('changed member '+row['path'])
actual={str(p.relative_to(ROOT))for p in ROOT.rglob('*')if p.is_file()and p!=seal}
if seen!=actual or len(seen)!=d['member_count']or sum(r['bytes']for r in d['members'])!=d['total_bytes']:raise ValueError('closure mismatch')
print(json.dumps({'seal_sha256':sha(seal),'members_verified':len(seen),'bytes_verified':d['total_bytes'],'source_sha256':d['source_sha256'],'source_tree_digest':d['source_tree_digest'],'independent_implementation_review_pending':not d['independent_implementation_accepted']},indent=2))
