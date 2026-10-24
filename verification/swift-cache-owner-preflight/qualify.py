#!/usr/bin/env python3
from pathlib import Path
import subprocess,os,json,hashlib,datetime,time
ROOT=Path(__file__).resolve().parent
ENV=dict(os.environ);ENV['PATH']='/opt/homebrew/opt/rustup/bin:'+ENV['PATH'];ENV['CARGO_TARGET_DIR']=str(ROOT/'build')
commands=[['rustc','-Vv'],['cargo','-V']]
for features in ['experimental-swift-reactor','experimental-swift-reactor,experimental-span-execution']:
 for release in [False,True]:
  commands.append(['cargo','test','--manifest-path',str(ROOT/'inputs/vm/Cargo.toml'),'--features',features,'--lib',*(['--release'] if release else []),'cache_tests::','--','--nocapture'])
 commands.append(['cargo','clippy','--manifest-path',str(ROOT/'inputs/vm/Cargo.toml'),'--features',features,'--lib','--','-D','warnings'])
rows=[]
for i,cmd in enumerate(commands):
 start=time.monotonic();p=subprocess.run(cmd,cwd=ROOT,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 name=f'{i:02d}.log';(ROOT/name).write_bytes(p.stdout)
 rows.append({'command':cmd,'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-start,'log':name,'sha256':hashlib.sha256(p.stdout).hexdigest()})
 print(i,p.returncode,cmd[:2],flush=True)
 if p.returncode:break
inputs=json.loads((ROOT/'inputs.json').read_text())
for e in inputs['inputs']:assert hashlib.sha256((ROOT/'inputs'/e['path']).read_bytes()).hexdigest()==e['sha256']
(ROOT/'receipt.json').write_text(json.dumps({'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'passed' if len(rows)==len(commands) and all(x['exit_code']==0 for x in rows) else 'failed','base':inputs['base'],'source_manifest_sha256':hashlib.sha256((ROOT/'inputs.json').read_bytes()).hexdigest(),'commands':rows,'scope':'Root borrow-only cache owner seam; construction caller accounting remains separately pending. No interpreter, target instantiation, physical or GA acceptance.'},indent=2)+'\n')
