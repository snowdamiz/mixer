#!/usr/bin/env python3
"""One bounded API37 pair9 R2 settings-driven motion callback gate, retaining the canonical smoke oracle."""
import argparse, datetime, hashlib, importlib.util, json, os, pathlib, re, secrets, shutil, signal, socket, subprocess, sys, tempfile, time, traceback, zipfile
P=pathlib.Path
ROOT=P(__file__).resolve().parents[3]
PARENT=P('/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4')
ORIGINAL=P('/Users/andreyyurlov/.t3/worktrees/mixer/t3-5c87cbc0')
PACKET=P(__file__).resolve().parent
OUT=PACKET/'runtime-attempt'
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

def sha(p): return hashlib.sha256(P(p).read_bytes()).hexdigest()
def save(p,v): P(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def flush(): save(OUT/'receipt.json',RECEIPT)
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
from cleanup_control import Commands, finish

def require(condition, message='controller prerequisite failed'):
    if not condition:
        raise RuntimeError(message)

def launch(name,args):
    item=COMMANDS.start(name,args,WORK,long_lived=True)
    flush()
    return item

def run(name,args,timeout=120,allowed=(0,)):
    try:
        return COMMANDS.run(name,args,WORK,timeout,allowed)
    finally:
        RECEIPT['commands']=COMMANDS.records
        flush()

def tool(p):
    p=P(p)
    RECEIPT['tools'][str(p)]={'realPath':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size}

def reserve(port):
    s=socket.socket();s.bind(('127.0.0.1',port));s.listen(1);RESERVATIONS.append(s);return s.getsockname()[1]

def adb(name,tail,timeout=45,allowed=(0,)):
    return run(name,[SDK/'platform-tools/adb','-P',RECEIPT['adbServerPort'],'-s','emulator-'+str(PORT),*tail],timeout,allowed)

def main():
    global START, DEADLINE, WORK, ENV, RECEIPT, EMULATOR, SERVER, PORT, RESERVATIONS, SOURCES, COMMANDS
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewed-controller-sha256', required=True)
    args=parser.parse_args()
    require(args.reviewed_controller_sha256==sha(__file__), 'Root must dispatch the independently reviewed controller hash')
    OUT.mkdir(exist_ok=False)
    START=time.monotonic(); DEADLINE=START+600
    WORK=P(tempfile.mkdtemp(prefix='mixer-20261107-motion-r2-native-',dir='/tmp'))
    ENV=dict(os.environ,JAVA_HOME=str(JDK),DEVELOPER_DIR='/Applications/Xcode_26.6.app/Contents/Developer',ANDROID_HOME=str(SDK),ANDROID_SDK_ROOT=str(SDK),PATH=str(JDK/'bin')+os.pathsep+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
    RECEIPT={'schema':1,'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'building','scratch':str(WORK),'commands':[],'tools':{},'nativeInstancesStarted':0,'physicalTargetsQueried':False,'scope':'PAIR9-R2-MOTION-CALLBACK-NATIVE: API37 arm64 settings-only platform callback, owner drain, exact restoration/removal plus original 11-check JNI/Swift smoke','nativeAcceptance':False,'gaAcceptance':False,'buildJobs':2,'maximumSeconds':600,'runtime':{'status':'NOT RUN'},'cleanup':{},'limitations':['API37 arm64 only; API28/32/33 loading and motion boundary gates remain pending','one emulator smoke does not establish complete V2 fault/IME/lifecycle coverage','no physical-phone, external immutable FieldLog, public release, store, customer, operational or GA qualification']}
    EMULATOR=None; SERVER=None; PORT=None; RESERVATIONS=[]; SOURCES={}
    COMMANDS=Commands(OUT,ENV,deadline=DEADLINE)
    flush()
    try:
        control=json.loads((PACKET/'host-controls-optimized.json').read_text())
        require(control['status']=='passed' and control['tests']==26
            and control['controllerSHA256']==sha(__file__)
            and control['lifecycleSHA256']==sha(PACKET/'cleanup_control.py')
            and control['controlsSHA256']==sha(PACKET/'host_controls.py')
            and control['fakeDriverSHA256']==sha(PACKET/'optimized_fake_controls.py'), 'host control binding mismatch')
        real=json.loads((PACKET/'fresh-host-experiments.json').read_text())
        require(real['status']=='passed' and real['controllerSHA256']==sha(__file__)
            and real['lifecycleSHA256']==sha(PACKET/'cleanup_control.py')
            and real['driverSHA256']==sha(PACKET/'fresh_host_experiments.py')
            and len(real['experiments'])==2
            and all(e['cleanup']['allTerminalCustody'] for e in real['experiments']), 'fresh host admission mismatch')
        baseline=PARENT/'verification/plan-continuation-2026-11-07/android-runtime'
        save(OUT/'baseline-manifest.json',{'files':{str(p.relative_to(baseline)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(baseline.rglob('*')) if p.is_file()}})
        RECEIPT['sourceRevision']=run('source-revision',['git','-C',ROOT,'rev-parse','HEAD'])
        RECEIPT['sourceTree']=run('source-tree',['git','-C',ROOT,'rev-parse','HEAD^{tree}'])
        require(RECEIPT['sourceRevision']=='96f03ab65966a6374e958e780fa09a3eed814c0b', 'R2 base revision mismatch')
        binding=json.loads((PACKET/'prepared-source-binding.json').read_text())
        for rel,expected in {**binding['canonicalInputs'],**binding['implementationFiles']}.items():
            require(sha(ROOT/rel)==expected['sha256'] and (ROOT/rel).stat().st_size==expected['bytes'], rel)
        spec=importlib.util.spec_from_file_location('canonical_checker',ROOT/'scripts/ci/check-android-generated-java.py')
        checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
        profile=checker.load_profile(ROOT);canonical=checker.source_inputs(profile)
        require(len(canonical)==101 and canonical==binding['canonicalInputs'] and checker.source_digest(canonical)==binding['canonicalDigest'], 'canonical101 mismatch')
        for kind in ('sdk','adapter'):
            require(profile[kind+'_files']==binding['projections'][kind]['files'],kind+' projection mismatch')
        reuse=json.loads((PACKET/'prepared-native-reuse.json').read_text())
        require(len(reuse['currentToolsEqualOriginalBuildTools'])==33 and reuse['nativeLibraryCount']==18, 'reuse counts')
        for path,expected in reuse['currentToolsEqualOriginalBuildTools'].items():
            require(sha(path)==expected['sha256'] and P(path).stat().st_size==expected['bytes'] and str(P(path).resolve())==expected['realPath'], 'tool drift: '+path)
        run('source-status',['git','-C',ROOT,'status','--short'])
        products=sorted((ROOT/'native/android/app/src').rglob('*.java'))
        inputs=set(str(p.relative_to(ROOT)) for p in products)
        inputs.update(TESTS+[DESCRIPTOR,MANIFEST,'native/android/engine/Package.swift','sdk/Package.swift','native/android/bridge/jni.c','native/android/bridge/mixer_android.h','native/android/bridge/mixer_android_v2.h','verification/android-coordinator-apk-packaging/apk_packaging.py'])
        for folder in ['sdk/Sources','sdk/Tests','native/android/engine/Sources','native/android/engine/Tests']:
            inputs.update(str(p.relative_to(ROOT)) for p in (ROOT/folder).rglob('*') if p.is_file())
        SNAP=WORK/'inputs'
        for rel in sorted(inputs):
            src=ROOT/rel;expected=sha(src);target=SNAP/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
            require(sha(target)==expected and sha(src)==expected, rel)
            SOURCES[rel]=expected
        RECEIPT['sourceClosureSHA256']=hashlib.sha256(json.dumps(SOURCES,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        RECEIPT['productionJavaFiles']=len(products);RECEIPT['allThreeReadinessBudgetsAndTransactionPostconditionsPreserved']=True
        RECEIPT['descriptorSHA256']=SOURCES[DESCRIPTOR]
        save(OUT/'source-lock.json',{'sourceRevision':RECEIPT['sourceRevision'],'sourceTree':RECEIPT['sourceTree'],'sourceClosureSHA256':RECEIPT['sourceClosureSHA256'],'files':SOURCES})
        for rel in TESTS+[DESCRIPTOR,MANIFEST]:
            target=OUT/'canonical-inputs'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SNAP/rel,target)
        for name,args in [('python-version',[sys.executable,'--version']),('java-version',[JDK/'bin/java','--version']),('javac-version',[JDK/'bin/javac','--version']),('swift-version',[SWIFT,'--version']),('clang-version',[NDK/'bin/aarch64-linux-android28-clang','--version']),('d8-version',[BT/'d8','--version']),('aapt2-version',[BT/'aapt2','version']),('apksigner-version',[BT/'apksigner','version']),('adb-version',[SDK/'platform-tools/adb','version']),('emulator-version',[SDK/'emulator/emulator','-version'])]:run(name,args,30)
        for p in [SWIFT,SWIFT.parent/'swift-frontend',NDK/'bin/clang',NDK/'bin/llvm-readelf',JDK/'bin/java',JDK/'bin/javac',JDK/'bin/keytool',BT/'aapt2',BT/'zipalign',BT/'lib/d8.jar',BT/'lib/apksigner.jar',JAR,SDK/'emulator/emulator',SDK/'platform-tools/adb',SDK/'cmdline-tools/latest/bin/avdmanager',SDK/'system-images/android-37.0/google_apis/arm64-v8a/source.properties',ART.parent/'info.json']:tool(p)
        accepted=PARENT/'verification/plan-continuation-2026-11-07/android-toggle-oracle-integrated'
        accepted_lock=json.loads((accepted/'source-lock.json').read_text())
        accepted_receipt=json.loads((accepted/'receipt.json').read_text())
        test_rel=TESTS[1]
        source_mismatches={rel:{'expected':expected,'actual':sha(ROOT/rel)} for rel,expected in accepted_lock['files'].items() if rel not in {test_rel,'native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java'} and sha(ROOT/rel)!=expected}
        tool_mismatches={path:identity for path,identity in accepted_receipt['tools'].items() if not P(path).is_file() or sha(path)!=identity['sha256'] or str(P(path).resolve())!=identity['realPath']}
        require(accepted_receipt['runtime']['passed'] and 'checks=11' in accepted_receipt['runtime']['instrumentationOutput'])
        require(not source_mismatches, source_mismatches)
        require(not tool_mismatches, tool_mismatches)
        original=ORIGINAL/'verification/plan-continuation-2026-11-07/android-runtime'
        prior=json.loads((original/'build-receipt.json').read_text())
        original_lock=json.loads((original/'source-lock.json').read_text())
        allowed_changes=set(TESTS+['native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java','native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java'])
        original_mismatches={rel:{'expected':expected,'actual':sha(ROOT/rel)} for rel,expected in original_lock['files'].items() if rel not in allowed_changes and sha(ROOT/rel)!=expected}
        original_tool_mismatches={path:identity for path,identity in prior['tools'].items() if not P(path).is_file() or sha(path)!=identity['sha256'] or str(P(path).resolve())!=identity['realPath']}
        require(not original_mismatches, original_mismatches)
        require(not original_tool_mismatches, original_tool_mismatches)
        retained=PARENT/'verification/plan-continuation-2026-11-07/android-runtime/canonical-smoke.apk'
        require(sha(retained)==prior['apkSHA256'], 'retained original APK hash mismatch')
        build=WORK/'build';build.mkdir();libdir=build/'lib/arm64-v8a';libdir.mkdir(parents=True)
        native={name:value for name,value in prior['artifacts'].items() if name.startswith('lib/arm64-v8a/')}
        require(len(native)==18, len(native))
        require(native==accepted_receipt['nativeReuse']['nativeLibraries'], 'accepted native identities differ')
        with zipfile.ZipFile(retained) as z:
            require(set(n for n in z.namelist() if n.startswith('lib/'))==set(native))
            for name,identity in native.items():
                data=z.read(name)
                require(len(data)==identity['bytes'] and hashlib.sha256(data).hexdigest()==identity['sha256'], name)
                (libdir/P(name).name).write_bytes(data)
        RECEIPT['nativeReuse']={'retainedAPK':str(retained),'retainedAPKSHA256':prior['apkSHA256'],
            'originalBuildReceipt':str(original/'build-receipt.json'),'originalBuildReceiptSHA256':sha(original/'build-receipt.json'),
            'originalSourceLockSHA256':sha(original/'source-lock.json'),'originalSourceMismatches':original_mismatches,
            'originalToolMismatches':original_tool_mismatches,'matchingInputsExceptInstrumentation':len(accepted_lock['files'])-1,
            'acceptedReceiptSHA256':sha(accepted/'receipt.json'),'acceptedSourceLockSHA256':sha(accepted/'source-lock.json'),
            'sourceMismatches':source_mismatches,'toolMismatches':tool_mismatches,'nativeLibraries':native,
            'rebuildCount':0,'all18AcceptedNativeLibrariesMatch':True,'matchingTools':prior['tools']}
        save(OUT/'native-reuse.json',RECEIPT['nativeReuse'])
        classes=build/'production-classes';classes.mkdir();empty=build/'empty';empty.mkdir()
        run('production-java17-sdk37',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',JAR,'-d',classes,*[SNAP/str(p.relative_to(ROOT)) for p in products]],120)
        tests=build/'test-classes';tests.mkdir()
        run('canonical-instrumentation-java17-sdk37',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',str(classes)+os.pathsep+str(JAR),'-d',tests,*[SNAP/p for p in TESTS]],120)
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
            apk=build/'diagnostic-smoke.apk';run('test-apk-sign',[BT/'apksigner','sign','--ks',key,'--ks-pass','env:MIXER_ANDROID_SMOKE_PASS','--key-pass','env:MIXER_ANDROID_SMOKE_PASS','--out',apk,aligned])
        finally:
            if not COMMANDS.hold:key.unlink(missing_ok=True)
            ENV.pop('MIXER_ANDROID_SMOKE_PASS',None)
        run('test-apk-signature',[BT/'apksigner','verify','--verbose','--print-certs',apk])
        run('test-apk-alignment',[BT/'zipalign','-c','-P','16','-v','4',apk])
        spec=importlib.util.spec_from_file_location('packaging_guard',SNAP/'verification/android-coordinator-apk-packaging/apk_packaging.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
        save(OUT/'packaging-validation.json',guard.validate(apk))
        with zipfile.ZipFile(apk) as z:require(hashlib.sha256(z.read('assets/MixerAppearanceV2/descriptor.json')).hexdigest()==SOURCES[DESCRIPTOR])
        RECEIPT['artifacts']={str(p.relative_to(build)):{'bytes':p.stat().st_size,'sha256':sha(p)} for folder in [dex,libdir] for p in sorted(folder.rglob('*')) if p.is_file()}
        RECEIPT['apkPath']=str(apk);RECEIPT['apkSHA256']=sha(apk);RECEIPT['status']='built-runtime-starting';flush()
        port_attempts=[]
        for proposed in [5570,*range(5580,5682,2)]:
            count=len(RESERVATIONS)
            try:
                reserve(proposed);reserve(proposed+1);PORT=proposed;break
            except OSError:
                port_attempts.append({'portPair':[proposed,proposed+1],'status':'occupied; no device contacted'})
                while len(RESERVATIONS)>count:RESERVATIONS.pop().close()
        require(PORT is not None, 'no free private emulator port pair in finite range')
        try:serverport=reserve(63338)
        except OSError:
            port_attempts.append({'serverPort':63338,'status':'occupied; no server contacted'})
            serverport=reserve(0)
        RECEIPT['portReservations']=port_attempts
        RECEIPT['adbServerPort']=str(serverport);RECEIPT['emulatorPort']=PORT;RECEIPT['targetSerial']='emulator-'+str(PORT)
        ENV.pop('ANDROID_PREFS_ROOT',None);ENV.pop('ANDROID_SDK_HOME',None)
        for name in ['avds','android','tmp']:(WORK/name).mkdir()
        ENV.update(ANDROID_AVD_HOME=str(WORK/'avds'),ANDROID_EMULATOR_HOME=str(WORK/'android'),ANDROID_USER_HOME=str(WORK/'android'),TMPDIR=str(WORK/'tmp'),ANDROID_ADB_SERVER_PORT=str(serverport),ADB_SERVER_PORT=str(serverport),ADB_LIBUSB='0')
        ENV['ADB_VENDOR_KEYS']=str(WORK/'android/adbkey')
        run('disposable-adb-key',[SDK/'platform-tools/adb','keygen',WORK/'android/adbkey'],30)
        avdname='mixer_20261107_motion_r2_native_'+WORK.name.rsplit('-',1)[-1];avdpath=WORK/'avds'/str(avdname+'.avd')
        RECEIPT['avd']={'name':avdname,'path':str(avdpath),'systemImage':'system-images;android-37.0;google_apis;arm64-v8a'}
        run('create-owned-avd',[SDK/'cmdline-tools/latest/bin/avdmanager','--verbose','create','avd','--name',avdname,'--path',avdpath,'--package','system-images;android-37.0;google_apis;arm64-v8a','--device','pixel_6'],120)
        with (avdpath/'config.ini').open('a') as f:f.write('\nhw.cpu.ncore=2\nhw.ramSize=2048\ndisk.dataPartition.size=2G\n')
        save(OUT/'owned-avd-config.json',{'config':(avdpath/'config.ini').read_text(),'portBindCheck':str([PORT,PORT+1,serverport])+' reserved until launch'})
        for s in RESERVATIONS:s.close()
        RESERVATIONS.clear()
        SERVER=launch('owned-adb-server',[SDK/'platform-tools/adb','-P',serverport,'-s',RECEIPT['targetSerial'],'--one-device',RECEIPT['targetSerial'],'server','nodaemon'])
        COMMANDS.pause(1)
        if COMMANDS.reaped(SERVER):raise RuntimeError('private adb server failed')
        EMULATOR=launch('owned-emulator',[SDK/'emulator/emulator','-avd',avdname,'-port',PORT,'-no-window','-no-audio','-no-boot-anim','-no-snapshot','-cores','2','-memory','2048','-gpu','swiftshader','-no-metrics','-no-sim'])
        RECEIPT['nativeInstancesStarted']=1;RECEIPT['runtime']['status']='booting';flush()
        bootlimit=min(time.monotonic()+180,DEADLINE-150);booted=False
        COMMANDS.deadline=bootlimit
        try:
            for i in range(80):
                if time.monotonic()>=bootlimit-COMMANDS.cleanup_seconds or COMMANDS.reaped(EMULATOR):break
                text=adb('boot-'+str(i),['shell','getprop','sys.boot_completed'],min(8,max(0,bootlimit-time.monotonic())),allowed=(0,1))
                if text.strip()=='1':booted=True;break
                COMMANDS.pause(min(2,max(0,bootlimit-time.monotonic())))
        finally:
            COMMANDS.deadline=DEADLINE
        if not booted:raise RuntimeError('owned emulator did not boot within 180 seconds')
        runtime={}
        for prop in ['ro.kernel.qemu','ro.boot.qemu.avd_name','ro.build.version.sdk','ro.build.version.release','ro.product.cpu.abi','ro.build.fingerprint','ro.product.model']:
            runtime[prop]=adb('target-'+prop,['shell','getprop',prop])
        RECEIPT['runtime'].update(status='booted',environment=runtime)
        require(runtime['ro.kernel.qemu']=='1' and runtime['ro.boot.qemu.avd_name']==avdname, 'ownership mismatch')
        require(runtime['ro.build.version.sdk']=='37' and runtime['ro.product.cpu.abi']=='arm64-v8a', runtime)
        adb('install-diagnostic-apk',['install','--no-streaming','--no-incremental',apk],120)
        uidtext=adb('installed-package-uid',['shell','pm','list','packages','-U','dev.mixer.android.coordinator.test'])
        match=re.fullmatch(r'package:dev\.mixer\.android\.coordinator\.test uid:(\d+)',uidtext)
        require(match, uidtext)
        uid=match.group(1);RECEIPT['appUID']=uid
        logcat=launch('app-logcat-before-startup',[SDK/'platform-tools/adb','-P',serverport,'-s',RECEIPT['targetSerial'],'logcat','-v','threadtime','--uid='+uid,'*:V'])
        COMMANDS.pause(1)
        require(not COMMANDS.reaped(logcat), 'pre-startup app log capture failed')
        RECEIPT['logCaptureStartedBeforeInstrumentation']=True;flush()
        RECEIPT['settingBeforeInstrumentation']=adb('animator-raw-before',['shell','settings','get','global','animator_duration_scale'])
        output=adb('canonical-instrumentation',['shell','am','instrument','-w','-r','dev.mixer.android.coordinator.test/dev.mixer.android.NativeCoordinatorV2IntegrationInstrumentation'],120)
        passed='INSTRUMENTATION_CODE: -1' in output and 'failure=' not in output and 'cleanupFailure=' not in output
        passed=passed and all(('INSTRUMENTATION_RESULT: '+key+'=true') in output for key in ['motionRawRestored','motionEffectiveRestored','motionNoCallbackAfterRemove','motionAllTestHandlesClosed','motionOwnerListenerRemoved'])
        passed=passed and 'INSTRUMENTATION_RESULT: originalSmokeChecks=11' in output
        RECEIPT['runtime'].update(instrumentationOutput=output,passed=passed,status='passed-smoke' if passed else 'failed-smoke')
        RECEIPT['status']=RECEIPT['runtime']['status']
        COMMANDS.pause(1)
    except BaseException as e:
        RECEIPT['status']='failed';RECEIPT['failure']=str(e);(OUT/'failure.log').write_text(traceback.format_exc());print('FAILED: '+str(e),flush=True)
    finally:
        def record_restoration(report):
            RECEIPT['restoration']=report
            save(OUT/'restoration-before-cleanup.json',report)
            flush()
        report,cleanup=finish(COMMANDS,WORK,RECEIPT.get('settingBeforeInstrumentation'),
            lambda: adb('animator-raw-after',['shell','settings','get','global','animator_duration_scale'],12),
            record_restoration)
        RECEIPT['cleanup']=cleanup
        for reservation in RESERVATIONS:
            try:reservation.close()
            except BaseException as error:RECEIPT['cleanup'].setdefault('errors',[]).append(repr(error))
        post={rel:{'before':expected,'after':sha(ROOT/rel) if (ROOT/rel).is_file() else None}
              for rel,expected in SOURCES.items() if not (ROOT/rel).is_file() or sha(ROOT/rel)!=expected}
        RECEIPT['sourceStable']=not post
        save(OUT/'source-postflight.json',{'changedInputs':post,'frozenInputCount':len(SOURCES)})
        RECEIPT['cleanup']['privateADBKeysRemoved']=not (WORK/'android/adbkey').exists()
        RECEIPT['cleanup']['privateKeyRetained']=(WORK/'build/disposable-test.keystore').exists()
        RECEIPT['apkRetained']=(WORK/'build/diagnostic-smoke.apk').exists()
        baseline=PARENT/'verification/plan-continuation-2026-11-07/android-runtime'
        if (OUT/'baseline-manifest.json').exists():
            frozen=json.loads((OUT/'baseline-manifest.json').read_text())['files']
            current={str(p.relative_to(baseline)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(baseline.rglob('*')) if p.is_file()}
            RECEIPT['baselineByteForBytePreserved']=current==frozen
            save(OUT/'baseline-postflight.json',{'byteForBytePreserved':current==frozen})
        else:RECEIPT['baselineByteForBytePreserved']=None
        if (report['raw']['status']!='verified' or report['effective']['status']!='verified'
                or not RECEIPT['cleanup']['scratchRemoved'] or not RECEIPT['sourceStable']
                or RECEIPT.get('baselineByteForBytePreserved') is not True):
            RECEIPT['status']='failed'
        RECEIPT['gate']='PAIR9-R2-MOTION-CALLBACK-NATIVE'
        RECEIPT['finishedUTC']=now();RECEIPT['elapsedSeconds']=round(time.monotonic()-START,2);flush()
        print(json.dumps({k:RECEIPT.get(k) for k in ['status','failure','elapsedSeconds','sourceStable','nativeInstancesStarted']}),flush=True)
    return 0 if RECEIPT['status']=='passed-smoke' else 1

if __name__=='__main__':
    sys.exit(main())
