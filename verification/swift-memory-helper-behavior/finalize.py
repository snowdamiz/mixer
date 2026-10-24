from pathlib import Path
import json,gzip,tarfile,shutil,datetime,subprocess,os,re
from run import SCRATCH,HERE,b
ROOT=HERE.parents[1]
archives={}
for label,path in [('baseline',SCRATCH/'baseline/vm'),('candidate',SCRATCH/'candidate/vm'),('metadata-baseline',SCRATCH/'metadata-baseline-binary'),('metadata-candidate',SCRATCH/'metadata-candidate-binary'),('parity-baseline',SCRATCH/'parity-final2-baseline'),('parity-candidate',SCRATCH/'parity-final2-candidate')]:
 m=b.manifest(path);(HERE/(label+'-source-manifest.json')).write_bytes(b.enc(m))
 with tarfile.open(HERE/(label+'-source.tar.gz'),'w:gz')as t:
  for n in m:t.add(path/n,arcname='vm/'+n,recursive=False)
 with tarfile.open(HERE/(label+'-source.tar.gz'))as t:
  actual={member.name.removeprefix('vm/'):__import__('hashlib').sha256(t.extractfile(member).read()).hexdigest()for member in t.getmembers()};assert actual==m
 archives[label]=dict(files=len(m),closure=b.digest(m))
