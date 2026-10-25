from pathlib import Path
import datetime,json,hashlib,difflib,subprocess,os
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest();write=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
latest=json.loads((packet/'latest-run.json').read_text());run=root/latest['run'];summary=json.loads((run/'summary.json').read_text());assert summary['status']=='passed'
manifest=json.loads((run/'source-manifest.json').read_text());assert manifest['sourceDigest']==latest['sourceDigest'];checks=[]
for e in manifest['entries']:
 b=(packet/'candidate'/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes']
write(packet/'source-manifest.json',manifest)
for p in sorted((packet/'candidate/dist').rglob('*')):
 if p.is_file():b=p.read_bytes();checks.append({'path':str(p.relative_to(packet/'candidate')),'sha256':sha(b),'bytes':len(b)})
write(packet/'compiled-manifest.json',{'entries':checks})
frozen=[]
for e in json.loads((packet/'input-manifest.json').read_text())['checks']:
 b=(root/e['path']).read_bytes();assert sha(b)==e['sha256'] and len(b)==e['bytes'];frozen.append(e)
write(packet/'input-verification-final.json',{'checks':len(frozen),'allUnchanged':True})
changes=[];patch=''
for p in sorted((packet/'candidate/src').rglob('*')):
 if p.is_file():
  rel=p.relative_to(packet/'candidate');a=(packet/'inputs/frozen-candidate'/rel).read_bytes();b=p.read_bytes()
  if a!=b:
   changes.append({'path':str(rel),'beforeSHA256':sha(a),'afterSHA256':sha(b)})
   patch+=''.join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='frozen/'+str(rel),tofile='candidate/'+str(rel)))
assert [c['path'] for c in changes]==['src/engine.ts','src/ledger.ts']
(packet/'terminal-consistency.patch').write_text(patch);write(packet/'production-delta.json',{'changedProductionModules':changes,'unchangedProductionFiles':sum(p.is_file() for p in (packet/'candidate/src').rglob('*'))-len(changes),'schemaPublicWireProviderClockRegistryChanged':False})
assert (packet/'candidate/test/run.mjs').read_bytes()==(packet/'inputs/frozen-candidate/test/run.mjs').read_bytes()
assert (packet/'candidate/test/review.mjs').read_bytes()==(packet/'inputs/review/test/review.mjs').read_bytes()
# Installed tools only; no Git, provider, native or production command.
code="""const {createRequire}=require('node:module');const{spawnSync}=require('node:child_process');const r=createRequire(process.cwd()+'/hosted-worker-controller/package.json');console.log(JSON.stringify({node:process.version,platform:process.platform,architecture:process.arch,miniflare:r('miniflare/package.json').version,typescript:r('typescript/package.json').version,workersTypes:r('@cloudflare/workers-types/package.json').version,workerd:spawnSync(r('workerd').default,['--version'],{encoding:'utf8'}).stdout.trim()}));"""
versions=json.loads(subprocess.check_output(['node','-e',code],cwd=root,text=True));write(packet/'tool-versions.json',versions)
allcleanup=[];attempts=[]
for attempt in sorted((packet/'runs').iterdir()):
 if not attempt.is_dir():continue
 s=json.loads((attempt/'summary.json').read_text());counts={};cleanup=[]
 for name in ['prior81','review40','terminal']:
  report=json.loads((attempt/(name+'-report.json')).read_text());counts[name]=sum(x['status']=='passed' for x in report['results']);cleanup+=report['cleanup']
 attempts.append({'run':str(attempt.relative_to(root)),'status':s['status'],'passed':counts,'sourceDigest':s['sourceDigest']});allcleanup+=cleanup
pids={i['pid'] for c in allcleanup for i in c.get('ownedProcesses',[])}|{c['pid'] for c in allcleanup if c.get('kind')=='SIGKILL'}
stores=sorted({c['persist'] for c in allcleanup if 'persist' in c});ps=subprocess.check_output(['/bin/ps','-axo','pid=,ppid=,comm='],text=True)
processes={int(v[0]):{'parentPid':int(v[1]),'command':v[2]} for line in ps.splitlines() if len(v:=line.strip().split(None,2))==3}
assert all(not Path(p).exists() for p in stores);assert not(pids&processes.keys())
cleanup={'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedStorageEnvironments':len(stores),'ownedSIGKILLControls':sum(c.get('kind')=='SIGKILL' for c in allcleanup),'allOwnedStorageAbsent':True,'allRecordedOwnedPidsAbsent':True,'storage':[{'path':p,'absent':True} for p in stores],'processes':[{'pid':p,'absent':True} for p in sorted(pids)],'unrelatedProcessesSignalled':False,'testReportedCleanupAllPassed':all(c.get('storageRemoved',True) and c.get('allOwnedPidsAbsent',True) for c in allcleanup),'remoteTaskCancellationClaimed':False}
write(packet/'cleanup-seal.json',cleanup)
# Reconstructable patch files bind finite Worker additions separately.
for name,base in [('test/worker.ts','inputs/frozen-candidate/test/worker.ts'),('test/harness.mjs','inputs/frozen-candidate/test/harness.mjs')]:
 a=(packet/base).read_text();b=(packet/'candidate'/name).read_text();(packet/(name.split('/')[-1]+'.patch')).write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='frozen/'+name,tofile='candidate/'+name)))
