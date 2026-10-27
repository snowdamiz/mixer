#!/usr/bin/env python3
"""Bounded pure Python runner; only the independent packet is writable."""
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
R=D.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    name=sys.argv[1];argv=sys.argv[2:];folder=D/'commands'/name
    folder.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=R,capture_output=True,text=True,check=True).stdout.strip()
    for path in (Path(__file__),D/'audit.py'):
        if path.exists():(folder/path.name).write_bytes(path.read_bytes())
    error=None;timed_out=False;output=b'';stderr=b''
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
    with (folder/'stdout').open('wb') as out,(folder/'stderr').open('wb') as err:
        p=subprocess.Popen(argv,cwd=R,env=env,stdout=out,stderr=err,start_new_session=True)
        try:exit_code=p.wait(timeout=60)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(p.pid,signal.SIGKILL);exit_code=p.wait()
    try:os.killpg(p.pid,0);absent=False
    except ProcessLookupError:absent=True
    for stream in ('stdout','stderr'):
        b=(folder/stream).read_bytes()
        if len(b)>4*1024*1024:error='output-limit-exceeded'
    receipt={'schema':1,'at':stamp,'argv':argv,'cwd':str(R),'python_version':sys.version,'python_executable':sys.executable,'python_executable_sha256':sha(Path(sys.executable).read_bytes()),'source_revision_at_command':head,'source146_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','runner_sha256':sha(Path(__file__).read_bytes()),'command_source_sha256':sha(Path(argv[2]).read_bytes()) if len(argv)>2 and Path(argv[2]).is_file() else None,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':60,'timed_out':timed_out,'exit_code':exit_code,'expectation_met':exit_code==0 and not timed_out and error is None,'owned_group':p.pid,'child_reaped':True,'owned_group_absent':absent,'global_process_inventory':False,'compiler_product_native_UI_capture_started':False,'environment_explicit':{'PYTHONDONTWRITEBYTECODE':'1'},'output_limit_error':error,'streams':{n:{'bytes':len((folder/n).read_bytes()),'sha256':sha((folder/n).read_bytes())} for n in ('stdout','stderr')}}
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'command':name,'exit_code':exit_code,'expectation_met':receipt['expectation_met'],'owned_group_absent':absent,'elapsed_seconds':receipt['elapsed_seconds']},sort_keys=True))
    raise SystemExit(0 if receipt['expectation_met'] else 1)
if __name__=='__main__':main()
