#!/usr/bin/env python3
"""Replay retained records through the actual bound composition without native calls."""
import copy, hashlib, importlib, json, pathlib, secrets, shutil, statistics, sys, tempfile, time
HERE=pathlib.Path(__file__).resolve().parent;REPO=HERE.parents[2]
mode=sys.argv[1];assert mode in ['baseline','candidate']
scratch=pathlib.Path(tempfile.mkdtemp(prefix='mixer-20261107-apple-settings-full-'+mode+'-',dir='/tmp')).resolve()
report={'scope':'host replay through exact composed receiver and binding guards; never native dispatch','mode':mode,'scratch':str(scratch)}
try:
 selected=scratch/'verification/apple-passive-lifecycle-runtime-preparation/native-run-v9-host-comparison/selected'
 shutil.copytree(HERE/'baseline-runtime',selected)
 relative='inputs/runtime/verification/apple-toggle-keyboard-focus-v9-preparation/settings_telemetry.py'
 if mode=='candidate':shutil.copyfile(HERE/'candidate/settings_telemetry.py',selected/relative)
 selection=json.loads((REPO/'verification/apple-passive-lifecycle-runtime-preparation/selection-template.json').read_text())
 root=json.loads((HERE.parent/'apple-runtime/root-selection.json').read_text())
 selection.update(repositoryRoot=str(REPO),outputBase=str(scratch/'output'),productsRoot=str(scratch/'unused-products'),trustedRootSelection=root)
 if mode=='candidate':selection['files'][relative]=hashlib.sha256((selected/relative).read_bytes()).hexdigest()
 (selected/'runtime-selection.json').write_text(json.dumps(selection))
 sys.path.insert(0,str(selected));m=importlib.import_module('composition')
 output=scratch/'captures';receiver=m.h.Bridge({'diagnostic':scratch/'unused-documents'},output,secrets.token_hex(32),root['ownedSimulatorIdentity'],allowed_cases={'keyboard-enabled-off'})
 actual=HERE.parent/'apple-runtime';result=json.loads((actual/'result.json').read_text());captures=actual/result['artifacts']['rawCaptures']
 rows=[json.loads(p.read_text()) for p in sorted(captures.glob('0000-settings-*.json'))]
 clock=[rows[0]['receivedUptime']];receiver.settings.now=lambda:clock[0];receiver.settings.token=rows[0]['generation'];receiver.settings.deadline=rows[0]['sessionDeadlineUptime']
 timings=[];skipped=[]
 for row in rows:
  record=row['record']
  if mode=='candidate' and record.get('slot')=='settings-0131-png':skipped.append(record['sequence']);continue
  clock[0]=row['receivedUptime'];began=time.monotonic();response=receiver.request('evaluate',{'settingsDiagnostic':copy.deepcopy(record)});timings.append(time.monotonic()-began)
 report.update(requests=len(timings),receiverSeconds=timings,totalSeconds=sum(timings),medianSeconds=statistics.median(timings),skippedRetainedRedundantChunks=skipped,settingsSummary=receiver.settings.summary(),actualSetupReady=m.setup_ready(receiver.settings),runtimeBindingsChecked=True)
 assert not m.setup_ready(receiver.settings)
 try:receiver.request('begin',{'candidate':'diagnostic','case':'keyboard-enabled-off'})
 except ValueError as e:
  assert 'Durable measured setup' in str(e);report['prematureTabRejected']=str(e)
 else:raise AssertionError('Premature Tab handoff allowed')
 # Source mutation must still fail before another request; no root/source originals touched.
 target=selected/relative;old=target.read_bytes();target.write_bytes(old+b'\n')
 try:receiver.request('evaluate',{'settingsDiagnostic':rows[-1]['record']})
 except ValueError as e:
  assert 'source/data changed' in str(e);report['sourceMutationRejected']=True
 else:raise AssertionError('Changed source passed binding gate')
 finally:target.write_bytes(old)
 if mode=='candidate':
  import replay
  replayed=replay.replay(output);assert replayed==report['settingsSummary'];report['exactComposedReplayPassed']=True
  assert (output/'settings-0131-png.png').read_bytes()==(captures/'settings-0083-png.png').read_bytes()
  report['terminalPayloadBytesEqualPriorValidatedPNG']=True
finally:
 shutil.rmtree(scratch);report['scratchRemoved']=not scratch.exists();(HERE/('full-composition-'+mode+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['receiverSeconds','settingsSummary']},indent=2))
