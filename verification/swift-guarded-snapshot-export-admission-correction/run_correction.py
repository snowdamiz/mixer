"""Fresh host-only source/signature proofs; never imports or replays frozen runners."""
import hashlib,json,os,pathlib,re,shutil,subprocess,sys,tempfile,time
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent.parent
ACCEPTED=HERE.parent/'swift-guarded-snapshot-export-preparation/inputs/accepted-source/vm'
ORIGINAL=HERE.parent/'swift-guarded-snapshot-export-admission-design'
REVIEW=HERE.parent/'swift-guarded-snapshot-export-admission-independent/actual-review'
SELECTION=HERE.parent/'swift-semantic-adapter-root-review/guarded-snapshot-export-admission-correction-selection.json'
RUSTC='/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc'
FEATURES=['experimental-swift-reactor','experimental-swift-wasi','experimental-stream-validation','experimental-function-cache']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def command(name,argv,cwd,env=None,timeout=120):
    folder=HERE/'commands'/name;folder.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    clean={k:v for k,v in os.environ.items() if not k.startswith('MIXER_LOADER_')}
    clean['PYTHONDONTWRITEBYTECODE']='1'
    if env:clean.update(env)
    try:
        child=subprocess.run(argv,cwd=cwd,env=clean,capture_output=True,timeout=timeout,check=False)
        out,err,code=child.stdout,child.stderr,child.returncode
    except subprocess.TimeoutExpired as exc:
        out,err,code=exc.stdout or b'',exc.stderr or b'',-999
    (folder/'stdout').write_bytes(out);(folder/'stderr').write_bytes(err)
    receipt=dict(argv=argv,cwd=str(cwd),environment_overrides=env or {},exit_code=code,
        elapsed_seconds=time.monotonic()-started,timeout_seconds=timeout,child_reaped=True,
        stdout_sha256=digest(folder/'stdout'),stderr_sha256=digest(folder/'stderr'))
    dump(folder/'receipt.json',receipt)
    return receipt,out.decode(errors='replace'),err.decode(errors='replace')
def checkseal(base,expected):
    assert digest(base/'seal.json')==expected
    seal=json.loads((base/'seal.json').read_text());total=0
    for member in seal['members']:
        p=base/member['path'];assert p.stat().st_size==member['bytes'] and digest(p)==member['sha256'];total+=member['bytes']
    assert len(seal['members'])==seal['member_count'] and total==seal['bytes']
    return dict(path=str(base.relative_to(ROOT)),seal_sha256=expected,members=len(seal['members']),bytes=total)
