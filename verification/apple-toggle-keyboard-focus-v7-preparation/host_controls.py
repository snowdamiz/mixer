#!/usr/bin/env python3
"""Fresh actual-implementation checks plus exact unchanged transport binaries."""
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
import run as r
b=r.BASE
r.require(not (b/'packet-seal.json').exists(),'Sealed host controls cannot be overwritten')
groups=[('actual-v7-session-bridge-replay',[sys.executable,'-B',str(b/'test_v7.py')],21),('actual-native-Swift-resolver-host-provider',[str(b/'host-tools/selection-controls'),str(b/'swift-public-witness.json')],71),('exact-unchanged-shared-transport',[str(r.V6/'host-tools/transport-controls')],16),('exact-unchanged-independent-transport',[str(r.V6/'host-tools/transport-adversarial')],35)]
commands=[]
for name,argv,count in groups:
 start=time.monotonic();p=subprocess.run(argv,cwd=r.ROOT,capture_output=True,text=True,timeout=60,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','DEVELOPER_DIR':str(r.h.DEVELOPER)})
 if name=='actual-v7-session-bridge-replay':
  match=re.search(r'Ran (\d+) tests? in ',p.stderr);observed=int(match.group(1)) if match else None
 elif name=='actual-native-Swift-resolver-host-provider':observed=json.loads(p.stdout)['actualSwiftResolverControls'] if p.returncode==0 else None
 else:observed=json.loads(p.stdout)['sharedSwiftTransportChecks' if count==16 else 'independentSharedTransportChecks'] if p.returncode==0 else None
 passed=p.returncode==0 and observed==count
 commands.append(dict(name=name,argv=argv,cwd=str(r.ROOT),exitCode=p.returncode,expectedCount=count,observedCount=observed,stdout=p.stdout,stderr=p.stderr,elapsedSeconds=time.monotonic()-start,observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=passed))
 print(name,'PASS' if passed else 'FAIL',flush=True)
 if not passed:print(p.stderr,flush=True)
inputs=[*[b/name for name in ['run.py','fixtures.py','settings_telemetry.py','replay.py','keyboard_oracle.py','test_v7.py','host_controls.py']],*b.glob('*.swift'),*b.glob('harness/UITests/*.swift'),b/'host-tools/selection-controls',b/'swift-public-witness.json',r.V6/'host-tools/transport-controls',r.V6/'host-tools/transport-adversarial']
passed=all(c['passed'] for c in commands)
result=dict(schema='mixer.apple-toggle.keyboard-v7-actual-implementation-host-controls.1',observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=[sys.executable,'-B',str(pathlib.Path(__file__).resolve())],pythonVersion=sys.version,pythonExecutableSHA256=r.sha(pathlib.Path(sys.executable).resolve()),platform=platform.platform(),sourceRevisionContext=r.read(b/'build-products-manifest.json')['sourceRevisionContext'],sourceFiles={str(p.relative_to(r.ROOT)):r.sha(p) for p in inputs},commands=commands,actualSessionTestMethods=21,actualSwiftResolverControls=71,unchangedTransportControls=[16,35],reviewModel37CountedAsImplementationTests=False,allRequiredGroupsPassed=passed,exitCode=0 if passed else 1,nativeExecuted=False,nativeInstancesQueried=False,scope='Synthetic actual Session/Bridge/replay and exact native resolver on macOS host; no XCUI runtime or application cases')
r.h.write(b/'host-controls.json',result)
raise SystemExit(0 if passed else 1)
