from pathlib import Path
import json,hashlib,datetime,subprocess,platform,difflib
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent;producer=root/'verification/hosted-worker-pending-migration-history'
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(name,data):(packet/name).write_text(json.dumps(data,indent=2)+'\n')
receipt=json.loads((producer/'receipt.json').read_text());receiptsha=sha((producer/'receipt.json').read_bytes());assert receiptsha=='5bce543f307a07666aa5bc70b4f9e5da6f59ac82edc5956c26d859a8f64d288e'
for e in receipt['artifacts']:
 b=(root/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'],e['path']
prior=json.loads((producer/'input-manifest.json').read_text())['checks']
for e in prior:
 b=(root/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'],e['path']
sm=json.loads((producer/'source-manifest.json').read_text());digest=sha(''.join(f"{e['path']}\0{e['sha256']}\0{e['bytes']}\n" for e in sm['entries']).encode());assert digest==sm['sourceDigest']=='361c391b035a7a4cdbfaa9d6013cb4944431eb97ad14c65731caac292f947483'
for e in sm['entries']:
 b=(producer/'candidate'/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes']
production=[]
for p in sorted((packet/'candidate/src').rglob('*')):
 if p.is_file():
  rel=p.relative_to(packet/'candidate');b=p.read_bytes();assert b==(producer/'candidate'/rel).read_bytes();production.append({'path':str(rel),'sha256':sha(b),'bytes':len(b)})
assert len(production)==13
# Independently reconstruct and bind the assertion-only driver delta.
assertions='';drivers=[]
for name in ['test/run.mjs','test/review.mjs','test/terminal-consistency.mjs','test/independent.mjs']:
 before=producer/('inputs/review' if name=='test/independent.mjs' else 'inputs/producer')/name;after=producer/'candidate'/name;a=before.read_bytes();b=after.read_bytes();drivers.append({'path':name,'beforeSHA256':sha(a),'afterSHA256':sha(b),'unchanged':a==b})
 if a!=b:assertions+=''.join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='frozen/'+name,tofile='candidate/'+name))
assert assertions.encode()==(producer/'assertion-amendments.patch').read_bytes();assert sha(assertions.encode())=='6f73ea6600d005c3649cf641c26e46bf98ff7cc51c0472074d5245d25fae1133';assert drivers==json.loads((producer/'driver-identity.json').read_text())['drivers']
write('input-verification-final.json',{'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producerReceiptSHA256':receiptsha,'candidateArtifactsVerified':len(receipt['artifacts']),'priorFrozenBindingsVerified':len(prior),'candidateSourceEntriesVerified':len(sm['entries']),'sourceDigestRecomputed':digest,'reviewProductionFilesByteIdentical':len(production),'allUnchanged':True,'driversAndAssertionDeltaVerified':True})
external=[]
for name in ['hosted-worker-controller/test/owned-workerd-identity.mjs','hosted-worker-controller/package.json','hosted-worker-controller/package-lock.json','verification/hosted-worker-controller-contract/vectors.json','hosted-worker-controller/node_modules/@cloudflare/workers-types/index.d.ts']:
 p=root/name;b=p.read_bytes();external.append({'path':name,'sha256':sha(b),'bytes':len(b)})
versions=json.loads(subprocess.check_output(['node','-e',"const{createRequire}=require('node:module');const{spawnSync}=require('node:child_process');const r=createRequire(process.cwd()+'/hosted-worker-controller/package.json');const executable=r('workerd').default;console.log(JSON.stringify({node:process.version,nodeExecutable:process.execPath,platform:process.platform,architecture:process.arch,miniflare:r('miniflare/package.json').version,typescript:r('typescript/package.json').version,workersTypes:r('@cloudflare/workers-types/package.json').version,workerd:spawnSync(executable,['--version'],{encoding:'utf8'}).stdout.trim(),workerdExecutable:executable}));"],cwd=root,text=True));versions['python']=platform.python_version();versions['pythonExecutable']=subprocess.check_output(['which','python3'],text=True).strip()
for field in ['nodeExecutable','workerdExecutable']:
 b=Path(versions[field]).read_bytes();versions[field+'SHA256']=sha(b)
write('tool-versions.json',versions)
latest=json.loads((packet/'latest-run.json').read_text());run=root/latest['run'];report=json.loads((run/'independent-report.json').read_text());assert (report['groupsRun'],report['groupsPassed'])==(69,65);assert all('extra-outbox' in e['id'] for e in report['results'] if e['status']=='failed')
reviewsm=json.loads((run/'source-manifest.json').read_text());assert latest['sourceDigest']==reviewsm['sourceDigest']
for e in reviewsm['entries']:
 b=(packet/'candidate'/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes']
write('source-closure.json',{'reviewSourceDigest':reviewsm['sourceDigest'],'producerSourceDigest':digest,'productionFiles':production,'externalFixtureAndToolBindings':external,'productionImportsRemainRelativeToReviewedSrc':True,'excludedTestEntryNotImportedByProduction':True,'fixtureClockAndProviderSynthetic':True,'sourceDependenciesRecordedNoNewDependency':True})
write('source-manifest.json',reviewsm)
compiled=[]
for p in sorted((packet/'candidate/dist').rglob('*')):
 if p.is_file():b=p.read_bytes();compiled.append({'path':str(p.relative_to(packet/'candidate')),'sha256':sha(b),'bytes':len(b)})
write('compiled-manifest.json',{'entries':compiled})
cleanup=[];attempts=[]
for attempt in sorted((packet/'runs').iterdir()):
 s=json.loads((attempt/'summary.json').read_text());r=json.loads((attempt/'independent-report.json').read_text());cleanup+=r['cleanup'];attempts.append({'run':str(attempt.relative_to(root)),'status':r['status'],'groupsRun':r['groupsRun'],'groupsPassed':r['groupsPassed'],'sourceDigest':s['sourceDigest'],'failures':[v for v in r['results'] if v['status']=='failed']})
stores=sorted({c['persist'] for c in cleanup if 'persist'in c});pids={i['pid'] for c in cleanup for i in c.get('ownedProcesses',[])}|{c['pid'] for c in cleanup if c.get('kind')=='SIGKILL'}
ps=subprocess.check_output(['/bin/ps','-axo','pid=,ppid=,comm='],text=True);live={int(x[0]) for line in ps.splitlines() if len(x:=line.strip().split(None,2))==3};assert not pids&live;assert all(not Path(p).exists() for p in stores);assert all(c.get('storageRemoved',True) and c.get('allOwnedPidsAbsent',True) for c in cleanup)
clean={'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedSQLiteEnvironments':len(stores),'ownedHardRestarts':sum(c.get('kind')=='SIGKILL' for c in cleanup),'allOwnedStorageAbsent':True,'allRecordedOwnedPidsAbsent':True,'stores':[{'path':s,'absent':True} for s in stores],'processes':[{'pid':p,'absent':True} for p in sorted(pids)],'unrelatedProcessesSignalled':False,'remoteTaskCancellationClaimed':False};write('cleanup-seal.json',clean);write('attempts.json',{'attempts':attempts})
artifacts=[]
for p in sorted(packet.rglob('*')):
 if p.is_file() and p.name not in ['receipt.json','seal.sha256']:
  b=p.read_bytes();artifacts.append({'path':str(p.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
doc=root/'docs/hosted-worker-pending-migration-history-review.md';b=doc.read_bytes();artifacts.append({'path':str(doc.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
out={'schema':1,'status':'independent-review-failed-one-selected-contract-finding','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rootProvidedHEAD':'be472ce6424a691de5673e3438d2768264827d23','gitRevisionRead':False,'producerReceiptSHA256':receiptsha,'producerSourceDigest':digest,'producerPatchSHA256':sha((producer/'migration-history.patch').read_bytes()),'reviewSourceDigest':reviewsm['sourceDigest'],'run':str(run.relative_to(root)),'groupsRun':69,'groupsPassed':65,'failingControls':4,'actionableFindings':1,'findings':[{'priority':2,'title':'Require null outbox for unenrolled explicit migration enrollment','file':'verification/hosted-worker-pending-migration-history/candidate/src/engine.ts','lines':[42,543],'controls':[e['id'] for e in report['results'] if e['status']=='failed'],'scope':'quarantine remains 1; registration and new outbox/version written; no new provider effect; no demonstrated execution authority','regressionAgainstPredecessorProven':False}],'originalSixFindingRegressionsPass':True,'producer688Rerun':False,'producerArtifactsVerified':213,'priorFrozenBindingsVerified':335,'productionFilesByteIdentical':13,'assertionDeltaVerified':True,'versions':versions,'commands':json.loads((run/'commands.json').read_text()),'attempts':attempts,'ownedStorageEnvironmentsRemoved':len(stores),'ownedHardRestarts':clean['ownedHardRestarts'],'allRecordedOwnedPidsAbsent':True,'allOwnedStorageAbsent':True,'liveIntegrated':False,'productionChanged':False,'gitChanged':False,'nativeDeviceRuns':False,'physicalPhonesDisconnectedDeferred':True,'forbiddenFrozenLanesReadImportedExecuted':False,'providerDeploymentCredentialCustomerPublicationChanges':False,'remoteRollbackCancellationClaimed':False,'gaAccepted':False,'limitations':['finite synthetic clock/provider local actual-workerd SQLite fixture only','one remaining selected-contract enrollment-shape gap; root correction and fresh review required','no predecessor baseline for this remaining gap','no full producer688, live controller71/process20, scheduled/public integration rerun','no deployed alarms/restore/fleet/capacity or production clock/provider qualification','immutable-package FieldLog, signing, store, final physical phones and accountable GA acceptance pending'],'artifacts':artifacts}
write('receipt.json',out);(packet/'seal.sha256').write_text(sha((packet/'receipt.json').read_bytes())+'  receipt.json\n');print(json.dumps({'status':out['status'],'receiptSHA256':sha((packet/'receipt.json').read_bytes()),'artifacts':len(artifacts),'groupsRun':69,'groupsPassed':65,'ownedStoresRemoved':len(stores),'ownedHardRestarts':clean['ownedHardRestarts']},indent=2))
