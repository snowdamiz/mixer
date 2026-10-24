from run import *
import shutil
vm=SCRATCH/'adversarial'
if not vm.exists():shutil.copytree(SCRATCH/'candidate',vm)
p=vm/'src/experimental_swift_reactor/bulk_memory_operations_tests.rs'
if 'fn review01_'not in p.read_text():p.write_text(p.read_text()+'\n'+(HERE/'adversarial-tests.rs').read_text())
source=digest(manifest(vm));(HERE/'adversarial-source-manifest.json').write_bytes(enc(manifest(vm)))
with tarfile.open(HERE/'adversarial-source.tar.gz','w:gz')as tar:
 for name in manifest(vm):tar.add(vm/name,arcname=name)
results=[]
for features,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in[False,True]:
  profile='release'if release else'debug';name='fresh-adversarial-'+features+'-'+profile+('-retry'if features=='swift'and profile=='debug'else'')
  p=run(name,['cargo','test','--lib','--locked','--offline',*flags,*(['--release']if release else[]),'bulk_memory_operations::tests::review','--','--nocapture','--test-threads=1'],vm,{'CARGO_TARGET_DIR':str(SCRATCH/'target-adversarial')})
  assert p.returncode==0
  names=re.findall(r'test ([\w:]+) \.\.\.',p.stdout.decode());assert len(names)==3 and all('::tests::review'in n for n in names)
  assert 'test result: ok. 3 passed; 0 failed; 0 ignored;'in p.stdout.decode()
  bounds=re.findall(r'BM_BOUND fixtures=(\d+) totalSteps=(\d+) maxStepsPerFixture=64 maxFrames=3 realPages=584',p.stdout.decode());assert sorted(bounds)==[('18','18'),('3','3'),('8','8')],bounds
  results.append(dict(features=features,profile=profile,tests=names,bounds=bounds,sourceSHA256=source));(HERE/'adversarial-results.json').write_bytes(enc(results))
