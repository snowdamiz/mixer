from pathlib import Path
import json,hashlib,subprocess,datetime,importlib.util,shutil,difflib
root=Path(__file__).resolve().parents[2];packet=Path(__file__).resolve().parent
producer=root/'verification/hosted-worker-pending-terminal-consistency'
sha=lambda b:hashlib.sha256(b).hexdigest();write=lambda p,d:p.write_text(json.dumps(d,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('review_prepare',packet/'prepare.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
binding=module.checks();write(packet/'frozen-final.json',binding)
production=[];compiled=[];baseline=[]
for p in sorted((packet/'candidate/src').rglob('*')):
 if p.is_file():
  rel=p.relative_to(packet/'candidate');b=p.read_bytes();assert b==(producer/'candidate'/rel).read_bytes()
  production.append({'path':str(rel),'sha256':sha(b),'bytes':len(b)})
for p in sorted((packet/'candidate/dist/src').rglob('*')):
 if p.is_file():
  rel=p.relative_to(packet/'candidate');b=p.read_bytes();assert b==(producer/'candidate'/rel).read_bytes()
  compiled.append({'path':str(rel),'sha256':sha(b),'bytes':len(b)})
for p in sorted((packet/'baseline-candidate/src').rglob('*')):
 if p.is_file():
  rel=p.relative_to(packet/'baseline-candidate');b=p.read_bytes();assert b==(producer/'inputs/frozen-candidate'/rel).read_bytes()
  baseline.append({'path':str(rel),'sha256':sha(b),'bytes':len(b)})
write(packet/'production-identity.json',{'candidateSourceByteIdentical':True,'candidateFiles':production,'candidateCompiledByteIdentical':True,'candidateCompiledFiles':compiled,'baselineSourceByteIdentical':True,'baselineFiles':baseline})
for name in ['test/worker.ts','test/harness.mjs']:
 a=(producer/'candidate'/name).read_text();b=(packet/'candidate'/name).read_text()
 (packet/(name.split('/')[-1]+'.patch')).write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='producer/'+name,tofile='review/'+name)))
