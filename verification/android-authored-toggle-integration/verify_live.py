"""Live integrated-source compositional rebuild; no native input or source mutation."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tarfile
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CANDIDATE=ROOT/'verification/android-authored-toggle-input/candidate-3'
BASE=ROOT/'verification/android-pointer-oracle-repair/candidate-5'
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK=Path('/opt/homebrew/share/android-commandlinetools')
BT=SDK/'build-tools/37.0.0'
JAR=SDK/'platforms/android-37.0/android.jar'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def bind(p): return {'sha256':sha(p),'bytes':p.stat().st_size}
def read(p): return json.loads(p.read_text())
def write(p,v): p.write_text(json.dumps(v,indent=2)+'\n')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

def main():
    out=HERE/'host-1';out.mkdir(exist_ok=False)
    helper=ROOT/'verification/android-coordinator-runner-cleanup/owned_process.py'
    assert sha(helper)=='209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216'
    owned=load('authored_review_owned',helper)
    work=Path(tempfile.mkdtemp(prefix='mixer-authored-root-review-'));identity=work.stat()
    commands=[];receipt={'schema':1,'status':'started','nativeRuntime':'NOT RUN','gaAccepted':False}
    env=dict(os.environ,JAVA_HOME=str(JDK),PYTHONDONTWRITEBYTECODE='1')
    def run(label,argv,allowed=(0,)):
        args=list(map(str,argv));r=owned.execute(args,cwd=ROOT,env=env,timeout=180)
        log=out/(label+'.log');log.write_bytes(r.stdout)
        commands.append({'label':label,'argv':args,'exitCode':r.returncode,'output':log.name,**bind(log),'groupCleanup':r.groupCleanup})
        assert r.returncode in allowed,(label,r.returncode)
        return r.stdout
    try:
        seal=read(CANDIDATE/'artifact-seal.json')
        actual={str(p.relative_to(CANDIDATE))for p in CANDIDATE.rglob('*')if p.is_file()and p!=CANDIDATE/'artifact-seal.json'}
        assert set(seal['files'])==actual
        for name,entry in seal['files'].items():assert bind(CANDIDATE/name)==entry,name
        locked=read(CANDIDATE/'source-lock.json')
        assert locked['sourceClosureSHA256']=='509ef6a00bbaf034ebbe9dd6d8d3b8716fe96d9600e7fe8fa92fac41ebca3f99'
        assert len(locked['files'])==106
        live_product={name:digest for name,digest in locked['files'].items() if name.startswith(('native/','sdk/'))}
        assert len(live_product)==89
        assert all(sha(ROOT/name)==digest for name,digest in live_product.items()), 'Live product source differs from native-tested candidate'
        receipt['liveProductInputs']=live_product
        for name,digest in locked['files'].items():assert sha(CANDIDATE/'inputs'/name)==digest,name
        candidate=read(CANDIDATE/'built-artifacts.json');baseline=read(BASE/'built-artifacts.json')
        expected_apk='24d75ecc19d08f44adc95e2db123936687929ca5a9fcd71f19189865240f6d18'
        apk=CANDIDATE/'coordinator-join.apk';assert sha(apk)==expected_apk
        run('java-version',[JDK/'bin/java','--version']);run('javac-version',[JDK/'bin/javac','--version'])
        run('d8-version',[BT/'d8','--version']);run('apksigner-version',[BT/'apksigner','version'])
        run('python-version',[sys.executable,'--version'])
        run('official-apksigner',[BT/'apksigner','verify','--verbose','--print-certs',apk])
        run('official-zipalign',[BT/'zipalign','-c','-P','16','-v','4',apk])
        with zipfile.ZipFile(apk) as z:
            names=z.namelist();assert len(names)==len(set(names))
            entries={n:{'bytes':len(z.read(n)),'sha256':hashlib.sha256(z.read(n)).hexdigest()}for n in names}
        assert entries==read(CANDIDATE/'apk-entries.json')
        old_entries=read(BASE/'apk-entries.json');assert set(entries)==set(old_entries)
        changed={n for n in entries if entries[n]!=old_entries[n]}
        assert changed=={'classes.dex','META-INF/DEBUG.RSA','META-INF/DEBUG.SF','META-INF/MANIFEST.MF'}
        assert len([n for n in entries if n.startswith('lib/')])==18
        with tarfile.open(BASE/'built-artifacts.tar.gz') as t:
            members=t.getmembers();assert len(members)==179 and {m.name for m in members}==set(baseline)
            for m in members:
                assert m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
                data=t.extractfile(m).read();assert {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}==baseline[m.name]
                if m.name.startswith(('production-classes/','test-classes/')):
                    dst=work/m.name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
        production=work/'production-classes';tests=work/'test-classes';empty=work/'empty';empty.mkdir()
        prefix='native/android/app/src/dev/mixer/android/'
        families=['NativeAppearanceViewsV2','NativeRenderer','AuthoredToggleInputV2']
        for p in production.rglob('*.class'):
            if p.name.split('$')[0].split('.')[0]in families:p.unlink()
        paths=[ROOT/(prefix+n+'.java')for n in families]
        run('compile-production',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',os.pathsep.join(map(str,[production,JAR])),'-d',production,*paths])
        fixtures=[CANDIDATE/'inputs/verification/android-coordinator-join'/n for n in ['CoordinatorJoinActivity.java','CoordinatorJoinInstrumentation.java']]
        originals=[ROOT/'verification/android-pointer-oracle-repair'/p.name for p in fixtures]
        assert all(p.read_bytes()==q.read_bytes() for p,q in zip(fixtures,originals))
        run('compile-unchanged-fixture',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',os.pathsep.join(map(str,[production,tests,JAR])),'-d',tests,*fixtures])
        class_files=sorted(production.rglob('*.class'))+sorted(tests.rglob('*.class'))
        rebuilt={str(p.relative_to(work)):bind(p)for p in class_files}
        expected_classes={n:e for n,e in candidate.items()if n.startswith(('production-classes/','test-classes/'))}
        assert rebuilt==expected_classes,'fresh complete class inventory differs'
        dex=work/'dex';dex.mkdir()
        run('compile-dex',[BT/'d8','--min-api','36','--lib',JAR,'--output',dex,*class_files])
        assert {str(p.relative_to(work)):bind(p)for p in dex.iterdir()}=={n:e for n,e in candidate.items()if n.startswith('dex/')}
        host=work/'host';host.mkdir()
        run('compile-policy-tests',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',production,'-d',host,CANDIDATE/'source-used/AuthoredToggleInputTest.java',HERE/'IndependentPolicyTest.java'])
        cp=os.pathsep.join(map(str,[production,host]))
        run('producer-policy-tests',[JDK/'bin/java','-ea','-cp',cp,'dev.mixer.android.AuthoredToggleInputTest'])
        run('independent-policy-tests',[JDK/'bin/java','-ea','-cp',cp,'dev.mixer.android.IndependentPolicyTest'])
        with tarfile.open(out/'fresh-class-dex-tests.tar.gz','w:gz')as t:
            for directory in [production,tests,dex,host]:
                for p in sorted(directory.rglob('*')):
                    if p.is_file():t.add(p,arcname=str(p.relative_to(work)),recursive=False)
        write(out/'fresh-artifacts.json',{str(p.relative_to(work)):bind(p)for d in [production,tests,dex,host]for p in sorted(d.rglob('*'))if p.is_file()})
        assert all(sha(ROOT/name)==digest for name,digest in live_product.items()), 'Live product changed during build'
        receipt.update(status='passed-live-integrated-source-build-and-artifact-review',candidate='candidate-3',sourceClosureSHA256=locked['sourceClosureSHA256'],apkSHA256=expected_apk,sourceInputs=106,matchedClasses=len(rebuilt),changedAPKEntries=sorted(changed),baselineFixtureBytesUnchanged=True,unchangedNativeLibraries=18)
        receipt['candidateBindings']={str((CANDIDATE/n).relative_to(ROOT)):e for n,e in seal['files'].items()}
        receipt['candidateBindings'][str((CANDIDATE/'artifact-seal.json').relative_to(ROOT))]=bind(CANDIDATE/'artifact-seal.json')
        receipt['tools']={str(p):bind(p)for p in [JDK/'bin/java',JDK/'bin/javac',BT/'d8',BT/'lib/d8.jar',BT/'zipalign',BT/'apksigner',BT/'lib/apksigner.jar',JAR,helper,Path(sys.executable)]}
    except BaseException as failure:
        receipt['status']='failed-live-integrated-source-build-review';receipt['failure']=repr(failure);raise
    finally:
        try:
            holders=run('scratch-holders',['lsof','-nP','+D',work],allowed=(1,));assert not holders
            actual=work.stat();assert (actual.st_dev,actual.st_ino)==(identity.st_dev,identity.st_ino)and not work.is_symlink()
            files=[p for p in work.rglob('*')if p.is_file()];size=sum(p.stat().st_size for p in files)
            shutil.rmtree(work)
            receipt['cleanup']={'removed':not work.exists(),'files':len(files),'bytes':size,'path':str(work),'device':identity.st_dev,'inode':identity.st_ino,'ownedGroupsEmpty':all(not c['groupCleanup']['after']for c in commands)}
        finally:
            receipt['commands']=commands;receipt['observedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat()
            receipt['reviewSource']={str(p.relative_to(ROOT)):bind(p)for p in [Path(__file__),HERE/'IndependentPolicyTest.java']}
            write(out/'receipt.json',receipt)
    print(json.dumps({k:receipt[k]for k in ['status','matchedClasses','sourceInputs','cleanup']}))

if __name__=='__main__':main()
