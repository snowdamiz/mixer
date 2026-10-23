#!/usr/bin/env python3
"""Rebuild exact full production Swift/C with fixed host linkage; retain evidence."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, os, shutil, subprocess, time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
p=argparse.ArgumentParser()
p.add_argument('--mode',choices=['debug','release','tsan'],default='debug')
p.add_argument('--scheduler',action='store_true')
p.add_argument('--probe',action='store_true')
p.add_argument('--debugger',action='store_true')
p.add_argument('--name',default='final-1')
a=p.parse_args();mode=a.mode
assert a.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in a.name)
assert int(a.scheduler)+int(a.probe)+int(a.debugger)<=1
tag=mode+('-scheduler' if a.scheduler else '-probe' if a.probe else '-debugger' if a.debugger else '')+'-'+a.name
out=HERE/'.build'/tag;out.mkdir(parents=True,exist_ok=False)
logs=HERE/'runs'/tag;logs.mkdir(parents=True,exist_ok=False)
source=out/'source';source.mkdir()
base_path=ROOT/'verification/guest-ui-teardown-window/builds/current-caaa005-1/build-receipt.json'
base=json.loads(base_path.read_text());original=next(x['argv'] for x in base['commands'] if x['name']=='link-current-runtime')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
receipt={'mode':mode,'started_utc':datetime.now(timezone.utc).isoformat(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'commands':[],'source_files':{},'dependency_artifacts':base['artifacts'],'dependency_receipt':str(base_path.relative_to(ROOT)),'dependency_receipt_sha256':sha(base_path),'artifacts':{},'cases_executed':[],'scope':'Private type-separated fixed host binding. Actual full activation Swift/C transport rebuilt. Retained real SDK/dependency objects are not rebuilt or TSan-instrumented. No JNI, Android Looper, device, signed core integration or GA authority.','scheduler_instrumentation':a.scheduler,'transport_barrier_instrumentation':a.probe}
flags=['-O','-g'] if mode=='release' else ['-g','-sanitize=thread'] if mode=='tsan' else ['-Onone','-g']
cflags=['-O2','-g'] if mode=='release' else ['-O1','-g','-fsanitize=thread'] if mode=='tsan' else ['-O0','-g']
env=dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
def save(): (logs/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def stable():
    for path,digest in receipt['source_files'].items():assert sha(source/path)==digest==sha(ROOT/path),path
def run(name,argv,expected=0,extra=None):
    stable();start=time.monotonic()
    try:r=subprocess.run([str(x) for x in argv],cwd=source,env=env|(extra or {}),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180);data,code=r.stdout,r.returncode
    except subprocess.TimeoutExpired as e:data,code=(e.stdout or b'')+b'\nTIMEOUT\n',124
    log=logs/(name+'.log');log.write_bytes(data)
    receipt['commands'].append({'name':name,'argv':[str(x) for x in argv],'cwd':str(source),'environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR']}|(extra or {}),'exit':code,'expected_exit':expected,'seconds':time.monotonic()-start,'log':str(log.relative_to(ROOT)),'log_sha256':sha(log)})
    save();print(name,code,flush=True);stable()
    if code!=expected or b'WARNING: ThreadSanitizer' in data:print(data.decode(errors='replace'));raise RuntimeError(name)
    return data.decode(errors='replace')
paths=list((ROOT/'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))
paths+=list((ROOT/'native/android/signed-guest-ui/binding/include').glob('*'))
paths+=[ROOT/'native/android/signed-guest-ui/transport'/n for n in ['transport.c','internal.h','include/mixer_ui_transport.h']]
paths+=list((HERE/'host-bridge').glob('*'))+[HERE/n for n in ['build.py','HostTests.swift','HoldingExecutor.swift','SchedulerTests.swift','ProbeTests.swift','DebuggerTests.swift','HostEntry.swift','HostOrdinaryClient.swift','HostPrivateClient.swift','host-bridge-contract.md']]
paths+=[ROOT/'docs/android-binding-stage4-seams.md',ROOT/'verification/android-binding-stage4-acceptance.json',ROOT/'verification/android-binding-stage4-contract/acceptance-matrix.json']
for path in paths:
    relative=str(path.relative_to(ROOT));target=source/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target);target.chmod(0o444);receipt['source_files'][relative]=sha(target)
receipt['source_tree_sha256']=hashlib.sha256(json.dumps(receipt['source_files'],sort_keys=True).encode()).hexdigest()
base_work=Path(base['dylib']).parents[1]
for relative,digest in base['artifacts'].items():assert sha(base_work/relative)==digest,relative
try:
    run('swift-version',['xcrun','swiftc','--version']);run('clang-version',['xcrun','clang','--version']);run('platform',['uname','-a'])
    transport=source/'native/android/signed-guest-ui/transport/transport.c';host=source/'verification/android-binding-stage4/host-bridge/host_bridge.c'
    cmaps=source/'native/android/signed-guest-ui/binding/include';fixture=source/'verification/android-binding-stage4/host-bridge'
    c_sources=[transport,host]+([fixture/'scheduler_probe.c'] if a.scheduler else [fixture/'transport_probe.c'] if a.probe else [])
    for c in c_sources:
        extra=['-Dmxuit_complete=mxish_transport_complete'] if a.scheduler and c==transport else ['-Dmxuit_facade_try_reclaim=mxish_actual_facade_try_reclaim','-Dmxuit_try_reclaim=mxish_actual_try_reclaim','-Dmxuit_ui_leave=mxish_actual_ui_leave','-Dmxuit_request=mxish_actual_request','-Dmxuit_complete=mxish_probe_complete','-Dmxuit_progress=mxish_probe_progress'] if a.probe and c==transport else []
        run(c.stem+'-compile',['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-DMIXER_UI_TRANSPORT_TESTING']+cflags+extra+['-c',c,'-o',out/(c.stem+'.o')])
    source_paths=sorted((source/'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))
    library=out/'libMixerAndroidStage4.dylib';argv=[]
    for arg in original:
        if arg.startswith(str(Path(base['source'])/'capability-activation/Sources/MixerCapabilityActivation')):continue
        if arg==base['dylib']:arg=str(library)
        elif arg.endswith('/products/MixerCapabilityActivation.swiftmodule'):arg=str(out/'MixerCapabilityActivation.swiftmodule')
        elif arg=='@rpath/libMixerGuestUITeardownRuntime.dylib':arg='@rpath/'+library.name
        argv.append(arg)
    module_flags=['-I',cmaps,'-I',fixture]
    insertion=argv.index('-emit-library');argv[insertion:insertion]=flags+module_flags+source_paths+[source/'verification/android-binding-stage4/HostEntry.swift']+[out/(c.stem+'.o') for c in c_sources]
    run('full-module-link',argv)
    receipt['artifacts'][str(library.relative_to(ROOT))]=sha(library)
    prefix=original[:original.index('-emit-library')];prefix=prefix[:2]+['-I',out]+prefix[2:]
    test=out/'Stage4HostTests';test_sources=[source/'verification/android-binding-stage4'/n for n in (['SchedulerTests.swift'] if a.scheduler else ['ProbeTests.swift'] if a.probe else ['DebuggerTests.swift'] if a.debugger else ['HostTests.swift','HoldingExecutor.swift'])]
    run('harness-link',prefix+flags+module_flags+['-Xcc','-fmodule-map-file='+str(fixture/'test.modulemap')]+(['-Xcc','-fmodule-map-file='+str(fixture/'scheduler.modulemap')] if a.scheduler else ['-Xcc','-fmodule-map-file='+str(fixture/'probe.modulemap')] if a.probe else [])+test_sources+['-emit-executable','-emit-module','-emit-module-path',out/'Stage4HostTests.swiftmodule','-L',out,'-lMixerAndroidStage4','-Xlinker','-rpath','-Xlinker',out,'-o',test])
    scenarios=[] if a.debugger else ['no-hold','hold'] if a.scheduler else ['lost-before','lost-after','no-progress','ui-leave','completion','progress','fast','request-rejection','late-entry'] if a.probe else ['smoke','prebind','single-join','destructor','helper-alias','fallback','late-before','late-after','after-reclaim','terminal-capacity','failed-retire','missing-native','capacity','facade-acquire-failure','endpoint-acquire-failure','bind-failure','cancelled-preparation','nested','fault-leave','fault-read','fault-write','cleanup-exhaustion','c-facade-exhaustion','cycles','drop-prepared','drop-transferred','drop-bound-late','fallback-ids','leased-ingress','partial-retire','wrong-final-owner','close-before-bind','late-progress-fault','rendezvous-reuse','queued-close','terminal-retire-failure']
    for scenario in scenarios:
        output=run(scenario,[test,scenario]);assert ('SCHEDULER_PASS' if a.scheduler else 'PROBE_PASS' if a.probe else 'HOST_PASS') in output
        receipt['cases_executed'].append(scenario);save()
    if not a.scheduler and not a.probe and not a.debugger:
        negative_flags=prefix+flags+module_flags
        ordinary=run('ordinary-private-types',negative_flags+['-typecheck',source/'verification/android-binding-stage4/HostOrdinaryClient.swift'],expected=1)
        assert "cannot find type 'CapabilityAndroidHostInstallation' in scope" in ordinary
        private=run('testable-sealed-authority',negative_flags+['-typecheck',source/'verification/android-binding-stage4/HostPrivateClient.swift'],expected=1)
        for needle in ["'lifetime' is inaccessible", "'permit' is inaccessible", "cannot convert value of type 'CapabilityAndroidHostInstallation'", "'CapabilityAndroidHostTaskReturnEvidence' initializer is inaccessible", "'CapabilityAndroidHostLifetimeCapsule' initializer is inaccessible"]:
            assert needle in private,needle
    receipt['artifacts'][str(test.relative_to(ROOT))]=sha(test)
    receipt['result']='actual host debugger binary compiled; execution requires separate debugger receipt' if a.debugger else 'selected actual host scenarios passed'
except BaseException as error:
    receipt['result']='failed verification retained';receipt['error']=str(error);raise
finally:
    receipt['completed_utc']=datetime.now(timezone.utc).isoformat();save()
