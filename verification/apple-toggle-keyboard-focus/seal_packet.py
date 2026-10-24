"""One immutable keyboard preparation seal; root alone selects native execution."""
import datetime
import json
import pathlib
import run
BASE,ROOT=run.BASE,run.ROOT;path=BASE/'packet-seal.json';assert not path.exists(),'Preserve rejected sealed bytes before edits'
controls=run.read(BASE/'host-controls.json');assert controls['exitCode']==0 and controls['testsRun']==20
app=run.read(BASE/'built-app-manifest.json');runner=run.read(BASE/'build-products-manifest.json');selection=run.read(BASE/'preparation-selection.json')
assert all(run.sha(ROOT/n)==d for n,d in selection['bindings'].items())
files=[]
for p in sorted(BASE.rglob('*')):
    parts=p.relative_to(BASE).parts
    if parts[0] in {'build','runtime','runtime-direct','__pycache__'} or '__pycache__' in parts:continue
    if p.is_file():assert not p.is_symlink();files.append(p)
files += [ROOT/'docs/apple-toggle-keyboard-focus-contract.md',ROOT/'docs/apple-toggle-keyboard-focus-qualification.md']+[ROOT/n for n in selection['bindings']]
value={'schema':'mixer.apple-toggle.keyboard-focus.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'sealed-preparation-awaiting-root-review-and-native-execution','candidateSourceClosureSHA256':run.read(BASE/'source-lock.json')['sourceClosureSHA256'],'candidateArchiveSHA256':app['archiveSHA256'],'testRunnerProductTreeSHA256':runner['productTreeSHA256'],'testRunnerArchiveSHA256':runner['productArchiveSHA256'],'sourceRevisionContext':selection['sourceRevisionContext'],'files':{str(p.relative_to(ROOT)):run.sha(p) for p in sorted(set(files))},'excludedMutableSubtrees':[str((BASE/'runtime').relative_to(ROOT))+'/',str((BASE/'runtime-direct').relative_to(ROOT))+'/'],'hostTestMethods':20,'expectedXCTestMethods':7,'dependentApplicationMethods':6,'caseScope':'Bothinitialvalues for enabled Space pair/forward-reverse neighbors, stale/resume gate, and disabled focus/traversal/silent value state. Acquisition atmost12realTabs percase.','selectedAdapters':'Reviewed stable observation reader/deadline subclass; closed same-endpoint keyboard witness and fixed existing command phases; exact owned xcresult attachment export before inherited cleanup on success/failure/timeout.','appOrCarrierChanged':False,'appRecompiled':False,'runnerCrossBuilt':True,'nativeExecuted':False,'nativeInstancesQueried':False,'physicalDevicesQueried':False,'nativeQualification':False,'productionAppleAdapterAcceptance':False,'gaAccepted':False,'limitations':'Preparation is not real keyboard/focus/Settings evidence. Root must review seal and run full7method suite. Settings failure leaves6appmethods skipped/unrun. Physicalkeyboard/VoiceOver, compositor/liveadapter/dogfood/store/operational/GA gates remain pending.'}
with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps({'sealSHA256':run.sha(path),'sealedFiles':len(value['files']),'nativeExecuted':False}))
