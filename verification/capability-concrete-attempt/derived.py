#!/usr/bin/env python3
"""Fixed derived-only setup/method tails and partial KV initialization probes."""
import difflib,hashlib,json,os,re,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise RuntimeError(message)
def main():
    base_path=HERE/'2026-10-23-candidate-4/receipt.json';base=json.loads(base_path.read_text());original=Path(base['export']);old_work=original.parent
    out=HERE/'2026-10-23-derived-1';out.mkdir(exist_ok=False)
    work=ROOT/'capability-activation/.build/concrete-derived-1';source=work/'source';source.mkdir(parents=True,exist_ok=False)
    for name,digest in base['source_files'].items():
        require(sha(original/name)==digest,'exact immutable base '+name);p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((original/name).read_bytes())
    own={n:sha(HERE/n) for n in ['DerivedHooks.swift','DerivedTests.swift','derived.py']}
    for name in own:
        p=source/'verification/capability-concrete-attempt'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((HERE/name).read_bytes())
    prefix=source/'capability-activation/Sources/MixerCapabilityActivation';patch=[];edits=[]
    def edit(name,before,after):
        p=prefix/name;old=p.read_text();require(old.count(before)==1,'unique derived anchor '+name);new=old.replace(before,after);p.write_text(new);edits.append([name,before,after]);patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='base/'+name,tofile='derived/'+name))
    edit('CapabilityConcreteAttempt.swift','            guard control.installSession(session) else { session.close(); throw concreteAttemptError("stopped") }\n            try control.requireOpen(deadline: true)','            guard control.installSession(session) else { session.close(); throw concreteAttemptError("stopped") }\n            try control.requireOpen(deadline: true)\n            await ConcreteProbeHooks.afterSetupSession()')
    edit('CapabilityConcreteAttempt.swift','        let result = try await session.startup()\n        try c.requireOpen','        let result = try await session.startup()\n        await ConcreteProbeHooks.afterStartup()\n        try c.requireOpen')
    edit('CapabilityConcreteAttempt.swift','                    namespaces: policy.namespaces, maximumTotalBytes: policy.maximumTotalBytes, maximumEntries: policy.maximumEntries)\n            }\n            try control.requireOpen(deadline: true)','                    namespaces: policy.namespaces, maximumTotalBytes: policy.maximumTotalBytes, maximumEntries: policy.maximumEntries)\n            }\n            try ConcreteProbeHooks.afterStorage()\n            try control.requireOpen(deadline: true)')
    edit('CapabilityConcreteRetirement.swift','    func recordRetired() { locked { $0.bridgeRetired = true }; completeIfReady() }','    func recordRetired() { ConcreteProbeHooks.bridgeRetired(); locked { $0.bridgeRetired = true }; completeIfReady() }')
    edit('CapabilityConcreteRetirement.swift','                    s.waiter = continuation; return nil','                    s.waiter = continuation; ConcreteProbeHooks.waiterInstalled(); return nil')
    (prefix/'ConcreteProbeHooks.swift').write_bytes((HERE/'DerivedHooks.swift').read_bytes())
    test=source/'capability-activation/Tests/MixerCapabilityActivationTests/ConcreteAttemptTests.swift'
    test.write_bytes(test.read_bytes()+b'\n'+(HERE/'DerivedTests.swift').read_bytes())
    (out/'test-only.patch').write_text(''.join(patch))
    derived={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    (out/'derived-source-manifest.sha256').write_text(''.join(d+'  '+n+'\n' for n,d in sorted(derived.items())))
    receipt=dict(status='running',base_receipt=dict(path=str(base_path.relative_to(ROOT)),sha256=sha(base_path)),base_source_manifest_sha256=base['source_manifest_sha256'],base_source=base['source_files'],base_export=str(original),
        derived_source=derived,export=str(source),fixed_edits=edits,patch_sha256=sha(out/'test-only.patch'),own_inputs=own,commands=[],artifacts={},
        scope='Derived-only fixed async frame barriers and failure after real returned KV init, actual C native creation/retirement, one counted cancellation-aware waiter; no fabricated bridge exit/ack or arbitrary service.',
        limitations=['Derived controls are not public reproductions','Each selected case runs in an isolated subprocess','No package/dependency/Rust graph rebuilt','OldSignals/immutable transition candidate2 dependency; coordinator composition is separately qualified','Logical frame gates do not prove runtime Task/allocator or OS destruction','No devices, signed execution authority, health, production, publication or GA qualification'])
    def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def unchanged():
        for name,digest in base['source_files'].items():require(sha(original/name)==digest,'base unchanged')
        for name,digest in derived.items():require(sha(source/name)==digest,'derived unchanged')
        for name,digest in own.items():require(sha(HERE/name)==digest,'original controls unchanged')
    def run(name,command,env=None,count=None):
        unchanged();began=time.monotonic();environment=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'}|(env or {})
        try:r=subprocess.run(command,cwd=source,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120);raw,code=r.stdout,r.returncode
        except subprocess.TimeoutExpired as error:raw,code=(error.stdout or b'')+b'\nderived probe timeout\n',124
        log=out/(name+'.log');log.write_bytes(raw);row=dict(name=name,command=command,cwd=str(source),environment={'DEVELOPER_DIR':environment['DEVELOPER_DIR']}|(env or {}),exit_code=code,seconds=time.monotonic()-began,log=log.name,log_sha256=sha(log))
        if count is not None:row.update(expected_tests=count,observed_test_counts=[int(n) for n in re.findall(rb'Executed (\d+) tests?, with 0 failures',raw)])
        receipt['commands'].append(row);save();require(code==0,name+' exit '+str(code))
        if count is not None:require(row['observed_test_counts'] and row['observed_test_counts'][-1]==count,'actual selected test count')
        require(b'WARNING: ThreadSanitizer' not in raw,'no TSan warning');unchanged();print(name+': '+str(code),flush=True)
    def command(name):return [arg.replace(str(old_work),str(work)) for arg in next(c for c in base['commands'] if c['name']==name)['command']]
    save()
    try:
        tests=['testDerivedSetupTailPinsAfterActualBridgeRetirementAndWaitCancellation','testDerivedMethodFramePinsAfterActualBridgeRetirement','testDerivedFailureAfterReturnedKVInitClosesInlineWithoutBridge']
        xctest=subprocess.check_output(['xcrun','--find','xctest'],env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},text=True).strip()
        for mode in ['debug','release','tsan']:
            (work/mode/'products').mkdir(parents=True)
            module=command(mode+'-module');run(mode+'-module',module+[str(prefix/'ConcreteProbeHooks.swift')])
            bundle=work/mode/'MixerConcreteTests.xctest';(bundle/'Contents/MacOS').mkdir(parents=True)
            (bundle/'Contents/Info.plist').write_bytes((old_work/mode/'MixerConcreteTests.xctest/Contents/Info.plist').read_bytes())
            run(mode+'-tests-link',command(mode+'-tests-link'))
            env=next(c for c in base['commands'] if c['name']==mode+'-tests')['environment'];env={k:v for k,v in env.items() if k!='DEVELOPER_DIR'}
            for testname in tests:run(mode+'-'+testname,[xctest,'-XCTest','MixerConcreteAttemptTests.ConcreteAttemptTests/'+testname,str(bundle)],env=env,count=1)
            dylib=work/mode/'products/libMixerCapabilityActivationConcrete.dylib';executable=bundle/'Contents/MacOS/MixerConcreteTests'
            run(mode+'-native-symbols',['nm','-gU',str(dylib)]);run(mode+'-test-native-symbols',['nm','-gU',str(executable)])
            require(len(re.findall(r'\b_mixer_vm_capability_session_enable_v1$',(out/(mode+'-native-symbols.log')).read_text(),re.M))==1,'single native registry definition')
            require(re.search(r'\b_mixer_vm_\w+$',(out/(mode+'-test-native-symbols.log')).read_text(),re.M) is None,'test bundle has no second native archive')
            receipt['artifacts'][mode]=dict(module=dict(path=str(dylib),sha256=sha(dylib)),test=dict(path=str(executable),sha256=sha(executable)));save()
        unchanged();receipt.update(status='passed',base_unchanged=True,derived_unchanged=True)
    except Exception as error:receipt.update(status='failed check preserved',problem=str(error));save();raise
    save();print('receipt_sha256 '+sha(out/'receipt.json'))
if __name__=='__main__':main()
