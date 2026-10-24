#!/usr/bin/env python3
from review import *
spec=json.loads((PRODUCER/'acceptance-matrix.json').read_text());results=[]
for feature,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in [False,True]:
  profile='release' if release else 'debug';common=['cargo','test','--lib','--locked','--offline',*flags,*(['--release'] if release else [])]
  for case in spec['cases']:
   name=case['id'];test='experimental_swift_reactor::execution::frame_operations::memory_operations::tests::'+name
   p=run('matrix-'+feature+'-'+profile+'-'+name,[*common,test,'--','--exact','--nocapture','--test-threads=1'],SCRATCH/'candidate/vm');assert p.returncode==0
   output=p.stdout.decode();assert '1 passed; 0 failed; 0 ignored' in output
   bounds=re.search(r'MM_BOUND fixtures=(\d+) totalSteps=(\d+)',output);assert bounds
   fixtures,steps=map(int,bounds.groups());assert fixtures<=64 and steps<=4096
   if name=='mm14_frozen_parity':assert ('feature absent' in output)==(feature=='swift')
   results.append(dict(case=name,feature=feature,profile=profile,fixtures=fixtures,steps=steps,exitCode=p.returncode));(HERE/'matrix-results.json').write_bytes(enc(results))
  for label,pattern in [('frame-control','frame_operations::tests::'),('value','value_operations::tests::')]:
   p=run('regression-'+feature+'-'+profile+'-'+label,[*common,pattern,'--','--test-threads=1'],SCRATCH/'candidate/vm');assert p.returncode==0
print('64 exact MM cases and eight prior regression selections passed',flush=True)
