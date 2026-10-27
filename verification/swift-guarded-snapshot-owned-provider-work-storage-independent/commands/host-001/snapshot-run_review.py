"""Bounded owned pure-host children. Never executes a compiler or product."""
from pathlib import Path
import datetime, hashlib, json, os, signal, subprocess, sys, time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    assert not (HERE/'seal.json').exists(),'review packet already immutable'
    dest=HERE/'commands'/('host-'+str(len(list((HERE/'commands').glob('host-*')))+1).zfill(3));dest.mkdir(parents=True)
    scripts={p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in HERE.glob('*.py')}
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();begin=time.monotonic();commands=[]
    candidate=ROOT/'verification/swift-guarded-snapshot-owned-provider-work-storage'
    roster=[([sys.executable,'-B',str(candidate/'check_packet.py')],candidate),([sys.executable,'-B',str(HERE/'independent.py')],HERE)]
    if (HERE/'test_independent.py').exists():roster.append(([sys.executable,'-B','-m','unittest','-v','test_independent'],HERE))
    for index,(argv,cwd) in enumerate(roster):
        out=dest/(str(index)+'-stdout');err=dest/(str(index)+'-stderr');t=time.monotonic();timeout=False;cleanup=[]
        environment={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
        with out.open('wb') as stdout,err.open('wb') as stderr:
            child=subprocess.Popen(argv,cwd=cwd,env=environment,stdout=stdout,stderr=stderr,start_new_session=True)
            try:child.wait(timeout=55)
            except subprocess.TimeoutExpired:
                timeout=True;os.killpg(child.pid,signal.SIGKILL);cleanup.append('SIGKILL-owned-group');child.wait(timeout=5)
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        commands.append({'argv':argv,'cwd':str(cwd),'environment':environment,'pid':child.pid,'pgid':child.pid,'limit_seconds':55,'elapsed_seconds':time.monotonic()-t,'exit_code':child.returncode,'timed_out':timeout,'child_reaped':True,'owned_group_absent':absent,'cleanup_signals':cleanup,'stdout':{'path':str(out.relative_to(HERE)),'bytes':out.stat().st_size,'sha256':sha(out.read_bytes())},'stderr':{'path':str(err.relative_to(HERE)),'bytes':err.stat().st_size,'sha256':sha(err.read_bytes())}})
        if child.returncode or timeout or not absent:break
    unchanged=all((HERE/name).stat().st_size==r['bytes'] and sha((HERE/name).read_bytes())==r['sha256'] for name,r in scripts.items())
    receipt={'schema':1,'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-begin,'python':sys.version,'python_executable':sys.executable,'python_executable_sha256':sha(Path(sys.executable).read_bytes()),'scripts':scripts,'scripts_unchanged':unchanged,'source_revision':'b20cd3bcd83f9110fbbc62ce60a265373f2a85e5 from retained plan; no Git query','source_tree_sha256':'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d','commands':commands,'success':unchanged and len(commands)==len(roster) and all(c['exit_code']==0 and not c['timed_out'] and c['owned_group_absent'] for c in commands),'scope':'owned pure-host Python source/MIR/LLVM review, read-only producer checker; no compiler/product/native/UI/capture/global inventory','new_compiler_invocations':0,'new_product_or_native_invocations':0,'cleanup':'All owned Python children synchronously reaped; owned groups checked individually only. No scratch or native instances created.'}
    (dest/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'receipt':str((dest/'receipt.json').relative_to(HERE)),'success':receipt['success'],'elapsed_seconds':receipt['elapsed_seconds']}))
    if not receipt['success']:
        print(err.read_text()[-5000:]);return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
