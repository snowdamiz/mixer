"""Pure preparation checks only; the one compiler command is never replayed."""
import datetime,hashlib,json,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1];rows=[]
for n in ('bind_acceptance.py','compare_mir.py','price_mir.py','verify.py'):
 p=D/n;o=D/'commands'/n[:-3];o.mkdir(parents=True,exist_ok=True)
 argv=[sys.executable,str(p)];env=dict(PATH='/usr/bin:/bin',PYTHONDONTWRITEBYTECODE='1');at=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic()
 r=subprocess.run(argv,cwd=R,env=env,capture_output=True,timeout=60)
 for k,b in [('stdout',r.stdout),('stderr',r.stderr)]:(o/k).write_bytes(b)
 row=dict(schema=1,at=at,argv=argv,cwd=str(R),environment=env,tool_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),python=sys.version,timeout_seconds=60,elapsed_seconds=time.monotonic()-start,exit_code=r.returncode,scope='pure source146 preparation, no product or compiler replay',outputs={k:dict(path=str((o/k).relative_to(R)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for k,b in [('stdout',r.stdout),('stderr',r.stderr)]})
 (o/'receipt.json').write_text(json.dumps(row,sort_keys=True,indent=2)+'\n');rows.append(row)
 if r.returncode:raise SystemExit(r.stderr.decode())
(D/'command-index.json').write_text(json.dumps(dict(schema=1,commands=rows),sort_keys=True,indent=2)+'\n');print(json.dumps(dict(status='all-pure-source146-checks-pass',commands=len(rows))))
