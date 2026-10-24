#!/usr/bin/env python3
"""Fresh empty-context private harness/class/DEX replay and candidate4-to5 mapping; host only."""
import argparse
import datetime
import json
import os
from pathlib import Path
import tarfile
import common
import build
import run
import verify_candidate


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',required=True);args=parser.parse_args()
    if not args.attempt.startswith('build-replay-') or not args.attempt[13:].isdigit():parser.error('fresh build-replay-N required')
    runner,_,_=run.load_runner();out=common.HERE/args.attempt;out.mkdir();work=out/'.build';work.mkdir();st=work.stat();ownership=(st.st_dev,st.st_ino)
    receipt={'schema':1,'status':'running-host-only-build-replay','commands':[],'startedUTC':now(),'scriptSHA256':common.sha(__file__),'nativeRuntime':'NOT RUN','nativeInstancesStarted':0,'physicalTargetsQueried':False,'nativeAcceptance':False,'gaAcceptance':False,'immutablePredecessorBindingsRechecked':common.preserved_inputs()}
    def command(name,argv):
        argv=list(map(str,argv));started=now();result=runner.execute(argv,cwd=common.ROOT,env=dict(os.environ,JAVA_HOME=str(build.JDK),PATH=str(build.JDK/'bin')+os.pathsep+os.environ['PATH']),timeout=180)
        log=out/(name+'.log');log.write_bytes(result.stdout);receipt['commands'].append({'name':name,'argv':argv,'cwd':str(common.ROOT),'startedUTC':started,'finishedUTC':now(),'exitCode':result.returncode,'output':log.name,'sha256':common.sha(log),'ownedCommandGroupCleanup':result.groupCleanup})
        print(name+': exit '+str(result.returncode),flush=True)
        if result.returncode:raise RuntimeError(name+' failed; full output retained')
        return result.stdout.decode(errors='replace').strip()
    try:
        receipt['sourceRevision']=command('source-revision',['git','rev-parse','HEAD']);receipt['sourceTree']=command('source-tree',['git','rev-parse','HEAD^{tree}']);command('source-status',['git','status','--short'])
        receipt['artifactReview']=verify_candidate.check();candidate=common.HERE/'candidate-5';frozen=json.loads((candidate/'receipt.json').read_text());index=json.loads((candidate/'built-artifacts.json').read_text());old_index=json.loads((common.PRIOR/'candidate-4/built-artifacts.json').read_text())
        delta={n:{'candidate4':old_index.get(n),'candidate5':index.get(n)} for n in sorted(set(index)|set(old_index)) if index.get(n)!=old_index.get(n)}
        expected={'coordinator-join.apk','dex/classes.dex','test-classes/dev/mixer/android/CoordinatorJoinInstrumentation.class'}
        if set(delta)!=expected:raise ValueError('unexpected candidate4-to5 compiled delta')
        common.save(out/'candidate4-compiled-delta.json',delta)
        with tarfile.open(candidate/'built-artifacts.tar.gz','r:gz') as archive:
            members=archive.getmembers();runner.validate_members(members,index);archive.extractall(work,members=members,filter='data')
        for name,value in index.items():
            if common.sha(work/name)!=value['sha256']:raise ValueError('frozen extracted artifact mismatch '+name)
        for folder in ('fresh-private-classes','empty-sourcepath','fresh-dex'):(work/folder).mkdir()
        classpath=os.pathsep.join(map(str,[work/'production-classes',build.JAR]));source=candidate/'inputs/verification/android-coordinator-join'
        receipt['versions']={name:command(name+'-version',argv) for name,argv in [('python',[os.sys.executable,'--version']),('javac',[build.JDK/'bin/javac','--version']),('d8',[build.BT/'d8','--version']),('apksigner',[build.BT/'apksigner','version'])]}
        command('fresh-harness-java17-sdk37',[build.JDK/'bin/javac','--release','17','-Xlint:all','-Werror','-sourcepath',work/'empty-sourcepath','-classpath',classpath,'-d',work/'fresh-private-classes',source/'CoordinatorJoinActivity.java',source/'CoordinatorJoinInstrumentation.java'])
        compiled={str(p.relative_to(work/'fresh-private-classes')):common.sha(p) for p in sorted((work/'fresh-private-classes').rglob('*.class'))}
        expected_classes={n.removeprefix('test-classes/'):v['sha256'] for n,v in index.items() if n.startswith('test-classes/')}
        if compiled!=expected_classes or len(compiled)!=4:raise ValueError('fresh private source-to-class bytes differ')
        command('fresh-complete-dex',[build.BT/'d8','--min-api','36','--lib',build.JAR,'--output',work/'fresh-dex',*sorted((work/'production-classes').rglob('*.class')),*sorted((work/'fresh-private-classes').rglob('*.class'))])
        dex={p.name:common.sha(p) for p in (work/'fresh-dex').glob('*.dex')};expected_dex={Path(n).name:v['sha256'] for n,v in index.items() if n.startswith('dex/')}
        if dex!=expected_dex:raise ValueError('fresh complete DEX bytes differ')
        command('official-zipalign',[build.BT/'zipalign','-c','-P','16','-v','4',work/'coordinator-join.apk'])
        signature=command('official-apksigner',[build.BT/'apksigner','verify','--verbose','--print-certs',work/'coordinator-join.apk'])
        if 'Verifies' not in signature or frozen['debugCertificateSHA256'] not in signature:raise ValueError('fresh signature certificate differs')
        tools=[build.JDK/'bin/javac',build.JDK/'bin/java',build.BT/'d8',build.BT/'lib/d8.jar',build.BT/'zipalign',build.BT/'apksigner',build.BT/'lib/apksigner.jar',build.JAR]
        receipt.update({'status':'passed-fresh-empty-context-source-class-dex-and-official-packaging-replay','tools':{str(p):{'sha256':common.sha(p),'bytes':p.stat().st_size,'realPath':str(p.resolve())} for p in tools},'sourceClosureSHA256':frozen['sourceClosureSHA256'],'apkSHA256':frozen['apkSHA256'],'builtArchiveSHA256':frozen['builtArchiveSHA256'],'freshClasses':compiled,'freshDEX':dex,'freshSourceInputs':2,'freshPrivateClassesByteExact':4,'unchangedCandidate4Artifacts':len(index)-len(delta),'changedCandidate4Artifacts':list(delta),'unchangedProductionClasses':155,'unchangedNativeLibraries':18,'unchangedNativeAndSDKInputs':88,'fixtureAndActivityBytesUnchangedFromCandidate4':True,'debugCertificateSHA256':frozen['debugCertificateSHA256']})
        common.preserved_inputs()
    except BaseException as failure:receipt.update({'status':'failed-host-build-replay-retained','failure':repr(failure)});raise
    finally:
        for directory in sorted((p for p in work.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
            if not list(directory.iterdir()):(directory/'.owned-empty-directory').write_text('owned generated empty directory marker\n')
        expected={str(p.relative_to(work)):{} for p in work.rglob('*') if p.is_file()}
        try:receipt['scratchCleanup']=runner.remove_owned_extraction(work,out,expected,ownership)
        except BaseException as failure:receipt.update({'status':'failed-host-build-replay-cleanup','scratchCleanup':repr(failure)});raise
        finally:receipt['finishedUTC']=now();common.save(out/'receipt.json',receipt);common.save(out/'artifact-seal.json',common.exact_seal(out))
    print(json.dumps({'status':receipt['status'],'freshPrivateClassesByteExact':4,'freshDEX':receipt['freshDEX'],'scratchCleanup':receipt['scratchCleanup']}))

if __name__=='__main__':main()
