"""Bounded compiler/control driver; requires a separately recorded root release.

Only explicit correction seal arguments unlock correction reads. This file may
be prepared before release; it is not invoked until root releases frozen input.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode=True
from prepare import HERE, VERIFICATION, ORIGINAL, BASE, CONTROL, TESTS, custody, sha, canonical, load, write, member

RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
def bounded(argv,env,cwd,timeout):
    start=time.monotonic();proc=subprocess.Popen([str(a) for a in argv],cwd=cwd,env=env,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    signals=[];expired=False
    try: out,err=proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        expired=True
        for sig in [signal.SIGTERM,signal.SIGKILL]:
            try: os.killpg(proc.pid,sig);signals.append(sig.name)
            except ProcessLookupError: pass
            try: out,err=proc.communicate(timeout=2);break
            except subprocess.TimeoutExpired: continue
        else: raise RuntimeError('owned child failed to reap')
    try: os.killpg(proc.pid,0);absent=False
    except ProcessLookupError: absent=True
    return out,err,dict(argv=[str(a) for a in argv],exit_code=proc.returncode,
        elapsed_seconds=time.monotonic()-start,timeout_seconds=timeout,timed_out=expired,
        owned_process_group=proc.pid,owned_group_absent=absent,child_reaped=True,new_session=True,cleanup_actions=signals)

def verify_correction(correction, expected_seal):
    assert sha((correction/'seal.json').read_bytes())==expected_seal
    seal=load(correction/'seal.json')
    assert sha(canonical(seal['members']))==seal['manifest_sha256']
    for row in seal['members']: assert member(correction/row['path'],row['path'])==row,row['path']
    manifest=load(correction/'source-manifest.json')
    assert len(manifest['members'])==144
    assert sha(canonical(manifest['members']))==manifest['source_tree_sha256']
    for row in manifest['members']:
        path=correction/'overlay'/row['path']
        if not path.exists(): path=BASE/'source/vm'/row['path']
        assert member(path,row['path'])==row,row['path']
    return manifest

PRODUCTION_ASSERTIONS=b'''\n// Independent production-only const floor probe; no runtime helper is emitted.\nconst _: () = {\n    assert!(matches!(FOUNDATION_CONSTRUCTION_BYTES, Some(366_312)));\n    assert!(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1 == 78_240);\n    assert!(COMMON_WORK_ADMISSION_SOURCE_EXTRA_BYTES_V1 == 1_436);\n    assert!(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1 == 941_467);\n    assert!(matches!(COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1, Some(445_988)));\n    assert!(matches!(SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1, Some(1_387_455)));\n    assert!(matches!(SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1, Some(1_387_455)));\n    assert!(matches!(1_387_455usize.checked_add(SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1), Some(1_817_630)));\n    assert!(SNAPSHOT_FIXED_EXECUTION_WORK_V1 == 451_814_442);\n};\n'''
def run(correction, expected_seal, label, unit):
    assert not (HERE/'seal.json').exists()
    release=load(HERE/'release.json');assert release['correction_seal_sha256']==expected_seal
    assert release['root_explicit_release'] is True
    custody();manifest=verify_correction(correction,expected_seal)
    folder=HERE/'commands'/label;folder.mkdir(parents=True,exist_ok=False)
    scratch=HERE/'owned-work'/label;scratch.mkdir(parents=True,exist_ok=False)
    actual=[]
    version,verr,vr=bounded([RUSTC,'--version','--verbose'],{'PATH':'/usr/bin:/bin'},HERE,10)
    assert vr['exit_code']==0 and vr['owned_group_absent']
    (folder/'compiler-version-stdout').write_bytes(version);(folder/'compiler-version-stderr').write_bytes(verr)
    overlay=(HERE/'independent-tests.inc.rs').read_bytes() if unit else PRODUCTION_ASSERTIONS
    (folder/('test-overlay.inc.rs' if unit else 'const-assertions.inc.rs')).write_bytes(overlay)
    try:
        for row in manifest['members']:
            source=correction/'overlay'/row['path']
            if not source.exists():source=BASE/'source/vm'/row['path']
            data=source.read_bytes()
            if row['path']==(TESTS if unit else CONTROL): data+=overlay
            target=scratch/'vm'/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            actual.append(dict(path=row['path'],bytes=len(data),sha256=sha(data)))
        binding=dict(members=actual,source_tree_sha256=sha(canonical(actual)),
            frozen_source_tree_sha256=manifest['source_tree_sha256'],overlay_sha256=sha(overlay),
            overlay_scope='test module append' if unit else 'production const-assertion-only append')
        artifact=scratch/('test-bin' if unit else 'metadata.rmeta')
        argv=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin',
            '-C','opt-level=0','-C','overflow-checks=yes','-C','panic=unwind']
        for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
            argv+=['--cfg','feature="'+feature+'"']
        argv+=['--test'] if unit else ['--crate-type','rlib']
        argv+=[str(scratch/'vm/src/lib.rs'),'--emit='+('link' if unit else 'metadata')+'='+str(artifact)]
        env={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch),'CARGO_MANIFEST_DIR':str(scratch/'vm'),
            'MIXER_LOADER_COMPILER_SHA256':sha(RUSTC.read_bytes()),'MIXER_LOADER_COMPILER_VERSION_SHA256':sha(version),
            'MIXER_LOADER_MANIFEST_SHA256':sha(canonical(binding)),
            'MIXER_LOADER_COMMAND_SHA256':sha(canonical([str(a) for a in argv]))}
        env['MIXER_LOADER_COMPILE_ENV_SHA256']=sha(canonical(env))
        out,err,receipt=bounded(argv,env,VERIFICATION.parent,55)
        (folder/'stdout.gz').write_bytes(gzip.compress(out,mtime=0));(folder/'stderr').write_bytes(err)
        receipt.update(schema=1,source_binding=binding,compiler_sha256=sha(RUSTC.read_bytes()),
            compiler_version=version.decode(),version_receipt=vr,environment=env,
            stdout_sha256=sha(out),stderr_sha256=sha(err),
            scope='independent host compiler only; native/device/UI/capture remain paused')
        if artifact.exists():receipt['removed_artifact']=member(artifact,artifact.name)
        (folder/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        assert receipt['exit_code']==0 and not receipt['timed_out'] and receipt['owned_group_absent'],err.decode()[-2500:]
        if unit:
            out,err,test=bounded([artifact,'ci_common_','--nocapture','--test-threads=1'],{'PATH':'/usr/bin:/bin'},scratch,30)
            (folder/'test-stdout').write_bytes(out);(folder/'test-stderr').write_bytes(err)
            test.update(schema=1,executable_sha256=sha(artifact.read_bytes()),source_tree_sha256=binding['source_tree_sha256'],
                overlay_sha256=sha(overlay),stdout_sha256=sha(out),stderr_sha256=sha(err),
                scope='four filtered independent actual control/parser tests; synthetic selected private-core fixture; no authentic ingress, loader, guest, cache, snapshot scope/construct, writer')
            (folder/'test-receipt.json').write_text(json.dumps(test,indent=2,sort_keys=True)+'\n')
            assert test['exit_code']==0 and not test['timed_out'] and test['owned_group_absent'],out.decode()+err.decode()
            assert b'4 passed; 0 failed' in out
        print(json.dumps(dict(label=label,compile_exit=receipt['exit_code'],seconds=receipt['elapsed_seconds'])))
    finally:
        shutil.rmtree(scratch)
        if (HERE/'owned-work').exists() and not any((HERE/'owned-work').iterdir()): (HERE/'owned-work').rmdir()
        write('commands/'+label+'/cleanup.json',dict(owned_scratch=str(scratch),removed=not scratch.exists(),
            scope='only this driver owned child groups were probed; no global inventory'))
    custody();verify_correction(correction,expected_seal)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('label');parser.add_argument('--correction',required=True)
    parser.add_argument('--seal-sha256',required=True);parser.add_argument('--unit',action='store_true')
    args=parser.parse_args();run(Path(args.correction),args.seal_sha256,args.label,args.unit)
