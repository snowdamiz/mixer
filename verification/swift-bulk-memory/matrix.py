from pathlib import Path
import re,json
from run import run,SCRATCH,HERE,b
names=re.findall(r'#\[test\] fn (bm\d+_\w+)',(HERE/'tests.rs').read_text());assert len(names)==16 and len(set(names))==16
results=[]
for features,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in [False,True]:
  profile='release'if release else'debug'
  p=run('sealed-runtime-'+features+'-'+profile,['cargo','test','--lib','--locked','--offline',*flags,*(['--release']if release else[]),'experimental_swift_reactor::execution::','--','--nocapture','--test-threads=1'],SCRATCH/'candidate');assert p.returncode==0
  text=p.stdout.decode();executed=re.findall(r'test ([\w:]+) \.\.\.',text)
  # Actual stdout can place the fixture's first print immediately after the dots.
  selected=[name.rsplit('::',1)[-1] for name in executed if 'bulk_memory_operations::tests::'in name]
  assert sorted(selected)==sorted(names),(selected,names)
  for name in names:assert selected.count(name)==1
  summary=re.search(r'test result: ok\. (\d+) passed; 0 failed; 0 ignored;',text);assert summary
  bounds=re.findall(r'BM_BOUND fixtures=(\d+) totalSteps=(\d+) maxStepsPerFixture=64 maxFrames=3 realPages=584',text);assert len(bounds)==16
  assert all(int(n)<=64 and int(steps)<=4096 for n,steps in bounds)
  results.append(dict(features=features,profile=profile,bulkTests=selected,passed=int(summary[1]),boundedFixtures=bounds,sourceTreeSHA256=b.digest(b.manifest(SCRATCH/'candidate/vm'))))
  (HERE/'matrix-results.json').write_bytes(b.enc(results))
