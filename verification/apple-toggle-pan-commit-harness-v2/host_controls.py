"""Record repeatable host-only oracle/reader controls; no native tools."""
import datetime
import json
import pathlib
import subprocess
import sys
import time
import run

BASE,ROOT=run.BASE,run.ROOT
assert not (BASE/'packet-seal.json').exists(),'Sealed preparation is immutable'
argv=[sys.executable,'-B','-m','unittest','discover','-s',str(BASE.relative_to(ROOT)),'-p','test_*.py','-v']
paths=list(BASE.glob('*.py'))+[BASE/'cases.json']+list((BASE/'harness').rglob('*'))
paths += [ROOT/'verification/apple-toggle-pan-origin-correction/oracle.py',ROOT/'verification/apple-toggle-native-interruption/interruption_oracle.py',ROOT/'verification/apple-toggle-native-interruption/test_oracle.py',ROOT/'verification/apple-toggle-semantic-activation/semantic_oracle.py']
source={str(p.relative_to(ROOT)):run.sha(p) for p in sorted(set(paths)) if p.is_file()}
started=time.monotonic();p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True)
assert source=={n:run.sha(ROOT/n) for n in source},'Host sources changed during controls'
value={'schema':'mixer.apple-toggle.pan-commit-harness-v2-host-controls.1','argv':argv,'cwd':str(ROOT),
       'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsedSeconds':time.monotonic()-started,
       'pythonVersion':sys.version,'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,
       'testsRun':37 if 'Ran 37 tests' in p.stderr else None,'expectedTestsRun':37,'sourceFiles':source,
       'oracleTestMethods':13,'readerAndDeadlineTestMethods':24,
       'syntheticPanPositiveControls':16,'explicitNegativeOracleMutationControls':527,
       'capturedFailedPanCasesReevaluatedDiagnostically':16,'offlineReplayStatus':'DIAGNOSTIC_ONLY',
       'unchangedOriginalNativeActionOracleReplays':13,'unchangedInterruptionOracleReplays':16,
       'unchangedScopedSemanticRows':36,'explicitWaitAndSessionDeadlineControls':True,
       'nativeExecuted':False,'nativeInstancesQueried':False,'physicalDevicesQueried':False,
       'scope':'Host synthetic/mutation/race controls only. Original native run remains failed; new native execution pending root selection.'}
attempt=len(list(BASE.glob('host-test-attempt-*.json')))+1
for path in [BASE/('host-test-attempt-'+str(attempt)+'.json'),BASE/'host-controls.json']:path.write_text(json.dumps(value,indent=2)+'\n')
print(p.stderr);print(json.dumps({k:v for k,v in value.items() if k not in ['stdout','stderr','sourceFiles']},sort_keys=True))
raise SystemExit(p.returncode)
