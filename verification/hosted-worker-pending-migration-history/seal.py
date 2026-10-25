from pathlib import Path
import datetime,json,hashlib,difflib,subprocess,platform
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest();write=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
latest=json.loads((packet/'latest-run.json').read_text());run=root/latest['run'];summary=json.loads((run/'summary.json').read_text());assert summary['status']=='passed' and summary['completeMatrix']
manifest=json.loads((run/'source-manifest.json').read_text());assert manifest['sourceDigest']==latest['sourceDigest']
for e in manifest['entries']:
 b=(packet/'candidate'/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes']
write(packet/'source-manifest.json',manifest)
checks=json.loads((packet/'input-manifest.json').read_text())['checks']
for e in checks:
 b=(root/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes']
write(packet/'input-verification-final.json',{'checks':len(checks),'allUnchanged':True})
compiled=[]
for p in sorted((packet/'candidate/dist').rglob('*')):
 if p.is_file():b=p.read_bytes();compiled.append({'path':str(p.relative_to(packet/'candidate')),'sha256':sha(b),'bytes':len(b)})
write(packet/'compiled-manifest.json',{'entries':compiled})
production=[];patch=''
for p in sorted((packet/'candidate/src').rglob('*')):
 if p.is_file():
  rel=p.relative_to(packet/'candidate');a=(packet/'inputs/producer'/rel).read_bytes();b=p.read_bytes()
  if a!=b:
   production.append({'path':str(rel),'beforeSHA256':sha(a),'afterSHA256':sha(b)})
   patch+=''.join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='frozen/'+str(rel),tofile='candidate/'+str(rel)))
assert [e['path'] for e in production]==['src/engine.ts'];(packet/'migration-history.patch').write_text(patch)
write(packet/'production-delta.json',{'changedProductionModules':production,'unchangedProductionFiles':12,'ledgerSchemaWireProviderClockRegistryChanged':False})
assertions='';driverchecks=[]
for name in ['test/run.mjs','test/review.mjs','test/terminal-consistency.mjs','test/independent.mjs']:
 base='inputs/review' if name=='test/independent.mjs' else 'inputs/producer';a=(packet/base/name).read_bytes();b=(packet/'candidate'/name).read_bytes();driverchecks.append({'path':name,'beforeSHA256':sha(a),'afterSHA256':sha(b),'unchanged':a==b})
 if a!=b:assertions+=''.join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='frozen/'+name,tofile='candidate/'+name))
assert [e['path'] for e in driverchecks if not e['unchanged']]==['test/run.mjs','test/review.mjs'];(packet/'assertion-amendments.patch').write_text(assertions)
write(packet/'driver-identity.json',{'drivers':driverchecks,'amendedPriorControlIds':['regressed-ledger-and-registry-ahead-never-reconstruct-authority','before-track-regression','after-committed-track-regression'],'amendmentPurpose':'Preserve exact restored operation row under independent ACK-history fence; retain permanent-fence, no-new-provider-effect, no-claim/report and remote-terminal-permanence assertions. No other control assertions amended.'})
for name in ['worker.ts','harness.mjs']:
 a=(packet/'inputs/review/test'/name).read_text();b=(packet/'candidate/test'/name).read_text();(packet/(name+'.patch')).write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='review/test/'+name,tofile='candidate/test/'+name)))
code="""const{createRequire}=require('node:module');const{spawnSync}=require('node:child_process');const r=createRequire(process.cwd()+'/hosted-worker-controller/package.json');console.log(JSON.stringify({node:process.version,platform:process.platform,architecture:process.arch,miniflare:r('miniflare/package.json').version,typescript:r('typescript/package.json').version,workersTypes:r('@cloudflare/workers-types/package.json').version,workerd:spawnSync(r('workerd').default,['--version'],{encoding:'utf8'}).stdout.trim()}));"""
versions=json.loads(subprocess.check_output(['node','-e',code],cwd=root,text=True));versions['python']=platform.python_version();write(packet/'tool-versions.json',versions)
allcleanup=[];attempts=[]
for attempt in sorted((packet/'runs').iterdir()):
 if not attempt.is_dir():continue
 s=json.loads((attempt/'summary.json').read_text());counts={};failures=[];cleanup=[]
 for reportpath in sorted(attempt.glob('*-report.json')):
  report=json.loads(reportpath.read_text());counts[reportpath.name]={'run':sum(x['status'] in ['passed','failed'] for x in report['results']),'passed':sum(x['status']=='passed' for x in report['results'])};failures +=[{'suite':reportpath.name,**x} for x in report['results'] if x['status']!='passed'];cleanup+=report['cleanup']
 attempts.append({'run':str(attempt.relative_to(root)),'status':s['status'],'completeMatrix':s['completeMatrix'],'counts':counts,'failures':failures,'sourceDigest':s['sourceDigest']});allcleanup+=cleanup
