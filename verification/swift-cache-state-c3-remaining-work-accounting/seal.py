#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def members():
 rows=[]
 for p in sorted(HERE.rglob('*')):
  if p.is_file() and p.name!='seal.json':
   b=p.read_bytes();rows.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha(b)})
 return rows
if sys.argv[1:]==['--verify']:
 j=json.loads((HERE/'seal.json').read_text())
 if j['members']!=members():raise ValueError('sealed packet drift')
 print(json.dumps({'verified':True,'members':len(j['members']),'bytes':sum(r['bytes'] for r in j['members']),'seal_sha256':sha((HERE/'seal.json').read_bytes())}))
elif not sys.argv[1:]:
 rows=members();j={'schema':1,'status':'unselected conservative source-covering proposal; independent completeness review and root selection pending','members':rows,'bytes':sum(r['bytes'] for r in rows),'source_sha256':'0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8','native_and_runtime_tests_executed':False,'release_or_GA_acceptance':False}
 (HERE/'seal.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps({'members':len(rows),'bytes':j['bytes'],'seal_sha256':sha((HERE/'seal.json').read_bytes())}))
else:raise ValueError('only --verify or no arguments')
