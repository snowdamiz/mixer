#!/usr/bin/env python3
"""Run only the independent offline audit and preserve every invocation."""
import datetime
import hashlib
import json
import pathlib
import platform
import subprocess
import sys
import time

OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def sha(data): return hashlib.sha256(data).hexdigest()
def write(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def closure():
    names=json.loads((ROOT/'verification/swift-count-plan-retention-candidate/baseline-source-manifest.json').read_bytes())
    return sha((json.dumps({n:sha((ROOT/'vm'/n).read_bytes()) for n in names},indent=2,sort_keys=True)+'\n').encode())
existing=list((OUT/'commands').glob('audit-*')) if (OUT/'commands').exists() else []
dest=OUT/'commands'/f'audit-{len(existing)+1:02d}'
dest.mkdir(parents=True,exist_ok=False)
argv=[sys.executable,'-B',str(OUT/'audit.py')]
before=closure()
revision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
command={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'cwd':str(ROOT),'timeoutSeconds':60,
         'scope':'Read-only finite offline Python evidence audit; in-memory tar members, no Rust/native/hosted execution',
         'revision':revision,'python':{'path':sys.executable,'version':sys.version,'sha256':sha(pathlib.Path(sys.executable).read_bytes())},
         'platform':platform.platform(),'liveClosureBefore':before,
         'sourceSHA256':sha((OUT/'audit.py').read_bytes()),'runnerSHA256':sha(pathlib.Path(__file__).read_bytes()),
         'producerSealSHA256':sha((ROOT/'verification/swift-count-plan-retention-candidate/seal.json').read_bytes())}
write(dest/'command.json',command)
(dest/'source.py').write_bytes((OUT/'audit.py').read_bytes())
start=time.monotonic()
run=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60)
(dest/'stdout').write_bytes(run.stdout);(dest/'stderr').write_bytes(run.stderr)
(dest/'audit-results.json').write_bytes((OUT/'audit-results.json').read_bytes())
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exitCode':run.returncode,'seconds':round(time.monotonic()-start,3),
        'stdoutBytes':len(run.stdout),'stderrBytes':len(run.stderr),'stdoutSHA256':sha(run.stdout),'stderrSHA256':sha(run.stderr),
        'liveClosureAfter':closure(),'producerSealSHA256After':sha((ROOT/'verification/swift-count-plan-retention-candidate/seal.json').read_bytes()),
        'auditResultSHA256':sha((OUT/'audit-results.json').read_bytes())}
write(dest/'result.json',result)
print(json.dumps({'command':str(dest.relative_to(ROOT)),'exitCode':run.returncode,'seconds':result['seconds']}))
print(run.stderr.decode(),end='')
sys.exit(run.returncode)
