#!/usr/bin/env python3
"""Prepare exact-product API28 private APK. This program cannot launch an emulator."""
import datetime, hashlib, json, os, pathlib, secrets, shutil, signal, struct, subprocess, sys, tempfile, time, traceback, zipfile
P = pathlib.Path
OUT = P(__file__).resolve().parent
ROOT = OUT.parents[2]
PARENT = P('/Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4')
EVIDENCE = PARENT / 'verification/plan-continuation-2026-11-07'
PAIR = P('/tmp/mixer-20261107-generated-java-pair8-03')
SDK = P('/opt/homebrew/share/android-commandlinetools')
JDK = P('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
BT = SDK / 'build-tools/37.0.0'
JAR = SDK / 'platforms/android-37.0/android.jar'
DEX_SHA = '5ab1fbfcb805ee0ce43a8c131ffe51ef66f64d4614d9c13bffe7f86283e65c67'
TESTS = ['native/android/tests/NativeLowerApiCompatibilityActivity.java', 'native/android/tests/NativeLowerApiCompatibilityInstrumentation.java']
MANIFEST = 'native/android/tests/lower-api/AndroidManifest.xml'
ENV = dict(os.environ, JAVA_HOME=str(JDK), PATH=str(JDK/'bin')+os.pathsep+os.environ['PATH'], PYTHONDONTWRITEBYTECODE='1')
START = time.monotonic()
RECEIPT = {'schema':1, 'gate':'PAIR8-LOWER-API-ART-LINKAGE', 'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status':'preparing', 'runtime':'NOT RUN: explicit Android lane release required', 'emulatorsCreated':0, 'emulatorsStarted':0, 'commands':[], 'tools':{}, 'productJavaRecompiled':False, 'nativeRebuildCount':0, 'physicalDevicesQueried':False, 'fullV2Below36Supported':False, 'GAQualified':False}

def sha(p):
    h=hashlib.sha256()
    with P(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def identity(p): return {'bytes':P(p).stat().st_size, 'sha256':sha(p)}
def save(p,v): P(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def flush(): save(OUT/'prepared.json',RECEIPT)

def stop(p):
    p.poll()
    try: os.killpg(p.pid,0); alive=True
    except ProcessLookupError: alive=False
    if alive:
        os.killpg(p.pid,signal.SIGTERM)
        end=time.monotonic()+2
        while time.monotonic()<end:
            p.poll()
            try: os.killpg(p.pid,0)
            except ProcessLookupError: break
            time.sleep(.05)
        else:
            try: os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError: pass
    try: p.wait(timeout=3); reaped=True
    except subprocess.TimeoutExpired: reaped=False
    end=time.monotonic()+2
    absent=False
    while time.monotonic()<end:
        try: os.killpg(p.pid,0)
        except ProcessLookupError: absent=True; break
        time.sleep(.05)
    return {'pid':p.pid,'ownedPGID':p.pid,'leaderReaped':reaped,'groupAbsent':absent}

def run(name,args,work,timeout=120):
    if time.monotonic()-START>900: raise RuntimeError('15 minute preparation bound exhausted')
    args=list(map(str,args)); log=OUT/(name+'.log')
    entry={'label':name,'argv':args,'cwd':str(work),'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'output':log.name}
    with log.open('wb') as f:
        p=subprocess.Popen(args,cwd=work,env=ENV,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    end=time.monotonic()+timeout; failure=None
    while p.poll() is None:
        if time.monotonic()>end: failure='timeout'; break
        if log.stat().st_size>16*1024*1024: failure='16MiB output cap'; break
        time.sleep(.1)
    cleanup=stop(p)
    entry.update(exitCode=p.poll(),cleanup=cleanup,outputIdentity=identity(log),failure=failure)
    RECEIPT['commands'].append(entry); flush()
    print(name,entry['exitCode'],flush=True)
    if failure or p.returncode!=0 or not cleanup['groupAbsent'] or not cleanup['leaderReaped']:
        raise RuntimeError(name+' failed; see '+str(log))
    return log.read_text(errors='replace').strip()

def descriptors(data):
    assert data[:8]==b'dex\n039\0'
    assert struct.unpack_from('<I',data,32)[0]==len(data)
    assert hashlib.sha1(data[32:]).digest()==data[12:32]
    import zlib
    assert zlib.adler32(data[12:])&0xffffffff==struct.unpack_from('<I',data,8)[0]
    strings_n,strings_o,types_n,types_o=struct.unpack_from('<IIII',data,56)
    def string(index):
        assert index<strings_n
        offset=struct.unpack_from('<I',data,strings_o+index*4)[0]
        while data[offset]&128: offset+=1
        offset+=1
        return data[offset:data.index(b'\0',offset)].decode('utf-8')
    types=[string(struct.unpack_from('<I',data,types_o+i*4)[0]) for i in range(types_n)]
    count,offset=struct.unpack_from('<II',data,96)
    names=[types[struct.unpack_from('<I',data,offset+i*32)[0]] for i in range(count)]
    assert len(set(names))==count
    return set(names)

def validate_payload(product,test,native,z):
    assert hashlib.sha256(product).hexdigest()==DEX_SHA and len(product)==417304
    pd=descriptors(product);td=descriptors(test)
    assert len(pd)==387
    assert not pd.intersection(td), sorted(pd.intersection(td))
    assert z.read('classes.dex')==product and z.read('classes2.dex')==test
    assert {n for n in z.namelist() if n.startswith('lib/')}==set(native)
    for n,i in native.items():
        b=z.read(n);assert len(b)==i['bytes'] and hashlib.sha256(b).hexdigest()==i['sha256'],n
    return {'productClasses':len(pd),'testClasses':len(td),'duplicateClassDescriptors':[], 'exactProductDEX':True,'exact18NativeLibraries':True}

def main():
    if (OUT/'prepared.json').exists():
        raise RuntimeError('A preparation receipt already exists. Preserve this failed attempt; no automatic rerun is authorized.')
    work=P(tempfile.mkdtemp(prefix='mixer-api28-prep-',dir='/tmp'))
    RECEIPT['scratch']=str(work);flush()
    try:
        assert run('source-head',['git','rev-parse','HEAD'],ROOT)=='c531cfc81cf89cdd591835fedd1dba5a414d31c9'
        RECEIPT['sourceRevision']='c531cfc81cf89cdd591835fedd1dba5a414d31c9'
        RECEIPT['sourceTree']=run('source-tree',['git','rev-parse','HEAD^{tree}'],ROOT)
        RECEIPT['sourceInputs']={p:identity(ROOT/p) for p in TESTS+[MANIFEST]}
        RECEIPT['sourceInputSHA256']=hashlib.sha256(json.dumps(RECEIPT['sourceInputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        bound=EVIDENCE/'generated-java-pair8-acceptance.json'
        RECEIPT['parentAcceptance']={'path':str(bound),**identity(bound)}
        for label,args in [('java-version',[JDK/'bin/java','--version']),('javac-version',[JDK/'bin/javac','--version']),('d8-version',[BT/'d8','--version']),('aapt2-version',[BT/'aapt2','version']),('apksigner-version',[BT/'apksigner','version'])]: run(label,args,work,30)
        for p in [JDK/'bin/java',JDK/'bin/javac',JDK/'bin/keytool',BT/'aapt2',BT/'zipalign',BT/'lib/d8.jar',BT/'lib/apksigner.jar',JAR]:
            RECEIPT['tools'][str(p)]={'realPath':str(p.resolve()),**identity(p)}
        original=PAIR/'debug-original';product_path=original/'dex/classes.dex'
        product=product_path.read_bytes();assert hashlib.sha256(product).hexdigest()==DEX_SHA
        RECEIPT['productDEX']={'path':str(product_path),**identity(product_path),'classDefinitions':len(descriptors(product))}
        all6={}
        for consumer in ['debug-original','debug-relocated','debug-exported','release-original','release-relocated','release-exported']:
            p=PAIR/consumer/'dex/classes.dex';all6[consumer]=identity(p);assert p.read_bytes()==product
        RECEIPT['all6ProductDEXIdentical']=all6
        classes=sorted((original/'classes').rglob('*.class'));assert len(classes)==215
        RECEIPT['retained215Classfiles']={str(p.relative_to(original/'classes')):identity(p) for p in classes}
        # Native-only closure is unchanged. Product Java is independently bound to exact pair8 DEX.
        reuse_path=EVIDENCE/'android-toggle-oracle-integrated/native-reuse.json'
        reuse=json.loads(reuse_path.read_text());baseline=EVIDENCE/'android-runtime'
        lock=json.loads((baseline/'source-lock.json').read_text())
        native_sources={rel:expected for rel,expected in lock['files'].items() if rel.startswith(('sdk/Sources/','native/android/engine/Sources/','native/android/bridge/')) or rel in ['sdk/Package.swift','native/android/engine/Package.swift']}
        assert native_sources
        mismatches={rel:sha(ROOT/rel) for rel,expected in native_sources.items() if sha(ROOT/rel)!=expected};assert not mismatches,mismatches
        tool_mismatches={path:identity(P(path)) for path,expected in reuse['matchingTools'].items() if sha(P(path))!=expected['sha256'] or str(P(path).resolve())!=expected['realPath']};assert not tool_mismatches,tool_mismatches
        retained=P(reuse['retainedAPK']);assert sha(retained)==reuse['retainedAPKSHA256']
        assert sha(baseline/'build-receipt.json')==reuse['buildReceiptSHA256']
        assert sha(baseline/'source-lock.json')==reuse['sourceLockSHA256']
        native=reuse['nativeLibraries'];assert len(native)==18
        RECEIPT['nativeReuse']={'acceptedReuseProof':{'path':str(reuse_path),**identity(reuse_path)},'acceptedRunner':identity(EVIDENCE/'android-toggle-oracle-integrated/run_native_probe.py'),'originalAPK':{'path':str(retained),**identity(retained)},'buildReceipt':identity(baseline/'build-receipt.json'),'sourceLock':identity(baseline/'source-lock.json'),'nativeSourceFiles':native_sources,'nativeSourceMismatches':mismatches,'toolsChecked':reuse['matchingTools'],'toolMismatches':tool_mismatches,'libraries':native,'rebuildCount':0}
        install_path=EVIDENCE/'android-api28-image-install/receipt.json';install=json.loads(install_path.read_text())
        image=P(install['target']);actual={str(p.relative_to(image)):identity(p) for p in sorted(image.rglob('*')) if p.is_file()}
        assert actual==install['installedFiles']
        RECEIPT['installedImage']={'receipt':{'path':str(install_path),**identity(install_path)},'package':install['package'],'files':actual,'fileCount':len(actual),'totalBytes':sum(i['bytes'] for i in actual.values()),'packageXMLRevision':2,'sourcePropertiesRevision':1,'metadataDiscrepancy':install['metadataDiscrepancy'],'sourcePropertiesRaw':(image/'source.properties').read_text(),'publisherArchive':install['expectedArchive'],'runtimeAPIAndABI':'NOT RUN'}
        for path,expected in install['protectedTools'].items(): assert identity(path)==expected,path
        RECEIPT['protectedTools']=install['protectedTools']
        empty=work/'empty';empty.mkdir();test_classes=work/'test-classes';test_classes.mkdir()
        run('harness-javac',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-classpath',str(JAR)+os.pathsep+str(original/'classes'),'-d',test_classes,*[ROOT/p for p in TESTS]],work)
        product_jar=work/'product-classpath.jar'
        with zipfile.ZipFile(product_jar,'w') as z:
            for p in classes:z.write(p,str(p.relative_to(original/'classes')))
        dex=work/'dex';dex.mkdir()
        inputs=sorted(test_classes.rglob('*.class'))
        run('harness-only-d8',[BT/'d8','--min-api','28','--lib',JAR,'--classpath',product_jar,'--output',dex,*inputs],work)
        test=(dex/'classes.dex').read_bytes()
        RECEIPT['harnessClassfiles']={str(p.relative_to(test_classes)):identity(p) for p in inputs}
        # Retain rejected compiler output before the fail-closed descriptor check.
        (OUT/'classes2.dex').write_bytes(test)
        for p in inputs:
            target=OUT/'harness-classfiles'/p.relative_to(test_classes)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        overlap=sorted(descriptors(product).intersection(descriptors(test)))
        RECEIPT['descriptorCheck']={'product':sorted(descriptors(product)),
            'harness':sorted(descriptors(test)),'overlap':overlap}
        RECEIPT['testDEX']=identity(OUT/'classes2.dex');flush()
        assert not overlap, 'test DEX duplicates product class descriptors: '+repr(overlap)
        res=work/'res/values';res.mkdir(parents=True);(res/'strings.xml').write_text('<resources><string name="private_linkage">Mixer API28 private linkage</string></resources>\n')
        compiled=work/'compiled';compiled.mkdir()
        run('aapt2-compile',[BT/'aapt2','compile',res/'strings.xml','-o',compiled],work)
        base=work/'base.apk';run('test-manifest-link',[BT/'aapt2','link','-I',JAR,'--manifest',ROOT/MANIFEST,'--min-sdk-version','28','--target-sdk-version','28','-o',base,*sorted(compiled.glob('*.flat'))],work)
        unsigned=work/'unsigned.apk'
        with zipfile.ZipFile(base) as source,zipfile.ZipFile(retained) as libs,zipfile.ZipFile(unsigned,'w') as z:
            for i in source.infolist():z.writestr(i,source.read(i.filename))
            z.writestr('classes.dex',product,compress_type=zipfile.ZIP_DEFLATED)
            z.writestr('classes2.dex',test,compress_type=zipfile.ZIP_DEFLATED)
            for name,i in native.items():
                b=libs.read(name);assert len(b)==i['bytes'] and hashlib.sha256(b).hexdigest()==i['sha256'];z.writestr(name,b,compress_type=zipfile.ZIP_STORED)
        aligned=work/'aligned.apk';run('zipalign',[BT/'zipalign','-f','-P','16','4',unsigned,aligned],work)
        key=work/'private.keystore';ENV['MIXER_API28_KEY_PASS']=secrets.token_urlsafe(32)
        try:
            run('disposable-signing-key',[JDK/'bin/keytool','-genkeypair','-keystore',key,'-storepass:env','MIXER_API28_KEY_PASS','-keypass:env','MIXER_API28_KEY_PASS','-alias','debug','-keyalg','RSA','-keysize','2048','-validity','2','-dname','CN=Mixer disposable API28 linkage'],work)
            apk=OUT/'lower-api-private.apk';run('sign-private-apk',[BT/'apksigner','sign','--ks',key,'--ks-pass','env:MIXER_API28_KEY_PASS','--key-pass','env:MIXER_API28_KEY_PASS','--out',apk,aligned],work)
        finally:
            key.unlink(missing_ok=True);ENV.pop('MIXER_API28_KEY_PASS',None)
        run('verify-signature',[BT/'apksigner','verify','--verbose','--print-certs',apk],work)
        run('verify-alignment',[BT/'zipalign','-c','-P','16','4',apk],work)
        run('inspect-packaged-manifest',[BT/'aapt2','dump','badging',apk],work)
        with zipfile.ZipFile(apk) as z: RECEIPT['packagingChecks']=validate_payload(product,test,native,z)
        controls={}
        with zipfile.ZipFile(apk) as z:
            for name,badproduct,badtest in [('changed-product',product[:-1]+bytes([product[-1]^1]),test),('duplicate-product-in-test',product,product)]:
                try:validate_payload(badproduct,badtest,native,z)
                except AssertionError:controls[name]='refused'
                else:raise AssertionError('tamper control accepted '+name)
        RECEIPT['negativeControls']=controls
        RECEIPT['apk']={'path':str(apk),**identity(apk)};RECEIPT['testDEX']=identity(OUT/'classes2.dex')
        RECEIPT['status']='PREPARED; awaiting explicit Android lane release'
    except BaseException as failure:
        RECEIPT['status']='FAILED PREPARATION';RECEIPT['failure']=repr(failure)
        (OUT/'preparation-failure.log').write_text(traceback.format_exc())
        raise
    finally:
        shutil.rmtree(work)
        RECEIPT['cleanup']={'scratchRemoved':not work.exists(),'signingKeyRetained':False,'allOwnedCommandsTerminal':all(x['cleanup']['groupAbsent'] and x['cleanup']['leaderReaped'] for x in RECEIPT['commands']),'noAVDCreated':True,'noADBServerStarted':True,'noPortsReserved':True}
        RECEIPT['elapsedSeconds']=round(time.monotonic()-START,3);flush()

if __name__=='__main__':main()
