#!/usr/bin/env python3
"""Independently recompile four supplement classes and DEX; bounded host-only attempts."""
import argparse
import datetime
import os
from pathlib import Path
import re
import shutil
import sys
import tarfile
import traceback
import zipfile
import support

JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
SDK = Path('/opt/homebrew/share/android-commandlinetools')
BT = SDK/'build-tools/37.0.0'
JAR = SDK/'platforms/android-37.0/android.jar'

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--attempt',required=True); args=parser.parse_args()
    if not re.fullmatch(r'host-[1-9][0-9]*',args.attempt): parser.error('fresh host-N required')
    out=support.HERE/args.attempt; out.mkdir(); work=out/'.build'; work.mkdir(); owner=work.stat()
    helper=support.HELPER
    if support.sha(helper)!=support.HELPER_SHA: raise ValueError('helper drift')
    owned=support.load('authored_runner_host_owned',helper)
    env=dict(os.environ,JAVA_HOME=str(JDK),PATH=str(JDK/'bin')+os.pathsep+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
    receipt={'schema':1,'status':'started','startedUTC':now(),'commands':[],'nativeRuntime':'NOT RUN','nativeInstancesStarted':0,'physicalTargetsQueried':False,'GitCommandsExecuted':0,'nativeAccepted':False,'gaAccepted':False}
    used=out/'source-used';used.mkdir()
    for p in support.HERE.glob('*.py'):shutil.copyfile(p,used/p.name)
    shutil.copyfile(support.HERE/'runner-contract.json',used/'runner-contract.json')
    def command(name,argv,allowed=(0,),timeout=180):
        argv=list(map(str,argv));started=now();result=owned.execute(argv,cwd=support.ROOT,env=env,timeout=timeout)
        log=out/(name+'.log');log.write_bytes(result.stdout)
        receipt['commands'].append({'name':name,'argv':argv,'cwd':str(support.ROOT),'startedUTC':started,'finishedUTC':now(),'exitCode':result.returncode,'output':log.name,**support.bind(log),'ownedCommandGroupCleanup':result.groupCleanup})
        support.save(out/'receipt.json',receipt);print(name+': exit '+str(result.returncode),flush=True)
        if result.returncode not in allowed:raise RuntimeError(name+' failed; raw output retained')
        return result.stdout
    try:
        before=support.frozen('supplement');support.save(out/'input-identity-before.json',before)
        tools=support.read(support.HERE/'runner-contract.json')['toolBindings'];receipt['tools']={n:support.bind(n) for n in tools}
        if any(v['sha256']!=tools[n] for n,v in receipt['tools'].items()):raise ValueError('tool drift')
        for name,argv in [('python-version',[sys.executable,'--version']),('java-version',[JDK/'bin/java','--version']),('javac-version',[JDK/'bin/javac','--version']),('d8-version',[BT/'d8','--version']),('aapt2-version',[BT/'aapt2','version']),('apksigner-version',[BT/'apksigner','version'])]:command(name,argv)
        command('producer-replay',[sys.executable,'-B',support.PRODUCER/'check_packet.py','--candidate','candidate-3','--supplement','supplement-3'])
        command('fresh-f01-f07-controls',[sys.executable,'-B',support.TIMING/'test_host.py','--work',work/'upstream-tests','--results',out/'upstream-test-results.json'])
        upstream=support.read(out/'upstream-test-results.json')
        if upstream['executed']!=55 or upstream['failures'] or upstream['errors'] or len(upstream['exactFiveControls'])!=5:raise ValueError('exact55 corrected guards required')
        artifacts=work/'objects';artifacts.mkdir();expected=support.extract(artifacts,'supplement')
        production=artifacts/'production-classes';classes=work/'fresh-supplement';classes.mkdir();empty=work/'empty';empty.mkdir();dex=work/'fresh-dex';dex.mkdir()
        if len(list(production.rglob('*.class')))!=159:raise ValueError('exact159 production classes')
        java=sorted((support.SUPPLEMENT/'source-used').glob('*.java'))
        command('compile-four-supplement-classes',[JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',empty,'-classpath',os.pathsep.join(map(str,[production,JAR])),'-d',classes,*java])
        fresh={'supplement-classes/'+str(p.relative_to(classes)):support.bind(p) for p in sorted(classes.rglob('*.class'))}
        if len(fresh)!=4 or fresh!=support.read(support.SUPPLEMENT/'supplement-class-inventory.json'):raise ValueError('fresh exact four-class inventory differs')
        command('compile-exact-component-dex',[BT/'d8','--min-api','36','--lib',JAR,'--output',dex,*sorted(production.rglob('*.class')),*sorted(classes.rglob('*.class'))])
        fresh_dex={'dex/'+p.name:support.bind(p) for p in dex.iterdir()}
        if fresh_dex!={n:v for n,v in expected.items() if n.startswith('dex/')}:raise ValueError('fresh component DEX differs')
        apk=artifacts/'coordinator-join.apk'
        signature=command('official-supplement-apksigner',[BT/'apksigner','verify','--verbose','--print-certs',apk])
        if re.findall(rb'certificate SHA-256 digest: ([0-9a-f]{64})',signature)!=[before['debugCertificateSHA256'].encode()]:raise ValueError('supplement certificate differs')
        command('official-supplement-zipalign',[BT/'zipalign','-c','-P','16','-v','4',apk])
        command('official-supplement-manifest',[BT/'aapt2','dump','xmltree',apk,'--file','AndroidManifest.xml'])
        packaging=support.load('authored_runner_host_packaging',support.ROOT/'verification/android-coordinator-apk-packaging/apk_packaging.py').validate(apk)
        if packaging!=before['packagingPreDispatch']:raise ValueError('supplement packaging differs')
        with zipfile.ZipFile(apk) as z:
            if len(z.namelist())!=len(set(z.namelist())):raise ValueError('duplicate APK entry')
            entries={n:support.data_bind(z.read(n)) for n in z.namelist()}
        if entries!=support.read(support.SUPPLEMENT/'apk-entries.json'):raise ValueError('supplement exact APK entries differ')
        baseline=support.read(support.CANDIDATE/'apk-entries.json');libs={n:v for n,v in entries.items() if n.startswith('lib/')}
        if len(libs)!=18 or any(baseline[n]!=v for n,v in libs.items()):raise ValueError('supplement changed native libraries')
        for name in ('resources.arsc','assets/MixerAppearanceV2/descriptor.json'):
            if entries[name]!=baseline[name]:raise ValueError('supplement changed common resource '+name)
        support.save(out/'fresh-artifacts.json',dict(fresh,**fresh_dex))
        with tarfile.open(out/'fresh-supplement-class-dex.tar.gz','w:gz') as archive:
            for folder,prefix in ((classes,'supplement-classes'),(dex,'dex')):
                for p in sorted(folder.rglob('*')):
                    if p.is_file():archive.add(p,arcname=prefix+'/'+str(p.relative_to(folder)),recursive=False)
        command('fresh-authored-runner-controls',[sys.executable,'-B',support.HERE/'test_host.py','--work',work/'authored-tests','--results',out/'test-results.json'])
        tests=support.read(out/'test-results.json')
        if tests['status']!='passed' or tests['tests']<15:raise ValueError('authored controls incomplete')
        after=support.frozen('supplement');support.save(out/'input-identity-after.json',after)
        if after!=before:raise ValueError('frozen inputs changed during host review')
        receipt.update(status='passed-independent-four-class-exact-DEX-supplement-review-and-host-controls',productionClasses=159,freshSupplementClasses=4,unchangedLibraries=18,baselineArtifactPayload=183,supplementArtifactPayload=183,upstreamControls=55,authoredControls=tests['tests'],scope='actual component fixture source/build review only; no native dispatch or coordinator authority; screenshot pixels unobserved')
    except BaseException as failure:
        receipt['status']='failed-host-attempt-retained';receipt['failure']=repr(failure);(out/'failure.log').write_text(traceback.format_exc());raise
    finally:
        try:
            result=command('scratch-open-holders',['/usr/sbin/lsof','-nP','+D',work],allowed=(1,))
            st=work.stat()
            if result or work.is_symlink() or (st.st_dev,st.st_ino)!=(owner.st_dev,owner.st_ino) or any(p.is_symlink() for p in work.rglob('*')):raise ValueError('owned scratch cleanup refused')
            size=sum(p.stat().st_size for p in work.rglob('*') if p.is_file());shutil.rmtree(work)
            receipt['cleanup']={'path':str(work),'device':owner.st_dev,'inode':owner.st_ino,'bytesRemoved':size,'absent':not work.exists(),'allCommandGroupsEmpty':all(not c['ownedCommandGroupCleanup']['after'] for c in receipt['commands'])}
        except BaseException as failure:receipt['status']='failed-owned-cleanup';receipt['cleanupFailure']=repr(failure);raise
        finally:
            receipt['finishedUTC']=now();support.save(out/'receipt.json',receipt)
            support.save(out/'artifact-seal.json',{str(p.relative_to(out)):support.bind(p) for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'artifact-seal.json'})

if __name__=='__main__':main()
