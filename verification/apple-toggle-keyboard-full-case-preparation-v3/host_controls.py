#!/usr/bin/env python3
"""Retained host command receipts; only synthetic loopback and fake native boundaries."""
import datetime
import hashlib
import json
import pathlib
import platform
import subprocess
import sys
import time
BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE.parents[1]
assert not (BASE/'packet-seal.json').exists(),'Sealed host evidence is immutable'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
source={str(p.relative_to(ROOT)):sha(p) for p in sorted(BASE.rglob('*')) if p.is_file() and (p.suffix=='.py' or 'harness' in p.parts) and '.scratch' not in p.parts}
commands=[]
for script,expected in [('test_keyboard.py',9),('test_adapters.py',4),('test_full_case.py',23),('test_v2.py',21),('test_v3.py',12),('import_inventory.py',None)]:
    name=script.removesuffix('.py');argv=[sys.executable,'-B',str(BASE/script)]
    started=time.monotonic();observed=datetime.datetime.now(datetime.timezone.utc).isoformat()
    process=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=60)
    out=BASE/(name+'-final.stdout');err=BASE/(name+'-final.stderr');out.write_text(process.stdout);err.write_text(process.stderr)
    passed=process.returncode==0 and (expected is None or ('Ran '+str(expected)+' tests') in process.stderr and process.stderr.rstrip().endswith('OK'))
    commands.append(dict(argv=argv,cwd=str(ROOT),observedUTC=observed,elapsedSeconds=time.monotonic()-started,exitCode=process.returncode,
      expectedMethods=expected,passed=passed,stdoutSHA256=sha(out),stderrSHA256=sha(err)))
    if not passed:break
assert all(sha(ROOT/name)==digest for name,digest in source.items()),'Host sources changed during verification'
receipts=list((BASE/'.scratch').rglob('http-receipts.json'))
result=dict(schema=1,command=[sys.executable,'-B',str(BASE/'host_controls.py')],python=sys.version,platform=platform.platform(),
    executable=str(pathlib.Path(sys.executable).resolve()),executableSHA256=sha(pathlib.Path(sys.executable).resolve()),sourceFiles=source,
    sourceTreeSHA256=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest(),commands=commands,
    passed=len(commands)==6 and all(row['passed'] for row in commands),hostMethods=69,syntheticHTTPReceiptFiles=len(receipts),
    syntheticHTTPRequestsAcrossRetainedAttempts=sum(len(json.loads(path.read_bytes())) for path in receipts),nativeInstancesQueried=False,nativeCompiled=False,nativeExecuted=False,
    nativeQualification=False,physicalPhones='disconnected-deferred',gaAccepted=False)
(BASE/'host-controls.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(passed=result['passed'],methods=69,commands=len(commands))))
raise SystemExit(0 if result['passed'] else 1)
