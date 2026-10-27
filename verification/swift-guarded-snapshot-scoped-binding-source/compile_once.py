#!/usr/bin/env python3
"""Two predeclared one-shot compiler-only queries; no runtime or retries."""
import datetime
import gzip
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from prepare import HERE, ROOT, INDEPENDENT, PROFILE, ACCOUNT, sha, manifest, write, query_source

RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
COMPILER_SHA='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'

def context(mode):
    base=json.loads((HERE/'source-manifest.json').read_bytes())
    source={x['path']:(HERE/'source/vm'/x['path']).read_bytes() for x in base['members']}
    assert manifest(source)==base
    source=query_source(source,mode)
    query=manifest(source)
    assert query==json.loads((HERE/(mode+'-source-manifest.json')).read_bytes())
    frozen=json.loads((INDEPENDENT/'compiler-plan.json').read_bytes())
    assert sha(RUSTC.read_bytes())==frozen['compiler_sha256']==COMPILER_SHA
    work=HERE/'owned-work'/mode
    argv=list(frozen['argv'])
    argv=[str(work/'vm/src/lib.rs') if x.endswith('/vm/src/lib.rs') else x for x in argv]
    argv=[('--emit=metadata='+str(work/'query.rmeta')+(',mir='+str(work/'query.mir') if mode=='positive' else '')) if x.startswith('--emit=') else x for x in argv]
    env=dict(frozen['environment'], CARGO_MANIFEST_DIR=str(work/'vm'),TMPDIR=str(work))
    plan=dict(schema=1,mode=mode,argv=argv,environment=env,cwd=str(ROOT),
        compiler_path=str(RUSTC),compiler_sha256=COMPILER_SHA,
        compiler_version_preimage=frozen['compiler_version_preimage'],
        compiler_version_sha256=frozen['compiler_version_sha256'],
        compiler_version_scope='Frozen exact-byte-bound -vV, no new compiler/version process',
        candidate_tree_sha256=base['tree_sha256'],query_tree_sha256=query['tree_sha256'],
        source_members=146,source_revision=frozen['source_revision'],python_version=sys.version,
        runner_sha256=sha(Path(__file__).read_bytes()),child_timeout_seconds=55,
        exact_owned_process_group_cleanup=True,output_limit_bytes=4194304,
        cfg_test=False,codegen=False,product_test_native_runtime=False,retries=0,
        expected='exit 0 and full MIR' if mode=='positive' else 'exit nonzero; E0515 twice, E0506, E0505, E0382',
        no_compile_identity_injection=True,compiler_invocations_authorized=1)
    return source,query,plan,work

def group_present(pid):
    try: os.killpg(pid,0); return True
    except ProcessLookupError: return False

def run(mode):
    source,query,plan,work=context(mode)
    assert json.loads((HERE/(mode+'-compiler-plan.json')).read_bytes())==plan
    out=HERE/'commands'/('compiler-'+mode)
    assert not out.exists() and not work.exists(), 'One shot; no replacement or retry'
    out.mkdir(parents=True); work.mkdir(parents=True)
    for name,data in source.items():
        p=work/'vm'/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data)
    receipt=dict(plan,state='starting',started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        compiler_invocations=0,owned_pid=None,owned_pgid=None,exit_code=None,timed_out=None,
        elapsed_seconds=None,child_reaped=False,owned_group_absent=None,owned_scratch_removed=False,artifacts=[])
    write(out/'receipt.json',receipt)
    child=None; started=time.monotonic()
    try:
        with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
            child=subprocess.Popen(plan['argv'],cwd=ROOT,env=plan['environment'],stdout=stdout,stderr=stderr,start_new_session=True)
            receipt.update(state='running',owned_pid=child.pid,owned_pgid=child.pid,compiler_invocations=1,timed_out=False)
            write(out/'receipt.json',receipt)
            try: child.wait(timeout=55)
            except subprocess.TimeoutExpired:
                receipt['timed_out']=True; os.killpg(child.pid,signal.SIGKILL); child.wait(timeout=5)
            receipt.update(state='terminal',exit_code=child.returncode,elapsed_seconds=time.monotonic()-started,child_reaped=child.poll() is not None)
            write(out/'receipt.json',receipt)
        for name in ['stdout','stderr']:
            data=(out/name).read_bytes(); receipt[name+'_bytes']=len(data); receipt[name+'_sha256']=sha(data)
        for name in ['query.rmeta','query.mir']:
            p=work/name
            if p.exists(): receipt['artifacts'].append(dict(path=name,bytes=p.stat().st_size,sha256=sha(p.read_bytes()),retained_uncompressed=False))
        if mode=='positive' and receipt['exit_code']==0 and not receipt['timed_out']:
            with (out/'query.mir.gz').open('wb') as dest:
                with gzip.GzipFile(filename='',fileobj=dest,mode='wb',mtime=0) as zipped: zipped.write((work/'query.mir').read_bytes())
            receipt['retained_mir_sha256']=sha((out/'query.mir.gz').read_bytes())
        receipt['expected_terminal_status_observed']=(receipt['exit_code']==0 if mode=='positive' else receipt['exit_code']!=0) and not receipt['timed_out']
    except BaseException as error:
        receipt['recorder_error']=repr(error)
    finally:
        if child is not None:
            if child.poll() is None:
                os.killpg(child.pid,signal.SIGKILL); child.wait(timeout=5)
                receipt.update(exit_code=child.returncode,child_reaped=True,forced_finally_kill=True)
            if group_present(child.pid): os.killpg(child.pid,signal.SIGKILL); receipt['owned_group_cleanup_signal']='SIGKILL'
            receipt['owned_group_absent']=not group_present(child.pid)
        shutil.rmtree(work)
        if work.parent.exists() and not any(work.parent.iterdir()): work.parent.rmdir()
        receipt.update(state='complete',owned_scratch_removed=not work.exists(),finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        write(out/'receipt.json',receipt)
    success=receipt.get('expected_terminal_status_observed') and receipt['child_reaped'] and receipt['owned_group_absent'] and receipt['owned_scratch_removed'] and not receipt.get('recorder_error')
    print(json.dumps({k:receipt.get(k) for k in ['mode','exit_code','elapsed_seconds','timed_out','child_reaped','owned_group_absent','owned_scratch_removed','expected_terminal_status_observed','recorder_error']}))
    if not success: sys.exit(1)

def main():
    assert len(sys.argv)==3 and sys.argv[2] in ['positive','negative']
    mode=sys.argv[2]
    if sys.argv[1]=='--plan':
        _,_,plan,work=context(mode)
        assert not work.exists() and not (HERE/'commands'/('compiler-'+mode)).exists()
        write(HERE/(mode+'-compiler-plan.json'),plan)
        print(json.dumps(dict(mode=mode,plan_sha256=sha((HERE/(mode+'-compiler-plan.json')).read_bytes()),query_tree=plan['query_tree_sha256'])))
    else:
        assert sys.argv[1]=='--run-once'; run(mode)

if __name__=='__main__': main()
