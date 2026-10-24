#!/usr/bin/env python3
"""Fixed frozen V5 adversarial replay; never write its journal or execute native."""
import hashlib
import json
import pathlib
import subprocess
import sys
import replay
B=pathlib.Path(__file__).resolve().parent;ROOT=B.parents[1]
OLD=B.parent/'apple-toggle-keyboard-focus-v5-preparation'
CAP=B.parent/'apple-toggle-keyboard-focus-v5-independent-review/witnesses/pre-tap-destination/captures'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 before={str(p.relative_to(ROOT)):sha(p) for p in sorted(CAP.iterdir()) if p.is_file()}
 code="import json,pathlib,sys;sys.path.insert(0,sys.argv[1]);import replay;print(json.dumps(replay.replay(pathlib.Path(sys.argv[2])),sort_keys=True))"
 argv=[sys.executable,'-B','-c',code,str(OLD),str(CAP)]
 p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=15)
 assert p.returncode==0,p.stderr
 historical=json.loads(p.stdout)
 assert historical['setupObservationSatisfied'] is True and len(historical['routeOpenedBindings'])==3
 records=[json.loads(p.read_bytes())['record'] for p in sorted(CAP.glob('0000-settings-*.json'))]
 details=[]
 for i in range(3):
  tap=next(r for r in records if r.get('stage')=='route-tap' and r['detail']['routeIndex']==i)
  opened=next(r for r in records if r.get('stage')=='route-opened' and r['routeIndex']==i)
  assert opened['captureStartedUptime'] < tap['detail']['startedUptime'] < tap['detail']['finishedUptime']
  details.append({'routeIndex':i,'tapSequence':tap['sequence'],'openedSequence':opened['sequence'],'tapStartedUptime':tap['detail']['startedUptime'],'tapFinishedUptime':tap['detail']['finishedUptime'],'openedCaptureStartedUptime':opened['captureStartedUptime'],'destinationObservedUptime':opened['routeWitness']['destination']['observedUptime']})
 try:replay.replay(CAP)
 except ValueError as e:reason=str(e)
 else:raise AssertionError('Exact stale V5 journal accepted')
 assert reason=='Route opened capture precedes same-route tap completion',reason
 assert before=={str(p.relative_to(ROOT)):sha(p) for p in sorted(CAP.iterdir()) if p.is_file()}
 return {'schema':'mixer.apple-toggle.keyboard-v6-fixed-stale-replay.1','status':'DIAGNOSTIC_ONLY','command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve().relative_to(ROOT)),'--check'],'sourceFiles':{str((OLD/'replay.py').relative_to(ROOT)):sha(OLD/'replay.py'),str((OLD/'settings_telemetry.py').relative_to(ROOT)):sha(OLD/'settings_telemetry.py'),str((B/'replay.py').relative_to(ROOT)):sha(B/'replay.py'),str((B/'settings_telemetry.py').relative_to(ROOT)):sha(B/'settings_telemetry.py')},'historicalCommand':argv,'historicalSummary':historical,'v6Rejected':True,'v6RejectionReason':reason,'routeDetails':details,'frozenJournalUnchanged':True,'frozenFiles':before,'nativeExecuted':False,'nativeKeyboardQualification':False,'gaAccepted':False}
if __name__=='__main__':
 result=check();path=B/'fixed-stale-replay.json'
 if '--check' in sys.argv:assert result==json.loads(path.read_bytes()),'Fixed replay differs'
 else:
  assert not (B/'packet-seal.json').exists(),'Sealed V6 is immutable'
  path.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'status':'fixed-stale-journal-rejected','v5HistoricalSetupTrue':True,'v6Rejected':True,'v6Reason':result['v6RejectionReason'],'allThreeHistoricalRoutesStale':True,'frozenFilesUnchanged':len(result['frozenFiles']),'nativeExecuted':False}))
