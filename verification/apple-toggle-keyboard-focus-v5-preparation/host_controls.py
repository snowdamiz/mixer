#!/usr/bin/env python3
"""V5 source-bound host controls and exact historical regressions."""
import ast
import datetime
import hashlib
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import time

B = pathlib.Path(__file__).resolve().parent; ROOT = B.parents[1]
assert not (B/'packet-seal.json').exists(), 'Sealed V5 is immutable'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
review = B.parent/'apple-toggle-keyboard-focus-v3-independent-review'
classes = lambda p: {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(p.read_text()).body if isinstance(n,ast.ClassDef)}
assert classes(review/'test_independent.py') == classes(B/'test_independent_adapted.py'), 'Independent class/test assertions changed'
groups = [
 ('v5-focused',[sys.executable,'-B',str(B/'test_v5.py')],18,0),
 ('v5-independent',[sys.executable,'-B',str(B/'test_independent_adapted.py')],17,0),
 ('v5-original44-fixture-extension',[sys.executable,'-B',str(B/'execute_v5_44.py')],44,0),
 ('unchanged-v4-39',[sys.executable,'-B',str(B/'execute_legacy_v4.py')],39,0),
 ('unchanged-v4-44-assertions',[sys.executable,'-B',str(B/'execute_legacy_v4_44.py')],44,0),
 ('unchanged-original-v3-44',[sys.executable,'-B',str(B/'execute_v3_controls.py')],44,0),
 ('unchanged-v2-29',[sys.executable,'-B',str(B.parent/'apple-toggle-keyboard-focus-v2/test_keyboard.py')],29,0),
 ('sealed-v3-still-three-findings',[sys.executable,'-B',str(B/'test_independent_adapted.py'),'--sealed-v3'],17,1),
 ('unchanged-v4-native-replay',[sys.executable,'-B',str(B.parent/'apple-toggle-keyboard-focus-v4/replay.py')],None,0),
 ('unchanged-v4-analysis-check',[sys.executable,'-B',str(B.parent/'apple-toggle-keyboard-focus-v4-runtime-analysis/analyze.py'),'--check'],None,0),
]
commands=[]
def command(name, argv, count=None, expected=0):
 start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,timeout=60,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 match=re.search(r'Ran (\d+) tests? in ',p.stderr);ran=int(match.group(1)) if match else None
 failures=sorted(set(re.findall(r'^FAIL: (test_\w+)',p.stderr,re.MULTILINE)))
 finding=['test_CONTRACT_replay_rejects_regressing_host_receipt_time','test_CONTRACT_wrong_route_search_cannot_satisfy_selected_route','test_CONTRACT_wrong_target_poll_cannot_supply_enabled_window']
 passed=p.returncode==expected and (count is None or ran==count) and (expected==0 or (failures==finding and 'FAILED (failures=5)' in p.stderr))
 commands.append({'name':name,'argv':list(map(str,argv)),'cwd':str(ROOT),'exitCode':p.returncode,'testsRun':ran,'expectedExitCode':expected,'expectedTestsRun':count,'elapsedSeconds':time.monotonic()-start,'stdout':p.stdout,'stderr':p.stderr,'expectedOutcomeMatched':passed})
 return p
for group in groups:command(*group)
host=B/'host-tools';host.mkdir(exist_ok=True)
compiler=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
sources=[B/'harness/UITests/DiagnosticTransport.swift',B/'TransportControls.swift']
sdk=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk')
compiled=command('shared-Swift-transport-host-build',[compiler,'-swift-version','6','-target','arm64-apple-macosx26.0','-sdk',sdk,*sources,'-o',host/'transport-controls'])
if compiled.returncode==0:command('shared-Swift-transport-host-controls',[host/'transport-controls'])
scratch=B/'.scratch'
assert not list(scratch.iterdir()), 'Host scratch not empty'
scratch.rmdir()
inputs=[*B.glob('*.py'),*B.glob('*.swift'),*sources,review/'test_independent.py',B.parent/'apple-toggle-keyboard-focus-v4/test_v4.py',B.parent/'apple-toggle-keyboard-focus-v3-preparation/test_settings_telemetry.py',compiler,sdk/'SDKSettings.json']
bindings={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha(p) for p in inputs}
passed=all(c['expectedOutcomeMatched'] for c in commands) and compiled.returncode==0
value={'schema':'mixer.apple-toggle.keyboard-v5-host-controls.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve().relative_to(ROOT))],'pythonVersion':sys.version,'hostVersion':platform.platform(),'exitCode':0 if passed else 1,'testsRun':18,'expectedTestsRun':18,'allRequiredGroupsPassed':passed,'commands':commands,'sourceFiles':bindings,'independentClassASTUnchanged':True,'fixtureAdaptation':'Synthetic route descendant/destination and fresh tap fields added before unchanged assertions; production accepts only explicit new wire. Legacy suites use old production with own scratch. No assertion relaxation.','sharedSwiftTransportSourceSHA256':sha(sources[0]),'sharedSwiftHostBinarySHA256':sha(host/'transport-controls') if compiled.returncode==0 else None,'stderr':'OK' if passed else 'inspect failed group','nativeExecuted':False,'runnerRuntimeExecuted':False}
attempt=len(list(B.glob('host-test-attempt-*.json')))+1
(B/f'host-test-attempt-{attempt}.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
if not passed:
 for c in commands:
  if not c['expectedOutcomeMatched']:print(c['name'],c['stderr'])
 raise SystemExit(1)
(B/'host-controls.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':'host-controls-passed','focusedV5':18,'independentV5':17,'same44V5Assertions':44,'legacyGroups':[39,44,44,29],'oldV3Findings':'same3methods/5failure records','sharedSwiftTransport':commands[-1]['stdout'].strip(),'nativeExecuted':False}))
