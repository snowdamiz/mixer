#!/usr/bin/env python3
"""Selected actual-runner synthetic response controls, independent of producer tests."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROUND=Path(__file__).resolve().parents[1]
REPO=ROUND.parents[2]
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['baseline','matrix'],required=True);a=p.parse_args()
ROOT=ROUND/'portable-root'
runner=ROOT/'scripts/ci/check-analyzer-envelope.py'
if hashlib.sha256(runner.read_bytes()).hexdigest()!='4c56beec330b8118f01be3a6e7460f9857e4b1e8b61f29b4a9bce16fb6c1130c':raise RuntimeError('unadmitted response runner')
methods=json.loads((ROOT/'verification/swift-envelope-ci-pack/inventories/expected-methods.json').read_bytes())
layouts=json.loads((ROOT/'verification/swift-envelope-ci-pack/inventories/expected-host-layouts.json').read_bytes())
oracle={'producer':methods['producer']['names'],'independent':methods['independent_exact_source']['names'],'layouts':[x['bytes'] for x in layouts['layouts']]}
if (ROUND/'response-oracle.json').exists():
    if json.loads((ROUND/'response-oracle.json').read_bytes())!=oracle:raise RuntimeError('response oracle changed')
else:
    with (ROUND/'response-oracle.json').open('x') as stream:json.dump(oracle,stream,indent=2,sort_keys=True);stream.write('\n')
compiler=ROUND/'response-toolchain/bin/rustc';compiler.parent.mkdir(parents=True,exist_ok=True)
data=(ROUND/'commands/response-compiler.py').read_text().replace("ROUND=Path('REPLACED_ROUND')",'ROUND=Path('+repr(str(ROUND))+')',1)
compiler.write_text('#!'+sys.executable+'\n'+'\n'.join(data.splitlines()[1:])+'\n');compiler.chmod(0o755)
cases=[('valid-response-protocol','valid','producer',False,True)]
for lane in ('producer','independent'):
    for mode in ('list-empty','list-missing','list-extra','list-duplicate','list-substitute','execute-empty','execute-missing','execute-duplicate','execute-substitute','execute-ignored','execute-failed','execute-measured','execute-filtered'):
        cases.append((lane+'-'+mode,mode,lane,mode.startswith('execute'),False))
for mode in ('layout-missing','layout-wrong','layout-duplicate','comparison-missing','comparison-wrong','comparison-duplicate','positive-fails','negative-missing-library','negative-malformed-json','negative-crash','negative-success','negative-produced-executable','independent-other-warning'):
    cases.append((mode,mode,'producer',True,False))
if a.phase=='baseline':cases=cases[:1]
else:
    baseline=json.loads((ROUND/'response-attempt2-baseline.json').read_bytes())
    if baseline['case_count']!=1 or baseline['passed']!=1:raise RuntimeError('valid response baseline required')
    cases=cases[1:]
results=[]
for name,mode,lane,optimize,expected_pass in cases:
    cfg={'case':name,'mode':mode,'lane':lane}
    (ROUND/'response-settings.json').write_text(json.dumps(cfg,sort_keys=True)+'\n')
    out=ROOT/'runs'/('response2-'+name)
    argv=[sys.executable,*(['-O'] if optimize else []),'-B',str(runner),'--out',str(out),'--rustc',str(compiler)]
    env=dict(os.environ);env.update({'RUSTFLAGS':'--cfg UNSELECTED','RUSTC_WRAPPER':'/unselected-wrapper','RUST_TEST_THREADS':'99','RUST_TEST_RUN_IGNORED':'1'})
    row={'name':name,'fixture':cfg,'argv':argv,'cwd':str(REPO),'expected_pass':expected_pass,'started_utc':datetime.now(timezone.utc).isoformat(),'python_optimization':1 if optimize else 0,'scope':'Synthetic protocol/fault response only; never product or compiler qualification.'}
    start=time.monotonic()
    with (ROUND/('response2-'+name+'.stdout')).open('xb') as stdout,(ROUND/('response2-'+name+'.stderr')).open('xb') as stderr:
        result=subprocess.run(argv,cwd=REPO,env=env,stdout=stdout,stderr=stderr,timeout=40)
    receipt=json.loads((out/'receipt.json').read_bytes())
    observed_pass=result.returncode==0 and receipt['status']=='passed-host-fixture-check'
    intended_stage='producer-list' if mode.startswith('list-') and lane=='producer' else 'independent-list' if mode.startswith('list-') else 'producer-execute' if mode.startswith('execute-') and lane=='producer' else 'independent-execute' if mode.startswith('execute-') else 'producer-execute' if mode.startswith(('layout-','comparison-')) else 'api-positive' if mode=='positive-fails' else 'api-negative-private-field' if mode.startswith('negative-') else 'independent-compile' if mode=='independent-other-warning' else 'revision-after'
    commands=[r['name'] for r in receipt['commands']]
    stage_reached=intended_stage in commands
    active=next((e for e in receipt['errors'] if e['phase']=='active'),None)
    stage_row=next((r for r in receipt['commands'] if r['name']==intended_stage),None)
    correct_failure=True
    if not expected_pass:
        if mode.startswith('list-'):correct_failure=stage_row is not None and stage_row['exit']==0 and active is not None and active['message'] in ('Listing total differs','Exact method inventory differs')
        elif mode.startswith('execute-'):correct_failure=stage_row is not None and stage_row['exit']==0 and active is not None and active['message'] in ('Partial/ignored/failed test result','Exact method inventory differs','Executed methods missing terminal ok')
        elif mode.startswith('layout-'):correct_failure=active is not None and active['message'] in ('Host layouts differ','Missing/duplicate complete layout observation')
        elif mode.startswith('comparison-'):correct_failure=active is not None and active['message']=='Fresh candidate comparison counters differ'
        elif mode=='negative-missing-library':correct_failure=active is not None and active['message']=='Unexpected API diagnostic code'
        elif mode=='negative-malformed-json':correct_failure=active is not None and active['type']=='JSONDecodeError'
        elif mode=='negative-produced-executable':correct_failure=active is not None and active['message']=='Negative API abnormal failure or executable'
        else:correct_failure=active is not None and active['message'].startswith('Command failed: '+intended_stage+';')
    row.update({'exit':result.returncode,'status':receipt['status'],'errors':receipt['errors'],'elapsed_seconds':round(time.monotonic()-start,6),'finished_utc':datetime.now(timezone.utc).isoformat(),'commands':commands,'intended_stage':intended_stage,'intended_stage_reached':stage_reached,'correct_failure_class':correct_failure,'passed':observed_pass==expected_pass and stage_reached and correct_failure,'receipt':str((out/'receipt.json').relative_to(ROUND)),'cleanup_removed':receipt['cleanup']['removed'],'environment_scrubbed':all(not any(k in r['environment'] for k in ('RUSTFLAGS','RUSTC_WRAPPER','RUST_TEST_THREADS','RUST_TEST_RUN_IGNORED')) for r in receipt['commands'])})
    row['raw_streams_verified']=True
    for command in receipt['commands']:
        for stream in ('stdout','stderr'):
            record=command[stream];path=out/record['path']
            if path.stat().st_size!=record['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:row['raw_streams_verified']=False
    results.append(row)
    (ROUND/('response-attempt2-'+a.phase+'-progress.json')).write_text(json.dumps(results,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'case':name,'passed':row['passed'],'status':row['status'],'intended_stage_reached':stage_reached,'elapsed_seconds':row['elapsed_seconds']},sort_keys=True),flush=True)
summary={'schema':1,'scope':'Independent actual-runner synthetic response protocol only. One valid fixture baseline and faults; no synthetic product qualification.','phase':a.phase,'python_version':sys.version,'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'compiler_fixture_sha256':hashlib.sha256(compiler.read_bytes()).hexdigest(),'case_count':len(results),'passed':sum(x['passed'] for x in results),'failed':[x['name'] for x in results if not x['passed']],'results':results}
with (ROUND/('response-attempt2-'+a.phase+'.json')).open('x') as stream:json.dump(summary,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({k:v for k,v in summary.items() if k!='results'},sort_keys=True))
sys.exit(0 if not summary['failed'] else 1)
