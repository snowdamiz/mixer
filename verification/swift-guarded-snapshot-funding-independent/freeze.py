#!/usr/bin/env python3
"""Freeze this independent packet only, without modifying any input."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
assert not (HERE/'owned-work').exists()
review=json.loads((HERE/'review.json').read_text())
assert review['controls_passed']==79 and not review['complete_floor_or_work_or_writer_release_accepted']
members=[]
for p in sorted(HERE.rglob('*')):
 if p.is_file() and p.name!='seal.json':
  assert '__pycache__' not in p.parts
  b=p.read_bytes()
  members.append({'path':p.relative_to(HERE).as_posix(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
seal={'schema':1,'scope':'Independent bounded constants-only source integration evidence; A/H lifetimes and complete funding/writer/GA release remain pending','source_tree_sha256':review['candidate_source_tree_sha256'],'member_count':len(members),'total_bytes':sum(r['bytes'] for r in members),'members_tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'members':members}
path=HERE/'seal.json';path.write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'members':len(members),'bytes':seal['total_bytes'],'seal_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}))
