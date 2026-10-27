#!/usr/bin/env python3
"""Record bounded one-shot pure-host review/test commands, never compiler/runtime."""
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
from prepare import HERE,ROOT,sha,write

def main():
    assert len(sys.argv)==2
    name=sys.argv[1]
    options={'mir-layout-review':['review.py','--derive'], 'mir-layout-review-final':['review.py','--derive'], 'source-and-evidence-tests':['test_model.py']}
    assert name in options
    out=HERE/'commands'/name; assert not out.exists(), 'Preserve every attempt'
    out.mkdir(parents=True)
    argv=[sys.executable,'-B',str(HERE/options[name][0])]+options[name][1:]
    env=dict(PATH='/usr/bin:/bin',PYTHONDONTWRITEBYTECODE='1')
    receipt=dict(schema=1,argv=argv,environment=env,cwd=str(ROOT),python_version=sys.version,
        python_sha256=sha(Path(sys.executable).read_bytes()),source_revision=json.loads((HERE/'positive-compiler-plan.json').read_bytes())['source_revision'],
        candidate_tree_sha256=json.loads((HERE/'source-manifest.json').read_bytes())['tree_sha256'],
        script_sha256=sha((HERE/options[name][0]).read_bytes()),started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        compiler_invocations=0,product_test_native_runtime=False,retries=0)
    write(out/'plan.json',receipt)
    started=time.monotonic(); child=None
    try:
        with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
            child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
            receipt.update(owned_pid=child.pid,owned_pgid=child.pid,timed_out=False)
            try: child.wait(timeout=55)
            except subprocess.TimeoutExpired:
                receipt['timed_out']=True;os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
            receipt.update(exit_code=child.returncode,elapsed_seconds=time.monotonic()-started,child_reaped=child.poll() is not None)
    finally:
        if child is not None:
            if child.poll() is None: os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
            try:os.killpg(child.pid,0);receipt['owned_group_absent']=False
            except ProcessLookupError:receipt['owned_group_absent']=True
        for stream in ['stdout','stderr']:
            data=(out/stream).read_bytes();receipt[stream+'_bytes']=len(data);receipt[stream+'_sha256']=sha(data)
        write(out/'receipt.json',receipt)
    print(json.dumps(dict(name=name,exit_code=receipt['exit_code'],elapsed_seconds=receipt['elapsed_seconds'],child_reaped=receipt['child_reaped'],owned_group_absent=receipt['owned_group_absent'])))
    if receipt['exit_code']!=0 or not receipt['owned_group_absent']:sys.exit(1)

if __name__=='__main__':main()
