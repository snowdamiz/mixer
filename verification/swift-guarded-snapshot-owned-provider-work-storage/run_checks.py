#!/usr/bin/env python3
"""Record bounded pure-host checks, with exact scripts and failure preservation."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys, time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,obj):path.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
def main():
    assert not (HERE/'seal.json').exists(),'immutable packet'
    prior=list((HERE/'commands').glob('host-checks-*'));dest=HERE/'commands'/('host-checks-'+str(len(prior)+1).zfill(3));dest.mkdir()
    scripts={}
    for name in ('derive.py','model.py','test_model.py','run_checks.py'):
        data=(HERE/name).read_bytes();(dest/name).write_bytes(data);scripts[name]={'bytes':len(data),'sha256':sha(data)}
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();begin=time.monotonic();commands=[]
    for index,argv in enumerate(([sys.executable,'-B','derive.py'],[sys.executable,'-B','-m','unittest','-v','test_model.py'],[sys.executable,'-B','derive.py','--check'])):
        out=dest/(str(index)+'-stdout');err=dest/(str(index)+'-stderr');started=time.monotonic()
        env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
        with out.open('wb') as stdout,err.open('wb') as stderr:
            try:
                process=subprocess.run(argv,cwd=HERE,env=env,stdout=stdout,stderr=stderr,timeout=55)
                code=process.returncode;error=None
            except subprocess.TimeoutExpired as exc:code=None;error=str(exc)
        commands.append({'argv':argv,'cwd':str(HERE),'environment':env,'exit_code':code,'exception':error,'elapsed_seconds':time.monotonic()-started,'stdout':{'bytes':out.stat().st_size,'sha256':sha(out.read_bytes())},'stderr':{'bytes':err.stat().st_size,'sha256':sha(err.read_bytes())}})
        if code!=0:break
    unchanged=all(sha((HERE/name).read_bytes())==data['sha256'] for name,data in scripts.items())
    receipt={'schema':1,'scope':'pure-host Python source/MIR/accounting tests only; no compiler/runtime/native/acquisition/UI/capture invocation','python_version':sys.version,'python_executable':sys.executable,'python_executable_sha256':sha(Path(sys.executable).read_bytes()),'candidate_source_tree':'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d','started_at':start,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-begin,'scripts':scripts,'scripts_unchanged':unchanged,'commands':commands,'success':unchanged and len(commands)==3 and all(c['exit_code']==0 for c in commands),'native_or_capture_processes_started':False,'compiler_invocations':0,'cleanup':'host children synchronously waited; no scratch created; no global process inventory'}
    write(dest/'receipt.json',receipt);write(HERE/'latest-checks.json',{'path':str((dest/'receipt.json').relative_to(HERE)),'sha256':sha((dest/'receipt.json').read_bytes()),'success':receipt['success']})
    print(json.dumps({'path':str(dest.relative_to(HERE)),'success':receipt['success'],'commands':len(commands),'elapsed_seconds':receipt['elapsed_seconds']}))
    return 0 if receipt['success'] else 1
if __name__=='__main__':raise SystemExit(main())
