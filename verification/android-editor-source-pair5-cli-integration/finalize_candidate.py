"""Freeze the produced CLI derivative and retain evidence; remove only owned scratch."""
import datetime,difflib,hashlib,json,os,pathlib,shutil,sys
HERE=pathlib.Path(__file__).resolve().parent
SOURCE=HERE/'source';EVIDENCE=HERE/'evidence'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(p):return {'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':sha(p)}
required=['cli-debug-tests-driver-guard','cli-release-original-context-final','python-driver-guard-final','final-cli-editor-entrypoints','final-cli-views-entrypoints','final-cli-renderer-entrypoints','final-cli-coordinator-entrypoints','cross-version-controls-02','optional-external-controls-final','generated-app-debug-swift','generated-app-release-swift-02','relocated-app-debug-swift','relocated-app-release-swift','generated-product18-sdk37-javac','generated-product18-min28-d8-02','raw-rendered-driver-release-build-final','generated-consumer-create-final','debug-cli-relocated-consumer-export','release-cli-consumer-export','offline-candidate-final-audit']
for label in required:
    j=json.loads((EVIDENCE/(label+'.json')).read_text());assert j['returncode']==0 and not j['timed_out'] and j['owned_child_reaped'],label
for label in ['cli-debug-tests-driver-guard','cli-release-original-context-final']:
    assert 'run with 42 tests' in (EVIDENCE/(label+'.log')).read_text()
# Preserve final artifacts before removing caches. Compiler/test configuration is
# recorded in its exact command rather than inferred from a shared filename.
for p,name in [(SOURCE/'.build-release/out/Products/Release/mixer','mixer-release'),(SOURCE/'.build-release-native/arm64-apple-macosx/release/mixer','mixer-release-native')]:
    if p.exists():shutil.copyfile(p,HERE/'artifacts/cli'/name);(HERE/'artifacts/cli'/name).chmod(0o755)
for src,dst in [(SOURCE/'.build/out/Products/Debug/MixerCLI_MixerBuild.bundle',HERE/'artifacts/pre-driver-guard/MixerCLI_MixerBuild.bundle')]:
    if src.exists():shutil.copytree(src,dst)
