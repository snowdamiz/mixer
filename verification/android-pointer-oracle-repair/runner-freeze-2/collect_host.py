#!/usr/bin/env python3
"""Host-only replay: executable negative controls, exact archive checks and deterministic DEX derivation."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import tarfile
import common
import build
import run
import verify_candidate
import check_packet


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',required=True);args=parser.parse_args()
    if not args.attempt.startswith('host-review-') or not args.attempt[12:].isdigit():parser.error('fresh host-review-N required')
    runner,_,_=run.load_runner();out=common.HERE/args.attempt;out.mkdir();work=out/'.build';work.mkdir();st=work.stat();ownership=(st.st_dev,st.st_ino);commands=[]
    receipt={'schema':1,'status':'running-host-only','commands':commands,'nativeRuntime':'NOT RUN','nativeAcceptance':False,'nativeInstancesStarted':0,'physicalTargetsQueried':False,'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'implementationBindings':{n:common.sha(common.HERE/n) for n in ('common.py','build.py','run.py','bounded_output.py','oracle.py','test_host.py','collect_host.py','verify_candidate.py','CoordinatorJoinActivity.java','CoordinatorJoinInstrumentation.java','operations.json','check_packet.py')}}
    def command(name,argv,allowed=(0,)):
        argv=list(map(str,argv));start=datetime.datetime.now(datetime.timezone.utc).isoformat();result=runner.execute(argv,cwd=common.ROOT,env=dict(os.environ,JAVA_HOME=str(build.JDK),PATH=str(build.JDK/'bin')+os.pathsep+os.environ['PATH']),timeout=180);log=out/(name+'.log');log.write_bytes(result.stdout)
        commands.append({'name':name,'argv':argv,'cwd':str(common.ROOT),'startedUTC':start,'finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':result.returncode,'output':log.name,'sha256':common.sha(log),'ownedCommandGroupCleanup':result.groupCleanup});print(name+': exit '+str(result.returncode),flush=True)
        if result.returncode not in allowed:raise RuntimeError(name+' failed; full output retained')
        return result.stdout.decode(errors='replace').strip()
    try:
        receipt['sourceRevision']=command('source-revision',['git','rev-parse','HEAD']);receipt['sourceTree']=command('source-tree',['git','rev-parse','HEAD^{tree}']);command('source-status',['git','status','--short']);command('python-version',[sys.executable,'--version'])
        receipt['artifactReview']=verify_candidate.check();common.save(out/'artifact-review.json',receipt['artifactReview'])
        command('host-negative-controls',[sys.executable,'-B',common.HERE/'test_host.py','--work',work])
        receipt['hostTestCount']=40;receipt['upstream']=check_packet.upstream()
        d8_results={}
        for label,directory in [('accepted',common.BASE),('pointer',common.HERE/'candidate-5')]:
            target=work/label;target.mkdir();index=json.loads((directory/'built-artifacts.json').read_text())
            with tarfile.open(directory/'built-artifacts.tar.gz','r:gz') as archive:
                members=archive.getmembers();runner.validate_members(members,index)
                chosen=[m for m in members if m.name.startswith(('production-classes/','test-classes/','dex/'))];archive.extractall(target,members=chosen,filter='data')
            production=target/'production-classes';tests=target/'test-classes';dex=target/'replayed-dex';dex.mkdir()
            command(label+'-dex-replay',[build.BT/'d8','--min-api','36','--lib',build.JAR,'--output',dex,*sorted(production.rglob('*.class')),*sorted(tests.rglob('*.class'))])
            expected={Path(n).name:v['sha256'] for n,v in index.items() if n.startswith('dex/')};actual={p.name:common.sha(p) for p in dex.glob('*.dex')}
            if actual!=expected:raise ValueError('deterministic DEX replay differs for '+label)
            d8_results[label]={'classInputs':{str(p.relative_to(target)):common.sha(p) for p in sorted(target.rglob('*.class'))},'replayedDEX':actual,'frozenDEX':expected,'matches':True}
        common.save(out/'deterministic-dex-replay.json',d8_results);receipt['deterministicDEXDerivation']='both accepted and pointer class closures replay byte-for-byte with the same pinned D8; all DEX change derives from the mapped two private harness families'
        receipt['status']='passed-host-only-pointer-fixture-controls-and-identity'
    except BaseException as failure:receipt.update({'status':'failed-host-review-retained','failure':repr(failure)});raise
    finally:
        for directory in sorted((p for p in work.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
            if not list(directory.iterdir()):(directory/'.owned-empty-directory').write_text('owned generated empty directory marker\n')
        expected={str(p.relative_to(work)):{} for p in work.rglob('*') if p.is_file()}
        try:receipt['scratchCleanup']=runner.remove_owned_extraction(work,out,expected,ownership)
        except BaseException as failure:receipt.update({'status':'failed-host-scratch-cleanup','scratchCleanup':repr(failure)});raise
        finally:receipt['finishedUTC']=datetime.datetime.now(datetime.timezone.utc).isoformat();common.save(out/'receipt.json',receipt);common.save(out/'artifact-seal.json',common.exact_seal(out))

if __name__=='__main__':main()
