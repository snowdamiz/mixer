"""Separate v2 seal; original81sealed bytes and all app/runner bytes stay unchanged."""
import datetime
import json
import pathlib
import run
BASE,ROOT=run.BASE,run.ROOT;path=BASE/'packet-seal.json';assert not path.exists(),'Preserve a rejected seal before edits'
controls=run.read(BASE/'host-controls.json');assert controls['exitCode']==0 and controls['testsRun']==29
reuse=run.read(BASE/'immutable-reuse.json');assert all(run.sha(ROOT/n)==d for n,d in reuse['previousBindings'].items())
files=[]
for p in sorted(BASE.rglob('*')):
    parts=p.relative_to(BASE).parts
    if parts[0] in {'build','runtime','runtime-direct','__pycache__'} or '__pycache__' in parts:continue
    if p.is_file():assert not p.is_symlink();files.append(p)
files += [ROOT/'docs/apple-toggle-keyboard-focus-v2-qualification.md',ROOT/'verification/apple-toggle-keyboard-focus/packet-seal.json',ROOT/'verification/apple-toggle-keyboard-focus-root-review/v2-repair-selection.json']
value={'schema':'mixer.apple-toggle.keyboard-focus-v2.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'sealed-v2-host-repair-awaiting-root-review-and-native-selection','candidateSourceClosureSHA256':reuse['sourceClosureSHA256'],'candidateArchiveSHA256':reuse['appArchiveSHA256'],'testRunnerProductTreeSHA256':reuse['runnerProductTreeSHA256'],'testRunnerArchiveSHA256':reuse['runnerArchiveSHA256'],'files':{str(p.relative_to(ROOT)):run.sha(p) for p in sorted(set(files))},'excludedMutableSubtrees':[str((BASE/'runtime').relative_to(ROOT))+'/',str((BASE/'runtime-direct').relative_to(ROOT))+'/'],'prior81SealedFilesPreserved':True,'hostTestMethods':29,'pairedFocusRequirement':'Each paired application focused state equals authored AX.hasFocus. Disagreement is failing evidence pending native analysis; no platform equivalence assumed.','nativeMetadataRequirement':'Authored AX label equals corresponding app label; all3fixed IDs/labels stable before/after and between keys/commands.','focusFreshnessRequirement':'If app focus changes, a new native focus event matching finalapp focus and changed capture are required; missing signal fails.','acquisitionScope':'Every Tab changes to an observed fixed element within12steps; strict3element scope, never general-system navigation.','unchangedRuntime':'Reuse exact public7method runner, Settings gate, closed witnesses/commands, stable reader, fixed artifact exporter, root-owned instance lifecycle and independent cleanup.','appOrCarrierChanged':False,'appOrRunnerRecompiled':False,'nativeExecuted':False,'nativeInstancesQueried':False,'physicalDevicesQueried':False,'nativeQualification':False,'productionAppleAdapterAcceptance':False,'gaAccepted':False}
with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps({'sealSHA256':run.sha(path),'sealedFiles':len(value['files']),'nativeExecuted':False}))
