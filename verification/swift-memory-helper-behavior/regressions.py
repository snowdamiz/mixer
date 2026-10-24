import sys
from run import run,SCRATCH,HERE,b
STAGE=sys.argv[1]+'-'if len(sys.argv)>1 else''
results=[]
for feature,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in [False,True]:
  profile='release'if release else'debug'
  for label,pattern in [('frame-control','frame_operations::tests::'),('value','value_operations::tests::')]:
   name=STAGE+'regression-'+feature+'-'+profile+'-'+label;p=run(name,['cargo','test','--lib','--locked','--offline',*flags,*(['--release']if release else[]),pattern,'--','--test-threads=1'],SCRATCH/'candidate/vm');assert p.returncode==0
   results.append(dict(command=name,passed=True));(HERE/'regression-results.json').write_bytes(b.enc(results))
print('all prior frame/control/value regressions passed across four feature/profile configurations',flush=True)
