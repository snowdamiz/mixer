from review import *
import shutil
vm=SCRATCH/'adversarial-v2/vm';shutil.copytree(SCRATCH/'candidate/vm',vm)
p=vm/'src/experimental_swift_reactor/memory_operations_tests.rs';p.write_bytes(p.read_bytes()+b'\n'+(HERE/'adversarial.rs').read_bytes())
(HERE/'adversarial-source-manifest.json').write_bytes(enc(manifest(vm)))
with tarfile.open(HERE/'adversarial-source.tar.gz','w:gz') as t:
 for path in manifest(vm):t.add(vm/path,arcname='vm/'+path,recursive=False)
for feature,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
 for release in [False,True]:
  p=run('adversarial-v2-'+feature+('-release' if release else '-debug'),['cargo','test','--lib','--locked','--offline',*flags,*(['--release'] if release else []),'memory_operations::tests::review_','--','--nocapture','--test-threads=1'],vm);assert p.returncode==0
  assert '6 passed; 0 failed; 0 ignored' in p.stdout.decode()
print('24 independent adversarial selections passed',flush=True)
