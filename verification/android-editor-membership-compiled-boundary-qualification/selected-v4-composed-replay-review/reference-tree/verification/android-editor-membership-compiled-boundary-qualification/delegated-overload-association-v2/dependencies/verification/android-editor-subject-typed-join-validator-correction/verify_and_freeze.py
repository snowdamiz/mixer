#!/usr/bin/env python3
import datetime,hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def main():
 assert not (HERE/'seal.json').exists()
 commands=[]
 for name,argv in [('retained-tests',[sys.executable,'-B','test_typed_join.py']),('correction-tests',[sys.executable,'-B','test_corrections.py']),('python-version',[sys.executable,'--version']),('source-head',['git','rev-parse','HEAD'])]:
  start=time.monotonic();r=subprocess.run(argv,cwd=HERE,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=45)
  stdout=HERE/(name+'.stdout');stderr=HERE/(name+'.stderr');stdout.write_bytes(r.stdout);stderr.write_bytes(r.stderr)
  commands.append({'name':name,'argv':argv,'exit':r.returncode,'elapsed_seconds':round(time.monotonic()-start,6),'timeout_seconds':45,'child_reaped':True,'stdout':ident(stdout),'stderr':ident(stderr)})
  assert r.returncode==0,name
 base=HERE.parent/'android-editor-subject-typed-join-validator'
 assert ident(base/'seal.json')['sha256']=='fed4e7f14c82d1f17b69a4ef2a6809e34edfba0adc67b5c773944e809b839c5d'
 assert ident(HERE/'policy.json')==ident(base/'policy.json')
 assert ident(HERE/'test_typed_join.py')==ident(base/'test_typed_join.py')
 receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'strict typed-join corrections tested; root-selection-pending','base_seal_sha256':ident(base/'seal.json')['sha256'],'policy':ident(HERE/'policy.json'),'corrected_module':ident(HERE/'typed_join.py'),'exact_root_findings':ident(HERE/'root-findings.json'),'retained_original_tests':42,'new_correction_tests':15,'total_tests':57,'commands':commands,'python':sys.version,'platform':platform.platform(),'source_revision_context':(HERE/'source-head.stdout').read_text().strip(),'native_UI_capture_process_inventory_started':False,'full_matrix_execution_closure_native_OTA_GA':'pending','qualified':False}
 (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 members=[{'path':p.name,**ident(p)} for p in sorted(HERE.iterdir()) if p.is_file()]
 assert all(p.is_file() for p in HERE.iterdir()),'no caches or unmanifested directories'
 seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen corrected strict host validator; root-selection-pending','members':members,'member_count':len(members),'member_bytes':sum(x['bytes']for x in members),'total_host_tests':57,'qualified':False}
 (HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
 print(json.dumps({'seal':ident(HERE/'seal.json'),'module':ident(HERE/'typed_join.py'),'policy':ident(HERE/'policy.json'),'tests':57,'qualified':False}))
if __name__=='__main__':main()
