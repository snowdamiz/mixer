#!/usr/bin/env python3
"""Bounded host data/compile-only controls; all mutations under this packet."""
from pathlib import Path
import datetime,hashlib,json,os,re,shutil,subprocess,sys,tempfile,time
OUT=Path(__file__).resolve().parent
SOURCE=OUT/'inputs/accepted-source/vm'
RUSTC=Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
def manifest(src):
    members=[{'path':str(p.relative_to(src)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(src.rglob('*')) if p.is_file()]
    return {'members':members,'member_count':len(members),'tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest()}

PATCHES={
'src/experimental_swift_reactor/cache/initial_profile_v1.rs': [
    ("struct InitialProfileBorrowV1<'a> {","pub(crate) struct InitialProfileBorrowV1<'a> {"),
    ('\n#[repr(u32)]\nenum ProfileAdmissionFailureV1', '''
impl InitialProfileBorrowV1<'_> {
    pub(crate) fn preparation_proof_v1(&self)->&ValidatedSwiftReactor { self.cache.proof() }
    pub(crate) fn preparation_selected_v1(&self)->Option<&super::super::retained_profile_loader_v1::LoaderProvenanceV1> {
        self.cache.adopted.selected_provenance()
    }
}
#[repr(u32)]
enum ProfileAdmissionFailureV1''')],
'src/experimental_swift_reactor/retained_profile_loader_v1.rs': [
    ('pub(super) struct LoaderProvenanceV1 {','pub(crate) struct LoaderProvenanceV1 {')],
}
APPENDS={
'src/experimental_swift_reactor/cache.rs': '\npub(crate) use initial_profile_v1::InitialProfileBorrowV1;\n',
'src/experimental_swift_reactor/mod.rs': '\npub(crate) use cache::InitialProfileBorrowV1;\npub(crate) use retained_profile_loader_v1::LoaderProvenanceV1;\n',
'src/experimental/account.rs': '''
impl<T:Copy> Buffer<T> {
    pub(super) fn preparation_inventory_v1(&self)->(usize,usize,usize,usize,Resource) {
        (self.values.len(),self.values.capacity(),std::mem::size_of::<T>(),self.charged,self.category)
    }
}
''',
'src/experimental_swift_reactor/retained_profile_loader_v1.rs': '''
impl LoaderProvenanceV1 {
    pub(crate) fn preparation_fields_v1(&self)->(&SwiftValidationBudget,u64,[[u8;32];6],[[u8;64];4]) {
        (&self.validation_budget,self.source_extent,
         [self.source,self.manifest,self.build,self.session,self.executable,self.nonce],
         self.identities.map(FileIdentityV1::encode))
    }
}
''',
'src/experimental/swift.rs': '\npub(crate) mod snapshot_export_preparation_v1 { include!(env!("MIXER_SNAPSHOT_BRIDGE")); }\n',
}
BASE='crate::experimental_swift_reactor::InitialProfileBorrowV1'
API='crate::experimental::swift::snapshot_export_preparation_v1'
CASES={
'positive': (None,f'''fn positive(g:&{BASE}<'_>,f:&mut std::fs::File) {{
 let _={API}::borrow_logical_snapshot_v1(g);
 let _={API}::export_signature_v1(g,f);
 let _signature: for<'a,'b> fn(&'a {BASE}<'b>,&mut std::fs::File)->Result<{API}::PreparationObservationV1,{API}::PreparationErrorV1>={API}::export_signature_v1;
}}'''),
'raw_proof_alternate': ('E0308',f'''fn forbidden(p:&crate::experimental_swift_reactor::ValidatedSwiftReactor,f:&mut std::fs::File) {{let _={API}::export_signature_v1(p,f);}}'''),
'foreign_source_argument': ('E0061',f'''fn forbidden(g:&{BASE}<'_>,p:&crate::experimental_swift_reactor::ValidatedSwiftReactor,f:&mut std::fs::File) {{let _={API}::export_signature_v1(g,p,f);}}'''),
'digest_mint': ('E0308',f'''fn forbidden(f:&mut std::fs::File) {{let _={API}::export_signature_v1(&[0u8;32],f);}}'''),
'boolean_mint': ('E0308',f'''fn forbidden(f:&mut std::fs::File) {{let _={API}::export_signature_v1(&true,f);}}'''),
'callback': ('E0308',f'''fn forbidden(g:&{BASE}<'_>) {{let _={API}::export_signature_v1(g,|_|Ok(0usize));}}'''),
'second_guard_literal': ('private',f'''fn forbidden(g:&{BASE}<'_>) {{let _={BASE} {{cache:g.cache,control:g.control,wasi:g.wasi,scalars:g.scalars}};}}'''),
'guard_clone': ('E0599',f'''fn forbidden(g:{BASE}<'_>) {{let _=g.clone();}}'''),
'view_source_escape': ('E0515',f'''fn forbidden<'a>(g:{BASE}<'a>)->&'a[u8] {{ match {API}::borrow_logical_snapshot_v1(&g) {{Ok(v)=>v.source(),Err(_)=>panic!()}} }}'''),
'view_prevents_guard_move': ('E0505',f'''fn forbidden(g:{BASE}<'_>) {{if let Ok(v)={API}::borrow_logical_snapshot_v1(&g) {{drop(g);let _=v.source();}}}}'''),
'view_literal': ('E0451',f'''fn forbidden(p:&crate::experimental_swift_reactor::ValidatedSwiftReactor,s:&crate::experimental_swift_reactor::LoaderProvenanceV1) {{let _={API}::LogicalSnapshotViewV1 {{proof:p,provenance:s}};}}'''),
'proof_mutation': ('E0594',f'''fn forbidden(g:&{BASE}<'_>) {{if let Ok(v)={API}::borrow_logical_snapshot_v1(g) {{v.source()[0]=0;}}}}'''),
}


+for _name,_owner in [('cache_mutation_while_view','cache'),('control_mutation_while_view','control')]:
+    CASES[_name]=('E0502',f'''use super::*;
+fn forbidden(cache:&mut SwiftFunctionCache,control:&mut RuntimeControl) {{
+ let scalars=InitialProfileScalarsV1 {{source_extent:0,type_count:0,slot_limit:0,pin_limit:0,initial_nonce:0,cache_base:0,cache_capacity:0,entry_limit:0}};
+ let g=InitialProfileBorrowV1 {{cache,control,wasi:None,scalars}};
+ let v={API}::borrow_logical_snapshot_v1(&g);
+ let _mutable=&mut *{_owner};
+ if let Ok(v)=v {{let _=v.source();}}
+}}
+''')

def main():
    attempt=1+len(list((OUT/'commands').glob('attempt-*'))); logs=OUT/'commands'/f'attempt-{attempt}'
    scratch=Path(tempfile.mkdtemp(prefix='preparation-compile-',dir=OUT));receipts=[]
    env=os.environ.copy();env['TMPDIR']=str(scratch/'tmp');Path(env['TMPDIR']).mkdir()
    env['MIXER_SNAPSHOT_BRIDGE']=str(OUT/'prototype/validator_bridge.rs')
    def run(name,argv,expected=None,timeout=60):
        folder=logs/name;folder.mkdir(parents=True);start=time.monotonic()
        with (folder/'stdout').open('wb') as out,(folder/'stderr').open('wb') as err:
            child=subprocess.Popen([str(v) for v in argv],cwd=OUT,env=env,stdout=out,stderr=err)
            killed=None
            while True:
                try:code=child.wait(timeout=.05);break
                except subprocess.TimeoutExpired:
                    if time.monotonic()-start>timeout:killed='timeout'
                    if (folder/'stdout').stat().st_size+(folder/'stderr').stat().st_size>8*1024*1024:killed='output cap'
                    if killed:child.kill();child.wait();code=124;break
        stderr=(folder/'stderr').read_text(errors='replace')
        codes=set(re.findall(r'error\[(E[0-9]+)\]',stderr))
        allowed={'E0616','E0451'} if expected=='private' else ({expected} if expected else set())
        met=(code==0) if expected is None else (code!=0 and expected in stderr and bool(codes) and codes <= allowed)
        receipt={'name':name,'source_inputs':{n:sha(OUT/n) for n in ['format_model.py','test_format_model.py','run_preparation.py','prototype/validator_bridge.rs']},'diagnostic_codes':sorted(codes),'environment':{k:env[k] for k in ['CARGO_MANIFEST_DIR','MIXER_SNAPSHOT_BRIDGE','MIXER_SNAPSHOT_CASE'] if k in env},'argv':[str(v) for v in argv],'cwd':str(OUT),'exit_code':code,'expected_diagnostic':expected,
                 'expectation_met':met,'timeout_seconds':timeout,'output_byte_cap':8*1024*1024,
                 'elapsed_seconds':time.monotonic()-start,'killed':killed,'child_reaped':True,
                 'stdout_sha256':sha(folder/'stdout'),'stderr_sha256':sha(folder/'stderr')}
        write(folder/'receipt.json',receipt);receipts.append(receipt);return receipt
    try:
        baseline=manifest(SOURCE);assert baseline['member_count']==144 and baseline['tree_sha256']=='9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb'
        write(OUT/f'input-source-attempt-{attempt}.json',baseline)
        run('python-version',[sys.executable,'--version']);run('rustc-version',[RUSTC,'-vV'])
        run('format-model',[sys.executable,'-B','-m','unittest','-v','test_format_model.py'])
        variant=scratch/'variant';shutil.copytree(SOURCE,variant)
        delta=[]
        for rel,replacements in PATCHES.items():
            p=variant/rel;s=p.read_text()
            for before,after in replacements:
                assert s.count(before)==1,rel;s=s.replace(before,after)
            p.write_text(s)
        for rel,append in APPENDS.items():
            p=variant/rel;p.write_text(p.read_text()+append)
        for rel in sorted(set(PATCHES)|set(APPENDS)):
            delta.append({'path':rel,'original_sha256':sha(SOURCE/rel),'prototype_sha256':sha(variant/rel),'original_unchanged':True})
        common=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','--crate-type','lib','--emit=metadata','-C','overflow-checks=yes']
        for feature in FEATURES:common+=['--cfg',f'feature="{feature}"']
        env['CARGO_MANIFEST_DIR']=str(variant)
        casesdir=OUT/'compile-cases';casesdir.mkdir(exist_ok=True)
        for name,(_,code) in CASES.items():(casesdir/f'{name}.rs').write_text(code+'\n')
        src=variant/'src/lib.rs';original=src.read_text()
        initial=variant/'src/experimental_swift_reactor/cache/initial_profile_v1.rs';original_initial=initial.read_text()
        for mode,opt in [('debug','0'),('optimized','3')]:
            for name,(expected,code) in CASES.items():
                src.write_text(original);initial.write_text(original_initial)
                destination=initial if name.endswith('_while_view') else src
                destination.write_text(destination.read_text()+'\n#[allow(dead_code)] mod snapshot_export_preparation_case { include!(env!("MIXER_SNAPSHOT_CASE")); }\n')
                env['MIXER_SNAPSHOT_CASE']=str(casesdir/f'{name}.rs')
                command=common+['-C',f'opt-level={opt}',src,'-o',scratch/'case.rmeta']
                actual=manifest(variant)
                write(OUT/'compiler-variants'/f'attempt-{attempt}'/f'{mode}-{name}.json',{'variant':actual,'baseline_tree_sha256':baseline['tree_sha256'],'bridge_sha256':sha(OUT/'prototype/validator_bridge.rs'),'case_sha256':sha(casesdir/f'{name}.rs'),'configuration':'ordinary-production lib; no --test or host cfg','product_integration':False})
                run(f'{mode}-{name}',command,expected)
        write(OUT/f'prototype-delta-attempt-{attempt}.json',{'modified_source_paths':delta,'lib_test_append_only':True,'guard_constructor_or_original_constructor_body_changed':False,'baseline_source_members':144,'baseline_layout_identities':201,'new_layout_or_admission_measured':False})
    finally:
        shutil.rmtree(scratch)
        result={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_revision_context':'606c42876855897c315ee279dcd38fabaeb561ad','source_tree_sha256':'9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb',
            'python':sys.version,'python_executable_sha256':sha(Path(sys.executable)),
            'rustc':str(RUSTC),'rustc_sha256':sha(RUSTC),'runner_sha256':sha(Path(__file__)),
            'commands':len(receipts),'passed_expectations':sum(r['expectation_met'] for r in receipts),
            'failed_expectations':[r['name'] for r in receipts if not r['expectation_met']],
            'compiler_configurations':['ordinary-production debug','ordinary-production optimized'],
            'scope':'data grammar and private signature feasibility only; no exporter product implementation',
            'cleanup':{'owned_scratch_removed':not scratch.exists(),'owned_children_reaped':all(r['child_reaped'] for r in receipts),'compiler_products_retained':False,'native_device_simulator_emulator_UI_capture_process_inventory':False}}
        write(OUT/f'receipt-attempt-{attempt}.json',result)
        print(json.dumps(result))
    return 0 if all(r['expectation_met'] for r in receipts) else 1
if __name__=='__main__':sys.exit(main())
