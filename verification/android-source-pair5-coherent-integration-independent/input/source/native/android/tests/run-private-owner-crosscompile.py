#!/usr/bin/env python3
"""Frozen profile5 Java/SDK37/D8 and unsigned ordinary engine/JNI cross-compilation."""
import argparse,datetime,hashlib,importlib.util,json,os,shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
_helper=Path(__file__).with_name('run-private-owner-host.py');spec=importlib.util.spec_from_file_location('private_owner_host_support',_helper);support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
ident=support.ident;save=support.save
ANDROID37={'bytes':43044472,'sha256':'bf1b4387cc7ca94fc6ef684f040d9d16fbf16248e181819f020736ea2053f177'}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--evidence',required=True,type=Path);parser.add_argument('--engine',action='store_true');parser.add_argument('--jdk',type=Path,default=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'));args=parser.parse_args()
 evidence=args.evidence.resolve();evidence.mkdir(parents=True,exist_ok=False)
 roster_path='native/android/tests/private-owner-source-pair5-roster.json';roster=json.loads((ROOT/roster_path).read_text());java=roster['crosscompile']['proposed_java'];swift=roster['crosscompile']['current_swift_c_h'];sources=java+swift
 if len(java)!=24 or len(swift)!=76:raise RuntimeError('selected crosscompile closure differs from explicit24/76')
 for name in sources:
  if ident((ROOT/name).read_bytes())!=roster['selected_source_identities'][name]:raise RuntimeError('selected source identity differs: '+name)
 auxiliary=[roster_path,'native/android/tests/run-private-owner-host.py','native/android/tests/run-private-owner-crosscompile.py'];frozen=support.freeze(ROOT,evidence,sources+auxiliary);save(evidence/'source-closure.json',{'java':java,'swift_c_h':swift,'auxiliary':auxiliary,'scope':'instrumentation crossbuild; AdapterInstrumentation is explicitly not a product export'})
 env=dict(os.environ)
 for key in support.STRIP:env.pop(key,None)
 env['DEVELOPER_DIR']='/Applications/Xcode_26.6.app/Contents/Developer';scratch=Path(tempfile.mkdtemp(prefix='owned-profile5-cross-',dir=evidence));tmp=scratch/'tmp';tmp.mkdir();env['TMPDIR']=str(tmp);env['TMP']=str(tmp);env['TEMP']=str(tmp)
 run=support.BoundedRun(evidence,ROOT,env);receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'unsigned Java/D8 and ordinary app-owned checklist engine Swift/JNI compilation only','native_runtime_ui_capture_process_inventory':False,'status':'failed','argv':sys.argv,'python':sys.version,'target_java_release':17,'ordinary_generated_consumer_module':'separate CLI lane; this is the frozen ordinary MixerAndroidEngine product'}
 try:
  jdk=args.jdk.resolve(strict=True);sdk=Path('/opt/homebrew/share/android-commandlinetools');android=sdk/'platforms/android-37.0/android.jar';d8=sdk/'build-tools/37.0.0/d8'
  if ident(android.read_bytes())!=ANDROID37:raise RuntimeError('pinnedSDK37 android.jar identity differs')
  env['JAVA_HOME']=str(jdk);env['PATH']=str(jdk/'bin')+os.pathsep+env.get('PATH','');tools=[jdk/'bin/javac',jdk/'bin/java',jdk/'lib/modules',jdk/'lib/server/libjvm.dylib',android,d8,d8.parent/'lib/d8.jar'];receipt['actual_tool_identities']={str(t):ident(t.resolve().read_bytes()) for t in tools};receipt['pinned_android37']=ANDROID37
  run.run('javac-version',[jdk/'bin/javac','-version']);run.run('java-version',[jdk/'bin/java','-version']);run.run('d8-version',[d8,'--version'])
  classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
  run.run('compile',[jdk/'bin/javac','-J-Djava.io.tmpdir='+str(tmp),'--release','17','-Xlint:all','-Werror','-proc:none','-classpath',android,'-sourcepath',empty,'-d',classes,*[evidence/'inputs'/s for s in java]])
  shutil.copytree(classes,evidence/'classes');classfiles=sorted(classes.rglob('*.class'));save(evidence/'classes.json',{str(p.relative_to(classes)):ident(p.read_bytes()) for p in classfiles})
  dex=scratch/'dex';dex.mkdir();run.run('dex',[d8,'--min-api','28','--lib',android,'--output',dex,*classfiles]);shutil.copytree(dex,evidence/'dex');save(evidence/'dex.json',{str(p.relative_to(dex)):ident(p.read_bytes()) for p in sorted(dex.rglob('*')) if p.is_file()})
  if args.engine:
   swift=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift');sdks=Path('/Users/andreyyurlov/.swiftpm/swift-sdks');bundle=sdks/'swift-6.3.3-RELEASE_android.artifactbundle/swift-android';ndk=bundle/'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64';clang=ndk/'bin/aarch64-linux-android28-clang';readelf=ndk/'bin/llvm-readelf'
   receipt['engine_tool_identities']={str(p):ident(p.resolve().read_bytes()) for p in (swift,clang,readelf)};run.run('swift-version',[swift,'--version']);run.run('clang-version',[clang,'--version'])
   run.run('swift-build',[swift,'build','--package-path',evidence/'inputs/native/android/engine','--scratch-path',scratch/'swift','--swift-sdks-path',sdks,'--swift-sdk','aarch64-unknown-linux-android28','--product','MixerAndroidEngine','--jobs','2','-c','release'])
   engines=list((scratch/'swift').rglob('libMixerAndroidEngine.so'))
   if len(engines)!=1:raise RuntimeError('ordinary engine output identity ambiguous')
   engine=engines[0];jni=scratch/'libmixer_android_jni.so'
   run.run('jni',[clang,'-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-I',evidence/'inputs/native/android/bridge',evidence/'inputs/native/android/bridge/jni.c','-L',engine.parent,'-lMixerAndroidEngine','-Wl,-z,max-page-size=16384','-Wl,--no-undefined','-o',jni])
   (evidence/'native-products').mkdir();shutil.copy2(engine,evidence/'native-products'/engine.name);shutil.copy2(jni,evidence/'native-products'/jni.name)
   elf_engine=run.run('elf-engine',[readelf,'--file-header','--dynamic','--dyn-syms',engine]);elf_jni=run.run('elf-jni',[readelf,'--file-header','--dynamic','--dyn-syms',jni]);
   for name,value in [('engine',elf_engine),('jni',elf_jni)]:
    if b'AArch64' not in value or b'ELF64' not in value:raise RuntimeError(name+' architecture not exact ELF64/AArch64')
   for symbol in (b'Java_dev_mixer_android_NativeBridge_create',b'Java_dev_mixer_android_NativeBridge_prepareV2',b'Java_dev_mixer_android_NativeBridge_commitV2',b'Java_dev_mixer_android_NativeBridge_abortV2',b'Java_dev_mixer_android_NativeBridge_destroy'):
    if symbol not in elf_jni:raise RuntimeError('missing JNI export '+str(symbol))
   if b'libMixerAndroidEngine.so' not in elf_jni:raise RuntimeError('JNI lacks engine dependency')
   save(evidence/'native-products.json',{p.name:ident(p.read_bytes()) for p in (engine,jni)})
  receipt['status']='passed-crosscompile-only';print('PASS profile5 Java24/SDK37/D8min28'+('/Swift/JNI' if args.engine else '')+' unsigned crosscompile; native runtime pending')
 except BaseException as failure:receipt['failure']={'type':type(failure).__name__,'message':str(failure)};raise
 finally:
  shutil.rmtree(scratch);receipt['cleanup']={'owned_scratch_removed':not scratch.exists(),'owned_children_reaped':run.reap_group(),'native_or_capture_processes_created_or_queried':False};receipt['source_stable']=all((ROOT/p).read_bytes()==b for p,b in frozen.items());save(evidence/'receipt.json',receipt)
if __name__=='__main__':main()