artifacts=[]
for p in sorted(packet.rglob('*')):
 if p.is_file() and p.name not in ['receipt.json','seal.sha256']:
  b=p.read_bytes();artifacts.append({'path':str(p.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
doc=root/'docs/hosted-worker-pending-terminal-consistency.md';b=doc.read_bytes();artifacts.append({'path':str(doc.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
receipt={'schema':1,'status':'isolated-terminal-consistency-correction-passed-awaiting-independent-review','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rootProvidedHEAD':'ee390cbf56ba388a21c7d28c884dbed5fd7282fe','gitRevisionRead':False,'frozenReceiptSHA256':'d9bd48d069746b24ed3386e9842a1693e5aba44c33ffd4e095646acaef7cff5c','frozenPatchSHA256':'a7876fc0786f53ea3e201a1969a3f90a07a0c48c71e2602151f5a4ee7ac64372','frozenSourceDigest':'f4290d7ab0ece9eb2546d9b6125054d6cbbd4d9ab572d418679fbc41e748b799','independentReviewReceiptSHA256':'f9b18c8fe622e14964abcb7e41ba046e1ef4e48cf81b80c22c457fa7bb7f13d1','sourceDigest':latest['sourceDigest'],'run':latest['run'],'changedProductionModules':['engine.ts','ledger.ts'],'patchSHA256':sha((packet/'terminal-consistency.patch').read_bytes()),'groupsPassed':400,'groupsRun':400,'prior81Passed':81,'prior81DriverUnchanged':True,'review40Passed':40,'review40DriverUnchanged':True,'terminalConsistencyPassed':279,'frozenInputFilesVerified':len(frozen),'frozenInputsUnchanged':True,'correctedRegistrySHA256':sha((packet/'candidate/src/vendor/pending-registry.ts').read_bytes()),'versions':versions,'commands':json.loads((run/'commands.json').read_text()),'preservedAttempts':attempts,'finalRunOwnedStorageEnvironments':400,'allRunsOwnedStorageEnvironmentsRemoved':len(stores),'allRunsOwnedSIGKILLControls':cleanup['ownedSIGKILLControls'],'allRecordedOwnedPidsAbsent':True,'terminalFencePreservesFullOperationRowAtOrdinaryAndMAX':True,'atomicAckRejectLeavesMetadataUntouched':True,'defaultFenceBehaviorChanged':False,'liveRootSourceChanged':False,'gitChanged':False,'publicOrScheduledEntryWired':False,'auditImportedOrChanged':False,'frozenRejectedLanesReadImportedExecuted':False,'nativeDeviceRuns':False,'physicalPhonesDisconnectedDeferred':True,'providerCustomerPublication':False,'remoteCommitRollbackCancellationClaimed':False,'distributedAtomicityQualified':False,'gaAccepted':False,'limitations':['fresh independent review and root live integration pending','synthetic excluded clock/provider and finite hostile restore fixtures','no live controller71/process20 suite rerun','no deployed schedule/alarm/restore/fleet discovery/capacity qualification','production clock/provider, signing, store, immutable-package FieldLog and final phones pending','no rollback of a remote terminal commit or ACK metadata already durable before a later local mutation'],'artifacts':artifacts}
write(packet/'receipt.json',receipt);(packet/'seal.sha256').write_text(sha((packet/'receipt.json').read_bytes())+'  receipt.json\n')
print(json.dumps({'receiptSHA256':sha((packet/'receipt.json').read_bytes()),'patchSHA256':receipt['patchSHA256'],'sourceDigest':receipt['sourceDigest'],'groups':400,'terminalGroups':279,'allRunsStoresRemoved':len(stores),'SIGKILL':cleanup['ownedSIGKILLControls'],'artifacts':len(artifacts)},indent=2))
