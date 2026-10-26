#!/usr/bin/env python3
"""Read-only exact-member verifier; no compiler/tests/contained imports."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=ROOT/'seal.json';s=json.loads(p.read_text())
for m in s['members']:
 q=REPO/m['path'];assert q.stat().st_size==m['bytes']and sha(q)==m['sha256']
assert {str(q.relative_to(REPO))for q in ROOT.rglob('*')if q.is_file()}=={m['path']for m in s['members']}|{str(p.relative_to(REPO))}
for path,h in s['target_source_sha256'].items():assert sha(REPO/path)==h
print(json.dumps({'seal_sha256':sha(p),'members':len(s['members']),'bytes':s['member_bytes'],'verified':True,'source_accounting_acceptance':False},indent=2))
