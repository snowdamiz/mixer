from run import *
expected=re.findall(r'#\[test\] fn (bm\d+_\w+)',(PACKET/'tests.rs').read_text());assert len(expected)==16
results=[]
for features,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in [False,True]:
  profile='release'if release else'debug'
  p=run('fresh-bulk-'+features+'-'+profile,['cargo','test','--lib','--locked','--offline',*flags,*(['--release']if release else[]),'bulk_memory_operations::tests::','--','--nocapture','--test-threads=1'],SCRATCH/'candidate')
  assert p.returncode==0
  text=p.stdout.decode();names=[n.rsplit('::',1)[-1]for n in re.findall(r'test ([\w:]+) \.\.\.',text)]
  assert sorted(names)==sorted(expected)and all(names.count(n)==1 for n in expected),(features,profile,names)
  assert 'test result: ok. 16 passed; 0 failed; 0 ignored;'in text
  bounds=re.findall(r'BM_BOUND fixtures=(\d+) totalSteps=(\d+) maxStepsPerFixture=64 maxFrames=3 realPages=584',text)
  assert len(bounds)==16 and all(int(n)<=64 and int(s)<=int(n)*64 for n,s in bounds)
  results.append(dict(features=features,profile=profile,selected=names,bounds=bounds,sourceSHA256=digest(manifest(SCRATCH/'candidate'))))
  (HERE/'matrix-results.json').write_bytes(enc(results))
