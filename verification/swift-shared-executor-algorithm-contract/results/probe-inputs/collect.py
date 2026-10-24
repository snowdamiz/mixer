#!/usr/bin/env python3
"""Compile isolated source overlays; execute function-binding/layout tests only."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = HERE / 'build' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
RUN.mkdir(parents=True, exist_ok=False)
OUT = HERE / 'results'
OUT.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
blobsha = lambda b: hashlib.sha256(b).hexdigest()
jsonbytes = lambda v: (json.dumps(v, sort_keys=True, indent=2)+'\n').encode()
source_files = [ROOT/'vm/Cargo.toml', ROOT/'vm/Cargo.lock'] + sorted((ROOT/'vm/src').rglob('*')) + sorted((ROOT/'vm/tests').rglob('*')) + sorted((ROOT/'vm/include').rglob('*'))
source_files = [p for p in source_files if p.is_file()]
source = {str(p.relative_to(ROOT/'vm')): sha(p) for p in source_files}
(OUT/'source-manifest.json').write_bytes(jsonbytes(source))
archive = OUT/'source.tar.gz'
with tarfile.open(archive, 'w:gz') as tf:
    for p in source_files: tf.add(p, arcname=str(p.relative_to(ROOT)), recursive=False)
probe_inputs = {p.name: sha(p) for p in [HERE/'common_probe.rs', HERE/'swift_probe.rs', HERE/'collect.py']}
(OUT/'probe-inputs').mkdir()
for name in probe_inputs:
    shutil.copy2(HERE/name, OUT/'probe-inputs'/name)
base_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
commands=[]; variants=[]; layout_outputs={}

env = dict(os.environ, PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
def verify(path, manifest):
    observed = {str(p.relative_to(path)):sha(p) for p in path.rglob('*') if p.is_file()}
    assert observed == manifest, 'closure changed'
def run(name, args, cwd, target=None, expected=0, diagnostic=None, derived=None):
    if derived: verify(cwd, derived)
    penv=dict(env)
    if target: penv['CARGO_TARGET_DIR']=str(target)
    p=subprocess.run(args,cwd=cwd,env=penv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
    log=OUT/(name+'.log');log.write_bytes(p.stdout)
    if derived: verify(cwd, derived)
    text=p.stdout.decode(errors='replace')
    commands.append(dict(name=name,argv=args,cwd=str(cwd),target=str(target) if target else None,
        exit=p.returncode,log=str(log.relative_to(ROOT)),sha256=sha(log),
        sourceBeforeAfterVerified=derived is not None))
    print(name,p.returncode,flush=True)
    if expected==0: assert p.returncode==0,text[-5000:]
    else:
        assert p.returncode!=0,text[-5000:]
        assert diagnostic in text,text[-5000:]
    return text

negative = {
 'view-cache-mutation': '''\nfn rejected_live_view(cache: &mut SwiftFunctionCache, pin: &SwiftFunctionPin,
    owned: SwiftFunctionPin, operation: &mut SwiftExecutionOperation<'_>) {
    let view = <SwiftMode as AlgorithmMode>::view(cache, pin, operation).unwrap();
    let _released = <SwiftMode as AlgorithmMode>::release(cache, owned, operation);
    std::hint::black_box(view.instructions.len());
}\n''',
 'view-static-escape': '''\nfn rejected_view_escape(cache: &SwiftFunctionCache, pin: &SwiftFunctionPin,
    operation: &mut SwiftExecutionOperation<'_>) -> FunctionView<'static> {
    <SwiftMode as AlgorithmMode>::view(cache, pin, operation).unwrap()
}\n''',
 'wasi-dispatch-during-cache-phase': '''\nfn rejected_dispatch(cache: &mut SwiftFunctionCache, operation: &mut SwiftExecutionOperation<'_>,
    function: crate::experimental_wasi::WasiFunction, memory: &mut [u8]) {
    let phase = cache.prepare_operation(&mut *operation.control, Some(&*operation.wasi), operation.cursor).unwrap();
    let _ = operation.wasi.dispatch(operation.control, function, &[], memory, operation.cursor);
    let _ = phase.complete(());
}\n''',
}
try:
    run('rustc-version',['rustc','-vV'],ROOT)
    run('cargo-version',['cargo','-V'],ROOT)
    for name, feature, suffix in [
        ('all-positive','--all-features',''),
        ('swift-positive','experimental-swift-reactor',''),
        ('base-layout','experimental-swift-reactor',''),
        *[(n,'experimental-swift-reactor',s) for n,s in negative.items()],
    ]:
        dest=RUN/name/'vm'
        with tarfile.open(archive) as tf:
            tf.extractall(RUN/name, filter='data')
        verify(dest,source)
        if name != 'base-layout':
            borrowed=dest/'src/experimental/execution/borrowed.rs'
            borrowed.write_text(borrowed.read_text()+'\n#[path = "algorithm_contract_probe.rs"]\npub(crate) mod algorithm_contract_probe;\n')
            shutil.copy2(OUT/'probe-inputs/common_probe.rs',dest/'src/experimental/execution/algorithm_contract_probe.rs')
            swift=dest/'src/experimental_swift_reactor/execution.rs'
            swift.write_text(swift.read_text()+'\n'+(OUT/'probe-inputs/swift_probe.rs').read_text()+suffix)
        derived={str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file()}
        (OUT/(name+'-manifest.json')).write_bytes(jsonbytes(derived))
        variants.append(dict(name=name,sourceTreeDigest=blobsha(jsonbytes(derived)),
            manifest=str((OUT/(name+'-manifest.json')).relative_to(ROOT)),
            overlay='none' if name=='base-layout' else 'append shared module; append Swift probe'+('; negative function' if suffix else ''),
            features=feature))
        flags=['--all-features'] if feature=='--all-features' else ['--features',feature]
        if name=='base-layout':
            output=run(name,['cargo','test','--locked','--offline','--lib',*flags,
                'frozen_executor_layout_prerequisite','--','--nocapture'],dest,
                RUN/name/'layout-target',derived=derived)
            assert 'test result: ok. 1 passed;' in output
            layout_outputs['base']=[line for line in output.splitlines() if line.startswith(('layout ', 'offset '))]
        elif suffix:
            diag='E0502' if name=='view-cache-mutation' else ('lifetime may not live long enough' if name=='view-static-escape' else 'E0499')
            run(name,['cargo','check','--locked','--offline','--lib',*flags],dest,
                RUN/name/'target',1,diag,derived)
        else:
            for profile in ['debug','release']:
                target=RUN/name/(profile+'-target')
                args=['cargo','test','--locked','--offline','--lib',*flags]
                if profile=='release': args+=['--release']
                output=run(name+'-'+profile,args+['shared_algorithm_contract','--','--nocapture'],
                    dest,target,derived=derived)
                expected=4 if name=='all-positive' else 3
                assert 'test result: ok. '+str(expected)+' passed;' in output,output[-2000:]
                if name=='swift-positive' and profile=='debug':
                    output=run('derived-frozen-layout',['cargo','test','--locked','--offline','--lib',*flags,
                        'frozen_executor_layout_prerequisite','--','--nocapture'],dest,target,derived=derived)
                    assert 'test result: ok. 1 passed;' in output
                    layout_outputs['derived']=[line for line in output.splitlines() if line.startswith(('layout ', 'offset '))]
    assert layout_outputs['base'] == layout_outputs['derived'] and layout_outputs['base']
    assert all(sha(ROOT/'vm'/p)==h for p,h in source.items()), 'live VM source drifted'
    assert all(sha(HERE/p)==h for p,h in probe_inputs.items()), 'probe input drifted'
    (OUT/'frozen-layout-comparison.json').write_bytes(jsonbytes(dict(equal=True,lines=layout_outputs['base'])))
    status='passed-type-and-borrow-probes-only'
except Exception:
    status='failed'
    raise
finally:
    (OUT/'receipt.json').write_bytes(jsonbytes(dict(schema='mixer-shared-algorithm-contract-probe-v1',
        observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        revision=base_revision,
        finalRevision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        status=status,scope='Derived type-only compilation; only bindings/layout tests executed. No interpreter/target/device.',
        baseSourceTreeDigest=blobsha(jsonbytes(source)),archiveSHA256=sha(archive),
        sourceManifestSHA256=sha(OUT/'source-manifest.json'),probeInputs=probe_inputs,
        originalVMSourceBeforeAfterVerified=all(sha(ROOT/'vm'/p)==h for p,h in source.items()),
        dirtyStatus=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
        variants=variants,commands=commands)))
