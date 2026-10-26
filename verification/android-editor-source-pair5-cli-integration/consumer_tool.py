"""Construct explicit cross-tool commands over the generated app-owned closure."""
import json, pathlib, subprocess, sys, os
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE/'consumers/PairFiveConsumer'
PROFILE=json.loads((HERE/'inputs/profile5.json').read_text())
JDK=pathlib.Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK=pathlib.Path('/opt/homebrew/share/android-commandlinetools')
ART=pathlib.Path.home()/'.swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android'
NDK=ART/'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64'
ADAPTER=ROOT/'Generated/MixerAndroid'
os.environ['JAVA_HOME']=str(JDK)
os.environ['PATH']=str(JDK/'bin')+os.pathsep+os.environ.get('PATH','')
mode=sys.argv[1]; config=sys.argv[2] if len(sys.argv)>2 else ''
relocated=mode.startswith('relocated-')
if relocated:
    mode=mode.removeprefix('relocated-');ROOT=HERE/'consumers/RelocatedConsumer';ADAPTER=ROOT/'Generated/MixerAndroid'
prefix='relocated-app-' if relocated else 'app-'
artifact=HERE/'artifacts/relocated' if relocated else HERE/'artifacts'
if mode=='java':
    output=HERE/'scratch/java-classes';output.mkdir(parents=True,exist_ok=True)
    sources=[ADAPTER/p for p in sorted(PROFILE['adapter_files']) if p.endswith('.java')]
    assert len(sources)==18
    command=[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath','','-classpath',SDK/'platforms/android-37.0/android.jar','-d',output,*sources]
    label='generated-product18-sdk37-javac'
elif mode=='d8':
    output=HERE/'scratch/java-dex';output.mkdir(parents=True,exist_ok=True)
    command=[SDK/'build-tools/37.0.0/d8','--min-api','28','--lib',SDK/'platforms/android-37.0/android.jar','--output',output,*sorted((HERE/'scratch/java-classes').rglob('*.class'))]
    label='generated-product18-min28-d8-02'
elif mode=='jni':
    assert config in ['debug','release']
    lib=HERE/f'scratch/{prefix}{config}/aarch64-unknown-linux-android28/{config}'
    output=artifact/config;output.mkdir(parents=True,exist_ok=True)
    command=[NDK/'bin/aarch64-linux-android28-clang','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-I',ADAPTER/'bridge',ADAPTER/'bridge/jni.c','-L',lib,'-lAppAndroid','-Wl,--no-undefined','-Wl,-z,max-page-size=16384','-o',output/'libmixer_android_jni.so']
    label=f'generated-app-{config}-jni'
elif mode in ['readelf','symbols','jni-readelf','jni-symbols']:
    assert config in ['debug','release']
    lib=HERE/f'scratch/{prefix}{config}/aarch64-unknown-linux-android28/{config}/libAppAndroid.so'
    if mode.startswith('jni-'): lib=artifact/config/'libmixer_android_jni.so'
    command=[NDK/'bin/llvm-readelf','-h','-d',lib] if mode.endswith('readelf') else [NDK/'bin/llvm-nm','-D','--defined-only',lib]
    label=f'generated-app-{config}-{mode}'
else: raise ValueError(mode)
if relocated: label='relocated-'+label
result=subprocess.run([sys.executable,str(HERE/'run.py'),label,*map(str,command)])
sys.exit(result.returncode)
