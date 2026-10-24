#!/usr/bin/env python3
"""V6 host-only source-bound ordering, unchanged assertions and historical failures."""
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
B=pathlib.Path(__file__).resolve().parent;ROOT=B.parents[1]
assert not (B/'packet-seal.json').exists(),'Sealed V6 is immutable'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
review=B.parent/'apple-toggle-keyboard-focus-v5-independent-review'
prior=B.parent/'apple-toggle-keyboard-focus-v5-preparation'
def methods(path,cls):
 c=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef) and n.name==cls)
 return {n.name:ast.dump(n,include_attributes=False) for n in c.body if isinstance(n,ast.FunctionDef)}
old=methods(review/'test_review.py','IndependentV5Tests');new=methods(B/'test_v5_independent26.py','IndependentV5Tests')
changed=[name for name in old if old[name]!=new.get(name)]
assert len(old)==len(new)==27 and changed==['test_CONTRACT_destination_captured_before_tap_return_cannot_complete'],changed
classes=lambda p:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text()).body if isinstance(n,ast.ClassDef)}
assert classes(B.parent/'apple-toggle-keyboard-focus-v3-independent-review/test_independent.py')==classes(B/'test_independent_adapted.py')
assert sha(B/'test_v5.py')==sha(prior/'test_v5.py')
assert sha(B/'fixtures.py')==sha(prior/'fixtures.py')
groups=[
 ('v6-focused-ordering',[sys.executable,'-B',B/'test_v6.py'],8,0),
 ('v6-independent26-semantics',[sys.executable,'-B',B/'test_v5_independent26.py'],26,0),
 ('unchanged-v5-focused18-on-v6',[sys.executable,'-B',B/'test_v5.py'],18,0),
 ('unchanged-independent17-on-v6',[sys.executable,'-B',B/'test_independent_adapted.py'],17,0),
 ('same-original44-on-v6',[sys.executable,'-B',B/'execute_v5_44.py'],44,0),
 ('unchanged-v4-39',[sys.executable,'-B',B/'execute_legacy_v4.py'],39,0),
 ('unchanged-v4-44',[sys.executable,'-B',B/'execute_legacy_v4_44.py'],44,0),
 ('unchanged-v3-44',[sys.executable,'-B',B/'execute_v3_controls.py'],44,0),
 ('unchanged-v2-29',[sys.executable,'-B',B.parent/'apple-toggle-keyboard-focus-v2/test_keyboard.py'],29,0),
 ('sealed-v3-same-three-findings',[sys.executable,'-B',B/'test_independent_adapted.py','--sealed-v3'],17,1),
 ('sealed-v5-same-ordering-finding26',[sys.executable,'-B',B/'execute_legacy_v5_review.py'],26,1),
 ('unchanged-v4-native-replay',[sys.executable,'-B',B.parent/'apple-toggle-keyboard-focus-v4/replay.py'],None,0),
 ('unchanged-v4-analysis-check',[sys.executable,'-B',B.parent/'apple-toggle-keyboard-focus-v4-runtime-analysis/analyze.py','--check'],None,0),
 ('exact-v5-shared-Swift-host-binary',[B/'host-tools/transport-controls'],None,0),
 ('exact-v5-independent-Swift-host-binary',[B/'host-tools/transport-adversarial'],None,0),
]
commands=[]
for name,argv,count,expected in groups:
 start=time.monotonic();argv=list(map(str,argv))
 p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=60,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 match=re.search(r'Ran (\d+) tests? in ',p.stderr);ran=int(match.group(1)) if match else None
 failures=sorted(set(re.findall(r'^FAIL: (test_\w+)',p.stderr,re.MULTILINE)))
 passed=p.returncode==expected and (count is None or ran==count)
 if expected==1:
  expected_failure=['test_CONTRACT_destination_captured_before_tap_return_cannot_complete'] if 'v5-' in name else ['test_CONTRACT_replay_rejects_regressing_host_receipt_time','test_CONTRACT_wrong_route_search_cannot_satisfy_selected_route','test_CONTRACT_wrong_target_poll_cannot_supply_enabled_window']
  passed=passed and failures==expected_failure and ('FAILED (failures=1)' if 'v5-' in name else 'FAILED (failures=5)') in p.stderr
 if name=='exact-v5-shared-Swift-host-binary':passed=passed and json.loads(p.stdout)['sharedSwiftTransportChecks']==16
 if name=='exact-v5-independent-Swift-host-binary':passed=passed and json.loads(p.stdout)['independentSharedTransportChecks']==35
 commands.append({'name':name,'argv':argv,'cwd':str(ROOT),'exitCode':p.returncode,'testsRun':ran,'expectedExitCode':expected,'expectedTestsRun':count,'elapsedSeconds':time.monotonic()-start,'stdout':p.stdout,'stderr':p.stderr,'expectedOutcomeMatched':passed})
 print(name,'PASS' if passed else 'FAIL',flush=True)
 if not passed:print(p.stderr,flush=True)
scratch=B/'.scratch';assert not list(scratch.iterdir()),'Host scratch not empty';scratch.rmdir()
inputs=[*B.glob('*.py'),*B.glob('*.swift'),*B.glob('harness/UITests/*.swift'),*B.glob('host-tools/*'),review/'test_review.py',review/'review-seal.json',B.parent/'apple-toggle-keyboard-focus-v3-independent-review/test_independent.py',B.parent/'apple-toggle-keyboard-focus-v4/test_v4.py',B.parent/'apple-toggle-keyboard-focus-v3-preparation/test_settings_telemetry.py']
bindings={str(p.relative_to(ROOT)):sha(p) for p in inputs}
passed=all(c['expectedOutcomeMatched'] for c in commands)
value={'schema':'mixer.apple-toggle.keyboard-v6-host-controls.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve().relative_to(ROOT))],'pythonVersion':sys.version,'hostVersion':platform.platform(),'exitCode':0 if passed else 1,'testsRun':8,'expectedTestsRun':8,'allRequiredGroupsPassed':passed,'commands':commands,'sourceFiles':bindings,'independent26UnchangedMethods':25,'independent26AdaptedContractMethod':changed,'independent17ClassASTUnchanged':True,'fixtureAdaptation':'Exact V5 positive fixture adapter, 18 focused methods and original44 assertions; 25 independent V5 methods unchanged; CONTRACT now expects immediate ValueError and retains its false-setup assertion. Historical tests use unchanged old producers and owned scratch/witnesses.','sharedSwiftTransportSourceSHA256':sha(B/'harness/UITests/DiagnosticTransport.swift'),'sharedSwiftHostBinarySHA256':sha(B/'host-tools/transport-controls'),'independentSwiftHostBinarySHA256':sha(B/'host-tools/transport-adversarial'),'stderr':'OK' if passed else 'inspect failed group','nativeExecuted':False,'runnerRuntimeExecuted':False,'compiled':False}
attempt=len(list(B.glob('host-test-attempt-*.json')))+1
(B/f'host-test-attempt-{attempt}.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
if not passed:raise SystemExit(1)
(B/'host-controls.json').write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':'all-host-groups-passed','focusedV6':8,'independentV5Semantics':26,'priorAssertions':[18,17,44,39,44,44,29],'historicalV5Finding':'one CONTRACT failure retained/25pass','historicalV3Findings':'same3methods/5failure records','SwiftChecks':[16,35],'nativeExecuted':False}))
