#!/usr/bin/env python3
import subprocess,hashlib,json,datetime,os,re
from pathlib import Path
out=Path(__file__).resolve().parent
root=out.parents[1]
env=dict(os.environ)
env['PATH']='/opt/homebrew/opt/rustup/bin:'+env['PATH']
env['CARGO_TARGET_DIR']=str(out/'target')
logs=out/'logs';logs.mkdir(exist_ok=True)
commands=json.loads((out/'commands.json').read_text()) if (out/'commands.json').exists() else []
def run(name,args,require_pass=True):
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    proc=subprocess.run(args,cwd=out/'tree/vm',env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    data=proc.stdout.encode();p=logs/(name+'.log');p.write_bytes(data)
    counts=re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out',proc.stdout)
    item={'name':name,'argv':args,'cwd':'tree/vm','started_utc':started,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':proc.returncode,'output':'logs/'+p.name,'output_sha256':hashlib.sha256(data).hexdigest(),'test_results':counts}
    commands.append(item);(out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    print(json.dumps({'name':name,'exit_code':proc.returncode,'test_results':counts}),flush=True)
    if require_pass and proc.returncode: print(proc.stdout[-6000:],flush=True);raise SystemExit(proc.returncode)
run('rustc-version',['rustc','-Vv'])
run('cargo-version',['cargo','-V'])
run('python-version',['python3','--version'])
for label,features in [('minimal','experimental-swift-reactor'),('combined','experimental-swift-reactor,experimental-span-execution')]:
    for profile in ['debug','release']:
        release=[] if profile=='debug' else ['--release']
        run(label+'-'+profile+'-independent',['cargo','test','--locked','--offline','--lib','--features',features,*release,'independent_construction_review_','--','--nocapture','--test-threads=1'])
        run(label+'-'+profile+'-producer',['cargo','test','--locked','--offline','--lib','--features',features,*release,'swift_construction_','--','--nocapture','--test-threads=1'])
        run(label+'-'+profile+'-layout',['cargo','test','--locked','--offline','--lib','--features',features,*release,'swift_executor_layout_','--','--nocapture','--test-threads=1'])
        run(label+'-'+profile+'-production-layout',['cargo','run','--locked','--offline','--features',features,*release,'--example','independent-construction-layout'])
