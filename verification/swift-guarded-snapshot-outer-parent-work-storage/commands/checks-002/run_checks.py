#!/usr/bin/env python3
"""Record bounded Python-only validation and retain every attempt."""
import datetime, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,a):p.write_text(json.dumps(a,indent=2,sort_keys=True)+'\n')
def main():
    number=1
    while (HERE/'commands'/('checks-'+str(number).zfill(3))).exists():number+=1
    out=HERE/'commands'/('checks-'+str(number).zfill(3));out.mkdir(parents=True)
    snapshots=[]
    for name in ['derive.py','model.py','test_model.py','run_checks.py']:
        data=(HERE/name).read_bytes();(out/name).write_bytes(data);snapshots.append({'path':name,'bytes':len(data),'sha256':sha(data)})
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
    commands=[[sys.executable,'-B',str(HERE/'derive.py'),'--check'],[sys.executable,'-B','-m','unittest','test_model','-v']]
    results=[]
    for index,argv in enumerate(commands):
        start=time.monotonic();completed=subprocess.run(argv,cwd=HERE,env=env,capture_output=True,timeout=60)
        for name,data in [('stdout',completed.stdout),('stderr',completed.stderr)]:(out/(str(index)+'-'+name)).write_bytes(data)
        results.append({'argv':argv,'cwd':str(HERE),'exit_code':completed.returncode,'elapsed_seconds':time.monotonic()-start,
            'stdout':{'bytes':len(completed.stdout),'sha256':sha(completed.stdout)},'stderr':{'bytes':len(completed.stderr),'sha256':sha(completed.stderr)}})
    passed=all(r['exit_code']==0 for r in results)
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python_version':sys.version,'python_executable':sys.executable,
        'platform':platform.platform(),'source_revision_from_root_acceptance':'a32d056355ec2f417e9ef7a73788b420176377b6','candidate_tree':'27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3',
        'source_snapshots':snapshots,'environment_delta':{'PYTHONDONTWRITEBYTECODE':'1'},'commands':results,'passed':passed,
        'scope':'Python-only exact source/data reproduction, typed arithmetic, immutable input omission/overflow controls and finite ownership-route controls; no compiler/native/product runtime',
        'cleanup':{'python_children_completed':True,'compiler_children_started':0,'native_UI_capture_started':False,'global_process_inventory':False,'scratch_created':False,'outside_owned_writes':False}}
    write(out/'receipt.json',receipt)
    write(HERE/'latest-checks.json',{'path':out.relative_to(HERE).as_posix()+'/receipt.json','sha256':sha((out/'receipt.json').read_bytes()),'passed':passed})
    print(json.dumps({'passed':passed,'attempt':number,'receipt':str(out/'receipt.json'),'commands':[r['exit_code'] for r in results]}))
    if not passed:sys.exit(1)
if __name__=='__main__':main()
