#!/usr/bin/env python3
"""Freeze only this independent preaccess packet; no active candidate access."""
from pathlib import Path
import hashlib,json,datetime,re
D=Path(__file__).resolve().parent
assert not (D/'seal.json').exists(),'preaccess packet already immutable'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def mapping(p):return {str(q.relative_to(p)):ident(q) for q in sorted(p.rglob('*')) if q.is_file()}
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
product=mapping(D/'old-source/source');host={n:mapping(D/'old-source'/n) for n in ('source','host-leaves','tests')}
assert len(product)==16 and len(host['host-leaves'])==86 and len(host['tests'])==8
assert digest(product)=='cb5c2b813b9cb375f2907bafcb066ba9c556a2713ffd04c9d74777d9595d01e4'
assert digest(host)=='702f0f88869f88b591ce6c167cc6a8fbfb967ada697947831d77ddab8efc42c9'
assert ident(D/'controls/IndependentPreservationCompletionControls.java')['sha256']=='73c01e685e0eb768109535b85284c06e2abfa752b4443a9401f3d091ae2b2686'
run=D/'old-execution-sealed';receipt=json.loads((run/'receipt.json').read_text());commands=receipt['commands']
assert len(commands)==27 and all(c['reaped'] and not c['timed_out'] and c['timeout_seconds']==60 for c in commands)
assert receipt['cleanup']['owned_scratch_removed'] and not (run/'owned-scratch').exists()
for row in json.loads((run/'input-map.json').read_text()):assert ident(D/row['path'])=={k:row[k] for k in ('bytes','sha256')},row['path']
for row in commands:
 for suffix in ('stdout','stderr'):assert ident(run/(row['name']+'.'+suffix))==row[suffix]
assert next(c for c in commands if c['name']=='unchanged-PC-C16')['exit']==1
assert 'Ccounted=true Creleased=false Cregistered=true busy=false' in (run/'unchanged-PC-C16.stdout').read_text()
positive=[c for c in commands if (c['name'].startswith('unchanged-') and c['name']!='unchanged-PC-C16') or c['name']=='prepared-healthy']
assert len(positive)==8 and all(c['exit']==0 for c in positive)
assert len([c for c in commands if c['name'].startswith('prepared-') and c['name']!='prepared-healthy'])==15
assert next(c for c in commands if c['name']=='prepared-size-negative')['exit']==0
assert all(c['exit']==1 for c in commands if c['name'].startswith('prepared-') and c['name'] not in ('prepared-healthy','prepared-size-negative'))
assert 'refused=false' in (run/'prepared-captured-substitution.stdout').read_text()
assert all(not (D/name/'owned-scratch').exists() for name in ('old-execution','old-execution-final','old-execution-sealed'))
checks=[]
for c in commands:
 if c['name'].startswith(('unchanged-','prepared-')):
  outputs=(run/(c['name']+'.stdout')).read_text();matches=re.findall(r' / (\d+) assertions',outputs)
  checks.append({'command':c['name'],'old_source_exit':c['exit'],'observed_assertions':int(matches[-1]) if matches else None,'classification':'required unchanged historical failure' if c['name']=='unchanged-PC-C16' else ('passed baseline regression' if c in positive else 'prospective old-source diagnostic only'),'stdout':c['stdout'],'stderr':c['stderr'],'candidate_status':'pending-root-release'})
source={'schema':1,'product_source_map':product,'product_tree':digest(product),'host_tree':digest(host),'complete_source_counts':{k:len(v) for k,v in host.items()},'witness_class':ident(D/'controls/IndependentPreservationCompletionControls.java'),'new_control_class':ident(D/'controls/IndependentMembershipControls.java'),'final_run_input_map':ident(run/'input-map.json'),'all_compiled_sources_rebound':True}
save(D/'source-verification.json',source)
summary={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'preaccess-frozen-candidate-review-pending','scope':'Independently prepared finite selected Android constructor/captured-scope membership controls; old copied-source execution only','candidate_access':False,'candidate_acceptance':False,'admission':ident(D/'input-admission.json'),'old_product_tree':digest(product),'old_complete_host_tree':digest(host),'selected_run':'old-execution-sealed','selected_run_commands':len(commands),'selected_positive_groups':8,'selected_positive_observed_assertions':sum(c['observed_assertions'] or 0 for c in checks if c['classification']=='passed baseline regression'),'unchanged_PC_C16':'Reproduced unchanged expected failure: SUCCESS_DONE/shared0 while original C remains counted/registered and busy=false','prospective_cases':15,'prospective_old_source_passes':['size-negative'],'prospective_old_source_failures':14,'new_healthy_assertions':171,'controls':checks,'cleanup':receipt['cleanup'],'candidate_pending':['root explicit released seal and independent rehash/copy','complete frozen regression and unchanged FH witnesses','all prepared controls against exact final source','actual source/bytecode tails and custody review','fresh official SDK37 javac/D8 min-api28 on same bytes'],'limitations':['private hostile invariant; ordinary reachability/exploit not established','not arbitrary private corruption recovery','initial broader scope copier superseded before access; not promoted to finding','host controls do not establish Android runtime behavior','native/UI/capture/process inventories paused','canonical/source-pair/public V2/FieldLog/release/OTA/GA pending']}
save(D/'summary.json',summary)
entries=[{'path':str(p.relative_to(D)),**ident(p)} for p in sorted(D.rglob('*')) if p.is_file() and p.name not in ('manifest.json','seal.json')]
save(D/'manifest.json',{'schema':1,'scope':'Exact preaccess payload; manifest separately listed in seal','member_count':len(entries),'member_bytes':sum(r['bytes'] for r in entries),'members':entries})
entries.append({'path':'manifest.json',**ident(D/'manifest.json')});entries.sort(key=lambda r:r['path'])
seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':summary['status'],'scope':summary['scope'],'product_tree':digest(product),'manifest':ident(D/'manifest.json'),'member_count':len(entries),'member_bytes':sum(r['bytes'] for r in entries),'members':entries,'candidate_review_pending':True,'native_canonical_OTA_GA_accepted':False}
save(D/'seal.json',seal)
print(json.dumps({'seal':ident(D/'seal.json'),'member_count':seal['member_count'],'member_bytes':seal['member_bytes'],'status':seal['status'],'positive_groups':summary['selected_positive_groups'],'positive_observed_assertions':summary['selected_positive_observed_assertions']},indent=2))
