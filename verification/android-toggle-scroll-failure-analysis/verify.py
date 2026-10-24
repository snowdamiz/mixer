#!/usr/bin/env python3
"""Fresh host-only replay of original-protocol scroll observation and exact APK composition."""
import argparse,json,os,re,shutil,sys,traceback,zipfile
from pathlib import Path
import support
import run
import test_host

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',required=True);args=parser.parse_args()
    if not re.fullmatch(r'host-[1-9][0-9]*',args.attempt):parser.error('fresh host-N required')
    out=support.HERE/args.attempt;out.mkdir();work=out/'.build';work.mkdir();owned=work.stat();env=dict(os.environ,JAVA_HOME=str(support.JDK),PATH=str(support.JDK/'bin')+os.pathsep+os.environ['PATH'],PYTHONDONTWRITEBYTECODE='1')
    receipt={'schema':1,'status':'host-review-running','startedUTC':support.now(),'nativeRuntime':'NOT RUN','nativeAccepted':False,'nativeInstancesStarted':0,'physicalTargetsQueried':False,'GitCommandsExecuted':0,'commands':[],'invocation':[sys.executable,'-B',str(Path(__file__).resolve()),'--attempt',args.attempt]}
    def command(name,argv,allowed=(0,)):
        argv=list(map(str,argv));started=support.now();result=support.owned.execute(argv,cwd=support.ROOT,env=env,timeout=180);log=out/(name+'.log');log.write_bytes(result.stdout)
        receipt['commands'].append({'name':name,'argv':argv,'cwd':str(support.ROOT),'JAVA_HOME':str(support.JDK),'startedUTC':started,'finishedUTC':support.now(),'exitCode':result.returncode,'output':log.name,**support.bind(log),'ownedCommandGroupCleanup':result.groupCleanup});support.save(out/'receipt.json',receipt);print(name+': exit '+str(result.returncode),flush=True)
        if result.returncode not in allowed:raise RuntimeError(name+' failed')
        return result.stdout
    try:
        receipt['upstreamBefore']=support.upstream();receipt['candidate']=support.frozen();receipt['runnerContract']=support.bind(support.HERE/'runner-contract.json')
        used=out/'source-used';used.mkdir()
        for name in ('support.py','run.py','diagnostics.py','test_host.py','verify.py','runner-contract.json','derived-runner.py','capture_analysis.py'):(used/name).write_bytes((support.HERE/name).read_bytes())
        for name in ('FixtureFailuresTest.java','ScrollTraceBufferTest.java'):(used/name).write_bytes((support.HERE/'host-tests'/name).read_bytes())
        for name,argv in [('python',[sys.executable,'--version']),('java',[support.JDK/'bin/java','--version']),('javac',[support.JDK/'bin/javac','--version']),('d8',[support.BT/'d8','--version']),('aapt2',[support.BT/'aapt2','version']),('apksigner',[support.BT/'apksigner','version'])]:command(name+'-version',argv)
        support.save(out/'payload-inventory.json',support.extract(work));production=work/'production-classes';fresh=work/'fresh-fixture';fresh.mkdir();host=work/'host';host.mkdir();dex=work/'fresh-dex';dex.mkdir()
        fixture=support.candidate()/'source-used'
        command('compile-exact-fixture',[support.JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',production,'-classpath',os.pathsep.join(map(str,[production,support.JAR])),'-d',fresh,*sorted(fixture.glob('*.java'))])
        actual={str(p.relative_to(fresh)):support.bind(p) for p in fresh.rglob('*.class')};expected={str(Path(n).relative_to('supplement-classes')):v for n,v in support.read(support.candidate()/'built-artifacts.json').items() if n.startswith('supplement-classes/')}
        if actual!=expected:raise ValueError('fresh diagnostic fixture class bytes differ')
        fixtureCount=len(actual);support.save(out/'fresh-fixture-classes.json',actual)
        command('compile-host-fixture-test',[support.JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-classpath',fresh,'-d',host,*sorted(used.glob('*Test.java'))])
        output=command('run-host-fixture-test',[support.JDK/'bin/java','-ea','-cp',os.pathsep.join(map(str,[fresh,host])),'dev.mixer.android.FixtureFailuresTest']);result=re.findall(rb'^RESULT (.+)$',output,re.M)
        if len(result)!=1:raise ValueError('one host fixture result required')
        support.save(out/'fixture-failure-tests.json',json.loads(result[0]))
        output=command('run-host-trace-buffer-test',[support.JDK/'bin/java','-ea','-cp',os.pathsep.join(map(str,[fresh,host])),'dev.mixer.android.ScrollTraceBufferTest']);result=re.findall(rb'^RESULT (.+)$',output,re.M)
        if len(result)!=1:raise ValueError('one trace buffer result required')
        support.save(out/'trace-buffer-tests.json',json.loads(result[0]))
        command('replay-exact-component-dex',[support.BT/'d8','--min-api','36','--lib',support.JAR,'--output',dex,*sorted(production.rglob('*.class')),*sorted(fresh.rglob('*.class'))])
        if {p.name:support.bind(p) for p in dex.glob('*.dex')}!={Path(n).name:v for n,v in support.read(support.candidate()/'built-artifacts.json').items() if n.startswith('dex/')}:raise ValueError('fresh exact DEX differs')
        apk=work/'coordinator-join.apk';command('official-repair-apksigner',[support.BT/'apksigner','verify','--verbose','--print-certs',apk]);command('official-repair-zipalign',[support.BT/'zipalign','-c','-P','16','-v','4',apk]);command('official-repair-manifest',[support.BT/'aapt2','dump','xmltree',apk,'--file','AndroidManifest.xml'])
        with zipfile.ZipFile(apk) as archive:entries={info.filename:support.data_bind(archive.read(info.filename)) for info in archive.infolist()}
        if entries!=support.read(support.candidate()/'apk-entries.json'):raise ValueError('APK entry replay drift')
        original=support.read(support.PRODUCER/'supplement-3/production-class-inventory.json');actual={str(p.relative_to(work)):support.bind(p) for p in production.rglob('*.class')}
        if actual!=original or len(actual)!=159:raise ValueError('production classes changed')
        support.save(out/'host-controls.json',test_host.test());receipt['upstreamAfter']=support.upstream();receipt.update({'status':'passed-fresh-host-original-protocol-scroll-observation-and-exact-apk-composition-native-NOT-RUN','unchangedProductionClasses':159,'unchangedNativeLibraries':18,'replayedFixtureClasses':fixtureCount,'exactDexReplay':True,'sourceSnapshots':{p.name:support.bind(p) for p in used.iterdir()}})
    except BaseException as failure:
        receipt['status']='failed-host-review-retained';receipt['failure']=repr(failure);(out/'failure.log').write_text(traceback.format_exc());raise
    finally:
        try:
            holders=command('scratch-open-holders',['/usr/sbin/lsof','-nP','+D',work],allowed=(1,))
            if holders:raise ValueError('owned scratch holder remains')
            current=work.stat()
            if work.is_symlink() or (current.st_dev,current.st_ino)!=(owned.st_dev,owned.st_ino):raise ValueError('owned scratch identity mismatch')
            files=[p for p in work.rglob('*') if p.is_file()];size=sum(p.stat().st_size for p in files);shutil.rmtree(work);receipt['cleanup']={'path':str(work),'filesRemoved':len(files),'bytesRemoved':size,'absent':not work.exists(),'ownedDevice':owned.st_dev,'ownedInode':owned.st_ino,'scope':'unique host build scratch only; all owned command groups empty'}
        except BaseException as failure:receipt['cleanupFailure']=repr(failure);receipt['status']='failed-owned-host-cleanup';raise
        finally:receipt['finishedUTC']=support.now();support.save(out/'receipt.json',receipt);support.save(out/'artifact-seal.json',support.seal(out))
if __name__=='__main__':main()
