"""New correction-only pure commands; no frozen producer-script replay."""
import datetime,hashlib,json,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1]
rows=[]
for name in ('custody.py','price_mir.py','verify.py'):
 p=D/name;out=D/'commands'/name[:-3];out.mkdir(parents=True,exist_ok=True)
 argv=[sys.executable,str(p)];env=dict(PATH='/usr/bin:/bin',PYTHONDONTWRITEBYTECODE='1')
 started=time.monotonic();at=datetime.datetime.now(datetime.timezone.utc).isoformat()
 r=subprocess.run(argv,cwd=R,env=env,capture_output=True,timeout=60)
 for n,b in [('stdout',r.stdout),('stderr',r.stderr)]:(out/n).write_bytes(b)
 row=dict(schema=1,at=at,argv=argv,cwd=str(R),environment=env,tool_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),python=sys.version,timeout_seconds=60,elapsed_seconds=time.monotonic()-started,exit_code=r.returncode,scope='correction pure custody/pricing/regression only; no product/original script replay/compiler',outputs={n:dict(path=str((out/n).relative_to(R)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in [('stdout',r.stdout),('stderr',r.stderr)]})
 (out/'receipt.json').write_text(json.dumps(row,sort_keys=True,indent=2)+'\n');rows.append(row)
 if r.returncode:raise SystemExit(r.stderr.decode())
(D/'command-index.json').write_text(json.dumps(dict(schema=1,commands=rows),sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status='correction-all-pure-checks-pass',commands=len(rows))))
