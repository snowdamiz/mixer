"""Prepare then execute precisely one coordinated LLVM retention query."""
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
R=D.parents[1]
B=R/'verification/swift-guarded-snapshot-resource-binary-correspondence'
V=R/'verification'
SOURCE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
APPEND_PATH='src/experimental_swift_reactor/cache/initial_profile_v1.rs'
APPEND='''
// Inert evidence-only retention: no registration, export, execution or fixture.
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static NATIVE_OPEN_READ_PATH_V1: fn(&'static std::path::Path) -> std::io::Result<std::fs::File> = std::fs::File::open::<&'static std::path::Path>;
#[cfg(mixer_bootstrap_one_fixture_v1)]
fn native_open_create_path_v1(path: &std::path::Path) -> std::io::Result<std::fs::File> {
    std::fs::OpenOptions::new().write(true).create_new(true).open(path)
}
#[cfg(mixer_bootstrap_one_fixture_v1)]
#[used]
static NATIVE_OPEN_CREATE_PATH_V1: fn(&std::path::Path) -> std::io::Result<std::fs::File> = native_open_create_path_v1;
'''
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def put(n,x):(D/n).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def checked(p,row):
    b=p.read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256'],str(p);return b
def counted(items):
    chunks=[struct.pack('<Q',len(items))]
    for item in items:
        b=item.encode();assert b'\0' not in b;chunks += [struct.pack('<Q',len(b)),b]
    return b''.join(chunks)
def owned_run(label,argv,env,timeout):
    assert not (D/(label+'-receipt.json')).exists(),'single owned query already recorded'
    started=time.monotonic();p=subprocess.Popen(argv,cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    actions=[];timed=False
    try:out,err=p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed=True;os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL owned group at ceiling');out,err=p.communicate()
    try:os.killpg(p.pid,0);absent=False
    except ProcessLookupError:absent=True
    outputs={}
    for n,b in [('stdout',out),('stderr',err)]:
        name=label+'.'+n+'.gz';(D/name).write_bytes(gzip.compress(b,mtime=0));outputs[n]=dict(path=name,bytes=len(b),sha256=sha(b))
    rec=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=argv,cwd=str(R),environment=env,direct_child_pid=p.pid,direct_child_waited=True,
      elapsed_seconds=time.monotonic()-started,exit_code=p.returncode,timed_out=timed,timeout_seconds=timeout,owned_group_absent=absent,cleanup_actions=actions,
      outputs=outputs,product_runtime=False,global_process_inventory=False)
    put(label+'-receipt.json',rec)
    assert p.returncode==0 and absent and not timed,'Preserve diagnostics; no retry authorized'
    return rec

def extra_native():
    tools=json.loads((B/'compatible-installed-tools.json').read_text());t=tools['tools']['llvm-objdump'];checked(Path(t['path']),t);checked(Path(tools['libLLVM']['path']),tools['libLLVM'])
    a=json.loads((B/'installed-inputs.json').read_text())['archives']['alloc'];checked(Path(a['path']),a)
    symbol='__RNvMs_NtNtCs6zY7rJBZy9D_5alloc3ffi5c_strNtB4_7CString19__from_vec_unchecked'
    argv=[t['path'],'--disassemble-symbols='+symbol,'--reloc',a['path']]
    put('cstring-constructor-plan.json',dict(authorization='Root approved one additional exact constructor symbol read <=15s',argv=argv,tool=t,libLLVM=tools['libLLVM'],archive=a,compiler=False,runtime=False))
    rec=owned_run('cstring-constructor',argv,{'PATH':'/usr/bin:/bin','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1'},15)
    print(json.dumps(dict(kind='constructor-native',seconds=rec['elapsed_seconds'],exit_code=rec['exit_code'])))

