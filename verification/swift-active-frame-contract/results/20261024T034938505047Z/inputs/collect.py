#!/usr/bin/env python3
"""Archive and compile private contract overlays; never edit VM/product files."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, tarfile
from inventory import rows, render, print_fields

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
STAMP=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT=HERE/'results'/STAMP
BUILD=HERE/'build'/STAMP
OUT.mkdir(parents=True); BUILD.mkdir(parents=True)
ENV=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
ENV.pop('RUSTC_BOOTSTRAP',None)
def encoded(x): return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def digest(x): return hashlib.sha256(x).hexdigest()
def sha(p): return digest(p.read_bytes())
def manifest(p): return {str(x.relative_to(p)):sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
# Pin the first captured exact accepted closure despite coordinated root test repair.
PINNED=HERE/'results/20261024T034305278564Z/source.tar.gz'
with tarfile.open(PINNED) as t:
    saved_source={m.name.removeprefix('vm/'):t.extractfile(m).read() for m in t.getmembers() if m.isfile()}
source={name:digest(data) for name,data in sorted(saved_source.items())}
(OUT/'source-manifest.json').write_bytes(encoded(source))
shutil.copyfile(PINNED,OUT/'source.tar.gz')
(OUT/'inputs').mkdir()
for name in ['collect.py','inventory.py','proposed.rs','initial-environment-attempt.json']:
    shutil.copyfile(HERE/name,OUT/'inputs'/name)
(OUT/'inventory-schema.json').write_bytes(encoded(rows()))
commands=[]; variants=[]; layouts=[]; comparisons=[]; privacy=[]; abi=[]
status='failed-preflight'
def cmd(name,argv,cwd,target=None,closure=None,bootstrap=False,error=None):
    if closure is not None: assert manifest(cwd)==closure, 'changed before '+name
    env=dict(ENV)
    if target: env['CARGO_TARGET_DIR']=str(target)
    if bootstrap: env['RUSTC_BOOTSTRAP']='1'
    p=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,text=True)
    for stream in ['stdout','stderr']: (OUT/(name+'.'+stream)).write_text(getattr(p,stream))
    commands.append(dict(name=name,argv=argv,cwd=str(cwd),target=str(target) if target else None,
        bootstrap=bootstrap,exitCode=p.returncode,expectedError=error,
        stdout=name+'.stdout',stdoutSHA256=sha(OUT/(name+'.stdout')),
        stderr=name+'.stderr',stderrSHA256=sha(OUT/(name+'.stderr'))))
    if closure is not None: assert manifest(cwd)==closure, 'changed after '+name
    if error:
        assert p.returncode!=0 and error in p.stderr+p.stdout, (name,p.stderr[-3000:])
    else: assert p.returncode==0, (name,p.stderr[-5000:])
    print(name,flush=True)
    return p.stdout
def extract(label,candidate=False,metadata=False):
    path=BUILD/label
    with tarfile.open(OUT/'source.tar.gz') as t: t.extractall(path,filter='data')
    vm=path/'vm'
    if candidate:
        execution=vm/'src/experimental_swift_reactor/execution.rs'
        s=execution.read_text()
        s=s.replace('pub execution_header: Option<ReservationTicket>,','pub execution_header: Option<ReservationTicket>,\n    pub frame_cleanup: active_contract::FrameCleanupState,',1)
        s=s.replace('execution_header: None,','execution_header: None,\n            frame_cleanup: active_contract::FrameCleanupState::empty(),',1)
        # Explicit new positive permanent positions; existing formula terms
        # remain literal except for this additional checked_add.
        old='header.checked_add(value_operations::PERMANENT_BYTES)'
        assert s.count(old)==1
        s=s.replace(old,'match header.checked_add(value_operations::PERMANENT_BYTES) { Some(n) => n.checked_add(active_contract::PERMANENT_BYTES), None => None }')
        s+='\n#[path="active_contract.rs"] mod active_contract;\n'
        execution.write_text(s)
        fixture=vm/'src/experimental_swift_reactor/execution_tests.rs'
        fixture.write_text(fixture.read_text().replace('execution_header: None,','execution_header: None,\n            frame_cleanup: Default::default(),',1))
        proposal=(OUT/'inputs/proposed.rs').read_text().replace('// INVENTORY_INSERTION_POINT',render()).replace('// INVENTORY_PRINT_POINT',print_fields())
        (vm/'src/experimental_swift_reactor/active_contract.rs').write_text(proposal)
        # Narrow construction leaf; no Control/Kind fields become accessible.
        common=vm/'src/experimental/execution/mod.rs'
        common.write_text(common.read_text()+'''\nimpl Control {
    pub(crate) const fn function_entry(end: usize, height: usize, result: bool) -> Self {
        Self { kind: Kind::Function, start: 0, end, height, result }
    }
}\n''')
        with (vm/'src/experimental_swift_reactor/active_contract.rs').open('a') as f:
            f.write('\nfn function_control_witness(end:usize,height:usize,result:bool)->Control { Control::function_entry(end,height,result) }\n')
    if metadata:
        execution=vm/'src/experimental_swift_reactor/execution.rs'
        s='''\npub(super) fn af_existing_layout() {
    macro_rules! ty { ($t:ty) => { println!("AF_EXISTING {} {} {}",stringify!($t),size_of::<$t>(),std::mem::align_of::<$t>()); }; }
    ty!(SwiftExecutionState); ty!(SwiftReactorInstance); ty!(SwiftFrame); ty!(EntryGuard);
    ty!(ExecutionOperationPhase<'static>); ty!(SwiftFunctionCache); ty!(RuntimeControl);
    ty!(AccountedWasi); ty!(Control); ty!(SwiftFunctionPin); ty!(SwiftReleaseFailure);
    println!("AF_RESERVATION {} {} {}", execution_header_bytes().unwrap(), construction_bytes().unwrap(), value_operations::value_operation_bytes().unwrap());
    println!("AF_OFFSET state_values {} state_controls {} state_frames {} state_header {}",std::mem::offset_of!(SwiftExecutionState,values),std::mem::offset_of!(SwiftExecutionState,controls),std::mem::offset_of!(SwiftExecutionState,frames),std::mem::offset_of!(SwiftExecutionState,execution_header));
    #[cfg(feature="experimental-span-execution")] crate::experimental::execution::af_frozen_layout();
'''
        if candidate: s+='    active_contract::print_contract_layout();\n'
        s+='}\n#[cfg(test)] #[test] fn af_layout_only() { af_existing_layout(); }\n'
        execution.write_text(execution.read_text()+s)
        module=vm/'src/experimental_swift_reactor/mod.rs'
        module.write_text(module.read_text()+'\npub(crate) fn af_layout_bridge() {execution::af_existing_layout();}\n')
        lib=vm/'src/lib.rs'
        lib.write_text(lib.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn af_layout_bridge(){experimental_swift_reactor::af_layout_bridge();}\n')
        common=vm/'src/experimental/execution/mod.rs'
        common.write_text(common.read_text()+'''\n#[cfg(feature="experimental-span-execution")] pub(crate) fn af_frozen_layout() {
    println!("AF_FROZEN {} {} {} {}",size_of::<SpanInstance>(),size_of::<Frame>(),size_of::<Control>(),size_of::<SpanInstance>()-size_of::<FunctionCache>()+3*size_of::<ExecutionFailure>()+2*size_of::<CacheFailure>()+size_of::<crate::experimental::cache::DecodedInstruction>()+size_of::<Control>()+size_of::<ScalarReader>()+512);
}\n''')
        (vm/'examples').mkdir(exist_ok=True)
        (vm/'examples/af-layout.rs').write_text('fn main(){mixer_vm::af_layout_bridge();}\n')
    closure=manifest(vm)
    (OUT/(label+'-manifest.json')).write_bytes(encoded(closure))
    with tarfile.open(OUT/(label+'-source.tar.gz'),'w:gz') as t:
        for name in closure: t.add(vm/name,arcname='vm/'+name,recursive=False)
    variants.append(dict(label=label,manifest=label+'-manifest.json',treeSHA256=digest(encoded(closure)),archive=label+'-source.tar.gz',archiveSHA256=sha(OUT/(label+'-source.tar.gz'))))
    return vm,closure
def method(s,name):
    start=s.index('fn '+name+'('); end=s.index('{',start)+1; level=1
    while level:
        level+=(s[end]=='{')-(s[end]=='}'); end+=1
    return s[start:end]
try:
    revision=cmd('revision',['git','rev-parse','HEAD'],ROOT).strip()
    cmd('rustc-version',['rustc','-vV'],ROOT)
    cmd('cargo-version',['cargo','-V'],ROOT)
    cmd('python-version',['python3','--version'],ROOT)
    accepted=json.loads((ROOT/'verification/swift-control-macro-root-review/acceptance.json').read_text())
    assert digest(encoded(source))==accepted['candidateTreeSHA256'], ('live exact source is not accepted macro closure',digest(encoded(source)))
    (OUT/'accepted-macro-binding.json').write_bytes(encoded({k:accepted[k] for k in ['status','sourceRevision','candidateTreeSHA256','decision']}))
    plain={}
    for candidate in [False,True]:
        label='candidate' if candidate else 'baseline'
        plain[label]=extract(label,candidate)
    for config,flags in [('default',[]),('span',['--features','experimental-span-execution']),('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
        for profile in ['debug','release']:
            vm,closure=plain['candidate']; label='candidate-'+config+'-'+profile+'-check'
            cmd(label,['cargo','check','--locked','--offline','--lib',*flags,*(['--release'] if profile=='release' else [])],vm,BUILD/(label+'-target'),closure)
    for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
        for profile in ['debug','release']:
            exports={}; expanded={}
            for label in ['baseline','candidate']:
                vm,closure=plain[label]; name=label+'-'+config+'-'+profile
                args=['cargo','rustc','--locked','--offline','--lib',*flags,*(['--release'] if profile=='release' else []),'--','-Zunpretty=expanded']
                output=cmd(name+'-expansion',args,vm,BUILD/(name+'-expansion-target'),closure,bootstrap=True)
                if config=='all':
                    owner=output[output.index('impl SpanInstance {'):]
                    expanded[label]={n:method(owner,n) for n in ['enter','finish','cleanup','pop32','close_control','branch']}
                    (OUT/(name+'-frozen-methods.json')).write_bytes(encoded(expanded[label]))
                target=BUILD/(name+'-abi-target')
                cmd(name+'-abi-build',['cargo','build','--locked','--offline','--lib',*flags,*(['--release'] if profile=='release' else [])],vm,target,closure)
                dylib=target/('release' if profile=='release' else 'debug')/'libmixer_vm.dylib'
                output=cmd(name+'-abi-exports',['nm','-gU','-j',str(dylib)],vm,target,closure)
                exports[label]=sorted(x for x in output.splitlines() if x.startswith('_mixer_'))
                assert exports[label]
                abi.append(dict(label=name,exports=exports[label],binarySHA256=sha(dylib)))
            assert exports['baseline']==exports['candidate']
            if config=='all': assert expanded['baseline']==expanded['candidate']
            comparisons.append(dict(config=config,profile=profile,CExportsEqual=True,frozenMethodsEqual=config=='all'))
    for candidate in [False,True]:
        label='candidate' if candidate else 'baseline'
        vm,closure=extract(label+'-metadata',candidate,True)
        for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
            for profile in ['debug','release']:
                for mode in ['production','unit']:
                    name=label+'-'+config+'-'+profile+'-'+mode+'-metadata'
                    target=BUILD/(name+'-target')
                    args=['cargo',('build' if mode=='production' else 'test'),'--locked','--offline','--message-format=json',*flags,*(['--release'] if profile=='release' else [])]
                    args+=['--example','af-layout'] if mode=='production' else ['--lib','--no-run']
                    output=cmd(name+'-build',args,vm,target,closure)
                    artifacts=[]
                    for line in output.splitlines():
                        try: item=json.loads(line)
                        except ValueError: continue
                        if item.get('reason')=='compiler-artifact' and item.get('executable') and (mode=='production' or item.get('profile',{}).get('test')): artifacts.append(Path(item['executable']))
                    assert len(artifacts)==1,(name,artifacts)
                    binary=artifacts[0]
                    args=[str(binary)]
                    if mode=='unit':
                        identity='experimental_swift_reactor::execution::af_layout_only'
                        listing=cmd(name+'-list',[str(binary),'--list'],vm,target,closure)
                        assert identity+': test' in listing.splitlines()
                        args += [identity,'--exact','--nocapture','--test-threads=1']
                    output=cmd(name+'-run',args,vm,target,closure)
                    records=[]
                    for line in output.splitlines():
                        at=line.find('AF_')
                        if at>=0: records.append(line[at:])
                    assert records
                    layouts.append(dict(label=name,records=records,binarySHA256=sha(binary)))
    # Real downstream bins are separate crates and see no private proposal API.
    for name,body,error in [
        ('private-frame-phase','use mixer_vm::experimental_swift_reactor::execution::active_contract::FrameOperationPhase; fn main(){}','E0603'),
        ('private-control-constructor','use mixer_vm::experimental::execution::Control; fn main(){let _=Control::function_entry(0,0,false);}','E0603'),
        ('no-public-invoke','use mixer_vm::experimental_swift_reactor::SwiftReactorInstance; fn main(){}','E0432'),
    ]:
        vm,closure=extract(name,True)
        (vm/'src/bin').mkdir(exist_ok=True)
        (vm/'src/bin/af-privacy.rs').write_text(body+'\n')
        closure=manifest(vm)
        (OUT/(name+'-actual-manifest.json')).write_bytes(encoded(closure))
        cmd(name,['cargo','check','--locked','--offline','--all-features','--bin','af-privacy','--message-format=json'],vm,BUILD/(name+'-target'),closure,error=error)
        privacy.append(dict(name=name,error=error))
    status='contract-compiler-layout-abi-privacy-preflight-only'
finally:
    live_changed=[name for name,value in source.items() if sha(ROOT/'vm'/name)!=value]
    unchanged=not live_changed
    product_unchanged=not any(not name.startswith('tests/') for name in live_changed)
    receipt=dict(schema=1,status=status,sourceRevision=locals().get('revision'),sourceTreeSHA256=digest(encoded(source)),sourceFiles=len(source),sourceArchiveSHA256=sha(OUT/'source.tar.gz'),commands=commands,variants=variants,layouts=layouts,comparisons=comparisons,abi=abi,privacy=privacy,
        productVMUnchanged=unchanged,productImplementationUnchanged=product_unchanged,coordinatedLiveChangedPaths=live_changed,implementationApplied=False,guestExecution=False,frameExecution=False,nativeRuntime=False,semanticAcceptance=False,accountingCompletenessAccepted=False,
        model='gpt-6.1-sol',reasoningEffort='xhigh',scope='Private type/lifetime and positive inventory contract only; no active-frame runtime acceptance')
    (OUT/'receipt.json').write_bytes(encoded(receipt))
    print(str(OUT),flush=True)
    assert product_unchanged
