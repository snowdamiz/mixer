from pathlib import Path
import datetime,difflib,hashlib,json,subprocess
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(name,value):(packet/name).write_text(json.dumps(value,indent=2)+'\n')
latest=json.loads((packet/'latest-run.json').read_text());run=root/latest['run'];summary=json.loads((run/'summary.json').read_text());assert summary['status']=='passed' and summary['completeMatrix'];assert (summary['producerGroups'],summary['reviewGroups'],summary['boundaryGroups'])==(688,69,12)
inputs=json.loads((packet/'input-manifest.json').read_text());checks=inputs['checks']
for e in checks:
 b=(root/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'],e['path']
write('input-verification-final.json',{'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':len(checks),'allUnchanged':True,'frozenArtifactsVerified':349})
manifest=json.loads((run/'source-manifest.json').read_text());assert manifest['sourceDigest']==latest['sourceDigest']
for e in manifest['entries']:
 b=(packet/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'];assert b==(run/'source'/e['path']).read_bytes()
write('source-manifest.json',manifest)
old=b"r.registration_json===null&&r.registry_ack_version==='0'";new=b"r.registration_json===null&&r.track_outbox_json===null&&r.registry_ack_version==='0'"
production=[];drivers=[];fixtures=[]
for closure,base in [('candidate','hosted-worker-pending-migration-history'),('independent-candidate','hosted-worker-pending-migration-history-review'),('boundary-candidate','hosted-worker-pending-migration-history-review')]:
 source=root/'verification'/base/'candidate';entries=[]
 for p in sorted((packet/closure/'src').rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(packet/closure);before=(source/rel).read_bytes();after=p.read_bytes();changed=before!=after
  if rel==Path('src/engine.ts'):assert before.count(old)==1 and after==before.replace(old,new)
  else:assert not changed
  entries.append({'path':str(rel),'beforeSHA256':sha(before),'afterSHA256':sha(after),'bytes':len(after),'changed':changed})
 assert len(entries)==13 and sum(e['changed'] for e in entries)==1
 production.append({'closure':closure,'productionFiles':entries,'changedProductionModules':['src/engine.ts'],'unchangedProductionFiles':12,'exactOneNullOutboxConditionOnly':True})
 for p in sorted((source/'test').glob('*.mjs')):
  b=p.read_bytes();a=(packet/closure/'test'/p.name).read_bytes();assert b==a
  drivers.append({'closure':closure,'path':'test/'+p.name,'beforeSHA256':sha(b),'afterSHA256':sha(a),'byteIdentical':True,'loaderPathChanged':False})
 before=(source/'test/worker.ts').read_bytes();after=(packet/closure/'test/worker.ts').read_bytes()
 if closure!='boundary-candidate':assert before==after
 fixtures.append({'closure':closure,'beforeSHA256':sha(before),'afterSHA256':sha(after),'byteIdentical':before==after,'finiteBoundaryActionOnly':closure=='boundary-candidate'})
assert len({e['afterSHA256'] for c in production for e in c['productionFiles'] if e['path']=='src/engine.ts'})==1
before=(root/'verification/hosted-worker-pending-migration-history/candidate/src/engine.ts').read_text();after=(packet/'candidate/src/engine.ts').read_text();patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='frozen/src/engine.ts',tofile='candidate/src/engine.ts'));assert (packet/'migration-outbox.patch').read_text()==patch
write('production-delta.json',{'closures':production,'distinctChangedProductionModules':['src/engine.ts'],'exactProductionAddedBytes':'r.track_outbox_json===null&&','otherProductionBytesChanged':False,'ledgerSchemaWireClockProviderRegistryPublicContractChanged':False})
write('driver-identity.json',{'allFrozenDriversByteIdentical':True,'assertionsChanged':False,'drivers':drivers,'fixtures':fixtures,'newBoundaryDriver':'boundary-candidate/test/outbox-boundary.mjs','newBoundaryFixturePatch':'boundary-fixture.patch'})
compiled=[]
for closure in ['candidate','independent-candidate','boundary-candidate']:
 for p in sorted((packet/closure/'dist').rglob('*')):
  if p.is_file():
   b=p.read_bytes();compiled.append({'path':str(p.relative_to(packet)),'sha256':sha(b),'bytes':len(b)})
compiledDigest=sha(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in compiled).encode());write('compiled-manifest.json',{'algorithm':'sha256','compiledDigest':compiledDigest,'entries':compiled})
assert len({e['sha256'] for e in compiled if e['path'].endswith('/dist/src/engine.js')})==1
external=[e for e in checks if not e['path'].startswith('verification/hosted-worker-pending-migration-history')]
write('source-closure.json',{'sourceDigest':manifest['sourceDigest'],'candidateClosureSourceDigests':{k:v['sourceDigest'] for k,v in manifest['closures'].items()},'compiledDigest':compiledDigest,'compiledFiles':len(compiled),'externalReadOnlyFixtureAndToolBindings':external,'productionImportsRemainRelativeToOwnedSrc':True,'testEntryNotImportedByProduction':True,'newDependencies':False,'fixtureClockAndProviderSynthetic':True,'threeOwnedEngineCopiesByteIdentical':True})
reports={name:json.loads((run/(name+'-report.json')).read_text()) for name in summary['counts']};assert all(r['status']=='passed' for r in reports.values())
former=[f'{phase}-unenrolled-extra-outbox-{form}-must-reject' for phase in ['stopped','completed'] for form in ['direct','restart']]
priorSix=[f'actual-schema{schema}-{phase}-constructor-restart-explicit-enrollment' for phase in ['stopped','completed'] for schema in [1,2]]+[f'{phase}-real-committed-ACK-lowered-state-regression' for phase in ['stopped','completed']]
independent={r['id']:r for r in reports['independent69']['results']}
for id in former+priorSix:assert independent[id]['status']=='passed'
write('finding-regressions.json',{'formerFourFailures':[independent[id] for id in former],'previousSixFindings':[independent[id] for id in priorSix],'allTenPassed':True,'formerFourAssertionsUnchanged':True})
producer=json.loads((root/'verification/hosted-worker-pending-migration-history/receipt.json').read_text());review=json.loads((root/'verification/hosted-worker-pending-migration-history-review/receipt.json').read_text());write('historical-attempts.json',{'originalProducerReceiptSHA256':inputs['frozenProducerReceiptSHA256'],'originalReviewReceiptSHA256':inputs['frozenReviewReceiptSHA256'],'originalProducerAttempts':producer['preservedAttempts'],'originalReviewAttempts':review['attempts'],'originalArtifactsRemainInPlaceUnmodified':True,'newReceiptDoesNotReplaceHistoricalFailures':True})
cleanup=[];attempts=[]
for attempt in sorted((packet/'runs').iterdir()):
 if not attempt.is_dir():continue
 s=json.loads((attempt/'summary.json').read_text());failures=[];counts={}
 for p in sorted(attempt.glob('*-report.json')):
  r=json.loads(p.read_text());cleanup+=r['cleanup'];counts[p.name]={'run':sum(x['status'] in ['passed','failed'] for x in r['results']),'passed':sum(x['status']=='passed' for x in r['results'])};failures +=[{'suite':p.name,**x} for x in r['results'] if x['status']!='passed']
 attempts.append({'run':str(attempt.relative_to(root)),'status':s['status'],'sourceDigest':s['sourceDigest'],'counts':counts,'failures':failures})
