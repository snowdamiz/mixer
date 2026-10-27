#!/usr/bin/env python3
import datetime,hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def main():
 assert not(HERE/'seal.json').exists()
 commands=[]
 for name,argv in [('tests',[sys.executable,'-B','test_delegated_raw.py']),('python-version',[sys.executable,'--version']),('source-head',['git','rev-parse','HEAD'])]:
  start=time.monotonic();r=subprocess.run(argv,cwd=HERE,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=45)
  out=HERE/(name+'.stdout');err=HERE/(name+'.stderr');out.write_bytes(r.stdout);err.write_bytes(r.stderr)
  commands.append({'name':name,'argv':argv,'exit':r.returncode,'elapsed_seconds':round(time.monotonic()-start,6),'timeout_seconds':45,'child_reaped':True,'stdout':ident(out),'stderr':ident(err)})
  assert r.returncode==0,name
 from test_delegated_raw import review
 from delegated_raw import load_policy,POLICY_SHA256
 result=review();(HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n');policy=load_policy()
 receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'narrow raw delegated join tested; root-selection-pending','api':'validate_delegated_raw(raw_row)','module':ident(HERE/'delegated_raw.py'),'policy_sha256':POLICY_SHA256,'mandatory_corrected_dependency':policy['mandatory_corrected_dependency'],'product_context':policy['product_context'],'source_map_sha256':policy['source_map_sha256'],'class_map_sha256':policy['class_map_sha256'],'exact_selected_frames':7,'authored_states':13,'offline_actual_positive_rows':26,'original_coherent_refusal_controls':9,'unittest_count':13,'commands':commands,'python':sys.version,'platform':platform.platform(),'source_revision_context':(HERE/'source-head.stdout').read_text().strip(),'native_UI_capture_process_inventory_started':False,'helper_body_state_authority_full_matrix_execution_closure_native_OTA_GA':'pending','qualified':False}
 (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 assert all(p.is_file()for p in HERE.iterdir()),'no caches or unmanifested directories'
 members=[{'path':p.name,**ident(p)}for p in sorted(HERE.iterdir())if p.is_file()]
 seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'frozen narrow exact delegated raw join; root-selection-pending','api':'validate_delegated_raw(raw_row)','members':members,'member_count':len(members),'member_bytes':sum(x['bytes']for x in members),'module':ident(HERE/'delegated_raw.py'),'policy':ident(HERE/'policy.json'),'mandatory_corrected_dependency':policy['mandatory_corrected_dependency'],'qualified':False}
 (HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
 print(json.dumps({'seal':ident(HERE/'seal.json'),'module':ident(HERE/'delegated_raw.py'),'policy':ident(HERE/'policy.json'),'members':len(members),'member_bytes':seal['member_bytes'],'tests':13,'actual_rows':26,'original_controls':9,'qualified':False}))
if __name__=='__main__':main()
