#!/usr/bin/env python3
"""Independent host tests and bounded adversarial oracle controls. No Android calls."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'verification/android-pointer-fixture'
OUT=Path(__file__).resolve().parent/'host-review-1'
EXPECTED_SEAL='317de5fb8a7e8ac7249bbb0fc49a17ba2f38a048ab6edfc1b27e24abc5ae6b52'

def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def main():
    OUT.mkdir(exist_ok=False);scratch=OUT/'.scratch';scratch.mkdir();commands=[];results=[]
    result={'schema':1,'scope':'host-only synthetic parser controls; no native evidence','nativeInstancesStarted':0,'physicalQueries':False,'pythonVersion':sys.version,'scriptSHA256':sha(Path(__file__).read_bytes()),'command':[sys.executable,'-B',str(Path(__file__).relative_to(ROOT))]}
    def run(name,argv):
        started=time.time();completed=subprocess.run(argv,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});data=completed.stdout;(OUT/(name+'.log')).write_bytes(data);commands.append({'argv':argv,'exitCode':completed.returncode,'output':name+'.log','outputSHA256':sha(data),'startedUnix':started,'finishedUnix':time.time()});assert completed.returncode==0,(name,data[-2000:]);return data
    try:
        assert sha((FIXTURE/'packet-seal.json').read_bytes())==EXPECTED_SEAL
        expected=json.loads((FIXTURE/'packet-seal.json').read_text())['files']
        for name,v in expected.items():
            data=(ROOT/name).read_bytes();assert {'bytes':len(data),'sha256':sha(data)}==v,name
        result['originalPacketBindingsRechecked']=len(expected)
        run('packet-check',[sys.executable,'-B',str(FIXTURE/'check_packet.py')])
        work=scratch/'producer-tests';work.mkdir()
        run('producer-host-tests',[sys.executable,'-B',str(FIXTURE/'test_host.py'),'--work',str(work)])
        sys.path.insert(0,str(FIXTURE));import run as wrapper;import oracle;import test_host
        runner,source,diff=wrapper.load_runner()
        assert sha(source.encode())=='30386d63319168afb0a6e3b1ea05b991a5a5a965087efda27d1bc25e5ef74ca9'
        result['concreteRunnerSHA256']=sha(source.encode());result['transformedSites']=len(json.loads(wrapper.CONTRACT.read_text())['sourceDeltas'])
        def probe(name,mutate,expected_rejection=True):
            directory=scratch/name;native,metadata=test_host.synthetic_oracle_fixture(directory)
            rows=[json.loads(line) for line in (directory/'pointer-observations.jsonl').read_text().splitlines()]
            mutate(native,rows,directory)
            data=('\n'.join(json.dumps(row) for row in rows)+'\n').encode();(directory/'pointer-observations.jsonl').write_bytes(data);native['exports']['pointer-observations.jsonl']={'bytes':len(data),'sha256':sha(data)}
            try:accepted=oracle.validate(native,directory,metadata);outcome={'name':name,'oracleAccepted':True,'oracleResult':accepted}
            except (ValueError,KeyError,TypeError) as failure:outcome={'name':name,'oracleAccepted':False,'failure':repr(failure)}
            outcome['expectedRejection']=expected_rejection;outcome['unexpectedAcceptance']=expected_rejection and outcome['oracleAccepted'];results.append(outcome)
        def delivered_field(key,value):
            def mutate(native,rows,directory):
                for row in rows:
                    if row['kind'] in ('activity-entry','activity-exit') and row.get('actionId')=='P03-1':row['event'][key]=value
            return mutate
        probe('obscured-activity-input',delivered_field('flags',1))
        def pressure(native,rows,directory):
            for row in rows:
                if row['kind'] in ('activity-entry','activity-exit') and row.get('actionId')=='P03-1' and row['event']['action']==2:row['event']['pointers'][0]['pressure']=0
        probe('move-pressure-zero',pressure)
        def history(native,rows,directory):
            for row in rows:
                if row['kind'] in ('activity-entry','activity-exit') and row.get('actionId')=='P03-1' and row['event']['action']==2:
                    row['event']['history']=[{'eventTime':row['event']['downTime']+17,'pointers':[{'id':0,'x':999999,'y':-999999,'pressure':1}]}]
        probe('history-outside-sealed-path',history)
        def missing_moves(native,rows,directory):
            rows[:]=[r for r in rows if not (r['kind'] in ('activity-entry','activity-exit') and r.get('actionId')=='P03-1' and r['event']['action']==2)]
            native['summaries'][2]['nativeDeliveryCount']=2
        probe('drag-without-any-delivered-move',missing_moves)
        def late_completion(native,rows,directory):
            for row in rows:
                if row['kind']=='worker-send' and row.get('actionId')=='P01-1':row['workerAfter']=row['workerBefore']+999999
        probe('worker-send-finish-beyond-action-deadline',late_completion)
        def revision(native,rows,directory):native['summaries'][0]['commitAcknowledgementCount']='2'
        probe('duplicate-acknowledgement-control',revision)
        def retirement(native,rows,directory):
            p=directory/'pointer-retirement-after.json';v=json.loads(p.read_text());v['savedPacketSHA256']='f'*64;data=json.dumps(v).encode();p.write_bytes(data);native['exports'][p.name]={'bytes':len(data),'sha256':sha(data)}
        probe('retirement-saved-packet-control',retirement)
        result['adversarialProbes']=results;result['producerHostTests']=22;result['status']='completed-host-review-with-semantic-findings' if any(r['unexpectedAcceptance'] for r in results) else 'passed-independent-host-controls'
        for name,v in expected.items():
            data=(ROOT/name).read_bytes();assert {'bytes':len(data),'sha256':sha(data)}==v,name
        result['sealedProducerPacketUnchanged']=True
    finally:
        holders=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(scratch)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30);(OUT/'scratch-open-holders.log').write_bytes(holders.stdout);assert holders.returncode==1 and not holders.stdout
        count=sum(p.is_file() for p in scratch.rglob('*'));size=sum(p.stat().st_size for p in scratch.rglob('*') if p.is_file());shutil.rmtree(scratch);result['scratchCleanup']={'files':count,'bytes':size,'pathAbsent':not scratch.exists(),'holderCheckExitCode':holders.returncode,'holderOutputSHA256':sha(holders.stdout)};result['commands']=commands;save(OUT/'receipt.json',result);(OUT/'check_host-used.py').write_bytes(Path(__file__).read_bytes());save(OUT/'artifact-seal.json',{str(p.relative_to(OUT)):{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(OUT.rglob('*')) if p.is_file() and p!=OUT/'artifact-seal.json'})
    print(json.dumps({'status':result['status'],'producerHostTests':result['producerHostTests'],'adversarialProbes':results,'scratchCleanup':result['scratchCleanup']}))

if __name__=='__main__':main()
