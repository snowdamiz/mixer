#!/usr/bin/env python3
"""Derived-only scheduling/report controls around real native/concrete SDK work."""
from pathlib import Path
import argparse,difflib,hashlib,json,os,re,subprocess,time
ROOT=Path(__file__).resolve().parents[2];PACKAGE=ROOT/'experimental-capability-runtime';OWN=ROOT/'verification/capability-bridge-lifecycle'
p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--freeze');p.add_argument('--modes',default='debug,release,tsan');a=p.parse_args();assert re.fullmatch('[a-z0-9-]{1,64}',a.name)
out=OWN/a.name;out.mkdir(exist_ok=False);scratch=ROOT/'.build/capability-bridge-lifecycle'/a.name;source=scratch/'source';source.mkdir(parents=True,exist_ok=False);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if a.freeze:
 receipt=json.loads((PACKAGE/'verification'/a.freeze/'receipt.json').read_text());base=Path(receipt['frozenSourceExport']);inputs=receipt['source'];stage=Path(receipt['stageRoot'])/'host'
else:
 base=ROOT;stage=PACKAGE/'build-verification/local/qualified-final-v3/host'
 paths=[PACKAGE/'Package.swift',Path(__file__),OWN/'Probe/Hooks.swift',OWN/'Probe/Tests.swift']
 for folder in [PACKAGE/'Sources',PACKAGE/'Tests',ROOT/'sdk']:
  paths.extend(v for v in folder.rglob('*') if v.is_file() and not {'.build','.git','.swiftpm','__pycache__'}.intersection(v.relative_to(folder).parts) and v.name!='.DS_Store')
 inputs={str(v.relative_to(ROOT)):sha(v) for v in sorted(set(paths))}
for name,digest in inputs.items():
 original=base/name;assert sha(original)==digest;target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original.read_bytes())
manifest=''.join(d+'  '+n+'\n' for n,d in sorted(inputs.items()));(out/'base-source-manifest.sha256').write_text(manifest);patch=[]
def edit(name,before,after):
 path=source/'experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime'/name;old=path.read_text();assert old.count(before)==1,(name,before);new=old.replace(before,after);path.write_text(new);patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='base/'+name,tofile='derived/'+name))
edit('Session.swift','                    lifecycle?.constructorReturned()','                    LifecycleProbeHooks.beforeConstructorTail()\n                    lifecycle?.constructorReturned()')
edit('Session.swift','            lifecycle?.expectsNative()','            LifecycleProbeHooks.afterCreate()\n            lifecycle?.expectsNative()')
edit('Lifecycle.swift','            if let storage { await storage.close() }','            await LifecycleProbeHooks.beforeStorageClose()\n            if let storage { await storage.close() }')
edit('Lifecycle.swift','return InstalledCapabilityAdapters(http: state.http, storage: state.storage)','return LifecycleProbeHooks.adapters(http: state.http, storage: state.storage)')
edit('Native.swift','        do {\n            try Self.check(status, report, operation: .construction','        LifecycleProbeHooks.createReport(&report)\n        do {\n            try Self.check(status, report, operation: .construction')
edit('Native.swift','                let cleanupStatus = mixer_vm_capability_session_close_v1','                LifecycleProbeHooks.nativeClose()\n                let cleanupStatus = mixer_vm_capability_session_close_v1')
edit('Native.swift','    func close() throws {\n        var report','    func close() throws {\n        LifecycleProbeHooks.nativeClose()\n        var report')
(out/'test-only.patch').write_text(''.join(patch))
for name,destination in [('Hooks.swift','Sources/MixerExperimentalCapabilityRuntime/LifecycleProbeHooks.swift'),('Tests.swift','Tests/MixerExperimentalCapabilityRuntimeTests/LifecycleProbeTests.swift')]:
 original=source/'verification/capability-bridge-lifecycle/Probe'/name;(source/'experimental-capability-runtime'/destination).write_bytes(original.read_bytes())
derived={str(v.relative_to(source)):sha(v) for v in sorted(source.rglob('*')) if v.is_file()};(out/'derived-source-manifest.sha256').write_text(''.join(d+'  '+n+'\n' for n,d in sorted(derived.items())))
record={'status':'running','scope':'Implementer derived-source controls, not unmodified public reproduction: real C create/drain and real concrete SDK storage; test-only holds after native create, after continuation publication/before constructor tail, before KV close, and SDK afterInvocation; malformed ABI injected after real create. No replacement adapter or trusted result setter.','baseFreeze':a.freeze,'baseSource':inputs,'baseManifestSHA256':hashlib.sha256(manifest.encode()).hexdigest(),'derivedSource':derived,'sourceExport':str(source),'driverSHA256':sha(Path(__file__)),'patchSHA256':sha(out/'test-only.patch'),'nativeArtifactSHA256':sha(stage/'lib/libmixer_vm_capability_experimental.a'),'commands':[],'limitations':['Local Swift6.3.3; pinned Xcode26.3 not installed','Each filtered probe is its own process; quarantine intentionally retains one consumed owner/permit','Held afterInvocation is scheduling control around real storage, not real hung device/network evidence','No runtime Task destruction, general OOM, activation/coordinator16, release or device qualification']}
def save():(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
save()
tests=['successfulHandoffCannotRetireBeforeConstructorTail','cancelledAfterActualNativeCreateKeepsGroupUntilNativeCleanup','concreteStorageCloseMustActuallyReturnBeforeUntransferredRetirement','wakeTerminalSignalPrecedesHungExitAndFinalRetirement','malformedCreateQuarantineClosesAdaptersWithoutRetirementOrCapacityRelease']
for mode in a.modes.split(','):
 extra={'debug':[],'release':['-c','release'],'tsan':['--sanitize','thread']}[mode]
 for test in tests:
  command=['swift','test','--package-path',str(source/'experimental-capability-runtime'),'--scratch-path',str(scratch/mode),'--filter',test]+extra+['-Xcc','-I'+str(stage/'include'),'-Xlinker','-L'+str(stage/'lib'),'-Xswiftc','-warnings-as-errors'];began=time.monotonic();result=subprocess.run(command,cwd=source,env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180);log=out/(mode+'-'+test+'.log');log.write_bytes(result.stdout);counts=[int(n) for n in re.findall(rb'Test run with (\d+) tests? in \d+ suites? passed',result.stdout)];record['commands'].append({'command':command,'cwd':str(source),'environment':{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},'exitCode':result.returncode,'elapsedSeconds':time.monotonic()-began,'passedTests':counts,'expectedTests':1,'log':log.name,'logSHA256':sha(log)});save();print(mode+' '+test+': '+str(result.returncode),flush=True)
record['baseUnchanged']=all(sha(base/name)==digest for name,digest in inputs.items());record['derivedUnchanged']=all(sha(source/name)==digest for name,digest in derived.items());record['status']='passed' if all(c['exitCode']==0 and c['passedTests']==[1] for c in record['commands']) and record['baseUnchanged'] and record['derivedUnchanged'] else 'failed_check_preserved';save();raise SystemExit(0 if record['status']=='passed' else 1)
