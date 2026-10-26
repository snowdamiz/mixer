#!/usr/bin/env python3
"""Retain actual File bytes once by content hash, with fresh case provenance."""
import json,pathlib,shutil
from run_host import ROOT,REPO,sha
store=ROOT/'evidence/content';store.mkdir(exist_ok=True);rows=[]
for mode in ['debug','optimized']:
 run=ROOT/f'evidence/tests-{mode}.json';j=json.loads(run.read_text())
 assert j['parent_exit_observed']and j['exit']==0 and j['failure']is None
 for case in sorted((ROOT/'evidence/public-cases'/mode).glob('case-*')):
  result=(case/'result.txt').read_text();private='boundary: InternalPoisoned, reason: InternalPoison'in result
  assert private==(case.name in ['case-031','case-032'])
  manifest={'case':str(case.relative_to(ROOT)),'scope':'private_injected_poison'if private else'public_actual_four_File','files':[],'fresh_test_receipt':str(run.relative_to(ROOT)),'fresh_test_receipt_sha256':sha(run),'test_command_interval':[j['started'],j['started']+j['elapsed']],'actual_executed_artifacts':j['owned_input_artifacts'],'private_public_reachability_credit':0 if private else None,'result_sha256':sha(case/'result.txt')}
  for name in ['input-0.bin','input-1.bin','input-2.bin','report.bin']:
   p=case/name;info=p.stat();assert j['started']<=info.st_mtime<=j['started']+j['elapsed']
   h=sha(p);target=store/(h+'.bin')
   if target.exists():assert target.read_bytes()==p.read_bytes()
   else:target.write_bytes(p.read_bytes())
   assert sha(target)==h
   manifest['files'].append({'original_name':name,'bytes':info.st_size,'sha256':h,'captured_mtime':info.st_mtime,'content_path':str(target.relative_to(REPO))})
   p.unlink();assert not p.exists()
  if private:
   dest=ROOT/'evidence/private-fault-cases'/mode/case.name;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();shutil.move(case,dest);case=dest;manifest['case']=str(case.relative_to(ROOT))
  (case/'files.json').write_text(json.dumps(manifest,indent=2)+'\n');rows.append({'case':manifest['case'],'scope':manifest['scope'],'manifest_sha256':sha(case/'files.json')})
assert len(rows)==62
(ROOT/'evidence/compaction.json').write_text(json.dumps({'schema':1,'cases':rows,'case_count':62,'unique_content_files':len(list(store.glob('*.bin'))),'all_actual_bytes_retained':True,'removed_only_duplicate_named_raw_copies_after_hash_check':True,'freshness_bound_to_actual_child_start_end':True,'public_per_mode':29,'private_per_mode':2},indent=2)+'\n')
print(json.dumps({'cases':62,'unique_content_files':len(list(store.glob('*.bin'))),'actual_bytes_preserved':True}))
