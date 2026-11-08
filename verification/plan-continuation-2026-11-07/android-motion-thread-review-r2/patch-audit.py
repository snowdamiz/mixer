import datetime, hashlib, json, shutil, subprocess, sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
PARENT=OUT.parents[2]
CAND=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-7764d3ec')
R1=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-9ff4db6c')
E=CAND/'verification/plan-continuation-2026-11-07/android-motion-thread-fix-r2'
BASE='e7254f3703d5b8191aa72ec2fb11fa91b5ea99ba'
def ident(p):
    b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
mapping=json.loads((E/'final-source-map.json').read_text())
records=[]
def run(args,cwd):
    p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=10)
    records.append({'argv':args,'cwd':str(cwd),'exit':p.returncode,'stdoutBytes':len(p.stdout),'stdoutSHA256':hashlib.sha256(p.stdout).hexdigest(),'stderr':p.stderr.decode()})
    if p.returncode:raise RuntimeError(p.stderr.decode())
    return p.stdout
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'gitVersion':run(['git','--version'],PARENT).decode().strip(),'replays':[]}
scratch=OUT/'patch-scratch';scratch.mkdir()
try:
    for label,patch in [('base-e725','implementation.patch'),('frozen-r1','incremental-r1-r2.patch')]:
        target=scratch/label;target.mkdir();run(['git','init','--quiet'],target)
        for path in mapping:
            data=run(['git','show',BASE+':'+path],PARENT) if label=='base-e725' else (R1/path).read_bytes()
            f=target/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data)
        run(['git','apply','--check',str(E/patch)],target)
        run(['git','apply',str(E/patch)],target)
        for path,expected in mapping.items():
            if ident(target/path)!=expected:raise RuntimeError('replay mismatch '+path)
        result['replays'].append({'baseline':label,'patch':patch,'identity':ident(E/patch),'exactFinalFiles':len(mapping)})
finally:
    shutil.rmtree(scratch);result['ownedScratchRemoved']=not scratch.exists()
    (OUT/'patch-commands.json').write_text(json.dumps(records,indent=2)+'\n')
    (OUT/'patch-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS both patches independently reproduce all 15 final file identities')
