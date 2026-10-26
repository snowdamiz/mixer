#!/usr/bin/env python3
"""Owned Android packaging using official Swift/NDK/SDK/JDK tools; no Gradle plugins."""
import os,pathlib,subprocess,shutil,re,json,hashlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2];HERE=ROOT/'native/android';BUILD=HERE/'build';BUILD.mkdir(exist_ok=True)
SDK=pathlib.Path(os.environ.get('ANDROID_HOME','/opt/homebrew/share/android-commandlinetools'))
JDK=pathlib.Path(os.environ.get('MIXER_JDK','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
SWIFT=pathlib.Path(os.environ.get('MIXER_SWIFT','/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift'))
SWIFT_SDKS=pathlib.Path('/Users/andreyyurlov/.swiftpm/swift-sdks');ART=SWIFT_SDKS/'swift-6.3.3-RELEASE_android.artifactbundle/swift-android'
NDK=ART/'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64';RUNTIME=ART/'swift-resources/usr/lib/swift-aarch64/android';BT=SDK/'build-tools/37.0.0';JAR=SDK/'platforms/android-37.0/android.jar'
ENV=os.environ.copy();ENV['DEVELOPER_DIR']='/Applications/Xcode_26.6.app/Contents/Developer';ENV['JAVA_HOME']=str(JDK);ENV['PATH']=str(JDK/'bin')+os.pathsep+ENV['PATH'];commands=[]
def run(args):
 args=list(map(str,args));p=subprocess.run(args,cwd=ROOT,env=ENV,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);commands.append({'command':args,'exit_code':p.returncode,'output':p.stdout});print(p.stdout,end='');
 if p.returncode:raise RuntimeError('command failed: '+repr(args))
 return p.stdout
run([SWIFT,'build','--package-path',HERE/'engine','--swift-sdks-path',SWIFT_SDKS,'--swift-sdk','aarch64-unknown-linux-android28','-c','release'])
engine=HERE/'engine/.build/aarch64-unknown-linux-android28/release/libMixerAndroidEngine.so'
if not engine.exists():
 candidates=list((HERE/'engine/.build').glob('*/release/libMixerAndroidEngine.so'));assert len(candidates)==1,candidates;engine=candidates[0]
for directory in [BUILD/'apk',BUILD/'classes',BUILD/'dex']:
 if directory.exists():shutil.rmtree(directory)
libdir=BUILD/'apk/lib/arm64-v8a';libdir.mkdir(parents=True,exist_ok=True)
run([NDK/'bin/aarch64-linux-android28-clang','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-I',HERE/'bridge',HERE/'bridge/jni.c','-L',engine.parent,'-lMixerAndroidEngine','-Wl,-z,max-page-size=16384','-o',libdir/'libmixer_android_jni.so'])
shutil.copy2(engine,libdir/engine.name)
readelf=NDK/'bin/llvm-readelf';system={'libc.so','libdl.so','libm.so','liblog.so','libandroid.so'};pending=list(libdir.glob('*.so'));dependencies={}
while pending:
 lib=pending.pop();text=run([readelf,'-d',lib]);needed=re.findall(r'\(NEEDED\).*\[([^\]]+)\]',text);dependencies[lib.name]=needed
 for name in needed:
  if name in system or (libdir/name).exists():continue
  candidates=[RUNTIME/name,NDK/'sysroot/usr/lib/aarch64-linux-android'/name]
  found=next((p for p in candidates if p.exists()),None)
  if found is None:raise RuntimeError('unresolved native dependency '+name)
  shutil.copy2(found,libdir/name);pending.append(libdir/name)
classes=BUILD/'classes';classes.mkdir(exist_ok=True);sources=sorted((HERE/'app/src').rglob('*.java'))
run([JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-classpath',JAR,'-d',classes,*sources])
dex=BUILD/'dex';dex.mkdir(exist_ok=True)
run([BT/'d8','--min-api','28','--lib',JAR,'--output',dex,*sorted(classes.rglob('*.class'))])
unsigned=BUILD/'unsigned.apk'
run([BT/'aapt2','link','-I',JAR,'--manifest',HERE/'app/AndroidManifest.xml','--min-sdk-version','28','--target-sdk-version','37','-o',unsigned])
# Standard ZIP container is assembled locally; all source remains independently authored.
import zipfile
with zipfile.ZipFile(unsigned,'a',compression=zipfile.ZIP_DEFLATED)as apk:
 for p in sorted((BUILD/'apk').rglob('*')):
  if p.is_file():apk.write(p,p.relative_to(BUILD/'apk'))
 for p in dex.glob('*.dex'):apk.write(p,p.name)
aligned=BUILD/'aligned.apk';run([BT/'zipalign','-f','-p','4',unsigned,aligned])
key=BUILD/'development.keystore'
if not key.exists():run([JDK/'bin/keytool','-genkeypair','-keystore',key,'-storepass','android','-keypass','android','-alias','development','-keyalg','RSA','-keysize','2048','-validity','365','-dname','CN=Mixer Local Development'])
apk=BUILD/'mixer-android-debug.apk';run([BT/'apksigner','sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android','--out',apk,aligned]);run([BT/'apksigner','verify','--verbose',apk]);
receipt={'apk':str(apk.relative_to(ROOT)),'apk_bytes':apk.stat().st_size,'apk_sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'native_dependencies':dependencies,'commands':commands,'scope':'local debug APK with official Swift Android SDK and native widgets; no production signing/distribution or FieldLog qualification'}
(BUILD/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('APK:',apk,'SHA256:',receipt['apk_sha256'])
