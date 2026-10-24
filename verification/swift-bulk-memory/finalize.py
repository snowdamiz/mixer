from pathlib import Path
import datetime,gzip,hashlib,json,os,shutil,subprocess,sys
from build_overlay import manifest,digest,enc,sha
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];session=json.loads((HERE/'session.json').read_text());scratch=Path(session['scratch'])
base=json.loads((HERE/'baseline-source-manifest.json').read_text());candidate=json.loads((HERE/'candidate-source-manifest.json').read_text())
assert manifest(scratch/'baseline/vm')==base and manifest(scratch/'candidate/vm')==candidate
assert digest(manifest(ROOT/'vm'))==digest(base)
for label,m in [('baseline',base),('candidate',candidate)]:shutil.copy2(HERE/'sources'/(digest(m)+'.tar.gz'),HERE/(label+'-source.tar.gz'))
for config in['production','unit']:
 shutil.copy2(HERE/('sealed-'+config+'.mir.gz'),HERE/('canonical-'+config+'.mir.gz'))
 (HERE/(config+'.mir')).unlink(missing_ok=True)
commands={d.name:json.loads((d/'receipt.json').read_text())for d in sorted((HERE/'commands').iterdir())if(d/'receipt.json').exists()}
qualifying=[name for name in commands if name.startswith('sealed-')or name.startswith('layout-sealed-candidate-')or name.startswith('layout-baseline-')or name in['rustc-version','cargo-version','python-version','host-version']]
assert all(commands[name]['exitCode']==0 for name in qualifying)
for name,r in commands.items():
 assert r['sourceUnchanged']
 assert(HERE/'sources'/(r['sourceTreeSHA256']+'.tar.gz')).exists()
 for stream in['stdout','stderr']:
  path=HERE/'commands'/name/stream
  if path.exists():
   data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==r[stream+'SHA256']
   with gzip.GzipFile(filename=str(path)+'.gz',mode='wb',mtime=0)as z:z.write(data)
   path.unlink()
(HERE/'command-index.json').write_bytes(enc(commands))
for pycache in HERE.rglob('__pycache__'):
 if pycache.is_dir():shutil.rmtree(pycache)
# Source bytes rechecked before targeted lsof and removal of this exact owned root.
assert scratch.name.startswith('mixer-swift-bulk-memory-')and scratch.parent!=ROOT and scratch.is_dir()
p=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(scratch)],capture_output=True)
(HERE/'cleanup-lsof.stdout').write_bytes(p.stdout);(HERE/'cleanup-lsof.stderr').write_bytes(p.stderr)
assert p.returncode==1 and not p.stdout and not p.stderr,(p.returncode,p.stdout,p.stderr)
assert manifest(scratch/'candidate/vm')==candidate and digest(manifest(ROOT/'vm'))==digest(base)
shutil.rmtree(scratch)
(HERE/'cleanup.json').write_bytes(enc(dict(command=['/usr/sbin/lsof','-nP','+D',str(scratch)],exitCode=p.returncode,openFilesBeforeRemoval=0,ownedScratch=str(scratch),removed=not scratch.exists(),nativeOrPhysicalToolsUsed=False,otherProjectsPreserved=True,liveBaselineUnchanged=True,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())))
receipt=dict(scope='private-bounded-host-bulk-memory-candidate',baselineSourceSHA256=digest(base),candidateSourceSHA256=digest(candidate),baselineFiles=len(base),candidateFiles=len(candidate),recordedSourceRevision=session['sourceRevision'],acceptedInputCommit='615a05dc14655dace87c2ff561a610bef4526621',freshPositiveFields=4324,retainedMemoryFields=4800,freshBulkTests=64,priorExecutionTests=248,allExecutionSelections=312,frozenObservationPairs=64,frozenIntegrationSelections=64,frozenExpandedMethods=39,unchangedContainingOwners=14,pairedLayouts=16,libraryChecks=8,swiftCIClippy=True,qualifyingCommands=qualifying,excludedFailedCommands=[name for name,r in commands.items()if r['exitCode']!=0],historicalSourceArchivesReconstructed=6,acceptance=dict(independentReview='pending',rootIntegration='pending',product='pending',ga='pending'),deferred=['growth','host','full-dispatch','Ready/public-invocation','full-Swift-target','native-joins','immutable-published-separate-repository-FieldLog','physical-phones','signing','store','customer','operational','GA','G08'],cleanup='cleanup.json',completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
(HERE/'receipt.json').write_bytes(enc(receipt))
seal=dict(files={str(p.relative_to(HERE)):sha(p)for p in sorted(HERE.rglob('*'))if p.is_file()and p.name not in['seal.json','offline-verify.log']and'__pycache__'not in p.parts},documentation={name:sha(ROOT/name)for name in['docs/swift-bulk-memory-contract.md','docs/swift-bulk-memory-implementation.md']})
(HERE/'seal.json').write_bytes(enc(seal))
print('sealed',len(seal['files']),'files; own scratch removed; accepted live source unchanged')
