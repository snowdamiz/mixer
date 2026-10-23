#!/usr/bin/env python3
"""Compare exported native inventory with original baseline, no guest run."""
import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
baseline=json.loads((HERE/'legacy-parity-receipt.json').read_text());OLD=Path(baseline['baseline_directory'])
ENV=dict(os.environ);ENV['PATH']='/opt/homebrew/opt/rustup/bin:'+ENV.get('PATH','')
def run(args,cwd=ROOT,env=ENV):
 p=subprocess.run(args,cwd=cwd,env=env,text=True,capture_output=True)
 return dict(argv=args,cwd=str(cwd),exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,CARGO_TARGET_DIR=env.get('CARGO_TARGET_DIR'))
r={'scope':'host native export/header inventory; no Swift or target execution','commands':[],'headers':{}}
for p in sorted((ROOT/'vm/include').glob('*.h')):
 q=OLD/'vm/include'/p.name;assert p.read_bytes()==q.read_bytes()
 r['headers'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
inventories=[]
for cwd,target in [(OLD,str(OLD/'vm/target')),(ROOT,'/tmp/mixer-cache-surface-current')]:
 env=dict(ENV);env['CARGO_TARGET_DIR']=target
 build=run(['cargo','build','--locked','--manifest-path','vm/Cargo.toml','--lib','--all-features'],cwd,env);r['commands'].append(build);assert build['exit_code']==0
 binary=Path(target)/'debug/libmixer_vm.dylib'
 n=run(['nm','-gU',str(binary)],cwd,env);r['commands'].append(n);assert n['exit_code']==0
 names=sorted(line.split()[-1]for line in n['stdout'].splitlines()if line.split()and line.split()[-1].startswith('_mixer_'))
 assert names;inventories.append(names)
assert inventories[0]==inventories[1]
r['original_exports']=inventories[0];r['current_exports']=inventories[1];r['status']='pass'
(HERE/'surface-receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':'pass','exports':len(inventories[0]),'headers':r['headers']},indent=2))
