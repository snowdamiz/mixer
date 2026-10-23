#!/usr/bin/env python3
"""Exact derived-tree type/layout/borrow prerequisite, never a target runner."""
from pathlib import Path
import difflib, hashlib, json, os, re, shutil, subprocess, time

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
TREE=OUT/'tree/vm'
TOOL=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin')
ENV=dict(os.environ,PATH=str(TOOL)+':'+os.environ['PATH'],CARGO_TARGET_DIR=str(OUT/'build'))
OWNED=['src/experimental/execution/borrowed.rs','src/experimental/execution/tests.rs',
       'src/experimental_swift_reactor/execution.rs','src/experimental_swift_reactor/execution_tests.rs']
receipt={'schema':'mixer.swift-executor-layout-prerequisite.v1','commands':[],
    'scope':'Private chosen types/layouts and borrowed boundaries only; no interpreter, target instance/initialize/invoke, device, release or GA acceptance.'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value): (OUT/name).write_text(json.dumps(value,indent=2)+'\n')
def run(name,args,expected=0,env=None):
    start=time.time();p=subprocess.run(args,cwd=TREE,env=env or ENV,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    log=OUT/'logs'/f'{name}.log';log.parent.mkdir(exist_ok=True);log.write_text(p.stdout)
    r={'name':name,'argv':args,'cwd':str(TREE),'seconds':round(time.time()-start,3),'exit_code':p.returncode,'expected':expected,'log':str(log.relative_to(ROOT)),'sha256':digest(log)}
    receipt['commands'].append(r);save('receipt.partial.json',receipt)
    if (p.returncode==0)!=(expected==0):raise RuntimeError(f'{name}: exit {p.returncode}, see {log}')
    return p.stdout

def setup():
    TREE.mkdir(parents=True,exist_ok=True)
    inputs={}
    for p in sorted((ROOT/'vm').rglob('*')):
        if not p.is_file() or any(x in {'target','.git'} for x in p.relative_to(ROOT/'vm').parts):continue
        rel=p.relative_to(ROOT);inputs[str(rel)]=digest(p)
        q=TREE/p.relative_to(ROOT/'vm');q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
    receipt['revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    receipt['input_manifest_sha256']=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    save('input-manifest.json',{'revision':receipt['revision'],'files':inputs})
    changes={}
    p=TREE/'src/experimental/mod.rs';s=p.read_text();s=s.replace('#[cfg(feature = "experimental-span-execution")]\npub mod execution;', '#[cfg(feature = "experimental-span-execution")]\npub mod execution;\n#[cfg(all(feature = "experimental-swift-reactor", not(feature = "experimental-span-execution")))]\npub(crate) mod execution;');changes[p]=s
    p=TREE/'src/experimental/execution/mod.rs';s=p.read_text();s=s.replace('struct Control {','pub(crate) struct Control {').replace('struct Frame {','pub(crate) struct Frame {')
    # Only legacy dormant definitions receive dead-code allowances. Existing
    # algorithms and their Drop body remain byte-identical under the span flag.
    s=s.replace('impl SpanInstance {','#[cfg(feature = "experimental-span-execution")]\nimpl SpanInstance {').replace('impl Drop for SpanInstance {','#[cfg(feature = "experimental-span-execution")]\nimpl Drop for SpanInstance {')
    s=s.replace('use super::cache::{','#[cfg_attr(not(feature = "experimental-span-execution"), allow(unused_imports))]\nuse super::cache::{').replace('use std::mem::size_of;','#[cfg(feature = "experimental-span-execution")]\nuse std::mem::size_of;')
    for token in ['const PAGE:','const CHUNK:','enum Kind {','pub enum ExecutionFailureKind {','pub(crate) struct Control {','pub(crate) struct Frame {','pub struct SpanInstance {','fn width(','fn unreachable_failure(','struct ScalarReader','impl ScalarReader','fn initializer(']:
        s=s.replace(token,'#[cfg_attr(not(feature = "experimental-span-execution"), allow(dead_code))]\n'+token)
    s+='\n#[cfg(feature = "experimental-swift-reactor")]\npub(crate) mod borrowed;\n';changes[p]=s
    p=TREE/'src/experimental_swift_reactor/mod.rs';s=p.read_text();s+='\nmod execution;\n#[cfg(test)]\nmod execution_tests;\n';changes[p]=s
    patch=''
    for p,s in changes.items():
        rel=p.relative_to(TREE);original=(ROOT/'vm'/rel).read_text();patch+=''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/vm/'+str(rel),tofile='b/vm/'+str(rel)));p.write_text(s)
    (OUT/'root-wiring.patch').write_text(patch)
    # Production probe is a derived-only external executable. Its sole exported
    # hook prints metadata; this hook does not enter any runnable owner route.
    t=(TREE/'src/experimental_swift_reactor/execution_tests.rs').read_text()
    start=t.index('fn swift_executor_layout_all_eight_phase_shapes()');body_start=t.index('{',start);depth=1;i=body_start+1
    while depth:
        depth+=(t[i]=='{')-(t[i]=='}');i+=1
    imports=t[:t.index('#[test]')].replace('use super::allocation_tests::measure;','').replace('use super::allocation_tests::measure;\n','')
    probe='#![allow(unused_imports)] // Derived metadata probe only.\n'+imports+'pub fn production_layout() '+t[body_start:i]+'\n'+(OUT/'final-boundary-probe.rs').read_text()
    (TREE/'src/experimental_swift_reactor/production_layout.rs').write_text(probe)
    p=TREE/'src/experimental_swift_reactor/mod.rs';p.write_text(p.read_text()+'\nmod production_layout;\n#[doc(hidden)]\npub fn executor_layout_probe_only() { production_layout::production_layout(); production_layout::boundary_shapes(); }\n')
    p=TREE/'examples/executor_layout_probe.rs';p.parent.mkdir(exist_ok=True);p.write_text('fn main() { mixer_vm::experimental_swift_reactor::executor_layout_probe_only(); }\n')
    save('overlay-manifest.json',{str(p.relative_to(TREE)):digest(p) for p in sorted(TREE.rglob('*')) if p.is_file() and 'target' not in p.parts})
    # Complete exact source overlay, including metadata-only executable hook.
    patch=''
    for p in sorted(TREE.rglob('*.rs')):
        if 'target' in p.parts:continue
        rel=p.relative_to(TREE);base=ROOT/'vm'/rel
        original=base.read_text() if base.exists() else ''
        if original!=p.read_text():patch+=''.join(difflib.unified_diff(original.splitlines(True),p.read_text().splitlines(True),fromfile='a/vm/'+str(rel),tofile='b/vm/'+str(rel)))
    (OUT/'measurement-overlay.patch').write_text(patch)

def main():
    setup()
    for name,args in [('rustc-version',['rustc','-Vv']),('cargo-version',['cargo','-V']),('host',['uname','-a']),('python-version',['python3','--version'])]:run(name,args)
    base=['cargo','test','--locked','--manifest-path',str(TREE/'Cargo.toml')]
    for profile in ['', '--release']:
        suffix='release' if profile else 'debug';opts=[profile] if profile else []
        run('layout-unit-'+suffix,base+opts+['--lib','--features','experimental-swift-reactor','swift_executor_layout','--','--nocapture','--test-threads=1'])
        run('layout-frozen-'+suffix,base+opts+['--lib','--features','experimental-swift-reactor','frozen_executor_layout_prerequisite','--','--nocapture','--test-threads=1'])
        run('layout-production-'+suffix,['cargo','run','--locked','--manifest-path',str(TREE/'Cargo.toml')]+opts+['--features','experimental-swift-reactor','--example','executor_layout_probe'])
    # All requested feature combinations; preexisting runtime and cache tests
    # remain meaningful. External legacy tests are collected separately below.
    features=[('neither',''),('span','experimental-span-execution'),('swift','experimental-swift-reactor'),('swift-cache','experimental-swift-reactor,experimental-function-cache'),('swift-span','experimental-swift-reactor,experimental-span-execution'),('all','ALL')]
    for suffix,profile in [('debug',[]),('release',['--release'])]:
        for label,f in features:
            flags=['--all-features'] if f=='ALL' else ['--features',f] if f else []
            run(f'features-{label}-{suffix}',base+profile+['--lib']+flags)
        run('legacy-execution-'+suffix,base+profile+['--features','experimental-span-execution','--test','span_execution','--test','span_execution_allocations','--test','span_execution_oracle'])
    # Compile/privacy probes are separate exact overlays, not runtime tests.
    cases={
      'reject_pin_clone':('fn probe(p: super::cache::SwiftFunctionPin) { let _ = p.clone(); }','E0599'),
      'reject_parts_double_mut':('fn probe(p: &mut ExecutionParts<\'_, SwiftMode>) { let a=&mut *p.cache; let b=&mut *p.cache; std::hint::black_box((a,b)); }','E0499'),
      'reject_wasi_shared_during_mut':('fn probe(op: &mut SwiftExecutionOperation<\'_>) { let a=&*op.wasi; let b=&mut *op.wasi; std::hint::black_box((a,b)); }','E0502'),
      'reject_view_across_cache_mut':('fn probe(c: &mut SwiftFunctionCache,p:&SwiftFunctionPin,q:SwiftFunctionPin,o:&mut SwiftExecutionOperation<\'_>) { let v=c.view(p,o.control,Some(&*o.wasi)).unwrap(); let r=c.release(q,o.control,Some(&*o.wasi)); std::hint::black_box((v,r)); }','E0502'),
      'reject_borrow_escape':('fn probe(p: &mut ExecutionOperationPhase<\'_>) -> &\'static mut RuntimeControl { with_cache_operation(p,|_,o| o.control) }','lifetime may not live long enough'),
    }
    p=TREE/'src/experimental_swift_reactor/execution_tests.rs';original=p.read_text();outcomes=[]
    for profile,opts in [('debug',[]),('release',['--release'])]:
        for name,(code,diagnostic) in cases.items():
            probe=OUT/(name+'.rs');probe.write_text(code+'\n');p.write_text(original+'\n'+code+'\n')
            output=run(name+'-'+profile,base+opts+['--lib','--no-run','--features','experimental-swift-reactor'],expected=1)
            if diagnostic not in output:raise RuntimeError(f'{name}: missing {diagnostic}')
            outcomes.append({'name':name,'profile':profile,'source_sha256':digest(probe),'expected_diagnostic':diagnostic,'rejected':True})
        p.write_text(original)
        for name,code in [
           ('reject_public_swift_owner','use mixer_vm::experimental_swift_reactor::execution::SwiftReactorInstance; fn main() {}'),
           ('reject_public_swift_only_legacy','use mixer_vm::experimental::execution::SpanInstance; fn main() {}')]:
            p=TREE/'examples/privacy_probe.rs';p.write_text(code+'\n');(OUT/(name+'.rs')).write_text(code+'\n')
            output=run(name+'-'+profile,['cargo','check','--locked','--manifest-path',str(TREE/'Cargo.toml')]+opts+['--features','experimental-swift-reactor','--example','privacy_probe'],expected=1)
            if 'E0603' not in output:raise RuntimeError(f'{name}: missing E0603')
            outcomes.append({'name':name,'profile':profile,'expected_diagnostic':'E0603','rejected':True})
            p.unlink()
        p=TREE/'src/experimental_swift_reactor/execution_tests.rs'
    save('privacy-outcomes.json',outcomes)
    for name,flags in [('minimal',['--features','experimental-swift-reactor']),('combined',['--features','experimental-swift-reactor,experimental-span-execution'])]:
        run('clippy-'+name,['cargo','clippy','--locked','--manifest-path',str(TREE/'Cargo.toml'),'--lib']+flags+['--','-D','warnings'])
    run('owned-rustfmt-check',['rustfmt','--check','--edition','2021']+[str(ROOT/'vm'/p) for p in OWNED])
    # Source preservation proof: full input hashes, including unchanged frozen
    # owner files, must still match after all subprocesses.
    inputs=json.loads((OUT/'input-manifest.json').read_text())['files']
    receipt['input_bytes_unchanged']=all(digest(ROOT/p)==sha for p,sha in inputs.items())
    if not receipt['input_bytes_unchanged']:raise RuntimeError('source changed during collection; recollect against current exact inputs')
    receipt['owned_source_sha256']={str(Path('vm')/p):digest(ROOT/'vm'/p) for p in OWNED}
    receipt['status']='complete';save('receipt.json',receipt)

if __name__=='__main__':main()
