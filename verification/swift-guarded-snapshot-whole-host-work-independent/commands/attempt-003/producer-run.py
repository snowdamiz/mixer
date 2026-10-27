#!/usr/bin/env python3
"""Run only local pure Python controls; retain raw outcomes, including failures."""
import datetime, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path
D=Path(__file__).resolve().parent
args=sys.argv[1:]
if not args:raise SystemExit('explicit local Python script and arguments required')
if args[0] not in ('derive.py','test_work.py'):raise SystemExit('local pure script only')
base=D/'commands';base.mkdir(exist_ok=True)
index=1
while (base/f'attempt-{index:03}').exists():index+=1
out=base/f'attempt-{index:03}';out.mkdir()
for source in D.glob('*.py'):(out/('source-'+source.name)).write_bytes(source.read_bytes())
command=[sys.executable,'-B',str(D/args[0]),*args[1:]]
before=time.monotonic();at=datetime.datetime.now(datetime.timezone.utc).isoformat()
env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
result=subprocess.run(command,cwd=D,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=50)
(out/'stdout').write_bytes(result.stdout);(out/'stderr').write_bytes(result.stderr)
members=[]
for p in sorted(D.glob('*.py')):
 raw=p.read_bytes();members.append({'path':p.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
receipt={'at':at,'command':command,'cwd':str(D),'python':sys.version,'platform':platform.platform(),
 'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-before,
 'source_revision':'Frozen source146/host11 identities in work-interface/input-custody; no Git command run.',
 'source_files':members,'tree_sha256':hashlib.sha256(json.dumps(members,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(result.stderr).hexdigest(),
 'scope':'Pure offline host Python. No compiler/product/native/UI/capture/process inventory. Waited subprocess.',
 'child_waited':True,'compiler_or_product_executed':False}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
sys.stdout.buffer.write(result.stdout);sys.stderr.buffer.write(result.stderr)
raise SystemExit(result.returncode)
