#!/usr/bin/env python3
"""Bounded source/compile audit only; no canonical/source-profile policy mutation."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
JAVA=ROOT/'native/android/app/src/dev/mixer/android'
P=ROOT/'verification/android-editor-integration-protocol'
C=ROOT/'verification/android-editor-preservation-membership-correction'
def identity(data): return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def read(path): return path.read_bytes()
def save(name,value): (OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def require(value,message):
    if not value: raise RuntimeError(message)
def run(name,argv):
    result=subprocess.run([str(x) for x in argv],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (OUT/(name+'.stdout')).write_bytes(result.stdout);(OUT/(name+'.stderr')).write_bytes(result.stderr)
    commands.append({'name':name,'argv':[str(x) for x in argv],'cwd':str(ROOT),'exit_code':result.returncode,
      'stdout':name+'.stdout','stderr':name+'.stderr'})
    require(result.returncode==0,'Command failed '+name)
    return result.stdout.decode().strip()
commands=[]
expected={
 'verification/android-editor-integration-protocol/seal.json':'2338ce170833c7a33d797d46a6d51d50e3b24398ed05b2b8b2129dafb35eb89f',
 'verification/android-editor-boundary-root-review/integration-source-inventory-amendment.md':'965f1aa77e990fbfe3b5f2b19c04e357c1fae1dda8874bc171268a101c6a1a34',
 'verification/android-editor-preservation-membership-correction/seal.json':'620bfefe8cde4b63c2101db76af991fcc1933276f9c1e8d8d1aa1e3db8f0bf0e',
 'verification/android-editor-boundary-root-review/preservation-membership-acceptance.json':'2d7d9515ef7a6dd4ceeb7c5d61b951d06b4720c1fffdfd5988938d5e47b34e75'}
for relative,digest in expected.items():require(identity(read(ROOT/relative))['sha256']==digest,'Frozen root input drift '+relative)
selected_sources=['Json.java','UiPacket.java','AppearanceDescriptorV1.java','AppearanceResolutionV1.java','AppearanceDescriptorV2.java','AppearanceGeometryV2.java']
selected_tests=['AppearanceDescriptorTests.java','AppearanceResolutionTests.java','AppearanceDescriptorV2Tests.java']
source_paths=[JAVA/name for name in selected_sources]+[ROOT/'native/android/tests'/name for name in selected_tests]
context=[ROOT/p for p in ['AGENTS.md','PLAN.md','cli/Sources/MixerBuild/AndroidSDKCompatibility.swift','cli/Sources/MixerBuild/AndroidProject.swift','cli/Sources/MixerBuild/ProjectGenerator.swift','cli/Sources/MixerBuild/Resources/android-build.py','cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift','cli/Tests/MixerBuildTests/AndroidProjectTests.swift','native/android/tests/NativeOwnerV2ConcreteHostTests.java','native/android/build.py','native/android/tests/run-private-owner-host.py','native/android/tests/run-private-owner-crosscompile.py','verification/android-private-owner-effect-roster-amendment/required-host-roster.json','verification/android-editor-integration-protocol/compiled-boundary-qualification.md','verification/android-editor-integration-protocol/integration-contract.md','verification/android-editor-integration-protocol/source-lists.json','verification/android-editor-integration-protocol/current-profile4.json','verification/android-editor-integration-protocol/proposed-profile5.json']]+[ROOT/p for p in expected]
source_map={str(path.relative_to(ROOT)):identity(read(path)) for path in sorted(set(context+source_paths))}
canonical={path.name:identity(read(path)) for path in sorted(JAVA.glob('*.java'))}
text=(ROOT/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift').read_text()
profile=json.loads(text.split('Data(#"""',1)[1].split('"""#.utf8)',1)[0])
product4={Path(path).name:ident for path,ident in profile['adapter_files'].items() if path.endswith('.java')}
require(len(product4)==17 and profile['id']=='mixer.android-source-pair.4','Unexpected canonical baseline')
for name,ident in product4.items(): require(canonical[name]==ident,'Canonical profile4 source drift '+name)
legacy={name:canonical[name] for name in ['AppearanceDescriptorV1.java','AppearanceResolutionV1.java']}
require(set(canonical)==set(product4)|set(legacy)|{'AdapterInstrumentation.java'},'Unexpected canonical Java inventory')
seal=json.loads(read(C/'seal.json'))
candidate={Path(member['path']).name:{k:member[k] for k in ('bytes','sha256')} for member in seal['members'] if member['path'].startswith('source/')}
require(len(candidate)==16,'Accepted source count')
for name,ident in candidate.items():
    path=C/'source'/name;require(identity(read(path))==ident,'Accepted source drift '+name)
    source_map[str(path.relative_to(ROOT))]=ident
product5={**product4,**candidate}
require(len(product5)==18 and set(product5)-set(product4)=={'NativeEditorConnectionV2.java'},'Future product subject set')
changed=sorted(name for name in product4 if product4[name]!=product5[name])
require(changed==['NativeAppearanceViewsV2.java','NativeCoordinatorV2.java','NativeRenderer.java'],'Accepted candidate delta')
roster=json.loads((ROOT/'verification/android-private-owner-effect-roster-amendment/required-host-roster.json').read_text())
baselines=roster['v1_compile_baseline_only'];require(len(baselines)==5,'Five V1 controls')
require(all(row['source']=='native/android/app/src/dev/mixer/android/NativeRenderer.java' for row in baselines),'V1 baseline ownership')
revision=run('revision',['git','rev-parse','HEAD'])
python_version=run('python-version',[sys.executable,'--version'])
git_version=run('git-version',['git','--version'])
# Exact compiler location observed in the frozen integration support receipt.
support=json.loads((P/'support-controls/receipt.json').read_text())
tool_paths=support['tools'];javac=Path(next(path for path in tool_paths if path.endswith('/bin/javac')))
jdk=javac.parent
for path in [javac,jdk/'java',jdk/'javap']:require(path.is_file(),'Frozen-receipt compiler unavailable '+str(path))
tools={str(path):identity(path.resolve().read_bytes()) for path in [javac,jdk/'java',jdk/'javap']}
for path,ident in tools.items():require(ident==tool_paths[path],'Compiler binary differs from observed receipt '+path)
javac_version=run('javac-version',[javac,'--version']);java_version=run('java-version',[jdk/'java','--version']);javap_version=run('javap-version',[jdk/'javap','-version'])
inputs=OUT/'compile-inputs';classes=OUT/'classes';empty=OUT/'empty'
for directory in [inputs,classes,empty]:directory.mkdir(exist_ok=False)
copies=[]
for source in source_paths:
    target=inputs/source.name;target.write_bytes(source.read_bytes());copies.append(target)
run('legacy-appearance-compile',[javac,'--release','17','-Xlint:all','-Werror','-proc:none','-classpath',empty,'-sourcepath',empty,'-d',classes,*copies])
classmap={str(path.relative_to(classes)):identity(path.read_bytes()) for path in sorted(classes.rglob('*.class'))}
run('legacy-appearance-control-bytecode',[jdk/'javap','-classpath',classes,'-c','-p','-s','dev.mixer.android.AppearanceDescriptorTests','dev.mixer.android.AppearanceResolutionTests','dev.mixer.android.AppearanceDescriptorV2Tests'])
bytecode=(OUT/'legacy-appearance-control-bytecode.stdout').read_text()
require('AppearanceDescriptorV1.decode' in bytecode and 'AppearanceResolutionV1.prepare' in bytecode,'Compiled legacy test references absent')
save('compiled-class-map.json',classmap)
# Preserve copied exact source inputs and class hashes; retire owned ephemeral class output.
shutil.rmtree(classes);empty.rmdir()
source_digest=hashlib.sha256(json.dumps(source_map,sort_keys=True,separators=(',',':')).encode()).hexdigest()
save('source-inputs.json',{'schema':1,'source_revision':revision,'source_tree_identity_format':'SHA256 of canonical compact sorted-key JSON path -> bytes/sha256 map','source_tree_sha256':source_digest,'members':source_map})
save('source-inventory.json',{'schema':1,'canonical_java':canonical,'profile4_product_java':product4,'canonical_only_legacy_appearance':legacy,'existing_named_probe':{'AdapterInstrumentation.java':canonical['AdapterInstrumentation.java']},'accepted_candidate_java':candidate,'future_profile5_product_java':product5,'accepted_candidate_replaced_profile4_names':changed,'five_v1_renderer_baselines':baselines,'profile4_java_count':len(product4),'canonical_java_count':len(canonical),'future_profile5_product_java_count':len(product5),'future_full_canonical_java_count':len(product5)+len(legacy)+1,'profile4_adapter_count':len(profile['adapter_files']),'future_profile5_adapter_count':len(profile['adapter_files'])+1})
# Only the context bytes actually audited are rechecked; no other active lane is read.
for relative,ident in source_map.items(): require(identity(read(ROOT/relative))==ident,'Audited source changed before seal '+relative)
save('commands.json',commands)
save('audit-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'passed-bounded-source-and-legacy-host-compile-audit','source_revision':revision,'source_tree_sha256':source_digest,'scope':'source inventory and actual legacy appearance host-test compile references only; no selected source-pair5 enforcement or behavioral qualification','versions':{'python':python_version,'git':git_version,'javac':javac_version,'java':java_version,'javap':javap_version},'compiler_tools':tools,'legacy_compile_source_count':len(source_paths),'compiled_class_count':len(classmap),'legacy_behavior_runtime_executed':False,'five_renderer_v1_behavior_baselines_reexecuted':False,'full_export_or_generated_consumer_executed':False,'native_runtime_UI_capture_or_process_inventory_started':False,'canonical_or_metadata_modified':False,'policy_amendment_selected':False,'owned_ephemeral_classes_removed':True,'new_dependencies':[],'limits':['Actual compiler is JDK27 with --release17, not a JDK17 execution receipt.','The five V1 renderer call-site baselines are separate from these two legacy appearance source controls.','Policy selection and actual Swift/Python preaccess enforcement tests remain root work.','Native runtime, API linkage/OEM/IME/accessibility/physical, unsigned SDK/D8 generated consumer, public V2, OTA and GA acceptance are not established.']})
print(json.dumps({'status':'passed','legacy_compile_sources':len(source_paths),'compiled_classes':len(classmap),'canonical_java':len(canonical),'product4_java':len(product4),'product5_java':len(product5),'legacy':legacy,'source_tree_sha256':source_digest},sort_keys=True))
