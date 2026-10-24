#!/usr/bin/env python3
"""Fresh serial focused matrix, with an explicit complementary Debug selection."""
import gzip,json,re
from run import HERE,SCRATCH,run,enc,digest,manifest
rows=[]
for features,flags in[('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for profile in['debug','release']:
  name='qualified-runtime-'+features+'-'+profile;commands=[name]
  p=run(name,['cargo','test','--lib','--locked','--offline',*flags,*(['--release']if profile=='release'else[]),'memory_growth_operations::tests::','--','--nocapture','--test-threads=1'],SCRATCH/'candidate/vm');assert p.returncode==0;text=p.stdout.decode()
  tests=re.findall(r'test ([\w:]+) \.\.\.',text);growth=[n.rsplit('::',1)[-1]for n in tests if'memory_growth_operations::tests::'in n];expected=19 if features=='swift' else 20
  assert len(growth)==expected and len(tests)==expected and len(set(tests))==len(tests),(features,profile,len(tests),growth)
  prior=json.loads((HERE/'inputs'/('accepted-'+features+'-runtime-test-names.json')).read_text());assert len(prior)==78
  bounds=re.findall(r'MG_BOUND fixtures=(\d+) steps=(\d+) maxFixtures=24 maxSteps=128 maxFrames=3',text);assert len(bounds)==expected and all(int(fixtures)<=24 and int(steps)<=128 for fixtures,steps in bounds)
  rows.append(dict(features=features,profile=profile,totalTests=len(tests),growthTests=growth,commands=commands,sourceTreeSHA256=digest(manifest(SCRATCH/'candidate/vm'))))
  (HERE/'matrix-results.json').write_bytes(enc(rows))
p=run('qualified-regression-all-release',['cargo','test','--lib','--all-features','--release','--locked','--offline','experimental_swift_reactor::execution::','--','--nocapture','--test-threads=1'],SCRATCH/'candidate/vm');assert p.returncode==0
names=re.findall(r'test ([\w:]+) \.\.\.',p.stdout.decode());assert len(names)==98 and len(set(names))==98
assert sorted(n for n in names if'memory_growth_operations::tests::'not in n)==json.loads((HERE/'inputs/accepted-all-runtime-test-names.json').read_text())
(HERE/'regression-results.json').write_bytes(enc(dict(commands=['qualified-regression-all-release'],totalTests=98,priorTests=78,growthRepeatTests=20,sourceTreeSHA256=digest(manifest(SCRATCH/'candidate/vm')))))
print('Four configs:78 fresh growth selections;98 broad Release selections (78 prior+20 repeated growth)',flush=True)
