#!/usr/bin/env python3
"""Seal an observed successful run without converting an unresolved gate to a pass."""
import datetime,hashlib,json,pathlib,sys
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 final=HERE/sys.argv[1];r=json.loads((final/'receipt.json').read_text());assert r['success']
 tests=json.loads((final/'driver-tests.json').read_text());assert tests['passed']==tests['total']==56
 attempts=[]
 for p in sorted(HERE.glob('run-*/receipt.json'),key=lambda p:int(p.parent.name.split('-')[1])):
  a=json.loads(p.read_text());attempts.append({'run':p.parent.name,'success':a['success'],'source_digest':a['source_digest'],'driver_tests':a.get('driver_tests'),'error':a.get('error'),'cleanup':a['cleanup']})
 receipt={'schema':1,'status':'frozen-candidate-awaiting-independent-review-and-root-acceptance','frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':r['scope'],'final_run':final.name,'source_digest':r['source_digest'],'dependency_digest':r['dependency_digest'],'source_revision':r['baseline_revision'] or r['revision'],'driver_tests':{'passed':56,'total':56},'original_schema_suite':r['original_suite'],'live_integration_authorized':False,'ga_acceptance':False,'attempts':attempts,'cleanup':{'all_owned_clusters_stopped':all(a['cleanup']['owned_cluster_stopped'] for a in attempts),'all_owned_scratch_removed':all(a['cleanup']['owned_scratch_removed'] for a in attempts),'tcp_listener_opened':False,'other_projects_touched':False,'native_runs':False},'pending':['Fresh independent review and root acceptance','Separate corrected catalog/startup schema selection','Combined domain RLS and fixed writer integration','Configured provider and authenticated HTTP/cancellation','Artifact metadata lookup and credential/management lifecycle','Neon/Cloudflare/R2/Oban/operations','Published FieldLog, physical-phone final matrix and all accountable GA gates']}
 (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 files={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in ['artifact-manifest.json','check-output.log'] and '__pycache__' not in p.parts}
 p=ROOT/'docs/hosted-authority-driver.md';files[str(p.relative_to(ROOT))]=sha(p.read_bytes())
 (HERE/'artifact-manifest.json').write_text(json.dumps({'schema':1,'files':files},indent=2,sort_keys=True)+'\n');print(json.dumps({'final_run':final.name,'bindings':len(files),'source_digest':r['source_digest']}))
if __name__=='__main__':main()
