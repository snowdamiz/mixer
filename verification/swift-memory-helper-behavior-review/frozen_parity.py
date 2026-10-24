from review import *
results=[]
for release in [False,True]:
 profile='release' if release else 'debug';output={}
 for label in ['baseline','candidate']:
  p=run('frozen-snapshot-'+label+'-'+profile,['cargo','test','--lib','--all-features','--locked','--offline',*(['--release'] if release else []),'experimental::execution::parity_memory_behavior::frozen_memory_behavior_snapshot','--','--exact','--nocapture','--test-threads=1'],SCRATCH/('parity-'+label)/'vm');assert p.returncode==0
  output[label]=[line[line.index('FROZEN_SNAPSHOT '):] for line in p.stdout.decode().splitlines() if 'FROZEN_SNAPSHOT ' in line];assert len(output[label])==28
 assert output['baseline']==output['candidate'];results.append(dict(profile=profile,identicalObservations=28,sha256=digest(output['baseline']),observations=output['baseline'],scope='Original Frozen invoke; finite fixtures <=2 pages, <=8 guest instructions, one frame. Swift-only feature absence is separate and does not provide Frozen execution.'))
 for label in ['baseline','candidate']:
  p=run('frozen-integration-'+label+'-'+profile,['cargo','test','--test','span_execution','--all-features','--locked','--offline',*(['--release'] if release else []),'--','--test-threads=1'],SCRATCH/label/'vm');assert p.returncode==0;assert '16 passed; 0 failed; 0 ignored' in p.stdout.decode()
 (HERE/'frozen-parity-results.json').write_bytes(enc(results))
print('56 concrete baseline/candidate Frozen pairs and 64 integration test selections passed',flush=True)
