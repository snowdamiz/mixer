#!/usr/bin/env python3
"""Install only the four independently reviewed additive audit component files."""
import datetime,hashlib,json,os,pathlib,shutil,subprocess
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 commands=[]
 def run(label,argv,cwd=ROOT):
  start=datetime.datetime.now(datetime.timezone.utc).isoformat()
  p=subprocess.run(argv,cwd=cwd,env={**os.environ,'ERL_FLAGS':'+S 2:2','MIX_ENV':'test','HEX_OFFLINE':'1'},capture_output=True)
  data=p.stdout+p.stderr;path=HERE/(label+'.log');path.write_bytes(data)
  commands.append({'label':label,'argv':argv,'cwd':str(cwd),'startedUTC':start,'exitCode':p.returncode,'log':path.name,'sha256':sha(path)})
  assert p.returncode==0,(label,p.returncode)
  return data
 status='failed';applied=[]
 try:
  for label,packet in [('original-check','hosted-audit-codec-integration'),('original-review-check','hosted-audit-codec-review'),('correction-check','hosted-audit-key-bound-correction'),('correction-review-check','hosted-audit-key-bound-review')]:
   run(label,['python3','-B',str(ROOT/'verification'/packet/'check.py')])
  correction=ROOT/'verification/hosted-audit-key-bound-correction';review=ROOT/'verification/hosted-audit-key-bound-review'
  cr=json.loads((correction/'receipt.json').read_text());rr=json.loads((review/'receipt.json').read_text());pre=json.loads((HERE/'preintegration.json').read_text())
  assert rr['status']=='passed-independent-correction-review' and not rr['findings']
  assert sha(correction/'receipt.json')==rr['frozenCorrectionReceiptSHA256']
  assert sha(review/'receipt.json')=='aea43009b21e18e02f86c77d265f69f6a553db0d41485c41faca2dd6dab526fa'
  manifest=json.loads((HERE/'preintegration-source.json').read_text())
  source=json.loads((correction/'run-1/receipt.json').read_text())
  for p,digest in source['baselineInputs'].items():assert sha(ROOT/p)==digest,p
  for p,digest in cr['overlay'].items():
   src=correction/'candidate'/p;dst=ROOT/'hosted'/p
   assert sha(src)==digest and not dst.exists(),p
  for p,digest in cr['overlay'].items():
   dst=ROOT/'hosted'/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(correction/'candidate'/p,dst);applied.append('hosted/'+p)
  for p,digest in manifest.items():assert sha(ROOT/p)==digest,p
  run('elixir-version',['elixir','--version']);run('mix-version',['mix','--version']);run('git-version',['git','--version']);run('host-version',['uname','-a'])
  run('integrated-format',['mix','format','--check-formatted'],ROOT/'hosted')
  run('integrated-focused',['mix','test','test/mixer_hosted/audit/upload_event_test.exs','--warnings-as-errors','--seed','0','--trace'],ROOT/'hosted')
  for p,digest in manifest.items():assert sha(ROOT/p)==digest,p
  assert 'Result: 12 passed' in (HERE/'integrated-focused.log').read_text()
  status='passed-integrated-focused-and-source-identity'
 finally:
  receipt={'schema':1,'status':status,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'appliedFiles':applied,'commands':commands,'sourceManifest':locals().get('manifest'),'environment':{'MIX_ENV':'test','HEX_OFFLINE':'1','ERL_FLAGS':'+S 2:2'},'scope':'Direct checkout pure audit integration; existing105fullhosted/2explicitLinuxskips/release reused with exact tested source. No SQL, HTTP, provider, UI, physical or GA acceptance.'}
  (HERE/'integration.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'status':status,'appliedFiles':applied}))
if __name__=='__main__':main()
