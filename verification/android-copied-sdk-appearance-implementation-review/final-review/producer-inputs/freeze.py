import datetime,hashlib,json,pathlib,shutil
BASE=pathlib.Path(__file__).resolve().parent;ROOT=BASE.parents[1]
def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def write(name,value):(BASE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
assert identity((ROOT/'verification/android-copied-sdk-appearance-contract-root-review/implementation-selection.json').read_bytes())['sha256']=='cb191b996f00752c4cad3a4c1df7314bcfe72b00b1f75be29a2f6e4301821917'
binding=json.loads((BASE/'source-binding.json').read_text())
for relative,row in binding['files'].items():assert identity((ROOT/relative).read_bytes())==row,relative
commands={p.parent.name:json.loads(p.read_text()) for p in (BASE/'commands').glob('*/result.json')};write('command-index.json',commands)
receipt=json.loads((BASE/'receipt.json').read_text());receipt['commands_recorded']=len(commands);write('receipt.json',receipt)
shutil.copyfile(ROOT/'docs/android-copied-sdk-appearance-implementation.md',BASE/'implementation.md')
owned=json.loads((BASE/'owned-source-manifest.json').read_text())
record={
 'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'frozen-implementation-handoff-awaiting-independent-review-and-root-acceptance',
 'implementation_selected':True,'implementation_accepted':False,'GA_qualified':False,
 'source_revision':'559858810e133640d52730972a6610e98442be6d',
 'selection':'verification/android-copied-sdk-appearance-contract-root-review/implementation-selection.json',
 'selection_sha256':'cb191b996f00752c4cad3a4c1df7314bcfe72b00b1f75be29a2f6e4301821917',
 'implementation_document':identity((BASE/'implementation.md').read_bytes()),
 'source_binding':identity((BASE/'source-binding.json').read_bytes()),
 'source_binding_tree_sha256':binding['tree_sha256'],
 'owned_product_files':owned,
 'observations':{'final_full_cli_functions_debug':31,'final_full_cli_functions_release':31,'python_methods':28,'actual_entrypoint_checks':52,'actual_marker_entrypoint_checks':4,'actual_copied_swift_methods':5,'production_java_checks':25,'java_class_files':69,'unchanged_native_input_members':75,'all_42_profile_sources_match_selected_git':True,'source_inputs_unchanged':True,'owned_consumer_scratch_removed':3},
 'source_profiles':receipt['profile'],
 'tool_versions':{'host_swift':'Apple Swift 6.4 (swiftlang-6.4.0.34.1 clang-2100.3.34.1), arm64-apple-macosx27.0.0','python':'3.14.8','git':'2.56.0','java_javac':'25.0.4.1','inspected_android_swift':'6.3.3 official distribution','inspected_ndk':'r27d / 27.3.13750724','inspected_platform_build_tools':'37.0.0'},
 'failed_attempts':receipt['failed_attempts'],
 'superseded_attempts':['copied-java-final-execute overlapped an intermediate compile; copied-java-qualified-compile then copied-java-qualified-execute bind final sources/classes/output'],
 'limits':['Exact first-party source-pair development admission only; no version range or stable ABI.','Generated drivers and local locks remain mutable/unauthenticated; no hostile concurrent-writer guarantee.','Native UI/capture/simulator/emulator runtime remains paused; physical phones remain disconnected.','No new native target compile or APK; 75 exact native inputs equal accepted packaging archive.','Full UInt64 generations were injected through an internal test-only snapshot constructor into the production writer; natural counter exhaustion was not reached.','Pure Java probe compiles four selected codec/geometry sources; other ten exported Java files are source-pinned.','Installed lifecycle, API28, resources/fonts/OS/input/accessibility/design, signing, immutable separate-repository FieldLog, release/store/operations and accountable GA gates remain pending.','Independent implementation review/root acceptance and root-owned metadata/commit/push/CI remain required.'],
 'unchanged_owned_scope_exclusions':['SDK implementation','Java/JNI/runtime/Activity','ProcessRunner','dependencies','hosted/control plane','production/credentials'],
 'forensic_helpers':'write_profile.py and patch_driver.py record one-time initial edits only. They are not build/test hooks or policy-refresh paths and must not be rerun over the final implementation.',
 'validation':'Run python3 -B verification/android-copied-sdk-appearance-implementation/check_packet.py for read-only member and current-owned-source verification.',
 'cleanup_receipt':'cleanup.json','commit_push_performed':False,
}
write('handoff.json',record)
manifest={p.relative_to(BASE).as_posix():identity(p.read_bytes()) for p in sorted(BASE.rglob('*')) if p.is_file() and p.name not in {'members.json','seal.sha256'}}
write('members.json',manifest)
(BASE/'seal.sha256').write_text(hashlib.sha256((BASE/'members.json').read_bytes()).hexdigest()+'  members.json\n')
maximum=max(manifest.items(),key=lambda item:item[1]['bytes'])
print(json.dumps({'members':len(manifest),'total_bytes':sum(x['bytes'] for x in manifest.values()),'max_member':maximum,'handoff':identity((BASE/'handoff.json').read_bytes()),'members_manifest':identity((BASE/'members.json').read_bytes()),'seal':identity((BASE/'seal.sha256').read_bytes()),'owned_source_manifest':identity((BASE/'owned-source-manifest.json').read_bytes()),'source_binding':identity((BASE/'source-binding.json').read_bytes())},indent=2))
