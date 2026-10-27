"""Compiler-only authority regression checks; no engine, native or UI execution."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,sys,time
HERE=Path(__file__).resolve().parent
REPO=HERE.parent.parent
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def members(root):
    return [{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file()]
def run(case,mode):
    label=case+'-'+mode;command=HERE/'commands'/label;command.mkdir(parents=True,exist_ok=False)
    scratch=HERE/'owned-work'/label;scratch.mkdir(parents=True,exist_ok=False)
    source=scratch/'vm';shutil.copytree(HERE/'source/vm',source)
    baseline=json.loads((HERE/'source-manifest.json').read_text())['members'];assert members(source)==baseline
    loader='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
    control='src/experimental_swift_reactor/control.rs'
    changes=[];expected=[];unit=case=='positive-unit';layout=case=='layout'
    def append(path,text):
        p=source/path;p.write_text(p.read_text()+text);changes.append({'path':path,'append':text})
    if case=='old-bypasses':
        evidence=HERE.parent/'swift-guarded-snapshot-composition-independent/candidate-review/bypass-evidence.json'
        assert sha(evidence.read_bytes())=='9d9a84a970e2c7c2417c9ac5c8a297e353074cfce8499c1fb211638a3d123608'
        for witness in json.loads(evidence.read_text())['results'][0]['exact_witnesses']:append(witness['path'],witness['text'])
        expected=['E0061','E0061']
    elif case=='forged-owners':
        append(loader,"""
fn correction_forged_owners<'a>(cache:&'a mut Option<super::cache::SwiftFunctionCache>,control:&'a mut RuntimeControl,adopted:super::control::AdoptedProof)->super::control::SnapshotScopeBorrowV1<'a>{
 super::control::SnapshotScopeBorrowV1 {cache,control,wasi:None,adopted}
}
""")
        expected=['E0451']
    elif case=='double-consume':
        append(loader,"""
fn correction_double_consume(owners:super::control::SnapshotScopeBorrowV1<'_>){
 let _first=owners.into_parts();
 let _second=owners.into_parts();
}
""")
        expected=['E0382']
    elif case=='borrow-escape':
        append(control,"""
fn correction_borrow_escape(mut scope:SnapshotScopeV1)->SnapshotScopeBorrowV1<'static>{
 let adopted=scope.adopted.take().expect("actual scope proof");
 SnapshotScopeBorrowV1 {cache:&mut scope.cache,control:&mut scope.control,wasi:scope.wasi.as_ref(),adopted}
}
""")
        expected=['E0515','E0515','E0515']
    elif layout:
        append(control,"""
