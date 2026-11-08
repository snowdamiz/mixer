import datetime,hashlib,json,subprocess,sys
from pathlib import Path
out=Path(__file__).resolve().parent
cand=Path('/Users/andreyyurlov/.t3/worktrees/mixer/t3-9ff4db6c')
producer=cand/'verification/plan-continuation-2026-11-07/android-motion-thread-fix'
def ident(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
assert all(ident(cand/p)==v for p,v in json.loads((producer/'final-source-map.json').read_text()).items())
audit=json.loads((out/'audit.json').read_text())
host=json.loads((out/'host-replay/receipt.json').read_text())
assert host['status']=='passed-host-only' and host['source_stable']
for name in ['targeted-commands.json','lifetime-commands.json']:
 for r in json.loads((out/name).read_text()):
  assert r['exit']==0 and r['stop'] is None and r['childReaped'] and r['ownedGroupAbsentAfterReap']
  assert ident(out/(r['label']+'.stdout'))==r['stdout']
  assert ident(out/(r['label']+'.stderr'))==r['stderr']
result={
 'verdict':'REQUEST_CHANGES','reviewer':'gpt-6-astra xhigh independent child review','startedUTC':'2026-11-07T23:57:01Z','finishedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'candidateBase':audit['candidateBase'],'parentHeadAtApplyCheck':audit['parentHead'],'candidateTree':str(cand),'patch':audit['patch'],'profile':audit['profile'],'canonicalInputs':audit['canonical'],
 'findings':[
  {'id':'R1','severity':'P2','file':'native/android/tests/NativeCoordinatorV2IntegrationInstrumentation.java','lines':[132,136],'title':'Sideband callback requires owner drain to remain pending','basis':'Reproduced exact candidate product host control/counterexample; both schedules refresh correctly, only one satisfies native line134','evidence':['targeted-ordering.stdout','targeted-result.json','MotionOrderingProbe.java'],'nativeReproduction':False},
  {'id':'R2','severity':'P2','file':'native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java','lines':[198,205],'title':'Coalesced callback omits producer-to-main getter publication','basis':'Source/Java memory-model inference; failed CAS does not publish, drain set(false) does not acquire; inspected framework scalar is nonvolatile','evidence':['publication-model.json','publication-model.py','host-replay/javap-NativeEnvironmentPlatformV2$Api33.stdout'],'nativeOrJVMStaleReadReproduction':False,'limit':'Current AOSP source is not bound to exact API37 image; finite manually stated HB model is not a complete Java verifier'}],
 'notFindings':[
  {'topic':'Queued closure retention after remove','conclusion':'No demonstrated retirement/retention contract violation','observed':'One entry retained after close, zero after drain; late callback cannot enqueue; closed epoch unchanged; no resurrection','limits':'No immediate reclamation contract found; no GC timing or indefinitely stalled-queue test','evidence':'lifetime-control.stdout'},
  {'topic':'Handler.post false on Binder','conclusion':'No admitted-platform stale-authority failure demonstrated','observed':'Injected refusal throws and resets reservation without Binder owner mutation; main current check rejects stale tuple and ordinary owner drain recovers','platformReasoning':'Inspected queue enqueue false is quitting; normal main Looper disallows quit','limits':'Injected live-queue refusal exceeds standard inspected semantics; not exact API37 image qualification','evidence':['lifetime-control.stdout','official-source.json']}],
 'freshExecution':{'focusedObserverPlatformReplays':1,'observerCases':187,'platformCases':134,'platformAssertions':699,'independentOrderingSchedules':2,'independentLifetimeRefusalControls':2,'fullBMatrices':0,'swiftBuilds':0,'nativeRuns':0,'pureChecks':['source/hash/patch/profile/canonical inventory/baseline custody','1364-file producer manifest','finite HB model with publication positive control']},
 'inspectedNotRepeated':['recorded1323-case14675-check fullB','recorded1157-check focused B','18 Python admission tests','22 Swift tests','strict SDK37 Java17 and D8 compilation'],
 'nativeHarness':{'originalSmokeAssertions':11,'originalReadinessBudgets':'three unchanged100x20ms','motionBudgets':'300x20ms and25x20ms quiet flush','twoStageEffectiveAndRawRestoration':'present; unrun; R1 applies to restoration oracle too','manualCallbackSubstitution':False},
 'parentOwnedWork':{'CIRebind':'Recompute corrected integrated source hashes; replace bootstrap pair8 digest and test/wording with final pair9; preserve all safeguards','sixConsumerRun':'Parent reported in progress at /tmp/mixer-20261107-generated-java-pair9-01; not inspected/polled here; no inherited acceptance'},
 'pending':['R1 native oracle correction','R2 explicit coalesced publication and matching source identity updates','parent actual pair9 six-consumer result and final integrated CI rebind','API37 callback/removal/two-stage restoration','API28/32/33 runtime','physical phones','published external FieldLog','signing/store/GA'],
 'ownership':{'newFilesOnly':str(out),'productCandidateCanonicalCIOrOldEvidenceEdits':False,'commitPushCloudChildrenDeviceUIADBOrHeldProcessProbe':False},
 'cleanup':{'hostReceipt':'host-replay/receipt.json','targeted':'targeted-cleanup.json','lifetime':'lifetime-cleanup.json','ownedScratchRemoved':True,'ownedHostChildrenReaped':True},
 'scope':'independent read-only product review with permitted host executions; no native or GA qualification','report':'REVIEW.md'}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
manifest={str(p.relative_to(out)):ident(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='manifest.json'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print(json.dumps({'verdict':result['verdict'],'finishedUTC':result['finishedUTC'],'filesSealed':len(manifest),'report':ident(out/'REVIEW.md'),'result':ident(out/'result.json')}))
