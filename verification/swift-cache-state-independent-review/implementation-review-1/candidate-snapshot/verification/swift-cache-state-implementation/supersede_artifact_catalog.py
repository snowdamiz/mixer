#!/usr/bin/env python3
"""Preserve v1 exactly; bind final-run versus preliminary raw File evidence."""
import datetime,hashlib,json,pathlib,re,sys
ROOT=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v1=ROOT/'seal.json';before=sha(v1);old=json.loads(v1.read_text());out=ROOT/'candidate-v2-seal.json';assert not out.exists()
for m in old['members']:
 p=ROOT/m['path'];assert p.stat().st_size==m['bytes']and sha(p)==m['sha256']
validation=json.loads((ROOT/'evidence/final-validation.json').read_text());catalog=json.loads((ROOT/'evidence/case-catalog.json').read_text());rows=[];summary={}
for mode in ['debug','optimized']:
 run=json.loads((ROOT/'evidence'/f'tests-{mode}.json').read_text());start=run['started'];end=start+run['elapsed'];counts={'final_public_four_File':0,'final_private_injected_fault':0,'preliminary_zero_final_credit':0}
 for case in catalog['cases']:
  if '/'+mode+'/' not in case['case']:continue
  raw=(ROOT/case['case']/'result.txt').read_text();match=re.search(r'input_stamps_before_and_after=\[Stamp \{ fields: \[([^\]]+)',raw);fields=[int(v.strip())for v in match[1].split(',')];stamp=fields[4]+fields[5]/1e9;fresh=start<=stamp<=end
  effective=('final_private_injected_fault' if case['scope']=='private-injected-fault'else'final_public_four_File')if fresh else'preliminary_zero_final_credit';counts[effective]+=1
  rows.append({'case':case['case'],'original_catalog_scope':case['scope'],'effective_scope':effective,'input_mtime_utc':datetime.datetime.fromtimestamp(stamp,datetime.timezone.utc).isoformat(),'input_mtime_epoch':stamp,'final_command_started':start,'final_command_ended':end,'result_sha256':case['result_sha256'],'raw_files_unchanged':True,'final_source_sha256':validation['source_sha256']if fresh else None,'preliminary_source_not_recovered':not fresh,'final_run_credit':fresh})
 assert counts=={'final_public_four_File':29,'final_private_injected_fault':2,'preliminary_zero_final_credit':2},counts
 summary[mode]=counts
receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,str(pathlib.Path(__file__).resolve())],'python':sys.version,'script_sha256':sha(pathlib.Path(__file__)),'status':'artifact-classification-correction-only; source-and-all-v1-member-bytes-unchanged','previous_seal_sha256':before,'previous_members_verified':len(old['members']),'classification':'A raw input stamp must lie within its final source-bound host command interval. The two deliberately injected poison cases per mode stay private. case-025/026 predate the final run and receive zero final-source/run credit. All bytes remain preserved.','counts':summary,'cases':rows,'method_counts_unchanged':{'new':22,'old_producer':78,'old_independent':14,'unique_per_mode':114},'independent_accepted':False,'native_runtime_or_capture_started':False,'GA_qualified':False}
(ROOT/'evidence/final-case-classification.json').write_text(json.dumps(receipt,indent=2)+'\n')
handoff=json.loads((ROOT/'handoff.json').read_text());handoff.update({'status':'superseding immutable producer candidate v2; root admission and independent acceptance pending','previous_seal_sha256':before,'artifact_correction':'evidence/final-case-classification.json','final_actual_File_counts_per_mode':summary,'preliminary_raw_case_source_or_pass_credit':False,'all_v1_bytes_preserved':True})
(ROOT/'handoff-v2.json').write_text(json.dumps(handoff,indent=2)+'\n')
members=[]
for p in sorted(ROOT.rglob('*')):
 if p.is_file():members.append({'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
seal={k:v for k,v in old.items()if k not in ['members','member_count','member_bytes','at','excluded','status']};seal.update({'schema':2,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'superseding-frozen-producer-v2-artifact-classification-corrected-awaiting-independent-review','excluded':['candidate-v2-seal.json'],'previous_seal_sha256':before,'members':members,'member_count':len(members),'member_bytes':sum(m['bytes']for m in members),'effective_case_evidence':'evidence/final-case-classification.json','root_implementation_accepted':False,'independent_accepted':False})
out.write_text(json.dumps(seal,indent=2)+'\n')
assert sha(v1)==before
for m in members:
 p=ROOT/m['path'];assert p.stat().st_size==m['bytes']and sha(p)==m['sha256']
assert {str(p.relative_to(ROOT))for p in ROOT.rglob('*')if p.is_file()}=={m['path']for m in members}|{'candidate-v2-seal.json'}
print(json.dumps({'seal':str(out),'sha256':sha(out),'members':len(members),'bytes':seal['member_bytes'],'source_tree_digest':seal['source_tree_digest'],'library_sha256':seal['library_sha256'],'final_actual_File_counts_per_mode':summary,'previous_v1_bytes_unchanged':True},indent=2))
