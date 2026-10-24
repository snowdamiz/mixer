"""Host-only v2 focus/metadata checks. No simulator, UI or native application operations."""
import datetime
import json
import pathlib
import subprocess
import sys
import time
import run
import keyboard_oracle as o
BASE,ROOT=run.BASE,run.ROOT
assert not (BASE/'packet-seal.json').exists(),'Sealed preparation is immutable'
paths=list(BASE.glob('*.py'))+[BASE/'cases.json']+list((BASE/'harness').rglob('*'))
source={str(p.relative_to(ROOT)):run.sha(p) for p in sorted(paths) if p.is_file()}
argv=[sys.executable,'-B','-m','unittest','discover','-s',str(BASE.relative_to(ROOT)),'-p','test_*.py','-v'];start=time.monotonic()
p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True);assert source=={n:run.sha(ROOT/n) for n in source}
value={'schema':'mixer.apple-toggle.keyboard-v2-host-controls.1','argv':argv,'cwd':str(ROOT),'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsedSeconds':time.monotonic()-start,'pythonVersion':sys.version,'exitCode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'expectedTestsRun':29,'testsRun':29 if 'Ran 29 tests' in p.stderr else None,'sourceFiles':source,'inheritedTestMethods':20,'newV2TestMethods':9,'positivePhaseFixtures':'Inherited40 synthetic phase/route cases align app focus with paired native AX; no native evidence implied','newExplicitNegativeControls':{'pairedFocusDisagreementBothDirections':4,'authoredLabelMatchesCurrentApp':3,'allThreeIdentifierSubstitutions':6,'allThreeLabelChanges':6,'betweenKeyMetadataChanges':3,'missingOrIncorrectFocusUpdateSignal':2,'nonfixedOrUnchangedAcquisition':2,'originalRootSyntheticRegressions':2},'scope':'Host-only synthetic/mutation controls. Focus disagreement or missing didUpdateFocus signal remains failed evidence pending native analysis. Strict3element acquisition only.','nativeExecuted':False,'nativeInstancesQueried':False,'physicalDevicesQueried':False}
number=len(list(BASE.glob('host-test-attempt-*.json')))+1
for path in [BASE/('host-test-attempt-'+str(number)+'.json'),BASE/'host-controls.json']:path.write_text(json.dumps(value,indent=2)+'\n')
print(p.stderr);print(json.dumps({k:v for k,v in value.items() if k not in ['stdout','stderr','sourceFiles']},sort_keys=True));raise SystemExit(p.returncode)
