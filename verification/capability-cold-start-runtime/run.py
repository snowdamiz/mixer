#!/usr/bin/env python3
"""Exact baseline + additive coordinator; direct target-only build, no package graph."""
import argparse, datetime, difflib, hashlib, json, os, plistlib, re, subprocess, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVISION = 'f5d99d1ea1595c431d87c99d110eb2bd4acd5b4c'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def need(ok, message):
    if not ok: raise RuntimeError(message)
def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--name', required=True); parser.add_argument('--modes', default='debug,release,tsan'); parser.add_argument('--derived', action='store_true'); parser.add_argument('--all-tests', action='store_true'); args = parser.parse_args()
    need(re.fullmatch('[a-z0-9-]{1,64}', args.name), 'bounded name')
    out = HERE / args.name; out.mkdir(exist_ok=False)
    work = HERE / '.build' / args.name; source = work / 'source'; source.mkdir(parents=True, exist_ok=False)
    dependency = ROOT / 'verification/capability-recovery-transitions/2026-10-23-candidate-3/receipt.json'
    dep = json.loads(dependency.read_text()); depwork = Path(dep['export']).parent
    native = depwork / 'native'
    own = [str(p.relative_to(ROOT)) for p in sorted((ROOT/'capability-activation/Sources/MixerCapabilityActivation').glob('CapabilityColdStart*.swift'))]
    concrete = {'capability-activation/Sources/MixerCapabilityActivation/CapabilityConcreteAttempt.swift':'039e789a763cd99b2e6eb0295984ab44ac3d11d25def26b1ba48f294132cdbbc', 'capability-activation/Sources/MixerCapabilityActivation/CapabilityConcreteRetirement.swift':'e143c347eae335e2b6dd53abd56d0da24dc9729efa72e5a185b79abc2510b8cc'}
    own += list(concrete) + ['capability-activation/Tests/MixerCapabilityActivationTests/CapabilityColdStartRuntimeTests.swift', 'verification/capability-cold-start-runtime/Bundle.swift', 'verification/capability-cold-start-runtime/run.py']
    if args.all_tests:own+=['capability-activation/Tests/MixerCapabilityActivationTests/ConcreteAttemptTests.swift']
    if args.derived: own += ['verification/capability-cold-start-runtime/DerivedHooks.swift','verification/capability-cold-start-runtime/DerivedTests.swift']
    inputs = {}; changed_baseline = {}
    for name, oldhash in dep['source_files'].items():
        raw = subprocess.check_output(['git','show',REVISION+':'+name],cwd=ROOT)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != oldhash:
            need(name.startswith('capability-activation/'), 'retained dependency code must match '+name)
            changed_baseline[name] = {'retained_export_sha256':oldhash,'baseline_sha256':digest}
        path=source/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw); inputs[name]=digest
    for name in own:
        path=ROOT/name; need(name not in concrete or sha(path)==concrete[name], 'concrete freeze '+name)
        raw=path.read_bytes(); target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);inputs[name]=sha(path)
    manifest=''.join(d+'  '+n+'\n' for n,d in sorted(inputs.items()));(out/'source-manifest.sha256').write_text(manifest)
    originals = dict(inputs)
    if args.derived:
        changes = {
            'capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartWorker.swift': [
                ('_ = try await attempt.startup() // Effects remain disabled.', 'do { _ = try await attempt.startup() } catch { await ColdStartDerivedHooks.startupFailure.hold(); throw error } // Captured-source gate after real checked startup failure.'),
                ('    func closeStore() async -> CapabilityRecoverySnapshot {', '    func derivedInvoke(_ name: String) async throws -> MixerExperimentalCapabilityRuntime.ExperimentalCapabilityInvocation {\n        let attempt = try control.concreteForMethod()\n        return try await attempt.invoke(name)\n    }\n    func closeStore() async -> CapabilityRecoverySnapshot {'),
                ('import Foundation','import Foundation\nimport MixerExperimentalCapabilityRuntime')],
            'capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartRuntime.swift': [
                ('    public func recoverySnapshot() async -> CapabilityColdStartRecoverySnapshot {', '    func derivedInvoke(_ name: String) async throws -> MixerExperimentalCapabilityRuntime.ExperimentalCapabilityInvocation {\n        let op = try core.control.admit(.milestone)\n        do {\n            let value = try await core.worker.derivedInvoke(name)\n            await ColdStartDerivedHooks.ordinaryTail.hold()\n            core.control.finish(op); return value\n        } catch { core.control.finish(op); throw error }\n    }\n    public func recoverySnapshot() async -> CapabilityColdStartRecoverySnapshot {'),
                ('import Foundation','import Foundation\nimport MixerExperimentalCapabilityRuntime')],
            'capability-activation/Sources/MixerCapabilityActivation/CapabilityConcreteRetirement.swift': [
                ('func recordRetired() { locked { $0.bridgeRetired = true }; completeIfReady() }','func recordRetired() { ColdStartDerivedHooks.adapterRetirement.hold(); locked { $0.bridgeRetired = true }; completeIfReady() }')]
        }
        patches=[]
        for name,replacements in changes.items():
            path=source/name; before=path.read_text();after=before
            for old,new in replacements:
                need(after.count(old)==1,'unique derived anchor '+old);after=after.replace(old,new)
            patches += list(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='original/'+name,tofile='derived/'+name))
            path.write_text(after);inputs[name]=sha(path)
        (out/'test-only.patch').write_text(''.join(patches))
        (out/'derived-source-manifest.sha256').write_text(''.join(d+'  '+n+'\n' for n,d in sorted(inputs.items())))
    receipt={'status':'running','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline_revision':REVISION,'source_files':inputs,'source_manifest_sha256':hashlib.sha256(manifest.encode()).hexdigest(),'export':str(source),'dependency_receipt':{'path':str(dependency),'sha256':sha(dependency)},'rebuilt_activation_baseline_changes':changed_baseline,'own_files':own,'commands':[],'artifacts':{},'retained_products':{},'native_directory':str(native),'native_files':dep['native_files'],'scope':'Experimental public cold-start coordinator and private composed lifecycle; exact committed Store/Signals baseline plus frozen concrete attempt; target-only builds with retained dependency objects and one experimental Rust archive. No package graph or native rebuild.','limitations':['Native milestones in tests are trusted embedding reports, not actual UI/FieldLog health evidence','Public guest UI event delivery and post-enable export ingress remain separate; no public invoke API','Swift TSan excludes uninstrumented Rust and system frameworks','Logical input/frame/owner joins do not prove runtime Task destruction or allocator/RSS bound','Local installed Xcode toolchain does not qualify pinned hosted Xcode or physical devices','No deployment, publication, activation widening or GA claim']}
    if args.derived:receipt.update(derived_only=True,original_source_files=originals,derived_manifest_sha256=sha(out/'derived-source-manifest.sha256'),test_only_patch_sha256=sha(out/'test-only.patch'),scope='DERIVED ONLY: real startup error/ordinary-tail scheduling gates and internal export driver added only to captured sources. Native VM, signed verification, private store and concrete KV unchanged. No unmodified public post-enable I/O reproduction claim.')
    def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def unchanged():
        for name,digest in inputs.items():
            need(sha(source/name)==digest,'export '+name)
            if name in own:need(sha(ROOT/name)==originals[name],'live owned '+name)
        for name,digest in dep['native_files'].items():need(sha(native/name)==digest,'native '+name)
    def run(label,cmd,env=None,count=None,timeout=180):
        unchanged(); began=time.monotonic(); environment=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'}|(env or {})
        try:r=subprocess.run(cmd,cwd=source,env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);raw,code=r.stdout,r.returncode
        except subprocess.TimeoutExpired as e:raw,code=(e.stdout or b'')+b'\nqualification timeout\n',124
        log=out/(label+'.log');log.write_bytes(raw);row={'name':label,'command':cmd,'cwd':str(source),'environment':{k:environment[k] for k in ['DEVELOPER_DIR']+list((env or {}).keys())},'exit_code':code,'seconds':time.monotonic()-began,'log':log.name,'log_sha256':sha(log)}
        if count is not None:row.update(expected_tests=count,observed_test_counts=[int(n) for n in re.findall(rb'Executed (\d+) tests?, with 0 failures',raw)])
        receipt['commands'].append(row);save();print(label,code,flush=True)
        need(code==0,label+' failed (preserved log)');need(b'WARNING: ThreadSanitizer' not in raw,'TSan warning')
        if count is not None:need(row['observed_test_counts'] and row['observed_test_counts'][-1]==count,'XCTest count')
        unchanged()
    unchanged();save();print('FROZEN',receipt['source_manifest_sha256'],flush=True)
    try:
        run('swift-version',['swift','--version']);run('xcode-version',['xcodebuild','-version'])
        frameworks=Path('/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/Library/Frameworks'); overlays=frameworks.parents[1]/'usr/lib'
        sources=sorted(str(p) for p in (source/'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))
        if args.derived:sources+=[str(source/'verification/capability-cold-start-runtime/DerivedHooks.swift')]
        objects=['Crypto','MixerCapabilities','MixerCore','MixerExperimentalCapabilityRuntime','MixerRuntimeIdentity','MixerUpdates','CMixerVMCapability','MixerCapabilityDurableIO','MixerCapabilityIO','MixerDurableIO']
        for mode in args.modes.split(','):
            retained=Path(dep['retained_products'][mode]['directory']);products=retained/'products';maps=retained/'modulemaps'
            receipt['retained_products'][mode]={'directory':str(retained),'objects':{n+'.o':sha(products/(n+'.o')) for n in objects}}
            target=work/mode;current=target/'products';current.mkdir(parents=True)
            flags=['swiftc','-parse-as-library','-swift-version','6','-warnings-as-errors','-I',str(products),'-F',str(frameworks)]
            for name in ['CMixerVMCapability','MixerCapabilityDurableIO','MixerCapabilityIO','MixerDurableIO']:flags+=['-Xcc','-fmodule-map-file='+str(maps/(name+'.modulemap'))]
            flags+=['-Xcc','-I'+str(native/'include')]
            if mode=='release':flags+=['-O']
            if mode=='tsan':flags+=['-sanitize=thread']
            dylib=current/'libMixerCapabilityActivationColdStart.dylib'
            run(mode+'-module',flags+['-emit-library','-emit-module','-enable-testing','-module-name','MixerCapabilityActivation','-emit-module-path',str(current/'MixerCapabilityActivation.swiftmodule')]+sources+[str(products/(n+'.o')) for n in objects]+['-L',str(native/'lib'),'-lmixer_vm_capability_experimental','-Xlinker','-install_name','-Xlinker','@rpath/'+dylib.name,'-o',str(dylib)])
            receipt['artifacts'][mode]={'module':{'path':str(dylib),'sha256':sha(dylib)},'swiftmodule':{'path':str(current/'MixerCapabilityActivation.swiftmodule'),'sha256':sha(current/'MixerCapabilityActivation.swiftmodule')}};save();print('MODULE_READY',mode,str(current),flush=True)
            run(mode+'-native-symbols',['nm','-gU',str(dylib)])
            defined=(out/(mode+'-native-symbols.log')).read_text();need(len(re.findall(r'\b_mixer_vm_capability_session_enable_v1$',defined,re.M))==1,'one native registry')
            bundle=target/'ColdStartTests.xctest';binary=bundle/'Contents/MacOS/ColdStartTests';binary.parent.mkdir(parents=True)
            (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'ColdStartTests','CFBundleIdentifier':'org.mixer.tests.cold-start','CFBundlePackageType':'BNDL','CFBundleVersion':'1'}))
            tests=[str(source/'capability-activation/Tests/MixerCapabilityActivationTests/CapabilityColdStartRuntimeTests.swift'),str(source/'verification/capability-cold-start-runtime/Bundle.swift')]
            if args.all_tests:tests=sorted(str(p) for p in (source/'capability-activation/Tests/MixerCapabilityActivationTests').glob('*.swift'))+[str(source/'verification/capability-cold-start-runtime/Bundle.swift')]
            if args.derived:tests+=[str(source/'verification/capability-cold-start-runtime/DerivedTests.swift')]
            run(mode+'-test-link',flags[:1]+['-I',str(current),'-I',str(overlays)]+flags[1:]+['-emit-library','-module-name','MixerColdStartTests']+tests+['-L',str(current),'-lMixerCapabilityActivationColdStart','-L',str(overlays),'-Xlinker','-rpath','-Xlinker',str(current),'-Xlinker','-rpath','-Xlinker',str(frameworks),'-Xlinker','-rpath','-Xlinker',str(overlays),'-o',str(binary)])
            env={'MIXER_COLD_START_TEST_BUNDLE':str(products/'MixerCapabilityActivation_MixerCapabilityActivationTests.bundle')}
            if mode=='tsan':
                resource=subprocess.check_output(['clang','-print-resource-dir'],text=True).strip();env['DYLD_INSERT_LIBRARIES']=str(Path(resource)/'lib/darwin/libclang_rt.tsan_osx_dynamic.dylib')
            expected=(95 if args.all_tests else 8)+(5 if args.derived else 0)
            xctest=subprocess.check_output(['xcrun','--find','xctest'],text=True).strip();run(mode+'-tests',[xctest,str(bundle)],env=env,count=expected,timeout=180)
            run(mode+'-test-native-symbols',['nm','-gU',str(binary)]);need(re.search(r'\b_mixer_vm_\w+$',(out/(mode+'-test-native-symbols.log')).read_text(),re.M) is None,'test bundle has no second registry')
            receipt['artifacts'][mode]['tests']={'path':str(binary),'sha256':sha(binary)};save()
            for name,digest in receipt['retained_products'][mode]['objects'].items():need(sha(products/name)==digest,'retained object unchanged')
        receipt.update(status='scoped tests passed; independent review pending',completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_unchanged=True)
    except Exception as e:receipt.update(status='failed check preserved',problem=str(e));save();raise
    save();print('RECEIPT',sha(out/'receipt.json'),flush=True)
if __name__=='__main__':main()
