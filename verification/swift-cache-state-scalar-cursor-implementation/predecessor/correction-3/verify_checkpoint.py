#!/usr/bin/env python3
"""Read-only exact c3 closure/source/baseline verification, no test execution."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parent;REPO=ROOT.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
seal=ROOT/'candidate-repo-seal.json';j=json.loads(seal.read_text());seen=set()
for m in j['members']:
 p=REPO/m['path'];assert p.is_relative_to(ROOT)and not p.is_symlink()and m['path']not in seen
 seen.add(m['path']);assert p.stat().st_size==m['bytes']and sha(p)==m['sha256']
assert seen=={str(p.relative_to(REPO))for p in ROOT.rglob('*')if p.is_file()and p!=seal}
assert len(seen)==j['member_count']and sum(m['bytes']for m in j['members'])==j['member_bytes']
assert hashlib.sha256(json.dumps(j['source_rows'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==j['source_tree_digest']
for row in j['source_rows']:
 p=ROOT/row['path'];assert p.stat().st_size==row['bytes']and sha(p)==row['sha256']
for old in j['preserved_packets']:
 p=REPO/old['seal'];assert sha(p)==old['sha256']
 for m in json.loads(p.read_text())['members']:
  q=REPO/m['path'];assert q.stat().st_size==m['bytes']and sha(q)==m['sha256']
print(json.dumps({'seal_sha256':sha(seal),'member_count_verified':len(seen),'member_bytes_verified':j['member_bytes'],'source_tree_digest':j['source_tree_digest'],'all_baseline_members_unchanged':True,'complete_work_or_lifetime_acceptance':False},indent=2))
