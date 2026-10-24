"""Record host-only keyboard oracle, transport and artifact-export controls."""
import datetime
import json
import pathlib
import subprocess
import sys
import time
import run
BASE,ROOT=run.BASE,run.ROOT
assert not (BASE/'packet-seal.json').exists(),'Sealed preparation is immutable'
paths=list(BASE.glob('*.py'))+list((BASE/'harness').rglob('*'))+[BASE/'cases.json']
source={str(p.relative_to(ROOT)):run.sha(p) for p in sorted(paths) if p.is_file()}
argv=[sys.executable,'-B','-m','unittest','discover','-s',str(BASE.relative_to(ROOT)),'-p','test_*.py','-v']
start=time.monotonic();p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True)
assert source=={n:run.sha(ROOT/n) for n in source},'Control source changed during tests'
value={'schema':'mixer.apple-toggle.keyboard-host-controls.1','argv':argv,'cwd':str(ROOT),'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsedSeconds':time.monotonic()-start,'pythonVersion':sys.version,'sourceRevisionContext':run.prerequisite()['sourceRevisionContext'],'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'expectedTestsRun':20,'testsRun':20 if 'Ran 20 tests' in p.stderr else None,'sourceFiles':source,'syntheticPositivePhaseControls':40,'explicitOracleNegativeMutationControls':63,'closedCursorAndWitnessIntegrationControls':True,'fixedExportSuccessFailureTimeoutCleanupControls':True,'nativeExecuted':False,'nativeInstancesQueried':False,'physicalDevicesQueried':False,'scope':'Host controls only. Public keyboard delivery, focus traversal and Settings runtime remain pending root execution.'}
number=len(list(BASE.glob('host-test-attempt-*.json')))+1
for target in [BASE/('host-test-attempt-'+str(number)+'.json'),BASE/'host-controls.json']:target.write_text(json.dumps(value,indent=2)+'\n')
print(p.stderr);print(json.dumps({k:v for k,v in value.items() if k not in ['stdout','stderr','sourceFiles']},sort_keys=True));raise SystemExit(p.returncode)