extra_tools=[]
for name in ['/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc','/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift-driver','/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar','/opt/homebrew/share/android-commandlinetools/build-tools/37.0.0/lib/d8.jar']:
    p=pathlib.Path(name).resolve();assert p.is_file();extra_tools.append({'path':name,'resolved_path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
(HERE/'compiler-support-identities.json').write_text(json.dumps({'schema':1,'identities':extra_tools,'host_swift_version_receipt':'evidence/tool-swift-version.json','javac_version_receipt':'evidence/tool-javac-version.json','java_release_flag_does_not_identify_compiler_version':True},indent=2)+'\n')
commands=[]
for p in sorted(EVIDENCE.glob('*.json')):
    j=json.loads(p.read_text())
    if isinstance(j,dict) and 'label' in j:
        commands.append({'receipt':str(p.relative_to(HERE)),'label':j['label'],'exit_code':j['returncode'],'timed_out':j['timed_out'],'elapsed_seconds':j['elapsed_seconds'],'source_tree_sha256':j['source_tree_sha256'],'owned_child_reaped':j['owned_child_reaped']})
(HERE/'command-index.json').write_text(json.dumps({'schema':1,'commands':commands,'required_final_rows':required,'all_required_final_rows_pass':True,'historical_failures_retained':True,'initial_metadata_scope_corrections':'harness-failures.json'},indent=2)+'\n')
# There are no active command cells when this is invoked. No process enumeration
# or unrelated/native/capture instance management is performed.
remove=[SOURCE/'.build',SOURCE/'.build-release',SOURCE/'.build-release-native',HERE/'scratch']
remove += [p/'.mixer' for p in (HERE/'consumers').iterdir() if p.is_dir() and (p/'.mixer').exists()]
removed=[]
for p in remove:
    if p.exists():
        assert p.is_dir() and not p.is_symlink() and HERE in p.resolve().parents,p
        shutil.rmtree(p);removed.append(str(p.relative_to(HERE)))
for base,dirs,names in os.walk(HERE):
    for d in list(dirs):
        if d=='__pycache__':
            p=pathlib.Path(base)/d;shutil.rmtree(p);dirs.remove(d);removed.append(str(p.relative_to(HERE)))
assert not any(p.name.startswith(('mixer-actual-','mixer-cross-version-','mixer-optional-actual-')) for p in HERE.iterdir())
(HERE/'cleanup.json').write_text(json.dumps({'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'removed_owned_paths':removed,'owned_command_groups_reaped':True,'owned_temporary_fixture_roots_remaining':0,'native_runtime_started':False,'capture_or_UI_started':False,'process_inventory_performed':False,'other_projects_processes_or_data_touched':False},indent=2)+'\n')
manifest=json.loads((HERE/'source-manifest.json').read_text());records=manifest['members']
assert len(records)==162
for m in records:
    p=HERE/m['path'];assert p.stat().st_size==m['bytes'] and sha(p)==m['sha256']
projection=hashlib.sha256(''.join(m['path'].removeprefix('source/')+'\0'+m['sha256']+'\n' for m in sorted(records,key=lambda m:m['path'])).encode()).hexdigest()
assert projection=='6ba31109183443ab62ef8ae9e36ae3e968ec3da383c67c4cc93aa6a2a9a5131a'
summary={'freeze_command':[sys.executable,*sys.argv],'python_version':sys.version,'schema':1,'status':'producer-frozen-awaiting-independent-and-root-review','scope':'CLI source-pair5 isolated derivative; host/source/cross evidence only','source_tree_sha256':projection,'source_members':162,'profile':'mixer.android-source-pair.5','SDK_map_members':22,'adapter_map_members':24,'product_java_subjects':18,'changed_canonical_targets':5,'canonical_source_changed':False,'independent_review_complete':False,'coherent_integration_accepted':False,'native_UI_capture_process_inventory_allowed':False,'pending':['Independent coherent source review and root acceptance','Canonical promotion and integrated CI','Android/iOS physical runtime and IME/focus/composition/accessibility parity','Immutable externally published FieldLog SDK packages','Public V2 routing, signing, stores, OTA and GA'],'tests':{'CLI_Debug_functions':42,'CLI_Release_original_Xcode_context_functions':42,'CLI_Release_original_context_elapsed_seconds':json.loads((EVIDENCE/'cli-release-original-context-final.json').read_text())['elapsed_seconds'],'CLI_Release_native_context_functions_supplementary':42,'Python_tests':33,'actual_four_source_negative_commands':240,'actual_optional_negative_commands':53,'actual_cross_generation_commands':37,'cross_generation_pre_correction_required_failure_witnesses':1,'unsigned_driver_commands':47,'unsigned_APK_sha256':'b52e60b07583ba095eab2c211a87fb64b87aa93641cd14cd74cfb8d73f2b1fe3','generated_and_relocated_ELF_audits':8,'emitted_Java_classes':212},'cleanup':'cleanup.json','preserved_failures':'command-index.json and harness-failures.json','promotion_targets':'promotion-targets.json'}
(HERE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
# Seal every ordinary member after metadata/cleanup. No skipped build directory or
# mutable output is silently excluded from the final closed tree.
members=[]
for p in sorted(HERE.rglob('*')):
    assert not p.is_symlink(),p
    if p.is_file() and p.name!='seal.json':members.append(identity(p))
seal={'schema':1,'scope':'Producer frozen CLI derivative; review pending, no integration/native/release acceptance','member_count':len(members),'member_bytes':sum(m['bytes'] for m in members),'members':members}
(HERE/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
print(json.dumps({'seal_sha256':sha(HERE/'seal.json'),'members':len(members),'bytes':seal['member_bytes'],'source_projection':projection,'summary':'summary.json','cleanup_removed':removed}))
