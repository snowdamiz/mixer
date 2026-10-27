"""Bounded compiler/control-only runner. Never invokes VM, loader or writer."""
from pathlib import Path
from collections import Counter
import argparse
import gzip
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
from prepare import HERE,ROOT,BASE,CONTROL,TESTS,base_members,canonical,sha,write

RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']

def bounded(argv,env,cwd,timeout=55):
    start=time.monotonic()
    child=subprocess.Popen(argv,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    expired=False;actions=[]
    try:out,err=child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        expired=True
        for sig,seconds in [(signal.SIGTERM,2),(signal.SIGKILL,2)]:
            try:os.killpg(child.pid,sig);actions.append(sig.name+' owned group')
            except ProcessLookupError:pass
            try:out,err=child.communicate(timeout=seconds);break
            except subprocess.TimeoutExpired:continue
        else:raise AssertionError('owned child failed to reap')
    try:os.killpg(child.pid,0);absent=False
    except ProcessLookupError:absent=True
    return out,err,dict(argv=[str(x) for x in argv],exit_code=child.returncode,elapsed_seconds=time.monotonic()-start,
        timeout_seconds=timeout,timed_out=expired,owned_process_group=child.pid,new_session=True,child_reaped=True,
        owned_group_absent=absent,cleanup_actions=actions)

def materialize(destination,base=False,unit=False):
    rows=base_members()
    for row in rows:
        target=destination/row['path'];target.parent.mkdir(parents=True,exist_ok=True)
        overlay=HERE/'overlay'/row['path']
        source=overlay if overlay.exists() and not base else BASE/'source/vm'/row['path']
        if unit and row['path']==TESTS and (HERE/'test-overlay'/TESTS).exists():source=HERE/'test-overlay'/TESTS
        # Copy verified bytes into owned scratch. Frozen inputs remain immutable.
        target.write_bytes(source.read_bytes())
    actual=[dict(path=p.relative_to(destination).as_posix(),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(destination.rglob('*')) if p.is_file()]
    return dict(members=actual,source_tree_sha256=sha(canonical(actual)),base=base,unit_test_overlay=unit)

def selected_mir(text):
    chunks=re.split(r'(?=^fn )',text,flags=re.M)
    selected=[p[:p.index('\n}\n')+2] for p in chunks if p.startswith('fn ') and '::adopt_body_core_v1' in p.split('\n',1)[0]]
    assert len(selected)>=2,[p.split('\n',1)[0] for p in selected]
    return selected

def compile_one(label,base=False,unit=False,execute=False,release=False):
    assert not (HERE/'seal.json').exists()
    folder=HERE/'commands'/label;folder.mkdir(parents=True,exist_ok=False)
    scratch=HERE/'owned-work'/label;scratch.mkdir(parents=True,exist_ok=False)
    binding=materialize(scratch/'vm',base=base,unit=unit)
    version,version_err,vr=bounded([RUSTC,'--version','--verbose'],{'PATH':'/usr/bin:/bin'},HERE,10)
    (folder/'compiler-version-stdout').write_bytes(version)
    (folder/'compiler-version-stderr').write_bytes(version_err)
    assert vr['exit_code']==0 and vr['owned_group_absent']
    artifact=scratch/('host-tests' if execute else 'candidate.rmeta');mir=scratch/'candidate.mir'
    argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin',
        '-C','opt-level='+('3' if release else '0'),'-C','overflow-checks=yes','-C','panic=unwind',
        '-Zmir-opt-level=0','-Zmir-include-spans=yes','-Zprint-type-sizes']
    for feature in FEATURES:argv+=['--cfg','feature="'+feature+'"']
    argv+=['--test'] if unit else ['--crate-type','rlib']
    argv+=[str(scratch/'vm/src/lib.rs')]
    argv+=['--emit=link','-o',str(artifact)] if execute else ['--emit=metadata='+str(artifact)+',mir='+str(mir)]
    env={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch),'RUSTC_BOOTSTRAP':'1','CARGO_MANIFEST_DIR':str(scratch/'vm'),
        'MIXER_LOADER_COMPILER_SHA256':sha(RUSTC.read_bytes()),'MIXER_LOADER_COMPILER_VERSION_SHA256':sha(version),
        'MIXER_LOADER_MANIFEST_SHA256':sha(canonical(binding)),'MIXER_LOADER_COMMAND_SHA256':sha(canonical(argv))}
    env['MIXER_LOADER_COMPILE_ENV_SHA256']=sha(canonical(env))
    try:
        out,err,receipt=bounded(argv,env,ROOT)
        (folder/'stdout.gz').write_bytes(gzip.compress(out,mtime=0));(folder/'stderr').write_bytes(err)
        receipt.update(schema=1,source_binding=binding,compiler_sha256=sha(RUSTC.read_bytes()),compiler_version=version.decode(),
            compiler_version_command=vr,environment=env,scope='actual control/parser/validator tests only' if execute else 'metadata/MIR only; no executable',
            stdout_sha256=sha(out),stdout_storage='stdout.gz (gzip, exact uncompressed SHA256)',stderr_sha256=sha(err))
        if mir.exists():
            allmir=mir.read_text();selected=selected_mir(allmir)
            (folder/'adoption-functions.mir').write_text('\n\n'.join(selected)+'\n')
            receipt['full_mir_removed']=dict(bytes=mir.stat().st_size,sha256=sha(mir.read_bytes()))
        if artifact.exists():receipt['removed_compiler_artifact']=dict(bytes=artifact.stat().st_size,sha256=sha(artifact.read_bytes()))
        (folder/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        assert receipt['exit_code']==0 and receipt['owned_group_absent'] and not receipt['timed_out'],err.decode()[-3500:]
        if execute:
            args=[str(artifact),'--exact','experimental_swift_reactor::control::tests::'+os.environ['MIXER_CONTROL_TEST_NAME'],'--nocapture','--test-threads=1'] if 'MIXER_CONTROL_TEST_NAME' in os.environ else [str(artifact),'work_admission_host_','--nocapture','--test-threads=1']
            out,err,run=bounded(args,{'PATH':'/usr/bin:/bin'},scratch,30)
            (folder/'test-stdout').write_bytes(out);(folder/'test-stderr').write_bytes(err)
            run.update(schema=1,executable_sha256=sha(artifact.read_bytes()),source_tree_sha256=binding['source_tree_sha256'],
                scope='filtered synthetic private policy core plus actual in-memory parser/validator; no loader/guest/cache/snapshot/writer dispatch',
                stdout_sha256=sha(out),stderr_sha256=sha(err))
            (folder/'test-receipt.json').write_text(json.dumps(run,indent=2,sort_keys=True)+'\n')
            assert run['exit_code']==0 and run['owned_group_absent'] and not run['timed_out'],out.decode()+err.decode()
        print(json.dumps(dict(label=label,exit_code=receipt['exit_code'],seconds=receipt['elapsed_seconds'])),flush=True)
    finally:
        shutil.rmtree(scratch)
        (folder/'cleanup.json').write_text(json.dumps(dict(owned_scratch=str(scratch),removed=not scratch.exists()),indent=2)+'\n')
    base_members()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--base',action='store_true');p.add_argument('--unit',action='store_true');p.add_argument('--execute',action='store_true');p.add_argument('--release',action='store_true');a=p.parse_args()
    compile_one(a.label,base=a.base,unit=a.unit,execute=a.execute,release=a.release)
