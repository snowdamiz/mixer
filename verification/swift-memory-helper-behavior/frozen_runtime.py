from pathlib import Path
import shutil,json,hashlib,sys
from run import run,SCRATCH,HERE,b
STAGE=sys.argv[1]+'-' if len(sys.argv)>1 else ''
sources={}
for label in ['baseline','candidate']:
 vm=SCRATCH/('parity-'+STAGE+label);shutil.copytree(SCRATCH/label/'vm',vm)
 p=vm/'src/experimental/execution/mod.rs';p.write_text(p.read_text()+'\n#[cfg(all(test,feature="experimental-span-execution",feature="experimental-swift-reactor"))]\n#[path="parity_memory_behavior.rs"]\nmod parity_memory_behavior;\n')
 shutil.copy2(HERE/'frozen_snapshot.rs',vm/'src/experimental/execution/parity_memory_behavior.rs');sources[label]=vm
comparisons=[]
for release in [False,True]:
 profile='release'if release else'debug';outputs={}
 for label,vm in sources.items():
  name=STAGE+'frozen-snapshot-'+label+'-'+profile;p=run(name,['cargo','test','--lib','--all-features','--locked','--offline',*(['--release']if release else[]),'experimental::execution::parity_memory_behavior::frozen_memory_behavior_snapshot','--','--exact','--nocapture','--test-threads=1'],vm);assert p.returncode==0
  lines=[line[line.index('FROZEN_SNAPSHOT '):]for line in p.stdout.decode().splitlines()if'FROZEN_SNAPSHOT 'in line];assert len(lines)==28,(label,len(lines));outputs[label]=lines
 assert outputs['baseline']==outputs['candidate'];comparisons.append(dict(profile=profile,identicalObservations=len(outputs['baseline']),sha256=hashlib.sha256(b.enc(outputs['baseline'])).hexdigest(),scope='Actual original Frozen invoke: values, bytes, traps, work, fuel, cache and synchronous allocation requests; 28 finite fixtures, max8 guest instructions, max1 frame, max2 pages'))
 for label in ['baseline','candidate']:
  p=run(STAGE+'frozen-integration-'+label+'-'+profile,['cargo','test','--test','span_execution','--all-features','--locked','--offline',*(['--release']if release else[]),'--','--test-threads=1'],SCRATCH/label/'vm');assert p.returncode==0
(HERE/'frozen-runtime-parity.json').write_bytes(b.enc(comparisons));print('56 baseline/candidate Frozen observations identical across Debug/Release; original integration suites passed',flush=True)
