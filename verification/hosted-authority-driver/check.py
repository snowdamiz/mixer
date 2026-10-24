#!/usr/bin/env python3
"""Fail closed on frozen driver evidence drift; does not run a provider or native gate."""
import hashlib,json,pathlib,sys,tarfile
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 manifest=json.loads((HERE/'artifact-manifest.json').read_text());verified=0
 for rel,expected in manifest['files'].items():
  p=ROOT/rel;assert p.is_file(),rel;assert sha(p.read_bytes())==expected,rel;verified+=1
 receipt=json.loads((HERE/'receipt.json').read_text());assert receipt['status']=='frozen-candidate-awaiting-independent-review-and-root-acceptance';assert receipt['live_integration_authorized'] is False and receipt['ga_acceptance'] is False
 for attempt in receipt['attempts']:
  out=HERE/attempt['run'];r=json.loads((out/'receipt.json').read_text());assert r['success']==attempt['success'];assert r['cleanup']['owned_cluster_stopped'] and r['cleanup']['owned_scratch_removed'];assert not r['cleanup']['other_processes_touched']
  for name,prefix in [('input-manifest.json','inputs'),('source-manifest.json','source')]:
   for item in json.loads((out/name).read_text()):
    b=(out/prefix/item['path']).read_bytes();assert sha(b)==item['sha256'] and len(b)==item['bytes'],str(out/item['path'])
  for command in json.loads((out/'commands.json').read_text()):
   assert sha((out/command['log']).read_bytes())==command['sha256']
  deps=json.loads((out/'dependency-manifest.json').read_text())
  with tarfile.open(out/'dependencies.tar.gz','r:gz') as archive:
   members={m.name:m for m in archive.getmembers()};assert len(members)==len(deps)
   for item in deps:
    b=archive.extractfile(members[item['path']]).read();assert sha(b)==item['sha256'] and len(b)==item['bytes']
 final=HERE/receipt['final_run'];r=json.loads((final/'receipt.json').read_text());assert r['success']
 tests=json.loads((final/'driver-tests.json').read_text());assert tests['total']==56 and tests['passed']==56 and all(t['passed'] for t in tests['results'])
 original=HERE/r['original_suite']['path'];summary=json.loads((original/'summary.json').read_text());assert summary['passed']==summary['total']==128;assert sha((original/'summary.json').read_bytes())==r['original_suite']['summary_sha256']
 assert sha((final/'source/schema.sql').read_bytes())=='d5883b47f308ffe9aa4ed55d3361aab313bf07421c41bffe13bba7b7f41cfd99'
 assert sha((final/'source/functions.sql').read_bytes())=='b70f9b1eb7d06f60a6ce3532d4d2fa51cd9afd564f10183a1d15a7ff36bbb11c'
 assert tests['observations']['actual_function_calls']==[['decide_current',1],['lock_admission_rows',2],['lookup_admission',6],['recheck_current',1]]
 assert int(tests['observations']['transport']['full_xid'])>2**32
 assert len(tests['observations']['five_waits'])==5 and all(x['wait_observed'] for x in tests['observations']['five_waits'])
 for p in (HERE/'probe').rglob('*'):
  if p.is_file():assert p.read_bytes()==(final/'source/probe'/p.relative_to(HERE/'probe')).read_bytes()
 print(json.dumps({'status':'passed','bindings_verified':verified,'driver_cases':56,'original_schema_cases_reused':128,'final_run':receipt['final_run'],'independent_review_pending':True}))
if __name__=='__main__':main()