def inventory(tree):
    return [dict(path=str(p.relative_to(tree)),bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(tree.rglob('*')) if p.is_file()]
def llvm_words(ll,name,count,folder):
    definition=next(line for line in ll.read_text().splitlines() if line.startswith('@'+name+' '))
    (folder/(name+'.llvm.txt')).write_text(definition+'\n')
    encoded=re.search(r'c"(.*?)"',definition)
    assert encoded,definition
    value=encoded.group(1);raw=bytearray();i=0
    while i<len(value):
        if value[i]=='\\':raw.append(int(value[i+1:i+3],16));i+=3
        else:raw.append(ord(value[i]));i+=1
    assert len(raw)==count*8
    return [int.from_bytes(raw[i:i+8],'little') for i in range(0,len(raw),8)]
def main():
    assert digest(SELECTION)=='df99aba0e0abe8cdb5a635a3ad77a058f972c907af1d604f1879da25506676ff'
    frozen=[checkseal(ORIGINAL,'b60d1ba0790076b35b6df30dd8df407486f89144e6914f40d2d0d55e4e20e1f5'),
        checkseal(REVIEW,'4356c1f7b8adde46dca0b661171d9ad935773a3ecfe47ac153581b2fb4a3e896')]
    source_manifest=ACCEPTED.parents[1]/'source-manifest.json'
    expected=json.loads(source_manifest.read_text())
    for member in expected['members']:
        p=ACCEPTED/member['path'];assert p.stat().st_size==member['bytes'] and digest(p)==member['sha256']
    assert len(inventory(ACCEPTED))==144
    dump(HERE/'input-custody.json',dict(frozen=frozen,selection_sha256=digest(SELECTION),
        accepted_manifest_sha256=digest(source_manifest),accepted_source_tree='9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb',
        accepted_members=144,frozen_commands_replayed=False,active_encoder_or_independent_read=False))
    for name,argv in [('rustc-version',[RUSTC,'--version','--verbose']),('python-version',[sys.executable,'--version']),
        ('source-revision',['git','rev-parse','HEAD'])]:
        receipt,_,err=command(name,argv,ROOT);assert receipt['exit_code']==0,err
    scratch=pathlib.Path(tempfile.mkdtemp(prefix='bounded-source-',dir=HERE));results=[]
    try:
        tree=scratch/'vm';shutil.copytree(ACCEPTED,tree)
        control=tree/'src/experimental_swift_reactor/control.rs'
        initial=tree/'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
        original_control=control.read_text()
        start=original_control.index('    pub(super) fn adopt_body(')
        end=original_control.index('    fn check_budget(',start)
        copied=original_control[start:end].replace('fn adopt_body(','fn correction_probe_adopt_body_v1(',1)
        copied=copied.replace('        cancellation: Cancellation,\n','        cancellation: Cancellation,\n        boundary:CorrectionBoundaryV1,\n        storage:CorrectionEarlyStorageV1,\n',1)
        copied=copied.replace(') -> Result<(Self, AdoptedProof), SwiftRunFailure> {',') -> CorrectionCoreReturnV1 {',1)
        copied=copied.replace('let construction = foundation_construction_bytes().ok_or_else(|| {',
            'let construction = foundation_construction_bytes().and_then(|base|base.checked_add(size_of::<CorrectionPreScopePlacesV1>())).ok_or_else(|| {',1)
        copied=copied.replace('            control.check(cursor)\n        })();',
            '''            // Test-only event at the exact original post-Construction final check.
            match boundary {
                CorrectionBoundaryV1::FinalCancel=>control.cancellation.cancel(),
                CorrectionBoundaryV1::FinalDeadline=>control.deadline=Instant::now(),
                CorrectionBoundaryV1::None=>{},
            }
            control.check(cursor)
        })();''',1)
        copied=copied.replace('            drop(body);','            drop(body);\n            let retirement=storage.retire(&mut control);',1)
        copied=copied.replace('            return Err(failure);','            return Err(CorrectionPreScopeFailureV1 {primary:failure,retirement});',1)
        generated='// Derived by exact recorded replacements from accepted original adopt_body.\n#[cfg(test)]\nimpl RuntimeControl {\n'+copied+'}\n'
        (HERE/'prototype/generated_admission_probe.rs').write_text(generated)
        proof_source=(ACCEPTED/'src/experimental_swift_reactor/control_tests.rs').read_text()
        proof_builder=proof_source[proof_source.index('fn uint('):proof_source.index('fn adopt(budget:')]
        for p,original_append,correction_append,tests in [
            (control,'control_append.rs','control_append.rs','control_tests_append.rs'),
            (initial,'initial_append.rs','initial_append.rs','initial_tests_append.rs')]:
            p.write_text(p.read_text()+'\n'+(ORIGINAL/'prototype'/original_append).read_text()+'\n'+(HERE/'prototype'/correction_append).read_text())
            test_text=(HERE/'prototype'/tests).read_text().replace('/* ACCEPTED_PROOF_BUILDER */',proof_builder)
            p.write_text(p.read_text()+'\n'+test_text)
        control.write_text(control.read_text()+'\n'+generated)
        original_initial=initial.read_text()
        begin=original_initial.index('    // Sole guard literal. No prepare/acquisition/callback/reentry follows it.')
        finish=original_initial.index('\n}\nfn write_initial_profile_rows_v1',begin)
        # The original ABI adapter exists only so all original test callsites typecheck.
        # It is never executed and is not an integrated phase-cleanup implementation.
        replacement='''    // Compiler-only ABI adapter. Never executed by this packet.
    correction_compose_signature_v1(cache,control,wasi,scalars,claims,row_output).primary'''
        initial.write_text(original_initial[:begin]+replacement+original_initial[finish:])
        assert initial.read_text().count('let initial=InitialProfileBorrowV1 {')==1
        dump(HERE/'compile-source-manifest.json',dict(members=inventory(tree),prototype_only=True,
            reconstructed_from_accepted=True,sole_original_guard_literal_relocated=True,
            abi_adapter_executed=False,proof_builder_sha256=hashlib.sha256(proof_builder.encode()).hexdigest()))
        for unit in [False,True]:
            for mode,opt in [('debug','0'),('optimized','3')]:
                name=('unit-' if unit else 'production-')+mode
                ll=scratch/(name+'.ll');binary=scratch/name
                argv=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin',
                    '-C','overflow-checks=yes','-C','opt-level='+opt]
                argv+=['--test','--emit',f'link={binary},llvm-ir={ll}'] if unit else ['--crate-type','lib','--emit',f'metadata={binary}.rmeta,llvm-ir={ll}']
                for feature in FEATURES:argv+=['--cfg',f'feature="{feature}"']
                argv+=[str(tree/'src/lib.rs')]
                receipt,_,err=command('compile-'+name,argv,HERE,{'CARGO_MANIFEST_DIR':str(tree)})
                assert receipt['exit_code']==0,err
                folder=HERE/'commands'/('compile-'+name)
                layouts={n:llvm_words(ll,n,count,folder) for n,count in [
                    ('MIXER_CORRECTION_EARLY_LAYOUT_V1',24),('MIXER_CORRECTION_REBORROW_LAYOUT_V1',18)]}
                results.append(dict(configuration=name,layouts=layouts,full_wrapper_executed=False))
                if unit:
                    for group,expected_tests in [('correction_early_tests',3),('correction_reborrow_tests',1)]:
                        r,out,err=command('run-'+name+'-'+group,[str(binary),group,'--nocapture','--test-threads=1'],HERE)
                        assert r['exit_code']==0 and f'{expected_tests} passed;' in out,(out,err)
        positive=initial.read_text()
        negative=positive.replace('control:access.shared_control(),wasi,scalars','control:control,wasi,scalars',1)
        assert negative!=positive
        initial.write_text(negative)
        dump(HERE/'negative-source-manifest.json',dict(members=inventory(tree),expected_error='E0502'))
        negatives=[]
        for mode,opt in [('debug','0'),('optimized','3')]:
            argv=[RUSTC,'--crate-name','mixer_vm','--edition=2021','--target','aarch64-apple-darwin','--crate-type','lib',
                '--emit',f'metadata={scratch}/negative-{mode}.rmeta','-C','overflow-checks=yes','-C','opt-level='+opt,'--error-format=json']
            for feature in FEATURES:argv+=['--cfg',f'feature="{feature}"']
            argv+=[str(tree/'src/lib.rs')]
            receipt,_,err=command('negative-direct-guard-'+mode,argv,HERE)
            errors=[]
            for line in err.splitlines():
                try:diagnostic=json.loads(line)
                except json.JSONDecodeError:continue
                if diagnostic.get('level')=='error' and diagnostic.get('code'):errors.append(diagnostic['code']['code'])
            assert receipt['exit_code']!=0 and errors==['E0502'],(errors,err)
            negatives.append(dict(mode=mode,errors=errors))
        initial.write_text(positive)
        assert inventory(tree)==json.loads((HERE/'compile-source-manifest.json').read_text())['members']
        dump(HERE/'results.json',dict(status='bounded-source-proof-passed-with-explicit-retention-limit',configurations=results,
            negative_direct_guard=negatives,host_tests_per_unit_mode=4,host_boundary_cases_per_unit_mode=8,
            no_full_writer=True,no_operational_floor=True,post_construction_healthy_cleanup_qualified=False,
            authentic_selected_entry_executed=False,full_conditional_admission_implemented=False))
    finally:
        shutil.rmtree(scratch)
        dump(HERE/'cleanup.json',dict(owned_scratch_removed=not scratch.exists(),all_children_reaped=True,
            native_runtime_ui_capture_started=False,process_inventory_performed=False,unrelated_processes_changed=False))
    # Revalidate the read-only inputs after all compiler work.
    assert checkseal(ORIGINAL,frozen[0]['seal_sha256'])==frozen[0]
    assert checkseal(REVIEW,frozen[1]['seal_sha256'])==frozen[1]
    for member in expected['members']:assert digest(ACCEPTED/member['path'])==member['sha256']
    print(json.dumps(dict(status='passed',configurations=4,host_test_runs=4,negative_compiles=2),indent=2))
if __name__=='__main__':main()
