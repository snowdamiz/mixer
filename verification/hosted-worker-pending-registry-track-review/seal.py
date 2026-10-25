from pathlib import Path
import hashlib,json,datetime,os,subprocess
packet=Path(__file__).resolve().parent;root=packet.parents[1];candidate=packet/'candidate';frozen=root/'verification/hosted-worker-pending-registry-track-recheck/candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
entries=[{'path':str(p.relative_to(candidate)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(candidate.rglob('*')) if p.is_file() and 'dist' not in p.relative_to(candidate).parts]
digest=hashlib.sha256(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in entries).encode()).hexdigest()
(packet/'source-manifest.json').write_text(json.dumps({'algorithm':'sha256','sourceDigest':digest,'entries':entries},indent=2)+'\n')
compiled=[{'path':str(p.relative_to(candidate)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((candidate/'dist').rglob('*')) if p.is_file()]
(packet/'compiled-manifest.json').write_text(json.dumps({'algorithm':'sha256','entries':compiled},indent=2)+'\n')
production=[{'path':str(p.relative_to(candidate)),'reviewSHA256':sha(p),'frozenSHA256':sha(frozen/p.relative_to(candidate)),'identical':sha(p)==sha(frozen/p.relative_to(candidate))} for p in sorted((candidate/'src').rglob('*')) if p.is_file()]
assert all(e['identical'] for e in production)
(packet/'production-parity.json').write_text(json.dumps(production,indent=2)+'\n')
reports=[json.loads((packet/p).read_text()) for p in ['report.json','snapshot-consistency-report.json','runs/initial-snapshot-consistency/report.json']]
clean=[x for report in reports for x in report['cleanup'] if x.get('disposed')]
restarts=[x for report in reports for x in report['cleanup'] if x.get('kind')=='SIGKILL']
pids=sorted({i['pid'] for x in clean for i in x['ownedProcesses']})
ps=subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True,check=True)
processes={int(line.strip().split(None,1)[0]):line.strip() for line in ps.stdout.splitlines() if line.strip()}
cleanup={'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'disposedEnvironments':len(clean),'storageDirectories':[{'path':x['persist'],'absent':not Path(x['persist']).exists()} for x in clean],'ownedSIGKILLControls':len(restarts),'processObservations':[{'pid':pid,'absent':pid not in processes,'currentProcess':processes.get(pid)} for pid in pids],'allRecordedStorageAbsent':all(not Path(x['persist']).exists() for x in clean),'allRecordedOwnedPidsAbsent':all(pid not in processes for pid in pids),'unrelatedProcessesSignalled':False}
assert cleanup['allRecordedStorageAbsent'] and cleanup['allRecordedOwnedPidsAbsent']
(packet/'cleanup-seal.json').write_text(json.dumps(cleanup,indent=2)+'\n')
commands=json.loads((packet/'commands.json').read_text());assert [x['exitCode'] for x in commands]==[0,0,1]
main=reports[0];assert main['groupsRun']==40 and main['groupsPassed']==40
assert all(x['status']=='passed' for x in main['results'])
assert reports[1]['status']=='failed' and reports[2]['status']=='failed'
for p in ['input-verification-before.json','input-verification-after.json']:assert json.loads((packet/p).read_text())['status']=='passed'
artifacts=[{'path':str(p.relative_to(root)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(packet.rglob('*')) if p.is_file() and p.name not in ['receipt.json','seal.sha256'] and 'dist' not in p.relative_to(packet).parts]
doc=root/'docs/hosted-worker-pending-registry-track-review.md';artifacts.append({'path':str(doc.relative_to(root)),'sha256':sha(doc),'bytes':doc.stat().st_size})
receipt={'schema':1,'status':'findings-not-accepted-for-live-integration','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'frozenReceiptSHA256':'d9bd48d069746b24ed3386e9842a1693e5aba44c33ffd4e095646acaef7cff5c','frozenPatchSHA256':'a7876fc0786f53ea3e201a1969a3f90a07a0c48c71e2602151f5a4ee7ac64372','frozenCandidateSourceDigest':'f4290d7ab0ece9eb2546d9b6125054d6cbbd4d9ab572d418679fbc41e748b799','reviewCandidateSourceDigest':digest,'rootProvidedHEAD':'ee390cbf56ba388a21c7d28c884dbed5fd7282fe','gitRevisionRead':False,'frozenBindingChecksBefore':91,'frozenBindingChecksAfter':91,'productionSourceByteIdentical':True,'productionFilesCompared':len(production),'groupsFocusedPassed':40,'groupsFocusedRun':40,'additionalRegressionGroupsFailed':1,'additionalRegressionReproductions':2,'frozen81GroupsRerun':False,'prior75PassAndMAXRollbackFailurePreserved':True,'findings':[{'id':'terminal-projection-phase-not-bound-to-permanent-row','priority':'P2','source':'candidate/src/engine.ts:79','introducedByTrackRecheckDelta':False,'actualWorkerd':True,'actualSQLite':True,'expectedFailClosedButObservedRPCAndOutboxClear':True}],'commands':commands,'toolVersions':json.loads((packet/'tool-versions.json').read_text()),'cleanup':cleanup,'artifacts':artifacts,'liveFilesModified':False,'gitModified':False,'publicOrScheduledEntryWired':False,'providerOrCustomerPublication':False,'nativeOrDeviceRuns':False,'remoteTerminalCancellationClaimed':False,'distributedAtomicityQualified':False,'gaAccepted':False,'limitations':['finding requires candidate correction and focused retest before root integration acceptance','excluded synthetic clock/provider and finite restore fixtures','no live 71/20 suite rerun','no deployment, independent fleet discovery, deployed alarm/restore or GA qualification','physical phones disconnected and deferred','no frozen catalog-inspector/authority-driver or rejected outbound transport evaluation']}
(packet/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(packet/'seal.sha256').write_text(sha(packet/'receipt.json')+'  receipt.json\n')
print(json.dumps({'status':receipt['status'],'receiptSHA256':sha(packet/'receipt.json'),'sourceDigest':digest,'groupsPassed':40,'failingRegressions':1,'cleanupEnvironments':len(clean),'allRecordedPidsAbsent':cleanup['allRecordedOwnedPidsAbsent']}))
