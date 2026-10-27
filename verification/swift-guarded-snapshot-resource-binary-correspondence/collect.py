"""One-shot read-only installed-archive collection; no compiler or product runtime."""
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

D = Path(__file__).resolve().parent
R = D.parents[1]
TOOLDIR = Path('/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin')
LIBDIR = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/lib/rustlib/aarch64-apple-darwin/lib')
LIBS = dict(std=LIBDIR/'libstd-614bb9b33bbc23af.rlib', core=LIBDIR/'libcore-adfbfa4d4eb69204.rlib', alloc=LIBDIR/'liballoc-d519ed569a95083f.rlib')

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def put(name,x): (D/name).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def info(p):
    b=p.read_bytes()
    return dict(path=str(p),bytes=len(b),sha256=sha(b),resolved_path=str(p.resolve()))

def run(label,argv,seconds=30):
    assert not (D/(label+'-receipt.json')).exists(), 'Never replay a collection command.'
    env=dict(PATH='/usr/bin:/bin', LC_ALL='C')
    started=time.monotonic();p=subprocess.Popen(argv,cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timeout=False;actions=[]
    try: out,err=p.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        timeout=True;os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL-owned-timeout-group');out,err=p.communicate()
    try: os.killpg(p.pid,0);present=True
    except ProcessLookupError: present=False
    if present:
        os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL-owned-residual-group')
        for _ in range(20):
            try: os.killpg(p.pid,0);time.sleep(.05)
            except ProcessLookupError: present=False;break
    for kind,b in [('stdout',out),('stderr',err)]: (D/(label+'.'+kind+'.gz')).write_bytes(gzip.compress(b,mtime=0))
    put(label+'-receipt.json',dict(argv=argv,environment=env,cwd=str(R),timeout_seconds=seconds,timed_out=timeout,exit_code=p.returncode,direct_child_pid=p.pid,direct_child_waited=True,owned_group_absent=not present,cleanup_actions=actions,elapsed_seconds=time.monotonic()-started,outputs={k:dict(bytes=len(b),sha256=sha(b),archive=label+'.'+k+'.gz') for k,b in [('stdout',out),('stderr',err)]},global_process_inventory=False,compiler_or_product_runtime=False))
    assert not timeout and not present
    return out,err,p.returncode

def main():
    assert not (D/'installed-inputs.json').exists()
    put('installed-inputs.json',dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),target='aarch64-apple-darwin',archives={k:info(p) for k,p in LIBS.items()},tools={k:info(TOOLDIR/k) for k in ('nm','llvm-objdump')},source_commit_is_binary_proof=False))
    for tool in ('nm','llvm-objdump'):
        assert run('find-'+tool,['/usr/bin/xcrun','--find',tool])[2]==0
        run('version-'+tool,[str(TOOLDIR/tool),'--version'])
    for name,p in LIBS.items():
        assert run('nm-'+name,[str(TOOLDIR/'nm'),'-A',str(p)])[2]==0
    print(json.dumps(dict(status='collected',archives=3,runtime=False)))

if __name__=='__main__': main()
