from review import *
import shutil
assert SCRATCH.parent==Path('/tmp') and SCRATCH.name.startswith('mixer-memory-independent-review-')
verified=[]
for label in ['baseline','candidate','metadata-baseline','metadata-candidate','parity-baseline','parity-candidate']:
 assert manifest(SCRATCH/label/'vm')==json.loads((PRODUCER/(label+'-source-manifest.json')).read_text());verified.append(label)
for label,name in [('adversarial','historical-adversarial-v1'),('adversarial-v2','adversarial')]:
 assert manifest(SCRATCH/label/'vm')==json.loads((HERE/(name+'-source-manifest.json')).read_text());verified.append(label)
p=run('cleanup-lsof',['lsof','-nP','+D',str(SCRATCH)]);assert p.returncode==1 and p.stdout==b''
files=[p for p in SCRATCH.rglob('*') if p.is_file()];count=len(files);logical=sum(p.stat().st_size for p in files)
shutil.rmtree(SCRATCH);assert not SCRATCH.exists()
(HERE/'cleanup.json').write_bytes(enc(dict(scratch=str(SCRATCH),ownedScratchRemoved=True,sourceManifestsVerifiedBeforeRemoval=verified,lsofExitCode=p.returncode,lsofObservedNoOpenFiles=True,files=count,logicalFileBytes=logical,deviceInstancesCreated=0,simulatorOrEmulatorStarted=False,processesTerminated=False,otherProjectDataTouched=False,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())))
print('owned scratch removed; other projects preserved',flush=True)
