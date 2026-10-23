#!/usr/bin/env python3
"""Implementer derived-source ownership probes; not an unmodified public reproduction."""
from pathlib import Path
import argparse, difflib, hashlib, json, os, re, subprocess, time
ROOT=Path(__file__).resolve().parents[2];PACKAGE=ROOT/'experimental-capability-runtime'
p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--freeze');p.add_argument('--modes',default='debug,release,tsan');p.add_argument('--filter',default='ValidationOwnerProbeTests');a=p.parse_args()
assert re.fullmatch(r'[a-z0-9-]{1,64}',a.name)
out=PACKAGE/'verification'/a.name;out.mkdir(exist_ok=False)
scratch=PACKAGE/'.build'/a.name;source=scratch/'source';source.mkdir(parents=True,exist_ok=False)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
if a.freeze:
 owner_path=PACKAGE/'verification'/a.freeze/'receipt.json';owner=json.loads(owner_path.read_text());base=Path(owner['frozenSourceExport']);inputs=owner['source'];stage=Path(owner['stageRoot'])/'host'
else:
 base=ROOT;stage=PACKAGE/'build-verification/local/qualified-final-v3/host'
 paths=[PACKAGE/'Package.swift',PACKAGE/'README.md',PACKAGE/'verification/verify.py',PACKAGE/'verification/with-loopback.py',Path(__file__),ROOT/'docs/experimental-capability-validation-api-design.md']
 for folder in [PACKAGE/'Sources',PACKAGE/'Tests',PACKAGE/'verification/ValidationProbe',ROOT/'sdk']:
  paths.extend(v for v in folder.rglob('*') if v.is_file() and not {'.build','.git','.swiftpm','__pycache__'}.intersection(v.relative_to(folder).parts) and v.name!='.DS_Store')
 inputs={str(v.relative_to(ROOT)):sha(v) for v in sorted(set(paths))}
for name,digest in inputs.items():
 origin=base/name;assert sha(origin)==digest
 target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(origin.read_bytes())
manifest=''.join(d+'  '+n+'\n' for n,d in sorted(inputs.items()));(out/'base-source-manifest.sha256').write_text(manifest)
validation=source/'experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Validation.swift';original=validation.read_text();anchor='        do {\n            try NativeDiagnostics.check'
assert original.count(anchor)==1
changed=original.replace(anchor,'        ValidationProbeHooks.afterReturn(&report)\n'+anchor);validation.write_text(changed)
(out/'test-only.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='base/Validation.swift',tofile='derived/Validation.swift')))
for name,destination in [('ProbeHooks.swift','Sources/MixerExperimentalCapabilityRuntime'),('ProbeTests.swift','Tests/MixerExperimentalCapabilityRuntimeTests')]:
 origin=source/'experimental-capability-runtime/verification/ValidationProbe'/name;target=source/'experimental-capability-runtime'/destination/name;target.write_bytes(origin.read_bytes())
derived={str(v.relative_to(source)):sha(v) for v in sorted(source.rglob('*')) if v.is_file()}
(out/'derived-source-manifest.sha256').write_text(''.join(d+'  '+n+'\n' for n,d in sorted(derived.items())))
record={'status':'running','scope':'Implementer derived-copy controls after actual C validate returns, before checked report publication. Malformed ABI is injected, not produced by C. Held C-frame test proves cleanup/cancellation ordering, not interruptibility or unmodified scheduling reproduction.','baseFreeze':a.freeze,'baseSource':inputs,'baseManifestSHA256':hashlib.sha256(manifest.encode()).hexdigest(),'derivedSource':derived,'sourceExport':str(source),'driverSHA256':sha(Path(__file__)),'testOnlyPatchSHA256':sha(out/'test-only.patch'),'commands':[],'nativeArtifact':{'path':str(stage/'lib/libmixer_vm_capability_experimental.a'),'sha256':sha(stage/'lib/libmixer_vm_capability_experimental.a')},'limitations':['Local Xcode27.1/Swift6.3.3; pinnedCI Xcode26.3 not installed','Derived-only post-C controls; no production hooks, no C interrupt/latency, no devices/release/activation qualification','Quarantine test runs in its own process and intentionally exhausts both validation permits']}
def save(): (out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
save()
for mode in a.modes.split(','):
 flags={'debug':[],'release':['-c','release'],'tsan':['--sanitize','thread']}[mode]
 # Fault tests exhaust process capacity, so each test is a separate filtered process.
 filters=['malformedRealValidationReturnQuarantinesEvenAfterOperationDeinit','cancellationAtRealCReturnHoldsCapacityUntilWorkerFrameReturns','rejectedCancelledSecondCallerCannotCancelFirstValidation'] if a.filter=='ValidationOwnerProbeTests' else [a.filter]
 for name in filters:
  command=['swift','test','--package-path',str(source/'experimental-capability-runtime'),'--scratch-path',str(scratch/mode),'--filter',name]+flags+['-Xcc','-I'+str(stage/'include'),'-Xlinker','-L'+str(stage/'lib'),'-Xswiftc','-warnings-as-errors']
  began=time.monotonic();result=subprocess.run(command,cwd=source,env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
  log=out/(mode+'-'+name+'.log');log.write_bytes(result.stdout);counts=[int(n) for n in re.findall(rb'Test run with (\d+) tests? in \d+ suites? passed',result.stdout)]
  record['commands'].append({'command':command,'cwd':str(source),'environment':{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},'exitCode':result.returncode,'passedTests':counts,'expectedTests':1,'elapsedSeconds':time.monotonic()-began,'log':log.name,'logSHA256':sha(log)});print(mode+' '+name+': '+str(result.returncode),flush=True);save()
record['baseUnchanged']=all(sha(base/name)==digest for name,digest in inputs.items());record['derivedUnchanged']=all(sha(source/name)==digest for name,digest in derived.items());record['status']='passed' if all(n['exitCode']==0 and n['passedTests']==[1] for n in record['commands']) and record['baseUnchanged'] and record['derivedUnchanged'] else 'failed_check_preserved';save();raise SystemExit(0 if record['status']=='passed' else 1)