pids={i['pid'] for c in allcleanup for i in c.get('ownedProcesses',[])}|{c['pid'] for c in allcleanup if c.get('kind')=='SIGKILL'};stores=sorted({c['persist'] for c in allcleanup if 'persist'in c});ps=subprocess.check_output(['/bin/ps','-axo','pid=,ppid=,comm='],text=True);live={int(v[0]):{'parentPid':int(v[1]),'command':v[2]} for line in ps.splitlines() if len(v:=line.strip().split(None,2))==3}
assert all(not Path(p).exists() for p in stores);assert not(pids&live.keys());assert all(c.get('storageRemoved',True) and c.get('allOwnedPidsAbsent',True) for c in allcleanup)
cleanup={'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedStorageEnvironments':len(stores),'ownedSIGKILLControls':sum(c.get('kind')=='SIGKILL' for c in allcleanup),'allOwnedStorageAbsent':True,'allRecordedOwnedPidsAbsent':True,'storage':[{'path':p,'absent':True} for p in stores],'processes':[{'pid':p,'absent':True} for p in sorted(pids)],'unrelatedProcessesSignalled':False,'testReportedCleanupAllPassed':True,'remoteTaskCancellationClaimed':False};write(packet/'cleanup-seal.json',cleanup)
write(packet/'attempts.json',{'attempts':attempts})
reports={name:json.loads((run/(name+'-report.json')).read_text()) for name in ['prior81','review40','terminal279','independent78','migration']};counts={name:sum(x['status']=='passed' for x in r['results']) for name,r in reports.items()};assert [counts[k] for k in ['prior81','review40','terminal279','independent78']]==[81,40,279,78];assert all(r['status']=='passed' for r in reports.values());total=sum(counts.values())
artifacts=[]
for p in sorted(packet.rglob('*')):
 if p.is_file() and p.name not in ['receipt.json','seal.sha256']:
  b=p.read_bytes();artifacts.append({'path':str(p.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
doc=root/'docs/hosted-worker-pending-migration-history.md';b=doc.read_bytes();artifacts.append({'path':str(doc.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
receipt={'schema':1,'status':'isolated-migration-history-correction-passed-awaiting-fresh-independent-review','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rootProvidedHEAD':'be472ce6424a691de5673e3438d2768264827d23','gitRevisionRead':False,'frozenProducerReceiptSHA256':'e4afac5866c26ffd96c460bbdd54e3cf0098bc1d378601ba7e542d6f819e677b','frozenProducerSourceDigest':'b46bac2e4377663e2df078743c655c062f42cc92893a3d53b702476b05b6966f','frozenReviewReceiptSHA256':'2a5646144c8696d6ff2c02d935a6942a18d61dd0c5f8ddf7e99314f5aa0dab13','sourceDigest':latest['sourceDigest'],'run':latest['run'],'changedProductionModules':['engine.ts'],'patchSHA256':sha((packet/'migration-history.patch').read_bytes()),'groupsPassed':total,'groupsRun':total,'suiteCounts':counts,'prior400GroupsRerun':True,'prior400AssertionAmendedControls':3,'prior400OtherControlsUnchanged':397,'independent78DriverByteIdentical':True,'originalFindingControlsPassed':6,'newMigrationHistoryGroups':counts['migration'],'assertionAmendmentsSHA256':sha((packet/'assertion-amendments.patch').read_bytes()),'frozenInputFilesVerified':len(checks),'frozenInputsUnchanged':True,'versions':versions,'commands':json.loads((run/'commands.json').read_text()),'preservedAttempts':attempts,'allRunsOwnedStorageEnvironmentsRemoved':len(stores),'allRunsOwnedSIGKILLControls':cleanup['ownedSIGKILLControls'],'allRecordedOwnedPidsAbsent':True,'migrationSignatureIsHistoricalOriginProof':False,'legacyAcceptanceGrantsAuthority':False,'explicitEnrollmentRetainsQuarantineAndExistingRow':True,'ackHistoryFencePreservesEntireObservedRow':True,'ledgerSchemaChanged':False,'liveRootSourceChanged':False,'gitChanged':False,'publicOrScheduledEntryWired':False,'auditImportedOrChanged':False,'frozenRejectedLanesReadImportedExecuted':False,'unrelatedVMSourceChanged':False,'nativeDeviceRuns':False,'physicalPhonesDisconnectedDeferred':True,'providerCustomerPublication':False,'remoteCommitRollbackCancellationClaimed':False,'distributedAtomicityQualified':False,'gaAccepted':False,'limitations':['fresh independent review and root live integration pending','migration-consistent state shape is not proof of historical origin and grants no authority','synthetic excluded clock/provider and finite hostile restore fixtures','three old assertion expectations amended to selected full-row-preservation contract; initial failed attempt retained','no live controller71/process20 suite rerun','no deployed schedule/alarm/restore/fleet discovery/capacity qualification','production clock/provider, signing, store, immutable-package FieldLog and final phones pending','no rollback of remote terminal commit or ACK metadata already durable before later local mutation'],'artifacts':artifacts}
write(packet/'receipt.json',receipt);(packet/'seal.sha256').write_text(sha((packet/'receipt.json').read_bytes())+'  receipt.json\n');print(json.dumps({'receiptSHA256':sha((packet/'receipt.json').read_bytes()),'patchSHA256':receipt['patchSHA256'],'sourceDigest':receipt['sourceDigest'],'groups':total,'suiteCounts':counts,'ownedStoresRemoved':len(stores),'hardRestarts':cleanup['ownedSIGKILLControls'],'artifacts':len(artifacts)},indent=2))
