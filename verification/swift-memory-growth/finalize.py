#!/usr/bin/env python3
"""Collect exact final packet, clean only owned scratch, then seal for review."""
from pathlib import Path
import datetime,gzip,json,os,shutil,subprocess,tarfile
from run import HERE,SCRATCH,manifest,digest,enc,sha
base=json.loads((HERE/'baseline-source-manifest.json').read_text());candidate=manifest(SCRATCH/'candidate/vm');closure=digest(candidate)
assert closure=='56e47ffa2c74ea243c9ead371a5ebfdeb59e85c0f05555419d51c84483afabe3'and len(candidate)==127
(HERE/'candidate-source-manifest.json').write_bytes(enc(candidate));shutil.copyfile(HERE/'sources'/(closure+'.tar.gz'),HERE/'candidate-source.tar.gz')
commands={p.parent.name:json.loads(p.read_text())for p in sorted((HERE/'commands').glob('*/receipt.json'))}
(HERE/'command-index.json').write_bytes(enc(commands))
qualifying=[name for name in commands if name.startswith(('qualified-','layout-qualified-','isolated-'))]
assert len([n for n in qualifying if n.startswith('layout-qualified-')])==16
assert all(commands[n]['exitCode']==0 for n in qualifying)
for name in qualifying:
 row=commands[name]
 if row['sourceTreeSHA256']:
  target=row['environment']['CARGO_TARGET_DIR'];assert'/target-source-'+row['sourceTreeSHA256']+'/'in target
  for binary in row['executables']:assert binary['path'].startswith(target+'/')
# Frozen/accepted identity includes exact source and compiler expansion, never
# source-pattern authorization for a release.
control=(SCRATCH/'candidate/vm/src/experimental_swift_reactor/control.rs').read_text()
growth=(SCRATCH/'candidate/vm/src/experimental_swift_reactor/memory_growth_operations.rs').read_text().split('// ACCOUNTING_START')[0]
start=growth.index('let ticket=slot.take()');end=growth.index('} else {Ok(())}',start)
tail=growth[start:end];assert'test'not in tail and'check('not in tail and'control.drop_reserved_with_wasi((),ticket,wasi)'in tail
(HERE/'refund-predicate-proof.json').write_bytes(enc(dict(controllerSHA256=sha(control.encode()),growthBodySHA256=sha(growth.encode()),predicates=[dict(borrowed='ticket.owner != self.owner || ticket.owner == 0',refund='same predicate',equivalent=True),dict(borrowed='live_tickets == 0',refund='live_tickets.checked_sub(1).is_none()',equivalent=True),dict(borrowed='category.current < ticket.bytes',refund='category.current.checked_sub(ticket.bytes).is_none()',equivalent=True),dict(borrowed='combined.current < ticket.bytes',refund='combined.current.checked_sub(ticket.bytes).is_none()',equivalent=True)],afterTakeSource=tail,exclusiveControlBorrow=True,unitStorageHasNoDestructor=True,noFallibleGap=True,foreignNewAndOldTicketNegativeTests=['mg12_ticket_retention_retry_refusal','mg17_old_refund_postcommit_retained_retry'],scope='Unchanged actual controller predicates and executed rejection-before-take behavior; no new release authority')))
receipt=dict(scope='private-bounded-host-memory-growth-candidate',baselineSourceSHA256=digest(base),candidateSourceSHA256=closure,baselineFiles=len(base),candidateFiles=len(candidate),sourceRevisionAtCapture=json.loads((HERE/'session.json').read_text())['sourceRevision'],rootBaselineCommit='a1f78d1e88d6e1e934a08cdb85ce90f87f6ff343',candidateArchiveSHA256=sha((HERE/'candidate-source.tar.gz').read_bytes()),qualifyingCommands=qualifying,excludedFailedCommands=[name for name,row in commands.items()if row['exitCode']!=0],excludedCacheOrContextCommands=[name for name,row in commands.items()if name not in qualifying and row['sourceTreeSHA256']],acceptance=dict(independentReview='pending',rootIntegration='pending',product='pending',ga='pending'),freshGrowthSelections=78,freshBroadReleaseSelections=98,priorBroadReleaseTests=78,repeatedGrowthBroadReleaseTests=20,freshFrozenCases=40,freshFrozenPairs=20,pairedLayouts=16,positiveNewFields=10356,retainedMemoryFields=4800,retainedBulkFields=4324,originalOwnerDeclarations=14,frozenExpandedMethods=39,reusedEvidence=dict(upstreamPriorExecutionSelections=312,status='historical-unchanged-component-only-not-current-source-four-config-passes'),nativeOrPhysicalToolsUsed=False,deferred=['independent-growth-review','root-growth-integration','host-imports','full-Swift-dispatch-and-calls','Ready-public-invocation','full-Swift-target','native-joins','simulator-emulator-native-joins','immutable-published-separate-repository-FieldLog','physical-phones','signing','store','customer','operational','GA','G08-absent-cursor'],completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
(HERE/'receipt.json').write_bytes(enc(receipt))
# Every retained source is already archived before touching disposable targets.
assert SCRATCH.name.startswith('mixer-swift-growth-')and SCRATCH.parent!=SCRATCH
probe=subprocess.run(['lsof','-nP','+D',str(SCRATCH)],capture_output=True,text=True)
(HERE/'cleanup-lsof.stdout').write_text(probe.stdout);(HERE/'cleanup-lsof.stderr').write_text(probe.stderr);assert probe.returncode==1 and probe.stdout.strip()==''
files=sum(1 for p in SCRATCH.rglob('*')if p.is_file());bytes_=sum(p.stat().st_size for p in SCRATCH.rglob('*')if p.is_file())
shutil.rmtree(SCRATCH);assert not SCRATCH.exists()
(HERE/'cleanup.json').write_bytes(enc(dict(scratch=str(SCRATCH),removed=True,openFilesBeforeRemoval=0,lsofExitCode=probe.returncode,filesRemoved=files,bytesRemoved=bytes_,nativeOrPhysicalToolsUsed=False,otherProjectsTouched=False,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())))
for cache in list(HERE.rglob('__pycache__')):shutil.rmtree(cache)
files={str(p.relative_to(HERE)):sha(p.read_bytes())for p in sorted(HERE.rglob('*'))if p.is_file()and p.name not in['seal.json','offline-verify.log']}
docs={name:sha((HERE.parents[1]/name).read_bytes())for name in['docs/swift-memory-growth-contract.md','docs/swift-memory-growth-implementation.md']}
(HERE/'seal.json').write_bytes(enc(dict(files=files,documentation=docs,sourceTreeSHA256=closure,createdUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())))
print('Candidate',closure,'files',len(candidate),'qualifying commands',len(qualifying),'owned scratch removed',bytes_,flush=True)
