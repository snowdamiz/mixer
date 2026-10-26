#!/usr/bin/env python3
"""Bounded dedicated old-source host driver; no full target or test suite."""
from pathlib import Path
import datetime,hashlib,json,os,platform,resource,shutil,subprocess,sys,tempfile,time
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
TOOLS=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def manifest(base):
    members=[{'path':str(p.relative_to(base)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(base.rglob('*')) if p.is_file()]
    return {'schema':1,'members':members,'member_count':len(members),'tree_definition':'sorted full path TAB bytes TAB sha256 LF','tree_sha256':hashlib.sha256(''.join(f"{m['path']}\t{m['bytes']}\t{m['sha256']}\n" for m in members).encode()).hexdigest()}
def child_limits():
    resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024*1024,4*1024*1024))
def run(argv,name,env):
    folder=OUT/'old-commands'/name;folder.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();timed=False
    with (folder/'stdout').open('wb') as stdout,(folder/'stderr').open('wb') as stderr:
        child=subprocess.Popen(list(map(str,argv)),cwd=ROOT,env=env,stdout=stdout,stderr=stderr,preexec_fn=child_limits)
        try:code=child.wait(timeout=60)
        except subprocess.TimeoutExpired:
            timed=True;child.kill();code=child.wait(timeout=5)
    record={'argv':list(map(str,argv)),'cwd':str(ROOT),'exit_code':code,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':60,'timed_out':timed,'output_file_byte_cap_each':4194304,'stdout_sha256':sha(folder/'stdout'),'stderr_sha256':sha(folder/'stderr'),'child_reaped':True}
    write(folder/'receipt.json',record);return code,folder
def main():
    source=OUT/'old-source/vm';base=json.loads((OUT/'inputs/base-source-manifest.json').read_text())
    existing=manifest(source)
    if existing['member_count']==134:
        assert existing['members']==base['members']
        write(OUT/'old-base-source-manifest.json',existing)
        q=source/'src/experimental_swift_reactor/cache/independent_preaccess_controls.rs';q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((OUT/'old_source_controls.rs').read_bytes())
        for rel,extra in [
          ('src/experimental_swift_reactor/cache.rs','\n// Independent PREACCESS original-source-only finite control bridge.\n#[path = "cache/independent_preaccess_controls.rs"]\nmod independent_preaccess_controls;\npub(super) fn run_independent_preaccess(a:&std::path::Path,b:&std::path::Path) { independent_preaccess_controls::run(a,b); }\n'),
          ('src/experimental_swift_reactor/mod.rs','\npub(crate) fn run_independent_preaccess(a:&std::path::Path,b:&std::path::Path) { cache::run_independent_preaccess(a,b); }\n'),
          ('src/lib.rs','\n#[cfg(feature="experimental-swift-reactor")]\npub fn run_independent_preaccess(a:&std::path::Path,b:&std::path::Path) { experimental_swift_reactor::run_independent_preaccess(a,b); }\n')]:
            p=source/rel;p.write_text(p.read_text()+extra)
        p=source/'src/bin/independent-preaccess.rs';p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('fn main(){ let a:Vec<_>=std::env::args().collect(); assert_eq!(a.len(),3); mixer_vm::run_independent_preaccess(std::path::Path::new(&a[1]),std::path::Path::new(&a[2])); }\n')
    m=manifest(source);assert m['member_count']==136
    write(OUT/'old-probe-source-manifest.json',m)
    env=os.environ.copy();scratch=Path(tempfile.mkdtemp(prefix='independent-old-',dir=OUT))
    env.update({'RUSTC':str(TOOLS/'rustc'),'PATH':str(TOOLS)+':'+env.get('PATH',''),'CARGO_TARGET_DIR':str(scratch/'target'),'CARGO_HOME':str(scratch/'cargo-home'),'TMPDIR':str(scratch/'tmp')});Path(env['TMPDIR']).mkdir()
    # Reject hidden compiler flag injection; fixed config below is the whole
    # selected compiler setting. Unrelated user configuration is not inherited.
    for key in ['RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','CARGO_BUILD_RUSTFLAGS','CARGO_TARGET_AARCH64_APPLE_DARWIN_RUSTFLAGS']:
        env.pop(key,None)
    results=[];okay=True
    environment={'schema':1,'scope':'OLD SOURCE ONLY; no initial-profile candidate read or acceptance','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'python_executable':sys.executable,'python_sha256':sha(Path(sys.executable)),'platform':platform.platform(),'rustc':str(TOOLS/'rustc'),'rustc_sha256':sha(TOOLS/'rustc'),'cargo':str(TOOLS/'cargo'),'cargo_sha256':sha(TOOLS/'cargo'),'source_tree_sha256':m['tree_sha256'],'runner_sha256':sha(Path(__file__)),'owned_scratch':str(scratch),'native_UI_capture_or_process_inventory':False,'compiler_environment':{k:env.get(k) for k in ['RUSTC','CARGO_TARGET_DIR','CARGO_HOME','TMPDIR','MACOSX_DEPLOYMENT_TARGET','SDKROOT','RUSTFLAGS']}}
    attempt=1
    while (OUT/f'old-commands/attempt-{attempt}-rustc-vV').exists():attempt+=1
    try:
        for name,argv in [('rustc-vV',[TOOLS/'rustc','-vV']),('cargo-version',[TOOLS/'cargo','--version']),('target-cfg',[TOOLS/'rustc','--print','cfg','--target','aarch64-apple-darwin']),('target-features',[TOOLS/'rustc','--print','target-features','--target','aarch64-apple-darwin']),('source-revision',['git','rev-parse','HEAD'])]:
            code,folder=run(argv,f'attempt-{attempt}-{name}',env);assert code==0
            environment[name]=(folder/'stdout').read_text()
        for mode in ['debug','release']:
            argv=[TOOLS/'cargo','build','--verbose','--offline','--locked','--manifest-path',source/'Cargo.toml','--target','aarch64-apple-darwin','--features','experimental-swift-reactor,experimental-function-cache','--bin','independent-preaccess']
            if mode=='release':argv+=['--release']
            code,folder=run(argv,f'attempt-{attempt}-{mode}-build',env)
            result={'mode':mode,'build_exit':code};results.append(result)
            if code:okay=False;continue
            binary=scratch/'target/aarch64-apple-darwin'/mode/'independent-preaccess'
            result.update({'executable_sha256':sha(binary),'executable_bytes':binary.stat().st_size})
            output=OUT/f'old-artifacts/attempt-{attempt}-{mode}';output.mkdir(parents=True,exist_ok=False)
            code,folder=run([binary,OUT/'fixtures',output],f'attempt-{attempt}-{mode}-controls',env)
            result.update({'control_exit':code,'artifacts':manifest(output),'PASS_lines':[line for line in (folder/'stdout').read_text().splitlines() if line.startswith('PASS ')]})
            okay=okay and code==0
    finally:
        shutil.rmtree(scratch)
        environment['cleanup']={'owned_scratch_removed':not scratch.exists(),'compiler_products_retained':False,'all_owned_children_reaped':True,'no_native_instance_started':True}
        write(OUT/f'old-environment-attempt-{attempt}.json',environment)
        write(OUT/f'old-controls-attempt-{attempt}.json',{'schema':1,'scope':'OLD SOURCE ONLY, constructor/phase/cleanup baseline; no guard/header/wrapper implementation evidence','results':results,'all_passed':okay,'cleanup':environment['cleanup']})
    print(f'old-source-only attempt {attempt}: passed={okay}; compiler scratch removed')
    if not okay:raise SystemExit(1)
if __name__=='__main__':main()