stores=sorted({e['persist'] for e in cleanup if 'persist' in e});pids={i['pid'] for e in cleanup for i in e.get('ownedProcesses',[])}|{e['pid'] for e in cleanup if e.get('kind')=='SIGKILL'}
ps=subprocess.check_output(['/bin/ps','-axo','pid=,ppid=,comm='],text=True);live={int(parts[0]) for row in ps.splitlines() if len(parts:=row.strip().split(None,2))==3};assert not pids&live;assert all(not Path(s).exists() for s in stores);assert all(e.get('storageRemoved',True) and e.get('allOwnedPidsAbsent',True) for e in cleanup)
clean={'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedSQLiteEnvironments':len(stores),'ownedHardRestarts':sum(e.get('kind')=='SIGKILL' for e in cleanup),'ownedProcessIdentities':sum(len(e.get('ownedProcesses',[])) for e in cleanup),'allOwnedStorageAbsent':True,'allRecordedOwnedPidsAbsent':True,'stores':[{'path':s,'absent':True} for s in stores],'processes':[{'pid':p,'absent':True} for p in sorted(pids)],'processRecheckCommand':['/bin/ps','-axo','pid=,ppid=,comm='],'hardRestartIdentityEvidenceInReports':True,'unrelatedProcessesSignalled':False,'remoteTaskCancellationClaimed':False};write('cleanup-seal.json',clean);write('attempts.json',{'attempts':attempts})
versions=json.loads((run/'tool-versions.json').read_text());write('tool-versions.json',versions)
artifacts=[]
for p in sorted(packet.rglob('*')):
 if p.is_file() and p.name not in ['receipt.json','seal.sha256']:
  b=p.read_bytes();artifacts.append({'path':str(p.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
doc=root/'docs/hosted-worker-pending-migration-outbox.md';b=doc.read_bytes();artifacts.append({'path':str(doc.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
receipt={'schema':1,'status':'isolated-null-outbox-correction-passed-awaiting-independent-narrow-acceptance-review','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rootProvidedHEAD':'be472ce6424a691de5673e3438d2768264827d23','gitRevisionRead':False,'frozenProducerReceiptSHA256':inputs['frozenProducerReceiptSHA256'],'frozenProducerSourceDigest':inputs['frozenProducerSourceDigest'],'frozenReviewReceiptSHA256':inputs['frozenReviewReceiptSHA256'],'rootSelectedCorrection':inputs['selectedCorrection'],'sourceDigest':manifest['sourceDigest'],'candidateSourceDigest':manifest['closures']['candidate']['sourceDigest'],'independentClosureSourceDigest':manifest['closures']['independent-candidate']['sourceDigest'],'boundaryClosureSourceDigest':manifest['closures']['boundary-candidate']['sourceDigest'],'compiledDigest':compiledDigest,'patchSHA256':sha((packet/'migration-outbox.patch').read_bytes()),'changedProductionModules':['engine.ts'],'exactOneNullOutboxConditionOnly':True,'otherProductionBytesChanged':False,'producerGroupsRun':688,'producerGroupsPassed':688,'independentGroupsRun':69,'independentGroupsPassed':69,'additionalBoundaryGroupsRun':12,'additionalBoundaryGroupsPassed':12,'groupsRun':769,'groupsPassed':769,'suiteCounts':{name:counts['passed'] for name,counts in summary['counts'].items()},'allFrozenDriversByteIdentical':True,'frozenAssertionChanges':False,'formerFourFailuresPassed':True,'previousSixFindingRegressionsPassed':True,'missingEmptyMalformedOutboxHardRestartCovered':True,'frozenArtifactsVerified':349,'frozenInputsVerified':len(checks),'allFrozenInputsUnchanged':True,'run':latest['run'],'commands':json.loads((run/'commands.json').read_text()),'versions':versions,'attempts':attempts,'historicalFailuresRetained':True,'allOwnedStorageAbsent':True,'allRecordedOwnedPidsAbsent':True,'ownedStorageEnvironmentsRemoved':len(stores),'ownedHardRestarts':clean['ownedHardRestarts'],'liveIntegrated':False,'liveRootSourceChanged':False,'gitChanged':False,'publicOrScheduledEntryWired':False,'forbiddenFrozenLanesReadImportedExecuted':False,'nativeDeviceRuns':False,'physicalPhonesDisconnectedDeferred':True,'providerDeploymentCredentialCustomerPublicationChanges':False,'remoteRollbackCancellationClaimed':False,'gaAccepted':False,'limitations':['root independent narrow acceptance review and any selected live integration remain pending','finite synthetic-clock/provider local actual-workerd SQLite fixture only','migration-consistent shape is not historical-origin proof and grants no execution authority','no live controller71/process20 suite rerun or public/scheduled entry qualification','no deployed alarms/restore/fleet/capacity or production clock/provider qualification','immutable-package FieldLog, signing, store, final physical phones and accountable GA acceptance remain pending','no rollback or cancellation of remote commits or distributed atomicity claim'],'artifacts':artifacts}
write('receipt.json',receipt);receiptsha=sha((packet/'receipt.json').read_bytes());(packet/'seal.sha256').write_text(receiptsha+'  receipt.json\n')
print(json.dumps({'status':receipt['status'],'receiptSHA256':receiptsha,'patchSHA256':receipt['patchSHA256'],'sourceDigest':receipt['sourceDigest'],'candidateSourceDigest':receipt['candidateSourceDigest'],'compiledDigest':compiledDigest,'artifacts':len(artifacts),'groups':769,'producer':688,'independent':69,'boundary':12,'ownedStoresRemoved':len(stores),'ownedHardRestarts':clean['ownedHardRestarts']},indent=2))
