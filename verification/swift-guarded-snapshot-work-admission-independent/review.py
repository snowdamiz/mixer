"""Independent bounded work-admission review. Writes only this owned directory."""
from pathlib import Path
from collections import Counter
import argparse
import difflib
import gzip
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRODUCER = HERE.parent / 'swift-guarded-snapshot-work-admission'
BASE = HERE.parent / 'swift-guarded-snapshot-funding-implementation'
CONTROL = 'src/experimental_swift_reactor/control.rs'
TESTS = 'src/experimental_swift_reactor/control_tests.rs'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
RELEASE = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-work-admission-independent-release.json'
EXPECTED_RELEASE = 'e902912c64ecb585782fd92e164377e46aefa3c3c1e7771ce0760655c3316e3d'
EXPECTED_PRODUCER = 'e8fe23ee4800a76ac6ca1486604b98b114a1f4dbdec1a25f520641c4e9951940'
EXPECTED_TREE = 'c909e78b0cd12c719f8366f5a701e871c86d8d640d90f34cb5dbe49ea9d5e712'
EXPECTED_BASE = '7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b'
def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
def write(name, value): (HERE/name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
def load(path): return json.loads(path.read_text())
def row(path, relative):
    data=path.read_bytes()
    return dict(path=relative,bytes=len(data),sha256=sha(data))
def custody():
    assert sha(RELEASE.read_bytes()) == EXPECTED_RELEASE
    assert sha((PRODUCER/'seal.json').read_bytes()) == EXPECTED_PRODUCER
    seal=load(PRODUCER/'seal.json')
    for member in seal['members']:
        assert row(PRODUCER/member['path'],member['path']) == member, member['path']
    assert len(seal['members'])==85 and sum(r['bytes'] for r in seal['members'])==5584323
    assert sha(canonical(seal['members']))==seal['manifest_sha256']
    manifest=load(PRODUCER/'source-manifest.json')
    base=load(BASE/'source-manifest.json')
    assert sha((BASE/'seal.json').read_bytes())==manifest['base_seal_sha256']
    assert len(base['members'])==144 and sha(canonical(base['members']))==EXPECTED_BASE
    for member in base['members']:
        assert row(BASE/'source/vm'/member['path'],member['path'])==member
    rows=[]
    for member in manifest['members']:
        path=PRODUCER/'overlay'/member['path']
        if not path.exists(): path=BASE/'source/vm'/member['path']
        assert row(path,member['path'])==member, member['path']
        rows.append(member)
    assert len(rows)==144 and sha(canonical(rows))==EXPECTED_TREE==manifest['source_tree_sha256']
    assert [a['path'] for a,b in zip(rows,base['members']) if a!=b]==[CONTROL]
    tests=load(PRODUCER/'test-overlay.json')
    assert (PRODUCER/tests['materialized']['path']).read_bytes()==(BASE/'source/vm'/TESTS).read_bytes()+(PRODUCER/'host-controls.inc.rs').read_bytes()
    return rows

def bounded(argv, env, cwd, timeout):
    started=time.monotonic()
    child=subprocess.Popen([str(a) for a in argv],cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    actions=[];expired=False
    try: out,err=child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        expired=True
        for sig in [signal.SIGTERM,signal.SIGKILL]:
            try: os.killpg(child.pid,sig);actions.append(sig.name)
            except ProcessLookupError: pass
            try: out,err=child.communicate(timeout=2);break
            except subprocess.TimeoutExpired: continue
        else: raise RuntimeError('owned child did not reap')
    try: os.killpg(child.pid,0); absent=False
    except ProcessLookupError: absent=True
    return out,err,dict(argv=[str(a) for a in argv],exit_code=child.returncode,elapsed_seconds=time.monotonic()-started,
        timeout_seconds=timeout,timed_out=expired,owned_process_group=child.pid,owned_group_absent=absent,
        child_reaped=True,new_session=True,cleanup_actions=actions)

def functions(text):
    result={}
    for chunk in re.split(r'(?=^fn )',text,flags=re.M):
        if not chunk.startswith('fn '):continue
        chunk=chunk[:chunk.index('\n}\n')+2]
        head=chunk.split('\n',1)[0]
        if '::adopt_body_core_v1' not in head:continue
        name='core' if '::{closure#' not in head else head[head.index('::{closure#'):].split('(',1)[0]
        roles=[]
        for m in re.finditer(r'^\s+let (?:mut )?(_\d+): ([^;]+);([^\n]*)',chunk,re.M):
            roles.append(dict(local=m[1],type=re.sub(r'\{closure@[^}]+\}','{closure}',m[2]),span=m[3].strip()))
        result[name]=dict(body=chunk,roles=roles)
    assert len(result)==6, list(result)
    return result

def compile_one(label, base=False, unit=False, release=False):
    rows=custody()
    folder=HERE/'commands'/label;folder.mkdir(parents=True,exist_ok=False)
    scratch=HERE/'owned-work'/label;scratch.mkdir(parents=True,exist_ok=False)
    actual=[]
    for member in rows:
        source=BASE/'source/vm'/member['path']
        if not base and (PRODUCER/'overlay'/member['path']).exists():source=PRODUCER/'overlay'/member['path']
        data=source.read_bytes()
        if unit and member['path']==TESTS:data+=(HERE/'independent-tests.inc.rs').read_bytes()
        target=scratch/'vm'/member['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        actual.append(dict(path=member['path'],bytes=len(data),sha256=sha(data)))
    version,verr,vr=bounded([RUSTC,'--version','--verbose'],{'PATH':'/usr/bin:/bin'},HERE,10)
    assert vr['exit_code']==0 and vr['owned_group_absent']
    (folder/'compiler-version-stdout').write_bytes(version);(folder/'compiler-version-stderr').write_bytes(verr)
    artifact=scratch/('test-bin' if unit else 'metadata.rmeta');mir=scratch/'output.mir'
    argv=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin',
        '-C','opt-level='+('3' if release else '0'),'-C','overflow-checks=yes','-C','panic=unwind',
        '-Zmir-opt-level=0','-Zmir-include-spans=yes','-Zprint-type-sizes']
    for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:
        argv+=['--cfg','feature="'+feature+'"']
    argv+=['--test'] if unit else ['--crate-type','rlib']
    argv+=[str(scratch/'vm/src/lib.rs'),'--emit='+('link' if unit else 'metadata')+'='+str(artifact)+',mir='+str(mir)]
    binding=dict(members=actual,source_tree_sha256=sha(canonical(actual)),source_kind='accepted base' if base else 'frozen candidate',independent_test_append=unit)
    env={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch),'RUSTC_BOOTSTRAP':'1','CARGO_MANIFEST_DIR':str(scratch/'vm'),
        'MIXER_LOADER_COMPILER_SHA256':sha(RUSTC.read_bytes()),'MIXER_LOADER_COMPILER_VERSION_SHA256':sha(version),
        'MIXER_LOADER_MANIFEST_SHA256':sha(canonical(binding)),'MIXER_LOADER_COMMAND_SHA256':sha(canonical([str(a) for a in argv]))}
    env['MIXER_LOADER_COMPILE_ENV_SHA256']=sha(canonical(env))
    try:
        out,err,receipt=bounded(argv,env,ROOT,55)
        (folder/'stdout.gz').write_bytes(gzip.compress(out,mtime=0));(folder/'stderr').write_bytes(err)
        receipt.update(schema=1,source_binding=binding,compiler_sha256=sha(RUSTC.read_bytes()),compiler_version=version.decode(),
            version_receipt=vr,environment=env,stdout_sha256=sha(out),stderr_sha256=sha(err),scope='host compiler only; no native/UI/capture')
        if mir.exists():
            data=mir.read_bytes();parts=functions(data.decode())
            (folder/'adoption-functions.mir').write_text('\n\n'.join(v['body'] for v in parts.values())+'\n')
            receipt['removed_full_mir']=dict(bytes=len(data),sha256=sha(data))
        if artifact.exists():receipt['removed_artifact']=row(artifact,artifact.name)
        (folder/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        assert receipt['exit_code']==0 and not receipt['timed_out'] and receipt['owned_group_absent'],err.decode()[-2500:]
        if unit:
            out,err,run=bounded([artifact,'ia_work_','--nocapture','--test-threads=1'],{'PATH':'/usr/bin:/bin'},scratch,30)
            (folder/'test-stdout').write_bytes(out);(folder/'test-stderr').write_bytes(err)
            run.update(schema=1,executable_sha256=sha(artifact.read_bytes()),source_tree_sha256=binding['source_tree_sha256'],
                stdout_sha256=sha(out),stderr_sha256=sha(err),scope='eight filtered independent synthetic private-policy tests; actual ordinary parser/validator proof; no loader/guest/cache/snapshot/writer')
            (folder/'test-receipt.json').write_text(json.dumps(run,indent=2,sort_keys=True)+'\n')
            assert run['exit_code']==0 and not run['timed_out'] and run['owned_group_absent'],out.decode()+err.decode()
            assert b'8 passed; 0 failed' in out
        print(json.dumps(dict(label=label,exit_code=receipt['exit_code'],seconds=receipt['elapsed_seconds'])),flush=True)
    finally:
        shutil.rmtree(scratch)
        (folder/'cleanup.json').write_text(json.dumps(dict(owned_scratch=str(scratch),removed=not scratch.exists()),indent=2)+'\n')
    custody()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('label');parser.add_argument('--base',action='store_true');parser.add_argument('--unit',action='store_true');parser.add_argument('--release',action='store_true')
    args=parser.parse_args();compile_one(args.label,base=args.base,unit=args.unit,release=args.release)
