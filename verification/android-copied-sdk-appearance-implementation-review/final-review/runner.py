from pathlib import Path
import os,signal,subprocess,time,json,hashlib
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def run(label,argv,cwd=None,env=None,timeout=120,allowed=(0,)):
    folder=HERE/'commands'/label
    if folder.exists():raise RuntimeError('refuse duplicate command '+label)
    folder.mkdir(parents=True)
    record={'argv':[str(a) for a in argv],'cwd':str(cwd or HERE),'timeout_seconds':timeout,'at':datetime.now(timezone.utc).isoformat(),'env_overrides':env or {}}
    (folder/'command.json').write_text(json.dumps(record,indent=2)+'\n')
    start=time.monotonic();timed_out=False
    with (folder/'stdout').open('wb') as out,(folder/'stderr').open('wb') as err:
        proc=subprocess.Popen(record['argv'],cwd=cwd or HERE,env=os.environ|dict(env or {}),stdout=out,stderr=err,start_new_session=True)
        try:code=proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(proc.pid,signal.SIGTERM)
            try:code=proc.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait(timeout=5)
    stdout=(folder/'stdout').read_bytes();stderr=(folder/'stderr').read_bytes()
    result=record|{'exit_code':code,'timed_out':timed_out,'elapsed_seconds':round(time.monotonic()-start,3),'stdout':identity(stdout),'stderr':identity(stderr),'owned_process_reaped':True}
    (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    if timed_out or code not in allowed:raise RuntimeError(f'{label}: exit {code}; see {folder}')
    print(json.dumps({'command':label,'exit_code':code,'seconds':result['elapsed_seconds']}),flush=True)
    return stdout.decode(errors='replace')+stderr.decode(errors='replace')
