#!/usr/bin/env python3
"""Record fresh actual implementation commands and exact execution inputs."""
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
import packet as p
b=p.BASE
p.require(not (b/'packet-seal.json').exists(),'Sealed V8 evidence is immutable')
attempts=b/'commands';attempts.mkdir(exist_ok=True)
number=1
while (attempts/('attempt-'+str(number))).exists():number+=1
out=attempts/('attempt-'+str(number));out.mkdir()
V6=b.parent/'apple-toggle-keyboard-focus-v6-preparation'
executables=[p.V7/'host-tools/selection-controls',V6/'host-tools/transport-controls',V6/'host-tools/transport-adversarial']
source_paths=[*b.glob('*.py'),*b.glob('harness/UITests/*.swift'),b/'swift-public-witness.json',*executables]
sourceFiles={str(path.relative_to(p.ROOT)):p.sha(path) for path in source_paths}
(out/'execution-inputs.json').write_text(json.dumps(sourceFiles,indent=2,sort_keys=True)+'\n')
groups=[('actual-v8-session-bridge-replay',[sys.executable,'-B',str(b/'test_v8.py')],21),
        ('adversarial-actual-session-bridge-http-replay-persistence',[sys.executable,'-B',str(b/'test_persistence.py')],10),
        ('unchanged-native-Swift-resolver-host-provider',[str(executables[0]),str(b/'swift-public-witness.json')],71),
        ('exact-unchanged-shared-transport',[str(executables[1])],16),
        ('exact-unchanged-independent-transport',[str(executables[2])],35)]
commands=[]
for name,argv,expected in groups:
    start=time.monotonic();observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat()
    c=subprocess.run(argv,cwd=p.ROOT,capture_output=True,text=True,timeout=60,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    (out/(name+'.stdout')).write_text(c.stdout);(out/(name+'.stderr')).write_text(c.stderr)
    if name.startswith('actual-') or name.startswith('adversarial-'):
        match=re.search(r'Ran (\d+) tests? in ',c.stderr);observed=int(match.group(1)) if match else None
    else:
        try:observed=json.loads(c.stdout)[{71:'actualSwiftResolverControls',16:'sharedSwiftTransportChecks',35:'independentSharedTransportChecks'}[expected]]
        except (ValueError,KeyError):observed=None
    passed=c.returncode==0 and observed==expected
    commands.append(dict(name=name,argv=argv,cwd=str(p.ROOT),observedUTC=observedUTC,exitCode=c.returncode,elapsedSeconds=time.monotonic()-start,expected=expected,observed=observed,passed=passed,stdoutSHA256=p.sha(out/(name+'.stdout')),stderrSHA256=p.sha(out/(name+'.stderr'))))
    print(name,'PASS' if passed else 'FAIL',flush=True)
    if not passed:print(c.stderr,flush=True)
# The witness binary rewrites its deterministic wire output; bind it again.
p.require(all(p.sha(p.ROOT/name)==expected for name,expected in sourceFiles.items()),'Executed sources changed')
passed=all(c['passed'] for c in commands)
result=dict(schema='mixer.apple-keyboard.v8-actual-host-controls.1',command=[sys.executable,'-B',str(pathlib.Path(__file__).resolve())],cwd=str(p.ROOT),
            observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceRevisionContext=subprocess.check_output(['git','rev-parse','HEAD'],cwd=p.ROOT,text=True).strip(),
            pythonVersion=sys.version,pythonExecutable=str(pathlib.Path(sys.executable).resolve()),pythonExecutableSHA256=p.sha(pathlib.Path(sys.executable).resolve()),platform=platform.platform(),
            sourceFiles=sourceFiles,sourceTreeSHA256=hashlib.sha256(json.dumps(sourceFiles,sort_keys=True,separators=(',',':')).encode()).hexdigest(),commands=commands,
            sessionMethods=21,persistenceMethods=10,persistenceConcreteHTTPControls=p.read(b/'persistence-controls.json')['controlCount'],unchangedSwiftResolverControls=71,unchangedTransportControls=[16,35],
            passed=passed,nativeExecuted=False,nativeInstancesQueried=False,scope='Synthetic actual V8 Session/Bridge/HTTP/replay plus unchanged compiled host controls; no native/UI/device execution',commandOutputDirectory=str(out.relative_to(p.ROOT)))
(out/'commands.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
(b/'host-controls.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
raise SystemExit(0 if passed else 1)
