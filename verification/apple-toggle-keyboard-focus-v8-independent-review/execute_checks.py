"""Record fresh review commands; mutates only this owned review directory."""
import datetime
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import time

HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
name=os.environ.get('MIXER_REVIEW_ATTEMPT','attempt-2');logs=HERE/'commands'/name;logs.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source={str(p.relative_to(ROOT)):sha(p) for p in [HERE/'independent_flow.py',HERE/'host_checks.py',HERE/'fault_probe.py',HERE/'execute_checks.py']}
for rel in source:(logs/pathlib.Path(rel).name).write_bytes((ROOT/rel).read_bytes())
results=[]
for label,argv in [('python-version',[sys.executable,'--version']),('independent-actual-http-host-checks',[sys.executable,'-B',str(HERE/'host_checks.py')]),('independent-guard-absence-probe',[sys.executable,'-B',str(HERE/'fault_probe.py')])]:
    started=time.monotonic();cp=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60,env={**os.environ,'MIXER_REVIEW_ATTEMPT':name})
    for suffix,data in [('stdout',cp.stdout),('stderr',cp.stderr)]:(logs/(label+'.'+suffix)).write_bytes(data)
    results.append(dict(name=label,argv=argv,cwd=str(ROOT),elapsedSeconds=time.monotonic()-started,exitCode=cp.returncode,observedUTC=datetime.datetime.now(datetime.UTC).isoformat(),stdoutSHA256=hashlib.sha256(cp.stdout).hexdigest(),stderrSHA256=hashlib.sha256(cp.stderr).hexdigest()))
    print(label,cp.returncode,cp.stdout.decode()[-1000:],cp.stderr.decode()[-4000:])
(logs/'commands.json').write_text(json.dumps(dict(schema='mixer.apple-keyboard.v8-independent-review-commands.1',commands=results,pythonVersion=sys.version,pythonExecutable=sys.executable,pythonCanonical=str(pathlib.Path(sys.executable).resolve()),pythonSHA256=sha(pathlib.Path(sys.executable)),platform=platform.platform(),sourceFiles=source,sourceTreeSHA256=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest(),nativeExecuted=False,nativeInstancesQueried=False),indent=2,sort_keys=True)+'\n')
raise SystemExit(0 if all(x['exitCode']==0 for x in results) else 1)
