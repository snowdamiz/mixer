#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
start=time.monotonic();argv=[sys.executable,str(OUT/'audit_packet.py')]
r=subprocess.run(argv,cwd=OUT.parents[1],capture_output=True,timeout=30)
(OUT/'audit.stdout').write_bytes(r.stdout);(OUT/'audit.stderr').write_bytes(r.stderr)
receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'cwd':str(OUT.parents[1]),
 'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start,'python':sys.version,'python_executable':sys.executable,
 'python_executable_sha256':sha(Path(sys.executable)),'audit_source_sha256':sha(OUT/'audit_packet.py'),
 'probe_source_manifest_sha256':sha(OUT/'probe-source-manifest.json'),'stdout_sha256':sha(OUT/'audit.stdout'),
 'stderr_sha256':sha(OUT/'audit.stderr'),'scope':'Finite offline custody/schema/layout controls only; no product semantic or lifetime tests'}
(OUT/'audit-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(r.stderr.decode(),end='');raise SystemExit(r.returncode)
