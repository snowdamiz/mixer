"""Run and retain each fresh independent review command in an exclusive attempt."""
import datetime
import hashlib
import json
import os
import pathlib
import platform
import subprocess
import sys
import time

HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
attempt=os.environ.get('MIXER_REVIEW_ATTEMPT','attempt-1')
logs=HERE/'commands'/attempt
logs.mkdir(parents=True,exist_ok=False)
sources={str(p.relative_to(ROOT)):sha(p) for p in sorted(HERE.glob('*.py'))}
for name in sources:
    (logs/pathlib.Path(name).name).write_bytes((ROOT/name).read_bytes())
commands=[('python-version',[sys.executable,'--version']),
          ('independent-input-inventory',[sys.executable,'-B',str(HERE/'inventory.py')]),
          ('producer-readonly-preflight',[sys.executable,'-B',str(ROOT/'verification/apple-toggle-keyboard-focus-v9-preparation/run.py'),'verify']),
          ('independent-actual-http-boundaries',[sys.executable,'-B',str(HERE/'host_checks.py')])]
results=[]
for label,argv in commands:
    started=time.monotonic()
    cp=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60,env={**os.environ,'MIXER_REVIEW_ATTEMPT':attempt})
    for suffix,data in [('stdout',cp.stdout),('stderr',cp.stderr)]:
        (logs/(label+'.'+suffix)).write_bytes(data)
    results.append(dict(name=label,argv=argv,cwd=str(ROOT),elapsedSeconds=time.monotonic()-started,
        exitCode=cp.returncode,observedUTC=datetime.datetime.now(datetime.UTC).isoformat(),
        stdoutSHA256=hashlib.sha256(cp.stdout).hexdigest(),stderrSHA256=hashlib.sha256(cp.stderr).hexdigest()))
    print(label,cp.returncode,cp.stdout.decode()[-5000:],cp.stderr.decode()[-2000:])
    if cp.returncode:
        break
result=dict(schema='mixer.apple-keyboard.v9-independent-review-commands.1',commands=results,
    pythonVersion=sys.version,pythonExecutable=sys.executable,pythonCanonical=str(pathlib.Path(sys.executable).resolve()),
    pythonSHA256=sha(pathlib.Path(sys.executable)),platform=platform.platform(),sourceFiles=sources,
    sourceTreeSHA256=hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
    passed=len(results)==len(commands) and all(x['exitCode']==0 for x in results),
    nativeExecuted=False,nativeInstancesQueried=False,compilationExecuted=False)
(logs/'commands.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
raise SystemExit(0 if result['passed'] else 1)
