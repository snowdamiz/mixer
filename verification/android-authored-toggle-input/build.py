#!/usr/bin/env python3
"""Isolated host build over sealed candidate-5; no Git, native target, or runtime entry."""
import argparse,datetime,difflib,hashlib,importlib.util,json,os,re,secrets,shutil,sys,tarfile,traceback,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent.parent
BASE=ROOT/'verification/android-pointer-oracle-repair/candidate-5'
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');SDK=Path('/opt/homebrew/share/android-commandlinetools');BT=SDK/'build-tools/37.0.0';JAR=SDK/'platforms/android-37.0/android.jar'
NATIVE='native/android/app/src/dev/mixer/android/'
FAMILIES=('NativeAppearanceViewsV2','NativeRenderer','AuthoredToggleInputV2')
FILES=[NATIVE+n+'.java' for n in FAMILIES]
FIXTURES={'CoordinatorJoinActivity.java':'verification/android-coordinator-join/CoordinatorJoinActivity.java','CoordinatorJoinInstrumentation.java':'verification/android-coordinator-join/CoordinatorJoinInstrumentation.java'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bind(p):p=Path(p);return {'bytes':p.stat().st_size,'sha256':sha(p)}
def save(p,v):Path(p).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def load(n,p):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
HELPER=ROOT/'verification/android-coordinator-runner-cleanup/owned_process.py'
assert sha(HELPER)=='209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216'
owned=load('authored_owned_process',HELPER)
def family(n):
    return any(n.startswith('production-classes/dev/mixer/android/'+f) and (n[len('production-classes/dev/mixer/android/'+f):]=='.class' or n[len('production-classes/dev/mixer/android/'+f):].startswith('$')) for f in FAMILIES)
def seal(folder):
    excluded=folder/'artifact-seal.json';result={}
    for p in sorted(folder.rglob('*')):
        if p.is_symlink():raise ValueError('symlink refused '+str(p))
        if p.is_file() and p!=excluded:result[str(p.relative_to(folder))]=bind(p)
    return {'schema':1,'excludedExactPath':str(excluded.relative_to(ROOT)),'files':result}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--attempt',required=True);a=ap.parse_args()
    if not re.fullmatch(r'candidate-[1-9][0-9]*',a.attempt):ap.error('fresh candidate-N required')
    out=HERE/a.attempt;out.mkdir();work=out/'.build';work.mkdir();identity=work.stat()
    env=dict(os.environ,JAVA_HOME=str(JDK),PATH=str(JDK/'bin')+os.pathsep+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
    receipt={'schema':1,'status':'building-isolated-authored-toggle','startedUTC':now(),'commands':[],
             'sourceRevisionContext':'root reported 8c634c49; this lane uses exact copied byte closures, no Git authority claimed',
             'nativeRuntime':'NOT RUN','nativeAccepted':False,'gaAccepted':False,'nativeInstancesStarted':0,'physicalTargetsQueried':False,
             'GitCommandsExecuted':0,'ownedProcessHelper':bind(HELPER),'sourceUsed':{},'privateKeyRetained':False}
    def command(name,argv,allowed=(0,)):
        started=now();argv=list(map(str,argv));r=owned.execute(argv,cwd=ROOT,env=env,timeout=180);p=out/(name+'.log');p.write_bytes(r.stdout)
        receipt['commands'].append({'name':name,'argv':argv,'cwd':str(ROOT),'startedUTC':started,'finishedUTC':now(),'exitCode':r.returncode,'output':p.name,**bind(p),'ownedCommandGroupCleanup':r.groupCleanup})
        save(out/'receipt.json',receipt);print(name+': exit '+str(r.returncode),flush=True)
        if r.returncode not in allowed:raise RuntimeError(name+' failed; exact output retained')
        return r.stdout.decode(errors='replace')
    def upstream():
        selected=json.loads((ROOT/'verification/android-authored-toggle-root-review/selection.json').read_text())
        for n,v in selected['bindings'].items():
            if bind(ROOT/n)!=v:raise ValueError('root selected contract binding drift '+n)
        for n,v in json.loads((HERE/'input-bindings.json').read_text())['files'].items():
            if bind(HERE/'inputs'/n)!=v:raise ValueError('captured input drift '+n)
            # Parent/root may evolve other files; these two source bytes and fixture must remain immutable during build.
            if n in FILES or n.startswith('verification/android-pointer-oracle-repair/CoordinatorJoin'):
                if bind(ROOT/n)!=v:raise ValueError('live baseline source or original fixture changed '+n)
        return {'selection':bind(ROOT/'verification/android-authored-toggle-root-review/selection.json'),'bindings':len(selected['bindings'])}
    try:
        receipt['upstreamBefore']=upstream()
        used=out/'source-used';used.mkdir()
        for p in [HERE/'build.py',*sorted((HERE/'host-tests').glob('*.java'))]:
            target=used/p.name;shutil.copyfile(p,target);receipt['sourceUsed'][p.name]=bind(target)
        base_receipt=json.loads((BASE/'receipt.json').read_text());base_lock=json.loads((BASE/'source-lock.json').read_text())
        if base_receipt['apkSHA256']!='57e82e4e98cdc61581c0639603ec6efa500a66d8d2754f6b47ece89c8165d714' or base_receipt['sourceClosureSHA256']!='9082e2de1327bd0784d752db5dfbe4484751d565b3410e01e78664321467f5ce':raise ValueError('wrong sealed baseline')
        if sha(BASE/'built-artifacts.tar.gz')!='847de52459dbe90b8fd5abbe186aaf2f936cce38981cbc28ce86b36bcdc9249b':raise ValueError('baseline archive drift')
        for n,digest in base_lock['files'].items():
            src=BASE/'inputs'/n
            if sha(src)!=digest:raise ValueError('baseline source drift '+n)
            target=out/'inputs'/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
        for n in FILES:
            target=out/'inputs'/n;target.parent.mkdir(parents=True,exist_ok=True);src=HERE/'candidate-source/dev/mixer/android'/Path(n).name
            if n in base_lock['files'] and sha(HERE/'inputs'/n)!=base_lock['files'][n]:raise ValueError('captured/live baseline differs '+n)
            before=target.read_text() if target.exists() else '';after=src.read_text();target.write_text(after)
            (out/(Path(n).name+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='sealed-candidate5/'+n,tofile='isolated-authored/'+n)))
        for fixture,n in FIXTURES.items():
            if (ROOT/'verification/android-pointer-oracle-repair'/fixture).read_bytes()!=(out/'inputs'/n).read_bytes():raise ValueError('frozen fixture mismatch')
        locked={str(p.relative_to(out/'inputs')):sha(p) for p in sorted((out/'inputs').rglob('*')) if p.is_file()}
        delta={n:{'before':base_lock['files'].get(n),'after':locked[n]} for n in locked if base_lock['files'].get(n)!=locked[n]}
        if set(delta)!=set(FILES):raise ValueError('only assigned production inputs may change')
        closure=hashlib.sha256(json.dumps(locked,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        save(out/'source-lock.json',{'sourceClosureSHA256':closure,'files':locked});save(out/'source-delta.json',{'baseline':str(BASE.relative_to(ROOT)),'baselineClosureSHA256':base_lock['sourceClosureSHA256'],'changed':delta,'sourceInputs':len(locked),'unchangedInputs':len(locked)-len(delta)})
        receipt['sourceClosureSHA256']=closure;receipt['sourceInputs']=len(locked)
        tools=[JDK/'bin/java',JDK/'bin/javac',JDK/'bin/keytool',BT/'d8',BT/'lib/d8.jar',BT/'apksigner',BT/'lib/apksigner.jar',BT/'zipalign',BT/'source.properties',JAR,HELPER,Path(sys.executable)]
        receipt['tools']={str(p):{**bind(p),'realPath':str(p.resolve())} for p in tools}
        for n,argv in [('python',[sys.executable,'--version']),('java',[JDK/'bin/java','--version']),('javac',[JDK/'bin/javac','--version']),('d8',[BT/'d8','--version']),('apksigner',[BT/'apksigner','version'])]:command(n+'-version',argv)
        old=json.loads((BASE/'built-artifacts.json').read_text());old_entries=json.loads((BASE/'apk-entries.json').read_text())
        with tarfile.open(BASE/'built-artifacts.tar.gz','r:gz') as archive:
            members=archive.getmembers()
            if len(members)!=179 or len({m.name for m in members})!=179 or set(m.name for m in members)!=set(old):raise ValueError('exact baseline 179 artifacts required')
            for m in members:
                if not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts:raise ValueError('unsafe baseline member')
                data=archive.extractfile(m).read()
                if {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}!=old[m.name]:raise ValueError('artifact drift '+m.name)
                target=work/m.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        guard=load('authored_packaging_guard',ROOT/'verification/android-coordinator-apk-packaging/apk_packaging.py')
        apk=work/'coordinator-join.apk';save(out/'baseline-packaging.json',guard.validate(apk))
        command('baseline-official-zipalign',[BT/'zipalign','-c','-P','16','-v','4',apk]);command('baseline-official-apksigner',[BT/'apksigner','verify','--verbose','--print-certs',apk])
        with zipfile.ZipFile(apk) as z:
            infos=z.infolist();payloads={i.filename:z.read(i.filename) for i in infos}
        if {n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in payloads.items()}!=old_entries:raise ValueError('baseline APK entry drift')
        for n in old:
            if family(n):(work/n).unlink()
        production,tests,dex=(work/n for n in ('production-classes','test-classes','dex'));empty=work/'empty-sourcepath';empty.mkdir()
        command('production-java17-sdk37',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',os.pathsep.join(map(str,[production,JAR])),'-d',production,*[out/'inputs'/n for n in FILES]])
        host=work/'host-test-classes';host.mkdir()
        command('policy-host-tests-java17',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',production,'-d',host,used/'AuthoredToggleInputTest.java'])
        test_output=command('production-policy-host-tests',[JDK/'bin/java','-ea','-cp',os.pathsep.join(map(str,[production,host])),'dev.mixer.android.AuthoredToggleInputTest'])
        result=re.findall(r'^RESULT (.+)$',test_output,re.M)
        if len(result)!=1:raise ValueError('one host result required')
        save(out/'policy-test-results.json',json.loads(result[0]))
        command('unchanged-private-harness-java17-sdk37',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',os.pathsep.join(map(str,[production,tests,JAR])),'-d',tests,*[out/'inputs'/n for n in FIXTURES.values()]])
        for p in dex.glob('*.dex'):p.unlink()
        command('joined-d8-min36-sdk37',[BT/'d8','--min-api','36','--lib',JAR,'--output',dex,*sorted(production.rglob('*.class')),*sorted(tests.rglob('*.class'))])
        unsigned=work/'unsigned.apk'
        with zipfile.ZipFile(unsigned,'w') as z:
            for info in infos:
                if info.filename.startswith('META-INF/') or info.filename.endswith('.dex'):continue
                info.compress_type=zipfile.ZIP_STORED if info.filename=='resources.arsc' or info.filename.endswith('.so') else info.compress_type
                z.writestr(info,payloads[info.filename])
            for p in sorted(dex.glob('*.dex')):z.write(p,p.name,compress_type=zipfile.ZIP_DEFLATED)
        aligned=work/'aligned.apk';command('align-16k',[BT/'zipalign','-f','-P','16','4',unsigned,aligned]);save(out/'pre-sign-packaging.json',guard.validate(aligned))
        command('pre-sign-official-zipalign',[BT/'zipalign','-c','-P','16','-v','4',aligned])
        key=work/'disposable-debug.keystore';env['MIXER_AUTHORED_DEBUG_PASS']=secrets.token_urlsafe(32)
        try:
            command('disposable-private-debug-key',[JDK/'bin/keytool','-genkeypair','-keystore',key,'-storepass:env','MIXER_AUTHORED_DEBUG_PASS','-keypass:env','MIXER_AUTHORED_DEBUG_PASS','-alias','debug','-keyalg','RSA','-keysize','2048','-validity','30','-dname','CN=Mixer Isolated Authored Toggle Verification'])
            command('private-debug-sign',[BT/'apksigner','sign','--ks',key,'--ks-pass','env:MIXER_AUTHORED_DEBUG_PASS','--key-pass','env:MIXER_AUTHORED_DEBUG_PASS','--out',apk,aligned])
        finally:key.unlink(missing_ok=True);env.pop('MIXER_AUTHORED_DEBUG_PASS',None)
        signature=command('predispatch-official-apksigner',[BT/'apksigner','verify','--verbose','--print-certs',apk]);command('predispatch-official-zipalign',[BT/'zipalign','-c','-P','16','-v','4',apk]);save(out/'predispatch-packaging.json',guard.validate(apk))
        certs=re.findall(r'certificate SHA-256 digest: ([0-9a-f]{64})',signature)
        if len(certs)!=1:raise ValueError('one debug certificate required')
        artifacts={str(p.relative_to(work)):bind(p) for folder in [production,tests,dex,work/'apk/lib/arm64-v8a'] for p in sorted(folder.rglob('*')) if p.is_file()};artifacts['coordinator-join.apk']=bind(apk)
        changes={n:{'before':old.get(n),'after':artifacts.get(n)} for n in sorted(set(old)|set(artifacts)) if old.get(n)!=artifacts.get(n)}
        if any(not(family(n) or n.startswith('dex/') or n=='coordinator-join.apk') for n in changes):raise ValueError('unassigned class family changed')
        with zipfile.ZipFile(apk) as z:entries={i.filename:{'bytes':i.file_size,'sha256':hashlib.sha256(z.read(i.filename)).hexdigest()} for i in z.infolist()}
        entry_changes={n:{'before':old_entries.get(n),'after':entries.get(n)} for n in sorted(set(old_entries)|set(entries)) if old_entries.get(n)!=entries.get(n)}
        if set(entries)!=set(old_entries) or any(not(n.startswith('META-INF/') or n.endswith('.dex')) for n in entry_changes):raise ValueError('baseline fixture/resource/library entry changed')
        libraries={n:v for n,v in artifacts.items() if n.startswith('apk/lib/')}
        if len(libraries)!=18 or any(old.get(n)!=v for n,v in libraries.items()):raise ValueError('exact eighteen unchanged native/Swift libraries required')
        save(out/'built-artifacts.json',artifacts);save(out/'artifact-delta.json',{'changedAllowedProductionFamiliesDexAPK':changes,'unchanged':{n:v for n,v in artifacts.items() if old.get(n)==v},'retention':'changed class/dex bytes retained once; unchanged objects supplied by exact sealed baseline archive'})
        save(out/'apk-entries.json',entries);save(out/'apk-entry-delta.json',entry_changes);save(out/'abi-libraries.json',libraries)
        with tarfile.open(out/'changed-artifacts.tar.gz','w:gz') as archive:
            for n in sorted(changes):
                if n!='coordinator-join.apk' and artifacts.get(n):archive.add(work/n,arcname=n,recursive=False)
        retained=out/'coordinator-join.apk';shutil.move(apk,retained)
        receipt.update({'apk':{'path':str(retained),**bind(retained)},'debugCertificateSHA256':certs[0],'sourceInputs':len(locked),'artifactCount':len(artifacts),'productionPolicyTests':json.loads(result[0]),'unchangedLibraries':18,'changedArtifacts':list(changes),'changedAPKEntries':list(entry_changes),'baselineFixtureBytesUnchanged':True,'sourceSnapshotUnchanged':all(sha(out/'inputs'/n)==v for n,v in locked.items())})
        receipt['upstreamAfter']=upstream();receipt['status']='passed-isolated-host-policy-java17-sdk37-d8-private-apk-build-runtime-NOT-RUN'
    except BaseException as failure:
        receipt['status']='failed-isolated-attempt-retained';receipt['failure']=repr(failure);(out/'failure.log').write_text(traceback.format_exc());raise
    finally:
        (work/'disposable-debug.keystore').unlink(missing_ok=True)
        try:
            holders=command('scratch-open-holders',['/usr/sbin/lsof','-nP','+D',work],allowed=(1,))
            if holders:raise ValueError('owned scratch holder remains')
            st=work.stat()
            if (st.st_dev,st.st_ino)!=(identity.st_dev,identity.st_ino) or work.is_symlink():raise ValueError('scratch ownership mismatch')
            files=[p for p in work.rglob('*') if p.is_file()];size=sum(p.stat().st_size for p in files);shutil.rmtree(work)
            receipt['cleanup']={'path':str(work),'ownedDevice':st.st_dev,'ownedInode':st.st_ino,'filesRemoved':len(files),'bytesRemoved':size,'absent':not work.exists(),'scope':'only unique owned build extraction; all command groups empty per command receipts'}
        except BaseException as failure:receipt['cleanupFailure']=repr(failure);receipt['status']='failed-owned-cleanup';raise
        finally:
            receipt['finishedUTC']=now();save(out/'receipt.json',receipt);save(out/'artifact-seal.json',seal(out))
if __name__=='__main__':main()
