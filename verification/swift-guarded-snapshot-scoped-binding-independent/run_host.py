#!/usr/bin/env python3
"""Bounded exact-owned-group recorder for read-only Python evidence review."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
def present(pid):
    try:os.killpg(pid,0);return True
    except ProcessLookupError:return False

def main():
    name=sys.argv[1];script=Path(sys.argv[2]).resolve();args=sys.argv[3:]
    assert name.replace('-','').isalnum()
    assert (script==HERE/'audit.py' and args==['--derive']) or (script==ROOT/'verification/swift-guarded-snapshot-scoped-binding-source/check.py' and args==['--read-only'])
    out=HERE/'commands'/name;assert not out.exists();out.mkdir(parents=True)
    plan=dict(schema=1,argv=[sys.executable,'-B',str(script),*args],cwd=str(ROOT),
        environment=dict(PATH='/usr/bin:/bin',PYTHONDONTWRITEBYTECODE='1'),
        python_version=sys.version,python_sha256=sha(Path(sys.executable).read_bytes()),
        script_sha256=sha(script.read_bytes()),source_revision='975b2e3ef25255a882e7476780caa2e844ce928d',
        source_revision_scope='frozen origin provenance, no live Git query',
        candidate_source_tree_sha256='69068367d2eaf334d6881a624cac9142a0b4ecfeed50f23382724ae29e51d5e7',
        candidate_seal_sha256='84a9bf52a127f5fcebd5d6db3dedb9c0e65fc9ef9cfd57b432c8e1f65f8e5ed2',
        compiler_invocations=0,product_test_native_runtime=False,timeout_seconds=55,retries=0,
        started_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write(out/'plan.json',plan);r=dict(plan);child=None;start=time.monotonic()
    try:
        with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
            child=subprocess.Popen(plan['argv'],cwd=ROOT,env=plan['environment'],stdout=stdout,stderr=stderr,start_new_session=True)
            r.update(owned_pid=child.pid,owned_pgid=child.pid,timed_out=False)
            try:child.wait(timeout=55)
            except subprocess.TimeoutExpired:
                r['timed_out']=True;os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
            r.update(exit_code=child.returncode,elapsed_seconds=time.monotonic()-start,child_reaped=child.poll() is not None)
    except BaseException as error:r['recorder_error']=repr(error)
    finally:
        if child is not None:
            if child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
            if present(child.pid):os.killpg(child.pid,signal.SIGKILL)
            r['owned_group_absent']=not present(child.pid)
        for n in ('stdout','stderr'):
            b=(out/n).read_bytes();r[n+'_bytes']=len(b);r[n+'_sha256']=sha(b)
        r.update(state='complete',finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),owned_scratch_created=False,global_process_inventory=False)
        write(out/'receipt.json',r)
    print(json.dumps({k:r.get(k) for k in ('exit_code','elapsed_seconds','timed_out','child_reaped','owned_group_absent','recorder_error','stdout_bytes','stderr_bytes')}))
    if r.get('exit_code')!=0 or not r.get('owned_group_absent') or r.get('recorder_error'):sys.exit(1)
if __name__=='__main__':main()
