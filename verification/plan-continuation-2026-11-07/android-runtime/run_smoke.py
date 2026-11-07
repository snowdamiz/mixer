#!/usr/bin/env python3
"""One fresh canonical Android smoke; all mutable build/AVD state is owned scratch."""
import datetime, hashlib, importlib.util, json, os, pathlib, re, secrets, shutil, signal, socket, subprocess, sys, tempfile, time, traceback, zipfile
P=pathlib.Path
ROOT=P(__file__).resolve().parents[3]
OUT=P(__file__).resolve().parent
SDK=P('/opt/homebrew/share/android-commandlinetools')
JDK=P('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SWIFT=P('/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift')
SDKS=P('/Users/andreyyurlov/.swiftpm/swift-sdks')
ART=SDKS/'swift-6.3.3-RELEASE_android.artifactbundle/swift-android'
NDK=ART/'android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64'
RUNTIME=ART/'swift-resources/usr/lib/swift-aarch64/android'
BT=SDK/'build-tools/37.0.0'; JAR=SDK/'platforms/android-37.0/android.jar'
DESCRIPTOR='verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
MANIFEST='verification/android-native-v2-coordinator/AndroidManifest.future-test.xml'
TESTS=['native/android/tests/NativeCoordinatorV2IntegrationActivity.java','native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java']
START=time.monotonic(); DEADLINE=START+1100
WORK=P(tempfile.mkdtemp(prefix='mixer-20261107-android-',dir='/tmp'))
ENV=dict(os.environ,JAVA_HOME=str(JDK),DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer',ANDROID_HOME=str(SDK),ANDROID_SDK_ROOT=str(SDK),PATH=str(JDK/'bin')+os.pathsep+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
RECEIPT={'schema':1,'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'building','scratch':str(WORK),'commands':[],'tools':{},'nativeInstancesStarted':0,'physicalTargetsQueried':False,'scope':'canonical current NativeOwnerV2/NativeCoordinatorV2/JNI/Swift smoke only','nativeAcceptance':False,'gaAcceptance':False,'buildJobs':2,'runtime':{'status':'NOT RUN'},'cleanup':{},'limitations':['one emulator smoke does not establish complete V2 fault/IME/lifecycle coverage','no physical-phone, external immutable FieldLog, public release, store, customer, operational or GA qualification']}
OWNED=[]; EMULATOR=None; SERVER=None; PORT=None; RESERVATIONS=[]; SOURCES={}

def sha(p): return hashlib.sha256(P(p).read_bytes()).hexdigest()
def save(p,v): P(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def flush(): save(OUT/'receipt.json',RECEIPT)
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def stop(p):
    result={'pid':p.pid,'pgid':p.pid,'signals':[]}
    for sig in [signal.SIGTERM,signal.SIGKILL]:
        try: os.killpg(p.pid,0)
        except ProcessLookupError: break
        os.killpg(p.pid,sig);result['signals'].append(sig.name)
        until=time.monotonic()+3
        while time.monotonic()<until:
            p.poll()
            try: os.killpg(p.pid,0)
            except ProcessLookupError: break
            time.sleep(.1)
    p.poll()
    try: os.killpg(p.pid,0);result['groupAbsent']=False
    except ProcessLookupError: result['groupAbsent']=True
    return result

def launch(name,args):
    args=list(map(str,args));log=OUT/(name+'.log');stream=log.open('wb')
    entry={'name':name,'argv':args,'cwd':str(WORK),'startedUTC':now(),'output':log.name}
    p=subprocess.Popen(args,cwd=WORK,env=ENV,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    stream.close();entry.update(pid=p.pid,pgid=p.pid);RECEIPT['commands'].append(entry);OWNED.append((p,entry,log));flush();return p,entry,log

def run(name,args,timeout=120,allowed=(0,)):
    p,e,log=launch(name,args);limit=min(time.monotonic()+timeout,DEADLINE);reason=None
    while p.poll() is None:
        if time.monotonic()>limit:reason='command/global deadline';break
        if log.stat().st_size>16*1024*1024:reason='16MiB output cap';break
        time.sleep(.2)
    if reason:e['stoppedBecause']=reason
    cleanup=stop(p);e.update(exitCode=p.wait(timeout=5),finishedUTC=now(),sha256=sha(log),processCleanup=cleanup);flush()
    print(name+': '+str(e['exitCode'])+(' '+reason if reason else ''),flush=True)
    if reason or e['exitCode'] not in allowed or not cleanup['groupAbsent']:
        raise RuntimeError(name+' failed: '+(reason or str(e['exitCode']))+'; see '+log.name)
    return log.read_text(errors='replace').strip()

def tool(p):
    p=P(p)
    RECEIPT['tools'][str(p)]={'realPath':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size}

def reserve(port):
    s=socket.socket();s.bind(('127.0.0.1',port));s.listen(1);RESERVATIONS.append(s);return s.getsockname()[1]

def adb(name,tail,timeout=45,allowed=(0,)):
    return run(name,[SDK/'platform-tools/adb','-P',RECEIPT['adbServerPort'],'-s','emulator-'+str(PORT),*tail],timeout,allowed)

flush()
try:
    RECEIPT['sourceRevision']=run('source-revision',['git','-C',ROOT,'rev-parse','HEAD'])
    RECEIPT['sourceTree']=run('source-tree',['git','-C',ROOT,'rev-parse','HEAD^{tree}'])
    run('source-status',['git','-C',ROOT,'status','--short'])
    products=sorted((ROOT/'native/android/app/src').rglob('*.java'))
    inputs=set(str(p.relative_to(ROOT)) for p in products)
    inputs.update(TESTS+[DESCRIPTOR,MANIFEST,'native/android/engine/Package.swift','sdk/Package.swift','native/android/bridge/jni.c','native/android/bridge/mixer_android.h','native/android/bridge/mixer_android_v2.h','verification/android-coordinator-apk-packaging/apk_packaging.py'])
    for folder in ['sdk/Sources','sdk/Tests','native/android/engine/Sources','native/android/engine/Tests']:
        inputs.update(str(p.relative_to(ROOT)) for p in (ROOT/folder).rglob('*') if p.is_file())
    SNAP=WORK/'inputs'
    for rel in sorted(inputs):
        src=ROOT/rel;expected=sha(src);target=SNAP/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
        assert sha(target)==expected and sha(src)==expected,rel
        SOURCES[rel]=expected
    RECEIPT['sourceClosureSHA256']=hashlib.sha256(json.dumps(SOURCES,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    RECEIPT['productionJavaFiles']=len(products);RECEIPT['testOracleUnchanged']=True
    RECEIPT['descriptorSHA256']=SOURCES[DESCRIPTOR]
    save(OUT/'source-lock.json',{'sourceRevision':RECEIPT['sourceRevision'],'sourceTree':RECEIPT['sourceTree'],'sourceClosureSHA256':RECEIPT['sourceClosureSHA256'],'files':SOURCES})
    for rel in TESTS+[DESCRIPTOR,MANIFEST]:
        target=OUT/'canonical-inputs'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SNAP/rel,target)
    for name,args in [('python-version',[sys.executable,'--version']),('java-version',[JDK/'bin/java','--version']),('javac-version',[JDK/'bin/javac','--version']),('swift-version',[SWIFT,'--version']),('clang-version',[NDK/'bin/aarch64-linux-android28-clang','--version']),('d8-version',[BT/'d8','--version']),('aapt2-version',[BT/'aapt2','version']),('apksigner-version',[BT/'apksigner','version']),('adb-version',[SDK/'platform-tools/adb','version']),('emulator-version',[SDK/'emulator/emulator','-version'])]:run(name,args,30)
    for p in [SWIFT,SWIFT.parent/'swift-frontend',NDK/'bin/clang',NDK/'bin/llvm-readelf',JDK/'bin/java',JDK/'bin/javac',JDK/'bin/keytool',BT/'aapt2',BT/'zipalign',BT/'lib/d8.jar',BT/'lib/apksigner.jar',JAR,SDK/'emulator/emulator',SDK/'platform-tools/adb',SDK/'cmdline-tools/latest/bin/avdmanager',SDK/'system-images/android-37.0/google_apis/arm64-v8a/source.properties',ART.parent/'info.json']:tool(p)
    run('swift-sdk-list',[SWIFT,'sdk','list','--swift-sdks-path',SDKS],30)
    build=WORK/'build';build.mkdir();swiftbuild=build/'swift'
    run('swift-android-release',[SWIFT,'build','--package-path',SNAP/'native/android/engine','--scratch-path',swiftbuild,'--swift-sdks-path',SDKS,'--swift-sdk','aarch64-unknown-linux-android28','--product','MixerAndroidEngine','--jobs','2','-c','release'],600)
    engines=list(swiftbuild.glob('*/release/libMixerAndroidEngine.so'));assert len(engines)==1,engines
    engine=engines[0];libdir=build/'lib/arm64-v8a';libdir.mkdir(parents=True);shutil.copy2(engine,libdir/engine.name)
    run('jni-link',[NDK/'bin/aarch64-linux-android28-clang','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror','-I',SNAP/'native/android/bridge',SNAP/'native/android/bridge/jni.c','-L',engine.parent,'-lMixerAndroidEngine','-Wl,-z,max-page-size=16384','-Wl,--no-undefined','-o',libdir/'libmixer_android_jni.so'])
    deps={};pending=list(libdir.glob('*.so'));system={'libc.so','libdl.so','libm.so','liblog.so','libandroid.so'}
    while pending:
        lib=pending.pop();dynamic=run('elf-dynamic-'+lib.name,[NDK/'bin/llvm-readelf','-d',lib],30)
        needed=re.findall(r'\(NEEDED\).*\[([^\]]+)\]',dynamic);deps[lib.name]=needed
        for name in needed:
            if name in system or (libdir/name).exists():continue
            found=next((p for p in [RUNTIME/name,NDK/'sysroot/usr/lib/aarch64-linux-android'/name] if p.is_file()),None)
            if found is None:raise RuntimeError('unresolved native dependency '+name)
            tool(found);shutil.copy2(found,libdir/name);pending.append(libdir/name)
    RECEIPT['nativeDependencies']=deps
    classes=build/'production-classes';classes.mkdir();empty=build/'empty';empty.mkdir()
    run('production-java17-sdk37',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',JAR,'-d',classes,*[SNAP/str(p.relative_to(ROOT)) for p in products]],120)
    tests=build/'test-classes';tests.mkdir()
    run('canonical-instrumentation-java17-sdk37',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',str(classes)+os.pathsep+str(JAR),'-d',tests,*[SNAP/p for p in TESTS]],120)
    dex=build/'dex';dex.mkdir()
    run('canonical-d8-min28',[BT/'d8','--min-api','28','--lib',JAR,'--output',dex,*sorted(classes.rglob('*.class')),*sorted(tests.rglob('*.class'))],120)
    # Authored packaging-only resource ensures an actual resource table for the canonical manifest.
    res=build/'res/values';res.mkdir(parents=True);(res/'strings.xml').write_text('<resources><string name="private_smoke_packaging">Mixer private smoke</string></resources>\n')
    compiledres=build/'compiled-res';compiledres.mkdir()
    run('resource-compile',[BT/'aapt2','compile',res/'strings.xml','-o',compiledres])
    base=build/'base.apk'
    run('canonical-manifest-link',[BT/'aapt2','link','-I',JAR,'--manifest',SNAP/MANIFEST,'--min-sdk-version','36','--target-sdk-version','37','-o',base,*sorted(compiledres.glob('*.flat'))])
    unsigned=build/'unsigned.apk'
    with zipfile.ZipFile(base) as source,zipfile.ZipFile(unsigned,'w') as z:
        for info in source.infolist():
            info.compress_type=zipfile.ZIP_STORED if info.filename=='resources.arsc' else info.compress_type
            z.writestr(info,source.read(info.filename))
        for p in sorted(libdir.glob('*.so')):z.write(p,'lib/arm64-v8a/'+p.name,compress_type=zipfile.ZIP_STORED)
        for p in sorted(dex.glob('*.dex')):z.write(p,p.name,compress_type=zipfile.ZIP_DEFLATED)
        z.write(SNAP/DESCRIPTOR,'assets/MixerAppearanceV2/descriptor.json',compress_type=zipfile.ZIP_DEFLATED)
    aligned=build/'aligned.apk';run('align-16k',[BT/'zipalign','-f','-P','16','4',unsigned,aligned])
    key=build/'disposable-test.keystore';ENV['MIXER_ANDROID_SMOKE_PASS']=secrets.token_urlsafe(32)
    try:
        run('disposable-test-key',[JDK/'bin/keytool','-genkeypair','-keystore',key,'-storepass:env','MIXER_ANDROID_SMOKE_PASS','-keypass:env','MIXER_ANDROID_SMOKE_PASS','-alias','debug','-keyalg','RSA','-keysize','2048','-validity','1','-dname','CN=Mixer Disposable November7 Smoke'])
        apk=OUT/'canonical-smoke.apk';run('test-apk-sign',[BT/'apksigner','sign','--ks',key,'--ks-pass','env:MIXER_ANDROID_SMOKE_PASS','--key-pass','env:MIXER_ANDROID_SMOKE_PASS','--out',apk,aligned])
    finally:key.unlink(missing_ok=True);ENV.pop('MIXER_ANDROID_SMOKE_PASS',None)
    run('test-apk-signature',[BT/'apksigner','verify','--verbose','--print-certs',apk])
    run('test-apk-alignment',[BT/'zipalign','-c','-P','16','-v','4',apk])
    spec=importlib.util.spec_from_file_location('packaging_guard',SNAP/'verification/android-coordinator-apk-packaging/apk_packaging.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    save(OUT/'packaging-validation.json',guard.validate(apk))
    with zipfile.ZipFile(apk) as z:assert hashlib.sha256(z.read('assets/MixerAppearanceV2/descriptor.json')).hexdigest()==SOURCES[DESCRIPTOR]
    RECEIPT['artifacts']={str(p.relative_to(build)):{'bytes':p.stat().st_size,'sha256':sha(p)} for folder in [classes,tests,dex,libdir] for p in sorted(folder.rglob('*')) if p.is_file()}
    RECEIPT['apkSHA256']=sha(apk);RECEIPT['status']='built-runtime-starting';flush()
    for candidate in range(5570,5584,2):
        n=len(RESERVATIONS)
        try:reserve(candidate);reserve(candidate+1);PORT=candidate;break
        except OSError:
            for s in RESERVATIONS[n:]:s.close()
            del RESERVATIONS[n:]
    if PORT is None:raise RuntimeError('no reserved owned emulator port pair')
    serverport=reserve(0);RECEIPT['adbServerPort']=str(serverport);RECEIPT['emulatorPort']=PORT;RECEIPT['targetSerial']='emulator-'+str(PORT)
    for name in ['avds','emuhome','user','prefs','tmp']:(WORK/name).mkdir()
    ENV.update(ANDROID_AVD_HOME=str(WORK/'avds'),ANDROID_EMULATOR_HOME=str(WORK/'emuhome'),ANDROID_USER_HOME=str(WORK/'user'),ANDROID_PREFS_ROOT=str(WORK/'prefs'),TMPDIR=str(WORK/'tmp'),ANDROID_ADB_SERVER_PORT=str(serverport),ADB_SERVER_PORT=str(serverport),ADB_LIBUSB='0')
    avdname='mixer_20261107_android_'+WORK.name.rsplit('-',1)[-1];avdpath=WORK/'avds'/str(avdname+'.avd')
    RECEIPT['avd']={'name':avdname,'path':str(avdpath),'systemImage':'system-images;android-37.0;google_apis;arm64-v8a'}
    run('create-owned-avd',[SDK/'cmdline-tools/latest/bin/avdmanager','create','avd','--name',avdname,'--path',avdpath,'--package','system-images;android-37.0;google_apis;arm64-v8a','--device','pixel_6'],120)
    with (avdpath/'config.ini').open('a') as f:f.write('\nhw.cpu.ncore=2\nhw.ramSize=2048\ndisk.dataPartition.size=2G\n')
    save(OUT/'owned-avd-config.json',{'config':(avdpath/'config.ini').read_text(),'portBindCheck':'both emulator ports and private adb server port held until launch'})
    for s in RESERVATIONS:s.close()
    RESERVATIONS.clear()
    SERVER=launch('owned-adb-server',[SDK/'platform-tools/adb','-P',str(serverport),'-s','emulator-'+str(PORT),'-L','tcp:127.0.0.1:'+str(serverport),'fork-server','server'])
    time.sleep(1)
    if SERVER[0].poll() is not None:raise RuntimeError('private adb server failed')
    EMULATOR=launch('owned-emulator',[SDK/'emulator/emulator','-avd',avdname,'-port',PORT,'-no-window','-no-audio','-no-boot-anim','-no-snapshot','-cores','2','-memory','2048','-gpu','swiftshader','-no-metrics','-no-sim','-no-bluetooth'])
    RECEIPT['nativeInstancesStarted']=1;RECEIPT['runtime']['status']='booting';flush()
    bootlimit=min(time.monotonic()+240,DEADLINE-100);booted=False
    for i in range(80):
        if time.monotonic()>bootlimit or EMULATOR[0].poll() is not None:break
        text=adb('boot-'+str(i),['shell','getprop','sys.boot_completed'],8,allowed=(0,1))
        if text.strip()=='1':booted=True;break
        time.sleep(2)
    if not booted:raise RuntimeError('owned emulator did not boot within 240 seconds')
    runtime={}
    for prop in ['ro.build.version.sdk','ro.build.version.release','ro.product.cpu.abi','ro.build.fingerprint','ro.product.model']:
        runtime[prop]=adb('target-'+prop,['shell','getprop',prop])
    RECEIPT['runtime'].update(status='booted',environment=runtime)
    assert int(runtime['ro.build.version.sdk'])>=36 and runtime['ro.product.cpu.abi']=='arm64-v8a',runtime
    adb('install-canonical-apk',['install','--no-streaming',apk],120)
    output=adb('canonical-instrumentation',['shell','am','instrument','-w','-r','dev.mixer.android.coordinator.test/dev.mixer.android.NativeCoordinatorV2IntegrationInstrumentation'],120)
    RECEIPT['runtime'].update(instrumentationOutput=output,passed=('INSTRUMENTATION_CODE: -1' in output and 'failure=' not in output and 'cleanupFailure=' not in output),status='passed-smoke' if 'INSTRUMENTATION_CODE: -1' in output and 'failure=' not in output and 'cleanupFailure=' not in output else 'failed-smoke')
    adb('target-logcat',['logcat','-d','-v','threadtime','-t','1200'],45)
    RECEIPT['status']=RECEIPT['runtime']['status']
except BaseException as e:
    RECEIPT['status']='failed';RECEIPT['failure']=str(e);(OUT/'failure.log').write_text(traceback.format_exc());print('FAILED: '+str(e),flush=True)
finally:
    if EMULATOR is not None and EMULATOR[0].poll() is None:
        try:adb('stop-only-owned-emulator',['emu','kill'],15,allowed=(0,1))
        except BaseException as e:RECEIPT['cleanup']['gracefulEmulatorStopError']=str(e)
    groups=[]
    for p,e,log in reversed(OWNED):
        cleanup=stop(p);e.update(exitCode=p.poll(),finishedUTC=now(),sha256=sha(log),processCleanup=cleanup);groups.append(cleanup)
    for s in RESERVATIONS:s.close()
    post={rel:{'before':expected,'after':sha(ROOT/rel) if (ROOT/rel).is_file() else None} for rel,expected in SOURCES.items() if not (ROOT/rel).is_file() or sha(ROOT/rel)!=expected}
    RECEIPT['sourceStable']=not post;save(OUT/'source-postflight.json',{'changedInputs':post,'frozenInputCount':len(SOURCES),'snapshotStable':all((WORK/'inputs'/rel).is_file() and sha(WORK/'inputs'/rel)==expected for rel,expected in SOURCES.items())})
    portresults={}
    if PORT is not None:
        for port in [PORT,PORT+1,int(RECEIPT['adbServerPort'])]:
            s=socket.socket()
            try:s.bind(('127.0.0.1',port));portresults[str(port)]='released'
            except OSError as e:portresults[str(port)]=str(e)
            finally:s.close()
    RECEIPT['cleanup'].update(groups=groups,allOwnedGroupsClosed=all(x['groupAbsent'] for x in groups),ports=portresults,privateKeyRetained=False)
    if RECEIPT['cleanup']['allOwnedGroupsClosed']:
        shutil.rmtree(WORK);RECEIPT['cleanup']['scratchRemoved']=not WORK.exists()
    else:RECEIPT['cleanup']['scratchRemoved']=False
    RECEIPT['finishedUTC']=now();RECEIPT['elapsedSeconds']=round(time.monotonic()-START,2);flush()
    print(json.dumps({k:RECEIPT.get(k) for k in ['status','failure','elapsedSeconds','sourceStable','nativeInstancesStarted']}),flush=True)
