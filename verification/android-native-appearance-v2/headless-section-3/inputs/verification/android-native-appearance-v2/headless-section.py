#!/usr/bin/env python3
"""Seal compile-only Section evidence while native runtime/computer use is paused."""
import datetime, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SDK=Path('/opt/homebrew/share/android-commandlinetools')
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
JAR=SDK/'platforms/android-37.0/android.jar'
D8=SDK/'build-tools/37.0.0/d8'
PRODUCT=[f'native/android/app/src/dev/mixer/android/{name}.java'for name in ['Json','UiPacket','AppearanceDescriptorV2','AppearanceGeometryV2','AppearanceResolverV2','AppearanceNativePathsV2','NativeEnvironmentV2','InstalledAppearanceV2','NativeAppearanceViewsV2','NativeRenderer']]
TESTS=[f'native/android/tests/NativeAppearanceV2{name}.java'for name in ['Activity','Instrumentation']]
INPUTS=PRODUCT+TESTS+['AGENTS.md','mixer-product-plan.md','docs/ui-measured-appearance-v2-contract.md','docs/native-appearance-v2-staging.md','docs/native-appearance-v2-implementation-boundary.md','docs/android-native-appearance-v2.md','verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json','verification/android-native-appearance-v2/qualify.py','verification/android-native-appearance-v2/headless-section.py','verification/android-native-appearance-v2/AndroidManifest.xml','verification/android-native-appearance-v2/computer-use-pause-cleanup.json','verification/apple-native-appearance-v2/shared-fixture/native-packet-v1.bin','verification/apple-native-appearance-v2/shared-fixture/descriptor.json']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
 if len(sys.argv)!=2 or not re.fullmatch(r'headless-section-[0-9]+',sys.argv[1]):raise SystemExit('bounded headless-section-N output required')
 out=HERE/sys.argv[1];out.mkdir();build=HERE/'build'/sys.argv[1];build.mkdir()
 env=dict(os.environ,JAVA_HOME=str(JDK),PATH=str(JDK/'bin')+os.pathsep+os.environ['PATH'])
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip()
 working=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
 manifest={};commands=[];status='failed';error=None
 for name in INPUTS:
  target=out/'inputs'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target);manifest[name]=sha(target)
 def run(name,args):
  argv=list(map(str,args));result=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,timeout=120)
  log=out/(name+'.log');log.write_bytes(result.stdout+result.stderr)
  commands.append(dict(name=name,argv=argv,cwd=str(ROOT),exitCode=result.returncode,output=str(log.relative_to(ROOT)),sha256=sha(log)))
  print(name,result.returncode,flush=True)
  if result.returncode:raise RuntimeError(name+': '+(result.stdout+result.stderr).decode(errors='replace')[-4000:])
  return result.stdout.decode()
 try:
  for name,args in [('python-version',[sys.executable,'--version']),('java-version',[JDK/'bin/java','--version']),('javac-version',[JDK/'bin/javac','--version']),('d8-version',[D8,'--version'])]:run(name,args)
  production=build/'production';production.mkdir()
  run('production-java-compile',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-classpath',JAR,'-d',production,*[out/'inputs'/x for x in PRODUCT]])
  bytecode=run('native-renderer-bytecode',[JDK/'bin/javap','-c','-p','-classpath',production,'dev.mixer.android.NativeRenderer'])
  constructor=bytecode.split('dev.mixer.android.NativeRenderer(android.content.Context, dev.mixer.android.NativeRenderer$Events);',1)[1].split('  private int dp(',1)[0]
  if any(name in constructor for name in ['java/util/Map.of','NativeAppearanceViewsV2','NativeEnvironmentV2']):raise RuntimeError('eager V2/API30 dependency in legacy constructor')
  pdex=build/'production-dex';pdex.mkdir();run('production-dex-min28',[D8,'--min-api','28','--lib',JAR,'--output',pdex,*sorted(production.rglob('*.class'))])
  classes=build/'instrumentation';classes.mkdir()
  run('instrumentation-java-compile',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-classpath',JAR,'-d',classes,*[out/'inputs'/x for x in PRODUCT+TESTS]])
  tdex=build/'instrumentation-dex';tdex.mkdir();run('instrumentation-dex-min36',[D8,'--min-api','36','--lib',JAR,'--output',tdex,*sorted(classes.rglob('*.class'))])
  status='passed-headless-java-and-dex-only'
 except Exception as failure:error=repr(failure);raise
 finally:
  unchanged=all(sha(ROOT/name)==digest for name,digest in manifest.items())
  receipt=dict(status=status if unchanged else 'failed-source-changed',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceRevision=revision,sourceTree=tree,workingTreeStatusAtStart=working,sourceManifest=manifest,sourceClosureSHA256=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest(),sourceUnchanged=unchanged,commands=commands,toolSHA256={str(x):sha(x)for x in [JAR,SDK/'build-tools/37.0.0/lib/d8.jar',JDK/'bin/java',JDK/'bin/javac']},artifacts={str(x.relative_to(HERE)):sha(x)for pattern in ['*.class','*.dex']for x in build.rglob(pattern)},nativeSectionRegression='pending-user-resumption-of-computer-use-and-native-runtime',screenshots='not-run-user-paused',emulator='not-booted',error=error,scope='Headless compile and DEX packaging only. Actual Section native measurements/layout/RTL/screenshots are pending; candidate15 is historical pre-Section-fix evidence. No adb, emulator, native runtime, screen capture or computer-use command executed. Minimum28 DEX compile is not API28 runtime support. Product prototype floor36, exercised historical API37 only; phones, engine/JNI coordinator, public support, resources/fonts, signed V2/FieldLog/stores/GA pending.')
  (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
  (out/'artifact-seal.json').write_text(json.dumps({str(x.relative_to(out)):sha(x)for x in sorted(out.rglob('*'))if x.is_file()},indent=2,sort_keys=True)+'\n')
  if not unchanged and error is None:raise RuntimeError('source changed during headless verification')
 print(status)

if __name__=='__main__':main()