def prepare():
    assert not (D/'compiler-owned-work').exists()
    base=V/'swift-guarded-snapshot-loader-work-source146'
    manifest=json.loads((base/'source146-manifest.json').read_text());refs=json.loads((base/'source-reference-map.json').read_text())['members']
    assert len(refs)==146 and sha(canonical(manifest['members']))==manifest['tree_sha256']==SOURCE
    assert [{k:r[k] for k in ('path','bytes','sha256')} for r in refs]==manifest['members']
    original={r['path']:checked(R/r['source'],r) for r in refs}
    sources=original.copy();sources[APPEND_PATH]+=APPEND.encode();(D/'generic-open-append.inc.rs').write_text(APPEND)
    compiled=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(sources.items(),key=lambda p:Path(p[0]))]
    work=D/'compiler-owned-work';vm=work/'vm'
    for n,b in sources.items():p=vm/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    prior=json.loads((B/'compiler-receipt.json').read_text());argv=prior['argv'].copy()
    argv[-2]=str(vm/'src/lib.rs');argv[-1]='--emit=llvm-ir='+str(work/'generic-open.ll')
    compiler=Path(argv[0]);compiler_sha=sha(compiler.read_bytes());assert compiler_sha=='dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0'
    version=(B/'compiler-version.stdout').read_bytes();assert sha(version)=='352d6857968e80a6357a926ac685b9b07f77c479aaafde33e73a53945e802909'
    env={k:v for k,v in prior['environment'].items() if not k.startswith('MIXER_LOADER_')}
    env.update(TMPDIR=str(work),CARGO_MANIFEST_DIR=str(vm),PYTHONDONTWRITEBYTECODE='1')
    closure=dict(schema=1,source_manifest=manifest,source_reference_map=refs,compiled_members=compiled,compiled_tree_sha256=sha(canonical(compiled)),
      append_path=APPEND_PATH,append_sha256=sha(APPEND.encode()),append_bytes=len(APPEND.encode()),original_source_bodies_unchanged=True,
      retained_functions=['File::open::<&Path>','OpenOptions::new().write(true).create_new(true).open::<&Path>'],
      compiler_sha256=compiler_sha,compiler_version_stdout_sha256=sha(version),compiler_version_stdout=version.decode(),
      query_script_sha256=sha(Path(__file__).read_bytes()),original_caller_binding=False,linked_executable=False,product_runtime=False)
    raw=canonical(closure);(D/'compiled-manifest.json').write_bytes(raw)
    av=counted(argv);ev=counted([k+'='+v for k,v in sorted(env.items())]);(D/'argv.bin').write_bytes(av);(D/'environment.bin').write_bytes(ev)
    keys=dict(zip(['MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256'],[sha(raw),sha(av),sha(ev),compiler_sha,sha(version)]))
    plan=dict(authorization='Root approved one codegen-only source146 query; target15s, ceiling60s, no runtime/linkexe/retry; exact original flags retained',
      argv=argv,environment=env|keys,compiled_manifest_sha256=sha(raw),source_tree_sha256=SOURCE,compiled_tree_sha256=closure['compiled_tree_sha256'],
      timeout_seconds=60,target_seconds=15,append_bytes=APPEND,append_sha256=sha(APPEND.encode()),compiler_sha256=compiler_sha,version=version.decode())
    put('compiler-plan.json',plan);print(sha((D/'compiler-plan.json').read_bytes()))

def run():
    plan=json.loads((D/'compiler-plan.json').read_text());closure=json.loads((D/'compiled-manifest.json').read_text())
    assert sha((D/'compiled-manifest.json').read_bytes())==plan['compiled_manifest_sha256']
    assert sha(Path(plan['argv'][0]).read_bytes())==plan['compiler_sha256']
    assert sha(Path(__file__).read_bytes())==closure['query_script_sha256']
    work=D/'compiler-owned-work'
    for row in closure['compiled_members']:checked(work/'vm'/row['path'],row)
    complete=False
    try:
        rec=owned_run('compiler',plan['argv'],plan['environment'],60)
        b=(work/'generic-open.ll').read_bytes();packed=gzip.compress(b,mtime=0);(D/'generic-open.ll.gz').write_bytes(packed)
        put('generic-open.ll-archive.json',dict(raw_bytes=len(b),raw_sha256=sha(b),archive_bytes=len(packed),archive_sha256=sha(packed),full_output_retained=True))
        complete=True
    finally:
        files=[p for p in work.rglob('*') if p.is_file()];rows=[dict(path=str(p.relative_to(work)),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in files]
        rec=json.loads((D/'compiler-receipt.json').read_text());safe=rec['direct_child_waited'] and rec['owned_group_absent']
        if safe:shutil.rmtree(work)
        put('compiler-cleanup.json',dict(complete=complete,owned_children_waited_and_groups_absent=safe,owned_scratch_removed=not work.exists(),removed_files=rows,
          product_runtime=False,native_simulator_emulator_or_capture=False,global_process_inventory=False))
    print(json.dumps(dict(kind='generic-instantiation-only',seconds=rec['elapsed_seconds'],exit_code=rec['exit_code'],runtime=False)))

if __name__=='__main__':{'extra-native':extra_native,'prepare':prepare,'run':run}[sys.argv[1]]()
