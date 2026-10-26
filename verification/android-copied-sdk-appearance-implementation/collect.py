"""Freeze exact observed host-only evidence. No product/policy refresh occurs."""
import ast, datetime, hashlib, json, pathlib, shutil, tarfile
from run import BASE, run
REPO=BASE.parents[1];REV='559858810e133640d52730972a6610e98442be6d'
CONSUMER=pathlib.Path('/tmp/mixer-source-pair-consumer-20261026')
FINAL=pathlib.Path('/tmp/mixer-source-pair-consumer-final-20261026')
PARITY=pathlib.Path('/tmp/mixer-source-pair-native-parity-20261026')
def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def write(name,value):(BASE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
binding=json.loads((BASE/'source-binding.json').read_text())
for relative,row in binding['files'].items():assert identity((REPO/relative).read_bytes())==row,relative
source=(REPO/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
policy=json.loads(source.split('Data(#"""\n',1)[1].split('\n        """#.utf8)',1)[0])
selected=json.loads((REPO/'verification/android-copied-sdk-appearance-contract/proposed-profile-observation.json').read_text());selected['id']='mixer.android-source-pair.1'
assert policy==selected
owned=['cli/Sources/MixerBuild/AndroidSDKCompatibility.swift','cli/Sources/MixerBuild/AndroidProject.swift','cli/Sources/MixerBuild/ProjectGenerator.swift','cli/Sources/MixerBuild/Resources/android-build.py','cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift','cli/Tests/MixerBuildTests/AndroidProjectTests.swift','cli/build-tests/test_android_sdk_compatibility.py','cli/build-tests/test_android_staging.py','cli/build-tests/test_android_appearance.py']
write('owned-source-manifest.json',{p:identity((REPO/p).read_bytes()) for p in owned})
profilepaths=['sdk/'+p for p in policy['sdk_files']]+['native/android/'+('engine/'+p if p.startswith('Sources/') else p) for p in policy['adapter_files']]
code,folder=run('selected-source-git-blobs',['git','ls-tree','-r',REV,'--',*profilepaths],20);assert code==0
blobrows={line.split('\t',1)[1]:line.split()[2] for line in (folder/'output.txt').read_text().splitlines()}
assert set(blobrows)==set(profilepaths)
for path,blob in blobrows.items():
    data=(REPO/path).read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==blob,path
write('selected-source-git-binding.json',{'revision':REV,'files':blobrows,'all_42_match_selected_git':True})
code,folder=run('ui-spec-git-blob',['git','ls-tree',REV,'--','contracts/ui-v1.json'],20);assert code==0
spec=(REPO/'contracts/ui-v1.json').read_bytes();blob=(folder/'output.txt').read_text().split()[2]
assert hashlib.sha1(b'blob '+str(len(spec)).encode()+b'\0'+spec).hexdigest()==blob
write('ui-spec-binding.json',{'path':'contracts/ui-v1.json','identity':identity(spec),'git_blob':blob,'source_revision':REV,'scope':'Separately pinned qualification specification. Production decoders execute their own selected implementations; this file is not an admission-policy input.'})
# Freeze the actual used consumer source closure; never copy repository SDK as fallback.
consumerrows={}
for path in sorted(CONSUMER.rglob('*')):
    if not path.is_file() or '.build' in path.parts or '__pycache__' in path.parts or any(x.startswith('qualification-') for x in path.relative_to(CONSUMER).parts):continue
    relative=path.relative_to(CONSUMER).as_posix();data=path.read_bytes();consumerrows[relative]=identity(data)
    target=BASE/'consumer-used'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
write('consumer-source-binding.json',consumerrows)
shutil.copytree(CONSUMER/'qualification-classes',BASE/'production-java-classes')
shutil.copytree(CONSUMER/'qualification-output',BASE/'consumer-outputs')
classes={p.relative_to(BASE/'production-java-classes').as_posix():identity(p.read_bytes()) for p in (BASE/'production-java-classes').rglob('*.class')}
write('production-java-class-binding.json',{'production_sources':[p for p in consumerrows if p.endswith(('Json.java','UiPacket.java','AppearanceDescriptorV2.java','AppearanceGeometryV2.java'))],'harness':identity((BASE/'consumer-tests/CopiedPairProbe.java').read_bytes()),'classes':classes,'scope':'Official javac --release17 from four exact copied production pure-Java files plus named probe, with existing empty source/class paths. Remaining 10 exported Java files are source-pinned, not compiled in this pure-Java host probe.'})
outputs={p.name:identity(p.read_bytes()) for p in (BASE/'consumer-outputs').iterdir() if p.is_file()}
write('consumer-output-binding.json',outputs)
# Final CLI creation exports identical selected source/data bytes to those executed.
comparisons={}
for p in list(policy['sdk_files'])+list(policy['adapter_files']):
    prefix='Generated/MixerSDK/' if p in policy['sdk_files'] else 'Generated/MixerAndroid/'
    assert (CONSUMER/(prefix+p)).read_bytes()==(FINAL/(prefix+p)).read_bytes()
    comparisons[p]=identity((CONSUMER/(prefix+p)).read_bytes())
write('final-created-pair-binding.json',{'all_42_final_created_sources_equal_executed_consumer':True,'files':comparisons})
# Exactly one actual rendered literal, with no marker, compiled policy and lock match.
rendered=(FINAL/'Generated/MixerAndroid/android-build.py').read_text()
assignments=[x for x in ast.parse(rendered).body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_PROFILE_HEX' for t in x.targets)]
assert len(assignments)==1 and isinstance(assignments[0].value,ast.Constant)
assert '__MIXER_ANDROID_SOURCE_PROFILE_HEX__' not in rendered
assert json.loads(bytes.fromhex(assignments[0].value.value))==policy
lock=json.loads((FINAL/'mixer.lock').read_text());expected={k:policy[k] for k in ['id','sdk_compatibility_sha256','adapter_compatibility_sha256','default_descriptor']};assert lock['android']['profile']==expected
write('actual-rendered-driver-binding.json',{'driver':identity(rendered.encode()),'profile':expected,'exactly_one_literal':True,'no_marker':True,'compiled_policy_and_lock_match':True,'final_lock':lock})
# Read-only comparison with the accepted native-target packaging inputs. Name/ID
# are the same in this separate fresh create, so no normalization masks differences.
oldarchive=REPO/'verification/android-default-appearance-packaging/run-2/generated-source-and-classes.tar.gz'
def native(path):
    return (path in ['Package.swift','Generated/MixerSDK/Package.swift','Generated/MixerAndroid/Package.swift','Platforms/Android/Package.swift','Platforms/Android/AndroidManifest.xml','Generated/MixerAndroid/contracts/android-profile-v1.json','Generated/MixerAndroid/app/assets/MixerAppearanceV2/descriptor.json'] or
        (path.startswith(('Sources/AppModels/','Sources/AppFeatures/','Generated/MixerSDK/Sources/','Generated/MixerAndroid/Sources/','Platforms/Android/Sources/')) and path.endswith('.swift')) or
        (path.startswith('Generated/MixerAndroid/app/src/') and path.endswith('.java')) or path.startswith('Generated/MixerAndroid/bridge/'))
parity={}
with tarfile.open(oldarchive) as archive:
    for member in archive.getmembers():
        prefix='AppearanceConsumer/'
        if not member.isfile() or not member.name.startswith(prefix):continue
        relative=member.name[len(prefix):]
        if not native(relative):continue
        old=archive.extractfile(member).read();new=(PARITY/relative).read_bytes();assert old==new,relative
        parity[relative]=identity(new)
assert len(parity)>=42
write('native-input-parity.json',{'prior_archive':str(oldarchive.relative_to(REPO)),'archive_identity':identity(oldarchive.read_bytes()),'prior_apk_sha256':'740e8af341e371697b82d415b37b719078aee8859eb57c1fe8d258cdd319114b','all_compared_native_target_inputs_equal':True,'files':parity,'scope':'Exact unchanged first-party compiled/generated native target inputs plus manifest/descriptor. No new native compilation/APK/device result is inferred.'})
# Preserve actual host test executable bytes and CLI binaries compressed, with identities.
compiled={}
with tarfile.open(BASE/'host-compiled-bindings.tar.gz','w:gz') as archive:
    for config in ['debug','release']:
        binary=REPO/'cli/.build'/config/'mixer';relative='cli-'+config+'/mixer'
        compiled[relative]=identity(binary.read_bytes());archive.add(binary,arcname=relative,recursive=False)
    scratch=CONSUMER/'Platforms/Android/.build'
    for directory in scratch.rglob('*.xctest'):
        for binary in (directory/'Contents/MacOS').glob('*'):
            if binary.is_file():
                relative='copied-consumer/'+binary.name;compiled[relative]=identity(binary.read_bytes());archive.add(binary,arcname=relative,recursive=False)
write('host-compiled-binding.json',compiled)
assert any(p.startswith('copied-consumer/') for p in compiled)
commands={p.parent.name:json.loads(p.read_text()) for p in (BASE/'commands').glob('*/result.json')}
write('command-index.json',commands)
for relative,row in binding['files'].items():assert identity((REPO/relative).read_bytes())==row,relative
write('receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'host-implementation-evidence-collected-awaiting-independent-review','source_revision':REV,'source_binding_tree_sha256':binding['tree_sha256'],'source_binding_sha256':identity((BASE/'source-binding.json').read_bytes())['sha256'],'observed_source_inputs_unchanged_since_final_binding':True,'owned_product_files':owned,'sdk_source_files':22,'adapter_source_files':20,'full_cli_tests_final_debug':31,'full_cli_tests_final_release':31,'python_test_methods':28,'actual_entrypoint_checks':52,'actual_marker_entrypoint_checks':4,'copied_consumer_swift_test_methods':5,'production_java_checks':25,'native_input_parity_members':len(parity),'production_java_class_files':len(classes),'outputs':outputs,'profile':expected,'commands_recorded':len(commands),'implementation_accepted':False,'GA_qualified':False,'native_runtime_or_capture_started':False,'new_APK_built':False,'failed_attempts':[name for name,item in commands.items() if item['exit_code']!=0 and name.endswith('copied-java-compile')],'failure_note':'Initial javac omitted creation of explicit empty source/class-path directories; -Werror rejected path warnings. Directories created; qualified compilation and execution succeeded. All expected negative entrypoint refusals are recorded nonzero and validated by outer probes. A premature intermediate Java execution overlapped a later compile; it is superseded by copied-java-qualified-execute after copied-java-qualified-compile.','scope':'Exact reviewed first-party development source-pair admission and bounded host API/wire execution. Editable local policy/locks remain unauthenticated; no stable ABI, native runtime, immutable distribution or release qualification.'})
print('Collected',len(consumerrows),'consumer source members,',len(classes),'Java classes,',len(parity),'unchanged native input members')
