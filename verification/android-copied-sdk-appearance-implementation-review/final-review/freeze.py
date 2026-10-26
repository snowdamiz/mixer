from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,stat,shutil,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def main():
    assert not (HERE/'seal.json').exists(),'final packet already sealed'
    # Producer-built executables are retained in the admitted compressed archive;
    # retire their disposable invocation copies and resource bundles after use.
    shutil.rmtree(HERE/'executables')
    cleanup=json.loads((HERE/'cleanup.json').read_text());cleanup['copied_producer_cli_invocation_directories_removed']=True
    cleanup['producer_cli_artifacts_retained_in']='producer-inputs/host-compiled-bindings.tar.gz'
    (HERE/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
    admission=json.loads((HERE/'admission.json').read_text());source=json.loads((HERE/'independent-source-review.json').read_text())
    compiled=json.loads((HERE/'independent-compiled-binding.json').read_text())
    with tarfile.open(HERE/'independent-compiled-artifacts.tar.gz') as archive:
        assert set(m.name for m in archive.getmembers())==set(compiled)
        for name,expected in compiled.items():assert identity(archive.extractfile(name).read())==expected,name
    for manifest,prefix in [('source-binding.json','source-inputs'),('owned-source-manifest.json','source-inputs')]:
        data=json.loads((HERE/'producer-inputs'/manifest).read_text());data=data.get('files',data)
        for name,expected in data.items():assert identity((HERE/'candidate'/name).read_bytes())==expected,name
    pre=HERE.parent/'preaccess';preseal=json.loads((pre/'seal.json').read_text())
    assert identity((pre/'seal.json').read_bytes())['sha256']=='a9554732573f2d6aa29c22e760bb15ff1fa2643c8507b6bccaca948b3683183c'
    for name,expected in preseal['files'].items():assert identity((ROOT/name).read_bytes())==expected,name
    doc=HERE.parent/'final-review.md'
    for path in [doc,*HERE.glob('*.py'),*HERE.glob('*.swift'),*HERE.glob('*.java')]:
        assert all(line.rstrip(' \t')==line for line in path.read_text().splitlines()),path
    verdict={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':'recommend-root-acceptance-of-scoped-development-source-pair-slice','actionable_product_findings':[],
        'root_selection_sha256':'cb191b996f00752c4cad3a4c1df7314bcfe72b00b1f75be29a2f6e4301821917',
        'candidate_handoff_sha256':admission['pins']['handoff.json'],'candidate_members_sha256':admission['pins']['members.json'],
        'candidate_source_binding_tree_sha256':'59b55224378dd2ce2ef2524d35b303f2dae7c913176d112a203541acb2ddd2c4',
        'preaccess_seal_sha256':'a9554732573f2d6aa29c22e760bb15ff1fa2643c8507b6bccaca948b3683183c',
        'source_files_audited':105,'unchanged_source_files':96,'selected_changed_or_added_files':9,
        'independent_main_entrypoint_controls':84,'independent_or_context_controls':26,'independent_alias_controls':6,'supplemental_observations':15,
        'copied_generated_swift_methods':3,'copied_independent_swift_methods':5,'production_java_assertions':30,'java_class_files':70,'focused_python_methods':28,
        'command_results':cleanup['command_results'],'timeouts':cleanup['timeouts'],'scratch_removed':cleanup['scratch_removed'],
        'unchanged_native_generated_inputs_independently_created_and_compared':75,'new_android_target_compile_or_apk':False,
        'ui_spec':source['ui_spec'],'full_uint64_limit':'Internal test-only snapshot injection exercised actual writer; natural counter exhaustion was not reached.',
        'implementation_accepted':False,'GA_qualified':False,'root_acceptance_required':True,'computer_use_capture_native_runtime_paused':True,
        'pending':['public V2','stable native ABI','installed lifecycle/capture/rendering','API28 support','resources/fonts/OS/input/accessibility/design matrix','signing and immutable CLI/SDK provenance','separate-repository FieldLog packages and dogfood','physical phones','OTA/store/operations and accountable GA review'],
        'review_doc':{'path':str(doc.relative_to(ROOT)),**identity(doc.read_bytes())},'command':['python3','-B',str(Path(__file__).relative_to(ROOT))]}
    (HERE/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n')
    files={str(doc.relative_to(ROOT)):identity(doc.read_bytes())}
    for p in sorted(HERE.rglob('*')):
        if p.is_file():
            assert stat.S_ISREG(p.lstat().st_mode),p
            files[str(p.relative_to(ROOT))]=identity(p.read_bytes())
    seal={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'scope':'Exact independent implementation-review source/input/output/member freeze; preaccess baseline remains separately immutable.','files':files}
    (HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    handoff={'schema':1,'at':datetime.now(timezone.utc).isoformat(),'status':verdict['status'],'review_doc':verdict['review_doc'],'verdict':{'path':str((HERE/'verdict.json').relative_to(ROOT)),**identity((HERE/'verdict.json').read_bytes())},'seal':{'path':str((HERE/'seal.json').relative_to(ROOT)),**identity((HERE/'seal.json').read_bytes())},'members':len(files),'bytes':sum(v['bytes'] for v in files.values()),'max_member_bytes':max(v['bytes'] for v in files.values()),'implementation_accepted':False,'GA_qualified':False,'scratch_removed':True}
    (HERE.parent/'final-handoff.json').write_text(json.dumps(handoff,indent=2)+'\n');print(json.dumps(handoff,indent=2))
if __name__=='__main__':main()