#[used]
#[no_mangle]
static MIXER_SCOPE_BORROW_LAYOUT_CORRECTION_V1:[usize;4]=[
 std::mem::size_of::<SnapshotScopeBorrowV1<'static>>(),std::mem::align_of::<SnapshotScopeBorrowV1<'static>>(),
 std::mem::size_of::<(&'static mut Option<super::cache::SwiftFunctionCache>,&'static mut RuntimeControl,Option<&'static AccountedWasi>,AdoptedProof)>(),
 std::mem::align_of::<(&'static mut Option<super::cache::SwiftFunctionCache>,&'static mut RuntimeControl,Option<&'static AccountedWasi>,AdoptedProof)>()
];
""")
    else:assert case in ('positive','positive-unit'),case
    version=subprocess.run([str(RUSTC),'--version','--verbose'],capture_output=True,check=True,timeout=5).stdout
    support=members(HERE.parent/'swift-guarded-snapshot-encoder-implementation/host');assert len(support)==11
    scripts=[{'path':name,'bytes':(HERE/name).stat().st_size,'sha256':sha((HERE/name).read_bytes())} for name in ['prepare.py','check.py','preparation.json','source-manifest.json','source-delta.patch']]
    preimage={'schema':1,'source_members':members(source),'upstream_encoder_support_members':support,'correction_support_members':scripts,'source_changes':changes}
    (command/'build-preimage.json').write_text(json.dumps(preimage,indent=2)+'\n')
    artifact=scratch/('candidate.ll' if layout else 'candidate.rmeta')
    argv=[str(RUSTC),'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','--error-format=json','-C','opt-level='+('3' if mode=='optimized' else '0'),'-C','overflow-checks=yes','-C','panic=unwind']
    for feature in ['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']:argv+=['--cfg','feature="'+feature+'"']
    argv+=['--test'] if unit else ['--crate-type','rlib']
    argv+=['--emit='+('llvm-ir' if layout else 'metadata'),str(source/'src/lib.rs'),'-o',str(artifact)]
    env={'PATH':'/usr/bin:/bin','TMPDIR':str(scratch),'CARGO_MANIFEST_DIR':str(source),'MIXER_LOADER_COMPILER_SHA256':sha(RUSTC.read_bytes()),'MIXER_LOADER_COMPILER_VERSION_SHA256':sha(version),'MIXER_LOADER_MANIFEST_SHA256':sha(canonical(preimage)),'MIXER_LOADER_COMMAND_SHA256':sha(json.dumps(argv,separators=(',',':')).encode())}
    env['MIXER_LOADER_COMPILE_ENV_SHA256']=sha(canonical(env))
    started=time.monotonic();p=subprocess.Popen(argv,cwd=REPO,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timed_out=False;cleanup=[]
    try:stdout,stderr=p.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out=True
        try:os.killpg(p.pid,signal.SIGTERM);cleanup.append('SIGTERM owned group')
        except ProcessLookupError:pass
        try:stdout,stderr=p.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try:os.killpg(p.pid,signal.SIGKILL);cleanup.append('SIGKILL owned group')
            except ProcessLookupError:pass
            stdout,stderr=p.communicate(timeout=2)
    try:os.killpg(p.pid,0);group_absent=False
    except ProcessLookupError:group_absent=True
    (command/'stdout').write_bytes(stdout);(command/'stderr').write_bytes(stderr)
    diagnostics=[]
    for line in stderr.splitlines():
        try:d=json.loads(line)
        except ValueError:continue
        if d.get('level')=='error' and d.get('code'):diagnostics.append({'code':d['code']['code'],'message':d['message'],'spans':d.get('spans',[])})
    codes=[d['code'] for d in diagnostics]
    passed=not timed_out and group_absent and ((p.returncode==0 and not expected) or (p.returncode!=0 and expected and sorted(codes)==sorted(expected)))
    output={'bytes':artifact.stat().st_size,'sha256':sha(artifact.read_bytes())} if artifact.exists() else None
    if layout and p.returncode==0:
        lines=[line for line in artifact.read_text().splitlines() if line.startswith('@MIXER_SCOPE_BORROW_LAYOUT_CORRECTION_V1 =')];assert len(lines)==1,lines
        (command/'exact-layout.llvm').write_text(lines[0]+'\n')
    receipt={'schema':1,'case':case,'mode':mode,'argv':argv,'cwd':str(REPO),'environment':env,'rustc_version':version.decode(),'source_tree_sha256':sha(canonical(preimage['source_members'])),'source_members':144,'support_members':11,'expected_error_codes':expected,'observed_error_codes':codes,'exit_code':p.returncode,'expectation_met':bool(passed),'timed_out':timed_out,'elapsed_seconds':time.monotonic()-started,'timeout_seconds':55,'owned_process_group':p.pid,'new_session':True,'child_reaped':True,'owned_group_absent':group_absent,'cleanup_actions':cleanup,'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),'artifact':output,'scope':'Compiler-only host authority controls. No engine/writer/native execution. No full storage or work admission.'}
    (command/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    shutil.rmtree(scratch)
    (command/'cleanup.json').write_text(json.dumps({'owned_scratch':str(scratch),'removed':not scratch.exists(),'compiler_child_reaped':True,'owned_group_absent':group_absent},indent=2)+'\n')
    print(json.dumps({'label':label,'passed':bool(passed),'codes':codes,'elapsed_seconds':receipt['elapsed_seconds']},sort_keys=True),flush=True)
    return bool(passed)
if __name__=='__main__':
    assert len(sys.argv)==3
    raise SystemExit(0 if run(sys.argv[1],sys.argv[2]) else 1)
