#!/usr/bin/env python3
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,tempfile
O=Path(__file__).resolve().parent;R=O.parents[1];C=O/'candidate';B=O/'runs/B';E=O/'runs/independent-extra-2';E.mkdir(exist_ok=False)
helper=C/'native/android/tests/run-private-owner-host.py';spec=importlib.util.spec_from_file_location('reviewed_host_support',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
classes=B/'classes';mapping=json.loads((B/'class-map.json').read_text());assert {str(p.relative_to(classes)):m.ident(p.read_bytes()) for p in sorted(classes.rglob('*.class'))}==mapping
original=B/'inputs/native/android/tests/NativeEditorPreservationHostControls/IndependentPreservationCompletionControls.java';accepted=R/'verification/android-editor-preservation-membership-correction/tests/IndependentPreservationCompletionControls.java';assert original.read_bytes()==accepted.read_bytes()
android=Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar');assert m.ident(android.read_bytes())=={'bytes':43044472,'sha256':'bf1b4387cc7ca94fc6ef684f040d9d16fbf16248e181819f020736ea2053f177'}
env=dict(os.environ)
for key in m.STRIP:env.pop(key,None)
env['PYTHONDONTWRITEBYTECODE']='1';scratch=Path(tempfile.mkdtemp(prefix='owned-independent-extra-',dir=E));tmp=scratch/'tmp';tmp.mkdir();empty=scratch/'empty';empty.mkdir();out=scratch/'extra';out.mkdir();env['TMPDIR']=str(tmp);run=m.BoundedRun(E,R,env);status='failed'
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');java=jdk/'bin/java';javac=jdk/'bin/javac';readelf=Path('/Users/andreyyurlov/.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android/android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-readelf')
try:
 run.run('original-PC-C16',[java,'-Djava.io.tmpdir='+str(tmp),'-ea','-Xmx256m','-cp',classes,'dev.mixer.android.IndependentPreservationCompletionControls','journal-membership',B/'inputs/descriptor.json'],contains=b'PASS independent prospective preservation control journal-membership')
 run.run('compile-V1-oracle',[javac,'--release','17','-Xlint:all','-Werror','-proc:none','-classpath',classes,'-sourcepath',empty,'-d',out,O/'IndependentV1Frames.java'])
 run.run('V1-frames',[java,'-Djava.io.tmpdir='+str(tmp),'-ea','-Xmx256m','-cp',str(out)+os.pathsep+str(classes),'dev.mixer.android.IndependentV1Frames',B/'inputs/descriptor.json',E/'unused-sites.txt'],contains=b'PASS independent five separate real V1 source/class/descriptor/BCI calls')
 shutil.copy2(classes/'DescriptorClosure.class',out/'DescriptorClosure.class')
 run.run('official-SDK37-descriptor38',[java,'-Djava.io.tmpdir='+str(tmp),'-ea','-Xmx256m','-cp',str(out)+os.pathsep+str(android),'DescriptorClosure'],contains=b'descriptor closure: 38;')
 cross=R/'verification/android-editor-source-pair5-host-integration/runs/cross-3';native=cross/'native-products'
 for name in ['libMixerAndroidEngine.so','libmixer_android_jni.so']:
  assert m.ident((native/name).read_bytes())==json.loads((cross/'native-products.json').read_text())[name]
  data=run.run('independent-elf-'+name,[readelf,'--file-header','--dynamic','--dyn-syms',native/name]);assert b'ELF64' in data and b'AArch64' in data
  if name=='libmixer_android_jni.so':
   assert b'libMixerAndroidEngine.so' in data
   for s in ['create','prepareV2','commitV2','abortV2','destroy']:assert ('Java_dev_mixer_android_NativeBridge_'+s).encode() in data
 status='passed-independent-extra-host-offline-checks';print('PASS unchanged originalPC-C16, five V1 descriptor/BCI calls, officialSDK37 exact38, retainedELF architecture/JNI exports/dependency')
finally:
 shutil.rmtree(scratch);m.save(E/'receipt.json',{'status':status,'class_map':m.ident((B/'class-map.json').read_bytes()),'unchanged_original_control':m.ident(original.read_bytes()),'helper':m.ident(helper.read_bytes()),'oracle':m.ident((O/'IndependentV1Frames.java').read_bytes()),'scope':'host JVM and offline source-bound cross artifacts only; no cross rebuild','cleanup':{'owned_scratch_removed':not scratch.exists(),'children_reaped':run.reap_group(),'native_ui_capture_or_process_inventory_started_or_queried':False}})
