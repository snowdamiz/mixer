#!/usr/bin/env python3
"""Owned bounded host supervisor. Exact argv; process-group cleanup on failure."""
from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,sys,time
P=Path(__file__).resolve().parent

def run(name,argv,env=None):
    logs=P/'logs';logs.mkdir(exist_ok=True)
    tmp=P/'scratch'/name;tmp.mkdir(parents=True,exist_ok=True)
    actual=os.environ.copy();controls=['RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTDOCFLAGS','CARGO_BUILD_RUSTC','CARGO_BUILD_TARGET','RUSTUP_TOOLCHAIN']
    inherited_controls=[k for k in controls if k in actual]
    for k in controls:actual.pop(k,None)
    actual.update({'CARGO_TARGET_DIR':str(P/'scratch'/'cargo-target'),'TMPDIR':str(tmp),'CARGO_NET_OFFLINE':'true','RUSTC':'/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc'})
    if env:actual.update(env)
    source_members=[{'path':str(f.relative_to(P/'source/vm')),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted((P/'source/vm').rglob('*')) if f.is_file()]
    candidate_digest=hashlib.sha256(json.dumps(source_members,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
    child=subprocess.Popen(argv,cwd=P.parents[1],env=actual,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timeout=False
    try:out,err=child.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        timeout=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate()
    # Reap the owned process group only. Do not inventory unrelated processes.
    try:os.killpg(child.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    record={'argv':argv,'inherited_compiler_control_names_removed':inherited_controls,'cwd':str(P.parents[1]),'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-tick,'timeout_seconds':60,'timed_out':timeout,'exit_code':child.returncode,'candidate_source_tree_sha256':candidate_digest,'source_freeze_sha256':hashlib.sha256((P/'source-freeze.json').read_bytes()).hexdigest(),'env_overrides':{k:actual[k] for k in ['CARGO_TARGET_DIR','TMPDIR','CARGO_NET_OFFLINE','RUSTC']},'owned_child_reaped':True}
    for label,data in [('stdout',out),('stderr',err)]:
        (logs/f'{name}.{label}').write_bytes(data);record[label]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    (logs/f'{name}.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record));print(out.decode(errors='replace')[-4000:]);print(err.decode(errors='replace')[-1500:]);return not timeout and child.returncode==0
if __name__=='__main__':sys.exit(0 if run(sys.argv[1],sys.argv[2:]) else 1)
