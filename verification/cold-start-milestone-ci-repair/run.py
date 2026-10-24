#!/usr/bin/env python3
"""Freeze/rebuild host source and force legal real-notification overlap schedules."""
import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tarfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CRYPTO = ROOT / 'verification/local/runtime-embedding-2026-10-22/ios/checkouts/swift-crypto'
CRYPTO_REVISION = 'c2cbadd7263439d8015189668f96ff5b5be565ce'
TEST = 'capability-activation/Tests/MixerCapabilityActivationTests/CapabilityColdStartRuntimeTests.swift'
PREFIX = 'capability-activation/Sources/MixerCapabilityActivation/'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
digest = lambda v: hashlib.sha256(json.dumps(v, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
parser.add_argument('--source-archive', type=Path)
parser.add_argument('--modes', nargs='+', choices=['debug', 'release', 'tsan'], default=['debug', 'release', 'tsan'])
args = parser.parse_args()
assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
out = HERE / args.name; out.mkdir(exist_ok=False)
work = HERE / '.build' / args.name; work.mkdir(parents=True, exist_ok=False)
source = work / 'source'; source.mkdir()
env = dict(os.environ, DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer', CLANG_MODULE_CACHE_PATH=str(work / 'clang-cache'))
receipt = {'schema': 1, 'started_utc': datetime.now(timezone.utc).isoformat(), 'driver_sha256': sha(Path(__file__)),
           'commands': [], 'artifacts': {}, 'source': str(source), 'status': 'running',
           'scope': 'Headless macOS XCTest only. Full current eight-test fixture and immutable derived hooks around real notification admission; no fabricated busy error, milestone acceptance, timer firing, or health.',
           'limitations': ['Hosted log proves the actual busy guard failed but does not identify the exact hosted interleaving. Controlled schedules prove an allowed overlap.',
                          'TSan instruments the rebuilt Swift/C host closure and tests, not the Rust archive or Apple system frameworks.',
                          'No native UI, simulator, emulator, device, published consumer, distribution signing, store, customer, operational or GA acceptance. Native checks remain pending under the user pause.']}
def save(): (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
def run(name, argv, expected=0, extra=None, cwd=source, timeout=240):
    argv = [str(a) for a in argv]; started = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=cwd, env=env | (extra or {}), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        data, code = p.stdout, p.returncode
    except subprocess.TimeoutExpired as e: data, code = (e.stdout or b'') + b'\nTIMEOUT\n', 124
    log = out / (name + '.log'); log.write_bytes(data)
    receipt['commands'].append({'name': name, 'argv': argv, 'cwd': str(cwd), 'environment': {k: env[k] for k in ['DEVELOPER_DIR', 'CLANG_MODULE_CACHE_PATH']} | (extra or {}), 'seconds': time.monotonic()-started, 'exit': code, 'expected_exit': expected, 'log': str(log.relative_to(ROOT)), 'sha256': sha(log)})
    save(); print(name, code, flush=True)
    assert code == expected, name
    assert b'WARNING: ThreadSanitizer' not in data, name
    return data.decode(errors='replace').strip()
files = {}; origins = {}
def freeze(relative, data, origin):
    path = source / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data); path.chmod(0o444)
    files[relative] = sha(path); origins[relative] = origin
    return path

def derive(relative, original, changed):
    path = freeze('derived/' + relative, changed.encode(), 'verification-only derived source')
    freeze('derived/' + relative + '.diff', ''.join(difflib.unified_diff(original.splitlines(keepends=True), changed.splitlines(keepends=True), fromfile='frozen/' + relative, tofile='derived/' + relative)).encode(), 'exact derivation diff')
    return path

def replace_once(text, needle, replacement):
    assert text.count(needle) == 1, needle
    return text.replace(needle, replacement)

try:
    receipt['source_revision'] = run('source-revision', ['git', 'rev-parse', 'HEAD'], cwd=ROOT)
    run('source-status', ['git', 'status', '--porcelain=v1'], cwd=ROOT)
    for name, argv in [('swift-version',['xcrun','swiftc','--version']), ('clang-version',['xcrun','clang','--version']), ('xcode-version',['xcodebuild','-version']), ('platform',['sw_vers']), ('python-version',['python3','--version']), ('rust-version',['/opt/homebrew/opt/rustup/bin/rustc','-Vv']), ('cargo-version',['/opt/homebrew/opt/rustup/bin/cargo','-V'])]: run(name,argv)
    sdk = run('sdk-path',['xcrun','--sdk','macosx','--show-sdk-path'])
    xctest = run('xctest-path',['xcrun','--find','xctest'])
    tsan = Path(run('clang-resource',['xcrun','clang','-print-resource-dir'])) / 'lib/darwin/libclang_rt.tsan_osx_dynamic.dylib'
    tool_paths = [Path(run(name + '-path',['xcrun','--find',name])) for name in ['swiftc','clang']]
    receipt['tools'] = {str(p):sha(p) for p in tool_paths + [Path(xctest),tsan,Path('/opt/homebrew/opt/rustup/bin/cargo'),Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo'),Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')]}
    receipt['modes'] = args.modes
    if args.source_archive:
        with tarfile.open(args.source_archive) as archive:
            for member in archive.getmembers():
                assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
                freeze(member.name, archive.extractfile(member).read(), 'replay archive ' + sha(args.source_archive))
        saved = json.loads((source / 'source-metadata.json').read_text())
        receipt['native_source_revision'] = saved['native_source_revision']; receipt['crypto_revision'] = saved['crypto_revision']
    else:
        receipt['crypto_revision'] = run('crypto-revision',['git','-C',CRYPTO,'rev-parse','HEAD'])
        assert receipt['crypto_revision'] == CRYPTO_REVISION
        assert not run('crypto-status',['git','-C',CRYPTO,'status','--porcelain=v1'])
        for folder in ['sdk/Sources','updates/Sources','runtime-identity/Sources','experimental-capability-runtime/Sources','capability-activation/Sources','capability-activation/Tests/MixerCapabilityActivationTests/Fixtures']:
            for p in sorted((ROOT / folder).rglob('*')):
                if p.is_file(): freeze(str(p.relative_to(ROOT)),p.read_bytes(),str(p))
        for relative in [TEST,'THIRD_PARTY.yml','sdk/Package.swift','updates/Package.swift','runtime-identity/Package.swift','experimental-capability-runtime/Package.swift','capability-activation/Package.swift']:
            freeze(relative,(ROOT/relative).read_bytes(),str(ROOT/relative))
        for p in sorted((CRYPTO/'Sources/Crypto').rglob('*')):
            if p.is_file(): freeze('dependencies/swift-crypto/'+str(p.relative_to(CRYPTO)),p.read_bytes(),str(p))
        for name in ['Package.swift','LICENSE.txt','NOTICE.txt']:
            if (CRYPTO/name).is_file(): freeze('dependencies/swift-crypto/'+name,(CRYPTO/name).read_bytes(),str(CRYPTO/name))
        revision = receipt['source_revision']; receipt['native_source_revision'] = revision
        paths = subprocess.check_output(['git','ls-tree','-r','--name-only',revision,'--','vm'],cwd=ROOT,text=True).splitlines()
        for relative in paths:
            freeze(relative,subprocess.check_output(['git','show',revision+':'+relative],cwd=ROOT),'git '+revision+':'+relative)
        original = subprocess.check_output(['git','show','6bee9510ac31456464c1e3a20024fc93dddc5fa7:'+TEST],cwd=ROOT)
        freeze('original-test.swift.txt',original,'git 6bee9510ac31456464c1e3a20024fc93dddc5fa7:'+TEST)
        for name in ['MilestoneProbe.swift','TestSupport.swift','run.py']:
            freeze('support/'+name,(HERE/name).read_bytes(),str(HERE/name))
        freeze('source-metadata.json',json.dumps({'native_source_revision':revision,'crypto_revision':receipt['crypto_revision']},sort_keys=True).encode(),'source metadata')
    # Retain a compact source-only replay archive, never build trees/binaries.
    with tarfile.open(out/'source.tar.gz','w:gz') as archive:
        for relative in sorted(files): archive.add(source/relative,arcname=relative,recursive=False)
    receipt['source_archive'] = {'path':str((out/'source.tar.gz').relative_to(ROOT)),'sha256':sha(out/'source.tar.gz')}
    receipt['input_files'] = dict(files); receipt['input_tree_sha256'] = digest(files)
    (out/'source-manifest.json').write_text(json.dumps({'files':files,'origins':origins,'sha256':digest(files)},indent=2)+'\n')
    receipt['source_manifest_sha256'] = sha(out/'source-manifest.json')
    runtime_files = sorted((source/PREFIX).glob('*.swift'))
    worker = source/PREFIX/'CapabilityColdStartWorker.swift'; original = worker.read_text()
    changed = replace_once(original,'        defer { control.finishNotification() }','        defer { control.finishNotification() }\n        await MilestoneCIProbe.shared.pauseNotification()')
    changed = replace_once(changed,'        try await store.reportMilestone(active, id: id)','        try await store.reportMilestone(active, id: id)\n        MilestoneCIProbe.shared.recordReport(id)')
    derived_worker = derive('CapabilityColdStartWorker.swift',original,changed)
    control = source/PREFIX/'CapabilityColdStartControl.swift'; original = control.read_text()
    changed = replace_once(original,'guard ordinary == nil, cancellation == nil, !notificationBusy else { throw coldStartError("busy") }','guard ordinary == nil, cancellation == nil, !notificationBusy else { MilestoneCIProbe.shared.recordBusy(kind); throw coldStartError("busy") }')
    changed = replace_once(changed,'        observation = CapabilityColdStartObservation(signals: signals, consumer: consumer)','        observation = CapabilityColdStartObservation(signals: signals, consumer: consumer)\n        MilestoneCIProbe.shared.install(self, signals)')
    derived_control = derive('CapabilityColdStartControl.swift',original,changed)
    repaired = (source/TEST).read_text(); original_test = (source/'original-test.swift.txt').read_text()
    retry = 'catch let error as UpdateError where error.code == "capability.runtime.busy" {'
    instrumented = replace_once(repaired,retry,retry+'\n                MilestoneCIProbe.shared.recordRetry()')
    early_name = 'testEarlyInstalledMilestonesWakeAutomaticHealthAndStartupAloneDoesNot'
    before_name = 'testBothReportsBeforeTimerPromoteWithoutFurtherPublicCalls'
    def controlled(text, order, repaired_variant):
        name = early_name if order == 'after-timer' else before_name
        start = text.index('    func '+name+'()'); end = text.index('\n    func ',start+1)
        body = text[start:end]
        needle = '        try await stage(f,runtime);'
        assert body.count(needle)==1
        body = body.replace(needle,'        let probe = MilestoneCIProbe.shared\n        addTeardownBlock { probe.release(); await runtime.close(); probe.reset() }\n'+needle)
        if order == 'after-timer':
            body = replace_once(body,'        try await Task.sleep(for: .milliseconds(1100))','        probe.arm()\n        try await Task.sleep(for: .milliseconds(1100))\n        try await eventually("timer notification not admitted") { probe.isEntered }\n        XCTAssertTrue(probe.timerFired)')
            call = 'try await reportInstalledMilestone("first_screen", to: runtime)' if repaired_variant else 'try await runtime.reportMilestone("first_screen")'
            milestone = 'first_screen'
        else:
            call = 'try await reportInstalledMilestone("feature_started", to: runtime)'; milestone='feature_started'
            marker = '        '+call+';'
            assert body.count(marker)==1
            body = body.replace(marker,'        probe.arm(); probe.wake()\n        try await eventually("pre-timer notification not admitted") { probe.isEntered }\n        XCTAssertFalse(probe.timerFired)\n'+marker)
        if repaired_variant:
            sequence = '''let returned = MilestoneCIReturnFlag()
        let reporting = Task { defer { returned.record() }; CALL }
        try await eventually("real busy retry not observed") { probe.retryCount >= 3 }
        XCTAssertGreaterThanOrEqual(probe.actualBusyCount, 3)
        XCTAssertFalse(returned.didReturn); XCTAssertEqual(probe.reported, [])
        let held = await runtime.recoverySnapshot(); XCTAssertNil(held.healthy)
        print("MILESTONE_CI held ORDER retries=\\(probe.retryCount) reported=\\(probe.reported) returned=\\(returned.didReturn) timerFired=\\(probe.timerFired)")
        probe.release(); try await reporting.value
        XCTAssertEqual(probe.reported, ["__REPORT__"])
        print("MILESTONE_CI released ORDER reported=\\(probe.reported) returned=\\(returned.didReturn) timerFired=\\(probe.timerFired)")'''.replace('CALL',call).replace('ORDER',order).replace('__REPORT__',milestone)
            # Replace only the selected call; the leading task statement replaces its line prefix.
            body = replace_once(body,call,sequence)
        else:
            body = replace_once(body,'        '+call,'        print("MILESTONE_CI original-call notificationHeld=\\(probe.isEntered) timerFired=\\(probe.timerFired)")\n        '+call)
        return text[:start]+body+text[end:]
    variants = {'repaired-unmodified':(repaired,None,None,0),
                'original-after-timer':(controlled(original_test,'after-timer',False),early_name,'original',1),
                'repaired-after-timer':(controlled(instrumented,'after-timer',True),early_name,'after-timer',0),
                'repaired-before-timer':(controlled(instrumented,'before-timer',True),before_name,'before-timer',0)}
    extra = r'''
    func testControlledInvalidAndClosedErrorsPropagate() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await opened(f), probe = MilestoneCIProbe.shared
        addTeardownBlock { probe.release(); await runtime.close(); probe.reset() }
        try await stage(f,runtime); _ = try await runtime.start()
        probe.arm(); probe.wake()
        try await eventually("notification missing") { probe.isEntered }
        let invalid = Task { try await reportInstalledMilestone("guest_supplied", to: runtime) }
        try await eventually("invalid report did not meet real busy") { probe.retryCount >= 3 }
        XCTAssertEqual(probe.reported, []); probe.release()
        do { try await invalid.value; XCTFail("invalid accepted") }
        catch let error as UpdateError { XCTAssertEqual(error.code,"capability.runtime.milestone"); print("MILESTONE_CI invalid-propagated \(error.code)") }
        try await close(runtime,baseline: baseline)
        let retries = probe.retryCount
        do { try await reportInstalledMilestone("feature_started", to: runtime); XCTFail("closed accepted") }
        catch let error as UpdateError { XCTAssertEqual(error.code,"capability.runtime.closed"); print("MILESTONE_CI closed-propagated \(error.code)") }
        XCTAssertEqual(probe.retryCount,retries); XCTAssertEqual(probe.reported, [])
    }
    func testControlledBusyDeadlineRemainsBounded() async throws {
        let baseline = CapabilityAttemptReservation.occupiedSlots, f = try fixture(), runtime = try await opened(f), probe = MilestoneCIProbe.shared
        addTeardownBlock { probe.release(); await runtime.close(); probe.reset() }
        try await stage(f,runtime); _ = try await runtime.start()
        probe.arm(); probe.wake()
        try await eventually("notification missing") { probe.isEntered }
        let started = ContinuousClock.now
        do { try await reportInstalledMilestone("feature_started", to: runtime); XCTFail("held report accepted") }
        catch let error as UpdateError { XCTAssertEqual(error.code,"test.timeout") }
        let elapsed = started.duration(to: .now)
        XCTAssertGreaterThanOrEqual(elapsed,.seconds(8)); XCTAssertLessThan(elapsed,.seconds(12))
        XCTAssertGreaterThan(probe.actualBusyCount,1); XCTAssertEqual(probe.actualBusyCount,probe.retryCount); XCTAssertEqual(probe.reported, [])
        let held = await runtime.recoverySnapshot(); XCTAssertNil(held.healthy)
        print("MILESTONE_CI deadline actualBusy=\(probe.actualBusyCount) reports=\(probe.reported) elapsed=\(elapsed)")
        probe.release(); try await close(runtime,baseline: baseline)
    }
'''
    extended = instrumented.rstrip(); assert extended.endswith('}'); extended = extended[:-1]+extra+'}\n'
    variants['repaired-errors']=(extended,'testControlledInvalidAndClosedErrorsPropagate','errors',0)
    variants['repaired-deadline']=(extended,'testControlledBusyDeadlineRemainsBounded','deadline',0)
    for name,(text,_,_,_) in variants.items(): derive(name+'.swift',original_test if name.startswith('original') else repaired,text)
    receipt['source_files'] = dict(files); receipt['source_tree_sha256'] = digest(files)
    (out/'derived-manifest.json').write_text(json.dumps({'files':files,'sha256':digest(files)},indent=2)+'\n')
    receipt['derived_manifest_sha256']=sha(out/'derived-manifest.json')
    # Preserve compact exact derivations separately from the replay input archive.
    shutil.copytree(source/'derived',out/'derived')
    def stable():
        for relative,h in files.items(): assert sha(source/relative)==h,relative
    stable()
    native_extra={'CARGO_TARGET_DIR':str(work/'rust-target'),'MACOSX_DEPLOYMENT_TARGET':'14.0','SDKROOT':sdk,'RUSTC':'/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc'}
    run('native-build',['/opt/homebrew/opt/rustup/bin/cargo','build','--locked','--offline','--release','--lib','--no-default-features','--features','experimental-capability-native','--manifest-path',source/'vm/Cargo.toml'],extra=native_extra)
    native=work/'rust-target/release/libmixer_vm.a'; receipt['native_archive']={'sha256':sha(native),'source_revision':receipt['native_source_revision'],'source_files':{k:v for k,v in receipt['input_files'].items() if k.startswith('vm/')}}
    frameworks=Path(env['DEVELOPER_DIR'])/'Platforms/MacOSX.platform/Developer/Library/Frameworks'; overlays=frameworks.parents[1]/'usr/lib'
    ctargets=[('MixerCapabilityIO','sdk/Sources/MixerCapabilities/NativeIO'),('MixerDurableIO','updates/Sources/MixerDurableIO'),('MixerCapabilityDurableIO','capability-activation/Sources/MixerCapabilityDurableIO'),('CMixerVMCapability','experimental-capability-runtime/Sources/CMixerVMCapability')]
    modules=[('Crypto','dependencies/swift-crypto/Sources/Crypto'),('MixerCore','sdk/Sources/MixerCore'),('MixerUI','sdk/Sources/MixerUI'),('MixerGuest','sdk/Sources/MixerGuest'),('MixerApple','sdk/Sources/MixerApple'),('MixerCapabilities','sdk/Sources/MixerCapabilities'),('MixerUpdates','updates/Sources/MixerUpdates'),('MixerRuntimeIdentity','runtime-identity/Sources/MixerRuntimeIdentity'),('MixerExperimentalCapabilityRuntime','experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime')]
    for mode in args.modes:
        stable(); products=work/mode; products.mkdir(); maps=products/'modulemaps'; maps.mkdir()
        flags=['-O'] if mode=='release' else ['-sanitize=thread'] if mode=='tsan' else []
        prefix=['xcrun','swiftc','-parse-as-library','-swift-version','6','-warnings-as-errors','-enable-testing','-target','arm64-apple-macosx14.0','-sdk',sdk,'-I',str(products),'-module-cache-path',str(products/'swift-cache')]+flags
        for name,folder in ctargets:
            includes=source/folder/'include'; mapping=maps/(name+'.modulemap'); mapping.write_text('module '+name+' { umbrella "'+str(includes)+'" export * }\n')
            prefix+=['-Xcc','-fmodule-map-file='+str(mapping)]
            cfiles=sorted((source/folder).glob('*.c')); assert len(cfiles)==1
            run(mode+'-compile-'+name,['xcrun','clang','-target','arm64-apple-macosx14.0','-isysroot',sdk,'-Wall','-Wextra','-Werror','-fPIC']+(['-fsanitize=thread'] if mode=='tsan' else ['-O2'] if mode=='release' else [])+['-I',includes,'-I',source/'vm/include','-c',cfiles[0],'-o',products/(name+'.o')])
        receipt.setdefault('generated_modulemaps',{})[mode] = {str(p.relative_to(products)): {'sha256':sha(p),'text':p.read_text()} for p in sorted(maps.glob('*'))}
        prefix+=['-Xcc','-I'+str(source/'vm/include')]
        for name,folder in modules:
            extra=['-DCRYPTO_IN_SWIFTPM','-enable-experimental-feature','Lifetimes','-enable-experimental-feature','SourceWarningControl','-enable-experimental-feature','CheckImplementationOnly'] if name=='Crypto' else []
            run(mode+'-compile-'+name,prefix+extra+['-whole-module-optimization','-emit-object','-emit-module','-module-name',name,'-emit-module-path',products/(name+'.swiftmodule')]+sorted((source/folder).rglob('*.swift'))+['-o',products/(name+'.o')])
        objects=[products/(name+'.o') for name,_ in ctargets+modules]
        for derived in [False,True]:
            active=products/('derived' if derived else 'production'); active.mkdir()
            lib=active/'libMixerMilestoneCI.dylib'
            active_files=[derived_worker if derived and p.name==derived_worker.name else derived_control if derived and p.name==derived_control.name else p for p in runtime_files]
            run(mode+('-derived' if derived else '-production')+'-link',prefix+['-emit-library','-emit-module','-module-name','MixerCapabilityActivation','-emit-module-path',active/'MixerCapabilityActivation.swiftmodule']+active_files+([source/'support/MilestoneProbe.swift'] if derived else [])+objects+[native,'-Xlinker','-install_name','-Xlinker','@rpath/'+lib.name,'-o',lib])
            for variant,(_,selection,order,expected) in variants.items():
                if (variant!='repaired-unmodified')!=derived: continue
                name=mode+'-'+variant; bundle=active/(variant+'.xctest'); exe=bundle/'Contents/MacOS/MixerMilestoneCITests'; exe.parent.mkdir(parents=True)
                shutil.copytree(source/'capability-activation/Tests/MixerCapabilityActivationTests/Fixtures',bundle/'Contents/Resources/Fixtures')
                (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':exe.name,'CFBundleIdentifier':'dev.mixer.milestone-ci.'+variant,'CFBundlePackageType':'BNDL','CFBundleVersion':'1'}))
                # Activation's matching module precedes dependencies' search path.
                test_prefix=prefix[:2]+['-I',str(active)]+prefix[2:]
                run(name+'-link',test_prefix+['-I',overlays,'-F',frameworks,'-emit-library','-module-name','MixerMilestoneCITests',source/('derived/'+variant+'.swift'),source/'support/TestSupport.swift','-L',active,'-lMixerMilestoneCI','-L',overlays,'-Xlinker','-rpath','-Xlinker',active,'-Xlinker','-rpath','-Xlinker',frameworks,'-Xlinker','-rpath','-Xlinker',overlays,'-o',exe])
                text=run(name,[xctest]+(['-XCTest','MixerMilestoneCITests.CapabilityColdStartRuntimeTests/'+selection] if selection else [])+[bundle],expected=expected,extra={'DYLD_INSERT_LIBRARIES':str(tsan)} if mode=='tsan' else None)
                if not selection: assert 'Executed 8 tests, with 0 failures' in text
                elif order=='original': assert 'actual-busy held=true' in text and 'caught error: "Capability cold-start runtime rejected"' in text and 'Executed 1 test, with 1 failure' in text
                else:
                    assert 'Executed 1 test, with 0 failures' in text
                    if order in ['before-timer','after-timer']:
                        assert 'MILESTONE_CI held '+order in text and 'reported=[] returned=false' in text
                        assert 'MILESTONE_CI released '+order in text and 'returned=true' in text
                        if order=='before-timer': assert 'returned=true timerFired=false' in text
                    elif order=='errors': assert 'invalid-propagated capability.runtime.milestone' in text and 'closed-propagated capability.runtime.closed' in text
                    elif order=='deadline': assert 'MILESTONE_CI deadline actualBusy=' in text and 'reports=[]' in text
                receipt['artifacts'][name]={'executable_sha256':sha(exe),'library_sha256':sha(lib)}
            receipt['artifacts'][mode+('-derived-runtime' if derived else '-production-runtime')]={'library_sha256':sha(lib),'module_sha256':sha(active/'MixerCapabilityActivation.swiftmodule')}
        receipt['artifacts'][mode+'-dependencies']={str(p.relative_to(products)):sha(p) for p in sorted(products.glob('*')) if p.is_file()}
        stable(); save()
    receipt['status']='passed'; receipt['result']='Every configured host mode passed the full repaired fixture, original expected real-busy failure, controlled before/after timer repair, exact invalid/closed propagation, and real-busy deadline.'
except BaseException as error:
    receipt['status']='failed'; receipt['problem']=repr(error); raise
finally:
    receipt['completed_utc']=datetime.now(timezone.utc).isoformat(); save()
