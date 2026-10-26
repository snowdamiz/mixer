#!/usr/bin/env python3
"""Keep failed-suite File bytes with original provenance using shared content."""
import json
from run_host import ROOT, REPO, sha
rows=[];store=ROOT/'evidence/content'
for attempt in ['frozen-attempt1','amended-attempt2']:
 evidence=ROOT/'evidence'/attempt
 for mode in ['debug','optimized']:
  receipt=evidence/f'tests-{mode}.json';run=json.loads(receipt.read_text());assert run['parent_exit_observed']and run['exit']==101
  for result in sorted((evidence/'public-cases'/mode).glob('*/result.txt')):
   case=result.parent;files=[]
   for name in ['input-0.bin','input-1.bin','input-2.bin','report.bin']:
    p=case/name;info=p.stat();assert run['started']<=info.st_mtime<=run['started']+run['elapsed'];digest=sha(p);target=store/(digest+'.bin')
    if target.exists():assert target.read_bytes()==p.read_bytes()
    else:target.write_bytes(p.read_bytes())
    assert sha(target)==digest
    files.append({'original_name':name,'bytes':info.st_size,'sha256':digest,'captured_mtime':info.st_mtime,'content_path':str(target.relative_to(REPO))});p.unlink()
   manifest={'case':str(case.relative_to(ROOT)),'files':files,'result_sha256':sha(result),'original_test_receipt':str(receipt.relative_to(ROOT)),'original_test_receipt_sha256':sha(receipt),'original_suite_exit':run['exit'],'failed_suite_not_reclassified_as_pass':True,'private_public_reachability_credit':0 if 'InternalPoisoned' in result.read_text()else None}
   (case/'files.json').write_text(json.dumps(manifest,indent=2)+'\n');rows.append({'manifest':str((case/'files.json').relative_to(ROOT)),'sha256':sha(case/'files.json')})
(ROOT/'proofs/failed-case-compaction.json').write_text(json.dumps({'schema':1,'cases':rows,'count':len(rows),'actual_bytes_preserved':True,'old_receipts_not_relabelled':True},indent=2)+'\n');print('FAILED_SUITE_CASES_PRESERVED',len(rows))