assert archives['baseline']['closure']=='241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5'
assert archives['candidate']['closure']=='6046a5fa8ba3800ec168b7ae6a80cb82bad5ba39b8701cb23a5db720d998bb62'
inputs=HERE/'inputs';inputs.mkdir()
for label,source in [('producer-receipt.json','swift-memory-helper-contract/receipt.json'),('review-receipt.json','swift-memory-helper-contract-review/receipt.json'),('root-acceptance.json','swift-memory-helper-root-review/acceptance.json'),('prerequisite-source.tar.gz','swift-memory-helper-contract/candidate-source.tar.gz')]:shutil.copy2(HERE.parent/source,inputs/label)
for config in ['production','unit']:
 p=HERE/(config+'.mir');(HERE/('canonical-'+config+'.mir.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0));p.unlink()
# Retain raw-byte hashes in each command receipt, and store raw output compressed.
commands=[];qualifying=[];binary_records=[]
for directory in sorted((HERE/'commands').iterdir()):
 rec=json.loads((directory/'receipt.json').read_text());commands.append(dict(name=directory.name,exitCode=rec['exitCode'],sourceClosure=rec['sourceTreeSHA256']))
 good=directory.name.startswith('final2-')and not directory.name.startswith('final2-layout') or directory.name.startswith('layout-binary-')
 if good:
  assert rec['exitCode']==0 and rec['sourceUnchanged'];qualifying.append(directory.name)
  for x in rec.get('executables',[]):binary_records.append(dict(command=directory.name,sourceClosure=rec['sourceTreeSHA256'],**x))
 for stream in ['stdout','stderr']:
  raw=directory/stream;assert b.sha(raw)==rec[stream+'SHA256'];(directory/(stream+'.gz')).write_bytes(gzip.compress(raw.read_bytes(),mtime=0));raw.unlink()
(HERE/'command-index.json').write_bytes(b.enc(commands));(HERE/'executable-manifest.json').write_bytes(b.enc(binary_records))
matrix=json.loads((HERE/'matrix-results.json').read_text());assert len(matrix)==64
for r in matrix:
 assert r['sourceClosure']==archives['candidate']['closure'];r['observedHarnessFixtureCount']=r.pop('observedFixtureCount');r['auxiliaryRealOwnerCount']=1 if r['id']=='mm07_pinned_decoded_caller'else 0;r['boundedRealOwnerCount']=r['observedHarnessFixtureCount']+r['auxiliaryRealOwnerCount'];assert r['boundedRealOwnerCount']<=64
(HERE/'matrix-results.json').write_bytes(b.enc(matrix))
# Archive all exact failed sources; their reconstruction is checked by manifests.
failures=json.loads((HERE/'historical-failed-source-reconstruction.json').read_text());assert len(failures)==3 and all(x['exactSourceReconstructed']for x in failures)
(HERE/'historical-attempts.json').write_bytes(b.enc(dict(failedCommands=[x for x in commands if x['exitCode']],failedExactSources=failures,excludedPrefixes=['draft','changed','corrected','accounted','runtime-','qualified-','layout-final2-'],note='Historical outputs are retained; only final2 and layout-binary commands qualify. Historical successful source snapshots predate the AF22 expectation/caller-cancellation additions.')))
versions={}
for name in ['rustc','cargo','rustfmt','python','host','git']:versions[name]=gzip.decompress((HERE/'commands'/('final2-tool-'+name)/'stdout.gz').read_bytes()).decode().strip()
receipt=dict(schema=1,status='candidate-frozen-for-fresh-independent-behavior-review',scope='Bounded private original-owner Swift Load/Store behavior on aarch64 host only',candidateSourceClosure=archives['candidate']['closure'],sourceArchives=archives,baselineSourceClosure=archives['baseline']['closure'],positiveFields=4792,productionCanonicalFields=2104,additionalUnitCanonicalFields=2156,authoredActiveFields=480,authoredPermanentFields=52,productionMemoryActiveBytes=624544,unitMemoryActiveBytes=1142696,memoryPermanentBytes=121856,productionHeaderBytes=1636360,unitHeaderBytes=2531040,productionFrameBytes=2836512,unitFrameBytes=5092824,stateLimitBytes=128*1024*1024,combinedLimitBytes=256*1024*1024,maximumReservationTickets=86,frozenReservationBytes=2912,frozenIdenticalExpandedMethods=39,memoryTestsExecuted=64,priorFrameControlTestsPerConfiguration=34,priorValueTestsPerConfiguration=12,priorConfigurations=4,frozenIdenticalRuntimeObservationPairs=56,frozenIntegrationTestsPerRun=16,frozenIntegrationRuns=4,qualifyingCommands=qualifying,qualifyingCommandCount=len(qualifying),toolVersions=versions,logicalNamedObjectAccountingOnly=True,independentReviewAccepted=False,rootAcceptance=False,liveVMEdited=False,fullDispatcher=False,readyOrPublicInvocation=False,nativeRuntime=False,physicalRuntime=False,UI=False,fullTargetExecuted=False,publishedFieldLogQualified=False,gaAcceptance=False,committed=False,pushed=False,G08='pending-preserved-absent-cursor-Cleanup-diagnostic',frozenFeatureDistinction='Swift-only MM14 records Frozen feature absent and requires the separate final2 all-feature baseline/candidate Debug/Release parity receipts; all-feature MM14 invokes actual SpanInstance',limitations=['Host logical requested/named-object bounds only; no compiler stack, allocator overhead or RSS claim.','Copy/fill/MemorySize/growth remain rejected by Swift memory API; full dispatcher/Ready/public/native joins remain pending.','Existing post-pop Cleanup retains original absent cursor/resource and real WASI; unreconciled debt never passes restoration.','Fresh independent behavior review and root acceptance are pending.','No phone/UI/full-target/published separate-repository FieldLog/signing/store/customer/operational/GA qualification.'],observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
# Only unique owned scratch is retired, after every qualifying source is archived.
files=list(p for p in SCRATCH.rglob('*')if p.is_file());cleanup=dict(scratch=str(SCRATCH),files=len(files),logicalFileBytes=sum(p.stat().st_size for p in files),sourceArchivesVerifiedBeforeRemoval=list(archives),deviceInstancesCreated=0,simulatorOrEmulatorStarted=False,processesTerminated=False,otherProjectDataTouched=False)
probe=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(SCRATCH)],capture_output=True);(HERE/'cleanup-lsof.stdout.gz').write_bytes(gzip.compress(probe.stdout,mtime=0));(HERE/'cleanup-lsof.stderr.gz').write_bytes(gzip.compress(probe.stderr,mtime=0));cleanup.update(lsofExitCode=probe.returncode,lsofObservedNoOpenFiles=probe.returncode==1 and not probe.stdout)
assert cleanup['lsofObservedNoOpenFiles'];shutil.rmtree(SCRATCH);cleanup.update(ownedScratchRemoved=not SCRATCH.exists(),completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat());(HERE/'cleanup.json').write_bytes(b.enc(cleanup));receipt['cleanup']=cleanup
for p in HERE.rglob('__pycache__'):shutil.rmtree(p)
receipt['documentationSHA256']=b.sha(ROOT/'docs/swift-memory-helper-behavior.md')
receipt['bindings']={str(p.relative_to(HERE)):b.sha(p)for p in sorted(HERE.rglob('*'))if p.is_file()and p not in [HERE/'receipt.json',HERE/'seal.json',HERE/'offline-verify.log']};receipt['boundEvidenceFiles']=len(receipt['bindings']);(HERE/'receipt.json').write_bytes(b.enc(receipt));(HERE/'seal.json').write_bytes(b.enc(dict(receiptSHA256=b.sha(HERE/'receipt.json'),candidateSourceClosure=receipt['candidateSourceClosure'],independentReviewAccepted=False)))
print('sealed',receipt['boundEvidenceFiles'],'files',len(qualifying),'qualifying commands',flush=True)
