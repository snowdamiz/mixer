#!/usr/bin/env python3
"""Direct admitted adapter/ordinary app Swift/JNI cross-compile; no signing or runtime."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
PACKET=Path(__file__).resolve().parent
PROFILE_RUN=PACKET/'profile-qualification-2'
OUT=PACKET/'cross-compilation-1'
PROPOSAL='80eed4b279283d073f745061eb071aff7daa7b4369cbabd9e4b97fab6ff98b8a'

def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def main():
    prior=json.loads((PROFILE_RUN/'receipt.json').read_text());assert prior['status']=='passed-host-profile2-qualification'
    proposal=json.loads((PACKET/'candidate-proposal.json').read_text())
    assert identity((PACKET/'candidate-proposal.json').read_bytes())['sha256']==PROPOSAL
    for relative,expected in proposal['files'].items():assert identity((ROOT/relative).read_bytes())==expected,relative
    app=PROFILE_RUN/'ObserverConsumer'
    driver=app/'Generated/MixerAndroid/android-build.py'
    spec=importlib.util.spec_from_file_location('admitted_actual_driver',driver);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    lock=json.loads((app/'mixer.lock').read_text());profile=m.source_profile()
    assert m.profile_lock(profile)==lock['android']['profile']
    assert profile==json.loads((PACKET/'candidate-profile-2.json').read_text())
    m.admit_source_pair(app,profile)
    OUT.mkdir(exist_ok=False);(OUT/'runner.py').write_bytes(Path(__file__).read_bytes())
    commands=[];status='failed';scratch=OUT/'scratch';scratch.mkdir();env=dict(m.ENV)
    for name in ('JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS','JDK_JAVAC_OPTIONS','CLASSPATH','JAVA_OPTS'):env.pop(name,None)
    def run(label,argv,timeout=180):
        argv=[str(p) for p in argv];start=time.time()
        p=subprocess.Popen(argv,cwd=app,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        timed=False
        try:out,err=p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed=True;os.killpg(p.pid,signal.SIGKILL);out,err=p.communicate()
        (OUT/(label+'.stdout')).write_bytes(out);(OUT/(label+'.stderr')).write_bytes(err)
        commands.append({'label':label,'argv':argv,'cwd':str(app),'exit':p.returncode,'timed_out':timed,'child_reaped':True,'elapsed_seconds':time.time()-start,'stdout':identity(out),'stderr':identity(err)})
        save(OUT/'commands.json',commands);print(label,p.returncode,flush=True)
        if p.returncode or timed:raise RuntimeError(label+' failed; retained streams')
        return out
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':[sys.executable,*sys.argv],
        'python_version':sys.version,'candidate_proposal_sha256':PROPOSAL,
        'source_profile':m.profile_lock(profile),'project_source_tree_sha256':m.source_tree(app),
        'scope':'Complete actual Android adapter against locked SDKjar, D8 min28, ordinary app-owned Swift/JNI arm64 ELF; compile-only',
        'native_runtime_capture_or_process_discovery':False,'new_dependencies':[]}
    try:
        # Installed tools, distribution hashes, and metadata are the exact creation lock.
        actual=m.inspect();save(OUT/'toolchain-observed.json',actual)
        assert actual==lock['android']['toolchain'],'installed toolchain differs from creation lock'
        receipt['android_sdk_jar']={'path':str(m.JAR),**identity(m.JAR.read_bytes())}
        run('swift-version',[m.SWIFT,'--version']);run('javac-version',[m.JDK/'bin/javac','--version']);run('java-version',[m.JDK/'bin/java','--version'])
        run('d8-version',[m.BT/'d8','--version']);run('clang-version',[m.NDK/'bin/aarch64-linux-android28-clang','--version'])
        run('revision',['git','-C',ROOT,'rev-parse','HEAD'])
        adapter=app/'Generated/MixerAndroid'
        java=[adapter/p for p in sorted(profile['adapter_files']) if p.startswith('app/src/') and p.endswith('.java')]
        assert len(java)==len(list((adapter/'app/src').rglob('*.java')))
        receipt['java_inputs']={p.relative_to(adapter).as_posix():identity(p.read_bytes()) for p in java}
        classes,empty,dex=scratch/'classes',scratch/'empty',scratch/'dex'
        classes.mkdir();empty.mkdir();dex.mkdir()
        run('javac-sdk',[m.JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-classpath',m.JAR,'-sourcepath',empty,'-d',classes,*java])
        receipt['classes']={p.relative_to(classes).as_posix():identity(p.read_bytes()) for p in sorted(classes.rglob('*.class'))}
        run('d8-min28',[m.BT/'d8','--min-api','28','--lib',m.JAR,'--output',dex,*sorted(classes.rglob('*.class'))])
        receipt['dex']={p.name:identity(p.read_bytes()) for p in sorted(dex.glob('*.dex'))}
        package=app/'Platforms/Android'
        args=[m.SWIFT,'build','--package-path',package,'--scratch-path',scratch/'swift','--swift-sdks-path',m.SWIFT_SDKS,'--swift-sdk',m.SDK_ID,'-c','release','--product','AppAndroid','-Xlinker','-z','-Xlinker','max-page-size=16384']
        run('swift-android',args,timeout=300)
        bin_path=Path(run('swift-bin-path',args+['--show-bin-path']).decode().strip())
        engine=bin_path/'libAppAndroid.so';assert engine.is_file()
        jni=scratch/'libmixer_android_jni.so'
        run('jni-clang',[m.NDK/'bin/aarch64-linux-android28-clang','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-I',adapter/'bridge',adapter/'bridge/jni.c','-L',bin_path,'-lAppAndroid','-Wl,--no-undefined','-Wl,-z,max-page-size=16384','-o',jni])
        receipt['elf']={}
        for label,path in [('app-swift',engine),('jni',jni)]:
            header=run(label+'-elf-header',[m.NDK/'bin/llvm-readelf','-h',path]).decode()
            assert 'ELF64' in header and 'AArch64' in header
            dynamic=run(label+'-elf-dynamic',[m.NDK/'bin/llvm-readelf','-d',path]).decode()
            symbols=run(label+'-symbols',[m.NDK/'bin/llvm-nm','-D','--defined-only',path]).decode()
            if label=='app-swift':
                for symbol in ['mixer_android_create','mixer_android_exchange','mixer_android_destroy','mixer_android_prepare_v2','mixer_android_commit_v2','mixer_android_abort_v2','AppFeatures','AppModels']:assert symbol in symbols,symbol
            else:
                for symbol in ['Java_dev_mixer_android_NativeBridge_create','Java_dev_mixer_android_NativeBridge_exchange','Java_dev_mixer_android_NativeBridge_prepareV2']:assert symbol in symbols,symbol
            receipt['elf'][label]={'file_name':path.name,**identity(path.read_bytes())}
        assert m.source_tree(app)==receipt['project_source_tree_sha256'],'app sources changed during crosscompile'
        m.admit_source_pair(app,profile)
        for relative,expected in proposal['files'].items():assert identity((ROOT/relative).read_bytes())==expected,relative
        status='passed-direct-cross-compilation-only'
    except BaseException as failure:
        receipt['failure']={'type':type(failure).__name__,'message':str(failure)};raise
    finally:
        shutil.rmtree(scratch)
        receipt.update(status=status,commands='commands.json',cleanup={'owned_scratch_removed':not scratch.exists(),'owned_children_reaped':all(c['child_reaped'] for c in commands),'native_or_capture_instances_created':False},pending=['Actual Android runtime/main-Looper/platform behavior','Public V2/effect-runner integration','API28-35 support','Final physical phones','Immutable published FieldLog packages','Signing/store/operational/GA qualification'])
        save(OUT/'receipt.json',receipt)

if __name__=='__main__':main()