code="const {createRequire}=require('node:module');const{spawnSync}=require('node:child_process');const r=createRequire(process.cwd()+'/hosted-worker-controller/package.json');console.log(JSON.stringify({node:process.version,platform:process.platform,architecture:process.arch,miniflare:r('miniflare/package.json').version,typescript:r('typescript/package.json').version,workersTypes:r('@cloudflare/workers-types/package.json').version,workerd:spawnSync(r('workerd').default,['--version'],{encoding:'utf8'}).stdout.trim()}));"
version=subprocess.run(['node','-e',code],cwd=root,capture_output=True,text=True,check=True);versions=json.loads(version.stdout)
write(packet/'tool-versions.json',{'versions':versions,'command':['node','-e',code],'cwd':str(root),'exitCode':version.returncode,'stdout':version.stdout,'stderr':version.stderr,'stdoutEOF':True,'stderrEOF':True})
reports={name:json.loads((packet/path).read_text()) for name,path in [('initialProbes','probe-report.json'),('initial68','attempts/initial68/independent-report.json'),('final78','independent-report.json'),('baseline6','baseline-report.json')]}
cleanup=[c for r in reports.values() for c in r['cleanup']]
stores=sorted({c['persist'] for c in cleanup if 'persist' in c})
pids={i['pid'] for c in cleanup for i in c.get('ownedProcesses',[])}|{c['pid'] for c in cleanup if c.get('kind')=='SIGKILL'}
process=subprocess.run(['/bin/ps','-axo','pid=,ppid=,comm='],capture_output=True,text=True,check=True)
live={int(v[0]):{'parentPid':int(v[1]),'command':v[2]} for line in process.stdout.splitlines() if len(v:=line.strip().split(None,2))==3}
assert all(not Path(p).exists() for p in stores);assert not(pids&live.keys())
assert all(c.get('storageRemoved',True) and c.get('allOwnedPidsAbsent',True) for c in cleanup)
cleanupSeal={'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ownedStorageEnvironments':len(stores),'ownedHardRestarts':sum(c.get('kind')=='SIGKILL' for c in cleanup),'allOwnedStorageAbsent':True,'allRecordedOwnedPidsAbsent':True,'unrelatedProcessesSignalled':False,'remoteTaskCancellationClaimed':False,'storage':[{'path':p,'absent':True} for p in stores],'processes':[{'pid':p,'absent':True} for p in sorted(pids)],'observationCommand':['/bin/ps','-axo','pid=,ppid=,comm='],'observationExitCode':process.returncode,'stdoutEOF':True,'stderrEOF':True}
write(packet/'cleanup-seal.json',cleanupSeal)
assert len(stores)==158 and cleanupSeal['ownedHardRestarts']==14
shutil.rmtree(packet/'__pycache__',ignore_errors=True)
artifacts=[]
for p in sorted(packet.rglob('*')):
 if p.is_file() and p.name not in ['receipt.json','seal.sha256']:
  b=p.read_bytes();artifacts.append({'path':str(p.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
doc=root/'docs/hosted-worker-pending-terminal-consistency-review.md';b=doc.read_bytes();artifacts.append({'path':str(doc.relative_to(root)),'sha256':sha(b),'bytes':len(b)})
receipt={'schema':1,'status':'findings-not-accepted-for-live-integration','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rootProvidedHEAD':'ee390cbf56ba388a21c7d28c884dbed5fd7282fe','gitRevisionRead':False,'producerReceiptSHA256':binding['receiptSHA256'],'producerPatchSHA256':'ca15d306c91dbdbccc3ae858fb09c0236258f5e51c2fa9dbc38b914ae73284d5','producerSourceDigest':binding['sourceDigest'],'reviewSourceDigest':json.loads((packet/'source-manifest.json').read_text())['sourceDigest'],'baselineSourceDigest':json.loads((packet/'baseline-source-manifest.json').read_text())['sourceDigest'],'producerArtifactsVerified':binding['producerArtifacts'],'frozenPriorBindingsVerified':binding['priorBindings'],'allFrozenInputsUnchanged':True,'candidateProductionSourceFiles':len(production),'candidateProductionSourceByteIdentical':True,'candidateProductionCompiledFiles':len(compiled),'candidateProductionCompiledByteIdentical':True,'baselineProductionSourceFiles':len(baseline),'baselineProductionSourceByteIdentical':True,'groupsFinalPassed':72,'groupsFinalRun':78,'findingControlsFailed':6,'baselineControlsPassed':4,'baselineControlsRun':6,'prior400GroupsRerun':False,'attempts':[{'name':k,'groupsRun':r['groupsRun'],'groupsPassed':r['groupsPassed'],'status':r['status']} for k,r in reports.items()],'findings':[{'id':'migrated-terminal-explicit-enrollment-blocked','priority':'P2','introducedByCandidate':True,'source':'candidate/src/engine.ts:51','dependentEntry':'candidate/src/engine.ts:524','actualWorkerdSQLiteCandidateFailures':4,'actualWorkerdSQLitePredecessorPasses':4},{'id':'no-outbox-terminal-ACK-ahead-unfenced','priority':'P2','introducedByCandidate':False,'source':'candidate/src/engine.ts:51','bypass':'candidate/src/engine.ts:107','actualWorkerdSQLiteCandidateFailures':2,'actualWorkerdSQLitePredecessorFailures':2}],'commands':json.loads((packet/'commands.json').read_text()),'versions':versions,'ownedStorageEnvironmentsRemoved':len(stores),'ownedHardRestarts':cleanupSeal['ownedHardRestarts'],'allRecordedOwnedPidsAbsent':True,'liveRootSourceChanged':False,'gitChanged':False,'liveVMTouched':False,'publicOrScheduledEntryChanged':False,'auditReadImportedOrChanged':False,'frozenRejectedLanesReadImportedExecuted':False,'providerDeploymentCredentialCustomerChanges':False,'nativeOrPhysicalDeviceRuns':False,'physicalPhonesDeferred':True,'remoteCommitRollbackCancellationClaimed':False,'distributedAtomicityQualified':False,'gaAccepted':False,'limitations':['synthetic excluded clock/provider with actual local workerd SQLite','no live 71/20 suite rerun','candidate not accepted; introduced migration regression and preexisting history gap remain','no deployed schedule/alarm/restore/capacity qualification','no immutable-package FieldLog/final phones/production provider clock/GA qualification','no rollback of remote terminal or local ACK already committed before a later mutation'],'artifacts':artifacts}
write(packet/'receipt.json',receipt);digest=sha((packet/'receipt.json').read_bytes());(packet/'seal.sha256').write_text(digest+'  receipt.json\n')
print(json.dumps({'receiptSHA256':digest,'reviewSourceDigest':receipt['reviewSourceDigest'],'artifacts':len(artifacts),'finalGroups':'72/78','ownedStoresRemoved':len(stores),'ownedHardRestarts':cleanupSeal['ownedHardRestarts']}))
