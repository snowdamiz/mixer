#!/usr/bin/env python3
"""Build fixture-only minimum scroll extent correction over exact selected production bytes; host only."""
import argparse,gzip,json,os,re,secrets,shutil,tarfile,traceback,zipfile
from pathlib import Path
import support as common
HERE=common.HERE;ROOT=common.ROOT;BASE=common.BASE;JDK=common.JDK;BT=common.BT;JAR=common.JAR

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--attempt',required=True);ap.add_argument('--production',required=True);a=ap.parse_args()
    if not re.fullmatch(r'supplement-[1-9][0-9]*',a.attempt) or not re.fullmatch(r'candidate-[1-9][0-9]*',a.production):ap.error('fresh contained attempt and production required')
    baseline=common.PRODUCER/a.production;out=HERE/a.attempt;out.mkdir();work=out/'.build';work.mkdir();identity=work.stat()
    env=dict(os.environ,JAVA_HOME=str(JDK),PATH=str(JDK/'bin')+os.pathsep+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
    receipt={'schema':1,'status':'building-separate-component-supplement','startedUTC':common.now(),'commands':[],
             'nativeRuntime':'NOT RUN','nativeAccepted':False,'gaAccepted':False,'nativeInstancesStarted':0,'physicalTargetsQueried':False,'GitCommandsExecuted':0,'privateKeyRetained':False,
             'scope':'component actual NativeAppearanceViewsV2.Record with fixture Input; fixture acknowledgements are not engine commits; unchanged baseline matrix remains required'}
    def command(name,argv,allowed=(0,)):
        argv=list(map(str,argv));start=common.now();r=common.owned.execute(argv,cwd=ROOT,env=env,timeout=180);log=out/(name+'.log');log.write_bytes(r.stdout)
        receipt['commands'].append({'name':name,'argv':argv,'cwd':str(ROOT),'startedUTC':start,'finishedUTC':common.now(),'exitCode':r.returncode,'output':log.name,**common.bind(log),'ownedCommandGroupCleanup':r.groupCleanup});common.save(out/'receipt.json',receipt);print(name+': exit '+str(r.returncode),flush=True)
        if r.returncode not in allowed:raise RuntimeError(name+' failed; output retained')
        return r.stdout.decode(errors='replace')
    def exact_seal(folder):
        data=json.loads((folder/'artifact-seal.json').read_text());actual=common.seal(folder)
        if data!=actual:raise ValueError('exact production attempt seal drift')
        return common.bind(folder/'artifact-seal.json')
    try:
        receipt['upstreamBefore']=common.upstream();receipt['productionSeal']=exact_seal(baseline);r=json.loads((baseline/'receipt.json').read_text());receipt['productionSourceClosureSHA256']=r['sourceClosureSHA256'];receipt['productionAPK']=r['apk']
        if r['status']!='passed-isolated-host-policy-java17-sdk37-d8-private-apk-build-runtime-NOT-RUN':raise ValueError('successful host production artifact required')
        used=out/'source-used';used.mkdir()
        for p in [HERE/'build.py',HERE/'support.py',*sorted((HERE/'fixture').glob('*'))]:
            if not p.is_file() or p.is_symlink():raise ValueError('plain supplementary source required')
            shutil.copyfile(p,used/p.name)
        locked={p.name:common.bind(p) for p in sorted(used.iterdir())};closure=__import__('hashlib').sha256(json.dumps({'productionClosure':r['sourceClosureSHA256'],'supplementInputs':locked},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        common.save(out/'source-lock.json',{'sourceClosureSHA256':closure,'productionClosureSHA256':r['sourceClosureSHA256'],'supplementInputs':locked})
        receipt['sourceClosureSHA256']=closure;receipt['tools']={str(p):{**common.bind(p),'realPath':str(p.resolve())} for p in [JDK/'bin/java',JDK/'bin/javac',JDK/'bin/keytool',BT/'d8',BT/'lib/d8.jar',BT/'aapt2',BT/'apksigner',BT/'lib/apksigner.jar',BT/'zipalign',BT/'source.properties',JAR,common.HELPER]}
        for n,argv in [('java',[JDK/'bin/java','--version']),('javac',[JDK/'bin/javac','--version']),('d8',[BT/'d8','--version']),('aapt2',[BT/'aapt2','version']),('apksigner',[BT/'apksigner','version'])]:command(n+'-version',argv)
        old=json.loads((BASE/'built-artifacts.json').read_text());expected=json.loads((baseline/'built-artifacts.json').read_text())
        with tarfile.open(BASE/'built-artifacts.tar.gz','r:gz') as z:
            for m in z.getmembers():
                if not m.isfile() or m.name not in old or Path(m.name).is_absolute() or '..' in Path(m.name).parts:raise ValueError('unsafe baseline archive')
                if not m.name.startswith(('production-classes/','apk/lib/')):continue
                data=z.extractfile(m).read()
                if {'bytes':len(data),'sha256':__import__('hashlib').sha256(data).hexdigest()}!=old[m.name]:raise ValueError('baseline object drift')
                p=work/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        with tarfile.open(baseline/'changed-artifacts.tar.gz','r:gz') as z:
            for m in z.getmembers():
                if not m.isfile() or m.name not in expected or Path(m.name).is_absolute() or '..' in Path(m.name).parts:raise ValueError('unsafe production overlay')
                if not m.name.startswith('production-classes/'):continue
                data=z.extractfile(m).read()
                if {'bytes':len(data),'sha256':__import__('hashlib').sha256(data).hexdigest()}!=expected[m.name]:raise ValueError('overlay drift')
                p=work/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        production=work/'production-classes';prod={str(p.relative_to(work)):common.bind(p) for p in sorted(production.rglob('*.class'))}
        if prod!={n:v for n,v in expected.items() if n.startswith('production-classes/')}:raise ValueError('exact production class inventory required')
        common.save(out/'production-class-inventory.json',prod)
        empty=work/'empty-sourcepath';empty.mkdir();tests=work/'supplement-classes';tests.mkdir();dex=work/'dex';dex.mkdir()
        command('separate-component-harness-java17-sdk37',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',os.pathsep.join(map(str,[production,JAR])),'-d',tests,*sorted(used.glob('*.java'))])
        classes={str(p.relative_to(work)):common.bind(p) for p in sorted(tests.rglob('*.class'))};common.save(out/'supplement-class-inventory.json',classes)
        command('component-d8-min36-sdk37',[BT/'d8','--min-api','36','--lib',JAR,'--output',dex,*sorted(production.rglob('*.class')),*sorted(tests.rglob('*.class'))])
        unsigned=work/'unsigned.apk';command('component-official-aapt2-manifest',[BT/'aapt2','link','-I',JAR,'--manifest',used/'AndroidManifest.xml','--min-sdk-version','36','--target-sdk-version','37','-o',unsigned])
        with zipfile.ZipFile(r['apk']['path']) as baseline_apk:
            descriptor=baseline_apk.read('assets/MixerAppearanceV2/descriptor.json');base_resources=baseline_apk.read('resources.arsc')
        with zipfile.ZipFile(unsigned,'a') as z:
            # aapt2's empty resource table is byte identical; only private manifest belongs to this fixture.
            if z.read('resources.arsc')!=base_resources:raise ValueError('unchanged empty resource table required')
            for p in sorted((work/'apk/lib/arm64-v8a').glob('*.so')):z.write(p,'lib/arm64-v8a/'+p.name,compress_type=zipfile.ZIP_STORED)
            for p in dex.glob('*.dex'):z.write(p,p.name,compress_type=zipfile.ZIP_DEFLATED)
            z.writestr('assets/MixerAppearanceV2/descriptor.json',descriptor,compress_type=zipfile.ZIP_DEFLATED)
            z.write(used/'supplement-contract.json','assets/AuthoredToggleSupplement/contract.json',compress_type=zipfile.ZIP_DEFLATED)
        aligned=work/'aligned.apk';command('align-16k',[BT/'zipalign','-f','-P','16','4',unsigned,aligned])
        guard=common.load('authored_supplement_packaging',ROOT/'verification/android-coordinator-apk-packaging/apk_packaging.py');common.save(out/'pre-sign-packaging.json',guard.validate(aligned));command('pre-sign-official-zipalign',[BT/'zipalign','-c','-P','16','-v','4',aligned])
        apk=work/'authored-toggle-supplement.apk';key=work/'disposable-debug.keystore';env['MIXER_SUPPLEMENT_DEBUG_PASS']=secrets.token_urlsafe(32)
        try:
            command('disposable-debug-key',[JDK/'bin/keytool','-genkeypair','-keystore',key,'-storepass:env','MIXER_SUPPLEMENT_DEBUG_PASS','-keypass:env','MIXER_SUPPLEMENT_DEBUG_PASS','-alias','debug','-keyalg','RSA','-keysize','2048','-validity','30','-dname','CN=Mixer Isolated Component Supplement'])
            command('private-debug-sign',[BT/'apksigner','sign','--ks',key,'--ks-pass','env:MIXER_SUPPLEMENT_DEBUG_PASS','--key-pass','env:MIXER_SUPPLEMENT_DEBUG_PASS','--out',apk,aligned])
        finally:key.unlink(missing_ok=True);env.pop('MIXER_SUPPLEMENT_DEBUG_PASS',None)
        signature=command('predispatch-official-apksigner',[BT/'apksigner','verify','--verbose','--print-certs',apk]);command('predispatch-official-zipalign',[BT/'zipalign','-c','-P','16','-v','4',apk]);common.save(out/'predispatch-packaging.json',guard.validate(apk))
        certs=re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})',signature)
        if len(certs)!=1:raise ValueError('single disposable certificate required')
        command('official-private-manifest-dump',[BT/'aapt2','dump','xmltree',apk,'--file','AndroidManifest.xml'])
        with zipfile.ZipFile(apk) as z:entries={i.filename:{'bytes':i.file_size,'sha256':__import__('hashlib').sha256(z.read(i.filename)).hexdigest()} for i in z.infolist()}
        base_entries=json.loads((common.SCROLL/'supplement-1/apk-entries.json').read_text());libs={n:v for n,v in entries.items() if n.startswith('lib/')}
        if len(libs)!=18 or any(base_entries[n]!=v for n,v in libs.items()):raise ValueError('unchanged native library inventory required')
        common.save(out/'apk-entries.json',entries);common.save(out/'abi-libraries.json',libs)
        allowed_entry_changes={'AndroidManifest.xml','classes.dex','assets/AuthoredToggleSupplement/contract.json'}
        changed_entries={n for n in set(base_entries)|set(entries) if base_entries.get(n)!=entries.get(n)}
        if any(n not in allowed_entry_changes and not n.startswith('META-INF/') for n in changed_entries):raise ValueError('unexpected component APK change')
        common.save(out/'apk-entry-delta.json',{'changedEntries':sorted(changed_entries),'unchangedResources':entries['resources.arsc']==base_entries['resources.arsc'],'unchangedDescriptor':entries['assets/MixerAppearanceV2/descriptor.json']==base_entries['assets/MixerAppearanceV2/descriptor.json']})
        common.save(out/'built-artifacts.json',{**prod,**classes,**{str(p.relative_to(work)):common.bind(p) for p in dex.glob('*.dex')}})
        with tarfile.open(out/'supplement-class-dex.tar.gz','w:gz') as z:
            for p in [*sorted(tests.rglob('*.class')),*sorted(dex.glob('*.dex'))]:z.add(p,arcname=str(p.relative_to(work)),recursive=False)
        # Retain final executable exactly once, compressed; root preinstall must decompress and verify uncompressed hash.
        executable=common.bind(apk);retained=out/'authored-toggle-supplement.apk.gz'
        with apk.open('rb') as src,retained.open('wb') as dst:
            with gzip.GzipFile(filename='',fileobj=dst,mode='wb',mtime=0) as gz:shutil.copyfileobj(src,gz)
        with gzip.open(retained,'rb') as gz:
            digest=__import__('hashlib').sha256();size=0
            while chunk:=gz.read(1048576):digest.update(chunk);size+=len(chunk)
        if {'bytes':size,'sha256':digest.hexdigest()}!=executable:raise ValueError('compressed executable replay failed')
        receipt['upstreamAfter']=common.upstream()
        receipt.update({'status':'passed-separate-component-java17-sdk37-d8-private-apk-build-runtime-NOT-RUN','apk':executable,'retainedExecutable':{'path':str(retained),**common.bind(retained),'encoding':'gzip exact final APK bytes'},'debugCertificateSHA256':certs[0],'unchangedProductionClasses':len(prod),'supplementClasses':len(classes),'unchangedLibraries':18,'resourcesBytesUnchanged':True,'baselineFixtureUntouched':True,'productionSealAfter':exact_seal(baseline)})
    except BaseException as failure:
        receipt['status']='failed-component-build-retained';receipt['failure']=repr(failure);(out/'failure.log').write_text(traceback.format_exc());raise
    finally:
        (work/'disposable-debug.keystore').unlink(missing_ok=True)
        try:
            holders=command('scratch-open-holders',['/usr/sbin/lsof','-nP','+D',work],allowed=(1,))
            if holders:raise ValueError('owned scratch holder remains')
            st=work.stat()
            if (st.st_dev,st.st_ino)!=(identity.st_dev,identity.st_ino) or work.is_symlink():raise ValueError('scratch ownership mismatch')
            files=[p for p in work.rglob('*') if p.is_file()];size=sum(p.stat().st_size for p in files);shutil.rmtree(work)
            receipt['cleanup']={'path':str(work),'ownedDevice':st.st_dev,'ownedInode':st.st_ino,'filesRemoved':len(files),'bytesRemoved':size,'absent':not work.exists(),'scope':'only unique owned build extraction; all command groups empty'}
        except BaseException as failure:receipt['status']='failed-owned-cleanup';receipt['cleanupFailure']=repr(failure);raise
        finally:receipt['finishedUTC']=common.now();common.save(out/'receipt.json',receipt);common.save(out/'artifact-seal.json',common.seal(out))
if __name__=='__main__':main()
