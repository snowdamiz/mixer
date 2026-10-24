from pathlib import Path
import json,re,sys
from run import run,SCRATCH,HERE,b
STAGE=sys.argv[1]+'-' if len(sys.argv)>1 else ''
vm=SCRATCH/'candidate/vm';source=b.digest(b.manifest(vm));matrix=json.loads((HERE/'acceptance-matrix.json').read_text());results=[]
for config,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in [False,True]:
  profile='release' if release else 'debug';common=['cargo','test','--lib','--locked','--offline',*flags,*(['--release']if release else [])]
  listed=run(STAGE+'runtime-list-'+config+'-'+profile,[*common,'--','--list'],vm);assert listed.returncode==0
  names={line.removesuffix(': test') for line in listed.stdout.decode().splitlines()if line.endswith(': test')};assert {c['requiredTest']for c in matrix['cases']}<=names
  for case in matrix['cases']:
   name=STAGE+'runtime-'+config+'-'+profile+'-'+case['id'];p=run(name,[*common,case['requiredTest'],'--','--exact','--nocapture','--test-threads=1'],vm);out=p.stdout.decode();assert p.returncode==0 and '1 passed; 0 failed; 0 ignored' in out
   bounds=re.findall(r'MM_BOUND fixtures=(\d+) totalSteps=(\d+) maxStepsPerFixture=64 maxFrames=3 realPages=584',out);assert len(bounds)==1,(case,out);fixtures,steps=map(int,bounds[0]);assert fixtures<=64 and steps<=4096
   results.append(dict(id=case['id'],requiredTest=case['requiredTest'],configuration=config+'-'+profile,command=name,status='passed',observedFixtureCount=fixtures,observedCountedHelperAttempts=steps,sourceClosure=source,frozenExecution=('separate-baseline-candidate-all-feature-debug-release-receipts' if case['id']=='mm14_frozen_parity' and config=='swift' else 'actual-SpanInstance-plus-separate-baseline-candidate-oracle' if case['id']=='mm14_frozen_parity' else 'not-applicable')))
   (HERE/'matrix-results.json').write_bytes(b.enc(results));assert b.digest(b.manifest(vm))==source
assert len(results)==64
print('64 exact memory behavior test executions passed',flush=True)
