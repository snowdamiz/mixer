"""Record exact pure checker commands/outputs; no product runner import."""
import datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
rows=[]
for name in ('extract_mir.py','price_mir.py','loop-audit.py','verify.py'):
 target=D/name;outdir=D/'commands'/name[:-3];outdir.mkdir(parents=True,exist_ok=True)
 argv=[sys.executable,str(target)];env=dict(PATH='/usr/bin:/bin',PYTHONDONTWRITEBYTECODE='1')
 at=datetime.datetime.now(datetime.timezone.utc).isoformat();started=time.monotonic()
 result=subprocess.run(argv,cwd=R,env=env,capture_output=True,timeout=60)
 (outdir/'stdout').write_bytes(result.stdout);(outdir/'stderr').write_bytes(result.stderr)
 row=dict(schema=1,at=at,argv=argv,cwd=str(R),environment=env,tool_sha256=sha(target.read_bytes()),python=sys.version,timeout_seconds=60,elapsed_seconds=time.monotonic()-started,exit_code=result.returncode,product_runtime=False,output={n:dict(path=str((outdir/n).relative_to(R)),bytes=len(v),sha256=sha(v)) for n,v in [('stdout',result.stdout),('stderr',result.stderr)]})
 (outdir/'receipt.json').write_text(json.dumps(row,sort_keys=True,indent=2)+'\n');rows.append(row)
 if result.returncode:raise SystemExit(result.stderr.decode())
(D/'command-index.json').write_text(json.dumps(dict(schema=1,commands=rows),sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status='all-pure-checks-pass',commands=len(rows))))
