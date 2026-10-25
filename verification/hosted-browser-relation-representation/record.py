#!/usr/bin/env python3
"""Audit exact completed fixture bindings and index the two final attempts."""
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
FINAL={17:'20261025T182923.920254Z-pg17-271d6c',16:'20261025T182929.207298Z-pg16-96ab1e'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v): p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
results={}
for major,name in FINAL.items():
 p=BASE/'attempts'/name;r=json.loads((p/'receipt.json').read_text())
 assert r['success'] and r['semantic_methods_passed']==82 and r['mutations_detected']==(24 if major==17 else 23)
 assert r['automatic_rename_equivalent'] and r['rewritten_fast_defaults_absent'] and r['rewrite_equivalent'] and r['rollback_restored_baseline']
 assert all(r['cleanup'].values()) and not r['source_changes_during_run'] and not r['dependency_changes_during_run']
 for rel,h in r['outputs_sha256'].items(): assert sha(p/rel)==h,(name,rel)
 bindings=json.loads((p/'source-bindings.json').read_text())
 for rel,h in bindings.items(): assert sha(p/'inputs'/rel)==h,(name,'input',rel)
 for rel,h in json.loads((p/'dependency-beams.json').read_text()).items(): assert sha(ROOT/rel)==h,(name,'dependency',rel)
 results[str(major)]={'attempt':str(p.relative_to(ROOT)),'receipt_sha256':sha(p/'receipt.json'),'frozen_expectation_sha256':r['frozen_expectation_sha256'],'source_tree_sha256':r['source_tree_sha256'],'dependency_tree_sha256':r['dependency_tree_sha256'],'environment':r['environment'],'counts':r['counts'],'semantic_checks_passed':82,'mutation_controls_detected':r['mutations_detected'],'cleanup':r['cleanup']}
a=json.loads((BASE/'attempts'/FINAL[17]/'frozen-expectation.json').read_text());b=json.loads((BASE/'attempts'/FINAL[16]/'frozen-expectation.json').read_text())
a['acl']=[r for r in a['acl'] if r['privilege_type']!='MAINTAIN']
for r in a['relations']+b['relations']: r.pop('raw_acl')
for r in a['table_effective']:r.pop('maintain')
assert a==b
historical=[]
for p in sorted((BASE/'attempts').iterdir()):
 if p.name not in FINAL.values():
  r=json.loads((p/'receipt.json').read_text());historical.append({'attempt':str(p.relative_to(ROOT)),'success':r['success'],'failure':r.get('failure'),'receipt_sha256':sha(p/'receipt.json'),'cleanup':r['cleanup']})
receipt={'schema':1,'scope':'Bounded ordinary source representation qualification only; no product RelationCatalog, owner/Store/readiness or GA acceptance.','passed':True,'final_attempts':results,'cross_major_equivalent_except_owner_maintain':True,'historical_attempts':historical,'artifacts_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'docs/hosted-browser-relation-representation.md',BASE/'qualify.py',BASE/'install.exs',BASE/'snapshot.sql',BASE/'record.py']},'delivery':{'committed':False,'pushed':False,'coordinator':'root'},'pending':['Independent packet review','RelationCatalog bounded implementation and adversity tests','Trusted Store/Repo/original deadline composition','Lifecycle readiness and provider/HTTP/console/Neon/operator qualification','Native/UI/capture/physical checks paused','Customer/FieldLog immutable packages and GA']}
write(BASE/'receipt.json',receipt)
print(json.dumps({'passed':True,'source_tree':results['17']['source_tree_sha256'],'receipt_sha256':sha(BASE/'receipt.json'),'historical_attempts_retained':len(historical)}))
