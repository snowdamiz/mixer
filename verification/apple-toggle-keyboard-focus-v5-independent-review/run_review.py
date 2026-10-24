#!/usr/bin/env python3
"""Bounded offline review. Writes only this new review directory."""
import datetime
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import time

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/apple-toggle-keyboard-focus-v5-preparation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
attempt=len(list(HERE.glob('attempt-*.json')))+1
commands=[]
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','CLANG_MODULE_CACHE_PATH':str(HERE/'host-module-cache'),'SWIFT_MODULECACHE_PATH':str(HERE/'host-module-cache')}

def command(name,argv):
    started=time.monotonic()
    try:
        p=subprocess.run(list(map(str,argv)),cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
        result={'name':name,'argv':list(map(str,argv)),'cwd':str(ROOT),'exitCode':p.returncode,'elapsedSeconds':time.monotonic()-started,'stdout':p.stdout,'stderr':p.stderr}
    except subprocess.TimeoutExpired as error:
        result={'name':name,'argv':list(map(str,argv)),'cwd':str(ROOT),'exitCode':None,'timedOut':True,'elapsedSeconds':time.monotonic()-started,'stdout':str(error.stdout),'stderr':str(error.stderr)}
    commands.append(result)
    (HERE/f'attempt-{attempt}-{name}.stdout').write_text(result['stdout'])
    (HERE/f'attempt-{attempt}-{name}.stderr').write_text(result['stderr'])
    print(json.dumps({k:result[k] for k in ['name','exitCode','elapsedSeconds']}),flush=True)
    return result

packet=PRODUCER/'packet-seal.json'
selection=ROOT/'verification/apple-toggle-keyboard-focus-v4-root-review/v5-preparation-selection.json'
assert sha(packet)=='8626e01f8622b0a27176cb37331edd7076d50b566f61b5c52bc5d4b1703770aa'
assert sha(selection)=='d9849baa4dadc9285e5b95f1ec35ff560d9926aec6d66e2d9f9e01e98b1cd8ca'
seal=json.loads(packet.read_bytes())
verified={name:sha(ROOT/name) for name in seal['files'] if (ROOT/name).is_file() and not (ROOT/name).is_symlink()}
assert verified==seal['files'] and len(verified)==84
compiler=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
sdk=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
command('python-version',[sys.executable,'--version'])
command('swift-version',[compiler,'--version'])
command('sealed-preflight',[sys.executable,'-B',PRODUCER/'run.py','verify'])
command('independent-host',[sys.executable,'-B',HERE/'test_review.py'])
compiled=command('shared-transport-build',[compiler,'-swift-version','6','-target','arm64-apple-macosx26.0','-sdk',sdk,'-module-cache-path',HERE/'host-module-cache',PRODUCER/'harness/UITests/DiagnosticTransport.swift',HERE/'TransportAdversarial.swift','-o',HERE/'transport-adversarial'])
if compiled['exitCode']==0:
    command('shared-transport-controls',[HERE/'transport-adversarial'])
assert not list((HERE/'.scratch').iterdir()),'Owned host scratch not empty'
(HERE/'.scratch').rmdir()
after={name:sha(ROOT/name) for name in seal['files']}
assert after==verified,'Producer sealed files changed during review'
inputs=[HERE/'run_review.py',HERE/'test_review.py',HERE/'TransportAdversarial.swift',packet,selection,ROOT/'AGENTS.md',ROOT/'mixer-product-plan.md',compiler,sdk/'SDKSettings.json',PRODUCER/'harness/UITests/ToggleUITests.swift',PRODUCER/'harness/UITests/DiagnosticTransport.swift',PRODUCER/'settings_telemetry.py',PRODUCER/'run.py',PRODUCER/'replay.py']
record={'schema':'mixer.apple-toggle.keyboard-v5-independent-review-attempt.1','attempt':attempt,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(HERE/'run_review.py')],'pythonVersion':sys.version,'hostVersion':platform.platform(),'sourceRevisionContext':json.loads((PRODUCER/'runner-binary-receipt.json').read_bytes())['sourceRevisionContext'],'producerPacketSHA256':sha(packet),'rootSelectionSHA256':sha(selection),'sealedFileCount':len(verified),'producerSealVerifiedBeforeAndAfter':True,'sourceFiles':{str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha(p) for p in inputs},'commands':commands,'scope':'Synthetic host-only real Session/Bridge/replay and host Foundation executable of exact shared Swift transport; no native execution','nativeExecuted':False,'nativeInstancesQueried':False,'physicalPhones':'disconnected-deferred','applicationCasesExecuted':0,'nativeKeyboardQualification':False,'carrierAccepted':False,'gaAccepted':False}
(HERE/f'attempt-{attempt}.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps({'attempt':attempt,'receipt':str(HERE/f'attempt-{attempt}.json'),'allCommandsExitZero':all(c['exitCode']==0 for c in commands)}))
