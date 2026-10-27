#!/usr/bin/env python3
"""Own-group bounded Python-only command custody; never launches Rust or products."""
from pathlib import Path
import datetime, hashlib, json, os, signal, subprocess, sys, time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def row(p):
    b=p.read_bytes(); return {'path':str(p.relative_to(ROOT)), 'bytes':len(b), 'sha256':sha(b)}
def custody():
    lock=HERE/'input-lock.json'
    if not lock.exists(): return []
    roster=json.loads(lock.read_bytes())['files']
    out=[]
    for item in roster:
        p=ROOT/item['path']; actual=row(p)
        if actual!=item: raise ValueError('input custody drift: '+str(p))
        out.append(actual)
    return out
def main():
    label=sys.argv[1]; tail=sys.argv[2:]
    if not label.replace('-','').isalnum(): raise ValueError('simple label required')
    if not tail or tail[0] not in ('fetch.py','derive.py','test_interfaces.py','check_packet.py'): raise ValueError('Python host script allowlist')
    dest=HERE/'commands'/label; dest.mkdir(parents=True,exist_ok=False)
    before=custody()
    argv=[sys.executable,'-B',str(HERE/tail[0]),*tail[1:]]
    env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','LC_ALL':'C','LANG':'C'}
    code={str(p.relative_to(HERE)):row(p) for p in HERE.glob('*.py')}
    for p in HERE.glob('*.py'): (dest/p.name).write_bytes(p.read_bytes())
    started=datetime.datetime.now(datetime.timezone.utc).isoformat(); begin=time.monotonic()
    child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timed_out=False
    try: stdout,stderr=child.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out=True; os.killpg(child.pid,signal.SIGKILL); stdout,stderr=child.communicate(timeout=2)
    try: os.killpg(child.pid,0); absent=False
    except ProcessLookupError: absent=True
    (dest/'stdout').write_bytes(stdout); (dest/'stderr').write_bytes(stderr)
    after=custody()
    receipt={'schema':1,'started':started,'elapsed_seconds':time.monotonic()-begin,'argv':argv,'cwd':str(ROOT),'environment':env,'python_version':sys.version,'python_executable':str(Path(sys.executable).resolve()),'python_sha256':sha(Path(sys.executable).resolve().read_bytes()),'source_scripts':code,'input_membership_before':before,'input_membership_after':after,'input_custody_unchanged':before==after,'exit_code':child.returncode,'timed_out':timed_out,'timeout_seconds':55,'owned_group_pid':child.pid,'owned_group_absent':absent,'child_reaped':child.poll() is not None,'stdout':row(dest/'stdout'),'stderr':row(dest/'stderr'),'compiler_invocations':0,'Rust_or_product_runtime_invocations':0,'native_UI_capture_or_global_inventory':False,'scratch_created':False}
    (dest/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'command':label,'exit_code':child.returncode,'elapsed_seconds':receipt['elapsed_seconds'],'input_members':len(before),'owned_group_absent':absent,'stdout':stdout.decode(errors='replace')[:3000],'stderr':stderr.decode(errors='replace')[-6000:]}))
    preparation=tail==['derive.py','--prepare'] and not before
    if child.returncode or timed_out or not absent or (before!=after and not preparation): raise SystemExit(1)
if __name__=='__main__': main()
