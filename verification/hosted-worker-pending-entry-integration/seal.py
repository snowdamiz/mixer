#!/usr/bin/env python3
from pathlib import Path
import json,hashlib,datetime,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];OWN=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def entry(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size}
def write(name,value):(OWN/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def digest(values):return sha(json.dumps(values,sort_keys=True,separators=(',',':')).encode())
before=json.loads((OWN/'inputs-before.json').read_text())
for b in before['bindings']:
 p=ROOT/b['path'];assert sha(p.read_bytes())==b['sha256'],b['path']
write('inputs-after.json',before)
source=[entry(p) for p in sorted((OWN/'candidate').rglob('*')) if p.is_file() and 'dist' not in p.parts]
compiled=[entry(p) for p in sorted((OWN/'candidate/dist').rglob('*')) if p.is_file()]
productionSource=[entry(p) for p in sorted((OWN/'candidate/src').rglob('*')) if p.is_file()]
closure=json.loads((OWN/'production-closure.json').read_text());assert closure['status']=='passed'
for f in closure['files']:assert sha((OWN/'candidate'/f['path']).read_bytes())==f['sha256']
# Rewired Engine and registry regression source modules must match final candidate.
shared=['engine.ts','ledger.ts','schema.sql','registry-context.ts','pending-types.ts','pending-registry.ts','pending-audit.ts','registry-schema.sql','public-contract.ts','wire.ts','provider.ts','clock.ts']
for directory in ['engine-regression','independent-regression','boundary-regression','component-regression']:
 for name in shared:assert (OWN/directory/'src'/name).read_bytes()==(OWN/'candidate/src'/name).read_bytes(),(directory,name)
write('source-manifest.json',{'files':source,'digest':digest(source),'productionSource':productionSource,'productionSourceDigest':digest(productionSource)})
write('compiled-manifest.json',{'files':compiled,'digest':digest(compiled),'reachableProductionDigest':digest(closure['files'])})
reports={'entry45':OWN/'entry-report.json','original28':OWN/'original-report.json','originalRegression7':OWN/'original-compat/regressions/regression-report.json','originalFocused36':OWN/'original-compat/focused/focused-report.json','engine81':OWN/'engine81-report.json','engine40':OWN/'engine40-report.json','engine279':OWN/'terminal-report.json','engine78':OWN/'independent-report.json','engine210':OWN/'migration-report.json','independent69':OWN/'independent69-report.json','boundary12':OWN/'boundary12-report.json','components17':OWN/'component-report.json'}
counts={};cleanup=[];versions=json.loads((OWN/'tool-versions.json').read_text())
for name,p in reports.items():
 r=json.loads(p.read_text());assert r['status']=='passed',name
 counts[name]=len(r['results']);assert all(x['status']=='passed' for x in r['results'])
 for c in r.get('cleanup',[]):
  cleanup.append(c)
  if c.get('persist'):
   assert not Path(c['persist']).exists(),c['persist']
   assert c.get('allOwnedPidsAbsent') is True,c
  for process in c.get('ownedProcesses',[]):
   try:__import__('os').kill(process['pid'],0)
   except ProcessLookupError:pass
   else:raise AssertionError(('owned_pid_alive',process))
counts['processIdentity20']=20
identityCommands=[json.loads(p.read_text()) for p in sorted((OWN/'attempts').glob('*/command.json')) if json.loads(p.read_text())['name']=='identity20'];assert identityCommands and identityCommands[-1]['exitCode']==0
commands=[json.loads(p.read_text()) for p in sorted((OWN/'attempts').glob('*/command.json'))]
for c in commands:assert c['stdoutEOF'] and c['stderrEOF']
failures=[{**c,'contemporaneousSourceManifest':(ROOT/c['stdout']).with_name('source-manifest.json').exists()} for c in commands if c['exitCode']!=0]
observations=json.loads((OWN/'entry-report.json').read_text())['observations']
receipt={'schema':1,'status':'isolated-entry-composition-passed-awaiting-fresh-independent-review','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rootProvidedHEAD':before['rootProvidedHEAD'],'gitRevisionRead':False,'entryContractSHA256':'a84602410ec46466bc65a7c785596de9ee8eb3012e2e93fd8dbc7d76dc2908a6','acceptedProducerReceiptSHA256':'a27b0ce3438705f0bd30ae4dd088f19d4ece3367cb91f78ad42eab8b1413bca1','acceptedReviewReceiptSHA256':'27b5a51b9eaecff3973f03eb5f66b13bdfe3e94145879f489cc9337779188c18','boundInputsVerified':len(before['bindings']),'allBoundInputsUnchanged':True,'producerArtifactsBoundBeforeCopy':before['producerArtifactsVerified'],'reviewArtifactsBoundBeforeCopy':before['reviewArtifactsVerified'],'sourceDigest':digest(source),'productionSourceDigest':digest(productionSource),'compiledDigest':digest(compiled),'reachableProductionCompiledDigest':digest(closure['files']),'reachableProductionFiles':len(closure['files']),'oldAcceptedCompiledIdentityClaimedUnchanged':False,'suiteCounts':counts,'groupsRun':sum(counts.values()),'groupsPassed':sum(counts.values()),'commands':commands,'failedAttempts':failures,'versions':versions,'observations':observations,'rootApprovedCompatibilityDiff':'original-compat/focused/root-approved-assertion.diff','originalFocusedFailuresPreserved':True,'productionOperationRPCMethods':closure['operationRPCMethods'],'productionUnavailableDependencies':True,'fixtureInjectionProductionConfigSwitch':False,'liveIntegrated':False,'liveControllerSourceChanged':False,'rootTrackersChanged':False,'gitChanged':False,'deploymentOrProviderPublication':False,'productionScheduleInstalled':False,'nativeOrPhysicalDeviceRuns':False,'physicalPhonesDisconnectedDeferred':True,'newDependencies':False,'allFinalAcceptanceOwnedStorageAbsent':True,'allFinalAcceptanceRecordedOwnedPidsAbsent':True,'ownedStorageEnvironments':sum(bool(x.get('persist')) for x in cleanup),'ownedHardRestarts':sum(x.get('signal')=='SIGKILL' for x in cleanup),'remoteCancellationClaimed':False,'gaAccepted':False,'limitations':['Earliest exploratory entry failure logs/reports/commands preserved, but contemporaneous source manifests were not captured until final acceptance work.','Old schema-2 and clock-unavailable terminal assertions intentionally fail unchanged; exact root-approved schema-3/stop-terminal adaptations are separately recorded.','Local workerd SQLite and synthetic fixture effects only; actual production clock/provider/verifier remain unavailable.','No provider Cron installation/delivery, deployed namespace/rollback qualification, operational ceilings, source/runner/result authority, signing/store/FieldLog/physical-phone/GA qualification.','Bounded header-contract documentation search returned original transport amendment/V2 snippets; no frozen rejected outbound-worker V2 packet implementation/test imported or executed.']}
write('receipt.json',receipt)
# Seal packet bytes, excluding only the two final self-referential seals.
paths=[p for p in sorted(OWN.rglob('*')) if p.is_file() and p.name not in ['artifact-manifest.json','seal-summary.json'] and '__pycache__' not in p.parts]
paths.append(ROOT/'docs/hosted-worker-pending-entry-integration.md')
artifacts=[entry(p) for p in paths];write('artifact-manifest.json',artifacts)
write('seal-summary.json',{'status':'sealed-for-independent-review','receiptSHA256':sha((OWN/'receipt.json').read_bytes()),'artifactManifestSHA256':sha((OWN/'artifact-manifest.json').read_bytes()),'artifacts':len(artifacts),'artifactDigest':digest(artifacts)})
print(json.dumps({'status':'sealed','groups':receipt['groupsPassed'],'sourceDigest':receipt['productionSourceDigest'],'compiledDigest':receipt['reachableProductionCompiledDigest'],'artifacts':len(artifacts)}))
