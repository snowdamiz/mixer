#!/usr/bin/env python3
"""Exact-source unsigned Java/D8 and ordinary engine/JNI cross-compilation; never runtime qualification."""
import argparse,datetime,hashlib,json,os,shutil,signal,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def identity(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,value):p.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--evidence',required=True,type=Path);parser.add_argument('--engine',action='store_true');args=parser.parse_args()
 evidence=args.evidence.resolve();evidence.mkdir(parents=True,exist_ok=False)
 roster=json.loads((ROOT/'verification/android-private-owner-effect-roster-amendment/required-host-roster.json').read_text())
 java=roster['closures']['B-concrete-renderer-views']['actual_production_sources']+['native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java']+['native/android/app/src/dev/mixer/android/'+name+'.java' for name in ('NativeBridge','MixerActivity','AdapterInstrumentation')]+['native/android/tests/'+name+'.java' for name in ('NativeAppearanceV2Activity','NativeAppearanceV2Instrumentation','AppearanceNativePathsV2Instrumentation','NativeCoordinatorV2IntegrationActivity','NativeCoordinatorV2IntegrationInstrumentation')]
 tracked=subprocess.check_output(['git','ls-files','-z','--','native/android/engine','sdk','native/android/bridge'],cwd=ROOT).decode().split('\0')
 swift=[s for s in tracked if s and Path(s).suffix in ('.swift','.c','.h')]
 sources=java+swift+[str(Path(__file__).relative_to(ROOT))];frozen={s:(ROOT/s).read_bytes() for s in sources}
 for source,data in frozen.items():
  target=evidence/'inputs'/source;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 save(evidence/'source-map.json',{s:identity(b) for s,b in frozen.items()})
 commands=[];env=dict(os.environ)
 for key in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS','SWIFT_EXEC','SWIFT_DRIVER_SWIFT_FRONTEND_EXEC'):env.pop(key,None)
 env['DEVELOPER_DIR']='/Applications/Xcode_26.6.app/Contents/Developer'
 scratch=Path(tempfile.mkdtemp(prefix='owner-cross-',dir=evidence));receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'unsigned cross-compilation only; no APK/signing, simulator/emulator, UI/capture or native execution','status':'failed','argv':sys.argv,'python':sys.version}
 def run(label,argv,timeout=120):
  outpath=evidence/(label+'.stdout');errpath=evidence/(label+'.stderr');start=time.monotonic();timed=overflow=False
  with outpath.open('wb') as out,errpath.open('wb') as err:
   child=subprocess.Popen([str(v) for v in argv],cwd=ROOT,env=env,stdout=out,stderr=err,start_new_session=True)
   try:
    while child.poll() is None:
     timed=time.monotonic()-start>timeout;overflow=max(outpath.stat().st_size,errpath.stat().st_size)>8_000_000
     if timed or overflow:os.killpg(child.pid,signal.SIGKILL);break
     time.sleep(.05)
   finally:
    if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
    child.wait()
  commands.append({'label':label,'argv':[str(v) for v in argv],'exit':child.returncode,'seconds':time.monotonic()-start,'timeout':timed,'output_limit_exceeded':overflow,'child_reaped':True,'stdout':identity(outpath.read_bytes()),'stderr':identity(errpath.read_bytes())});save(evidence/'commands.json',commands)
  if child.returncode or timed or overflow:raise RuntimeError(label+' failed')
  return outpath.read_bytes()
 try:
  jdk=Path('/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home').resolve();sdk=Path('/opt/homebrew/share/android-commandlinetools');android=sdk/'platforms/android-37.0/android.jar';d8=sdk/'build-tools/37.0.0/d8'
  env['JAVA_HOME']=str(jdk);env['PATH']=str(jdk/'bin')+os.pathsep+env.get('PATH','');tools=[jdk/'bin/javac',jdk/'bin/java',android,d8];receipt['revision']=run('revision',['git','rev-parse','HEAD']).decode().strip();receipt['tools']={str(p):identity(p.read_bytes()) for p in tools};run('javac-version',[jdk/'bin/javac','-version']);run('java-version',[jdk/'bin/java','-version']);run('d8-version',[d8,'--version'])
  classes=scratch/'classes';classes.mkdir();empty=scratch/'empty';empty.mkdir()
  run('compile',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',android,'-sourcepath',empty,'-d',classes,*[evidence/'inputs'/s for s in java]])
  shutil.copytree(classes,evidence/'classes');classfiles=sorted(classes.rglob('*.class'));save(evidence/'classes.json',{str(p.relative_to(classes)):identity(p.read_bytes()) for p in classfiles})
  dex=scratch/'dex';dex.mkdir();run('dex',[d8,'--min-api','28','--lib',android,'--output',dex,*classfiles]);shutil.copytree(dex,evidence/'dex');save(evidence/'dex.json',{str(p.relative_to(dex)):identity(p.read_bytes()) for p in sorted(dex.rglob('*')) if p.is_file()})
  if args.engine:
   swift=Path('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift');sdks=Path('/Users/andreyyurlov/.swiftpm/swift-sdks');bundle=sdks/'swift-6.3.3-RELEASE_android.artifactbundle/swift-android';ndk=bundle/'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64';clang=ndk/'bin/aarch64-linux-android28-clang';readelf=ndk/'bin/llvm-readelf'
   receipt['engine_tools']={str(p):identity(p.resolve().read_bytes()) for p in (swift,clang,readelf)};run('swift-version',[swift,'--version']);run('clang-version',[clang,'--version'])
   run('swift-build',[swift,'build','--package-path',evidence/'inputs/native/android/engine','--scratch-path',scratch/'swift','--swift-sdks-path',sdks,'--swift-sdk','aarch64-unknown-linux-android28','--product','MixerAndroidEngine','-c','release'],600)
   engines=list((scratch/'swift').rglob('libMixerAndroidEngine.so'))
   if len(engines)!=1:raise RuntimeError('ordinary engine output identity ambiguous')
   engine=engines[0];jni=scratch/'libmixer_android_jni.so'
   run('jni',[clang,'-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-I',evidence/'inputs/native/android/bridge',evidence/'inputs/native/android/bridge/jni.c','-L',engine.parent,'-lMixerAndroidEngine','-Wl,-z,max-page-size=16384','-Wl,--no-undefined','-o',jni])
   (evidence/'native-products').mkdir();shutil.copy2(engine,evidence/'native-products'/engine.name);shutil.copy2(jni,evidence/'native-products'/jni.name)
   run('elf-engine',[readelf,'--file-header','--dynamic','--dyn-syms',engine]);run('elf-jni',[readelf,'--file-header','--dynamic','--dyn-syms',jni]);save(evidence/'native-products.json',{p.name:identity(p.read_bytes()) for p in (engine,jni)})
  receipt['status']='passed-crosscompile-only';print('PASS private owner explicit Java/SDK/D8'+('/Swift/JNI' if args.engine else '')+' cross-compilation; native execution pending')
 except BaseException as failure:receipt['failure']={'type':type(failure).__name__,'message':str(failure)};raise
 finally:
  shutil.rmtree(scratch);receipt['cleanup']={'scratch_removed':not scratch.exists(),'children_reaped':all(c['child_reaped'] for c in commands),'native_or_capture_processes_created_or_queried':False};receipt['source_stable']=all((ROOT/s).read_bytes()==b for s,b in frozen.items());save(evidence/'receipt.json',receipt)
if __name__=='__main__':main()
